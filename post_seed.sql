create table "mega_evolution" (
	"pokemon" text,
	"form" text,
	"item" text not null unique,
	primary key ("pokemon", "form"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("item") references "item" ("id")
) without rowid;

insert into "mega_evolution" ("pokemon", "form", "item")
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

create table "primal_reversion" (
	"pokemon" text,
	"form" text,
	"item" text not null unique,
	primary key ("pokemon", "form"),
	foreign key ("pokemon", "form") references "pokemon_form" ("pokemon", "name"),
	foreign key ("item") references "item" ("id")
) without rowid;

insert into "primal_reversion" ("pokemon", "form", "item")
values
('KYOGRE', 'Primal', 'BLUEORB'),
('GROUDON', 'Primal', 'REDORB');

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

create table "type_z_crystal" (
	"type" text primary key,
	"item" text not null unique,
	foreign key ("type") references "type" ("id"),
	foreign key ("item") references "item" ("id")
) without rowid;

insert into "type_z_crystal" ("type", "item")
values
('NORMAL', 'NORMALIUMZ2'),
('FLYING', 'FLYINIUMZ2'),
('GROUND', 'GROUNDIUMZ2'),
('BUG', 'BUGINIUMZ2'),
('STEEL', 'STEELIUMZ2'),
('WATER', 'WATERIUMZ2'),
('ELECTRIC', 'ELECTRIUMZ2'),
('ICE', 'ICIUMZ2'),
('DARK', 'DARKINIUMZ2'),
('FIGHTING', 'FIGHTINIUMZ2'),
('POISON', 'POISONIUMZ2'),
('ROCK', 'ROCKIUMZ2'),
('GHOST', 'GHOSTIUMZ2'),
('FIRE', 'FIRIUMZ2'),
('GRASS', 'GRASSIUMZ2'),
('PSYCHIC', 'PSYCHIUMZ2'),
('DRAGON', 'DRAGONIUMZ2'),
('FAIRY', 'FAIRIUMZ2');

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