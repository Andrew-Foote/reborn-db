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
#   - 0 TPSPECIES: its species ID
#   - 1 TPLEVEL: its level
#   - 2 TPITEM: its held item ID, or a default (0) -- 0 means no item
#   - 3 TPMOVE1: a move ID, or a default (0)
#   - 4 TPMOVE2 etc.
#   - 5 TPABILITY: an "ability flag", 0-5, or a default (nil).
#       the ability index is this, if it's not nil, otherwise the personal ID mod 3
#       (the personal ID is initalized randomly when pbLoadTrainer is called, i.e. per battle)
#       then, the index is mapped to the actual ability: 0 = first, 1 = second, 2 = hidden
#       if the resulting ability ID (not index) comes out as 0, the ability is randomly set to either the first or second
#       if the resulting ability ID is still blank or zero, the first ability is used
#   - 6 TPGENDER: a gender ID (0=male, 1=female, 2=genderless) (nil)
#       if the pokemon's species genderbyte is 255 or 0 or 254, this has no effect -- does not set the genderflag
#       if the genderflag is not null, it gets returned as the gender
#       otherwise, the gender is determined by the genderbyte: 255 = genderless, 254 = female, 0 = male,
#          anything else = (personalID & 0xFF <= genderbyte) ? female : male
#   - 7 TPFORM: a form index, or a default (0)
#   - 8 TPSHINY: true or false, or a default (false)
#   - 9 TPNATURE: a nature ID, or a default (PBNatures::HARDY)
#   - 10 TPIV: an IV value from 0-32, or a default (32 = trick room ivs) (default is 10)
#       the ivs are initialized in two ways (before this value is used at all):
#          - if the pokemon belongs to egg group 15, or is manaphy, then 3 ivs are set to 31, the rest are randomly set from 0-31
#          - otherwise all stats randomly set from 0-31
#       (Full IVs or Empty IVs passwords can override this)
#       this completely overriden though, so it's only for wilds. for the trainer mons, we just set each iv
#       to the value, except if the value is 32, in which case speed is 0 and rest are 31
#   - 11 TPHAPPINESS: a friendship value from 0-255, or a default (70)
#         this is initialized with the base value for the speices, but is overridden with this value
#   - 12 TPNAME: a nickname, or a default (nil)
#         this is initialized with the species name, but is overridden if the tpname is not blank
#   - 13 TPSHADOW: true or false, or a default (false)
#   - 14 TPBALL: a ball number (not sure how to interpret), or a default (0)
#         this (PokeBattle_Pokemon.ballused) is initialized with 0, but is overridden
#   - 15 THIDDENPOWER: not set in Compiler.rb; keeps value from CSV; default is 17 but i don't think it'll be used
#   - 16 TP{stat}EV: a value or default (0)
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

from collections import Counter, defaultdict
from dataclasses import dataclass
from parsers import marshal
from reborndb import DB
from reborndb import pbs
from reborndb import settings
import dcformat

def extract():
	pbs_trainer_rows = []

	pbs_trainers = pbs.load('trainers')

	for pbs_order, ((type_, name, id_), trainer) in enumerate(pbs_trainers.items()):
		pbs_trainer_rows.append((type_, name, id_, pbs_order))

	trainers = marshal.load(settings.REBORN_DATA_PATH / 'trainers.dat')
	rows = defaultdict(lambda: [])

	assert isinstance(trainers, marshal.MarshalArray)

	for trainer_type_id, trainers_for_type in enumerate(trainers.items):
		assert isinstance(trainers_for_type, marshal.MarshalHash)

		prev_trainer_name = None

		for trainer_name, parties in trainers_for_type.mapping.items():
			assert isinstance(trainer_name, marshal.MarshalDecodedString), dcformat.stringify((trainer_type_id, trainer_name, prev_trainer_name))
			prev_trainer_name = trainer_name
			trainer_name = trainer_name.content

			assert isinstance(parties, marshal.MarshalHash)

			for party_id, party in parties.mapping.items():
				assert isinstance(party_id, marshal.MarshalFixnum)
				party_id = party_id.val
				trainer_id = (trainer_type_id, trainer_name, party_id)
				rows['marshal_trainer'].append(trainer_id)

				assert isinstance(party, marshal.MarshalArray)
				pokemons, items = party.items

				assert isinstance(pokemons, marshal.MarshalArray)

				assert isinstance(items, marshal.MarshalArray)

				for item_id, quantity in Counter(items.items).items():
					rows['marshal_trainer_item'].append((*trainer_id, item_id.val, quantity))

				for i, pokemon in enumerate(pokemons.items):
					pokerow = map(marshal.pythonify, pokemon.items)
					rows['marshal_trainer_pokemon'].append((*trainer_id, i, *pokerow))

	with DB.H.transaction():
		DB.H.bulk_insert(
			'trainer',
			('type', 'name', 'party_id', 'pbs_order'),
			pbs_trainer_rows
		)

		DB.H.dump_as_table(
			'marshal_trainer_item',
			('trainer_type', 'trainer_name', 'party_id', 'item', 'quantity'),
			rows['marshal_trainer_item']
		)

		DB.H.exec('''
			insert into "trainer_item" ("trainer_type", "trainer_name", "party_id", "item", "quantity")
			select "trainer_type"."id", "mti"."trainer_name", "mti"."party_id", "item"."id", "mti"."quantity"
			from "marshal_trainer_item" as "mti"
			join "trainer_type" on "trainer_type"."code" = "mti"."trainer_type"
			left join "item" on "item"."code" = "mti"."item"
		''')

		DB.H.dump_as_table(
			'marshal_trainer_pokemon',
			(
				'trainer_type', 'trainer_name', 'party_id', 'index', 'pokemon', 'level', 'item',
				'move1', 'move2', 'move3', 'move4', 'ability', 'gender', 'form', 'shiny',
				'nature', 'ivs', 'friendship', 'nickname', 'shadow', 'ball', 'hidden_power',
				'hp_ev', 'atk_ev', 'def_ev', 'spd_ev', 'sa_ev', 'sd_ev'

			),
			rows['marshal_trainer_pokemon']
		)

		DB.H.exec('create index "marshal_trainer_pokemon_idx_ivs" on "marshal_trainer_pokemon" ("ivs")')
		DB.H.exec('create index "marshal_trainer_pokemon_idx_hp_ev" on "marshal_trainer_pokemon" ("hp_ev")')

		DB.H.exec('''
			insert into "trainer_pokemon" (
				"trainer_type", "trainer_name", "party_id", "index", "pokemon", "form",
				"nickname", "gender", "level", "nature", "item", "friendship",
				"shiny", "shadow", "ball", "hidden_power"
			)
			select
				"trainer_type"."id", "mtp"."trainer_name", "mtp"."party_id", "mtp"."index",
				"pokemon"."id", ifnull("form"."name", ''), "mtp"."nickname",
				case
					when "pokemon"."male_frequency" is null then 'Genderless'
					when "pokemon"."male_frequency" = 1000 then 'Male'
					when "pokemon"."male_frequency" = 0 then 'Female'
					else "gender"."name"
				end as "gender", 
				"mtp"."level", "nature"."id", "item"."id", "mtp"."friendship", "mtp"."shiny",
				"mtp"."shadow", "mtp"."ball", "mtp"."hidden_power"
			from "marshal_trainer_pokemon" as "mtp"
			join "trainer_type" on "trainer_type"."code" = "mtp"."trainer_type"
			join "pokemon" on "pokemon"."number" = "mtp"."pokemon"
			left join "pokemon_form" as "form" on (
				"form"."pokemon" = "pokemon"."id" and "form"."order" = "mtp"."form"
			)
			left join "gender" on "gender"."code" = "mtp"."gender"
			join "nature" on "nature"."code" = "mtp"."nature"
			left join "item" on "item"."code" = "mtp"."item" and "mtp"."item" != 0

		''')

		# if mti.ability is actually null, it could be any of the three abilites
		# but if mti.ability is just an index that the pokemon doesn't have a slot for,
		# then it may be the first or second ability, but not the hidden one
		DB.H.exec('''
			insert into "trainer_pokemon_ability" (
				"trainer_type", "trainer_name", "party_id", "pokemon_index", "ability"
			)
			select
				"trainer_type"."id", "mtp"."trainer_name", "mtp"."party_id", "mtp"."index",
				"ability"."index"
			from "marshal_trainer_pokemon" as "mtp"
			join "trainer_type" on "trainer_type"."code" = "mtp"."trainer_type"
			join "pokemon" on "pokemon"."number" = "mtp"."pokemon"
			left join "pokemon_form" as "form" on (
				"form"."pokemon" = "pokemon"."id" and "form"."order" = "mtp"."form"
			)
			left join "pokemon_ability" as "matching_ability" on (
				"matching_ability"."pokemon" = "pokemon"."id"
				and "matching_ability"."form" = ifnull("form"."name", '')
				and "matching_ability"."index" = "mtp"."ability" + 1
			)
			join "pokemon_ability" as "ability" on (
				"ability"."pokemon" = "pokemon"."id"
				and "ability"."form" = ifnull("form"."name", '')
				and (
					"mtp"."ability" is null
					or ("matching_ability"."index" is null and "ability"."index" != 3)
					or "ability"."index" = "matching_ability"."index"
				)
			)
		''')

		DB.H.exec('''
			insert into "trainer_pokemon_move" (
				"trainer_type", "trainer_name", "party_id",
				"pokemon_index", "move_index", "move"
			)
			select
				"trainer_type"."id", "mtp"."trainer_name", "mtp"."party_id",
				"mtp"."index", "mtp_move"."key", "move"."id"
			from "marshal_trainer_pokemon" as "mtp"
			join "trainer_type" on "trainer_type"."code" = "mtp"."trainer_type"
			join json_each(json_array(
				"mtp"."move1", "mtp"."move2", "mtp"."move3", "mtp"."move4"
			)) as "mtp_move"
			join "move" on "move"."code" = "mtp_move"."value"
			where (
				"mtp"."move1" != 0 or "mtp"."move2" != 0 
				or "mtp"."move3" != 0 or "mtp"."move4" != 0
			) and "mtp_move"."value" != 0
		''')

		DB.H.exec('''
			insert into "trainer_pokemon_move" (
				"trainer_type", "trainer_name", "party_id",
				"pokemon_index", "move_index", "move"
			)
			select * from (
				select
					"trainer_type"."id", "mtp"."trainer_name", "mtp"."party_id",
					"mtp"."index",  4 - (rank() over (
						partition by "move"."pokemon", "move"."form"
						order by "move"."level" desc, "move"."order" desc
					)) as "move_index", "move"."move"
				from "marshal_trainer_pokemon" as "mtp"
				join "trainer_type" on "trainer_type"."code" = "mtp"."trainer_type"
				join "pokemon" on "pokemon"."number" = "mtp"."pokemon"
				left join "pokemon_form" as "form" on (
					"form"."pokemon" = "pokemon"."id" and "form"."order" = "mtp"."form"
				)
				join "level_move" as "move" on (
					"move"."pokemon" = "pokemon"."id"
					and "move"."form" = ifnull("form"."name", '')
				)
				where (
					"mtp"."move1" = 0 and "mtp"."move2" = 0 
					and "mtp"."move3" = 0 and "mtp"."move4" = 0
				)
			) where "move_index" > 0
		''')

		DB.H.exec('''
			insert into "trainer_pokemon_ev" (
				"trainer_type", "trainer_name", "party_id", "pokemon_index", "stat", "value"
			)
			select
				"trainer_type"."id", "mtp"."trainer_name", "mtp"."party_id", "mtp"."index",
				"stat"."id", "ev"."value"
			from "marshal_trainer_pokemon" as "mtp"
			join "trainer_type" on "trainer_type"."code" = "mtp"."trainer_type"
			join json_each(json_array(
				"mtp"."hp_ev", "mtp"."atk_ev", "mtp"."def_ev", "mtp"."spd_ev",
				"mtp"."sa_ev", "mtp"."sd_ev"
			)) as "ev"
			join "stat" on "stat"."order" = "ev"."key"
			where (
				"mtp"."hp_ev" != 0 or "mtp"."atk_ev" != 0 or "mtp"."def_ev" != 0
				or "mtp"."spd_ev" != 0 or "mtp"."sa_ev" != 0 or "mtp"."sd_ev" != 0
			)
		''')

		DB.H.exec('''
			insert into "trainer_pokemon_ev" (
				"trainer_type", "trainer_name", "party_id", "pokemon_index", "stat", "value"
			)
			select
				"trainer_type"."id", "mtp"."trainer_name", "mtp"."party_id", "mtp"."index",
				"stat"."id", min(85, "mtp"."level" * 3 / 2)
			from "marshal_trainer_pokemon" as "mtp"
			join "trainer_type" on "trainer_type"."code" = "mtp"."trainer_type"
			join "stat"
			where (
				"mtp"."hp_ev" = 0 and "mtp"."atk_ev" = 0 and "mtp"."def_ev" = 0
				and "mtp"."spd_ev" = 0 and "mtp"."sa_ev" = 0 and "mtp"."sd_ev" = 0
			)
		''')

		DB.H.exec('''
			insert into "trainer_pokemon_iv" (
				"trainer_type", "trainer_name", "party_id", "pokemon_index", "stat", "value"
			)
			select
				"trainer_type"."id", "mtp"."trainer_name", "mtp"."party_id", "mtp"."index",
				"stat"."id", "mtp"."ivs"
			from "marshal_trainer_pokemon" as "mtp"
			join "trainer_type" on "trainer_type"."code" = "mtp"."trainer_type"
			join "stat"
			where "mtp"."ivs" != 32
		''')

		DB.H.exec('''
			insert into "trainer_pokemon_iv" (
				"trainer_type", "trainer_name", "party_id", "pokemon_index", "stat", "value"
			)
			select
				"trainer_type"."id", "mtp"."trainer_name", "mtp"."party_id", "mtp"."index",
				"stat"."id", case when "stat"."id" = 'SPD' then 0 else 31 end
			from "marshal_trainer_pokemon" as "mtp"
			join "trainer_type" on "trainer_type"."code" = "mtp"."trainer_type"
			join "stat"
			where "mtp"."ivs" = 32
		''')

		# special cases from PokemonEncounterModifiers.rb

		DB.H.exec('''
			update "trainer_pokemon" set "nickname" = 'Same as player', "gender" = 'Same as player'
			where
				"trainer_type" in ('SHELLY', 'FUTURESHELLY') and "trainer_name" = 'Shelly'
				and "index" = 5 and "pokemon" = 'LEAVANNY'
		''')

		DB.H.exec('''
			update "trainer_pokemon" set "nickname" = 'Same one you gave to the Darkrai that Shiv appeared to give you'
			where
				"trainer_type" = 'DARKRAI' and "trainer_name" = 'Darkrai'
				and "index" = 3 and "pokemon" = 'DARKRAI'
		''')

		# for trainer type 'DARKRAI', trainer name 'Darkrai',
		# 4th party member, species 'DARKRAI',
		# the name is set to $game_variables[782] if it's a non-empty string
		# and it's shiny if $game_switches[2200] is true
		# so we need to find where those variables/switches are set (can't see them CTRL+Fing map 893)
		# (it just looked like a normal darkrai when i got to it in-game)
		# oh wait, there's a second darkrai... and it looks like it has the same nickname i gave to
		# the fake darkrai i got from shiv
		# (still don't know fur sure if the shininess is affected by shiv's gift. especially since you
		# never actually see that darkrai, so i don't know if it would have a personality value)
		# the darkrai is given in endgame, so we should examine the map scripts for endgame