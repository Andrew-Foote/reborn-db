drop table if exists `damage_class`;

create table `damage_class` (
	`id` text primary key,
	`name` text not null unique check (`name` != '')
) without rowid;

insert into `damage_class` (`id`, `name`)
values
('PHYSICAL', 'Physical'),
('SPECIAL', 'Special'),
('STATUS', 'Status');