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
