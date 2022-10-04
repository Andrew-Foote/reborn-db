with
"egg_group_o" as (
    select
        "pokemon_egg_group"."pokemon",
        "egg_group"."pbs_name" as "id", "egg_group"."name"
    from "pokemon_egg_group"
    join "egg_group" on "egg_group"."name" = "pokemon_egg_group"."egg_group"
    order by "pokemon_egg_group"."egg_group"
),
"form_o" as (
    with "type_effect_o" as (
        select "type_effect2".* from "type_effect2"
        join "type" as "attacking_type" on "attacking_type"."id" = "type_effect2"."attacking_type"
        order by "attacking_type"."code"
    ),
    "level_move_o" as (
        select
        	"level_move"."pokemon", "level_move"."form", "level_move"."level",
        	"move"."id", "move"."name"
        from "level_move" join "move" on "move"."id" = "level_move"."move"
        order by "level_move"."pokemon", "level_move"."form", "level_move"."level", "level_move"."order"
    )
    select
        "form"."pokemon"
        ,"form"."name"
        ,"form"."order"
        ,"form"."pokedex_entry"
        ,"form"."catch_rate"
        ,"form"."height"
        ,"form"."weight"
        ,case when "type2"."id" is null
            then json_array("type1"."name")
            else json_array("type1"."name", "type2"."name")
        end as "types"
        ,"double_weaknesses"."all" as "double_weaknesses"
        ,"weaknesses"."all" as "weaknesses"
        ,"resistances"."all" as "resistances"
        ,"double_resistances"."all" as "double_resistances"
        ,"immunities"."all" as "immunities"
        ,"abilities"."all" as "abilities"
        ,case when "wild_always_held_item"."id" is null
            then "wild_held_items"."all"
            else json_array(json_object('rarity', '100', 'name', "wild_always_held_item"."name"))
        end as "wild_held_items"
        ,"base_stats"."all" as "base_stats"
        ,"base_stats"."bst" as "bst"
        ,"ev_yields"."all" as "ev_yields"
        ,"ev_yields"."evtot" as "evtot"
        ,"level_moves"."all" as "level_moves"
        ,"evolution_moves"."all" as "evolution_moves"
        ,"egg_moves"."all" as "egg_moves"
        ,"machine_moves"."all" as "machine_moves"
        ,"tutor_moves"."all" as "tutor_moves"
        ,"preevo_moves"."all" as "preevo_moves"
        ,"encounters"."all" as "encounters"
        ,"specialencs"."all" as "specialencs"
        ,"evo_tree"."branches" as "evo_tree"
        ,"sprite"."sprite" as "sprite"
        ,json_object(
            'method', case
                when "megev_item"."id" is not null then 'item'
                when "megev_move"."id" is not null then 'move'
                else null
            end
            ,'item', json_object('id', "megev_item"."id", 'name', "megev_item"."name")
            ,'move', json_object('id', "megev_move"."id", 'name', "megev_move"."name")
        ) as "mega_evolution",
        (
            select json_group_array(json_object(
                'name', "baby"."name", 'form', "baby"."form",
                'incense', json("baby"."incense"), 'probability', "baby"."probability"
            ))
            from (
                select
                    "baby_pokemon"."name", "baby"."baby_form" as "form",
                    json_object(
                        'id', "item"."id", 'name', "item"."name",
                        'relation', "baby"."incense"
                    ) as "incense",
                    "baby"."probability"
                from "baby"
                join "pokemon" as "baby_pokemon" on "baby_pokemon"."id" = "baby"."baby"
                left join "incense" on "incense"."pokemon" = "baby"."baby"
                left join "item" on "item"."id" = "incense"."item"
                where "baby"."adult" = "form"."pokemon" and "baby"."adult_form" = "form"."name"
                order by "baby"."incense", "baby_pokemon"."number"
            ) as "baby"
        ) as "babies"
    from "pokemon_form" as "form"
    left join "pokemon_sprite" as "sprite" on (
     	"sprite"."pokemon" = "form"."pokemon" and "sprite"."form" = "form"."name"
     	and "sprite"."type" = 'front' and "sprite"."shiny" = 0 and
    	("sprite"."gender" is null or "sprite"."gender" = 'Male')
    )
    join "pokemon_type" as "pokemon_type1" on (
        "pokemon_type1"."index" = 1
        and "pokemon_type1"."pokemon" = "form"."pokemon" and "pokemon_type1"."form" = "form"."name"
    )
    join "type" as "type1" on "type1"."id" = "pokemon_type1"."type"
    left join "pokemon_type" as "pokemon_type2" on (
        "pokemon_type2"."index" = 2
        and "pokemon_type2"."pokemon" = "form"."pokemon" and "pokemon_type2"."form" = "form"."name"
    )
    left join "type" as "type2" on "type2"."id" = "pokemon_type2"."type"
    left join (
        select
            "type_effect"."defending_type1",  "type_effect"."defending_type2",
            json_group_array("type_effect"."attacking_type") as "all"
        from "type_effect_o" as "type_effect"
        where "type_effect"."multiplier" = 4
        group by "type_effect"."defending_type1", "type_effect"."defending_type2"
    ) as "double_weaknesses" on (
        "double_weaknesses"."defending_type1" = "type1"."id"
        and "double_weaknesses"."defending_type2" is "type2"."id"
    )
    left join (
        select
            "type_effect"."defending_type1",  "type_effect"."defending_type2",
            json_group_array("type_effect"."attacking_type") as "all"
        from "type_effect_o" as "type_effect"
        where "type_effect"."multiplier" = 2
        group by "type_effect"."defending_type1", "type_effect"."defending_type2"
    ) as "weaknesses" on (
        "weaknesses"."defending_type1" = "type1"."id"
        and "weaknesses"."defending_type2" is "type2"."id"
    )
    left join (
        select
            "type_effect"."defending_type1",  "type_effect"."defending_type2",
            json_group_array("type_effect"."attacking_type") as "all"
        from "type_effect_o" as "type_effect"
        where "type_effect"."multiplier" = 0.5
        group by "type_effect"."defending_type1", "type_effect"."defending_type2"
    ) as "resistances" on (
        "resistances"."defending_type1" = "type1"."id"
        and "resistances"."defending_type2" is "type2"."id"
    )
    left join (
        select
            "type_effect"."defending_type1",  "type_effect"."defending_type2",
            json_group_array("type_effect"."attacking_type") as "all"
        from "type_effect_o" as "type_effect"
        where "type_effect"."multiplier" = 0.25
        group by "type_effect"."defending_type1", "type_effect"."defending_type2"
    ) as "double_resistances" on (
        "double_resistances"."defending_type1" = "type1"."id"
        and "double_resistances"."defending_type2" is "type2"."id"
    )
    left join (
        select
            "type_effect"."defending_type1",  "type_effect"."defending_type2",
            json_group_array("type_effect"."attacking_type") as "all"
        from "type_effect_o" as "type_effect"
        where "type_effect"."multiplier" = 0
        group by "type_effect"."defending_type1", "type_effect"."defending_type2"
    ) as "immunities" on (
        "immunities"."defending_type1" = "type1"."id"
        and "immunities"."defending_type2" is "type2"."id"
    )
    join (
        select "ability"."pokemon", "ability"."form", json_group_object(
            "ability"."index",
            json_object('name', "ability"."name", 'desc', "ability"."desc")
        ) as "all"
        from (
            select
                "pokemon_ability"."pokemon", "pokemon_ability"."form",
                "pokemon_ability"."index", "ability"."name", "ability"."desc"
            from "pokemon_ability"
            join "ability" on "ability"."id" = "pokemon_ability"."ability"
            order by "pokemon_ability"."index"
        ) as "ability"
        group by "ability"."pokemon", "ability"."form"
    ) as "abilities" on "abilities"."pokemon" = "form"."pokemon" and "abilities"."form" = "form"."name"
    left join "item" as "wild_always_held_item" on (
        "wild_always_held_item"."id" != 'DUMMY' and "wild_always_held_item"."id" = "form"."wild_always_held_item"
    )
    left join (
        select "wild_held_item"."pokemon", "wild_held_item"."form", json_group_array(json_object(
            'rarity', "wild_held_item"."rarity", 'name', "wild_held_item"."name"
        )) as "all"
        from (
            select
                "wild_held_item"."pokemon", "wild_held_item"."form",
                "rarity"."percentage" as "rarity", "item"."name"
            from "wild_held_item"
            join "wild_held_item_rarity" as "rarity" on "rarity"."name" = "wild_held_item"."rarity"
            join "item" on "item"."id" = "wild_held_item"."item"
            order by "rarity"."order"
        ) as "wild_held_item"
        group by "wild_held_item"."pokemon", "wild_held_item"."form"
    ) as "wild_held_items" on (
        "form"."wild_always_held_item" = 'DUMMY' and
        "wild_held_items"."pokemon" = "form"."pokemon" and "wild_held_items"."form" = "form"."name"
    )
    join (
        select
            "base_stat"."pokemon", "base_stat"."form",
            json_group_object("base_stat"."stat", "base_stat"."value") as "all",
            sum("base_stat"."value") as "bst"
        from (
            select "base_stat"."pokemon", "base_stat"."form", "stat"."id" as "stat", "base_stat"."value"
            from "base_stat"
            join "stat" on "stat"."id" = "base_stat"."stat"
            order by "stat"."order"
        ) as "base_stat"
        group by "base_stat"."pokemon", "base_stat"."form"
    ) as "base_stats" on "base_stats"."pokemon" = "form"."pokemon" and "base_stats"."form" = "form"."name"
    join (
        select
            "ev_yield"."pokemon", "ev_yield"."form",
            json_group_object("ev_yield"."stat", "ev_yield"."value") as "all",
            sum("ev_yield"."value") as "evtot"
        from (
            select "ev_yield"."pokemon", "ev_yield"."form", "stat"."id" as "stat", "ev_yield"."value"
            from "ev_yield"
            join "stat" on "stat"."id" = "ev_yield"."stat"
            order by "stat"."order"
        ) as "ev_yield"
        group by "ev_yield"."pokemon", "ev_yield"."form"
    ) as "ev_yields" on "ev_yields"."pokemon" = "form"."pokemon" and "ev_yields"."form" = "form"."name"
    join (
        select "level_move"."pokemon", "level_move"."form", json_group_array(json_object(
            'level', "level_move"."level", 'id', "level_move"."id", 'name', "level_move"."name"
        )) as "all"
        from "level_move_o" as "level_move" where "level_move"."level" != 0
        group by "level_move"."pokemon", "level_move"."form"
    ) as "level_moves" on (
        "level_moves"."pokemon" = "form"."pokemon"
        and "level_moves"."form" = "form"."name"
    )
    left join (
        select "level_move"."pokemon", "level_move"."form", json_group_array(json_object(
        	'id', "level_move"."id", 'name', "level_move"."name"
        )) as "all"
        from "level_move_o" as "level_move" where "level_move"."level" = 0
        group by "level_move"."pokemon", "level_move"."form"
    ) as "evolution_moves" on (
        "evolution_moves"."pokemon" = "form"."pokemon"
        and "evolution_moves"."form" = "form"."name"
    )
    left join (
        select "machine_move"."pokemon", "machine_move"."form", json_group_array(json_object(
            'item', "machine_move"."item", 'id', "machine_move"."id", 'name', "machine_move"."name"
        )) as "all"
        from (
            select "machine_move"."pokemon", "machine_move"."form", "move"."id", "move"."name", "item"."name" as "item"
            from "machine_move"
            join "move" on "move"."id" = "machine_move"."move"
            join "machine_item" as "machine" on "machine"."move" = "move"."id"
            join "item" on "item"."id" = "machine"."item"
            order by "machine"."type", "machine"."number"
        ) as "machine_move"
        group by "machine_move"."pokemon", "machine_move"."form"
    ) as "machine_moves" on "machine_moves"."pokemon" = "form"."pokemon" and "machine_moves"."form" = "form"."name"
    left join (
        select "tutor_move"."pokemon", "tutor_move"."form", json_group_array(json_object(
        	'id', "tutor_move"."id", 'name', "tutor_move"."name"
        )) as "all"
        from (
            select "tutor_move"."pokemon", "tutor_move"."form", "move"."id", "move"."name"
            from "tutor_move"
            join "move" on "move"."id" = "tutor_move"."move"
            order by "tutor_move"."pokemon", "tutor_move"."form", "move"."name"
        ) as "tutor_move"
        group by "tutor_move"."pokemon", "tutor_move"."form"
    ) as "tutor_moves" on "tutor_moves"."pokemon" = "form"."pokemon" and "tutor_moves"."form" = "form"."name"
    left join (
    	select "preevo_move"."pokemon", "preevo_move"."form", json_group_array(json_object(
    		'preevo', "preevo_move"."preevo", 'preevo_form', "preevo_move"."preevo_form",
    		'id', "preevo_move"."id",
    		'name', "preevo_move"."name", 'method', "preevo_move"."method", 'level', "preevo_move"."level"
    	)) as "all"
    	from (
    		select
    			"preevo_move"."pokemon", "preevo_move"."form", "preevo"."name" as "preevo", "preevo_move"."preevo_form",
    			"move"."id", "move"."name", "preevo_move"."method", "preevo_move"."level"
    		from "preevo_move"
    		join "move" on "move"."id" = "preevo_move"."move"
    		join "pokemon_form" as "preevo_form" on "preevo_form"."pokemon" = "preevo_move"."preevo" and "preevo_form"."name" = "preevo_move"."preevo_form"
    		join "pokemon" as "preevo" on "preevo"."id" = "preevo_form"."pokemon"
    		-- preevo_move.method has three values: 'level', 'machine' and 'tutor'
    		-- which just happen to be in the right order alphabetically
    		-- should probably handle this better at some point though
    		order by "preevo_move"."dist" desc, "preevo_form"."order", "preevo_move"."method", "preevo_move"."level", "preevo_move"."order", "move"."name"
    	) as "preevo_move"
    	group by "preevo_move"."pokemon", "preevo_move"."form"
    ) as "preevo_moves" on "preevo_moves"."pokemon" = "form"."pokemon" and "preevo_moves"."form" = "form"."name"
    left join (
        select
            "encounter"."pokemon", "encounter"."form",
            json_group_array(json_object(
                'map_id', "encounter"."map_id", 'map_name', "encounter"."map_name", 'method', "encounter"."method",
                'min_level', "encounter"."min_level", 'max_level', "encounter"."max_level", 'rate',
                frac_mul("encounter"."rate", 100)
            )) as "all"
        from (
            select
                "encounter"."pokemon", "encounter"."form", "map"."id" as "map_id", "map"."name" as "map_name",
                "method"."desc" as "method", "encounter"."min_level", "encounter"."max_level", "encounter"."rate"
            from "pokemon_encounter_rate_by_level_range" as "encounter"
            join "map" on "map"."id" = "encounter"."map"
            join "encounter_method" as "method" on "method"."name" = "encounter"."method"
            order by
                "encounter"."pokemon", "encounter"."form", 
                "map"."order", "method"."order",
                "encounter"."rate" collate "frac" desc
        ) as "encounter"
        group by "encounter"."pokemon", "encounter"."form"
    ) as "encounters" on "encounters"."pokemon" = "form"."pokemon" and (
        "encounters"."form" = "form"."name" or "encounters"."form" is null
    )
    left join (
        select
            "specialenc"."pokemon", "specialenc"."form",
            json_group_array(json_object(
                'map_id', "specialenc"."map_id", 'map_name', "specialenc"."map_name",
                'type', "specialenc"."type", 'level', "specialenc"."level"
            )) as "all"
        from (
            select
                "encounter"."pokemon", "encounter"."form",
                "map"."id" as "map_id", "map"."name" as "map_name",
                "encounter"."type", "encounter"."level"
            from "event_encounter" as "encounter"
            join "map" on "map"."id" = "encounter"."map_id"
            order by "map"."order"
        ) as "specialenc"
        group by "specialenc"."pokemon", cast("specialenc"."form" as int) -- string vs. int diff cause sunnecesary splitting
    ) as "specialencs" on "specialencs"."pokemon" = "form"."pokemon" and "specialencs"."form" = "form"."order"
    left join (
        with recursive "evo_base" ("pokemon", "form", "base_pokemon", "base_form") as (
            select "form"."pokemon", "form"."name", "form"."pokemon", "form"."name"
            from "pokemon_form" as "form"
            join "pokemon" on "pokemon"."id" = "form"."pokemon"
            where "pokemon"."evolves_from" is null
            union all
            select
                "evolution"."to", "evolution"."to_form",
                "evo_base"."base_pokemon", "evo_base"."base_form"
            from "evo_base"
            join "evolution" on (
                "evolution"."from" = "evo_base"."pokemon"
                and "evolution"."from_form" = "evo_base"."form"
            )
        )
        select * from "evo_base"
    ) as "evo_base" on "evo_base"."pokemon" = "form"."pokemon" and "evo_base"."form" = "form"."name"
    left join (
        select "egg_move"."pokemon", "egg_move"."form", json_group_array(json_object(
        	'id', "egg_move"."id", 'name', "egg_move"."name"
        )) as "all"
        from (
            select "egg_move"."pokemon", "egg_move"."form", "move"."id", "move"."name"
            from "egg_move"
            join "move" on "move"."id" = "egg_move"."move"
            order by "egg_move"."pokemon", "egg_move"."form", "move"."name"
        ) as "egg_move"
        group by "egg_move"."pokemon", "egg_move"."form"
    ) as "egg_moves" on "egg_moves"."pokemon" = "form"."pokemon" and "egg_moves"."form" = "form"."name"
    -- ) as "egg_moves" on "egg_moves"."pokemon" = "evo_base"."base_pokemon" and "egg_moves"."form" = "evo_base"."base_form"
    left join (
        with recursive "evo_tree" (
            "level", "root", "root_form", "id", "form", "pokemon_order", "form_order", "node"
        ) as (
            select
                0, "pokemon"."id", "form"."name", "pokemon"."id", "form"."name",
                "pokemon"."number", "form"."order",
                json_object(
                    'methods', json_array(),
                    'result', json_object(
                        'id', "pokemon"."id", 'name', "pokemon"."name", 'form', "form"."name"
                    )
                )
            from "pokemon" join "pokemon_form" as "form" on "form"."pokemon" = "pokemon"."id"
            where "evolves_from" is null
            union all
            select
                "evo_tree"."level" + 1, "evo_tree"."root", "evo_tree"."root_form",
                "pokemon"."id", "form"."name", "pokemon"."number", "form"."order",
                json_object(
                    'methods', json("evolution"."schemes")
                    ,'result', json_object(
                        'id', "evolution"."to",
                        'name', "pokemon"."name",
                        'form', "evolution"."to_form"
                    )
                )
            from "pokemon_evolution_schemes" as "evolution" join "evo_tree" on (
                "evolution"."from" = "evo_tree"."id"
                and "evolution"."from_form" = "evo_tree"."form"
            )
            join "pokemon" on "pokemon"."id" = "evolution"."to"
            join "pokemon_form" as "form" on (
                "form"."pokemon" = "evolution"."to" and "form"."name" = "evolution"."to_form"
            )
            order by "evo_tree"."level" + 1 desc, "pokemon"."number", "form"."order"
        )
        select
            "evo_tree"."root", "evo_tree"."root_form",
            df2tree("evo_tree"."level", "evo_tree"."node") as "branches"
        from "evo_tree" group by "evo_tree"."root", "evo_tree"."root_form"
    ) as "evo_tree" on (
        "evo_tree"."root" = "evo_base"."base_pokemon"
        and "evo_tree"."root_form" = "evo_base"."base_form"
    )
    left join "mega_evolution_item" as "megevi" on (
        "megevi"."pokemon" = "form"."pokemon" and "megevi"."form" = "form"."name"
    )
    left join "item" as "megev_item" on "megev_item"."id" = "megevi"."item"
    left join "mega_evolution_move" as "megevm" on (
        "megevm"."pokemon" = "form"."pokemon" and "megevm"."form" = "form"."name"
    )
    left join "move" as "megev_move" on "megev_move"."id" = "megevm"."move"
    order by "form"."order"
)
select "pokemon"."name", json_object(
    'id', "pokemon"."id"
    ,'number', "pokemon"."number"
    ,'name', "pokemon"."name"
    ,'prev_name', "prev_pokemon"."name"
    ,'next_name', "next_pokemon"."name"
    ,'category', "pokemon"."category"
    ,'base_friendship', "pokemon"."base_friendship"
    ,'male_frequency', "pokemon"."male_frequency"
    ,'hatch_steps', "pokemon"."hatch_steps"
    ,'base_exp', "pokemon"."base_exp"
    ,'growth_rate', json_object(
        'id', "growth_rate"."pbs_name",
        'name', "growth_rate"."name"
    )
    ,'egg_groups', json("egg_groups"."all")
    ,'breedability', case
        when "pokemon"."id" = 'DITTO' then 'ditto'
        when exists (
            select 1 from json_each(json("egg_groups"."all")) as "egg_group"
            where json_extract("egg_group"."value", '$.id') = 'Undiscovered'
        ) then 'none'
        when "pokemon"."male_frequency" is null then 'ditto-only'
        else 'full'
    end
    ,'forms', json("forms"."all")
)
from "pokemon"
left join "pokemon" as "prev_pokemon" on "prev_pokemon"."number" = "pokemon"."number" - 1
left join "pokemon" as "next_pokemon" on "next_pokemon"."number" = "pokemon"."number" + 1
join "growth_rate" on "growth_rate"."name" = "pokemon"."growth_rate"
join (
    select
        "egg_group"."pokemon",
        json_group_array(json_object(
            'id', "egg_group"."id", 'name', "egg_group"."name"
        )) as "all"
    from "egg_group_o" as "egg_group"
    group by "egg_group"."pokemon"
) as "egg_groups" on "egg_groups"."pokemon" = "pokemon"."id"
join (
    select
        "form"."pokemon",
        json_group_array(json_object(
            'name', "form"."name"
            ,'sprite', case when "form"."sprite" is null then null else base64("form"."sprite") end
            ,'order', "form"."order"
            ,'pokedex_entry', "form"."pokedex_entry"
            ,'catch_rate', "form"."catch_rate"
            ,'height_m', "form"."height" / 100.0
            ,'height_feet', cast(round("form"."height" * 0.3937 / 12) as int)
            ,'height_inches', cast(round(mod("form"."height" * 0.3937, 12)) as int)
            ,'weight_kg', "form"."weight" / 10.0
            ,'weight_pounds', cast(round("form"."weight" * 2.2046) as int)
            ,'types', json("form"."types")
            ,'double_weaknesses', json(ifnull("form"."double_weaknesses", '[]'))
            ,'weaknesses', json(ifnull("form"."weaknesses", '[]'))
            ,'resistances', json(ifnull("form"."resistances", '[]'))
            ,'double_resistances', json(ifnull("form"."double_resistances", '[]'))
            ,'immunities', json(ifnull("form"."immunities", '[]'))
            ,'abilities', json("form"."abilities")
            ,'wild_held_items', json(ifnull("form"."wild_held_items", '[]'))
            ,'base_stats', json("form"."base_stats")
            ,'bst', "form"."bst"
            ,'ev_yields', json("form"."ev_yields")
            ,'evtot', "form"."evtot"
            ,'level_moves', json("form"."level_moves")
            ,'evolution_moves', json(ifnull("form"."evolution_moves", '[]'))
            ,'egg_moves', json(ifnull("form"."egg_moves", '[]'))
            ,'machine_moves', json(ifnull("form"."machine_moves", '[]'))
            ,'tutor_moves', json(ifnull("form"."tutor_moves", '[]'))
            ,'preevo_moves', json(ifnull("form"."preevo_moves", '[]'))
            ,'encounters', json(ifnull("form"."encounters", '[]'))
            ,'special_encounters', json(ifnull("form"."specialencs", '[]'))
            ,'evo_tree', json("form"."evo_tree")
            ,'mega_evolution', json("form"."mega_evolution")
            ,'babies', json("form"."babies")
        )) as "all"
    from "form_o" as "form"
    group by "form"."pokemon"
) as "forms" on "forms"."pokemon" = "pokemon"."id"