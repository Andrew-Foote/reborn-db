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
	join "pokemon" on "pokemon"."id" = "evolution_tree"."node" ->> '$.pokemon'
	group by "pokemon"."evolves_from"
)
select * from "evolution_tree";

-- output we want
-- {'Wurmple': {'Silcoon': {'Beautifly': null}, 'Cascoon': {'Dustox': null}}}

-- Wurmple, 