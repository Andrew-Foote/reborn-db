select "subq"."defending_type1", "subq"."defending_type2", sum("subq"."multiplier") from (

select
	"attacking_type"."id" as "attacking_type",
	"defending_type1"."id" as "defending_type1", NULL as "defending_type2",
	ifnull("type_effect"."multiplier", 1) as "multiplier"
from "type" as "attacking_type" join "type" as "defending_type1"
left join "type_effect" on "type_effect"."attacking_type" = "attacking_type"."id" and "type_effect"."defending_type" = "defending_type1"."id"
union
select * from (
	select
		"attacking_type"."id" as "attacking_type",
		"defending_type1"."id" as "defending_type1", "defending_type2"."id" as "defending_type2",
		ifnull("effect1"."multiplier", 1) * ifnull("effect2"."multiplier", 1) as "multiplier"
	from "type" as "attacking_type"
	join "type" as "defending_type1" on not "defending_type1"."is_pseudo"
	left join "type_effect" as "effect1"
		on "effect1"."attacking_type" = "attacking_type"."id" and "effect1"."defending_type" = "defending_type1"."id"
	join "type" as "defending_type2" on not "defending_type2"."is_pseudo"
	left join "type_effect" as "effect2"
		on "effect2"."attacking_type" = "attacking_type"."id" and "effect2"."defending_type" = "defending_type2"."id"
	where not "attacking_type"."is_pseudo" and "defending_type1"."id" != "defending_type2"."id"
)

)  as "subq"
join "type" as "t1" on "t1"."id" = "subq"."defending_type1"
left join "type" as "t2" on "t2"."id" = "subq"."defending_type2"
where ("subq"."defending_type2" is null or "t1"."code" < "t2"."code")
group by "subq"."defending_type1", "subq"."defending_type2"
order by sum("subq"."multiplier")