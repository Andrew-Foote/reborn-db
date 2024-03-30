---------------------------------------------------------------------------------------------------
-- Breeding
---------------------------------------------------------------------------------------------------

-- The Pokémon {male} and {female} are gender counterparts of each other, in that an egg laid by
-- a member of either's evolutionary family may hatch into either one, with a 50% chance for each
create table "gender_counterpart" (
	"male" text primary key,
	"female" text not null unique,
	foreign key ("male") references "pokemon" ("id"),
	foreign key ("female") references "pokemon" ("id")
) without rowid;

insert into "gender_counterpart" ("male", "female")
values
('NIDORANmA', 'NIDORANfE'),
('VOLBEAT', 'ILLUMISE');

-- Eggs produced by {pokemon} hatch into the (assumed unique) Stage 1 evolution in the evolutionary
-- family, rather than the basic form, unless either parent holds {item}
create table "incense" (
	"item" text primary key,
	"pokemon" text not null unique,
	foreign key ("item") references "item" ("id"),
	foreign key ("pokemon") references "pokemon" ("id")
) without rowid;

insert into "incense" ("item", "pokemon")
values
('SEAINCENSE', 'AZURILL'),
('LAXINCENSE', 'WYNAUT'),
('ROSEINCENSE', 'BUDEW'),
('PUREINCENSE', 'CHIMECHO'),
('ROCKINCENSE', 'BONSLY'),
('ODDINCENSE', 'MIMEJR'),
('LUCKINCENSE', 'HAPPINY'),
('WAVEINCENSE', 'MANTYKE'),
('FULLINCENSE', 'MUNCHLAX');

create table "anomalous_baby" (
	"adult" text
	,"adult_form" text
	,"baby" text
	,"baby_form" text
	,primary key ("adult", "adult_form")
	,foreign key ("adult", "adult_form") references "pokemon_form" ("pokemon", "name")
	,foreign key ("baby", "baby_form") references "pokemon_form" ("pokemon", "name")
) without rowid;

insert into "anomalous_baby"
select 'MANAPHY', '', 'PHIONE', ''
union
select 'ROTOM', "form"."name", 'ROTOM', 'Normal'
from "pokemon_form" as "form"
where "form"."pokemon" = 'ROTOM' and "form"."name" != 'Normal';

-- An egg produced by a Pokémon of species {pokemon} in its {form} form which is holding/not
-- holding (as per {incense}) its associated incense will hatch into a Pokémon of specie
-- {baby_pokemon} in its {baby_form} form with probability {probability}.
create table "baby" (
	"adult" text
	,"adult_form" text
	,"incense" text check ("incense" in ('holding', 'not-holding', 'na'))
	,"baby" text
	,"baby_form" text
	,"probability" real check ("probability" > 0.0 and "probability" <= 1.0)
	,primary key ("adult", "adult_form", "incense", "baby", "baby_form")
	,foreign key ("adult", "adult_form") references "pokemon_form" ("pokemon", "name")
	,foreign key ("baby", "baby_form") references "pokemon_form" ("pokemon", "name")
) without rowid;

-- this is a materialized view basically
insert into "baby"
select
	"from_baby"."to", "from_baby"."to_form", 'na',
	"from_baby"."from", "from_baby"."from_form", 1.0
from "evolution_trcl" as "from_baby"
left join "evolution" as "to_baby" on (
	"to_baby"."to" = "from_baby"."from" and "to_baby"."to_form" = "from_baby"."from_form"
)
left join "pokemon_egg_group" on (
	"pokemon_egg_group"."pokemon" = "from_baby"."to"
	and "pokemon_egg_group"."egg_group" in ('No Eggs Discovered', 'Ditto')
)
where "to_baby"."from" is null and "pokemon_egg_group"."egg_group" is null;

update "baby" set "probability" = 0.5
where "baby"."baby" in (
	select "male" from "gender_counterpart" union select "female" from "gender_counterpart"
);

-- this assumes Pokémon with gender counterparts don't have multiple forms
insert into "baby" ("adult", "adult_form", "incense", "baby", "baby_form", "probability")
select "adult", '', 'na', "counterpart"."second", '', 0.5
from "baby"
join (
	select "male" as "first", "female" as "second" from "gender_counterpart"
	union
	select "female" as "first", "male" as "second" from "gender_counterpart"
) as "counterpart" on "counterpart"."first" = "baby"."baby";

update "baby" set "incense" = 'holding'
where exists (select 1 from "incense" where "incense"."pokemon" = "baby"."baby");

insert into "baby" ("adult", "adult_form", "incense", "baby", "baby_form", "probability")
select
	"baby"."adult", "baby"."adult_form", 'not-holding',
	"evolution"."to", "evolution"."to_form", "baby"."probability"
from "baby"
join "incense" on "incense"."pokemon" = "baby"."baby"
join "evolution" on (
	"evolution"."from" = "baby"."baby" and "evolution"."from_form" = "baby"."baby_form"
);


/*update "baby" set ("baby", "baby_form") = (
	select "anomaly"."baby", "anomaly"."baby_form" from "anomalous_baby" as "anomaly"
	where "anomaly"."adult" = "baby"."adult" and "anomaly"."adult_form" = "baby"."adult_form"
)
where exists (
	select 1 from "anomalous_baby" as "anomaly"
	where "anomaly"."adult" = "baby"."adult" and "anomaly"."adult_form" = "baby"."adult_form"
);*/


update "baby"
set "baby" = "anomaly"."baby", "baby_form" = "anomaly"."baby_form"
from "anomalous_baby" as "anomaly"
where "anomaly"."adult" = "baby"."adult" and "anomaly"."adult_form" = "baby"."adult_form";

---------------------------------------------------------------------------------------------------
-- Mega Evolution
---------------------------------------------------------------------------------------------------

-- A Pokémon of species {pokemon} may Mega Evolve into its {form} form iff it is holding {item}.
create table "mega_evolution_item" (
	"pokemon" text
	,"form" text
	,"item" text not null unique
	,primary key ("pokemon", "form")
	,foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name")
	,foreign key ("item") references "item" ("id")
) without rowid;

insert into "mega_evolution_item" ("pokemon", "form", "item")
values
('VENUSAUR', 'Mega', 'VENUSAURITE'),
('CHARIZARD', 'Mega X', 'CHARIZARDITEX'),
('CHARIZARD', 'Mega Y', 'CHARIZARDITEY'),
('BLASTOISE', 'Mega', 'BLASTOISINITE'),
('BEEDRILL', 'Mega', 'BEEDRILLITE'),
('PIDGEOT', 'Mega', 'PIDGEOTITE'),
('ALAKAZAM', 'Mega', 'ALAKAZITE'),
('GENGAR', 'Mega', 'GENGARITE'),
('SLOWBRO', 'Mega', 'SLOWBRONITE'),
('KANGASKHAN', 'Mega', 'KANGASKHANITE'),
('PINSIR', 'Mega', 'PINSIRITE'),
('GYARADOS', 'Mega', 'GYARADOSITE'),
('AERODACTYL', 'Mega', 'AERODACTYLITE'),
('MEWTWO', 'Mega X', 'MEWTWONITEX'),
('MEWTWO', 'Mega Y', 'MEWTWONITEY'),
('AMPHAROS', 'Mega', 'AMPHAROSITE'),
('STEELIX', 'Mega', 'STEELIXITE'),
('SCIZOR', 'Mega', 'SCIZORITE'),
('HOUNDOOM', 'Mega', 'HOUNDOOMINITE'),
('HERACROSS', 'Mega', 'HERACRONITE'),
('TYRANITAR', 'Mega', 'TYRANITARITE'),
('SCEPTILE', 'Mega', 'SCEPTILITE'),
('BLAZIKEN', 'Mega', 'BLAZIKENITE'),
('SWAMPERT', 'Mega', 'SWAMPERTITE'),
('GARDEVOIR', 'Mega', 'GARDEVOIRITE'),
('AGGRON', 'Mega', 'AGGRONITE'),
('SABLEYE', 'Mega', 'SABLENITE'),
('MAWILE', 'Mega', 'MAWILITE'),
('MANECTRIC', 'Mega', 'MANECTITE'),
('ALTARIA', 'Mega', 'ALTARIANITE'),
('CAMERUPT', 'Mega', 'CAMERUPTITE'),
('SHARPEDO', 'Mega', 'SHARPEDONITE'),
('ABSOL', 'Mega', 'ABSOLITE'),
('MEDICHAM', 'Mega', 'MEDICHAMITE'),
('BANETTE', 'Mega', 'BANETTITE'),
('GLALIE', 'Mega', 'GLALITITE'),
('SALAMENCE', 'Mega', 'SALAMENCITE'),
('METAGROSS', 'Mega', 'METAGROSSITE'),
('LATIAS', 'Mega', 'LATIASITE'),
('LATIOS', 'Mega', 'LATIOSITE'),
('LOPUNNY', 'Mega', 'LOPUNNITE'),
('GARCHOMP', 'Mega', 'GARCHOMPITE'),
('LUCARIO', 'Mega', 'LUCARIONITE'),
('ABOMASNOW', 'Mega', 'ABOMASITE'),
('GALLADE', 'Mega', 'GALLADITE'),
('AUDINO', 'Mega', 'AUDINITE'),
('DIANCIE', 'Mega', 'DIANCITE');

-- A Pokémon of species {pokemon} may Mega Evolve into its {form} form iff it knows {move}.
create table "mega_evolution_move" (
	"pokemon" text
	,"form" text
	,"move" text not null unique
	,primary key ("pokemon", "form")
	,foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name")
	,foreign key ("move") references "move" ("id")
) without rowid;

insert into "mega_evolution_move" ("pokemon", "form", "move")
values
('RAYQUAZA', 'Mega', 'DRAGONASCENT');

---------------------------------------------------------------------------------------------------
-- Primal Reversion
---------------------------------------------------------------------------------------------------

-- A Pokémon of species {pokemon} will undergo Primal Reversion into its {form} form in battle iff
-- it is holding {item}.
create table "primal_reversion_item" (
	"pokemon" text
	,"form" text
	,"item" text not null unique
	,primary key ("pokemon", "form")
	,foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name")
	,foreign key ("item") references "item" ("id")
) without rowid;

insert into "primal_reversion_item" ("pokemon", "form", "item")
values
('KYOGRE', 'Primal', 'BLUEORB'),
('GROUDON', 'Primal', 'REDORB');

---------------------------------------------------------------------------------------------------
-- Ultra Burst
---------------------------------------------------------------------------------------------------

-- A Pokémon of species {pokemon} in its {from_form} form may use Ultra Burst in order to become
-- {to_form} in battle iff it is holding {item}.
create table "ultra_burst_item" (
	"pokemon" text
	,"from_form" text
	,"to_form" text not null
	,"item" text not null
	,primary key ("pokemon", "from_form")
	,foreign key ("pokemon", "from_form") references "pokemon_form" ("pokemon", "name")
	,foreign key ("pokemon", "to_form") references "pokemon_form" ("pokemon", "name")
	,foreign key ("item") references "item" ("id")
) without rowid;

insert into "ultra_burst_item" ("pokemon", "from_form", "to_form", "item")
values
('NECROZMA', 'Dusk Mane', 'Ultra', 'ULTRANECROZIUMZ'),
('NECROZMA', 'Dawn Wings', 'Ultra', 'ULTRANECROZIUMZ');

---------------------------------------------------------------------------------------------------
-- Z-Moves
---------------------------------------------------------------------------------------------------

-- The Z-Crystal item {bag_item} can be used on a Pokémon to equip it with {held_item}, which may
-- allow it to use the Z-Move named {name}.
create table "z_move" (
	"name" text primary key
	,"bag_item" text not null unique
	,"held_item" text not null unique
	,foreign key ("bag_item") references "item" ("id")
	,foreign key ("held_item") references "item" ("id")
) without rowid;

insert into "z_move" ("name", "bag_item", "held_item") values
('Breakneck Blitz', 'NORMALIUMZ', 'NORMALIUMZ2'),
('All-Out Pummeling', 'FIGHTINIUMZ', 'FIGHTINIUMZ2'),
('Supersonic Skystrike', 'FLYINIUMZ', 'FLYINIUMZ2'),
('Acid Downpour', 'POISONIUMZ', 'POISONIUMZ2'),
('Tectonic Rage', 'GROUNDIUMZ', 'GROUNDIUMZ2'),
('Continental Crush', 'ROCKIUMZ', 'ROCKIUMZ2'),
('Savage Spin-Out', 'BUGINIUMZ', 'BUGINIUMZ2'),
('Never-Ending Nightmare', 'GHOSTIUMZ', 'GHOSTIUMZ2'),
('Corkscrew Crash', 'STEELIUMZ', 'STEELIUMZ2'),
('Inferno Overdrive', 'FIRIUMZ', 'FIRIUMZ2'),
('Hydro Vortex', 'WATERIUMZ', 'WATERIUMZ2'),
('Bloom Doom', 'GRASSIUMZ', 'GRASSIUMZ2'),
('Gigavolt Havoc', 'ELECTRIUMZ', 'ELECTRIUMZ2'),
('Shattered Psyche', 'PSYCHIUMZ', 'PSYCHIUMZ2'),
('Subzero Slammer', 'ICIUMZ', 'ICIUMZ2'),
('Devastating Drake', 'DRAGONIUMZ', 'DRAGONIUMZ2'),
('Black Hole Eclipse', 'DARKINIUMZ', 'DARKINIUMZ2'),
('Twinkle Tackle', 'FAIRIUMZ', 'FAIRIUMZ2'),
('Catastropika', 'PIKANIUMZ', 'PIKANIUMZ2'),
-- Pikachu with a cap is not in the game
-- ('10,000,000 Volt Thunderbolt', 'PIKASHUNIUMZ', 'PIKASHUNIUMZ2'),
('Stoked Sparksurfer', 'ALORAICHIUMZ', 'ALORAICHIUMZ2'),
('Extreme Evoboost', 'EEVIUMZ', 'EEVIUMZ2'),
('Pulverizing Pancake', 'SNORLIUMZ', 'SNORLIUMZ2'),
('Genesis Supernova', 'MEWNIUMZ', 'MEWNIUMZ2'),
('Sinister Arrow Raid', 'DECIDIUMZ', 'DECIDIUMZ2'),
('Malicious Moonsault', 'INCINIUMZ', 'INCINIUMZ2'),
('Oceanic Operetta', 'PRIMARIUMZ', 'PRIMARIUMZ2'),
('Splintered Stormshards', 'LYCANIUMZ', 'LYCANIUMZ2'),
('Let''s Snuggle Forever', 'MIMIKIUMZ', 'MIMIKIUMZ2'),
('Clangorous Soulblaze', 'KOMMONIUMZ', 'KOMMONIUMZ2'),
('Guardian of Alola', 'TAPUNIUMZ', 'TAPUNIUMZ2'),
('Searing Sunraze Smash', 'SOLGANIUMZ', 'SOLGANIUMZ2'),
('Menacing Moonraze Maelstrom', 'LUNALIUMZ', 'LUNALIUMZ2'),
('Light That Burns the Sky', 'ULTRANECROZIUMZ', 'ULTRANECROZIUMZ2'),
('Soul-Stealing 7-Star Strike', 'MARSHADIUMZ', 'MARSHADIUMZ2');

-- A move of type {type} can be upgraded into the Z-Move named {move}.
create table "type_based_z_move" (
	"type" text primary key
	,"z_move" text not null unique
	,foreign key ("type") references "type" ("id")
	,foreign key ("z_move") references "z_move" ("name")
) without rowid;

insert into "type_based_z_move" ("type", "z_move")
values
('NORMAL', 'Breakneck Blitz'),
('FIGHTING', 'All-Out Pummeling'),
('FLYING', 'Supersonic Skystrike'),
('POISON', 'Acid Downpour'),
('GROUND', 'Tectonic Rage'),
('ROCK', 'Continental Crush'),
('BUG', 'Savage Spin-Out'),
('GHOST', 'Never-Ending Nightmare'),
('STEEL', 'Corkscrew Crash'),
('FIRE', 'Inferno Overdrive'),
('WATER', 'Hydro Vortex'),
('GRASS', 'Bloom Doom'),
('ELECTRIC', 'Gigavolt Havoc'),
('PSYCHIC', 'Shattered Psyche'),
('ICE', 'Subzero Slammer'),
('DRAGON', 'Devastating Drake'),
('DARK', 'Black Hole Eclipse'),
('FAIRY', 'Twinkle Tackle');

-- Only the move {move} can be upgraded into the Z-Move named {move}.
create table "move_based_z_move" (
	"move" text primary key
	,"z_move" text not null unique
	,foreign key ("move") references "move" ("id")
	,foreign key ("z_move") references "z_move" ("name")
) without rowid;

insert into "move_based_z_move" ("move", "z_move")
values
('VOLTTACKLE', 'Catastropika'),
('THUNDERBOLT', 'Stoked Sparksurfer'),
('LASTRESORT', 'Extreme Evoboost'),
('GIGAIMPACT', 'Pulverizing Pancake'),
('PSYCHIC', 'Genesis Supernova'),
('SPIRITSHACKLE', 'Sinister Arrow Raid'),
('DARKESTLARIAT', 'Malicious Moonsault'),
('SPARKLINGARIA', 'Oceanic Operetta'),
('STONEEDGE', 'Splintered Stormshards'),
('PLAYROUGH', 'Let''s Snuggle Forever'),
('CLANGINGSCALES', 'Clangorous Soulblaze'),
('NATURESMADNESS', 'Guardian of Alola'),
('SUNSTEELSTRIKE', 'Searing Sunraze Smash'),
('MOONGEISTBEAM', 'Menacing Moonraze Maelstrom'),
('PHOTONGEYSER', 'Light That Burns the Sky'),
('SPECTRALTHIEF', 'Soul-Stealing 7-Star Strike');

-- Only {pokemon} in its {form} Form may use the Z-Move {move}.
create table "pokemon_z_move" (
	"pokemon" text
	,"form" text
	,"z_move" text not null
	,primary key ("pokemon", "form")
	,foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name")
	,foreign key ("z_move") references "z_move" ("name")
) without rowid;

insert into "pokemon_z_move" ("pokemon", "form", "z_move")
values
('PIKACHU', '', 'Catastropika'),
('RAICHU', 'Alolan', 'Stoked Sparksurfer'),
('EEVEE', '', 'Extreme Evoboost'),
('SNORLAX', '', 'Pulverizing Pancake'),
('MEW', '', 'Genesis Supernova'),
('DECIDUEYE', '', 'Sinister Arrow Raid'),
('INCINEROAR', '', 'Malicious Moonsault'),
('PRIMARINA', '', 'Oceanic Operetta'),
('LYCANROC', 'Midday', 'Splintered Stormshards'),
('LYCANROC', 'Midnight', 'Splintered Stormshards'),
('LYCANROC', 'Dusk', 'Splintered Stormshards'),
('MIMIKYU', 'Disguised', 'Let''s Snuggle Forever'),
('MIMIKYU', 'Broken', 'Let''s Snuggle Forever'),
('KOMMOO', '', 'Clangorous Soulblaze'),
('TAPUKOKO', '', 'Guardian of Alola'),
('TAPULELE', '', 'Guardian of Alola'),
('TAPUBULU', '', 'Guardian of Alola'),
('TAPUFINI', '', 'Guardian of Alola'),
('SOLGALEO', '', 'Searing Sunraze Smash'),
('LUNALA', '', 'Menacing Moonraze Maelstrom'),
('NECROZMA', 'Dusk Mane', 'Searing Sunraze Smash'),
('NECROZMA', 'Dawn Wings', 'Menacing Moonraze Maelstrom'),
('NECROZMA', 'Ultra', 'Light That Burns the Sky'),
('MARSHADOW', '', 'Soul-Stealing 7-Star Strike');

-- still need to include info about the actual effects of the moves

---------------------------------------------------------------------------------------------------
-- Type Items
---------------------------------------------------------------------------------------------------

-- Moves of type {type} are boosted by the plate item {item}.
create table "type_plate" (
	"type" text primary key,
	"item" text not null unique,
	foreign key ("type") references "type" ("id"),
	foreign key ("item") references "item" ("id")
) without rowid;

insert into "type_plate" ("type", "item")
values
('DRAGON', 'DRACOPLATE'),
('DARK', 'DREADPLATE'),
('GROUND', 'EARTHPLATE'),
('FIGHTING', 'FISTPLATE'),
('FIRE', 'FLAMEPLATE'),
('ICE', 'ICICLEPLATE'),
('BUG', 'INSECTPLATE'),
('STEEL', 'IRONPLATE'),
('GRASS', 'MEADOWPLATE'),
('PSYCHIC', 'MINDPLATE'),
('FAIRY', 'PIXIEPLATE'),
('FLYING', 'SKYPLATE'),
('WATER', 'SPLASHPLATE'),
('GHOST', 'SPOOKYPLATE'),
('ROCK', 'STONEPLATE'),
('POISON', 'TOXICPLATE'),
('ELECTRIC', 'ZAPPLATE');

create table "pokemon_form_change_desc" (
	"pokemon" text,
	"form" text,
	"desc" text,
	primary key ("pokemon", "form"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name")
) without rowid;

insert into "pokemon_form_change_desc" ("pokemon", "form", "desc")
values
('CASTFORM', '', 'It is always in this form when not on the field of battle. When on the field of battle, it will remain in this form if neither rain, sun nor hail is active, or if the active weather has been negated by an ability, or if Castform''s ability is no longer Forecast.'),
('CASTFORM', 'Rainy', 'It changes into this form when on the field of battle when rain is active, unless the weather is negated by an ability or if Castform''s ability is no longer Forecast.'),
('CASTFORM', 'Sunny', 'It changes into this form when on the field of battle when sun is active, unless the weather is negated by an ability or if Castform''s ability is no longer Forecast.'),
('CASTFORM', 'Snowy', 'It changes into this form when on the field of battle when hail is active, unless the weather is negated by an ability or if Castform''s ability is no longer Forecast.'),
('DEOXYS', 'Attack', 'You can change it into this form by examining one of the meteorites in <a href="/area/884.html">New World Crash (map ID 884)</a>.'),
('DEOXYS', 'Defense', 'You can change it into this form by examining one of the meteorites in <a href="/area/884.html">New World Crash (map ID 884)</a>.'),
('DEOXYS', 'Normal', 'You can change it into this form by examining one of the meteorites in <a href="/area/884.html">New World Crash (map ID 884)</a>.'),
('DEOXYS', 'Speed', 'You can change it into this form by examining one of the meteorites in <a href="/area/884.html">New World Crash (map ID 884)</a>.'),
('BURMY', 'Plant Cloak', 'It changes form after depending on the field effect and the area. The following field effects induce Plant Cloak: Grassy Terrain, Misty Terrain, Burning Field, Swamp Field, Rainbow Field, Forest Field, Water Surface, Underwater, Fairy Tale Field, Flower Garden Field. If there is no field effect, any battle on an outdoor map, not underwater, outside of any cave, and not on rocky or sandy terrain will induce Plant Cloak.'),
('BURMY', 'Sandy Cloak', 'It changes form after battle depending on the field effect and the area. The following field effects induce Sandy Cloak: Dark Crystal Cavern, Desert Field, Icy Field, Rocky Field, Super-heated Field, Ashen Beach, Cave, Crystal Cavern, Mountain, Snowy Mountain, Dragon''s Den. If there is no field effect, any battle in a cave, or on rocky or sandy terrain will induce Sandy Cloak, unless the battle is underwater.'),
('BURMY', 'Trash Cloak', 'It changes form after battle depending on the field effect and the area. The following field effects induce Trash Cloak: Electric Terrain, Chess Board, Big Top Arena, Corrosive Field, Corrosive Mist Field, Factory Field, Short-circuit Field, Wasteland, Glitch Field, Murkwater Surface, Holy Field, Mirror Arena, New World, Inverse Field. If there is no field, any battle which is underwater induces Trash Cloak, as does any battle in an outdoor area where the terrain is not rocky or sandy.'),
('CHERRIM', 'Overcast', 'It is always in this form when not on the field of battle. When on the field of battle, it will remain in this form when sun is not active, or if the active weather has been negated by an ability, or if Cherrim''s ability is no longer Flower Gift.'),
('CHERRIM', 'Sunshine', 'It changes into this form when on the field of battle when sun is active, unless the active weather has been negated by an ability, or if Cherrim''s ability is no longer Flower Gift.'),
('ROTOM', 'Normal', 'You can change it into this form by examining one of the appliances in a house in <a href="/area/460.html">Ametrine City (map ID 460)</a>.'),
('ROTOM', 'Fan', 'You can change it into this form by examining one of the appliances in a house in <a href="/area/460.html">Ametrine City (map ID 460)</a>.'),
('ROTOM', 'Frost', 'You can change it into this form by examining one of the appliances in a house in <a href="/area/460.html">Ametrine City (map ID 460)</a>.'),
('ROTOM', 'Heat', 'You can change it into this form by examining one of the appliances in a house in <a href="/area/460.html">Ametrine City (map ID 460)</a>.'),
('ROTOM', 'Mow', 'You can change it into this form by examining one of the appliances in a house in <a href="/area/460.html">Ametrine City (map ID 460)</a>.'),
('ROTOM', 'Wash', 'You can change it into this form by examining one of the appliances in a house in <a href="/area/460.html">Ametrine City (map ID 460)</a>.'),
('GIRATINA', 'Altered', 'It will be in this form when not holding a <a href="/item/griseous-orb.html">Griseous Orb</a>.'),
('GIRATINA', 'Origin', 'It will be in this form when holding a <a href="/item/griseous-orb.html">Griseous Orb</a>.'),
('SHAYMIN', 'Land', 'It changes into this form at night, after being frozen, or after being withdrawn from the PC.'),
('SHAYMIN', 'Sky', 'It changes into this form when a <a href="/item/gracidea.html">Gracidea</a> is used on it.'),
('ARCEUS', 'Normal', 'It will be in this form when not holding a Plate item or a type-specific Z-Crystal.'),
('ARCEUS', 'Flying', 'It will be in this form when holding a <a href="/item/sky-plate.html">Sky Plate</a> or <a href="/item/flyinium-z.html">Flyinium Z</a>.');

----------------------------------------------------------------------------------------------------
-- Views
----------------------------------------------------------------------------------------------------

create view "tutor_move_teach_command" ("move", "command") as
select
	regexp_capture("arg"."value", '^pbMoveTutorChoose\(PBMoves::(\w+)\)$', 1),
	"arg"."command"
from "event_command_text_argument" as "arg"
where "arg"."command_type" = 'ConditionalBranch'
and "arg"."command_subtype" = 'Script'
and "arg"."parameter" = 'expr'
and "arg"."value" like "pbMoveTutorChoose(%";

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
and "arg"."value" like "addTutorMove(%";

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
and "arg"."value" like "addTutorMove(%";

---------------------------------------------------------------------------------------------------
-- Materialized Views
---------------------------------------------------------------------------------------------------

create table "pokemon_evolution_schemes" as
	select
		"pem"."from", "pem"."from_form", "pem"."to", "pem"."to_form"
		,evolution_schemes("em"."base_method", "em"."reqs") as "schemes"
	from "pokemon_evolution_method" as "pem"
	join (
		select
			"em"."id", "em"."base_method",
			case
				when "erd"."kind" is null then json_object()
				else json_group_object("erd"."kind", json("erd"."args"))
			end as "reqs"
		from "evolution_method" as "em"
		left join "evolution_requirement_display" as "erd" on "erd"."method" = "em"."id"
		group by "em"."id"
	) as "em" on "em"."id" = "pem"."method"
	group by "pem"."from", "pem"."from_form", "pem"."to", "pem"."to_form";	
