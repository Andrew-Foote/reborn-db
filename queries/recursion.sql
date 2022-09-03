-- gives all pre-evo / post-evo pairs

with recursive "parent" ("number", "id", "parent_id") as (
	select "number", "id", "evolves_from"
	from "pokemon" where "evolves_from" is not null
	union
	select "pokemon"."number", "pokemon"."id", "pokemon"."evolves_from"
	from "parent"
	join "pokemon" on "pokemon"."id" = "parent"."parent_id"
	where "pokemon"."evolves_from" is not null 
	order by "pokemon"."number"
)
select * from "parent"
order by "number"


-- gives the evolutionary ancestors of each pokemon (but i think it's inefficient since it goes from the final stage backwards)

with recursive "pokemon_evolution_ancestor" (
	"number", "pokemon", "ancestor", "level"
) as (
	select "number", "id", "id", 0 from "pokemon"
	union all
	select
		"pokemon"."number"
		,"pokemon"."id"
		,"evolves_from"."id"
		,"pokemon_evolution_ancestor"."level" + 1
	from "pokemon_evolution_ancestor"
	join "pokemon" on "pokemon"."id" = "pokemon_evolution_ancestor"."pokemon"
	join "pokemon" as "ancestor" on "ancestor"."id" = "pokemon_evolution_ancestor"."ancestor"
	join "pokemon" as "evolves_from" on "evolves_from"."id" = "ancestor"."evolves_from"
	order by "pokemon"."number"
)
select *
from "pokemon_evolution_ancestor"

--- gets the descendants, a bit more efficient

with recursive "pokemon_evolution_descendant" (
	"number", "pokemon", "descendant", "stage"
) as (
	select "number", "id", "id", 0 from "pokemon" where "evolves_from" is null
	union all
	select
		"pokemon"."number"
		,"pokemon"."id"
		,"evolves_to"."id"
		,"pokemon_evolution_descendant"."stage" + 1
	from "pokemon_evolution_descendant"
	join "pokemon" on "pokemon"."id" = "pokemon_evolution_descendant"."pokemon"
	join "pokemon" as "descendant" on "descendant"."id" = "pokemon_evolution_descendant"."descendant"
	join "pokemon" as "evolves_to" on "evolves_to"."evolves_from" = "descendant"."id"
	order by "pokemon"."number"
)
select *
from "pokemon_evolution_descendant"


---

with recursive "evolution_tree" (
	"node"
) as (
	select json_object('pokemon', "pokemon"."id", 'evolutions', null) from "pokemon"
	left join "pokemon" as "evolves_to" on "evolves_to"."evolves_from" = "pokemon"."id"
	where "evolves_to"."id" is null
	union all
	select json_object(
		'pokemon', "pokemon"."evolves_from",
		'evolutions', json_group_array(
			"evolution_tree"."node"
		)
	)
	from "evolution_tree"
	join "pokemon" on "pokemon"."id" = json_extract("evolution_tree"."node", '$.pokemon')
	group by "pokemon"."evolves_from"
)
select * from "evolution_tree";

-- output we want
-- {'Wurmple': {'Silcoon': {'Beautifly': null}, 'Cascoon': {'Dustox': null}}}

-- Wurmple, 

-- i think this would work, but sqlite (and all other sql dialects i know of)
-- don't support aggregates in recursive ctes