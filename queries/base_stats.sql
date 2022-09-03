select
	"form"."pokemon", "form"."name" as "form",
	"hp"."value" as "hp", "atk"."value" as "atk", "def"."value" as "def", "spd"."value" as "spd", "sa"."value" as "sa", "sd"."value" as "sd",
	"hp"."value" + "atk"."value" + "def"."value" + "spd"."value" + "sa"."value" + "sd"."value" as "total"
from "pokemon_form" as "form"
join "base_stat" as "hp" on "hp"."stat" = 'HP' and "hp"."pokemon" = "form"."pokemon" and "hp"."form" = "form"."name"
join "base_stat" as "atk" on "atk"."stat" = 'ATK' and "atk"."pokemon" = "form"."pokemon" and "atk"."form" = "form"."name"
join "base_stat" as "def" on "def"."stat" = 'DEF' and "def"."pokemon" = "form"."pokemon" and "def"."form" = "form"."name"
join "base_stat" as "spd" on "spd"."stat" = 'SPD' and "spd"."pokemon" = "form"."pokemon" and "spd"."form" = "form"."name"
join "base_stat" as "sa" on "sa"."stat" = 'SA' and "sa"."pokemon" = "form"."pokemon" and "sa"."form" = "form"."name"
join "base_stat" as "sd" on "sd"."stat" = 'SD' and "sd"."pokemon" = "form"."pokemon" and "sd"."form" = "form"."name"
where "form"."name" like "PULSE%"
order by "total" desc;
