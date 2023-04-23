-- Calculates movesets for wild Pokémon encountered via random encounters. These Pokémon always
-- know the last four moves they learnt via levelling up.
-- 
-- For event encounters, it would be a bit more complicated: we have to take into account the
-- overrides in PokemonEncounterModifiers.rb.

with
	"level_move_o" as (
		select
			"pokemon", "form", "level"
			,row_number() over (partition by "pokemon", "form" order by "level", "order") as "order"
			,"move"
		from "level_move"
	)
	,"per" as (
		select
			"per"."map", "per"."method", "per"."pokemon", "per"."form", "per"."level", max("lm"."order") as "last_move_order"
			from "pokemon_encounter_rate" as "per"
			join "level_move_o" as "lm" on "lm"."pokemon" = "per"."pokemon" and "per"."form" = "per"."form" and "lm"."level" <= "per"."level"
			group by "per"."map", "per"."method", "per"."pokemon", "per"."form", "per"."level"
	)
select 
	"per"."map", "per"."method", "per"."pokemon", "per"."form", "per"."level"
	 ,(
	 	select "lm"."move" from "level_move_o" "lm"
	 	where "lm"."pokemon" = "per"."pokemon" and "lm"."form" = "per"."form" and "lm"."order" = "per"."last_move_order" - 3
	 ) as "move1" 
	 ,(
	 	select "lm"."move" from "level_move_o" "lm"
	 	where "lm"."pokemon" = "per"."pokemon" and "lm"."form" = "per"."form" and "lm"."order" = "per"."last_move_order" - 2
	 ) as "move2"
	 ,(
	 	select "lm"."move" from "level_move_o" "lm"
	 	where "lm"."pokemon" = "per"."pokemon" and "lm"."form" = "per"."form" and "lm"."order" = "per"."last_move_order" - 1
	 ) as "move3"
	 ,(
	 	select "lm"."move" from "level_move_o" "lm"
	 	where "lm"."pokemon" = "per"."pokemon" and "lm"."form" = "per"."form" and "lm"."order" = "per"."last_move_order"
	 ) as "move4"
	 from "per"
;