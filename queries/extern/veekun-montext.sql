with
	"en" as ( select "id" from "languages" where "identifier" = 'en' )
select json_group_object(
	replace(upper("ps"."identifier"), '-', '')
	,(
		with
			"peg" as (
				select "eg"."id", case
					when "eg"."identifier" = 'monster' then 'Monster'
					when "eg"."identifier" = 'water1' then 'Water1'
					when "eg"."identifier" = 'bug' then 'Bug'
					when "eg"."identifier" = 'flying' then 'Flying'
					when "eg"."identifier" = 'ground' then 'Field'
					when "eg"."identifier" = 'fairy' then 'Fairy'
					when "eg"."identifier" = 'plant' then 'Grass'
					when "eg"."identifier" = 'humanshape' then 'HumanLike'
					when "eg"."identifier" = 'water3' then 'Water3'
					when "eg"."identifier" = 'mineral' then 'Mineral'
					when "eg"."identifier" = 'indeterminate' then 'Amorphous'
					when "eg"."identifier" = 'water2' then 'Water2'
					when "eg"."identifier" = 'dragon' then 'Dragon'
					when "eg"."identifier" = 'no-eggs' then 'Undiscovered'
				end as "name"
				from "pokemon_egg_groups" as "peg"
				join "egg_groups" as "eg" on "eg"."id" = "peg"."egg_group_id"
				where "peg"."species_id" = "ps"."id" and "eg"."identifier" != 'ditto'
			)
		select json_group_object(
			"p"."form_identifier"
			,(
				with
					"pstat" as (
						select
							case
								when "stat"."identifier" = 'hp' then 0
								when "stat"."identifier" = 'attack' then 1
								when "stat"."identifier" = 'defense' then 2
								when "stat"."identifier" = 'special-attack' then 3
								when "stat"."identifier" = 'special-defense' then 4
								when "stat"."identifier" = 'speed' then 5
							end as "index"
							,"pstat"."base_stat"
							,"pstat"."effort"
						from "pokemon_stats" as "pstat"
						join "stats" as "stat" on "stat"."id" = "pstat"."stat_id"
						where "pstat"."pokemon_id" = "p"."id"
					)
					,"pa" as (
						select
							"pa"."is_hidden","pa"."slot"
							,replace(upper("a"."identifier"), '-', '') as "ability"
						from "pokemon_abilities" as "pa"
						join "abilities" as "a" on "a"."id" = "pa"."ability_id"
						where "pa"."pokemon_id" = "p"."id"
					)
					,"pm" as (
						select
							"pmm"."identifier" as "method"
							,"pm"."level"
							,"pm"."order"
							,replace(upper("m"."identifier"), '-', '') as "move"
							,"vg"."identifier" as "version_group"
						from "pokemon_moves" as "pm"
						join "moves" as "m" on "m"."id" = "pm"."move_id"
						join "pokemon_move_methods" as "pmm"
							on "pmm"."id" = "pm"."pokemon_move_method_id"
						join "version_groups" as "vg" on "vg"."id" = "pm"."version_group_id"
						where "pm"."pokemon_id" = "p"."id"
					),
					"pi" as (
						select
							"pi"."rarity",
							replace(upper("i"."identifier"), '-', '') as "item"
						from "pokemon_items" as "pi"
						join "versions" as "v" on "v"."id" = "pi"."version_id"
						join "items" as "i" on "i"."id" = "pi"."item_id"
						where "pi"."pokemon_id" = "p"."id"
						and "v"."identifier" = 'ultra-sun' -- no difference between using ultra-sun vs ultra-moon here, i checked
					)
				select json_group_object("attr"."name", json("attr"."value"))
				from (
					select 0 as "index", 'name' as "name", json_quote("ps"."name") as "value"
					union
					select
						1 as "index", 'dexnum' as "name", json_quote("ps"."pokedex_number") as "value"
					union
					select
						2 as "index", 'Type1' as "name"
						,json_quote(upper("t"."identifier")) as "value"
					from "pokemon_types" as "pt"
					join "types" as "t" on "t"."id" = "pt"."type_id"
					where "pt"."pokemon_id" = "p"."id" and "pt"."slot" = 1
					union
					select
						3 as "index", 'Type2' as "name"
						,json_quote(upper("t"."identifier")) as "value"
					from "pokemon_types" as "pt"
					join "types" as "t" on "t"."id" = "pt"."type_id"
					where "pt"."pokemon_id" = "p"."id" and "pt"."slot" = 2
					union
					select
						4 as "index", 'BaseStats' as "name"
						,json_group_array("pstat"."base_stat") as "value"
					from (
						select "pstat"."base_stat" from "pstat" order by "pstat"."index"
					) as "pstat"
					union
					select
						5 as "index", 'EVs' as "name", json_group_array("pstat"."effort") as "value"
					from (
						select "pstat"."effort" from "pstat" order by "pstat"."index"
					) as "pstat"
					union
					select
						6 as "index", 'Abilities' as "name"
						,json_group_array("pa"."ability") as "value"
					from (
						select "pa"."ability" from "pa" where "pa"."is_hidden" = 0
						order by "pa"."slot"
					) as "pa"
					union
					select
						7 as "index", 'HiddenAbilities' as "name"
						,json_quote("pa"."ability") as "value"
					from "pa" where "pa"."is_hidden" = 1
					union
					select
						8 as "index", 'GrowthRate' as "name"
						,json_quote("ps"."growth_rate") as "value"
					union
					select
						9 as "index", 'GenderRatio' as "name",
						json_quote("ps"."gender_rate") as "value"
					union
					select
						10 as "index", 'BaseEXP' as "name"
						,json_quote("p"."base_experience") as "value"
					union
					select
						11 as "index", 'CatchRate' as "name"
						,json_quote("ps"."capture_rate") as "value"
					union
					select
						12 as "index", 'Happiness' as "name"
						,json_quote("ps"."base_happiness") as "value"
					union
					select
						13 as "index", 'EggSteps' as "name"
						,json_quote("ps"."egg_steps") as "value"
					union
					select
						14 as "index", 'EggMoves' as "name"
						,json_group_array("pm"."move") as "value"
					from (
						select "pm"."move" from "pm" where
							"pm"."method" = 'egg'
							and "pm"."version_group" = 'ultra-sun-ultra-moon'
						order by "pm"."move"
					) as "pm"
					group by '' -- don't create empty list
					union
					select 15 as "index", 'Moveset' as "name", json_group_array(
						json_array("pm"."level", "pm"."move")
					) as "value"
					from (
						select "pm"."level", "pm"."move" from "pm" where
							"pm"."method" = 'level-up'
							and "pm"."version_group" = 'ultra-sun-ultra-moon'
						order by "pm"."level", "pm"."order"
					) as "pm"
					union
					select
						16 as "index", 'compatiblemoves' as "name"
						,json_group_array("pm"."move") as "value"
					from (
						select "pm"."move" from "pm" -- where "pm"."method" in ('tutor', 'machine')
						order by "pm"."move"
					) as "pm"
					union
					select 18 as "index", 'Color' as "name", json_quote("ps"."color") as "value"
					union
					select 19 as "index", 'Habitat' as "name", json_quote("ps"."habitat") as "value"
					where "ps"."habitat" is not null
					union
					select
						20 as "index", 'EggGroups' as "name",
						json_group_array("peg"."name")
					from ( select "peg"."name" from "peg" order by "peg"."id" ) as "peg"
					union
					select 21 as "index", 'Height' as "name", json_quote("p"."height") as "value"
					union
					select 22 as "index", 'Weight' as "name", json_quote("p"."weight") as "value"
					union
					select 23 as "index", 'kind' as "name", json_quote("ps"."species") as "value"
					union
					select
						24 as "index", 'WildItemCommon' as "name"
						,json_quote("pi"."item") as "value"
					from "pi" where "pi"."rarity" in (100, 50)
					union
					select
						24 as "index", 'WildItemUncommon' as "name"
						,json_quote("pi"."item") as "value"
					from "pi" where "pi"."rarity" in (100, 5)
					union
					select
						24 as "index", 'WildItemRare' as "name"
						,json_quote("pi"."item") as "value"
					from "pi" where "pi"."rarity" in (100, 1)
					order by "index"
				) as "attr"
			)
		)
		from (
			select
				"p"."id"
				,ifnull("pf"."form_identifier", '') as "form_identifier"
				,"p"."base_experience"
				,"p"."height"
				,"p"."weight"
			from "pokemon" as "p"
			join "pokemon_forms" as "pf" on "pf"."pokemon_id" = "p"."id"
			where "p"."species_id" = "ps"."id"
			order by "pf"."form_order"
		) as "p"
	)
) as "data"
from (
	select
		"ps"."id"
		,"ps"."identifier"
		,"pdn"."pokedex_number"
		,"psn"."name"
		,case
			when "gr"."identifier" = 'slow' then 'Slow'
			when "gr"."identifier" = 'medium' then 'MediumFast'
			when "gr"."identifier" = 'fast' then 'Fast'
			when "gr"."identifier" = 'medium-slow' then 'MediumSlow'
			when "gr"."identifier" = 'slow-then-very-fast' then 'Erratic'
			when "gr"."identifier" = 'fast-then-very-slow' then 'Fluctuating'
		end as "growth_rate"
		,case 
			when "ps"."gender_rate" = -1 then 'Genderless'
			when "ps"."gender_rate" = 0 then 'FemZero'
			when "ps"."gender_rate" = 1 then 'FemEighth'
			when "ps"."gender_rate" = 2 then 'FemQuarter'
			when "ps"."gender_rate" = 4 then 'FemHalf'
			when "ps"."gender_rate" = 6 then 'MaleQuarter'
			when "ps"."gender_rate" = 7 then 'MaleEighth'
			when "ps"."gender_rate" = 8 then 'MaleZero'
		end as "gender_rate"
		,"ps"."capture_rate"
		,"ps"."base_happiness"
		,("ps"."hatch_counter" + 1) * 255 as "egg_steps"
		,"pcn"."name" as "color"
		,case
			when "ph"."identifier" = 'cave' then 'Cave'
			when "ph"."identifier" = 'forest' then 'Forest'
			when "ph"."identifier" = 'grassland' then 'Grassland'
			when "ph"."identifier" = 'mountain' then 'Mountain'
			when "ph"."identifier" = 'rare' then 'Rare'
			when "ph"."identifier" = 'rough-terrain' then 'RoughTerrain'
			when "ph"."identifier" = 'sea' then 'Sea'
			when "ph"."identifier" = 'urban' then 'Urban'
			when "ph"."identifier" = 'waters-edge' then 'WatersEdge'
		end as "habitat"
		,replace("psn"."genus", ' Pokémon', '') as "species"
	from "pokemon_species" as "ps"
	join "pokemon_dex_numbers" as "pdn" on "pdn"."species_id" = "ps"."id"
	join "pokedexes" as "pd" on (
		"pd"."id" = "pdn"."pokedex_id"
		and "pd"."identifier" = 'national'
		and "pdn"."pokedex_number" <= 807
	)
	join "pokemon_species_names" as "psn" on (
		"psn"."pokemon_species_id" = "ps"."id" and "psn"."local_language_id" = (select "id" from "en")
	)
	join "growth_rates" as "gr" on "gr"."id" = "ps"."growth_rate_id"
	join "pokemon_colors" as "pc" on "pc"."id" = "ps"."color_id"
	join "pokemon_color_names" as "pcn" on (
		"pcn"."pokemon_color_id" = "pc"."id" and "pcn"."local_language_id" = (select "id" from "en")
	)
	left join "pokemon_habitats" as "ph" on "ph"."id" = "ps"."habitat_id"
	order by "pdn"."pokedex_number"
) as "ps"