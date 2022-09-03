drop table if exists `move_flag`;

create table `move_flag` (
	`id` text primary key,
	`desc` text not null check (`desc` != '')
) without rowid;

insert into `move_flag` (`id`, `desc`)
values
('a', 'Makes physical contact'),
('b', 'Can be protected against by Protect/Detect'),
('c', 'Can be reflected by Magic Coat'),
('d', 'Can be Snatched'),
('e', 'Can be copied by Mirror Move'),
('f', 'May inflict flinch if the user holds King''s Rock or Razor Fang'),
('g', 'If used when frozen, thaws user out'),
('h', 'Has a high critical hit chance'),
('i', 'Is a biting move'),
('j', 'Is a punching move'),
('k', 'Is a sound move'),
('l', 'Is a powder move'),
('m', 'Is a pulse move'),
('n', 'Is an explosive move');
