with
	"pstat" as (
		select
			"pstat"."pokemon_id"
			,(
				select json_group_array("pstat"."base_stat")
				from (
					select "pstat"."base_stat" from "pokemon_stats" as "pstat"
					join "stats" on "stats"."id" = "pstat"."stat_id"
					order by "stats"."game_index" 
				) as "pstat"
			) as "base_stats",
			,(
				select json_group_array("pstat"."effort")
				from (
					select "pstat"."effort" from "pokemon_stats" as "pstat"
					join "stats" on "stats"."id" = "pstat"."stat_id"
					order by "stats"."game_index" 
				) as "pstat"
			)

			,json_group_array("pstat"."base_stat") as "base_stats"
			,json_group_array("pstat"."effort") as "evs"
		from (
			select "pstat"."pokemon_id", "pstat"."base_stat", "pstat"."effort"
			from "pokemon_stats" as "pstat" join "stats" on "stats"."id" = "pstat"."stat_id"
			order by "pstat"."game_index"
		)
		group by "pstat"."pokemon_id"
	)
	,"pa" as (
		select
			"pa"."pokemon_id"
			,"pa"."is_hidden"
			,"pa"."slot"
			,replace(upper("a"."identifier"), '-', '') as "ability_identifier"
		from "pokemon_abilities" as "pa" join "abilities" as "a" on "a"."id" = "pa"."ability_id"
	)
	,"pa_reg" as (
		select "pa"."pokemon_id", json_group_array("pa"."ability_identifier") as "abilities"
		from "pa" where "pa"."is_hidden" = 0 group by "pa"."pokemon_id" order by "pa"."slot"
	)
	,"pm" as (
		select
			"pm"."pokemon_id"
			,"pmm"."identifier" as "method"
			,"pm"."level"
			,"pm"."order"
			,replace(upper("m"."identifier"), '-', '') as "move_identifier"
		from "pokemon_moves" as "pm" join "moves" as "m" on "m"."id" = "pm"."move_id"
		join "pokemon_move_methods" as "pmm" on "pmm"."id" = "pm"."pokemon_move_method_id"
		join "version_groups" as "vg" on "vg"."id" = "pm"."version_group_id" and "vg"."identifier" = 'ultra-sun-ultra-moon'
	)
	,"egg_move" as (
		select "pm"."pokemon_id", json_group_array("pm"."move_identifier") as "moves"
		from "pm" where "pm"."method" = 'egg' group by "pm"."pokemon_id"
	)
	,"level_move" as (
		select "pm"."pokemon_id", json_group_array(json_array("pm"."level", "pm"."move_identifier")) as "moves"
		from "pm" where "pm"."method" = 'level-up' group by "pm"."pokemon_id"
		order by "pm"."level", "pm"."order"
	)
	,"pcm" as (
		select distinct "pm"."pokemon_id", "pm"."move_identifier" from "pm" where "pm"."method" in ('tutor', 'machine')
	)
	,"compat_move" as (
		select "pcm"."pokemon_id", json_group_array("pcm"."move_identifier") as "moves" from "pcm" group by "pcm"."pokemon_id"
	)
	,"peg" as (
		select "peg"."species_id", json_group_array(case
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
		end) as "egg_groups"
		from "pokemon_egg_groups" as "peg"
		join "egg_groups" as "eg" on "eg"."id" = "peg"."egg_group_id"
		where "eg"."identifier" != 'ditto'
		group by "peg"."species_id"
		union
		select "ps"."id", json_array() as "egg_groups"
		from "pokemon_species" as "ps"
		where not exists (
			select * from "pokemon_egg_groups" as "peg"
			join "egg_groups" as "eg" on "eg"."id" = "peg"."egg_group_id"
			where "peg"."species_id" = "ps"."id" and "eg"."identifier" != 'ditto'
		)
	)
	,"pwi" as (
		select
			"pwi"."pokemon_id"
			,"pwi"."rarity"
			,replace(upper("items"."identifier"), '-', '') as "item_identifier"
		from "pokemon_items" as "pwi" join "items" on "items"."id" = "pwi"."item_id"
		join "pokemon" as "p" on "p"."id" = "pwi"."pokemon_id"
		join "pokemon_species" as "ps" on "ps"."id" = "p"."species_id"
		join "versions" as "ver" on (
			"ver"."id" = "pwi"."version_id" and (
				("ps"."generation_id" <= 5 and "ver"."identifier" = 'black')
				or ("ps"."generation_id" = 6 and "ver"."identifier" = 'x')
				or "ver"."identifier" = 'sun'
			)
		)
	)
	,"shadow_move" as (
		select "pm"."pokemon_id", json_group_array("pm"."move_identifier") as "moves"
		from "pm" where "pm"."method" = 'xd-shadow' group by "pm"."pokemon_id"
	)
	,"p" as (
		select
			"p"."species_id"
			,replace(upper("ps"."identifier"), '-', '') as "species_identifier"
			,ifnull("pf"."form_identifier", '') as "form_name"
			,"pdn"."pokedex_number"
			,"pf"."id" as "form_id"
			,json_patch(
				json_object(
					'name', "psn"."name"
					,'dexnum', "pdn"."pokedex_number"
					,'Type1', upper("t1"."identifier")
					,'BaseStats', json("pstat"."base_stats")
					,'EVs', json("pstat"."evs")
					,'Abilities', json("pa_reg"."abilities")
					,'GrowthRate', case
						when "gr"."identifier" = 'slow' then 'Slow'
						when "gr"."identifier" = 'medium' then 'MediumFast'
						when "gr"."identifier" = 'fast' then 'Fast'
						when "gr"."identifier" = 'medium-slow' then 'MediumSlow'
						when "gr"."identifier" = 'slow-then-very-fast' then 'Erratic'
						when "gr"."identifier" = 'fast-then-very-slow' then 'Fluctuating'
					end
					,'GenderRatio', case 
						when "ps"."gender_rate" = -1 then 'Genderless'
						when "ps"."gender_rate" = 0 then 'MaleZero'
						when "ps"."gender_rate" = 1 then 'FemEighth'
						when "ps"."gender_rate" = 2 then 'FemQuarter'
						when "ps"."gender_rate" = 4 then 'FemHalf'
						when "ps"."gender_rate" = 6 then 'MaleQuarter'
						when "ps"."gender_rate" = 7 then 'MaleEighth'
						when "ps"."gender_rate" = 8 then 'FemZero'
					end
					,'BaseEXP', "p"."base_experience"
					,'CatchRate', "ps"."capture_rate"
					,'Happiness', "ps"."base_happiness"
					,'EggSteps', ("ps"."hatch_counter" + 1) * 255
					,'compatiblemoves', case when "compat_move"."moves" is null then json_array() else json("compat_move"."moves") end
					,'moveexceptions', json_array()
					,'Color', "pcolorn"."name"
					,'EggGroups', json("peg"."egg_groups")
					,'Height', "p"."height"
					,'Weight', "p"."weight"
					,'kind', replace("psn"."genus", ' Pokémon', '')
				)
			,json_patch(
				case
					when "pt2"."type_identifier" is null then json_object()
					else json_object('Type2', upper("pt2"."type_identifier"))
				end
			,json_patch(
				case
					when "pa_hid"."ability_identifier" is null then json_object()
					else json_object('HiddenAbilities', "pa_hid"."ability_identifier")
				end
			,json_patch(
				case
					when "egg_move"."moves" is null then json_object()
					else json_object('EggMoves', json("egg_move"."moves"))
				end
			,json_patch(
				case
					when "level_move"."moves" is null then json_object()
					else json_object('Moveset', json("level_move"."moves"))
				end
			,json_patch(
				case
					when "phabitat"."identifier" is null then json_object()
					else json_object('Habitat', case
						when "phabitat"."identifier" = 'cave' then 'Cave'
						when "phabitat"."identifier" = 'forest' then 'Forest'
						when "phabitat"."identifier" = 'grassland' then 'Grassland'
						when "phabitat"."identifier" = 'mountain' then 'Mountain'
						when "phabitat"."identifier" = 'rare' then 'Rare'
						when "phabitat"."identifier" = 'rough-terrain' then 'RoughTerrain'
						when "phabitat"."identifier" = 'sea' then 'Sea'
						when "phabitat"."identifier" = 'urban' then 'Urban'
						when "phabitat"."identifier" = 'waters-edge' then 'WatersEdge'
					end)
				end
			,json_patch(
				case
					when "wi_common"."item_identifier" is null then json_object()
					else json_object('WildItemCommon', "wi_common"."item_identifier")
				end
			,json_patch(
				case
					when "wi_uncommon"."item_identifier" is null then json_object()
					else json_object('WildItemUncommon', "wi_uncommon"."item_identifier")
				end
			,json_patch(
				case
					when "wi_rare"."item_identifier" is null then json_object()
					else json_object('WildItemRare', "wi_rare"."item_identifier")
				end
			,json_patch(
				case
					when "shadow_move"."moves" is null then json_object()
					else json_object('shadowmoves', json("shadow_move"."moves"))
				end
			,json_object()
			)))))))))) as "data"
		from "pokemon" as "p"
		join "pokemon_forms" as "pf" on "pf"."pokemon_id" = "p"."id"
		left join (
			select "pfn"."pokemon_form_id", "pfn"."form_name" from "pokemon_form_names" as "pfn"
			join "languages" as "pfnl" on "pfnl"."id" = "pfn"."local_language_id" and "pfnl"."identifier" = 'en'
		) as "pfn" on "pfn"."pokemon_form_id" = "pf"."id"
		join "pokemon_species" as "ps" on "ps"."id" = "p"."species_id"
		join "pokemon_species_names" as "psn" on "psn"."pokemon_species_id" = "ps"."id"
		join "languages" as "psnl" on "psnl"."id" = "psn"."local_language_id" and "psnl"."identifier" = 'en'
		join "pokemon_dex_numbers" as "pdn" on "pdn"."species_id" = "ps"."id"
		join "pokedexes" as "pd" on "pd"."id" = "pdn"."pokedex_id" and "pd"."identifier" = 'national' and "pdn"."pokedex_number" <= 807
		join "pokemon_types" as "pt1" on "pt1"."pokemon_id" = "p"."id" and "pt1"."slot" = 1
		join "types" as "t1" on "t1"."id" = "pt1"."type_id"
		left join (
			select "pt2"."pokemon_id", "pt2"."slot", "t2"."identifier" as "type_identifier" from "pokemon_types" as "pt2"
			join "types" as "t2" on "t2"."id" = "pt2"."type_id"
		) as "pt2" on "pt2"."pokemon_id" = "p"."id" and "pt2"."slot" = 2
		join "pstat" on "pstat"."pokemon_id" = "p"."id"
		join "pa_reg" on "pa_reg"."pokemon_id" = "p"."id"
		left join "pa" as "pa_hid" on "pa_hid"."pokemon_id" = "p"."id" and "pa_hid"."is_hidden" = 1
		join "growth_rates" as "gr" on "gr"."id" = "ps"."growth_rate_id"
		left join "egg_move" on "egg_move"."pokemon_id" = "p"."id"
		left join "level_move" on "level_move"."pokemon_id" = "p"."id"
		left join "compat_move" on "compat_move"."pokemon_id" = "p"."id"
		join "pokemon_colors" as "pcolor" on "pcolor"."id" = "ps"."color_id"
		join "pokemon_color_names" as "pcolorn" on "pcolorn"."pokemon_color_id" = "pcolor"."id"
		join "languages" as "pcolornl" on "pcolornl"."id" = "pcolorn"."local_language_id" and "pcolornl"."identifier" = 'en'
		left join "pokemon_habitats" as "phabitat" on "phabitat"."id" = "ps"."habitat_id"
		join "peg" on "peg"."species_id" = "ps"."id"
		left join "pwi" as "wi_common" on "wi_common"."pokemon_id" = "p"."id" and "wi_common"."rarity" in (50, 100)
		left join "pwi" as "wi_uncommon" on "wi_uncommon"."pokemon_id" = "p"."id" and "wi_uncommon"."rarity" in (5, 100)
		left join "pwi" as "wi_rare" on "wi_rare"."pokemon_id" = "p"."id" and "wi_rare"."rarity" in (1, 100)
		left join "shadow_move" on "shadow_move"."pokemon_id" = "p"."id"
	)
	,"ps" as (
		select
			"p"."species_identifier" as "identifier"
			,"p"."pokedex_number"
			,json_group_object("p"."form_name", json("p"."data")) as "data"
		from "p" group by "p"."species_id" order by "p"."pokedex_number", "p"."form_id"
	)
select json_group_object("ps"."identifier", json("ps"."data"))
from "ps"

