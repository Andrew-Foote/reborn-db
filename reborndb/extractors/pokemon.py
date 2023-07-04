from collections import Counter, defaultdict
from decimal import Decimal
import itertools as it
from reborndb import DB
from reborndb import pbs
from reborndb import script

# this one could do with some clean-up. 

def is_form_battle_only(pokemon_id, form_name):
	return (
		(form_name != '' and pokemon_id in (
			'CASTFORM', 'CHERRIM', 'DARMANITAN', 'MELOETTA', 'AEGISLASH', 'MIMIKYU'
		))
		or (pokemon_id == 'MINIOR' and form_name != 'Core')
		or 'Mega' in form_name or 'Primal' in form_name
		or 'PULSE' in form_name
	)

POKEMON_COUNT = 807 # Ignore Gen 8
STATS = ('HP', 'ATK', 'DEF', 'SPD', 'SA', 'SD')

INT_FIELDS = {
	'base_exp': 'BaseEXP',
	'base_friendship': 'Happiness',
	# Number of steps to hatch an Egg. (Seems it is based on the exact steps in this game, rather than "egg cycles".)
	'hatch_steps': 'StepsToHatch',
}

MAPPED_FIELDS = {
	# Gender ratio. We turn it into a male-per-1000 frequency (per-1000 so that it's always an integer).
	'male_frequency': ('GenderRate', {
		'AlwaysMale': 1000,
		'FemaleOneEighth': 875,
		'Female25Percent': 750,
		'Female50Percent': 500,
		'Female75Percent': 250,
		'AlwaysFemale': 0,
		'Genderless': None,
	}),
	'growth_rate': ('GrowthRate', {
		'Medium': 'Medium Fast',
		'Slow': 'Slow',
		'Fast': 'Fast',
		'Parabolic': 'Medium Slow',
		'Erratic': 'Erratic',
		'Fluctuating': 'Fluctuating',
	}),
	# Habitat as recorded in the FireRed/LeafGreen Pokédex.
	'habitat': ('Habitat', {
		None: None,
		'Grassland': 'Grassland',
		'Cave': 'Cave',
		'Forest': 'Forest',
		'Mountain': 'Mountain',
		'Rare': 'Rare',
		'RoughTerrain': 'Rough-terrain',
		'Sea': 'Sea',
		'Urban': 'Urban',
		'WatersEdge': 'Water\'s-edge',
	}),
}

EGG_GROUP_MAP = {
	'Humanlike': 'Human-Like',
	'Undiscovered': 'No Eggs Discovered',
	'Water1': 'Water 1',
	'Water2': 'Water 2',
	'Water3': 'Water 3'
}

def should_ignore_this_form(pokemon, form):
	# Ignore Galar forms (Gen 8 stuff) and Perfection forms (Desolation stuff)
	if form in ('Galarian', 'Galar', 'Galar Zen', 'Perfection'):
		return True

	# Mega Mightyena/Toxicroak only appear in Desolation as far as I know
	if pokemon in ('MIGHTYENA', 'TOXICROAK') and form == 'Mega':
		return True

	# the dev marshadow also doesn't seem to appear anywhere in Reborn, but I'll keep it in anyway

	return False

def extract():
	# note: we ignore gen8pokemon.txt, it appears to contain (rather confusingly) only data
	# for pokemon up to gen 7, but is otherwise the same as this file
	pbs_data = pbs.load('pokemon')
	script_data = script.parse(script.get_path('MultipleForms.rb'))
	rows = defaultdict(lambda: [])

	for section in pbs_data:
		number = int(section.header) # National Pokédex number.
		if number > POKEMON_COUNT: continue # Gen 8 never happened
		section_keys = set(section.content.keys())

		expected_keys = {
			'_SectionNumber', 'InternalName', 'Name', 'GenderRate', 'GrowthRate', 'BaseEXP',
			'Rareness', 'Happiness', 'StepsToHatch', 'Habitat', 'Kind', 'Pokedex', 'Type1', 'Type2',
			'EffortPoints', 'Compatibility', 'FormNames', 'BaseStats', 'Abilities', 'HiddenAbility',
			'Moves', 'EggMoves', 'Height', 'Weight', 'Color', 'Evolutions',
			'WildItemCommon', 'WildItemUncommon', 'WildItemRare',
			'BattlerPlayerY', 'BattlerEnemyY', 'BattlerAltitude', 'RegionalNumbers'
		}

		if not section_keys.issubset(expected_keys):
			raise ValueError(f'unexpected keys in PBS file: {section_keys - expected_keys}')

		id_ = section.content['InternalName']
		pbs_name = section.content['Name']
		name = pbs_name + {'NIDORANfE': '♀', 'NIDORANmA': '♂'}.get(id_, '')
		
		row = {
			'number': number, 'id': id_, 'name': name,
			'category': section.content['Kind'], # Category ("X Pokémon").
			'color': section.content['Color']
		}

		rows['pokemon'].append(row)

		for field, pbs_field in INT_FIELDS.items():
			row[field] = int(section.content[pbs_field])

		for field, (pbs_field, map_) in MAPPED_FIELDS.items():
			row[field] = map_[section.content.get(pbs_field)]

		egg_groups = [EGG_GROUP_MAP.get(egg_group.strip(), egg_group.strip()) for egg_group in section.content['Compatibility'].split(',')]

		for egg_group in egg_groups:
			rows['pokemon_egg_group'].append({'pokemon': id_, 'egg_group': egg_group})

		# Form names are a bit of a mess. The PBS file contains what's supposed to be a complete list
		# of form names, but it's sometimes missing (e.g. for Tornadus/Thundurus/Landorus). The script
		# only serves to overwrite or add form names that are missing from the PBS file; normally it
		# only overwrites the forms other than the first. In addition, I have my own preferences for
		# the form names (I don't want stuff like "Form" being redundantly appended to the form name).

		pbs_form_names = section.content.get('FormNames', '').split(',')
		script_section = script_data.get(f'PBSpecies::{id_}', {})
		
		script_form_names = {
			int(i): name for i, name in script_section.get('FormName', {}).items()
			if not should_ignore_this_form(id_, name)
		}

		form_count = max((len(pbs_form_names), *(i + 1 for i in script_form_names.keys())))
		form_names = []

		for form_index in range(form_count):
			if form_index in script_form_names:
				form_name = script_form_names[form_index]
			elif form_index < len(pbs_form_names):
				form_name = pbs_form_names[form_index]
			else:
				form_name = ''

			form_name = form_name.strip()
			form_name = form_name.removesuffix('Form').strip()
			form_name = form_name.removesuffix('Forme').strip()
			form_name = form_name.removesuffix(section.content['Name']).strip()
			form_name = form_name.removeprefix(section.content['Name']).strip()

			if id_ == 'UNOWN':
				form_name = form_name[0]
			elif id_ == 'ARCEUS' and form_index >= 19:
				form_name = f'PULSE-{form_names[form_index % 19]}'
			elif form_index == 0:
				if id_ in ('THUNDURUS', 'TORNADUS', 'LANDORUS') and form_index == 0:
					form_name = 'Incarnate'
				elif id_ == 'MELOETTA':
					form_name = 'Arira'
				elif id_ == 'MEOWSTIC':
					form_name = 'Male'

			form_names.append(form_name)

		if id_ in ('DEERLING', 'SAWSBUCK'):
			form_names = ['Spring', 'Summer', 'Autumn', 'Winter']
		elif id_ in ('FLABEBE', 'FLOETTE', 'FLORGES'):
			form_names = ['Red Flower', 'Orange Flower', 'Yellow Flower', 'Blue Flower', 'White Flower']
		elif id_ == 'ABRA':
			# it has two PULSE entries under FormNames for some reason
			# assuming that's just a dupe rather than anything meaningufl?:
			form_names = ['', 'PULSE']
		elif id_ == 'STEELIX':
			# Gargantuan Form (my own name for it; it's the form the Gargantuan Steelix has, although
			# it's basically identical to Mega Steelix except that it doesn't require Mega Evolution)
			# isn't listed in MultipleForms.rb
			form_names = ['', 'Mega', 'Gargantuan']
		elif id_ == 'PICHU':
			form_names = [''] # ignore Spiky-Eared
 
		for form_index, form_name in enumerate(form_names):
			script_subsection = script_section.get(script_form_names.get(form_index), {})
			type1_id = script_subsection['Type1'].removeprefix('PBTypes::') if 'Type1' in script_subsection else section.content['Type1']
			type2_id = script_subsection['Type2'].removeprefix('PBTypes::') if 'Type2' in script_subsection else (section.content.get('Type2') or None)

			if type2_id == type1_id: # MultipleForms.entry sometimes puts both type1 and type2 as the same type
				type2_id = None

			height = int(Decimal(script_subsection.get('Height', section.content['Height'])) * 100) # Converted from metres to centimetres.
			weight = int(Decimal(script_subsection.get('Weight', section.content['Weight'])) * 10) # Converted from kilogrammes to tenths of a kilogramme.
			pokedex_entry = script_subsection.get('DexEntry', section.content['Pokedex'])
			catch_rate = int(script_subsection.get('CatchRate', section.content['Rareness'])) # Minior's catch rate changes between forms.

			if 'Ability' in script_subsection:
				ability_ids = script_subsection['Ability']

				if isinstance(ability_ids, str):
					ability_ids = [ability_ids]

				ability_ids = [ability_id.removeprefix('PBAbilities::') for ability_id in ability_ids]
				hidden_ability_id = ability_ids[2] if len(ability_ids) >= 3 else None

				if len(ability_ids) >= 2 and ability_ids[0] == ability_ids[1]:
					del ability_ids[1]
			else:
				ability_ids = [ability_id.strip() for ability_id in section.content['Abilities'].split(',')]
				hidden_ability_id = section.content.get('HiddenAbility')

				# if id_ in ('PLUSLE', 'MINUN'): # these Pokémon have their hidden abilities incorrectly listed as second abilities
				# 	hidden_ability_id = ability_ids.pop()
				# update 27/05/2023 - nope, looks like the game just treats them as reg abiities

			if 'WildHoldItems' in script_subsection:
				wild_hold_items = [str(item).removeprefix('PBItems::') if item != '0' else None for item in script_subsection['WildHoldItems']]
			else:
				wild_hold_items = [section.content.get('WildItemCommon'), section.content.get('WildItemUncommon'), section.content.get('WildItemRare')]

			if wild_hold_items[0] is not None and wild_hold_items[0] == wild_hold_items[1] == wild_hold_items[2]:
				wild_always_held_item = wild_hold_items[0]
			else:
				wild_always_held_item = 'DUMMY'

			form_row = {
				'pokemon': id_, 'name': form_name, 'order': form_index,
				'catch_rate': catch_rate, 'height': height, 'weight': weight,
				'pokedex_entry': pokedex_entry, 'wild_always_held_item': wild_always_held_item,
				'battle_only': is_form_battle_only(id_, form_name)
			}

			# what is GetEvo? oh, it's an array of 3-arrays, each one containing the method code, "level" (really method arg) and evolved pokemon number (form?)
			# should update encounter data too form the OnCreate procs
			# we need to know hwich forms are mega + what items induce it
			# pokemon_mega_evolution : (pokemon_id, form_name, item_id)
			# primary key should be item_id

			rows['pokemon_form'].append(form_row)

			rows['pokemon_type'].append({'pokemon': id_, 'form': form_name, 'index': 1, 'type': type1_id})
			if type2_id is not None: rows['pokemon_type'].append({'pokemon': id_, 'form': form_name, 'index': 2, 'type': type2_id})

			rows['pokemon_ability'].append({'pokemon': id_, 'form': form_name, 'index': 1, 'ability': ability_ids[0]})

			if len(ability_ids) >= 2 and ability_ids[1] != ability_ids[0]: # some of the entries in pokemon.txt list the same ability for the first and second slots
				rows['pokemon_ability'].append({'pokemon': id_, 'form': form_name, 'index': 2, 'ability': ability_ids[1]})
			
			if hidden_ability_id is not None: rows['pokemon_ability'].append({'pokemon': id_, 'form': form_name, 'index': 3, 'ability': hidden_ability_id})

			if wild_always_held_item == 'DUMMY':
				for i, item in enumerate(wild_hold_items):
					if item is not None:
						rows['wild_held_item'].append({
							'pokemon': id_, 'form': form_name, 'always_held_item': 'DUMMY',
							'rarity': ['Common', 'Uncommon', 'Rare'][i], 'item': item
						})

			base_stats = [int(base_stat.strip()) for base_stat in script_subsection.get('BaseStats', section.content['BaseStats'].split(','))]
			assert len(STATS) == len(base_stats)

			for stat_id, base_stat in zip(STATS, base_stats):
				rows['base_stat'].append({'pokemon': id_, 'form': form_name, 'stat': stat_id, 'value': base_stat})

			stat_yields = [int(stat_yield.strip()) for stat_yield in script_subsection.get('EVs', section.content['EffortPoints'].split(','))]
			assert len(STATS) == len(stat_yields)

			for stat_id, stat_yield in zip(STATS, stat_yields):
				if stat_yield != 0:
					rows['ev_yield'].append({'pokemon': id_, 'form': form_name, 'stat': stat_id, 'value': stat_yield})

			if 'Movelist' in script_subsection:
				level_moves = [(int(level), move.removeprefix('PBMoves::')) for level, move in script_subsection['Movelist']]
			else:
				pbs_level_moves = [move.strip() for move in section.content['Moves'].split(',')]
				level_moves = list(zip(map(int, pbs_level_moves[::2]), pbs_level_moves[1::2]))

			level_moves_counter = Counter()

			for level, move in level_moves:
				order = level_moves_counter[level]
				level_moves_counter[level] += 1
				rows['level_move'].append({'pokemon': id_, 'form': form_name, 'level': level, 'order': order, 'move': move})

			# level_moves_set = set()

			# for level, move in level_moves:
			# 	# there are some duplicates
			# 	if (id_, form_name, level, move) not in level_moves_set:
			# 		rows['level_move'].append({'pokemon': id_, 'form': form_name, 'level': level, 'move': move})

			# 	level_moves_set.add((id_, form_name, level, move))

			if 'EggMoves' in script_subsection:
				egg_moves = [move.removeprefix('PBMoves::') for move in script_subsection['EggMoves']]
			elif section.content.get('EggMoves'):
				egg_moves = [move.strip() for move in section.content['EggMoves'].split(',')]
			else:
				egg_moves = []

			for move_id in egg_moves:
				rows['egg_move'].append({'pokemon': id_, 'form': form_name, 'move': move_id})

			# PokemonData.rb, lines 315--342 is our guide to what "GetEvo" means
			# basically it's an array of 3-tuples, each one containing the evolution method, method arg, and evolved Pokémon --- but encoded via
			# integer ids rather than string ids
			# It seems to be unreliable though --- e.g. if I interpret it right, it says Alolan Sandshrew and Alolan Vulpix both evolve into Clauncher
			# It doesn't appear to specify the form on evolution
			# And there is no data in there on the evolutions of Pokémon that don't have multiple forms, but whose evolutions do (e.g. Raichu)
			# So I'm going to just ignore it and put form evolution data in manually

			# oh wait, I interpreted it wrong... it's evolved pokemon number, method id, argument (as id)


	with DB.H.transaction():
		for table, tablerows in rows.items():
			fields = tuple(tablerows[0].keys())
			DB.H.bulk_insert(table, fields, (
				tuple(row[field] for field in fields)
				for row in tablerows
			))

	with DB.H.transaction():
		handle_evolutions()

EVOLUTION_REQUIREMENT_COLS = {
	'level': ('level',),
	'item': ('item',),
	'held_item': ('item',),
	'map': ('map',),
	'stat_cmp': ('stat1', 'stat2', 'operator'),
	'coin_flip': ('value',),
	'gender': ('gender',),
	'teammate': ('pokemon',),
	'teammate_type': ('type',),
	'move': ('move',),
	'move_type': ('type',),
	'time': ('time',),
	'weather': ('weather',),
	'trademate': ('pokemon',),
}

EVOLUTION_METHOD_MAP = {
	'Level': lambda arg: [('level', {'level': arg})],
	'Ninjask': lambda arg: [('level', {'level': arg})],
	'Shedinja': lambda arg: [('level', {'level': arg, 'leftover': None})],
	'Item': lambda arg: [('item', {'item': arg})],
	'Trade': lambda arg: [('trade', {})],
	'Happiness': lambda arg: [('level', {'friendship': None})],
	'TradeItem': lambda arg: [('trade', {'held_item': arg})],
	'Location': lambda arg: [('level', {'map': int(arg)})],
	'Affection': lambda arg: [('level', {'friendship': None, 'move_type': 'FAIRY'})],
	'HappinessDay': lambda arg: [('level', {'friendship': None, 'time': 'Day'})],
	'HappinessNight': lambda arg: [('level', {'friendship': None, 'time': 'Night'})],
	'DayHoldItem': lambda arg: [('level', {'held_item': arg, 'time': 'Day'})],
	'NightHoldItem': lambda arg: [('level', {'held_item': arg, 'time': 'Night'})],
	'AttackGreater': lambda arg: [('level', {'level': arg, 'stat_cmp': ('ATK', 'DEF', '>')})],
	'DefenseGreater': lambda arg: [('level', {'level': arg, 'stat_cmp': ('ATK', 'DEF', '<')})],
	'AtkDefEqual': lambda arg: [('level', {'level': arg, 'stat_cmp': ('ATK', 'DEF', '=')})],
	'Silcoon': lambda arg: [('level', {'level': arg, 'coin_flip': 0})],
	'Cascoon': lambda arg: [('level', {'level': arg, 'coin_flip': 1})],
	'ItemMale': lambda arg: [('item', {'item': arg, 'gender': 'Male'})],
	'ItemFemale': lambda arg: [('item', {'item': arg, 'gender': 'Female'})],
	'LevelMale': lambda arg: [('level', {'level': arg, 'gender': 'Male'})],
	'LevelFemale': lambda arg: [('level', {'level': arg, 'gender': 'Female'})],
	'HasInParty': lambda arg: [('level', {'teammate': arg})],
	'BadInfluence': lambda arg: [('level', {'level': arg, 'teammate_type': 'DARK'})],
	'HasMove': lambda arg: [('level', {'move': arg})],
	'LevelDay': lambda arg: [('level', {'level': arg, 'time': 'Day'})],
	'LevelNight': lambda arg: [('level', {'level': arg, 'time': 'Night'})],
	'LevelRain': lambda arg: [('level', {'level': arg, 'weather': 'Rain'})], # use LevelWeather instead
	'Beauty': lambda arg: [('level', {'beauty': None})],
	'ItemLocation': lambda arg: [('item', {'item': arg[0], 'map': int(arg[1])})],
	'LevelDayLocation': lambda arg: [('level', {'level': arg[0], 'time': 'Day', 'map': int(arg[1])})],
	'TradeSpecies': lambda arg: [('trade', {'trademate': arg})],
	'Cancel': lambda arg: [('level', {'level': arg, 'cancel': None})],
	'LevelDayNotDusk': lambda arg: [('level', {'level': arg, 'time': 'DayNotDusk'})],
	'LevelDusk': lambda arg: [('level', {'level': arg, 'time': 'Dusk'})],
	'LevelWeather': lambda arg: [('level', {'level': arg[0], 'weather': arg[1]})],
}

def identity(arg):
	return arg

def lookup_item(id_):
	return list(DB.H.exec('select "id" from "item" where "code" = ?', (id_,)))[0][0]

def lookup_move(id_):
	return list(DB.H.exec('select "id" from "move" where "code" = ?', (id_,)))[0][0]

def lookup_pokemon(id_):
	return list(DB.H.exec('select "id" from "pokemon" where "number" = ?', (id_,)))[0][0]

# used for parsing the GetEvo fields in the MultipleForms.rb script
# second element of tuple is a callback that will be applied to the argument
# to put it in the same form expected in the PBS file
PBS_METHODS_BY_ID = [
	('Unknown', identity),
	('Happiness', identity),
	('HappinessDay', identity),
	('HappinessNight', identity),
	('Level', identity),
	('Trade', identity),
	('TradeItem', lookup_item),
	('Item', lookup_item),
	('AttackGreater', identity),
	('AtkDefEqual', identity),
	('DefenseGreater', identity),
	('Silcoon', identity),
	('Cascoon', identity),
	('Ninjask', identity),
	('Shedinja', identity),
	('Beauty', identity),
	('ItemMale', lookup_item),
	('ItemFemale', lookup_item),
	('DayHoldItem', lookup_item),
	('NightHoldItem', lookup_item),
	('HasMove', lookup_move),
	('HasInParty', lookup_pokemon),
	('LevelMale', identity),
	('LevelFemale', identity),
	('Location', identity),
	('TradeSpecies', lookup_pokemon),
	('BadInfluence', identity),
	('Affection', identity),
	('LevelRain', identity),
	('LevelDay', identity),
	('LevelNight', identity),
	('Custom6', identity),
	('Custom7', identity),
]

def handle_evolutions():
	# lifted from PokemonEvolution.rb
	RAICHU_MAPS = [15,16,17,18,19,20,21,22,23,25,26,27,30,31,32,33,34,35,199,200,201,202,203,204,205,206,207,208,536,538,547,553,556,558,562,563,564,565,566,567,568,569,574,575,576,577,578,579,586,601,603,604,605]
	EXEGGUTOR_MAPS = [15,16,17,18,19,20,21,22,23,25,26,27,30,31,32,33,34,35,199,200,201,202,203,204,205,562,563,564,565,566,567,568]
	MAROWAK_MAPS = [152,552]
	CRABOMINABLE_MAPS = [364,366,373,374,375,376,377,378,379,380,384,385,386,387,388,389,390,391,392,393,394,395,396,397,398,399,400,401,402,403,430,431,432,433,434,435,436,439,440,441,442,457,458,459,460,461,462,463,464]
	MAGNETIC_MAPS = [197,198,281]
	MAGNETIC_EVOLUTIONS = (('MAGNETON', 'MAGNEZONE'), ('NOSEPASS', 'PROBOPASS'), ('CHARJABUG', 'VIKAVOLT'))
	GOODRA_WEATHERS = ('HeavyRain', 'Rain', 'Storm')

	def get_complement_maps(map_set):
		return [map_ for map_, in DB.H.exec(
			'select "id" from "map" where "id" not in ({})'.format(', '.join('?' for _ in map_set)),
			map_set
		)]

	MANUAL_EVOLUTIONS = {
		('PIKACHU', ''): [
			*(('ItemLocation', ('THUNDERSTONE', map_), 'RAICHU', 'Normal') for map_ in get_complement_maps(RAICHU_MAPS)),
			*(('ItemLocation', ('THUNDERSTONE', map_), 'RAICHU', 'Alolan') for map_ in RAICHU_MAPS),
		],
		# not sure if there are any conditions on how Diglett evolves
		('EXEGGCUTE', ''): [
			*(('ItemLocation', ('LEAFSTONE', map_), 'EXEGGUTOR', 'Normal') for map_ in get_complement_maps(EXEGGUTOR_MAPS)),
			*(('ItemLocation', ('LEAFSTONE', map_), 'EXEGGUTOR', 'Alolan') for map_ in EXEGGUTOR_MAPS),
		],
		('CUBONE', ''): [
			*(('LevelDayLocation', (28, map_), 'MAROWAK', 'Normal') for map_ in get_complement_maps(MAROWAK_MAPS)),
			*(('LevelDayLocation', (28, map_), 'MAROWAK', 'Alolan') for map_ in MAROWAK_MAPS),
			('LevelNight', 28, 'MAROWAK', 'Alolan'),
		],
		('KARRABLAST', ''): [('TradeSpecies', 'SHELMET', 'ESCAVALIER', '')],
		('SHELMET', ''): [('TradeSpecies', 'KARRABLAST', 'ACCELGOR', '')],
		('INKAY', ''): [('Cancel', 30, 'MALAMAR', '')],
		('SLIGGOO', ''): [('LevelWeather', (50, weather), 'GOODRA', '') for weather in GOODRA_WEATHERS],
		('CRABRAWLER', ''): [('Location', map_, 'CRABOMINABLE', '') for map_ in CRABOMINABLE_MAPS],
		('ROCKRUFF', ''): [
			('LevelDayNotDusk', 25, 'LYCANROC', 'Midday'),
			('LevelNight', 25, 'LYCANROC', 'Midnight'),
			('LevelDusk', 25, 'LYCANROC', 'Dusk'),
		],
		('ESPURR', ''): [
		    ('LevelMale', 25, 'MEOWSTIC', 'Male'),
		    ('LevelFemale', 25, 'MEOWSTIC', 'Female')
		],
	}

	for pokemon, evolution in MAGNETIC_EVOLUTIONS:
		MANUAL_EVOLUTIONS[(pokemon, '')] = [
			*(('Location', map_, evolution, '') for map_ in MAGNETIC_MAPS),
		]

	pbs_data = pbs.load('pokemon')
	script_data = script.parse(script.get_path('MultipleForms.rb'))
	evolution_rows = defaultdict(lambda: [])
	evo_methods_keyed_by_evo_id = defaultdict(lambda: [])
	evo_methods_by_pbs_name = {}

	BIG_COUNTER = 0

	def create_evolution_method(pbs_method, argument, i, method, requirements):
		nonlocal BIG_COUNTER

		if (pbs_method, argument, i) not in evo_methods_by_pbs_name:
			method_id = '-'.join([pbs_method, *map(str, (argument if isinstance(argument, tuple) else [argument])), str(i)]) # crude, but it works
			method_row = {'id': method_id, 'pbs_name': pbs_method, 'base_method': method}
			evo_methods_by_pbs_name[pbs_method, argument, i] = method_row
			evolution_rows['evolution_method'].append(method_row)

			for kind, value in requirements.items():
				evolution_rows['evolution_requirement'].append({'method': method_id, 'kind': kind})

				if value is not None:
					if not isinstance(value, tuple):
						value = (value,)

					value = {col: v for col, v in zip(EVOLUTION_REQUIREMENT_COLS[kind], value)}

					req_row = {
						'method': method_id, 'kind': kind, **value
					}

					if kind == 'item':
						req_row['base_method'] = 'item'
					elif kind == 'trademate':
						req_row['base_method'] = 'trade'

					evolution_rows[f'evolution_requirement_{kind}'].append(req_row)

	def get_form_name(pokemon, index):
		to_form_names = list(DB.H.exec(
			'select "name" from "pokemon_form" where "pokemon" = ? and "order" = ?',
			(pokemon, index)
		))

		if to_form_names:
			return to_form_names[0][0]
		else:
			# assume there's only one form for the evolution
			# (Burmy and PULSE-Abra)
			return ''

	for section in pbs_data:
		id_ = section.content['InternalName']
		pbs_evolutions = section.content.get('Evolutions')
		script_section = script_data.get(f'PBSpecies::{id_}', {})
		script_form_names = {
			int(i): name for i, name in script_section.get('FormName', {}).items()
			if not should_ignore_this_form(id_, name)
		}
			
		for form_index, form_name in list(DB.H.exec(
			'select "order", "name" from "pokemon_form" where "pokemon" = ?',
			(id_,)
		)):
			script_subsection = script_section.get(script_form_names.get(form_index), {})
			evolutions = []

			if form_name.startswith('PULSE'):
				continue # not that it really matters, but I'd opt for excluding irrelevant information

			if (id_, form_name) in MANUAL_EVOLUTIONS:
				evolutions = MANUAL_EVOLUTIONS[id_, form_name]

			elif 'GetEvo' in script_subsection:
				script_evolutions = script_subsection['GetEvo']

				for evolution_id, method_id, argument in script_evolutions:
					# the Galarian forms appear to have the order as method_id, argument, evolution_id
					# instead... fortunately we can ignore those
					evolution_id = lookup_pokemon(evolution_id)
					pbs_method, parse_argument = PBS_METHODS_BY_ID[int(method_id)]
					
					evolutions.append((
						pbs_method,
						parse_argument(argument),
						evolution_id,
						get_form_name(evolution_id, form_index),
					))

			elif section.content.get('Evolutions'):
				pbs_evolutions = [evo.strip() for evo in section.content['Evolutions'].split(',')]
				#pbs_evolutions = list(zip(pbs_evolutions[1::3], pbs_evolutions[2::3], pbs_evolutions[::3]))
				pbs_evolutions = list(zip(pbs_evolutions[::3], pbs_evolutions[1::3], pbs_evolutions[2::3]))

				for evolution_id, pbs_method, argument in pbs_evolutions:
					evolutions.append((
						pbs_method,
						argument,
						evolution_id,
						get_form_name(evolution_id, form_index),
					))

			if evolutions:
				for pbs_method, argument, evolution_id, evolution_form in evolutions:
					if form_index == 0: # no point repeating this for the other forms
						DB.H.exec(
							'update "pokemon" set "evolves_from" = ? where "id" = ?',
							(id_, evolution_id)
						)

					methods = EVOLUTION_METHOD_MAP[pbs_method](argument)

					for i, (method, requirements) in enumerate(methods):
						argument = str(argument)
						create_evolution_method(pbs_method, argument, i, method, requirements)

						pem_row = {
							'from': id_, 'from_form': form_name,
							'to': evolution_id, 'to_form': evolution_form,
							'method': evo_methods_by_pbs_name[pbs_method, argument, i]['id']
						}

						evolution_rows['pokemon_evolution_method'].append(pem_row)

	for table, rows in evolution_rows.items():
		fields = tuple(rows[0].keys())
		DB.H.bulk_insert(table, fields, (
			tuple(row[field] for field in fields)
			for row in rows
		))
