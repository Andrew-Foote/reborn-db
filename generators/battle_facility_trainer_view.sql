select json_object(
  'name', "type"."name" || ' ' || ifnull("trainer"."name", 'no name') || case
      when count(*) over (partition by "type"."name", "trainer"."name") > 1
      then ' ' || row_number() over (partition by "type"."name", "trainer"."name") else ''
      -- order by?
  end
  ,'skill', "type"."skill"
  ,'front_sprite', base64("type"."battle_sprite")
  ,'back_sprite', base64("type"."battle_back_sprite")
  ,'begin_speech', "trainer"."begin_speech"
  ,'win_speech', "trainer"."win_speech"
  ,'lose_speech', "trainer"."lose_speech"
  ,'pokemons', (
  	select json_group_array(json_object(
  		'name', "pokemon"."name", 'number', "pokemon"."number"
  		,'form', "pokemon"."form", 'form_order', "pokemon"."form_order"
			,'nature', "pokemon"."nature"
  		,'item', "pokemon"."item", 'sprite', "pokemon"."sprite"
  	  ,'abilities', json("pokemon"."abilities"), 'moves', json("pokemon"."moves")
  		,'evs', json("pokemon"."evs")
  	))
  	from (
  		select
  			"pokemon"."name", "pokemon"."number"
  			,"form"."name" as "form", "form"."order" as "form_order"
  			,"nature"."name" as "nature","item"."name" as "item"
  			,base64("sprite"."sprite") as "sprite"
  			,(
  				select json_group_array(json_object(
  					'form', "possible_form"."name",
  					'ability', "possible_form"."ability"
  				))
  				from (
  					select "possible_form"."name", "ability"."name" as "ability"
  					from "pokemon_form" as "possible_form"
  					join "pokemon_ability" on (
  						"pokemon_ability"."pokemon" = "bfset"."pokemon"
  						and "pokemon_ability"."form" = "possible_form"."name"
  						and "pokemon_ability"."index" = "bfset"."ability"
  					)
						join "ability" on "ability"."id" = "pokemon_ability"."ability"
  					where
	  					"possible_form"."pokemon" = "bfset"."pokemon"
	  					and 
  						("bfset"."form" is null or "possible_form"."name" = "bfset"."form")
	  				order by "possible_form"."order"
  				) as "possible_form"
  			) as "abilities"
				,(
					select json_group_array(json_object(
						'id', "move"."id", 'name', "move"."name", 'pp', "move"."pp"
					))
					from (
						select "move"."name", "move"."id", case
						  when "type"."skill" >= 100
							then ("move"."pp" * 8) / 5 else "move"."pp"
						end as "pp"
						from "battle_facility_set_move" as "pokemon_move"
						join "move" on "move"."id" = "pokemon_move"."move"
						where
							"pokemon_move"."list" = "bfset"."list"
							and "pokemon_move"."set_index" = "bfset"."index"
						order by "pokemon_move"."move_index"
					) as "move"
				) as "moves"
				,(
					select json_group_array(json_object('stat', "ev"."stat", 'value', "ev"."value"))
					from (
						select "stat"."name" as "stat", "ev"."ev" as "value"
						from "battle_facility_set_ev" as "ev"
						join "stat" on "stat"."id" = "ev"."stat"
						where
							"ev"."list" = "bfset"."list"
							and "ev"."set_index" = "bfset"."index"
						order by "stat"."order"
					) as "ev"
				) as "evs"
      from "battle_facility_trainer_pokemon" as "bftp"
      join "battle_facility_set" as "bfset" on (
      	"bfset"."list" = "bftp"."list" and "bfset"."pokemon" = "bftp"."pokemon"
      )
      left join "pokemon_form" as "form" on (
          "form"."pokemon" = "bfset"."pokemon"
          and "form"."name" = "bfset"."form"
      )
      join "pokemon" on "pokemon"."id" = "bfset"."pokemon"
      left join "pokemon_sprite" as "sprite" on (
      	"sprite"."pokemon" = "bfset"."pokemon"
      	-- due solely to Arcade Star Carol 3 having a Meowstic with variable gender, we have to account for the form
      	-- sometimes being null (in which case we just use the first form, i.e. Male in this case, for the sprite)
      	and ("form"."name" is null or "sprite"."form" = "form"."name")
      	and "sprite"."type" = 'front' and "sprite"."shiny" = 0
      	and ("sprite"."gender" is null or "sprite"."gender" = 'Male')
      )
      join "pokemon_form" as "sprite_form" on "sprite_form"."pokemon" = "sprite"."pokemon" and "sprite_form"."name" = "sprite"."form"
      join "nature" on "nature"."id" = "bfset"."nature"
      left join "item" on "item"."id" = "bfset"."item"
      where 
      	"bftp"."list" = "trainer"."list"
      	and "bftp"."trainer_index" = "trainer"."index"
		    and ("form"."name" is not null or "sprite_form"."order" = 0)
      order by "bftp"."pokemon_index", "bfset"."index"
  	) as "pokemon"
  )
)
from "battle_facility_trainer" as "trainer"
join "trainer_type" as "type" on "type"."id" = "trainer"."type"

-- where does the order of the trainers in debug menu come from?