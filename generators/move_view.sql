-- THERE CAN BE MULTIPLE MOVES WITH THE SAME NAME! (e.g. multi-attack) so the url scheme needs to be rethought a bit --
select "move"."id", json_object(
  'name', "move"."name"
  ,'damage_class', "move"."damage_class"
  ,'type', "move"."type"
  ,'power', "move"."power"
  ,'accuracy', "move"."accuracy"
  ,'pp', "move"."pp"
  ,'target', "target"."desc"
  ,'priority', "move"."priority"
  ,'function', "function"."desc"
  ,'additional_effect_chance', "move"."additional_effect_chance"
  ,'desc', "move"."desc"
  ,'learners', (
  	select json_group_array(json_object(
  		'name', "learner"."name",
  		'form', "learner"."form",
  		'learn_methods', json("learner"."learn_methods")
  	)) 
  	from (
  		select
  			"pokemon"."name", "form"."name" as "form", 
  			json_array(
	  			case
	  				when "level_move"."move" is null then null
	  				when "level_move"."level" = 0 then 'Evolution'
	  				else 'Level ' || "level_move"."level"
	  			end,
	  			case when "egg_move"."move" is null then null else 'Egg move' end,
	  			case when "machine_move"."move" is null then null else "machine"."name" end,
	  			case when "tutor_move"."move" is null then null else 'Move tutor' end
	  		) as "learn_methods"
  		from "pokemon_form" as "form"
	  	join "pokemon" on "pokemon"."id" = "form"."pokemon"
	  	left join "level_move" on (
	  		"level_move"."pokemon" = "pokemon"."id" and "level_move"."form" = "form"."name"
	  		and "level_move"."move" = "move"."id"
	  	)
	  	left join "egg_move" on (
	  		"egg_move"."pokemon" = "pokemon"."id" and "egg_move"."form" = "form"."name"
	  		and "egg_move"."move" = "move"."id"
	  	)
	  	left join "machine_move" on (
	  		"machine_move"."pokemon" = "pokemon"."id" and "machine_move"."form" = "form"."name"
	  		and "machine_move"."move" = "move"."id"
	  	)
	  	left join "machine_item" on "machine_item"."move" = "machine_move"."move"
	  	left join "item" as "machine" on "machine_item"."item" = "machine"."id"
	  	left join "tutor_move" on (
	  		"tutor_move"."pokemon" = "pokemon"."id" and "tutor_move"."form" = "form"."name"
	  		and "tutor_move"."move" = "move"."id"
	  	)
	  	where (
	  		"level_move"."move" is not null
	  		or "egg_move"."move" is not null
	  		or "machine_move"."move" is not null
	  		or "tutor_move"."move" is not null
	  	)
		  order by "pokemon"."number", "form"."order"
	  ) as "learner"
  )
)
from "move"
join "type" on "type"."id" = "move"."type"
join "move_target" as "target" on "target"."code" = "move"."target"
join "move_function" as "function" on "function"."code" = "move"."function"
order by "move"."code"
      
-- 