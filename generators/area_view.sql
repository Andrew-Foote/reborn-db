-- although form notes' content will be the same for a given pokemon across all maps, their numbers
-- may differ between maps, due to the order in which the pokemon are listed
with "encounter_form_note" ("map", "id", "pokemon", "content") as (
    select
        "encounter"."map"
        ,row_number() over (partition by "encounter"."map") as "id"
        ,"encounter"."pokemon"
        ,replace("form_note"."note", '$ID', row_number() over (partition by "encounter"."map")) as "note"
    from (
        select "encounter"."map", "encounter"."pokemon" from "pokemon_encounter_rate_by_level_range" as "encounter"
        join "encounter_method" as "method" on "method"."name" = "encounter"."method"
        join "pokemon" on "pokemon"."id" = "encounter"."pokemon"
        order by "encounter"."map", "method"."order", "encounter"."rate" collate "frac" desc, "pokemon"."number"
    ) as "encounter"
    left join "pokemon_encounter_form_note" as "form_note" on "form_note"."pokemon" = "encounter"."pokemon"
    where "form_note"."note" is not null
    group by "encounter"."map", "encounter"."pokemon"
)
,"event_encounter_form_note_w_id" ("map", "id", "encounter", "content") as (
    select
        "encounter"."map"
        ,row_number() over (partition by "encounter"."map") as "id"
        ,"encounter"."id" as "encounter"
        ,replace("form_note"."note", '$ID', row_number() over (partition by "encounter"."map")) as "note"
    from (
        select "encounter_map"."map", "encounter"."id"
        from "encounter_map_event" as "encounter_map"
        join "event_encounter" as "encounter" on "encounter"."id" = "encounter_map"."encounter"
    ) as "encounter"
    left join "event_encounter_form_note" as "form_note" on "form_note"."encounter" = "encounter"."id"
    where "form_note"."note" is not null
)
,"encounter" ("map", "method", "rate", "pokemon", "form", "form_note", "level_range", "movesets") as (
     select
        "encounter"."map", "method"."desc", "encounter"."rate"
        ,"pokemon"."name" as "pokemon", "encounter"."form", "form_note"."id"
        ,"encounter"."level_range"
        ,(
            select json_group_array(json_object('level', "level", 'form', "form", 'moves', "moves"))
            from (
                select "level_range"."value" as "level", "random_encounter_moveset"."form", "random_encounter_moveset"."moves"
                from json_each("encounter"."level_range") as "level_range"
                join "random_encounter_moveset" on (
                    "random_encounter_moveset"."map" = "encounter"."map"
                    and "random_encounter_moveset"."method" = "encounter"."method"
                    and "random_encounter_moveset"."pokemon" = "encounter"."pokemon"
                    and ("random_encounter_moveset"."form" = "encounter"."form" or "encounter"."form" is null)
                    and "random_encounter_moveset"."level" = "level_range"."value"
                )
                order by "level_range"."key"
            )
        ) as "movesets"
    from "pokemon_encounter_rate_by_level_range" as "encounter"
    join "encounter_method" as "method" on "method"."name" = "encounter"."method"
    join "pokemon" on "pokemon"."id" = "encounter"."pokemon"
    left join "pokemon_form" as "form" on (
        "form"."pokemon" = "encounter"."pokemon" and "form"."name" = "encounter"."form"
    )
    left join "encounter_form_note" as "form_note" on (
        "form_note"."map" = "encounter"."map" and "form_note"."pokemon" = "encounter"."pokemon"
    )
    order by
        "encounter"."map", "method"."order", "encounter"."rate" collate "frac" desc
        ,"pokemon"."number", "form"."order"
)
select "map"."id", json_object(
    'id', "map"."id", 'name', "map"."name"
    ,'parent_id', "map"."parent_id", 'parent_name', "parent"."name"
    ,'backdrop', "map"."battle_backdrop", 'field_effect', "field_effect"."name"
    ,'outdoor', "map"."outdoor", 'bicycle_usable', "map"."bicycle_usable"
    ,'flashable', "map"."flashable"
    ,'weather', case when "map"."weather_chance" = 100 then "map"."weather" else null end
    ,'underwater_id', "map"."underwater_map", 'underwater_name', "underwater"."name"
    ,'surface_id', "surface"."id", 'surface_name', "surface"."name"
    ,'children', ifnull(json("children"."all"), json_array())
    ,'encrates', ifnull(json("encrates"."all"), json_array())
    ,'encounters', ifnull(json("encounters"."all"), json_array())
    ,'encounter_form_notes', ifnull(json("encounter_form_notes"."all"), json_array())
    ,'special_encounters', ifnull(json("special_encounters"."all"), json_array())
    ,'event_encounter_form_notes', ifnull(json("event_encounter_form_notes"."all"), json_array())
)
from "map"
left join "map" as "parent" on "parent"."id" = "map"."parent_id"
left join "field_effect" on "field_effect"."backdrop" = "map"."battle_backdrop"
left join "map" as "underwater" on "underwater"."id" = "map"."underwater_map"
left join "map" as "surface" on "surface"."underwater_map" = "map"."id"
left join (
    select "child"."parent" as "map", json_group_array(json_object(
        'id', "child"."id", 'name', "child"."name"
    )) as "all" from (
        select "parent"."id" as "parent", "child"."id", "child"."name"
        from "map" as "child" join "map" as "parent" on "parent"."id" = "child"."parent_id"
        order by "child"."order"
    ) as "child"
    group by "child"."parent"
) as "children" on "children"."map" = "map"."id"
left join (
    select "encrate"."map", json_group_array(json_object(
        'terrain', "encrate"."terrain", 'rate', frac_mul(frac_div("encrate"."rate", 250), 100)
    )) as "all" from (
        select "rate"."map", "terrain"."name" as "terrain", "rate"."rate"
        from "map_encounter_rate" as "rate"
        join "terrain" on "terrain"."name" = "rate"."terrain"
        order by "terrain"."order"
    ) as "encrate"
    group by "encrate"."map"
) as "encrates" on "encrates"."map" = "map"."id"
left join (
    select "encounter"."map", json_group_array(json_object(
        'method', "encounter"."method"
        ,'pokemon', "encounter"."pokemon", 'form', "encounter"."form"
        ,'form_note', "encounter"."form_note"
        ,'level_range', json("encounter"."level_range")
        ,'rate', frac_mul("encounter"."rate", 100)
        ,'movesets', json("encounter"."movesets")
    )) as "all" from "encounter"
    group by "encounter"."map"
) as "encounters" on "encounters"."map" = "map"."id"
left join (
    select "form_note"."map", json_group_array(json_object(
        'id', "form_note"."id", 'content', "form_note"."content"
    )) as "all"
    from "encounter_form_note" as "form_note"
    group by "form_note"."map"
) as "encounter_form_notes" on "encounter_form_notes"."map" = "map"."id"
left join (
    select "form_note"."map", json_group_array(json_object(
        'id', "form_note"."id", 'content', "form_note"."content"
    )) as "all"
    from "event_encounter_form_note_w_id" as "form_note"
    group by "form_note"."map"
) as "event_encounter_form_notes" on "event_encounter_form_notes"."map" = "map"."id"
left join (
    select "encounter"."map", json_group_array(json_object(
        'pokemon', "encounter"."pokemon", 'form', "encounter"."form", 'form_note', "encounter"."form_note",
        'type', "encounter"."type", 'level', "encounter"."level", 'nickname', "encounter"."nickname",
        'ot', "encounter"."ot", 'trainer_id', "encounter"."trainer_id",
        'hp', "encounter"."hp", 'gender', "encounter"."gender", 'friendship', "encounter"."friendship",
        'held_item', "encounter"."held_item", 'ability', "encounter"."ability",
        'move_preference', json("encounter"."move_preference"), 'move_sets', json("encounter"."move_sets"),
        'ivs', json("encounter"."ivs")
    )) as "all" from (
        select
            "encounter_map"."map" as "map",
            "pokemon"."name" as "pokemon", "form"."name" as "form", "form_note"."id" as "form_note",
            "encounter"."type", "encounter"."level", "encounter"."nickname",
            "encounter"."hp", "encounter"."gender", "held_item"."name" as "held_item",
            "encounter"."friendship", "ability"."name" as "ability", "encounter_ot"."ot", "encounter_ot"."trainer_id",
            json_object('id', "move_preference"."id", 'name', "move_preference"."name") as "move_preference",
            (
                select json_group_array(json("moves"))
                from (
                    select json_group_array(
                       json_object('id', "move"."id", 'name', "move"."name")
                    ) as "moves"
                    from "event_encounter_extra_move_set" as "set"
                    join "event_encounter_move" as "encmove" on "encmove"."set" = "set"."id"
                    join "move" on "move"."id" = "encmove"."move"
                    where "set"."encounter" = "encounter"."id"
                    group by "set"."id"
                ) as "move_sets_subq"
            ) as "move_sets",
            (
                select json_group_array(
                    json_object('stat', "stat"."name", 'value', "iv"."value")
                )
                from "event_encounter_iv" as "iv"
                join "stat" on "stat"."id" = "iv"."stat"
                where "iv"."encounter" = "encounter"."id"
                order by "stat"."order"
            ) as "ivs"
        from "encounter_map_event" as "encounter_map"
        join "event_encounter" as "encounter" on "encounter"."id" = "encounter_map"."encounter"
        join "pokemon" on "pokemon"."id" = "encounter"."pokemon"
        left join "pokemon_form" as "form" on (
            "form"."pokemon" = "encounter"."pokemon" and "form"."name" = "encounter"."form"
        )
        left join "event_encounter_form_note_w_id" as "form_note" on "form_note"."encounter" = "encounter"."id"
        left join "item" as "held_item" on "held_item"."id" = "encounter"."held_item"
        left join "pokemon_ability" on (
            "pokemon_ability"."pokemon" = "form"."pokemon"
            and "pokemon_ability"."form" = "form"."name"
            and "pokemon_ability"."index" = "encounter"."ability"
        )
        left join "ability" on "ability"."id" = "pokemon_ability"."ability"
        left join "event_encounter_ot" as "encounter_ot" on "encounter_ot"."encounter" = "encounter"."id"
        left join "move" as "move_preference" on "move_preference"."id" = "encounter"."move_preference"
        order by "pokemon"."number", "form"."order"
    ) as "encounter"
    group by "encounter"."map"    
) as "special_encounters" on "special_encounters"."map" = "map"."id"
