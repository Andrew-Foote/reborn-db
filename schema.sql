-- Notes on how this schema is designed, mostly for my own reference so I remember to follow
-- them:
--
-- * Where possible I try to describe the meaning of a table with a "membership statement". This
--   will be surrounded in square brackets and will involve references to the columns in curly
--   brackets. When the values for a given row are substituted in place of the column references,
--  the result is what it means for that row to be present in the table.
--
-- * IDs are preferentially textual (not numeric) so that they are meaningful on reading. All this
--   data is essentially static so changes making the ID misleading isn't really a concern. A lot
--   of things have textual IDs already assigned to them by Essentials. They often also have a
--   numeric ID too; we will still store that numeric ID as a unique column in case it proves
--   useful.

-------------------
-- POKÉMON TYPES --
-------------------

-- Move damage classes (physical, special, or status).
create table "damage_class" (
	"name" text primary key
	,"order" integer not null unique
) without rowid;

-- Pokémon types.
create table "type" (
	"id" text primary key
	,"name" text not null unique
	,"code" integer not null unique
	,"damage_class" text not null -- Used by Glitch Field
	,"is_pseudo" integer not null check ("is_pseudo" in (0, 1)) -- So we can ignore the ?? type where
	                                                            -- necessary
	,"icon" blob not null
	,foreign key ("damage_class") references "damage_class" ("name")
) without rowid;

-- [An {attacking_type} move hitting a Pokémon with the single type {defending_type} will
-- have a damage multiplier of {multiplier}.]
create table "type_effect" (
	"attacking_type" text
	,"defending_type" text
	,"multiplier" real check ("multiplier" in (0, 0.5, 2))
	,primary key ("attacking_type", "defending_type")
	,foreign key ("attacking_type") references "type" ("id")
	,foreign key ("defending_type") references "type" ("id")
) without rowid;

create index "type_effect_idx_multiplier" on "type_effect" ("multiplier");

-------------------
-- POKÉMON MOVES --
-------------------

-- Move 'functions', which are just values that determine what additional effects a move has,
-- besides the defaults determined by its other attrbutes (e.g. status effects, stat changes).
-- Each move has exactly one function.
create table `move_function` (
	`code` text primary key,
	`desc` text not null
) without rowid;

-- Values that determine what targets can be selected for a move (e.g. 'any single Pokémon on the
-- field', 'always targets all opponents', 'may target self or ally')
create table `move_target` (
	`code` text primary key,
	`desc` text not null
) without rowid;

-- Moves.
create table `move` (
	`id` text primary key,
	`name` text not null, -- note: not unique because of Hidden Power/Judgement/Multi-Attack
	`code` integer not null unique,
	`damage_class` text not null,
	`type` text not null,
	`power` integer check (`power` >= 0),
	`accuracy` integer check (`accuracy` >= 0 and `accuracy` <= 100), -- null if never misses
	`pp` integer check (`pp` >= 0),
	`target` text not null,
	`priority` integer not null,
	`function` text not null,
	`additional_effect_chance` integer check (`additional_effect_chance` >= 0 and `additional_effect_chance` <= 100), -- null if no additional effect
	`desc` text not null check (`desc` != ''),
	foreign key (`damage_class`) references `damage_class` (`name`),
	foreign key (`type`) references `type` (`id`),
	foreign key (`target`) references `move_target` (`code`),
	foreign key (`function`) references `move_function` (`code`)
);

-- Flags used to indicate binary attributes of moves (e.g. is a contact move, is a biting move,
-- can be reflected by Magic Coat). A move can have many flags; the pivot table is `move_flag_set`.
create table `move_flag` (
	`code` text primary key,
	`desc` text not null
) without rowid;

-- `move` to `move_flag` pivot table.
create table `move_flag_set` (
	`move` text not null,
	`flag` text not null,
	primary key (`move`, `flag`),
	foreign key (`move`) references `move` (`id`),
	foreign key (`flag`) references `move_flag` (`code`)
) without rowid;

-----------
-- ITEMS --
-----------

-- Bag pockets.
create table `pocket` (
	"name" text primary key
	,"code" integer not null unique
) without rowid;

-- Values specifying how an item is used outside of battle---whether it's on a specific Pokémon or
-- not, whether it's reusable, etc.
create table `item_out_battle_usability` (
	`name` text primary key,
	`code` integer not null unique,
	`desc` text not null
) without rowid;

-- Values specifying how an item is used in battle---whether it's on a specific Pokémon or not,
-- whether it's reusable, etc.
create table `item_in_battle_usability` (
	`name` text primary key,
	`code` integer not null unique,
	`desc` text not null
) without rowid;

-- Item types, to more specificity than supplied by the bag pocket (e.g. evolution stone, fossil).
create table "item_type" (
	"name" text primary key,
	"code" integer not null unique
) without rowid;

-- Items.
create table `item` (
	`id` text primary key,
	`name` text not null,
	`code` integer not null unique,
	`pocket` text not null, -- The bag pocket the item is stored in.
	`buy_price` integer not null,
	`desc` text not null check (`desc` != ''),
	`out_battle_usability` text not null,
	`in_battle_usability` text not null,
	`type` text not null,
	foreign key (`pocket`) references `pocket` (`name`),
	unique (`id`, `pocket`),
	foreign key (`out_battle_usability`) references `item_out_battle_usability` (`name`),
	foreign key (`in_battle_usability`) references `item_in_battle_usability` (`name`),
	foreign key (`type`) references `item_type` (`name`)
);

-- Moves taught by TM(X)s.
create table "machine_item" (
	"item" text primary key,
	"pocket" text check ("pocket" = 'TMs & HMs'),
	"type" text not null check ("type" in ('tm', 'tmx')),
	"number" integer not null,
	"move" text not null unique,
	unique ("type", "number"),
	foreign key ("item", "pocket") references "item" ("id", "pocket"),
	foreign key ("move") references "move" ("id")
) without rowid;

----------------------------------
-- POKÉMON AND THEIR ATTRIBUTES --
----------------------------------

-- Pokémon growth rates (these affect how a Pokémon's level is determined from its total EXP
-- gained).
create table "growth_rate" (
	"name" text primary key
	,"pbs_name" text not null unique
	,"order" integer not null unique
	-- The formula is used for calculating the total EXP required to attain each level,
	-- but only for levels greater than 100.
	,"python_formula" text not null 
	,"latex_formula" text not null
) without rowid;

-- [A Pokémon with growth rate {growth_rate} requires exactly {exp} EXP in total (including all the
-- EXP required to attain previous levels) in order to reach level {level}.]
create table "level_exp" (
	"growth_rate" text
	,"level" integer
	,"exp" integer not null
	,primary key ("growth_rate", "level")
	,foreign key ("growth_rate") references "growth_rate" ("name")
);

-- Unenforced constraint: a "level_exp" must exist for each "growth_rate" and each "level" from
-- 0--100.

-- Pokémon habitats (as recorded in the FireRed/LeafGreen Pokédex).
create table "habitat" (
	"name" text primary key
	,"pbs_name" text not null unique
	,"order" integer not null unique
) without rowid;

-- Pokémon (non-form-specific data). Note that all Pokémon have at least one form (a Pokémon with
-- no form differences is one that has only one form).
create table "pokemon" (
	"id" text primary key
	,"name" text not null unique
	,"number" integer not null unique
	,"category" text not null check ("category" != '')
	,"base_exp" integer not null check ("base_exp" >= 0)
	,"growth_rate" text not null
	,"base_friendship" integer not null check ("base_friendship" >= 0 and "base_friendship" <= 255)
	,"male_frequency" integer check ("male_frequency" >= 0 and "male_frequency" <= 1000) -- per 1000, NULL if genderless
	,"hatch_steps" integer not null check ("hatch_steps" >= 0)
	,"habitat" text
	,"color" text not null
	,"evolves_from" text -- The Pokémon it evolves from---there is always at most one such Pokémon.
	,unique ("evolves_from", "id")
	,foreign key ("growth_rate") references "growth_rate" ("name")
	,foreign key ("habitat") references "habitat" ("name")
	,foreign key ("evolves_from") references "pokemon" ("id")
) without rowid;

-- Pokémon egg groups.
create table "egg_group" (
	"name" text primary key
	,"pbs_name" text not null unique
	,"order" integer not null unique
) without rowid;

-- [{egg_group} is one of {pokemon}'s egg groups.]
create table "pokemon_egg_group" (
	"pokemon" text
	,"egg_group" not null
	,primary key ("pokemon", "egg_group")
	,foreign key ("pokemon") references "pokemon" ("id")
	,foreign key ("egg_group") references "egg_group" ("name")
) without rowid;

create index "pokemon_egg_group_idx_egg_group" on "pokemon_egg_group" ("egg_group");

-- Pokémon forms.
create table "pokemon_form" (
	"pokemon" text,
	"name" text,
	"order" integer,
	"wild_always_held_item" text not null, -- if the Pokémon doesn't always hold an item in the
	                                       -- wild, this is set to the dummy item (with ID
	                                       -- 'DUMMY'), which is a bit hacky but it allows us to
	                                       -- set up the right constraint

	                                       -- we should just use a partial unique index instead
	-- catch rate is form-specific soley due to Minior
	"catch_rate" integer not null check ("catch_rate" >= 0 and "catch_rate" <= 255),
	"height" integer not null check ("height" >= 0), -- in centimetres
	"weight" integer not null check ("weight" >= 0), -- in tenths of a kilogram (100g each)			
	"pokedex_entry" text not null,
	"battle_only" integer not null check ("battle_only" in (0, 1)) default 0,
	primary key ("pokemon", "name"),
	unique ("pokemon", "order"),
	unique ("pokemon", "name", "wild_always_held_item"),
	foreign key ("pokemon") references "pokemon" ("id"),
	foreign key ("wild_always_held_item") references "item" ("id")
) without rowid;

-- for each form we have a normal sprite, shiny sprite, back-normal, back-shiny
-- egg, shiny-egg. PULSE forms lack shiny sprites
-- overworld sprites are in Graphics/Characters/pkmn_{internalname}.png
--   some with a number before the extension, not necess related to form
--   (e.g. charizard3.png is Cal riding Charizard)
--   icons in Graphics/Icons/icon{number}, arranged horizontakkky wuth second two shiny
--     and icon{number}egg.png, icon{number}f.png
--     oh, the two are just the two frames---generally second is one pixel lower than first
--     also, egg sprites only for non-evolutions

create table "pokemon_sprite" (
	"pokemon" text,
	"form" text,
	-- icon1/icon2 are the first and second frame for the in-party icons
	"type" text not null check ("type" in ('front', 'back', 'egg', 'icon1', 'icon2', 'egg-icon1', 'egg-icon2')),
	"shiny" integer not null check ("shiny" in (0, 1)),
	"gender" text, -- null if no gender differences
	"sprite" blob not null,
	-- can't make it a PK because gender is nullable
	unique ("pokemon", "form", "type", "shiny", "gender"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("gender") references "gender" ("name")
);

-- Unenforced constraint: each form must have, at least, normal (non-shiny) sprites of front, 
-- back, icon1 and icon2 types.
-- Unenforced constraint: a sprite can only have non-null gender if the linked Pokémon is not 
-- genderless.

-- Pokémon type slots (first, second).
create table "type_slot" ("index" integer primary key) without rowid;

-- Pivot table between `pokemon_form` and `type`, with `type_slot` limiting the number of `type`s
-- per `pokemon_form`.
create table `pokemon_type` (
	`pokemon` text,
	`form` text,
	`index` integer,
	`type` text not null,
	primary key (`pokemon`, `form`, `index`),
	foreign key (`pokemon`, `form`) references `pokemon_form` (`pokemon`, `name`),
	foreign key (`index`) references `type_slot` (`index`),
	foreign key (`type`) references `type` (`id`)
) without rowid;

-- Unenforced constraint: each `pokemon_form` must have at least one related `pokemon_type`.

-- Pokémon abilities.
create table `ability` (
	`id` text primary key,
	`name` text not null unique,
	`code` integer unique not null,
	`desc` text not null
);

-- Pokémon ability slots (first, second, Hidden).
create table `ability_slot` (
	`index` integer primary key,
	`name` text not null unique
) without rowid;

-- Pivot table between `pokemon_form` and `type`, with `ability_slot` limiting the number of
-- `ability`s per `pokemon_form`.
create table "pokemon_ability" (
	"pokemon" text,
	"form" text,
	"index" integer,
	"ability" text not null,
	primary key ("pokemon", "form", "index"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("index") references "ability_slot" ("index"),
	foreign key ("ability") references "ability" ("id")
) without rowid;

-- Unenforced constraint: each `pokemon_form` must have at least one related `pokemon_ability`.

-- Pokémon wild held item rarities (always held, common, uncommon, rare).
create table "wild_held_item_rarity" (
	"name" text primary key,
	"order" integer not null unique,
	"percentage" integer not null unique
) without rowid;

-- Pivot table between `pokemon_form` and `item`, with `wild_held_item_rarity` limiting the number
-- of `items` per "pokemon_form".
create table "wild_held_item" (
	"pokemon" text,
	"form" text,
	"always_held_item" text not null check ("always_held_item" = 'DUMMY'),
	"rarity" text,
	"item" text not null,
	primary key ("pokemon", "form", "rarity"),
	foreign key ("pokemon", "form", "always_held_item") references "pokemon_form" (
		"pokemon", "name", "wild_always_held_item"
	),
	foreign key ("rarity") references "wild_held_item_rarity" ("name"),
	foreign key ("item") references "item" ("id")
) without rowid;

-- The six primary stats (HP, Attack, Defense, Special Attack, Special Defense, Speed).
create table "stat" (
	"id" text primary key,
	"name" text not null unique,
	"order" integer not null
) without rowid;

-- [{pokemon} ({form} form) has a base {stat} value of {value}.]
create table "base_stat" (
	"pokemon" text,
	"form" text,
	"stat" text,
	"value" integer not null check ("value" >= 0 and "value" <= 255),
	primary key ("pokemon", "form", "stat"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("stat") references "stat" ("id")
) without rowid;

-- [{pokemon} ({form} form) yields {value} EVs in {stat} when defeated.]
create table "ev_yield" (
	"pokemon" text,
	"form" text,
	"stat" text,
	"value" integer not null check ("value" >= 1 and "value" <= 3),
	primary key ("pokemon", "form", "stat"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("stat") references "stat" ("id")
) without rowid;

-- Moves learned when a Pokémon reaches a particular level.
create table "level_move" (
	"pokemon" text,
	"form" text,
	"level" integer check ("level" >= 0), -- 0 = move learnt on evolution

	-- when multiple moves are learnt at the same level, this column determines the order in which
	-- they are learnt
	"order" integer not null,

	"move" text not null,
	primary key ("pokemon", "form", "level", "order"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("move") references "move" ("id")
) without rowid;

create index "level_move_idx_move" on "level_move" ("move");

-- Egg moves.
create table "egg_move" (
	"pokemon" text,
	"form" text,
	"move" text not null,
	primary key ("pokemon", "form", "move"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("move") references "move" ("id")
) without rowid;

create index "egg_move_idx_move" on "egg_move" ("move");

-- Moves learnable via TM(X)s.
create table "machine_move" (
	"pokemon" text,
	"form" text,
	"move" text,
	primary key ("pokemon", "form", "move"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("move") references "move" ("id")
) without rowid;

create index "machine_move_idx_move" on "machine_move" ("move");

-- Moves learnable from Move Tutors. (As listed in the tm.txt PBS file. This includes some moves 
-- for which there isn't actually an existing move tutor NPC in-game, so that they are effectively 
-- not learnable.)
create table "tutor_move" (
	"pokemon" text,
	"form" text,
	"move" text,
	primary key ("pokemon", "form", "move"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("move") references "move" ("id")
) without rowid;

create index "tutor_move_idx_move" on "tutor_move" ("move");

create table "move_learn_method" (
	"name" text primary key,
	"order" integer not null unique
) without rowid;

-----------------------------
-- AREAS IN THE GAME WORLD --
-----------------------------

create table "map" (
	"id" integer primary key,
	"name" text not null, -- name from the MapInfos.rxdata file (appears to reflect in-game name)
	"pbs_name" text, -- name from the PBS metadata.txt file
	"desc" text, -- hand-written description by me (actually absent for every map because i can't be bothered writing them)
	"tileset" text,
	"width" integer, "height" integer, -- in terms of tiles---technically derivable from the map data but the denormalization is convenient
	"parent_id" integer, -- from MapInfos.rxdata, no in-game meaning but useful for organisation
	"order" integer not null unique, -- from MapInfos.rxdata, no in-game meaning AFAIK
	"expanded" integer not null check (`expanded` in (0, 1)), -- refers to transient UI state in RPG Maker XP so not very important
	"scroll_x" integer not null, -- another transient UI state thing
	"scroll_y" integer not null, -- another transient UI state thing
	"region_id" integer, -- reborn only has one region so this one's a bit moot
	"x" integer, "y" integer, -- x and y coordinates of the area within the region's Town Map
	-- whether there's a pop-up showing the map name when the player enters
	"has_location_signpost" integer not null check ("has_location_signpost" in (0, 1)),
	"battle_backdrop" text,
	"outdoor" integer not null check ("outdoor" in (0, 1)),
	"bicycle_usable" integer not null check ("bicycle_usable" in (0, 1)),
	"bicycle_required" integer not null check ("bicycle_required" in (0, 1)),
	"flashable" integer not null check ("flashable" in (0, 1)),
	"sets_teleport_map" integer, -- teleport takes you here.
	"sets_teleport_x" integer, "sets_teleport_y" integer, -- tile coordinates
	"underwater_map" integer, -- using dive takes you here
	"weather" text, "weather_chance" integer,
	"in_safari_zone" integer not null check ("in_safari_zone" in (0, 1)),
	"bicycle_music" text not null,
	"surf_music" text not null,
	"wild_battle_music" text not null,
	"wild_win_music" text not null,
	"trainer_battle_music" text not null,
	"trainer_win_music" text not null,
	"data" blob not null, -- the map tile data
	foreign key ("tileset") references "tileset" ("name"),
	foreign key ("parent_id") references "map" ("id"),
	foreign key ("sets_teleport_map") references "map" ("id"),
	foreign key ("underwater_map") references "map" ("id")
);

create index "map_idx_parent_id" on "map" ("parent_id");

create table "map_bgm" (
	"map" integer primary key,
	"file" text not null,
	"volume" integer not null,
	"pitch" integer not null,
	foreign key ("map") references "map" ("id")
);

create table "map_bgs" (
	"map" integer primary key,
	"file" text not null,
	"volume" integer not null,
	"pitch" integer not null,
	foreign key ("map") references "map" ("id")
);

create table "field_effect" (
	"name" text primary key
	,"code" integer unique not null
	,"backdrop" text unique not null
) without rowid;

create table "tileset_file" (
	"name" text primary key,
	"content" blob not null
) without rowid;

create table "panorama" (
	"name" text primary key,
	"image" blob not null
) without rowid;

create table "tileset" (
	"name" text primary key,
	"id" integer not null unique,
	"file" text not null,
	"panorama" text,
	-- ignore panorama hue, fog settings, battleback settings
	-- since these are the same for all tilesets in reborn
	"passages" blob not null,
	"priorities" blob not null,
	"terrain_tags" blob not null,
	foreign key ("file") references "tileset_file" ("name"),
	foreign key ("panorama") references "panorama" ("name")
) without rowid;

create table "autotile" (
	"name" text primary key,
	"image" blob not null
) without rowid;

create table "tileset_autotile" (
	"tileset" text,
	"index" integer check ("index" >= 0 and "index" < 7),
	"autotile" text,
	primary key ("tileset", "index"),
	foreign key ("tileset") references "tileset" ("name"),
	foreign key ("autotile") references "autotile" ("name")
) without rowid;

-------------------------------
-- POKÉMON EVOLUTION METHODS --
-------------------------------

-- Times of day (day, night or dusk---note that dusk is a sub-period of day).
create table "time_of_day" (
	"name" text primary key
	,"desc" text not null
	,"order" integer not null unique
	,"range_desc" text not null
) without rowid;

-- Pokémon genders.
create table "gender" ("name" text primary key, "code" integer not null unique) without rowid;

-- Weathers that may occur in the overworld.
create table "weather" (
	"name" text primary key
	,"desc" text not null
	,"order" integer not null unique
) without rowid;

-- The 'base method' for a evolving a Pokémon--either levelling up, using an item on it, or trading
-- it. Further requirements are added to these base methods to encode a full evolution method.
create table "evolution_base_method" ("name" text primary key) without rowid;

create table "evolution_method" (
	"id" text primary key,
	"pbs_name" text,
	"base_method" text not null,
	unique ("id", "base_method"),
	foreign key ("base_method") references "evolution_base_method" ("name")
) without rowid;

create table "evolution_requirement_kind" ("name" text primary key) without rowid;

-- Evolution requirements. Each requirement represents an atomic proposition; they can be ANDed
-- together by adding them to the same `evolution_method`, or they can be ORed together by adding
-- them to separate `evolution_methods`. (That means the overall evolution condition has to be
-- expressed in conjunctive normal form, but that works well enough.)
--
-- Depending on the kind of requirement, it may require arguments, which are encoded in a table
-- specific to the kind. The argument values are set up so that it would be impossible or
-- meaningless to satisfy two requirements of the same kind (hence we can use (`method`, `kind`) as
-- the primary key for `evolution_requirement`).
create table `evolution_requirement` (
	`method` integer,
	`kind` text,
	primary key (`method`, `kind`),
	foreign key (`method`) references `evolution_method` (`id`)
) without rowid;

-- The Pokémon must have reached a certain level.
create table `evolution_requirement_level` (
	`method` integer primary key,
	`kind` text check (`kind` = 'level'),
	`level` integer not null check (`level` >= 0),
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`)
) without rowid;

-- A specific item must be used on the Pokémon.
create table `evolution_requirement_item` (
	`method` integer primary key,
	`base_method` text not null check (`base_method` = 'item'),
	`kind` text check (`kind` = 'item'),
	`item` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`method`, `base_method`) references `evolution_method` (`id`, `base_method`),
	foreign key (`item`) references `item` (`id`)
) without rowid;

-- Unenforced constraint: the `evolution_method` related to an `evolution_requirement_item` must
-- have 'item' as its `base_method`.

-- The Pokémon must hold a specific item.
create table `evolution_requirement_held_item` (
	`method` integer primary key,
	`kind` text check (`kind` = 'held_item'),
	`item` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`item`) references `item` (`id`)
) without rowid;

-- The evolution must take place at a specific time of day.
create table `evolution_requirement_time` (
	`method` integer primary key,
	`kind` text check (`kind` = 'time'),
	`time` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`time`) references `time_of_day` (`name`)
) without rowid;

-- The Pokémon must have two stats in a certain order relation.
create table `evolution_requirement_stat_cmp` (
	`method` integer primary key,
	`kind` text check (`kind` = 'stat_cmp'),
	`stat1` text not null,
	`stat2` text not null,
	`operator` text not null check (`operator` in ('<', '=', '>')),
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`stat1`) references `stat` (`id`),
	foreign key (`stat2`) references `stat` (`id`)
) without rowid;

create table `evolution_requirement_coin_flip` (
	`method` integer primary key,
	`kind` text check (`kind` = 'coin_flip'),
	`value` integer not null check (`value` in (0, 1)),
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`)
) without rowid;

-- The Pokémon must have a certain gender.
create table `evolution_requirement_gender` (
	`method` integer primary key,
	`kind` text check (`kind` = 'gender'),
	`gender` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`gender`) references `gender` (`name`)
) without rowid;

-- The Pokémon must have a certain Pokémon as a teammate.
create table `evolution_requirement_teammate` (
	`method` integer primary key,
	`kind` text check (`kind` = 'teammate'),
	`pokemon` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`pokemon`) references `pokemon` (`id`)
) without rowid;

-- The Pokémon must know a certain move.
create table `evolution_requirement_move` (
	`method` integer primary key,
	`kind` text check (`kind` = 'move'),
	`move` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`move`) references `move` (`id`)
) without rowid;

-- The evolution must take place within a certain map.
create table `evolution_requirement_map` (
	`method` integer primary key,
	`kind` text check (`kind` = 'map'),
	`map` integer not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`map`) references `map` (`id`)
) without rowid;

-- The Pokémon must be traded with a certain other Pokémon.
create table `evolution_requirement_trademate` (
	`method` integer primary key,
	`base_method` text not null check (`base_method` = 'trade'),
	`kind` text check (`kind` = 'trademate'),
	`pokemon` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`method`, `base_method`) references `evolution_method` (`id`, `base_method`),
	foreign key (`pokemon`) references `pokemon` (`id`)
) without rowid;

-- The Pokémon must have a Pokémon of a certain type as a teammate.
create table `evolution_requirement_teammate_type` (
	`method` integer primary key,
	`kind` text check (`kind` = 'teammate_type'),
	`type` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`type`) references `type` (`id`)
) without rowid;

-- The Pokémon must know a move of a certain type.
create table `evolution_requirement_move_type` (
	`method` integer primary key,
	`kind` text check (`kind` = 'move_type'),
	`type` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`type`) references `type` (`id`)
) without rowid;

-- The evolution must take place at a time and place where the overworld weather is of a certain type.
create table `evolution_requirement_weather` (
	"method" integer primary key,
	`kind` text check (`kind` = 'weather'),
	`weather` text not null,
	foreign key (`method`, `kind`) references `evolution_requirement` (`method`, `kind`),
	foreign key (`weather`) references `weather` (`name`)
) without rowid;

-- Determines the method for evolving one Pokémon into another.
create table `pokemon_evolution_method` (
	`from` text,
	`from_form` text,
	`to` text not null,
	`to_form` text not null,
	`method` integer,
	primary key (`from`, `from_form`, `method`),
	foreign key (`from`, `to`) references `pokemon` (`evolves_from`, `id`)
	foreign key (`from`, `from_form`) references `pokemon_form` (`pokemon`, `name`),
	foreign key (`to`, `to_form`) references `pokemon_form` (`pokemon`, `name`),
	foreign key (`method`) references `evolution_method` (`id`)
) without rowid;

create index "pokemon_evolution_method_from_to_idx" on "pokemon_evolution_method" (
	"from", "to", "from_form", "to_form"
);

--------------------------------------
-- ATTRIBUTES OF INDIVIDUAL POKÉMON --
--------------------------------------

-- Pokémon natures.
create table `nature` (
	`increased_stat` text,
	`decreased_stat` text,
	`id` text not null unique,
	`name` text not null unique,
	"code" integer not null unique,
	primary key (`increased_stat`, `decreased_stat`),
	foreign key (`increased_stat`) references `stat` (`id`),
	foreign key (`decreased_stat`) references `stat` (`id`)
) without rowid;

-- Pokémon move slots (first, second, third, fourth).
create table "move_slot" ("index" integer primary key) without rowid;

----------------------
-- POKÉMON TRAINERS --
----------------------

create table "trainer_type" (
	"id" text primary key,
	"name" text not null,
	"code" integer not null unique,
	"base_prize" integer not null check ("base_prize" >= 0 and "base_prize" <= 255),
	"bg_music" text,
	"win_music" text,
	"intro_music" text,
	"gender" text,
	"skill" integer not null check ("skill" >= 0 and "skill" <= 255),
	"battle_sprite" blob,
	"battle_back_sprite" blob,
	foreign key ("gender") references "gender" ("name")
) without rowid;

create table "trainer" (
	"type" text,
	"name" text,
	"party_id" integer,
	"pbs_order" integer not null unique,
	primary key ("type", "name", "party_id"),
	foreign key ("type") references "trainer_type" ("id")
) without rowid;

create table "trainer_item" (
	"trainer_type" text,
	"trainer_name" text,
	"party_id" integer,
	"item" text,
	"quantity" integer not null check ("quantity" >= 0),
	primary key ("trainer_type", "trainer_name", "party_id", "item"),
	foreign key ("trainer_type", "trainer_name", "party_id") references "trainer" ("type", "name", "party_id"),
	foreign key ("item") references "item" ("id")
) without rowid;

create table "trainer_pokemon" (
	"trainer_type" text,
	"trainer_name" text,
	"party_id" integer,
	"index" integer check ("index" >= 0),
	"pokemon" text not null,
	"form" text,
	"nickname" text,
	"gender" text, -- null = determined by personal id, i.e. effectively random per battle
	"level" integer not null check ("level" >= 0),
	"ability" integer, -- null = determined by personal id, i.e. effectively random per battle
	                   -- we also use -1 for determined by personal id, but never hidden
	"nature" text, -- null = determined by personal id, i.e. effectively random per battle
	"item" text, 
	"friendship" integer not null check ("friendship" >= 0 and "friendship" <= 255),
	"shiny" integer not null check ("shiny" in (0, 1)),
	"shadow" integer not null check ("shadow" in (0, 1)),
	"ball" integer not null, -- references a "Ball number", whatever that is
	"hidden_power" integer, -- seems to not be used?
	-- huh, just looking at the code, it seems like hidden power might always depend on the
	-- personal ID (i.e. be randomized per battle)
	primary key ("trainer_type", "trainer_name", "party_id", "index"),
	foreign key ("trainer_type", "trainer_name", "party_id") references "trainer" ("type", "name", "party_id"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("gender") references "gender" ("name"),
	-- unfortunately there can be no equivalent of this FK now that abilities are in a separate table
	-- foreign key ("pokemon", "form", "ability") references "pokemon_ability" ("pokemon", "form", "index"),
	foreign key ("nature") references "nature" ("id"),
	foreign key ("item") references "item" ("id")
) without rowid;

-- this table lists all the possible abilities a trainer pokemon can have
-- some have a specific ability, others can have any of their three abils (depending
-- on personal id), some can only have first/second but not hidden
-- also arcade star carol's meowstic, which has variable gender and hence form, will choose from a different
-- set of abilities accordingly!
create table "trainer_pokemon_ability" (
	"trainer_type" text,
	"trainer_name" text,
	"party_id" integer,
	"pokemon_index" integer check ("pokemon_index" >= 0),
	"ability" integer not null,
	primary key ("trainer_type", "trainer_name", "party_id", "pokemon_index", "ability"),
	foreign key ("trainer_type", "trainer_name", "party_id") references "trainer" ("type", "name", "party_id"),
	foreign key ("ability") references "ability_slot" ("index")
) without rowid;

create table "trainer_pokemon_move" (
	"trainer_type" text,
	"trainer_name" text,
	"party_id" integer,
	"pokemon_index" integer check ("pokemon_index" >= 0),
	"move_index" integer,
	"move" text not null,
	primary key ("trainer_type", "trainer_name", "party_id", "pokemon_index", "move_index"),
	foreign key ("trainer_type", "trainer_name", "party_id", "pokemon_index") references "trainer_pokemon" ("trainer_type", "trainer_name", "party_id", "index"),
	foreign key ("move_index") references "move_slot" ("index"),
	foreign key ("move") references "move" ("id")
) without rowid;

create table "trainer_pokemon_ev" (
	"trainer_type" text,
	"trainer_name" text,
	"party_id" integer,
	"pokemon_index" integer check ("pokemon_index" >= 0),
	"stat" text not null,
	"value" integer not null check ("value" >= 0),
	primary key ("trainer_type", "trainer_name", "party_id", "pokemon_index", "stat"),
	foreign key ("trainer_type", "trainer_name", "party_id", "pokemon_index") references "trainer_pokemon" ("trainer_type", "trainer_name", "party_id", "index"),
	foreign key ("stat") references "stat" ("id")
) without rowid;

create table "trainer_pokemon_iv" (
	"trainer_type" text,
	"trainer_name" text,
	"party_id" integer,
	"pokemon_index" integer check ("pokemon_index" >= 0),
	"stat" text not null,
	"value" integer not null check ("value" >= 0 and "value" <= 31),
	primary key ("trainer_type", "trainer_name", "party_id", "pokemon_index", "stat"),
	foreign key ("trainer_type", "trainer_name", "party_id", "pokemon_index") references "trainer_pokemon" ("trainer_type", "trainer_name", "party_id", "index"),
	foreign key ("stat") references "stat" ("id")
) without rowid;

create table "trainer_list" (
	"id" integer primary key
	,"trainers_file" text not null
	,"pokemon_file" text not null
	,"is_default" integer not null check ("is_default" in (0, 1))
);

create table "battle_facility_trainer" (
	"list" integer
	,"index" integer
	,"type" text not null
	,"name" text
	,"begin_speech" text not null
	,"lose_speech" text not null
	,"win_speech" text not null
	,primary key ("list", "index")
	,foreign key ("list") references "trainer_list" ("id")
	,foreign key ("type") references "trainer_type" ("id")
	-- ,unique ("type", "name")
) without rowid;

create table "battle_facility_trainer_pokemon" (
	"list" integer
	,"trainer_index" integer
	,"pokemon_index" integer
	,"pokemon" text
	,primary key ("list", "trainer_index", "pokemon_index")
	,foreign key ("list", "trainer_index") references "battle_facility_trainer" ("list", "index")
	,foreign key ("pokemon") references "pokemon" ("id")
) without rowid;

-- Pokémon sets for use in battle facilities.
-- Depends on "pokemon_form", "item", "nature" and "ability_slot".
create table "battle_facility_set" (
	"list" integer
	,"index" integer
	,"pokemon" text not null
	,"form" text not null
	,"ability" integer not null
	,"nature" text not null
	,"item" text
	,primary key ("list", "index")
	,foreign key ("list") references "trainer_list" ("id")
	,foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name")
	,foreign key ("pokemon", "form", "ability") references "pokemon_ability" ("pokemon", "form", "index")
	,foreign key ("nature") references "nature" ("id")
	,foreign key ("item") references "item" ("id")
) without rowid;

-- Determines what move a Pokémon set from "battle_facility_set" in a particular slot.
-- Depends on "battle_facility_set", "move_slot" and "move".
create table "battle_facility_set_move" (
	"list" integer
	,"set_index" integer
	,"move_index" integer
	,"move" text not null
	,primary key ("list", "set_index", "move_index")
	,foreign key ("list", "set_index") references "battle_facility_set" ("list", "index")
	,foreign key ("move_index") references "move_slot" ("index")
	,foreign key ("move") references "move" ("id")
) without rowid;

-- Unenforced constraint: each "battle_facility_set" must have at least one related
-- "battle_facility_set_move".

-- Stats that have EVs in them, for Pokémon sets from `battle_facility_set`.
-- (The amounts are not specified; the Pokémon's 510 available EVs will be evenly distributed
-- between the stats that are to have EVs in them as designated by this table.)
-- Depends on "battle_facility_set", "stat".
create table "battle_facility_set_ev_stat" (
	"list" integer
	,"set_index" integer
	,"stat" text
	,primary key ("list", "set_index", "stat")
	,foreign key ("list", "set_index") references "battle_facility_set" ("list", "index")
	,foreign key ("stat") references "stat" ("id")
) without rowid;

------------
-- EVENTS --
------------

create table "game_switch" ("id" integer primary key, "name" text not null);
create table "game_variable" ("id" integer primary key, "name" text not null);

create table "direction" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "direction" ("name", "code")
values
('none', 0),
('down', 2),
('left', 4),
('right', 6),
('up', 8);

create table "move_type" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "move_type" ("name", "code")
values
('fixed', 0),
('random', 1),
('approach', 2),
('custom', 3);

create table "move_speed" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "move_speed" ("name", "code")
values
('slowest', 1), -- the superior unit system
('slower', 2),
('slow', 3),
('fast', 4),
('faster', 5),
('fastest', 6);

create table "move_frequency" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "move_frequency" ("name", "code")
values
('lowest', 1),
('lower', 2),
('low', 3),
('high', 4),
('higher', 5),
('highest', 6);

create table "common_event_trigger" ("name" text primary key, "code" integer not null unique) without rowid;
insert into "common_event_trigger" ("name", "code")
values
('none', 0),
('autorun', 1),
('parallel', 2);

create table "character_file" (
	"name" text primary key,
	"content" blob not null
) without rowid;

create table "character_image" (
	"file" text,
	"direction" text check ("direction" != 'none'),
	"pattern" integer check ("pattern" between 0 and 3),
	"content" blob not null,
	primary key ("file", "direction", "pattern"),
	foreign key ("file") references "character_file" ("name"),
	foreign key ("direction") references "direction" ("name")
) without rowid;

------------------------
-- POKÉMON ENCOUNTERS --
------------------------

-- The three types of terrain on a map, which are distinguished with respect to encounter rates
-- (grass, cave and water).
create table "terrain" ("name" text primary key, "order" integer not null unique) without rowid;

-- The chance of encountering a wild Pokémon per step (as a fraction of 250), for each map and
-- terrain type. This is for any Pokémon; the chances of encountering each specific Pokémon,
-- conditional on an encounter having started already, are given in `pokemon_encounter_rate`.
-- Depends on `map` and `terrain`.
create table `map_encounter_rate` (
	`map` integer,
	`terrain` text not null, 
	`rate` integer not null check (`rate` >= 0 and `rate` <= 250),
	primary key (`map`, `terrain`),
	foreign key (`map`) references `map` (`id`),
	foreign key (`terrain`) references `terrain` (`name`)
) without rowid;

-- Unenforced constraint: there must be a `map_encounter_rate` row for each `map` and each of the
-- three terrain types (grass, cave and water).

-- The various methods of initiating an encounter (e.g. walking on the ground, using the Old Rod,
-- headbutting a tree).
create table "encounter_method" (
	"name" text primary key,
	"order" integer not null unique,
	"desc" text not null
) without rowid;

-- The chance of encountering a given wild Pokémon, given that an encounter has started, for each
-- map, encounter method and level.
-- Depends on `map`, `encounter_method` and `pokemon_form`.
create table "pokemon_encounter_rate" (
	"map" integer,
	"method" text,
	"pokemon" text,
	"form" text, -- may be null if form is not determined by the area
	"level" integer,
	"rate" text check (is_frac("rate")) collate "frac",
	-- this should be the PK but since form is nullable, SQL won't let us do it
	unique ("map", "method", "pokemon", "form", "level"),
	foreign key ("map") references "map" ("id"),
	foreign key ("method") references "encounter_method" ("name"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name")
);

create index "pokemon_encounter_rate_idx" on "pokemon_encounter_rate" (
	"map", "method", "pokemon", "form", "rate" collate "frac" desc
);

-- Verbal notes to explain how an encounter's form is determined, if not by area.
create table "pokemon_encounter_form_note" (
	"pokemon" text
	,"note" text not null
	,primary key ("pokemon")
	,foreign key ("pokemon") references "pokemon" ("id")
) without rowid;

create table if not exists "event_encounter_type" ("name" text primary key) without rowid;
insert into "event_encounter_type" ("name") values
('battle'),
('gift'),
('trade');

create table if not exists "event_encounter" (
	"id" integer primary key,
	"start_event_command" integer not null,
	"end_event_command" integer not null,
	"pokemon" text not null,
	"form" text,
	"level" integer, -- 0 for egg
	"type" text not null,
	"nickname" text,
	"hp" integer,
	"gender" text,
	"held_item" text,
	"friendship" integer,
	"ability" integer,
	"move_preference" text,
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("type") references "event_encounter_type" ("name"),
	foreign key ("gender") references "gender" ("name"),
	foreign key ("held_item") references "item" ("id"),
	foreign key ("ability") references "ability_slot" ("index"),
	foreign key ("move_preference") references "move" ("id")
);

-- Verbal notes to explain how an event encounter's form is determined.
create table if not exists "event_encounter_form_note" (
	"encounter" integer primary key
	,"note" text not null
	,foreign key ("encounter") references "event_encounter" ("id")
);

create table if not exists "event_encounter_ot" (
	"encounter" integer primary key,
	"ot" text not null,
	"trainer_id" text,
	foreign key ("encounter") references "event_encounter" ("id")
);

-- Each event encounter is associated with zero or more "extra move sets", each of which consists of
-- a set of moves. When the encounter occurs, one of the extra move sets is randomly chosen, and the
-- moves from that set are added to the encountered Pokémon's move set.
create table if not exists "event_encounter_extra_move_set" (
	"id" integer primary key,
	"encounter" integer not null,
	foreign key ("encounter") references "event_encounter" ("id")
);

create table if not exists "event_encounter_move" (
	"set" integer,
	"move" text not null,
	"index" integer,
	primary key ("set", "index"),
	foreign key ("set") references "event_encounter_extra_move_set" ("id"),
	foreign key ("move") references "move" ("id"),
	foreign key ("index") references "move_slot" ("index")
);

create table if not exists "event_encounter_iv" (
	"encounter" integer,
	"stat" text,
	"value" integer not null,
	primary key ("encounter", "stat"),
	foreign key ("encounter") references "event_encounter" ("id"),
	foreign key ("stat") references "stat" ("id")
) without rowid;

create table if not exists "encounter_common_event" (
	"encounter" integer primary key,
	"event" integer not null,
	foreign key ("encounter") references "event_encounter" ("id"),
	foreign key ("event") references "common_event" ("id")
);

create table if not exists "encounter_map_event" (
	"encounter" integer primary key,
	"map" integer not null,
	"event" integer not null,
	"event_page" integer not null,
	foreign key ("encounter") references "event_encounter" ("id"),
	foreign key ("map") references "map" ("id")
);

create table "roam_path" (
	"from_map" integer,
	"to_map" integer,
	primary key ("from_map", "to_map"),
	foreign key ("from_map") references "map" ("id"),
	foreign key ("to_map") references "to" ("id")
) without rowid;

create table "roam_type" (
	"name" text primary key,
	"order" integer not null unique,
	"desc" text not null
) without rowid;

insert into "roam_type" ("name", "order", "desc")
values
('Any', 0, 'Encountered when walking in grass, walking in a cave, or surfing.'),
('Ground', 1, 'Encountered when walking in grass or a cave.'),
('Surfing', 2, 'Encountered when surfing.'),
('Fishing', 3, 'Encountered when fishing.'),
('Surfing or fishing', 4, 'Encountered when surfing or fishing.');

create table "roam_type_encounter_method" (
	"roam_type" text,
	"method" text,
	primary key ("roam_type", "method"),
	foreign key ("roam_type") references "roam_type" ("name"),
	foreign key ("method") references "encounter_method" ("name")
);

create table "roamer" (
	"id" integer primary key,
	"pokemon" text not null,
	"level" integer not null,
	"type" text not null,
	"graphic" text not null,
	"switch" integer,
	"bgm" text,
	foreign key ("pokemon") references "pokemon" ("id"),
	foreign key ("type") references "roam_type" ("name"),
	foreign key ("switch") references "game_switch" ("id")
) without rowid;

create table "fossil" (
	"item" text,
	"pokemon" text,
	primary key ("item", "pokemon"),
	foreign key ("item") references "item" ("id"),
	foreign key ("pokemon") references "pokemon" ("id")
) without rowid;

-----------------
-- THEME TEAMS --
-----------------

create table "theme_team" (
	"trainer_id" integer,
	"trainer_name" text not null,
	"team_name" text not null,
	"party" integer,
	"field_effect" integer not null,
	"is_double" integer not null check ("is_double" in (0, 1)),
	primary key ("trainer_id", "party"),
	unique ("trainer_name", "team_name"),
	foreign key ("field_effect") references "field_effect" ("code")
) without rowid;

create table "elite_4_challenger" (
	"theme_team_trainer_id" integer primary key,
	"type" text,
	"pre_battle_speech" text not null,
	"end_speech" text not null,
	"post_battle_speech" text not null,
	"is_double" integer not null check ("is_double" in (0, 1)),
	"switch_required" integer not null,
	"character_file" text not null,
	unique ("type"),
	foreign key ("theme_team_trainer_id") references "theme_team" ("trainer_id"),
	foreign key ("type") references "trainer_type" ("id"),
	foreign key ("switch_required") references "game_switch" ("id"),
	foreign key ("character_file") references "character_file" ("name")
)