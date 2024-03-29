create table "map_event" (
	"map_id" integer, 
	"event_id" integer,
	"name" text not null,
	"x" integer not null,
	"y" integer not null,
	primary key ("map_id", "event_id"),
	foreign key ("map_id") references "map" ("id")
) without rowid;

drop table if exists "event_page_trigger";
create table "event_page_trigger" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "event_page_trigger" ("name", "code")
values
('action_button', 0),
('player_touch', 1),
('event_touch', 2),
('autorun', 3),
('parallel_process', 4);

create table "event_page" (
	"map_id" integer,
	"event_id" integer,
	"page_number" integer,
	"trigger" text not null,
	"move_type" text not null,
	"move_speed" text not null,
	"move_frequency" text not null,
	"move_route_repeat" integer not null check ("move_route_repeat" in (0, 1)),
	"move_route_skippable" integer not null check ("move_route_skippable" in (0, 1)),
	"moving_animation" integer not null check ("moving_animation" in (0, 1)),
	"stopped_animation" integer not null check ("stopped_animation" in (0, 1)),
	"fixed_direction" integer not null check ("fixed_direction" in (0, 1)),
	"move_through" integer not null check ("move_through" in (0, 1)),
	"always_on_top" integer not null check ("always_on_top" in (0, 1)),
	primary key ("map_id", "event_id", "page_number"),
	foreign key ("map_id", "event_id") references "map_event" ("map_id", "event_id"),
	foreign key ("trigger") references "event_page_trigger" ("name"),
	foreign key ("move_type") references "move_type" ("name"),
	foreign key ("move_speed") references "move_speed" ("name"),
	foreign key ("move_frequency") references "move_frequency" ("name")
) without rowid;

create table "event_page_switch_condition" (
	"map_id" integer,
	"event_id" integer,
	"page_number" integer,
	"index" integer not null check ("index" in (1, 2)),
	"switch" integer not null,
	primary key ("map_id", "event_id", "page_number", "index"),
	foreign key ("map_id", "event_id", "page_number") references "event_page" ("map_id", "event_id", "page_number"),
	foreign key ("switch") references "game_switch" ("id")
) without rowid;

create table "event_page_variable_condition" (
	"map_id" integer,
	"event_id" integer,
	"page_number" integer,
	"variable" integer not null,
	"lower_bound" integer not null,
	primary key ("map_id", "event_id", "page_number"),
	foreign key ("map_id", "event_id", "page_number") references "event_page" ("map_id", "event_id", "page_number"),
	foreign key ("variable") references "game_variable" ("id")
) without rowid;

create table "event_page_self_switch_condition" (
	"map_id" integer,
	"event_id" integer,
	"page_number" integer,
	"switch" text not null,
	primary key ("map_id", "event_id", "page_number"),
	foreign key ("map_id", "event_id", "page_number") references "event_page" ("map_id", "event_id", "page_number")
) without rowid;

create table "event_page_tile" (
	"map_id" integer,
	"event_id" integer,
	"page_number" integer,
	"tile" integer,
	primary key ("map_id", "event_id", "page_number"),
	foreign key ("map_id", "event_id", "page_number") references "event_page" ("map_id", "event_id", "page_number")
) without rowid;

create table "event_page_character" (
	"map_id" integer,
	"event_id" integer,
	"page_number" integer,
	"character_name" text not null,
	"character_hue" integer not null,
	"direction" text not null,
	"pattern" integer not null,
	"opacity" integer not null,
	"blend_type" integer not null,
	primary key ("map_id", "event_id", "page_number"),
	foreign key ("map_id", "event_id", "page_number") references "event_page" ("map_id", "event_id", "page_number"),
	foreign key ("direction") references "direction" ("name")
) without rowid;

create table "parameter_type" ("name" text primary key) without rowid;
insert into "parameter_type" ("name")
values
('integer'),
('text'),
('bool'),
('audio_file'),
('direction'),
('choices_array'),
('tone'),
('color'),
('cancel_type'),
('text_position'),
('switch_state'),
('diff_type'),
('appoint_type'),
('move_route'),
('weather'),
('move_command'),
('comparison'),
('bound_type');

drop table if exists "switch_state";
create table "switch_state" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "switch_state" ("name", "code")
values
('on', 0),
('off', 1);

drop table if exists "cancel_type";
create table "cancel_type" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "cancel_type" ("name", "code")
values
('disallow', 0),
('choice1', 1),
('choice2', 2),
('choice3', 3),
('choice4', 4),
('branch', 5);

drop table if exists "appoint_type";
create table "appoint_type" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "appoint_type" ("name", "code")
values
('direct', 0),
('variable', 1),
('exchange', 2);

drop table if exists "comparison";
create table "comparison" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "comparison" ("name", "code")
values
('eq', 0),
('ge', 1),
('le', 2),
('gt', 3),
('lt', 4),
('ne', 5);

drop table if exists "bound_type";
create table "bound_type" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "bound_type" ("name", "code")
values
('lower', 0),
('upper', 1);

drop table if exists "diff_type";
create table "diff_type" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "diff_type" ("name", "code")
values
('decrease', 0),
('increase', 1);

drop table if exists "text_position";
create table "text_position" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "text_position" ("name", "code")
values
('top', 0),
('middle', 1),
('bottom', 2);

---------------------------------------------------------------------------------------------------
-- Move commands
---------------------------------------------------------------------------------------------------

create table "move_command_type" (
	"name" text primary key,
	"readable_name" text not null unique,
	"code" integer not null unique
);

insert into "move_command_type" ("name", "readable_name", "code")
values
('Blank', 'blank', 0),
('MoveDown', 'move down', 1),
('MoveLeft', 'move left', 2),
('MoveRight', 'move right', 3),
('MoveUp', 'move up', 4),
('MoveLowerLeft', 'move lower left', 5),
('MoveLowerRight', 'move lower right', 6),
('MoveUpperLeft', 'move upper left', 7),
('MoveUpperRight', 'move upper right', 8),
('MoveAtRandom', 'move at random', 9),
('MoveTowardPlayer', 'move towards player', 10),
('MoveAwayFromPlayer', 'move away from player', 11),
('StepForward', 'step forward', 12),
('StepBackward', 'step backward', 13),
('Jump', 'jump', 14),
('Wait', 'wait', 15),
('TurnDown', 'turn down', 16),
('TurnLeft', 'turn left', 17),
('TurnRight', 'turn right', 18),
('TurnUp', 'turn up', 19),
('Turn90Right', 'turn 90° right', 20),
('Turn90Left', 'turn 90° left', 21),
('Turn180', 'turn 180°', 22),
('Turn90RightOrLeft', 'turn 90° right or left', 23),
('TurnAtRandom', 'turn at random', 24),
('TurnTowardPlayer', 'turn towards player', 25),
('TurnAwayFromPlayer', 'turn away from player', 26),
('SwitchOn', 'turn switch on', 27),
('SwitchOff', 'turn switch off', 28),
('ChangeSpeed', 'change speed', 29),
('ChangeFreq', 'change frequency', 30),
('MoveAnimationOn', 'turn move animation on', 31),
('MoveAnimationOff', 'turn move animation off', 32),
('StopAnimationOn', 'turn stop animation on', 33),
('StopAnimationOff', 'turn stop animation off', 34),
('DirectionFixOn', 'fix direction', 35),
('DirectionFixOff', 'unfix direction', 36),
('ThroughOn', 'allow movement through obstacles', 37),
('ThroughOff', 'prevent movement through obstacles', 38),
('AlwaysOnTopOn', 'turn always on top on', 39),
('AlwaysOnTopOff', 'turn always on top off', 40),
('Graphic', 'change graphic', 41),
('ChangeOpacity', 'change opacity', 42),
('ChangeBlendType', 'change blend type', 43),
('PlaySE', 'play sound effect', 44),
('Script', 'run script', 45);

create table "move_command_parameter" (
	"command_type" text,
	"name" text,
	"type" text,
	primary key ("command_type", "name", "type"),
	unique ("command_type", "name"),
	foreign key ("command_type") references "move_command_type" ("name"),
	foreign key ("type") references "parameter_type" ("name")
) without rowid;

insert into "move_command_parameter" ("command_type", "name", "type")
values
('Jump', 'x', 'integer'),
('Jump', 'y', 'integer'),
('Wait', 'count', 'integer'),
('SwitchOn', 'switch_id', 'integer'),
('SwitchOff', 'switch_id', 'integer'),
('ChangeSpeed', 'speed', 'integer'),
('ChangeFreq', 'freq', 'integer'),
('Graphic', 'character_name', 'text'),
('Graphic', 'character_hue', 'integer'),
('Graphic', 'direction', 'direction'),
('Graphic', 'pattern', 'integer'),
('ChangeOpacity', 'opacity', 'integer'),
('ChangeBlendType', 'blend_type', 'integer'),
('PlaySE', 'audio', 'audio_file'),
('Script', 'line', 'text');

create table "move_command" (
	"id" integer unique,
	"type" text,
	primary key ("id", "type")
	foreign key ("type") references "move_command_type" ("name")
) without rowid;

create table "event_page_move_command" (
	"map_id" integer,
	"event_id" integer,
	"page_number" integer,
	"command_number" integer,	
	"command" integer not null,
	primary key ("map_id", "event_id", "page_number", "command_number"),
	foreign key ("map_id", "event_id", "page_number") references "event_page" ("map_id", "event_id", "page_number"),
	foreign key ("command") references "move_command" ("id")
) without rowid;

create table "move_command_integer_argument" (
	"command" integer,
	"command_type" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'integer'),
	"value" integer not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type") references "move_command" ("id", "type"),
	foreign key ("command_type", "parameter", "type")
		references "move_command_parameter" ("command_type", "name", "type")
) without rowid;

create table "move_command_text_argument" (
	"command" integer,
	"command_type" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'text'),
	"value" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type") references "move_command" ("id", "type"),
	foreign key ("command_type", "parameter", "type")
		references "move_command_parameter" ("command_type", "name", "type")
) without rowid;

create table "move_command_audio_file_argument" (
	"command" integer,
	"command_type" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'audio_file'),
	"name" text not null,
	"volume" integer not null,
	"pitch" integer not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type") references "move_command" ("id", "type"),
	foreign key ("command_type", "parameter", "type")
		references "move_command_parameter" ("command_type", "name", "type")
) without rowid;

create table "move_command_direction_argument" (
	"command" integer,
	"command_type" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'direction'),
	"direction" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type") references "move_command" ("id", "type"),
	foreign key ("command_type", "parameter", "type")
		references "move_command_parameter" ("command_type", "name", "type"),
	foreign key ("direction") references "direction" ("name")
) without rowid;

---------------------------------------------------------------------------------------------------
-- Event commands
---------------------------------------------------------------------------------------------------

create table "event_command_type" (
	"name" text primary key,
	"code" integer not null unique
) without rowid;

create table "event_command_subtype"  (
	"command_type" text,
	"name" text,
	"code" integer not null,
	primary key ("command_type", "name"),
	foreign key ("command_type") references "event_command_type" ("name"),
	unique ("command_type", "code")
) without rowid;

create table "event_command_parameter" (
	"command_type" text,
	"command_subtype" text,
	"name" text,
	"type" text,
	primary key ("command_type", "command_subtype", "name", "type"),
	unique ("command_type", "command_subtype", "name"),
	foreign key ("command_type", "command_subtype")
		references "event_command_subtype" ("command_type", "name"),
	foreign key ("type") references "parameter_type" ("name")
) without rowid;

create table "event_command" (
	"id" integer unique,
	"type" text,
	"subtype" text,
	primary key ("id", "type", "subtype"),
	foreign key ("type", "subtype") references "event_command_subtype" ("command_type", "name")
) without rowid;

create table "event_page_command" (
	"map_id" integer,
	"event_id" integer,
	"page_number" integer,
	"command_number" integer,
	"indent" integer,
	"command" integer not null,
	primary key ("map_id", "event_id", "page_number", "command_number"),
	foreign key ("map_id", "event_id", "page_number") references "event_page" ("map_id", "event_id", "page_number"),
	foreign key ("command") references "event_command" ("id")
) without rowid;

create table "event_command_integer_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'integer'),
	"value" integer not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type")
) without rowid;

create table "event_command_text_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'text'),
	"value" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type")
) without rowid;

create table "event_command_bool_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'bool'),
	"value" integer not null check ("value" in (0, 1)),
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type")
) without rowid;

create table "event_command_audio_file_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'audio_file'),
	"name" text not null,
	"volume" integer not null,
	"pitch" integer not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type")
) without rowid;

create table "event_command_direction_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'direction'),
	"direction" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type"),
	foreign key ("direction") references "direction" ("name")
) without rowid;

create table "event_command_choices_array_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'choices_array'),
	"choice1" text not null,
	"choice2" text not null,
	"choice3" text not null,
	"choice4" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type")
) without rowid;

create table "event_command_tone_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'tone'),
	"value" blob not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type")
) without rowid;

create table "event_command_color_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'color'),
	"value" blob not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type")
) without rowid;

create table "event_command_cancel_type_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'cancel_type'),
	"cancel_type" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type"),
	foreign key ("cancel_type") references "cancel_type" ("name")
) without rowid;

create table "event_command_text_position_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'text_position'),
	"text_position" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type"),
	foreign key ("text_position") references "text_position" ("name")
) without rowid;

create table "event_command_switch_state_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'switch_state'),
	"switch_state" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type"),
	foreign key ("switch_state") references "switch_state" ("name")
) without rowid;

create table "event_command_diff_type_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'diff_type'),
	"diff_type" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type"),
	foreign key ("diff_type") references "diff_type" ("name")
) without rowid;

create table "event_command_appoint_type_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'appoint_type'),
	"appoint_type" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type"),
	foreign key ("appoint_type") references "appoint_type" ("name")
) without rowid;

create table "event_command_move_route_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'move_route'),
	"repeat" integer not null check ("repeat" in (0, 1)),
	"skippable" integer not null check ("skippable" in (0, 1)),
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type")
) without rowid;

create table "event_command_move_route_argument_move_command" (
	"event_command" integer,
	"parameter" text,
	"move_command_number" integer,
	"move_command" integer not null,
	primary key ("event_command", "parameter", "move_command_number"),
	foreign key ("event_command", "parameter")
		references "event_command_move_route_argument" ("command", "parameter"),
	foreign key ("move_command") references "move_command" ("id")
) without rowid;

create table "event_command_comparison_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'comparison'),
	"comparison" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type"),
	foreign key ("comparison") references "comparison" ("name")
) without rowid;

create table "event_command_bound_type_argument" (
	"command" integer,
	"command_type" text not null,
	"command_subtype" text not null,
	"parameter" text,
	"type" text not null check ("type" = 'bound_type'),
	"bound_type" text not null,
	primary key ("command", "parameter"),
	foreign key ("command", "command_type", "command_subtype")
		references "event_command" ("id", "type", "subtype"),
	foreign key ("command_type", "command_subtype", "parameter", "type")
		references "event_command_parameter" ("command_type", "command_subtype", "name", "type"),
	foreign key ("bound_type") references "bound_type" ("name")
) without rowid;

-- insert into "event_command_type" ("name", "code")
-- values
-- ('blank', 0), ('show text', 101), ('show choices', 102), ('input number', 103),
-- ('change text options', 104), 
-- ('get input from button press', 105),
-- ('wait', 106),
-- ('comment', 108),
-- ('conditional branch', 111),
-- ('loop', 112),
-- ('break loop', 113),

-- ('move down', 1), ('move left', 2), ('move right', 3), ('move up', 4),
-- ('move lower left', 5), ('move lower right', 6), ('move upper left', 7), ('move upper right', 8),
-- ('move at random', 9), ('move towards player', 10), ('move away from player', 11),
-- ('step forward', 12), ('step backward', 13), ('jump', 14), ('wait', 15),
-- ('turn down', 16), ('turn left', 17), ('turn right', 18), ('turn up', 19),
-- ('turn 90° right', 20), ('turn 90° left', 21), ('turn 180°', 22), ('turn 90° right or left', 23),
-- ('turn at random', 24), ('turn towards player', 25), ('turn away from player', 26),
-- ('turn switch on', 27), ('turn switch off', 28), ('change speed', 29), ('change frequency', 30),
-- ('turn move animation on', 31), ('turn move animation off', 32),
-- ('turn stop animation on', 33), ('turn stop animation off', 34),
-- ('fix direction', 35), ('unfix direction', 36),
-- ('allow movement through obstacles', 37), ('prevent movement through obstacles', 38),
-- ('turn always on top on', 39), ('turn always on top off', 40),
-- ('change graphic', 41), ('change opacity', 42), ('change blend type', 43),
-- ('play sound effect', 44), ('run script', 45);



-- insert into "event_command_parameter" ("command_type", "name", "type")
-- values
-- ('show text', 'text', 'string'),
-- ('show choices', 'choices', 'array[string]'),
-- ('show choices', 'cancel_type', 'cancel_type'),

-- ('jump', 'x', 'integer'),
-- ('jump', 'y', 'integer'),
-- ('wait', 'count', 'integer'),
-- ('turn switch on', 'switch', 'switch'),
-- ('turn switch off', 'switch', 'switch'),
-- ('change speed', 'speed', 'integer'),
-- ('change frequency', 'frequency', 'integer'),
-- ('change graphic', 'character_name', 'string'),
-- ('change graphic', 'character_hue', 'integer'),
-- ('change graphic', 'direction', 'direction'),
-- ('change graphic', 'pattern', 'integer'),
-- ('change opacity', 'opacity', 'integer'),
-- ('change blend type', 'blend_type', 'integer'),
-- ('play sound effect', 'audio', 'audio'),
-- ('run script', 'line', 'string');
