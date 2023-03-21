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
,"encounter" ("map", "method", "rate", "pokemon", "form", "form_note", "min_level", "max_level") as (
     select
        "encounter"."map", "method"."desc", "encounter"."rate"
        ,"pokemon"."name" as "pokemon", "encounter"."form", "form_note"."id"
        ,"encounter"."min_level", "encounter"."max_level"
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
        ,'min_level', "encounter"."min_level", 'max_level', "encounter"."max_level"
        ,'rate', frac_mul("encounter"."rate", 100)
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
    select "encounter"."map", json_group_array(json_object(
        'pokemon', "encounter"."pokemon", 'form', "encounter"."form"
        ,'type', "encounter"."type", 'level', "encounter"."level",
        'ot', "encounter"."ot", 'trainer_id', "encounter"."trainer_id",
        'hp', "encounter"."hp", 'friendship', "encounter"."friendship",
        'held_item', "encounter"."held_item", 'ability', "encounter"."ability",
        'moves', json("encounter"."moves"), 'ivs', json("encounter"."ivs")
    )) as "all" from (
        select
            "encounter"."map_id" as "map",
            "pokemon"."name" as "pokemon", "form"."name" as "form",
            "encounter"."type", "encounter"."level", "encounter"."ot", "encounter"."trainer_id",
            "encounter"."gender", "encounter"."hp", "encounter"."friendship",
            "held_item"."name" as "held_item", "ability"."name" as "ability",
            (
                select json_group_array(
                    json_object('id', "move"."id", 'name', "move"."name")
                )
                from json_each("encounter"."moves") as "encmove"
                join "move" on "move"."id" = "encmove"."value"
            ) as "moves",
            (
                select json_group_array(
                    json_object('stat', "stat"."name", 'value', "iv"."value")
                )
                from json_each("encounter"."ivs") as "iv"
                join "stat" on "stat"."order" = "iv"."key"
            ) as "ivs"
        from "event_encounter" as "encounter"
        join "pokemon" on "pokemon"."id" = "encounter"."pokemon"
        join "pokemon_form" as "form" on (
            "form"."pokemon" = "encounter"."pokemon" and "form"."order" = "encounter"."form"
        )
        left join "item" as "held_item" on "held_item"."id" = "encounter"."held_item"
        left join "pokemon_ability" on (
            "pokemon_ability"."pokemon" = "form"."pokemon"
            and "pokemon_ability"."form" = "form"."name"
            and "pokemon_ability"."index" = "encounter"."ability" + 1
        )
        left join "ability" on "ability"."id" = "pokemon_ability"."ability"
        order by "pokemon"."number", "form"."order"
    ) as "encounter"
    group by "encounter"."map"    
) as "special_encounters" on "special_encounters"."map" = "map"."id"
