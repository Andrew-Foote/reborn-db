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

-- Too many command types, resorting to EAV schema

-- create table "parameter_type" ("name" text primary key) without rowid;
-- insert into "parameter_type" ("name")
-- values
-- ('integer'),
-- ('real'),
-- ('text'),
-- ('game_switch'),
-- ('game_variable'),
-- ('direction'),
-- ('audio');

-- ---------------------------------------------------------------------------------------------------
-- -- Move commands
-- ---------------------------------------------------------------------------------------------------

-- create table "move_command_type" ("name" text primary key, "code" integer not null unique);

-- insert into "move_command_type" ("name", "code")
-- values
-- ('blank', 0), ('move down', 1), ('move left', 2), ('move right', 3), ('move up', 4),
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

-- create table "move_command_parameter" (
-- 	"command_type" text,
-- 	"name" text,
-- 	"type" text not null,
-- 	primary key ("command_type", "name"),
-- 	foreign key ("command_type") references "move_command_type" ("name"),
-- 	foreign key ("type") references "parameter_type" ("name")
-- ) without rowid;

-- insert into "move_command_parameter" ("command_type", "name", "type")
-- values
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

-- create table "move_command_argument" (
-- 	"command" integer,
-- 	"command_type" text
-- 	"parameter" text,
-- 	"type" text not null,
-- 	"value",
-- 	primary key ("command", "command_type", "parameter"),
-- 	foreign key ("command", "command_type") references "move_command" ("id", "type"),
-- 	foreign key ("command_type", "parameter") references "move_command_parameter" ("command_type", "name")
-- ) without rowid;

-- create table "move_command" (
-- 	"id" integer primary key,
-- 	"type" text not null,
-- 	foreign key ("type") references "move_command_type" ("name")
-- );

-- create table "event_page_move_command" (
-- 	"map_id" integer,
-- 	"event_id" integer,
-- 	"page_number" integer,
-- 	"command_number" integer,	
-- 	"command" integer not null,
-- 	primary key ("map_id", "event_id", "page_number", "command_number"),
-- 	foreign key ("map_id", "event_id", "page_number") references "event_page" ("map_id", "event_id", "page_number"),
-- 	foreign key ("command") references "move_command" ("id")
-- ) without rowid;

-- ---------------------------------------------------------------------------------------------------
-- -- Event commands
-- ---------------------------------------------------------------------------------------------------

-- create table "event_command_type" ("name" text primary key, "code" integer not null unique);

-- insert into "event_command_type" ("name", "code")
-- values
-- ('blank', 0), ('show text', 101), ('show choices', 102), ('input number', 103),
-- ('change text options', 104), 


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

-- create table "event_command_parameter" (
-- 	"command_type" text,
-- 	"name" text,
-- 	"type" text not null,
-- 	primary key ("command_type", "name"),
-- 	foreign key ("command_type") references "event_command_type" ("name"),
-- 	foreign key ("type") references "parameter_type" ("name")
-- ) without rowid;

-- insert into "event_command_parameter" ("command_type", "name", "type")
-- values
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

-- create table "event_command_argument" (
-- 	"command" integer,
-- 	"command_type" text
-- 	"parameter" text,
-- 	"type" text not null,
-- 	"value",
-- 	primary key ("command", "command_type", "parameter"),
-- 	foreign key ("command", "command_type") references "event_command" ("id", "type"),
-- 	foreign key ("command_type", "parameter") references "event_command_parameter" ("command_type", "name")
-- ) without rowid;

-- create table "event_command" (
-- 	"id" integer primary key,
-- 	"type" text not null,
-- 	foreign key ("type") references "event_command_type" ("name")
-- );

-- create table "event_page_command" (
-- 	"map_id" integer,
-- 	"event_id" integer,
-- 	"page_number" integer,
-- 	"command_number" integer,
-- 	"indent" integer,
-- 	"command" integer not null,
-- 	primary key ("map_id", "event_id", "page_number", "command_number"),
-- 	foreign key ("map_id", "event_id", "page_number") references "event_page" ("map_id", "event_id", "page_number"),
-- 	foreign key ("command") references "event_command" ("id")
-- ) without rowid;
