drop table if exists `stat`;

create table `stat` (
	`id` text primary key,
	`name` text not null unique check (`name` != ''),
	`order` integer not null
) without rowid;

insert into `stat`
values
('HP', 'HP', 0),
('ATK', 'Attack', 1),
('DEF', 'Defense', 2),
('SPD', 'Speed', 3),
('SA', 'Special Attack', 4),
('SD', 'Special Defense', 5);