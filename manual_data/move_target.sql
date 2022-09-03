drop table if exists `move_target`;

create table `move_target` (
	`id` text primary key,
	`desc` text not null check (`desc` != '')
) without rowid;

insert into `move_target` (`id`, `desc`)
values
('00', 'Single target'),
('01', 'No target'),
('02', 'Single opponent selected randomly'),
('04', 'All opponents'),
('08', 'All available targets other than self'),
('10', 'Self'),
('20', 'Both sides'),
('40', 'User''s side'),
('80', 'Opponent''s side'),
('100', 'Ally'),
('200', 'Ally or self'),
('400', 'Single opponent'),
('800', 'Single opponent directly opposite user');
