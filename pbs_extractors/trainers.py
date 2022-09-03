import apsw
from collections import defaultdict
from utils import apsw_ext, pbs

# The script which loads the PBS files is `Compiler.rb`. The method which handles the
# `trainers.txt` file is `pbCompileTrainers`. This method makes use of constants from
# `PokemonTrainers.rb`. It returns an array of trainer data which is saved to the file
# `Data/trainers.dat` using a method `save_data`, and also stored in a global variable
# `$cache.trainers`.
#
# (It's unclear what `save_data` does---I can't seem to find its definition anywhere).

# The `PokemonTrainers.rb` script also contains a method `pbLoadTrainer`
# which is used to parse the 
#
# 


# gender algorithm (Compiler.b#pbCompileTrainers, PokemonTrainers.rb#pbLoadTrainer, PokeBattle_Pokemon.rb#setGender)



def extract(db):
	trainers = pbs.load('trainers')
	rows = defaultdict(lambda: [])

	for pbs_order, ((type_, name, id_), trainer) in enumerate(trainers.items()):
		full_id = {'type': type_, 'name': name, 'id': id_, 'pbs_order': pbs_order}
		rows['trainer'].append(full_id)

		pfull_id = {'trainer_type': type_, 'trainer_name': name, 'trainer_id': id_}

		for item, quantity in trainer['items'].items():
			rows['trainer_item'].append({**pfull_id, 'item': item, 'quantity': quantity})

		for i, pokemon in enumerate(trainer['pokemon']):
			moves = pokemon.pop('moves')
			evs = pokemon.pop('evs')
			pokemon_id = pokemon.pop('id')
			pokemon['pokemon'] = pokemon_id

			# map forms
			form_index = pokemon.pop('form')

			form_names = db.cursor().execute(
				'select "name" from "pokemon_form" where "pokemon" = ? and "order" = ?',
				(pokemon_id, form_index)
			).fetchall()

		if not form_names:
				#print(full_id)
				#print(trainer)
				#raise Exception(f'couldn\'t find form name for pokemon {pokemon_id}, index {form_index}')
				#ok, there are too many of these
				# for now, let's just default to the first form
				form_names = db.cursor().execute(
					'select "name" from "pokemon_form" where "pokemon" = ? and "order" = ?',
					(pokemon_id, 0)
				).fetchall()

		pokemon['form'] = form_names[0][0]

		# if the ability index is 2 or 3 for a pokemon that only has 1 ability, we can set it to 1
		if pokemon['ability'] in (2, 3):
			abilities = db.cursor().execute(
				'select 1 from "pokemon_ability" where "pokemon" = ? and "form" = ? and "index" = ?',
				(pokemon_id, pokemon['form'], pokemon['ability'])
			).fetchall()

			if not abilities:
				pokemon['ability'] = 1

		# if the nature is not set then it defaults to the personal id % 25
		# special case: any trainer with type=SHELLY or FUTURESHELLY and name=Shelly
		# with Leavanny in the 4th slot has its gender matching that of the player

		rows['trainer_pokemon'].append({**pfull_id, 'index': i, **pokemon})

		for j, move in enumerate(moves):
			rows['trainer_pokemon_move'].append({
				**pfull_id, 'pokemon_index': i, 'move_index': j, 'move': move
			})

		for stat, ev in evs.items():
			rows['trainer_pokemon_ev'].append({
				**pfull_id, 'pokemon_index': i, 'stat': stat, 'value': ev
			})

	apsw_ext.bulk_insert_multi(db, rows)

