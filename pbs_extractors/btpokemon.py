# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       `env\Scripts\python -m pbs_extractors.btpokemon

# The `btpokemon.txt` file is a list of Pokémon sets used to populate teams in the Battle Tower and
# similar facilities. To interpret it, I had to read the the `PokemonOrgBattle.rb` script, class
# `PBPokemon`, method `fromInspected`.
#
# The CSV has 7 columns:
# - Column 1 contains the ID of the Pokémon for the set.
# - Column 2 contains the ID of the held item for the set, or an empty string if there is no held
#   item.
# - Column 3 contains the ID the nature for the set.
# - Column 4 contains a comma-separated list of either two or three stat IDs ("HP", "ATK", "DEF",
#   "SPD", "SA" or "SD"), which determine the EV spread for the set. The Pokémon's 510 EVs will be
#   divided evenly between each of the listed stats (using floor division).
# - Column 5 contains a comma-separated list of move IDs for the set (always of size 4, although
#   move slots other than the first may be empty).
# - Column 6 contains the index of the Pokémon's form for the set (with the forms ordered as in
#   `pokemon.txt`).
# - Column 7 contains the index of the ability for the set (0 = first ability, 1 = second ability,
#   2 = third ability, with the first and second abilities ordered as in `pokemon.txt`).

import apsw
import csv
import itertools as it
from utils import apsw_ext, sql

with open('PBS/btpokemon.txt', newline='', encoding='utf-8') as f:
	data = list(csv.reader(f, delimiter=';'))

base_data = []
ev_data = []

apsw_ext.setup_error_handling()
db = apsw.Connection('db.sqlite')

def get_form_id(pokemon_id, form_idx):
	with db:
		for row in db.cursor().execute(
			"select `id` from `pokemon_form` where `pokemon_id` = ? and `index` = ?",
			(pokemon_id, form_idx)
		):
			return row[0]

	raise RuntimeError(f'no form with pokemon_id {pokemon_id} and index {form_idx}!')

for i, blango in enumerate(data):
	if len(blango) == 1 and blango[0][0] == '#':
		continue # comment

	pokemon_id, item_id, nature_id, evs, moves, form_idx, ability_idx = blango
	form_id = get_form_id(pokemon_id, form_idx)
	move1_id, move2_id, move3_id, move4_id = (move.strip() for move in moves.split(','))
	base_data.append((i, form_id, item_id, nature_id, move1_id, move2_id, move3_id, move4_id, ability_idx))

	for ev in evs.split(','):
		ev = ev.strip()
		ev_data.append((i, ev))


with open('manual_data/stat.sql') as f:
	with db:
		db.cursor().execute(f.read())

with open('manual_data/nature.sql') as f:
	with db:
		db.cursor().execute(f.read())

with db:
	query = f"""
		drop table if exists `battle_tower_set_ev`;
		drop table if exists `battle_tower_set`;

		create table `battle_tower_set` (
			`id` integer primary key,
			`pokemon_form_id` text not null,
			`item_id` text,
			`nature_id` text not null,
			`move1_id` text not null,
			`move2_id` text,
			`move3_id` text,
			`move4_id` text,
			`ability_idx` integer check (`ability_idx` in (0, 1, 2)),
			foreign key (`pokemon_form_id`) references `pokemon_form` (`id`),
			foreign key (`item_id`) references `item` (`id`),
			foreign key (`nature_id`) references `nature` (`id`),
			foreign key (`move1_id`) references `move` (`id`),
			foreign key (`move2_id`) references `move` (`id`),
			foreign key (`move3_id`) references `move` (`id`),
			foreign key (`move4_id`) references `move` (`id`)
		);

		insert into `battle_tower_set` (
			`id`, `pokemon_form_id`, `item_id`, `nature_id`, `move1_id`, `move2_id`, `move3_id`, `move4_id`, `ability_idx`
		)
		values
		{sql.placeholders_table(base_data)};

		create table `battle_tower_set_ev` (
			`set_id` integer,
			`stat_id` text,
			primary key (`set_id`, `stat_id`),
			foreign key (`stat_id`) references `stat` (`id`)
		) without rowid;

		insert into `battle_tower_set_ev` (`set_id`, `stat_id`)
		values
		{sql.placeholders_table(ev_data)};
	"""

	db.cursor().execute(query, it.chain(it.chain.from_iterable(base_data), it.chain.from_iterable(ev_data)))
