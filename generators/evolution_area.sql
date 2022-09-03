-- we need all schemes where the variable kind is 'map''

-- each page is for a certain pokemon, a certain form, and a certain scheme
-- apart from the forms, we just need the scheme desc and the map

select 
	"from"."name" as "from_name", "evolution"."from_form" as "from_form"
	,"to"."name" as "to_name", "evolution"."to_form" as "to_form"
	,"scheme"."key" as "scheme_index", "scheme"."value" as "scheme"
from "pokemon_evolution_schemes" as "evolution"
join "pokemon" as "from" on "from"."id" = "evolution"."from"
join "pokemon" as "to" on "to"."id" = "evolution"."to"
join json_each("evolution"."schemes") as "scheme"
where "scheme" -> '$.requirements.map' is not null