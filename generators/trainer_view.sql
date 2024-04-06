select json_object(
  'name', "trainer"."id"
  ,'front_sprite', base64("trainer"."battle_sprite")
  ,'back_sprite', base64("trainer"."battle_back_sprite")
  ,'base_prize', "trainer"."base_prize"
  ,'skill', "trainer"."skill"
  ,'battles', (
	select json_group_array(json_object(
		'area', json_object('id', "battle"."map_id", 'name', "battle"."map_name"),
		'x', "battle"."x", 'y', "battle"."y",
		'end_speech', "battle"."end_speech",
		'pre_battle_speech', "battle"."pre_battle_speech",
		'post_battle_speech', "battle"."post_battle_speech",
		'level_100', "battle"."level_100",
		'is_double', "battle"."is_double",
		'partner_index', "battle"."partner_index",
		'partner', "battle"."partner",
		'can_lose', "battle"."can_lose"
	))
	from (
		select 
			"map"."id" as "map_id", "map"."name" as "map_name"
			,"map_event"."x", "map_event"."y"
			,"tbc"."end_speech", "tbc"."pre_battle_speech", "tbc"."post_battle_speech"
			,"tbc"."level_100"
			,"tbc"."is_double", "tbc"."partner_index", "partner"."id" as "partner"
			,"tbc"."can_lose"
		from "trainer_battle_command" as "tbc"
		left join "event_page_command" as "epc" on "epc"."command" = "tbc"."command"
		left join "map_event" on (
			"map_event"."map_id" = "epc"."map_id"
			and "map_event"."event_id" = "epc"."event_id"
		)
		left join "map" on "map"."id" = "epc"."map_id"
		left join "trainer_v" as "partner" on (
			"partner"."type" = "tbc"."partner_type" 
			and "partner"."name" = "tbc"."partner_name"
			and "partner"."party" = "tbc"."partner_party"
		)
		where "tbc"."trainer_type" = "trainer"."type"
		and "tbc"."trainer_name" = "trainer"."name"
		and "tbc"."party" = "trainer"."party"
		order by "tbc"."command"
	) as "battle"
  )
  ,'items_', (
  	select json_group_array(json_object('name', "item"."name", 'quantity', "item"."quantity"))
  	from (
  		select "item"."name", "trainer_item"."quantity"
  		from "trainer_item" join "item" on "item"."id" = "trainer_item"."item"
  		where
    		"trainer_item"."trainer_type" = "trainer"."type"
    		and "trainer_item"."trainer_name" = "trainer"."name"
    		and "trainer_item"."party_id" = "trainer"."party"
  		order by "item"."code"
  	) as "item"
  )
  ,'pokemons', (
  	select json_group_array(json_object(
  		'name', "pokemon"."name", 'number', "pokemon"."number"
  		,'form', "pokemon"."form", 'form_order', "pokemon"."form_order"
  		,'nickname', "pokemon"."nickname", 'shiny', "pokemon"."shiny"
  		,'level', "pokemon"."level", 'gender', "pokemon"."gender",'nature', "pokemon"."nature"
  		,'item', "pokemon"."item", 'friendship', "pokemon"."friendship", 'sprite', "pokemon"."sprite"
  	  ,'abilities', json("pokemon"."abilities"), 'moves', json("pokemon"."moves")
  		,'evs', json("pokemon"."evs"), 'ivs', json("pokemon"."ivs"), 'stats', json("pokemon"."stats")
  	))
  	from (
  		select
  			"pokemon"."name", "pokemon"."number",
  			"form"."name" as "form", "form"."order" as "form_order"
  			,ifnull("trainer_pokemon"."nickname", "pokemon"."name") as "nickname"
  			,"trainer_pokemon"."shiny", "trainer_pokemon"."level", "trainer_pokemon"."gender"
  			,"nature"."name" as "nature","item"."name" as "item", "trainer_pokemon"."friendship"
  			,base64("sprite"."sprite") as "sprite"
  			,(
  				select json_group_array(json_object('form', "possible_form"."name", 'abilities', json("possible_form"."abilities")))
  				from (
  					select "possible_form"."name", (
  						select json_group_array("ability"."name")
  						from (
  							select "ability"."name"
  							from "trainer_pokemon_ability"
  							join "pokemon_ability" on (
  								"pokemon_ability"."pokemon" = "trainer_pokemon"."pokemon"
  								and "pokemon_ability"."form" = "possible_form"."name"
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
  					from "pokemon_form" as "possible_form"
  					where
	  					"possible_form"."pokemon" = "trainer_pokemon"."pokemon"
	  					and 
  						("trainer_pokemon"."form" is null or "possible_form"."name" = "trainer_pokemon"."form")
	  				order by "possible_form"."order"
  				) as "possible_form"
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
      left join "pokemon_form" as "form" on (
          "form"."pokemon" = "trainer_pokemon"."pokemon"
          and "form"."name" = "trainer_pokemon"."form"
      )
      join "pokemon" on "pokemon"."id" = "trainer_pokemon"."pokemon"
      left join "pokemon_sprite" as "sprite" on (
      	"sprite"."pokemon" = "trainer_pokemon"."pokemon"
      	-- due solely to Arcade Star Carol 3 having a Meowstic with variable gender, we have to account for the form
      	-- sometimes being null (in which case we just use the first form, i.e. Male in this case, for the sprite)
      	and ("form"."name" is null or "sprite"."form" = "form"."name")
      	and "sprite"."type" = 'front' and "sprite"."shiny" = "trainer_pokemon"."shiny"
      	and ((
      		"trainer_pokemon"."gender" is null
      		and ("sprite"."gender" is null or "sprite"."gender" = 'Male')
      	) or (
      		"sprite"."gender" is null or "trainer_pokemon"."gender" = "sprite"."gender"
      	))
      )
      join "pokemon_form" as "sprite_form" on "sprite_form"."pokemon" = "sprite"."pokemon" and "sprite_form"."name" = "sprite"."form"
      join "nature" on "nature"."id" = "trainer_pokemon"."nature"
      left join "item" on "item"."id" = "trainer_pokemon"."item"
      where 
		    "trainer_pokemon"."trainer_type" = "trainer"."type"
		    and "trainer_pokemon"."trainer_name" = "trainer"."name"
		    and "trainer_pokemon"."party_id" = "trainer"."party"
		    and ("form"."name" is not null or "sprite_form"."order" = 0)
      order by "trainer_pokemon"."index"
  	) as "pokemon"
  )
)
from "trainer_v" as "trainer"
-- where does the order of the trainers in debug menu come from?