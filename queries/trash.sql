with recursive "pokemon_evolution_ancestor" ("ancestor", "pokemon") as (
	select "id", "id" from "pokemon" where "evolves_from" is null
	union all
	select "pokemon"."id", "evolution"."id" from "pokemon_evolution_ancestor"
	join "pokemon" on
		"pokemon"."id" = "pokemon_evolution_ancestor"."ancestor"
		and "pokemon"."id" = "pokemon_evolution_ancestor"."pokemon"
	join "pokemon" as "evolution" on "evolution"."evolves_from" = "pokemon"."id"
	-- union all
	-- select "evolution"."id", "evolution"."id" from "pokemon_evolution_ancestor"
	-- join "pokemon" as "evolution" on
	-- 	"evolution"."evolves_from" = "pokemon_evolution_ancestor"."ancestor"
	-- 	and "evolution"."evolves_from" = "pokemon_evolution_ancestor"."pokemon"
)
select * from "pokemon_evolution_ancestor"
order by "pokemon"