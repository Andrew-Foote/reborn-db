select
	"trainer"."id"
	,ifnull("trainer_pokemon"."nickname", "pokemon"."name") as "nickname"
	,"trainer_pokemon"."shiny", "trainer_pokemon"."level", "trainer_pokemon"."gender"
	,"nature"."name" as "nature","item"."name" as "item", "trainer_pokemon"."friendship"
	,"sprite"."sprite"
	,base64("sprite"."sprite") as "sprite"
	,(
		select json_group_array("ability"."name")
		from (
			select "ability"."name"
			from "trainer_pokemon_ability"
			join "pokemon_ability" on (
				"pokemon_ability"."pokemon" = "trainer_pokemon"."pokemon"
				and "pokemon_ability"."form" = "trainer_pokemon"."form"
				and "pokemon_ability"."index" = "trainer_pokemon_ability"."ability"
			)
			join "ability" on "ability"."id" = "pokemon_ability"."ability"
			where
				"trainer_pokemon_ability"."trainer_type" = "trainer_pokemon"."trainer_type"
				and "trainer_pokemon_ability"."trainer_name" = "trainer_pokemon"."trainer_name"
				and "trainer_pokemon_ability"."party_id" = "trainer_pokemon"."party_id"
				and "trainer_pokemon_ability"."pokemon_index" = "trainer_pokemon"."index"
			order by "pokemon_ability"."index"
		) as "ability"
	) as "abilities"
	,(
		select json_group_array(json_object('id', "move"."id", 'name', "move"."name", 'pp', "move"."pp"))
		from (
			select "move"."name", "move"."id", case
			  when "trainer_pokemon"."level" >= 100 and "trainer"."skill" >= 100
				then ("move"."pp" * 8) / 5 else "move"."pp"
			end as "pp"
			from "trainer_pokemon_move" as "pokemon_move"
			join "move" on "move"."id" = "pokemon_move"."move"
			where
				"pokemon_move"."trainer_type" = "trainer_pokemon"."trainer_type"
				and "pokemon_move"."trainer_name" = "trainer_pokemon"."trainer_name"
				and "pokemon_move"."party_id" = "trainer_pokemon"."party_id"
				and "pokemon_move"."pokemon_index" = "trainer_pokemon"."index"
			order by "pokemon_move"."move_index"
		) as "move"
	) as "moves"
	,(
		select json_group_array(json_object('stat', "ev"."stat", 'value', "ev"."value"))
		from (
			select "stat"."name" as "stat", "ev"."value"
			from "trainer_pokemon_ev" as "ev"
			join "stat" on "stat"."id" = "ev"."stat"
			where
				"ev"."trainer_type" = "trainer_pokemon"."trainer_type"
				and "ev"."trainer_name" = "trainer_pokemon"."trainer_name"
				and "ev"."party_id" = "trainer_pokemon"."party_id"
				and "ev"."pokemon_index" = "trainer_pokemon"."index"
			order by "stat"."order"
		) as "ev"
	) as "evs"
	,(
		select json_group_array(json_object('stat', "iv"."stat", 'value', "iv"."value"))
		from (
			select "stat"."name" as "stat", "iv"."value"
			from "trainer_pokemon_iv" as "iv"
			join "stat" on "stat"."id" = "iv"."stat"
			where
				"iv"."trainer_type" = "trainer_pokemon"."trainer_type"
				and "iv"."trainer_name" = "trainer_pokemon"."trainer_name"
				and "iv"."party_id" = "trainer_pokemon"."party_id"
				and "iv"."pokemon_index" = "trainer_pokemon"."index"
			order by "stat"."order"
		) as "iv"
	) as "ivs"
	,(
		select json_group_array(json_object('stat', "stat"."stat", 'value', "stat"."value"))
		from (
			select "stat"."name" as "stat", "pokemon_stat"."value"
			from "trainer_pokemon_stat" as "pokemon_stat"
			join "stat" on "stat"."id" = "pokemon_stat"."stat"
			where
				"pokemon_stat"."trainer_type" = "trainer_pokemon"."trainer_type"
				and "pokemon_stat"."trainer_name" = "trainer_pokemon"."trainer_name"
				and "pokemon_stat"."party_id" = "trainer_pokemon"."party_id"
				and "pokemon_stat"."pokemon_index" = "trainer_pokemon"."index"
			order by "stat"."order"
		) as "stat"
	) as "stats"
from "trainer_pokemon"
join "trainer_v" as "trainer" on (
	"trainer"."type_id" = "trainer_pokemon"."trainer_type"
	and "trainer"."trainer_name" = "trainer_pokemon"."trainer_name"
	and "trainer"."party_id" = "trainer_pokemon"."party_id"
)
join "pokemon" on "pokemon"."id" = "trainer_pokemon"."pokemon"
join "nature" on "nature"."id" = "trainer_pokemon"."nature"
left join "pokemon_sprite" as "sprite" on (
	"sprite"."pokemon" = "trainer_pokemon"."pokemon" and "sprite"."form" = "trainer_pokemon"."form"
	and "sprite"."type" = 'front' and "sprite"."shiny" = "trainer_pokemon"."shiny"
	and ((
		"trainer_pokemon"."gender" is null
		and ("sprite"."gender" is null or "sprite"."gender" = 'Male')
	) or (
		"sprite"."gender" is null or "trainer_pokemon"."gender" = "sprite"."gender"
	))
)
left join "item" on "item"."id" = "trainer_pokemon"."item"
where 
	"trainer_pokemon"."pokemon" = 'VENUSAUR' and "trainer_pokemon"."form" = ''