with recursive "map_tree" ("level", "id", "order", "node") as (
	select 0, "map"."id", "map"."order", json_object(
		'id', "map"."id", 'name', "map"."name", 'desc', "map"."desc"
	)
	from "map" where "parent_id" is null
	union all
	select "map_tree"."level" + 1, "map"."id", "map"."order", json_object(
		'id', "map"."id", 'name', "map"."name", 'desc', "map"."desc"
	)
	from "map" join "map_tree" on "map"."parent_id" = "map_tree"."id"
	order by "map_tree"."level" + 1 desc, "map"."order"
)
select df2tree("map_tree"."level", "map_tree"."node") from "map_tree";