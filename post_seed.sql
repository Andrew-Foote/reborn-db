create view "evolution" ("from", "from_form", "to", "to_form") as
select distinct "from", "from_form", "to", "to_form"
from "pokemon_evolution_method";
	
create view "evolution_trcl" ("from", "from_form", "to", "to_form", "dist") as
with recursive "evolution_trcl" ("from", "from_form", "to", "to_form", "dist") as (
	select "from", "from_form", "to", "to_form", 1 from "evolution"
	union all
	select "trcl"."from", "trcl"."from_form", "evolution"."to", "evolution"."to_form", "trcl"."dist" + 1
	from "evolution_trcl" as "trcl"
	join "evolution" on (
		"evolution"."from" = "trcl"."to" and "evolution"."from_form" = "trcl"."to_form"
	)
)
select * from "evolution_trcl"
union
select "form"."pokemon", "form"."name", "form"."pokemon", "form"."name", 0
from "pokemon_form" as "form";

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

---------------------------------------------------------------------------------------------------
-- Materialized Views
---------------------------------------------------------------------------------------------------

create view "evolution_requirement_display" ("method", "kind", "args") as
select "base"."method", "base"."kind", case
	when "base"."kind" = 'level' then json_array("er_level"."level")
	when "base"."kind" = 'item' then json_array("item"."name")
	when "base"."kind" = 'held_item' then json_array("held_item"."name")
	when "base"."kind" = 'friendship' then json_array()
	when "base"."kind" = 'time'	then json_array("time"."desc", "time"."range_desc")
	when "base"."kind" = 'stat_cmp' then json_array("stat1"."name", "stat2"."name", "er_stat_cmp"."operator")
	when "base"."kind" = 'coin_flip' then json_array("er_coin_flip"."value")
	when "base"."kind" = 'leftover' then json_array()
	when "base"."kind" = 'gender' then json_array("er_gender"."gender")
	when "base"."kind" = 'teammate' then json_array("teammate"."name")
	when "base"."kind" = 'move' then json_array("move"."name")
	when "base"."kind" = 'map' then json_array("map"."id", "map"."name")
	when "base"."kind" = 'trademate' then json_array("trademate"."name")
	when "base"."kind" = 'teammate_type' then json_array("teammate_type"."name")
	when "base"."kind" = 'cancel' then json_array()
	when "base"."kind" = 'move_type' then json_array("move_type"."name")
	when "base"."kind" = 'weather' then json_array("weather"."desc")
end
from "evolution_requirement" as "base"
left join "evolution_requirement_level" as "er_level" on "er_level"."method" = "base"."method"
left join "evolution_requirement_item" as "er_item" on "er_item"."method" = "base"."method"
left join "item" on "item"."id" = "er_item"."item"
left join "evolution_requirement_held_item" as "er_held_item" on "er_held_item"."method" = "base"."method"
left join "item" as "held_item" on "held_item"."id" = "er_held_item"."item"
left join "evolution_requirement_time" as "er_time" on "er_time"."method" = "base"."method"
left join "time_of_day" as "time" on "time"."name" = "er_time"."time"
left join "evolution_requirement_stat_cmp" as "er_stat_cmp" on "er_stat_cmp"."method" = "base"."method"
left join "stat" as "stat1" on "stat1"."id" = "er_stat_cmp"."stat1"
left join "stat" as "stat2" on "stat2"."id" = "er_stat_cmp"."stat2"
left join "evolution_requirement_coin_flip" as "er_coin_flip" on "er_coin_flip"."method" = "base"."method"
left join "evolution_requirement_gender" as "er_gender" on "er_gender"."method" = "base"."method"
left join "gender" as "gender" on "gender"."name" = "er_gender"."gender"
left join "evolution_requirement_teammate" as "er_teammate" on "er_teammate"."method" = "base"."method"
left join "pokemon" as "teammate" on "teammate"."id" = "er_teammate"."pokemon"
left join "evolution_requirement_map" as "er_map" on "er_map"."method" = "base"."method"
left join "map" on "map"."id" = "er_map"."map"
left join "evolution_requirement_move" as "er_move" on "er_move"."method" = "base"."method"
left join "move" on "move"."id" = "er_move"."move"
left join "evolution_requirement_trademate" as "er_trademate" on "er_trademate"."method" = "base"."method"
left join "pokemon" as "trademate" on "trademate"."id" = "er_trademate"."pokemon"
left join "evolution_requirement_teammate_type" as "er_teammate_type" on "er_teammate_type"."method" = "base"."method"
left join "type" as "teammate_type" on "teammate_type"."id" = "er_teammate_type"."type"
left join "evolution_requirement_move_type" as "er_move_type" on "er_move_type"."method" = "base"."method"
left join "type" as "move_type" on "move_type"."id" = "er_move_type"."type"
left join "evolution_requirement_weather" as "er_weather" on "er_weather"."method" = "base"."method" 
left join "weather" as "weather" on "weather"."name" = "er_weather"."weather"
order by 
 "item"."code", "held_item"."code", "time"."order", "stat1"."order", "stat2"."order",
 "er_coin_flip"."value", "gender"."code", "teammate"."number", "map"."order", "move"."code",
 "trademate"."number", "teammate_type"."code", "move_type"."code", "weather"."order";

create table "pokemon_evolution_schemes" (
	"from" text,
	"from_form" text,
	"to" text,
	"to_form" text,
	"schemes" text,
	primary key ("from", "to", "from_form", "to_form")
) without rowid;

insert into "pokemon_evolution_schemes"
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

create table "trainer_v" (
	"id" text primary key,
	"type" text,
	"name" text,
	"party" text,
	"type_name" text,
	"type_code" integer,
	"pbs_order" integer,
	"base_prize" integer,
	"bg_music" text,
	"win_music" text,
	"intro_music" text,
	"gender" text,
	"skill" integer,
	"battle_sprite" blob,
	"battle_back_sprite" blob,
	unique ("type", "name", "party"),
	unique ("pbs_order")
) without rowid;

insert into "trainer_v"
	select
		"type"."name" || ' ' || "trainer"."name" || case
			when count(*) over (partition by "type"."name", "trainer"."name") > 1
			then ' ' || row_number() over (partition by "type"."name", "trainer"."name") else ''
		end as "id",
		"type"."id" as "type", "trainer"."name", "trainer"."party_id" as "party",
		"type"."name" as "type_name", "type"."code" as "type_code", "trainer"."pbs_order",
		"type"."base_prize", "type"."bg_music", "type"."win_music", "type"."intro_music",
		"type"."gender", "type"."skill", "type"."battle_sprite", "type"."battle_back_sprite"
	from "trainer" join "trainer_type" as "type" on "trainer"."type" = "type"."id";


create view "trainer_single_battle_command" (
	"command", "level100",
	"type", "name", "endspeech", "doublebattle", "party",
	"canlose", "variable"
) as
with "args" ("command", "index", "value") as (
	select
		"arg"."command", "arg_index"."value",
		regexp_capture("arg"."value", '^pbTrainerBattle((?:100)?)\(PBTrainers::(.*?),"(.*?)",_I\("(.*?)"\)(?:,(true|false)(?:,(\d+)(?:,(true|false)(?:,(\d+))?)?)?)?\)$', "arg_index"."value")
	from "event_command_text_argument" as "arg"
	join generate_series(1, 8) as "arg_index"
	where "arg"."value" like 'pbTrainerBattle%'
	and "arg"."command" not in (
		471049, -- exclude challengers at elite four
		488168, -- exclude the themed teams at the nightclub arena
		585399, -- exclude self battle at neoteric isle
		618855, -- exclude grind trainer common event
		572057 -- exclude this kyurem battle which i don't think can actually be accessed
		       -- (it has trainer type='KYUREM' which isn't a valid trainer type)
	) 
)
select
	"command",
	max(case when "index" = 1 then "value" = '100' else null end),
	max(case when "index" = 2 then "value" else null end),
	max(case when "index" = 3 then "value" else null end),
	max(case when "index" = 4 then "value" else null end),
	max(case when "index" = 5 then "value" is not null and "value" = 'true' else null end),
	max(case when "index" = 6 then ifnull(cast("value" as integer), 0) else null end),
	max(case when "index" = 7 then "value" is not null and "value" = 'true' else null end),
	max(case when "index" = 8 then cast("value" as integer) else null end)
from "args" group by "command";


-- pbDoubleTrainerBattle(
-- trainerid1, trainername1, trainerparty1, endspeech1,
-- trainerid2, trainername2, trainerparty2, endspeech2,
-- canlose=false, variable=nil, switch_sprites=false, recorded=false
-- )

-- canlose = if true, all non-fainted pokemon get healed when we lose the battle?
-- otherwise, we do pbStartOver when losing -- pbStartOver takes you to a poke center, etc
-- switch_sprites presumably controls the order in which the two trainers appear in the field
--   (although i'm not sure why they don't just pass in the trainer arguments the other way round)
-- 

create view "trainer_double_battle_command" (
	"command", "level100",
	"type1", "name1", "party1", "endspeech1",
	"type2", "name2", "party2", "endspeech2",
	"switch_sprites"
) as
with "args" ("command", "index", "value") as (
	select
		"arg"."command", "arg_index"."value",
		regexp_capture("arg"."value", '^pbDoubleTrainerBattle((?:100)?)\(PBTrainers::(.*?),"(.*?)",(\d+),_I\("(.*?)"\),PBTrainers::(.*?),"(.*?)",(\d+),_I\("(.*?)"\)(?:,switch_sprites:\s*(true|false))?\)$', "arg_index"."value")
	from "event_command_text_argument" as "arg"
	join generate_series(1, 10) as "arg_index"
	where "arg"."value" like 'pbDoubleTrainerBattle%'
	and not "arg"."command" in (
		8542, -- CRAUDBURRY trainer type doesn't exist
		488240, -- exclude the themed teams at the nightclub arena
		618842 -- exclude grind trainers
	)
)
select
	"command",
	max(case when "index" = 1 then "value" = '100' else null end),
	max(case when "index" = 2 then "value" else null end),
	max(case when "index" = 3 then "value" else null end),
	max(case when "index" = 4 then cast("value" as integer) else null end),
	max(case when "index" = 5 then "value" else null end),
	max(case when "index" = 6 then "value" else null end),
	max(case when "index" = 7 then "value" else null end),
	max(case when "index" = 8 then "value" else null end),
	max(case when "index" = 9 then cast("value" as integer) else null end),
	max(case when "index" = 10 then "value" is not null and "value" = 'true' else null end)
from "args" group by "command";

create table "trainer_battle_command" (
	"trainer_type" text,
	"trainer_name" text,
	"party" text,
	"command" integer,
	"level_100" integer,
	"end_speech" text,
    "is_double" integer,
	"partner_index" integer,
    "partner_type" integer,
	"partner_name" text,
	"partner_party" text,
    "can_lose" integer,
	primary key ("trainer_type", "trainer_name", "party", "command")
) without rowid;

insert into "trainer_battle_command"
    select
        "type", "name", "party", "command", "level100", "endspeech",
        "doublebattle", null, null, null, null, "canlose"
    from "trainer_single_battle_command"
    union
    select
        "type1", "name1", "party1", "command", "level100", "endspeech1",
        1, 1, "type2", "name2", "party2", 0
    from "trainer_double_battle_command"
    union
    select
        "type2", "name2", "party2", "command", "level100", "endspeech2",
        1, 2, "type1", "name1", "party1", 0
    from "trainer_double_battle_command";