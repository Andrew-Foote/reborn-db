# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       env\Scripts\python -m pbs_extractors.tm

import apsw
from collections import defaultdict
from utils import apsw_ext, pbs

def extract(db):
	pbs_data = pbs.load('tm')
	rows = defaultdict(lambda: [])

	for section in pbs_data:
		table = {'TMs': 'machine_move', 'HMs': 'machine_move', 'Move Tutors': 'tutor_move'}[section.header]
		move = section.tm
		pokemons = set(section.content) # sometimes the list contains dupes

		for pokemon in pokemons:
			for form, in db.cursor().execute('select "name" from "pokemon_form" where "pokemon" = ?', (pokemon,)):
				# form-specific differences need to be added in manually
				rows[table].append({'pokemon': pokemon, 'form': form, 'move': move})

	apsw_ext.bulk_insert_multi(db, rows)

# machine_data = []
# tutor_data = []

# for class_, thingy in data:
# 	which_data = {'TMs': machine_data, 'HMs': machine_data, 'Move Tutors': tutor_data}[class_]

# 	for move, pokemons in thingy:
# 		for pokemon in pokemons:
# 			which_data.append((pokemon, move))

# apsw_ext.setup_error_handling()
# db = apsw.Connection('db.sqlite')

# # PBS files contain some dupes so we use on conflict replace

# with db:
# 	db.cursor().execute(f"""
# 		drop table if exists `machine_move`;
# 		drop table if exists `tutor_move`;

# 		create table `machine_move` (
# 			`pokemon_id` text,
# 			`move_id` text,
# 			primary key (`pokemon_id`, `move_id`) on conflict replace,
# 			foreign key (`pokemon_id`) references `pokemon` (`id`),
# 			foreign key (`move_id`) references `move` (`id`)
# 		); -- without rowid;
# 	""")

# 	apsw_ext.bulk_insert(db, 'machine_move', ('pokemon_id', 'move_id'), machine_data)

# 	db.cursor().execute(f"""
# 		create table `tutor_move` (
# 			`pokemon_id` text,
# 			`move_id` text,
# 			primary key (`pokemon_id`, `move_id`) on conflict replace,
# 			foreign key (`pokemon_id`) references `pokemon` (`id`),
# 			foreign key (`move_id`) references `move` (`id`)
# 		) without rowid;
# 	""")

# 	apsw_ext.bulk_insert(db, 'tutor_move', ('pokemon_id', 'move_id'), machine_data)

