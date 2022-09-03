import apsw
from collections import defaultdict
from utils import apsw_ext, pbs

# The script which loads the PBS files is `Compiler.rb`. The method which handles the
# `trainers.txt` file is `pbCompileTrainers`. This method makes use of constants from
# `PokemonTrainers.rb`. It returns an array of trainer data which is saved to the file
# `Data/trainers.dat` using a method `save_data`, and also stored in a global variable
# `$cache.trainers`. 
#
# (It's unclear what exactly `save_data` does---I can't seem to find its definition
# anywhere).
#
# The array of trainer data is organised as follows:
# - The array has one entry for each "trainer class" (trainer type i think). The indexes correspond to the trainer type IDs.
# - Each entry is a hash whose keys are the names of the rainers in that class.
# - The values are hashes themselves, keyed by the trainer IDs (= "party IDs") under the given
#   name.
# - The values of those hashes are arrays of 2 items each --- their Pokémon, and their items.
# - The item array is just a list of item codes.
# - The Pokémon array has the following items: (defaults are used when the CSV entry is blank [but not if it's 0])
#   - TPSPECIES: its species ID
#   - TPLEVEL: its level
#   - TPITEM: its held item ID, or a default (0) -- 0 means no item
#   - TPMOVE1: a move ID, or a default (0)
#   - TPMOVE2 etc.
#   - TPABILITY: an "ability flag", 0-5, or a default (nil).
#       the ability index is this, if it's not nil, otherwise the personal ID mod 3
#       (the personal ID is initalized randomly when pbLoadTrainer is called, i.e. per battle)
#       then, the index is mapped to the actual ability: 0 = first, 1 = second, 2 = hidden
#       if the resulting ability ID comes out as 0, the ability is randomly set to either the first or second
#       if the resulting ability ID is still blank or zero, the first ability is used
#   - TPGENDER: a gender ID (0=male, 1=female, 2=genderless) (nil)
#       if the pokemon's species genderbyte is 255 or 0 or 254, this has no effect -- does not set the genderflag
#       if the genderflag is not null, it gets returned as the gender
#       otherwise, the gender is determined by the genderbyte: 255 = genderless, 254 = female, 0 = male,
#          anything else = (personalID & 0xFF <= genderbyte) ? female : male
#   - TPFORM: a form index, or a default (0)
#   - TPSHINY: true or false, or a default (false)
#   - TPNATURE: a nature ID, or a default (PBNatures::HARDY)
#   - TPIV: an IV value from 0-32, or a default (32 = trick room ivs) (default is 10)
#       the ivs are initialized in two ways (before this value is used at all):
#          - if the pokemon belongs to egg group 15, or is manaphy, then 3 ivs are set to 31, the rest are randomly set from 0-31
#          - otherwise all stats randomly set from 0-31
#       (Full IVs or Empty IVs passwords can override this)
#       this completely overriden though, so it's only for wilds. for the trainer mons, we just set each iv
#       to the value, except if the value is 32, in which case speed is 0 and rest are 31
#   - TPHAPPINESS: a friendship value from 0-255, or a default (70)
#         this is initialized with the base value for the speices, but is overridden with this value
#   - TPNAME: a nickname, or a default (nil)
#         this is initialized with the species name, but is overridden if the tpname is not blank
#   - TPSHADOW: true or false, or a default (false)
#   - TPBALL: a ball number (not sure how to interpret), or a default (0)
#         this (PokeBattle_Pokemon.ballused) is initialized with 0, but is overridden
#   - THIDDENPOWER: not set in Compiler.rb; keeps value from CSV; default is 17 but i don't think it'll be used
#   - TP{stat}EV: a value or default (0)
#       evs are initially set to all 0 on init
#       but for the trainer mon, it'll look at the sum of the evs from the data
#       if the sum is nonzero, those evs are used
#       otherwise, each ev is set to the min of 85 and the pokemon's level * 3/2

# TO set the moves, first resetMoves is called to give the Pokémon the last four level-up moves it would naturally
# learn at its current level. If there are less than four of those, the remaining slots will be set to 0.
# Then, as long as one of the moves from the data file is not set to 0, it will set each of the Pokémon's moves to
# the moves from the data file (overwriting the level up moves)
# Move ID 0 is used for empty slots
# If the pokemon's level is >= 100, and the trainer's skill is also >= 100, then the move's PP will be as if
# 3 PP Ups were used

from dataclasses import dataclass
from parsers import marshal

class CodeToResolve:
	code: int
	table: str
	code_col: str='code'
	id_col: str='id'

def extract(db):
	trainers = marshal.parse('D:\\Program Files\\Reborn19-Win\\Pokemon Reborn\\Data\\trainers.dat')
	rows = defaultdict(lambda: [])

	assert isinstance(trainers, marshal.MarshalArray)

	for trainer_type_id, trainers_for_type in enumerate(trainers.items):
		assert isinstance(trainers_for_type, marshal.MarshalHash)

		for trainer_name, parties in trainers_for_type.mapping.items():
			assert isinstance(trainer_name, marshal.MarshalString)
			trainer_name = trainer_name.content.decode('utf-8')

			assert isinstance(parties, marshal.MarshalHash)

			for party_id, party in parties.mapping.items():
				assert isinstance(party_id, marshal.MarshalFixnum)
				party_id = party_id.val

				trainer_id = {
					'trainer_type': CodeToResolve(trainer_type_id, 'trainer_type'),
					'trainer_name': trainer_name,
					'party_id': party_id
				}

				assert isinstance(party, marshal.MarshalArray)
				pokemons, items = party.items

				assert isinstance(pokemons, marshal.MarshalArray)

				assert isinstance(items, marshal.MarshalArray)

				for item_id, quantity in Counter(items.items).items():
					rows['trainer_item'].append({
						**trainer_id, 'item': CodeToResolve(item_id, 'item'), 'quantity': quantity
					})



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

