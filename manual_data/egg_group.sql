drop table if exists `egg_group`;

create table `egg_group` (
	`id` text primary key,
	`name` text not null unique check (`name` != '')
) without rowid;

insert into `egg_group`
values
('MONSTEER', 'Monster'),
('WATER1', 'Water 1'),
('BUG', 'Bug'),
('FLYING', 'Flying'),
('FIELD', 'Field'),
('FAIRY', 'Fairy'),
('GRASS', 'Grass'),
('HUMANLIKE', 'Human-Like'),
('WATER3', 'Water 3'),
('MINERAL', 'Mineral'),
('AMORPHOUS', 'Amorphous'),
('WATER2', 'Water 2'),
('DITTO', 'Ditto'),
('DRAGON', 'Dragon'),
('UNDISCOVERED', 'No Eggs Discovered');