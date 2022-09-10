with "sprite0" ("pokemon", "form", "type", "shiny", "gender", "sprite", "shinykey") as (
	select "sprite".*, case
		when "sprite"."shiny" = 0 then 'nonshiny'
		when "sprite"."shiny" = 1 then 'shiny'
	end as "shinykey"
	from "pokemon_sprite" as "sprite"
)
,"sprite1" ("pokemon", "form", "type", "shiny", "gender", "sprite", "shinykey", "key", "genderdiff") as (
	select "sprite0".*, case
		when "sprite0"."gender" is null then "sprite0"."shinykey"
		else "sprite0"."shinykey" || '_' || lower("sprite0"."gender")
	end as "key",
	("sprite0"."gender" is not null) as "genderdiff"
	from "sprite0"
)
select
	"pokemon"."name" as "pokemon", "form"."name" as "form"
	,exists (
		select 1 from "pokemon_sprite" as "sprite"
		where
			"sprite"."pokemon" = "form"."pokemon" and "sprite"."form" = "form"."name"
			and "sprite"."gender" is not null
	) as "genderdiff"
	,(
		select json_patch(
			json_group_object("sprite1"."key", base64("sprite1"."sprite")),
			json_object('genderdiff', "sprite1"."genderdiff")
		) from "sprite1"
		where "sprite1"."pokemon" = "form"."pokemon" and "sprite1"."form" = "form"."name" and "sprite1"."type" = 'front'
	) as "front_sprite"
	,(
		select json_patch(
			json_group_object("sprite1"."key", base64("sprite1"."sprite")),
			json_object('genderdiff', "sprite1"."genderdiff")
		) from "sprite1"
		where "sprite1"."pokemon" = "form"."pokemon" and "sprite1"."form" = "form"."name" and "sprite1"."type" = 'back'
	) as "back_sprite"
	,(
		select json_patch(
			json_group_object("sprite1"."key", base64("sprite1"."sprite")),
			json_object('genderdiff', "sprite1"."genderdiff", 'exists', ("sprite1"."sprite" is not null))
		) from "sprite1"
		where "sprite1"."pokemon" = "form"."pokemon" and "sprite1"."form" = "form"."name" and "sprite1"."type" = 'egg'
	) as "egg_sprite"
	,(
		select json_patch(
			json_group_object("sprite1"."key", base64("sprite1"."sprite")),
			json_object('genderdiff', "sprite1"."genderdiff")
		) from "sprite1"
		where "sprite1"."pokemon" = "form"."pokemon" and "sprite1"."form" = "form"."name" and "sprite1"."type" = 'icon1'
	) as "icon"
	,(
		select json_patch(
			json_group_object("sprite1"."key", base64("sprite1"."sprite")),
			json_object('genderdiff', "sprite1"."genderdiff", 'exists', ("sprite1"."sprite" is not null))
		) from "sprite1"
		where "sprite1"."pokemon" = "form"."pokemon" and "sprite1"."form" = "form"."name" and "sprite1"."type" = 'egg-icon1'
	) as "egg_icon"
from "pokemon_form" as "form"
join "pokemon" on "pokemon"."id" = "form"."pokemon"