----------------------------------------------------------------------------------------------------
-- Types
----------------------------------------------------------------------------------------------------

-- [An {attacking_type} move hitting a Pokémon of type {defending_type1}/{defending_type2}
-- will have a damage multiplier of {multiplier}. (If {defending_type2} is null, this includes
-- the case where the defending Pokémon has a single type.)]
create view "type_effect2" ("attacking_type", "defending_type1", "defending_type2", "multiplier")
as select
	"attacking_type",
	"defending_type" as "defending_type1", NULL as "defending_type2",
	"multiplier"
from "type_effect"
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
where "multiplier" != 1;

----------------------------------------------------------------------------------------------------
-- Evolution
----------------------------------------------------------------------------------------------------

-- [{evolution} is the stage {stage} evolution of the unevolved Pokémon {pokemon},
-- with {evolves_from} as the previous Pokémon in the evolution chain. (Note:
-- unevolved Pokémon are counted as the stage 0 evolutions of themselves.)]
create view "pokemon_evolution_stage" ("pokemon", "evolution", "stage", "evolves_from") as
with recursive "pokemon_evolution_stage" (
	"pokemon", "evolution", "stage", "evolves_from"
) as (
	select "id", "id", 0, null from "pokemon" where "evolves_from" is null
	union all
	select
		"pokemon"."id"
		,"evolves_to"."id"
		,"pokemon_evolution_stage"."stage" + 1
		,"evolution"."id"
	from "pokemon_evolution_stage"
	join "pokemon" on "pokemon"."id" = "pokemon_evolution_stage"."pokemon"
	join "pokemon" as "evolution" on "evolution"."id" = "pokemon_evolution_stage"."evolution"
	join "pokemon" as "evolves_to" on "evolves_to"."evolves_from" = "evolution"."id"
)
select * from "pokemon_evolution_stage";

----------------------------------------------------------------------------------------------------
-- Moves
----------------------------------------------------------------------------------------------------

create view "pokemon_move" ("pokemon", "form", "move", "method", "level", "order") as
	select "pokemon", "form", "move", 'level', "level", "order" from "level_move"
	union
	select "pokemon", "form", "move", 'egg', null, null from "egg_move"
	union
	select "pokemon", "form", "move", 'machine', null, null from "machine_move"
	union
	select "pokemon", "form", "move", 'tutor', null, null from "tutor_move";

-- note that this includes egg moves --- this is relevant because for a Pokémon like Roserade, it
-- can learn either Extrasensory via Budew's egg move or Bullet Seed via Roselia's egg moves, but
-- not both
create view "preevo_move" ("pokemon", "form", "preevo", "preevo_form", "dist", "method", "level", "order", "move") as
select
	"form"."pokemon", "form"."name", "preevo"."from", "preevo"."from_form", "preevo"."dist",
	"move"."method", "move"."level", "move"."order", "move"."move"
from "pokemon_form" as "form"
join "evolution_trcl" as "preevo" on (
	"preevo"."to" = "form"."pokemon" and "preevo"."to_form" = "form"."name"
)
join "pokemon_move" as "move" on (
	"move"."pokemon" = "preevo"."from" and "move"."form" = "preevo"."from_form"
)
left join "pokemon_move" as "evo_move" on (
   "evo_move"."pokemon" = "form"."pokemon" and "evo_move"."form" = "form"."name"
   and "evo_move"."move" = "move"."move"
)
where "evo_move"."move" is null;


----------------------------------------------------------------------------------------------------
-- Encounters
----------------------------------------------------------------------------------------------------

-- note that the level range is not necessarily made up of consecutive levels!
-- example is pyroar in obsidia alleyway post-restoration; 4% encounter rate,
-- 2% levels 45--65, 2% levels 70--90
create view "pokemon_encounter_rate_by_level_range" (
	"map", "method", "pokemon", "form", "level_range", "rate"
) as select
	"map", "method", "pokemon", "form", json_group_array("level"),
	frac_mul("rate", count("level"))
from "pokemon_encounter_rate"
group by "map", "method", "pokemon", "form", "rate";

create view "pokemon_encounter_rate_by_form" (
	"map", "method", "pokemon", "form", "rate"
) as select
	"map", "method", "pokemon", "form", frac_sum("rate")
from "pokemon_encounter_rate"
group by "map", "method", "pokemon", "form";

create view "random_encounter_move" ("map", "method", "pokemon", "form", "level", "index", "move") as
with
	"level_move_o" as (
		select
			"pokemon", "form", "level"
			,row_number() over (partition by "pokemon", "form" order by "level", "order") as "order"
			,"move"
		from "level_move"
	)
	,"per" as (
		select
			"per"."map", "per"."method", "lm"."pokemon", "lm"."form", "per"."level", max("lm"."order") as "last_move_order"
			from "pokemon_encounter_rate" as "per"
			join "level_move_o" as "lm"
				on "lm"."pokemon" = "per"."pokemon" and ("lm"."form" = "per"."form" or "per"."form" is null)
				and "lm"."level" <= "per"."level"
			group by "per"."map", "per"."method", "lm"."pokemon", "lm"."form", "per"."level"
	)
select 
	"per"."map", "per"."method", "per"."pokemon", "per"."form", "per"."level"
	,"lm"."order" - "per"."last_move_order" + min(3, "last_move_order" - 1) as "index"
	,"lm"."move"
from "per" join "level_move_o" as "lm" on "lm"."pokemon" = "per"."pokemon" and "lm"."form" = "per"."form"
and "lm"."order" between "per"."last_move_order" - 3 and "per"."last_move_order";

----------------------------------------------------------------------------------------------------
-- Move tutors
----------------------------------------------------------------------------------------------------

create view "tutor_move_teach_command" ("move", "command") as
select
	regexp_capture("arg"."value", '^pbMoveTutorChoose\(PBMoves::(\w+)\)$', 1),
	"arg"."command"
from "event_command_text_argument" as "arg"
where "arg"."command_type" = 'ConditionalBranch'
and "arg"."command_subtype" = 'Script'
and "arg"."parameter" = 'expr'
and "arg"."value" glob 'pbMoveTutorChoose(*';

create view "tutorable_move" ("move") as
select distinct "move" from "tutor_move_teach_command";

create view "tutor_move_item_cost" (
	"move", "item", "quantity", "command1", "command2",
	"map_id", "event_id", "page_number", "command1_number"
) as
select
	regexp_capture("arg"."value", '^addTutorMove\(PBMoves::(\w+)\)$', 1),
	regexp_capture("arg0"."value", '^PBItems::(\w+),(\d+)\)$', 1),
	regexp_capture("arg0"."value", '^PBItems::(\w+),(\d+)\)$', 2),
	"arg0"."command",
	"arg"."command",
	"epc"."map_id",
	"epc"."event_id",
	"epc"."page_number",
	"epc"."command_number"
from "event_command_text_argument" as "arg"
join "event_page_command" as "epc" on "epc"."command" = "arg"."command"
join "event_page_command" as "epc0" on (
	"epc0"."map_id" = "epc"."map_id"
	and "epc0"."event_id" = "epc"."event_id"
	and "epc0"."page_number" = "epc"."page_number"
	and "epc0"."command_number" = "epc"."command_number" - 1
)
join "event_command_text_argument" as "arg0" on (
	"arg0"."command" = "epc0"."command"
	and "arg0"."command_type" = 'ContinueScript'
	and "arg0"."command_subtype" = ''
	and "arg0"."parameter" = 'line'
)
where "arg"."command_type" = 'Script'
and "arg"."command_subtype" = ''
and "arg"."parameter" = 'line'
and "arg"."value" glob 'addTutorMove(*';

create view "tutor_move_money_cost" (
	"move", "amount", "command1", "command2",
	"map_id", "event_id", "page_number", "command1_number"
) as
select
	regexp_capture("arg"."value", '^addTutorMove\(PBMoves::(\w+)\)$', 1),
	"arg0"."value",
	"arg0"."command",
	"arg"."command",
	"epc"."map_id",
	"epc"."event_id",
	"epc"."page_number",
	"epc"."command_number"
from "event_command_text_argument" as "arg"
join "event_page_command" as "epc" on "epc"."command" = "arg"."command"
join "event_page_command" as "epc0" on (
	"epc0"."map_id" = "epc"."map_id"
	and "epc0"."event_id" = "epc"."event_id"
	and "epc0"."page_number" = "epc"."page_number"
	and "epc0"."command_number" = "epc"."command_number" - 1
)
join "event_command_integer_argument" as "arg0" on (
	"arg0"."command" = "epc0"."command"
	and "arg0"."command_type" = 'ChangeGold'
	and "arg0"."command_subtype" = ''
	and "arg0"."parameter" = 'amount'
)
join "event_command_bool_argument" as "arg0_withvar" on (
	"arg0_withvar"."command" = "epc0"."command"
	and "arg0_withvar"."command_type" = 'ChangeGold'
	and "arg0_withvar"."command_subtype" = ''
	and "arg0_withvar"."parameter" = 'with_variable'
	and "arg0_withvar"."value" = 0
)
join "event_command_diff_type_argument" as "arg0_difftype" on (
	"arg0_difftype"."command" = "epc0"."command"
	and "arg0_difftype"."command_type" = 'ChangeGold'
	and "arg0_difftype"."command_subtype" = ''
	and "arg0_difftype"."parameter" = 'diff_type'
	and "arg0_difftype"."diff_type" = 'decrease'
)
where "arg"."command_type" = 'Script'
and "arg"."command_subtype" = ''
and "arg"."parameter" = 'line'
and "arg"."value" glob 'addTutorMove(*';

create view "event_page_character_image" (
	"map_id", "event_id", "page_number",
	"character_name", "character_hue",
	"direction", "pattern",
	"opacity", "blend_type",
	"image"
) as
select "epchar".*, "char_img"."content"
from "event_page_character" as "epchar"
join "character_image" as "char_img" on (
	"char_img"."file" = "epchar"."character_name"
	and "char_img"."direction" = "epchar"."direction"
	and "char_img"."pattern" = "epchar"."pattern"
);

create view "move_tutor_v" (
	"move", "cost_is_monetary", "cost_quantity", "cost_item", "sprite", "map"
) as
select
	"tcmd"."move",
	case when "mcost"."amount" is null then 0 else 1 end,
	coalesce("icost"."quantity", "mcost"."amount"),
	"icost"."item",
	"char_img"."content",
	"epcmd"."map_id"
from "tutor_move_teach_command" as "tcmd"
join "event_page_command" as "epcmd" on "epcmd"."command" = "tcmd"."command"
join "event_page_character" as "epchar" on (
	"epchar"."map_id" = "epcmd"."map_id"
	and "epchar"."event_id" = "epcmd"."event_id"
	and "epchar"."page_number" = "epcmd"."page_number"
)
join "character_image" as "char_img" on (
	"char_img"."file" = lower("epchar"."character_name")
	and "char_img"."direction" = "epchar"."direction"
	and "char_img"."pattern" = "epchar"."pattern"
)
left join "tutor_move_item_cost" as "icost" on (
	"icost"."map_id" = "epcmd"."map_id"
	and "icost"."event_id" = "epcmd"."event_id"
	and "icost"."page_number" = "epcmd"."page_number"
	and "icost"."move" = "tcmd"."move"
)
left join "tutor_move_money_cost" as "mcost" on (
	"mcost"."map_id" = "epcmd"."map_id"
	and "mcost"."event_id" = "epcmd"."event_id"
	and "mcost"."page_number" = "epcmd"."page_number"
	and "mcost"."move" = "tcmd"."move"
);

----------------------------------------------------------------------------------------------------
-- Trainers
----------------------------------------------------------------------------------------------------

create view "trainer_pokemon_stat" (
	"trainer_type", "trainer_name", "party_id", "pokemon_index", "stat", "value"
) as
	select
		"tp"."trainer_type", "tp"."trainer_name", "tp"."party_id", "tp"."index", "base_stat"."stat",
		case when "base_stat"."stat" = 'HP' then
			case when "base_stat"."value" = 1 then 1 -- for shedinja
			else
			cast(
				("base_stat"."value" * 2 + "iv"."value" + "ev"."value" / 4) * "tp"."level" / 100
			as int) + "tp"."level" + 10
			end
		else
			cast((cast(
				("base_stat"."value" * 2 + "iv"."value" + "ev"."value" / 4) * "tp"."level" / 100
			as int) + 5) * (
				case
					when (
						"nature"."increased_stat" = "base_stat"."stat"
						and "nature"."decreased_stat" != "base_stat"."stat"
					) then 1.1
					when (
						"nature"."decreased_stat" = "base_stat"."stat"
						and "nature"."increased_stat" != "base_stat"."stat"
					) then 0.9
					else 1
				end
			) as int)
		end as "value"
	from "trainer_pokemon" as "tp"
	join "base_stat" on (
		"base_stat"."pokemon" = "tp"."pokemon"
		and "base_stat"."form" = "tp"."form"
	)
	join "trainer_pokemon_ev" as "ev" on (
		"ev"."trainer_type" = "tp"."trainer_type"
		and "ev"."trainer_name" = "tp"."trainer_name"
		and "ev"."party_id" = "tp"."party_id"
		and "ev"."pokemon_index" = "tp"."index"
		and "ev"."stat" = "base_stat"."stat"
	)
	join "trainer_pokemon_iv" as "iv" on (
		"iv"."trainer_type" = "tp"."trainer_type"
		and "iv"."trainer_name" = "tp"."trainer_name"
		and "iv"."party_id" = "tp"."party_id"
		and "iv"."pokemon_index" = "tp"."index"
		and "iv"."stat" = "base_stat"."stat"
	)
	join "nature" on "nature"."id" = "tp"."nature";

create view "trainer_pokemon_v" (
	"trainer_id", "trainer_sprite", "index"
	,"pokemon", "form", "nickname", "shiny", "level", "gender"
	,"nature", "item", "friendship", "sprite", "abilities", "moves",
	"evs", "ivs", "stats"
) as
select
	"trainer"."id", "trainer"."battle_sprite", "trainer_pokemon"."index"
	,"trainer_pokemon"."pokemon", "trainer_pokemon"."form", "trainer_pokemon"."nickname"
	,"trainer_pokemon"."shiny", "trainer_pokemon"."level", "trainer_pokemon"."gender"
	,"nature"."name" as "nature","item"."name" as "item", "trainer_pokemon"."friendship"
	,"sprite"."sprite"
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
				and ("trainer_pokemon"."form" is null or "possible_form"."name" = "trainer_pokemon"."form")
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
join "trainer_v" as "trainer" on (
	"trainer"."type" = "trainer_pokemon"."trainer_type"
	and "trainer"."name" = "trainer_pokemon"."trainer_name"
	and "trainer"."party" = "trainer_pokemon"."party_id"
)
join "pokemon" on "pokemon"."id" = "trainer_pokemon"."pokemon"
join "nature" on "nature"."id" = "trainer_pokemon"."nature"
left join "pokemon_sprite" as "sprite" on (
	"sprite"."pokemon" = "trainer_pokemon"."pokemon" and
	("trainer_pokemon"."form" is null or "sprite"."form" = "trainer_pokemon"."form")
	and "sprite"."type" = 'front' and "sprite"."shiny" = "trainer_pokemon"."shiny"
	and ((
		"trainer_pokemon"."gender" is null
		and ("sprite"."gender" is null or "sprite"."gender" = 'Male')
	) or (
		"sprite"."gender" is null or "trainer_pokemon"."gender" = "sprite"."gender"
	))
)
join "pokemon_form" as "sprite_form" on (
	"sprite_form"."pokemon" = "trainer_pokemon"."pokemon"
	and "sprite_form"."name" = "sprite"."form"
)
left join "item" on "item"."id" = "trainer_pokemon"."item"
where "trainer_pokemon"."form" is not null or "sprite_form"."order" = 0;

create view "battle_facility_set_ev" ("list", "set_index", "stat", "ev") as
	with "set" as (
		select "list", "set_index" as "index", count(*) as "stat_with_ev_count"
		from "battle_facility_set_ev_stat"
		group by "list", "set_index"
	)
	select "bes"."list", "bes"."set_index", "bes"."stat", min(252, 510 / "set"."stat_with_ev_count")
	from "battle_facility_set_ev_stat" as "bes"
	join "set" on "set"."list" = "bes"."list" and "set"."index" = "bes"."set_index"
	union
	select "set"."list", "set"."index", "stat"."id", 0
	from "battle_facility_set" as "set"
	join "stat"
	left join "battle_facility_set_ev_stat" as "bes"
		on "bes"."list" = "set"."list" and "bes"."set_index" = "set"."index"
		and "bes"."stat" = "stat"."id"
	where "bes"."stat" is null; 

create view "event_command_location" (
    "command", "event_type", "event_id", "event_name",
    "number", "indent", "page",
    "map_id", "map_name", "x", "y"
)
as select
    "cmd"."id",
    case when "ce"."id" is not null then 'common' when "me"."event_id" is not null then 'map' end,
    coalesce("ce"."id", "me"."event_id"),
    coalesce("ce"."name", "me"."name"),
    coalesce("ce_cmd"."command_number", "ep_cmd"."command_number"),
    coalesce("ce_cmd"."indent", "ep_cmd"."indent"),
    "ep_cmd"."page_number",
    "ep_cmd"."map_id",
    "map"."name",
    "me"."x",
    "me"."y"
from "event_command" as "cmd"
left join "common_event_command" as "ce_cmd" on "ce_cmd"."command" = "cmd"."id"
left join "common_event" as "ce" on "ce"."id" = "ce_cmd"."common_event_id"
left join "event_page_command" as "ep_cmd" on "ep_cmd"."command" = "cmd"."id"
left join "map_event" as "me" on (
    "me"."map_id" = "ep_cmd"."map_id"
    and "me"."event_id" = "ep_cmd"."event_id"
)
left join "map" on "map"."id" = "ep_cmd"."map_id";

create view "event_comment_line" (
	"map_id", "event_id", "page_number",
	"first_command_number", "command_number", "command",
	"line"
) as
select
	"map_id", "event_id", "page_number",
	"first_command_number", "command_number", "command",
	"line"
from "map_event_comment_line"
union
select
	null, "common_event_id", null,
	"first_command_number", "command_number", "command",
	"line"
from "common_event_comment_line";


