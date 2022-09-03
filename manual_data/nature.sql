drop table if exists `nature`;

create table `nature` (
	`increased_stat_id` text,
	`decreased_stat_id` text,
	`id` text not null unique check (`id` != ''),
	`name` text not null unique check (`name` != ''),
	primary key (`increased_stat_id`, `decreased_stat_id`),
	foreign key (`increased_stat_id`) references `stat` (`id`),
	foreign key (`decreased_stat_id`) references `stat` (`id`)
) without rowid;

insert into `nature`
values
('ATK', 'ATK', 'HARDY', 'Hardy'),
('ATK', 'DEF', 'LONELY', 'Lonely'),
('ATK', 'SA', 'ADAMANT', 'Adamant'),
('ATK', 'SD', 'NAUGHTY', 'Naughty'),
('ATK', 'SPD', 'BRAVE', 'Brave'),
('DEF', 'ATK', 'BOLD', 'Bold'),
('DEF', 'DEF', 'DOCILE', 'Docile'),
('DEF', 'SA', 'IMPISH', 'Impish'),
('DEF', 'SD', 'LAX', 'Lax'),
('DEF', 'SPD', 'RELAXED', 'Relaxed'),
('SA', 'ATK', 'MODEST', 'Modest'),
('SA', 'DEF', 'MILD', 'Mild'),
('SA', 'SA', 'BASHFUL', 'Bashful'),
('SA', 'SD', 'RASH', 'Rash'),
('SA', 'SPD', 'QUIET', 'Quiet'),
('SD', 'ATK', 'CALM', 'Calm'),
('SD', 'DEF', 'GENTLE', 'Gentle'),
('SD', 'SA', 'CAREFUL', 'Careful'),
('SD', 'SD', 'QUIRKY', 'Quirky'),
('SD', 'SPD', 'SASSY', 'Sassy'),
('SPD', 'ATK', 'TIMID', 'Timid'),
('SPD', 'DEF', 'HASTY', 'Hasty'),
('SPD', 'SA', 'JOLLY', 'Jolly'),
('SPD', 'SD', 'NAIVE', 'Naive'),
('SPD', 'SPD', 'SERIOUS', 'Serious');
