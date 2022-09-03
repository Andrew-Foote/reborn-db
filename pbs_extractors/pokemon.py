# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       env\Scripts\python -m pbs_extractors.pokemon

import apsw
from collections import defaultdict
from decimal import Decimal
import itertools as it
from utils import apsw_ext, pbs, sql

# latin1 because it contains some és in Pokémon encoded as e9
# note: we ignore gen8pokemon.txt, it appears to contain (rather confusingly) only data
# for pokemon up to gen 7, but is otherwise the same as this file
with open('PBS/pokemon.txt', newline='', encoding='latin1') as f:
	data = pbs.parse_config_style_file(f)

base_data = []
form_data = []
ev_data = []
egg_group_data = []
form_data = []
stat_data = []
level_move_data = []
egg_move_data = []
evolution_data = []
evolution_method_data = []
evolution_method_item_data = []
evolution_requirement_data = []
evolution_requirement_subdata = defaultdict(lambda: [])

for dict_ in data:
	base_dict = {}
	base_form_dict = {}
	pokemon_number = int(dict_['_SectionNumber'])

	if pokemon_number > 807:
		continue

	

	base_dict['number'] = pokemon_number
	pokemon_id = base_dict['id'] = dict_['InternalName']
	
	for k, v in dict_.items():
		if k in ('_SectionNumber', 'InternalName'):
			pass
		elif k == 'Name':
			if v == 'Nidoran':
				if dict_['GenderRate'] == 'AlwaysMale':
					gender_symbol = '♂'
				elif dict_['GenderRate'] == 'AlwaysFemale':
					gender_symbol = '♀'
				else:
					raise ValueError('non-fixed-gender Nidoran?!?')

				v += gender_symbol

			base_dict['name'] = v
		elif k == 'Type1':
			base_form_dict['type1_id'] = v
		elif k == 'Type2':
			base_form_dict['type2_id'] = v if v else None
		elif k == 'BaseStats':
			stat_ids = ('HP', 'ATK', 'DEF', 'SPD', 'SA', 'SD')
			stats = v.split(',')
			assert len(stat_ids) == len(stats)

			for stat_id, stat in zip(stat_ids, stats):
				stat = int(stat.strip())
				stat_data.append((pokemon_id, stat_id, stat))
		elif k == 'GenderRate':
			base_dict['male_chance'] = {
				'AlwaysMale': 1000,
				'FemaleOneEighth': 875,
				'Female25Percent': 750,
				'Female50Percent': 500,
				'Female75Percent': 250,
				'AlwaysFemale': 0,
				'Genderless': None,
			}[v]
		elif k == 'GrowthRate':
			base_dict['growth_rate_id'] = {
				'Medium': 'MEDIUMFAST',
				'Slow': 'SLOW',
				'Fast': 'FAST',
				'Parabolic': 'MEDIUMSLOW',
				'Erratic': 'ERRATIC',
				'Fluctuating': 'FLUCTUATING',
			}[v]
		elif k == 'BaseEXP':
			base_dict['base_exp'] = int(v)
		elif k == 'EffortPoints':
			stat_ids = ('HP', 'ATK', 'DEF', 'SPD', 'SA', 'SD')
			stats = v.split(',')
			assert len(stat_ids) == len(stats)

			for stat_id, stat in zip(stat_ids, stats):
				stat = int(stat.strip())
				ev_data.append((pokemon_id, stat_id, stat))
		elif k == 'Rareness':
			base_dict['catch_rate'] = int(v)
		elif k == 'Happiness':
			base_dict['base_friendship'] = int(v)
		elif k == 'Abilities':
			abilities = [ability.strip() for ability in v.split(',')]
			base_form_dict['ability1_id'] = abilities[0]
			base_form_dict['ability2_id'] = abilities[1] if len(abilities) > 1 else None
		elif k == 'HiddenAbility':
			base_form_dict['hidden_ability_id'] = v
		elif k == 'Moves':
			data = [datum.strip() for datum in v.split(',')]

			for i in range(0, len(data), 2):
				level = data[i]
				move_id = data[i + 1]
				level_move_data.append((pokemon_id, level, move_id))
		elif k == 'EggMoves':
			data = [datum.strip() for datum in v.split(',')]

			for move_id in data:
				egg_move_data.append((pokemon_id, move_id))
		elif k == 'Compatibility':
			compats = [compat.strip().upper() for compat in v.split(',')]

			for compat in compats:
				egg_group_data.append((pokemon_id, compat))
		elif k == 'StepsToHatch':
			base_dict['hatch_steps'] = int(v)
		elif k == 'Height':
			base_form_dict['height'] = int(Decimal(v) * 100)
		elif k == 'Weight':
			base_form_dict['weight'] = int(Decimal(v) * 10)
		elif k == 'Color':
			base_form_dict['color'] = v
		elif k == 'Habitat':
			base_dict['habitat'] = v
		elif k == 'Kind':
			base_dict['category'] = v
		elif k == 'Pokedex':
			base_dict['pokedex_entry'] = v
		elif k == 'Evolutions':
			data = [datum.strip() for datum in v.split(',')] if v else []

			for i in range(0, len(data), 3):
				evolution_id = data[i]
				method = data[i + 1]
				method_arg = data[i + 2] if i + 2 < len(data) else None
				evolution_data.append((evolution_id, pokemon_id))
				method_id = len(evolution_method_data)
				method_datum = [method_id, evolution_id]
				requirements = []

				if method in ('Level', 'Ninjask'):
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
				elif method == 'Item':
					method_datum.append('item')
					requirements.append(('item', method_arg))
				elif method == 'Trade':
					method_datum.append('trade')
				elif method == 'Happiness':
					method_datum.append('level')
					requirements.append(('friendship',))
				elif method == 'TradeItem':
					method_datum.append('trade')
					requirements.append(('held_item', method_arg))
				elif method == 'Location':
					method_datum.append('level')
					requirements.append(('location', int(method_arg)))
				elif method == 'Affection':
					method_datum.append('level')
					requirements.append(('friendship',))
					requirements.append(('move_type', 'FAIRY'))
				elif method == 'HappinessDay':
					method_datum.append('level')
					requirements.append(('friendship',))
					requirements.append(('time', 'day'))
				elif method == 'HappinessNight':
					method_datum.append('level')
					requirements.append(('friendship',))
					requirements.append(('time', 'night'))
				elif method == 'DayHoldItem':
					method_datum.append('level')
					requirements.append(('time', 'day'))
					requirements.append(('held_item', method_arg))
				elif method == 'NightHoldItem':
					method_datum.append('level')
					requirements.append(('time', 'night'))
					requirements.append(('held_item', method_arg))
				elif method == 'AttackGreater':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('stat_cmp', 'ATK', 'DEF', '>'))
				elif method == 'DefenseGreater':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('stat_cmp', 'ATK', 'DEF', '<'))
				elif method == 'AtkDefEqual':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('stat_cmp', 'ATK', 'DEF', '='))
				elif method == 'Silcoon':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('random', 0))
				elif method == 'Cascoon':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('random', 1))
				elif method == 'Cascoon':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('random', 1))
				elif method == 'ItemMale':
					method_datum.append('item')
					requirements.append(('item', method_arg))
					requirements.append(('gender', 'male'))
				elif method == 'ItemFemale':
					method_datum.append('item')
					evolution_method_item_data.append((evolution_id, 'item', method_arg))
					requirements.append(('gender', 'female'))
				elif method == 'Shedinja':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('leftover',))
				elif method == 'LevelMale':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('gender', 'male'))
				elif method == 'LevelFemale':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('gender', 'female'))
				elif method == 'HasInParty':
					method_datum.append('level')
					requirements.append(('teammate', method_arg))
				elif method == 'HasMove':
					method_datum.append('level')
					requirements.append(('move', method_arg))
				elif method == 'BadInfluence':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('teammate_type', 'DARK'))
				elif method == 'LevelDay':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('time', 'day'))
				elif method == 'LevelNight':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('time', 'night'))
				elif method == 'LevelRain':
					method_datum.append('level')
					requirements.append(('level', int(method_arg)))
					requirements.append(('weather', 'rain')) # note that this corresponds to weather types 1 (Rain), 2 (Storm) and 6 (HeavyRain)
				elif method == 'Beauty':
					pass # ignore this one
				else:
					raise RuntimeError(f'unhandled evo method: {method}')

				if len(method_datum) == 3:
					evolution_method_data.append(method_datum)

					for class_, *args in requirements:
						evolution_requirement_data.append((method_id, class_))

						if args:
							evolution_requirement_subdata[class_].append((method_id, class_, *args))

		elif k == 'WildItemCommon':
			base_form_dict['wild_item_id_common'] = v
		elif k == 'WildItemUncommon':
			base_form_dict['wild_item_id_uncommon'] = v
		elif k == 'WildItemRare':
			base_form_dict['wild_item_id_rare'] = v
		elif k == 'FormNames':
			pass # handle later on
		elif k in ('BattlerPlayerY', 'BattlerEnemyY', 'BattlerAltitude', 'RegionalNumbers'):
			# we don't care about these
			pass
		else:
			raise RuntimeError(f'unknown key: {k}')

	for k in ('type2_id', 'hidden_ability_id', 'wild_item_id_common', 'wild_item_id_uncommon', 'wild_item_id_rare'):
		if k not in base_form_dict:
			base_form_dict[k] = None

	if 'habitat' not in base_dict:
		base_dict['habitat'] = None

	# The PBS file doesn't contain data on some evolutions, add them in manually
	if pokemon_id == 'INKAY':
		evolution_id = 'MALAMAR'
		evolution_data.append((evolution_id, pokemon_id))
		method_id = len(evolution_method_data)
		evolution_method_data.append((method_id, evolution_id, 'level'))
		evolution_requirement_data.append((method_id, 'level'))
		evolution_requirement_subdata['level'].append((method_id, 'level', 30))
		evolution_requirement_data.append((method_id, 'cancel'))
	elif pokemon_id == 'KARRABLAST':
		evolution_id = 'ESCAVALIER'
		evolution_data.append((evolution_id, pokemon_id))
		method_id = len(evolution_method_data)
		evolution_method_data.append((method_id, evolution_id, 'trade'))
		evolution_requirement_data.append((method_id, 'trademate')),
		evolution_requirement_subdata['trademate'].append((method_id, 'trademate', 'SHELMET'))
	elif pokemon_id == 'SHELMET':
		evolution_id = 'ACCELGOR'
		evolution_data.append((evolution_id, pokemon_id))
		method_id = len(evolution_method_data)
		evolution_method_data.append((method_id, evolution_id, 'trade'))
		evolution_requirement_data.append((method_id, 'trademate')),
		evolution_requirement_subdata['trademate'].append((method_id, 'trademate', 'KARRABLAST'))
	# there are some extra evolution locations for these mons besides the ones listed
	elif pokemon_id in ('MAGNETON', 'NOSEPASS', 'CHARJABUG'):
		evolution_id = {'MAGNETON': 'MAGNEZONE', 'NOSEPASS': 'PROBOPASS', 'CHARJABUG': 'VIKAVOLT'}[pokemon_id]

		for map_id in (197, 198):
			method_id = len(evolution_method_data)
			evolution_method_data.append((method_id, evolution_id, 'level'))
			evolution_requirement_data.append((method_id, 'location'))
			evolution_requirement_subdata['location'].append((method_id, 'location', map_id))
	elif pokemon_id == 'CRABRAWLER':
		evolution_id = 'crabominable'

		for map_id in (364,366,373,374,375,376,377,378,379,380,384,385,386,387,388,389,390,391,392,393,394,395,396,397,398,399,400,401,402,403,430,431,432,434,435,436,439,440,441,442,457,458,459,460,461,462,463,464):
			method_id = len(evolution_method_data)
			evolution_method_data.append((method_id, evolution_id, 'level'))
			evolution_requirement_data.append((method_id, 'location'))
			evolution_requirement_subdata['location'].append((method_id, 'location', map_id))
	elif pokemon_id == 'CUBONE': # evolves into normal or alolan marowak depending on time/area
		# hmm, that means normal one has a location requirement too, though it'll be a long list
		evolution_id = 'MAROWAK-Alternate'
		
		for map_id in (152,552):
			method_id = len(evolution_method_data)
			evolution_method_data.append((method_id, evolution_id, 'level'))
			evolution_requirement_data.append((method_id, 'level'))
			evolution_requirement_subdata['level'].append((method_id, 'level', 28))
			evolution_requirement_data.append((method_id, 'location'))
			evolution_requirement_subdata['location'].append((method_id, 'location', map_id))

		method_id = len(evolution_method_data)
		evolution_method_data.append((method_id, evolution_id, 'level'))
		evolution_requirement_data.append((method_id, 'level'))
		evolution_requirement_subdata['level'].append((method_id, 'level', 28))
		evolution_requirement_data.append((method_id, 'time'))
		evolution_requirement_subdata['time'].append((method_id, 'time', 'night'))
		# need to handle the marowak-normal requirements too

	base_data.append((
		base_dict['number'], base_dict['id'], base_dict['name'], base_dict['male_chance'], base_dict['growth_rate_id'],
		base_dict['base_exp'], base_dict['catch_rate'], base_dict['base_friendship'],
		base_dict['hatch_steps'], base_dict['habitat'], base_dict['category'],
		base_dict['pokedex_entry']
	))

	forms = []

	if dict_.get('FormNames'):
		forms = [v.strip() for v in dict_['FormNames'].split(',')] if dict_['FormNames'] else []

	if not forms:
		if pokemon_id in ('THUNDURUS', 'TORNADUS', 'LANDORUS'):
			forms = ['Incarnate', 'Therian']
		elif pokemon_id == 'MELOETTA':
			forms = ['Aria', 'Pirouette']
		elif pokemon_id in ('DEERLING', 'SAWSBUCK'):
			forms = ['Spring', 'Summer', 'Autumn', 'Winter']
		else:
			forms.append(None)

	if forms == ['Meowstic', 'Meowstic']:
		forms = ['Male', 'Female']

	for i, form in enumerate(forms):
		if form == '':
			form = None

		form_dict = base_form_dict.copy()
		form_id = pokemon_id + ('' if form is None else '-' + form)

		# Form differences other than names need to be manually coded
		if form == 'Alternate':
			if pokemon_id in ('RATTATA', 'RATICATE'):
				form_dict['type1_id'] = 'DARK'
				form_dict['type2_id'] = 'NORMAL'
			elif pokemon_id == 'RAICHU':
				form_dict['type2_id'] = 'PSYCHIC'
			elif pokemon_id in ('SANDSHREW', 'SANDSLASH'):
				form_dict['type1_id'] = 'ICE'
				form_dict['type2_id'] = 'STEEL'
			elif pokemon_id == 'VULPIX':
				form_dict['type1_id'] = 'ICE'
			elif pokemon_id == 'NINETALES':
				form_dict['type1_id'] = 'ICE'
				form_dict['type2_id'] = 'FAIRY'
			elif pokemon_id in ('DIGLETT', 'DUGTRIO'):
				form_dict['type2_id'] = 'STEEL'
			elif pokemon_id in ('MEOWTH', 'PERSIAN'):
				form_dict['type1_id'] = 'DARK'
			elif pokemon_id in ('GEODUDE', 'GRAVELER', 'GOLEM'):
				form_dict['type2_id'] = 'ELECTRIC'
			elif pokemon_id in ('GRIMER', 'MUK'):
				form_dict['type2_id'] = 'DARK'
			elif pokemon_id == 'EXEGGUTOR':
				form_dict['type2_id'] = 'DRAGON'
			elif pokemon_id == 'MAROWAK':
				form_dict['type1_id'] = 'FIRE'
				form_dict['type2_id'] = 'GHOST'

		form_data.append((
			form_id, form, pokemon_id, i, form_dict['type1_id'],
			form_dict['type2_id'], form_dict['ability1_id'], form_dict['ability2_id'],
			form_dict['hidden_ability_id'], form_dict['wild_item_id_common'],
			form_dict['wild_item_id_uncommon'], form_dict['wild_item_id_rare'],
			form_dict['height'], form_dict['weight'], form_dict['color']
		))

apsw_ext.setup_error_handling()
db = apsw.Connection('db.sqlite')

with open('manual_data/stat.sql') as f:
	with db:
		db.cursor().execute(f.read())

with open('manual_data/egg_group.sql') as f:
	with db:
		db.cursor().execute(f.read())

with open('manual_data/growth_rate.sql') as f:
	with db:
		db.cursor().execute(f.read())

with db:
	query = f"""
		drop table if exists `evolution_requirement_weather`;
		drop table if exists `evolution_requirement_move_type`;
		drop table if exists `evolution_requirement_teammate_type`;
		drop table if exists `evolution_requirement_trademate`;
		drop table if exists `evolution_requirement_location`;
		drop table if exists `evolution_requirement_move`;
		drop table if exists `evolution_requirement_teammate`;
		drop table if exists `evolution_requirement_gender`;
		drop table if exists `evolution_requirement_random`;
		drop table if exists `evolution_requirement_stat_cmp`;
		drop table if exists `evolution_requirement_time`;
		drop table if exists `evolution_requirement_held_item`;
		drop table if exists `evolution_requirement_item`;
		drop table if exists `evolution_requirement_level`;
		drop table if exists `evolution_requirement`;
		drop table if exists `evolution_method`;
		drop table if exists `evolution`;
		drop table if exists `egg_move`;
		drop table if exists `level_move`;
		drop table if exists `base_stat`;
		drop table if exists `pokemon_form`;
		drop table if exists `pokemon_egg_group`;
		drop table if exists `ev_yield`;
		drop table if exists `pokemon`;

		create table `pokemon` (
			`number` integer primary key,
			`id` text not null unique check (`id` != ''),
			`name` text not null unique check (`name` != ''),
			`male_chance` integer check (`male_chance` >= 0 and `male_chance` <= 1000), -- out of 1000, null if genderless
			`growth_rate_id` text not null,
			`base_exp` integer not null check (`base_exp` >= 0),
			`catch_rate` integer not null check (`catch_rate` >= 0 and `catch_rate` <= 255), -- called "rareness" for some reason
			`base_friendship` integer not null check (`base_friendship` >= 0 and `base_friendship` <= 255),
			`hatch_steps` integer not null check (`hatch_steps` >= 0),
			`habitat` text check (`habitat` in ('Grassland', 'Forest', 'WatersEdge', 'Sea', 'Cave', 'Mountain', 'RoughTerrain', 'Urban', 'Rare')),
			`category` text not null check (`category` != ''),
			`pokedex_entry` text not null check (`pokedex_entry` != ''),
			foreign key (`growth_rate_id`) references `growth_rate` (`id`)
		) without rowid;

		insert into `pokemon` (
			`number`, `id`, `name`, `male_chance`, `growth_rate_id`, `base_exp`,
			`catch_rate`, `base_friendship`, `hatch_steps`, `habitat`, `category`,
			`pokedex_entry`
		)
		values
		{sql.placeholders_table(base_data)};

		create table `ev_yield` (
			`pokemon_id` text,
			`stat_id` text,
			`value` integer not null check (`value` >= 0 and `value` <= 255),
			primary key (`pokemon_id`, `stat_id`),
			foreign key (`pokemon_id`) references `pokemon` (`id`),
			foreign key (`stat_id`) references `stat` (`id`)
		) without rowid;

		insert into `ev_yield` (`pokemon_id`, `stat_id`, `value`)
		values
		{sql.placeholders_table(ev_data)};

		create table `pokemon_egg_group` (
			`pokemon_id` text,
			`egg_group_id` not null,
			primary key (`pokemon_id`, `egg_group_id`),
			foreign key (`pokemon_id`) references `pokemon` (`id`),
			foreign key (`egg_group_id`) references `egg_group` (`id`)
		) without rowid;

		insert into `pokemon_egg_group` (`pokemon_id`, `egg_group_id`)
		values
		{sql.placeholders_table(egg_group_data)};

		create table `pokemon_form` (
			`id` text primary key,
			`name` text check (`name` != ''),
			`pokemon_id` text not null,
			`index` integer,
			`type1_id` text not null,
			`type2_id` text,
			`ability1_id` text not null,
			`ability2_id` text,
			`hidden_ability_id` text,
			`wild_item_id_common` text,
			`wild_item_id_uncommon` text,
			`wild_item_id_rare` text,
			`height` integer not null check (`height` >= 0), -- in centimetres
			`weight` integer not null check (`weight` >= 0), -- in tenths of a kilogram (100g each)			
			`color` text not null check (`color` != ''),
			unique (`pokemon_id`, `index`),
			foreign key (`pokemon_id`) references `pokemon` (`id`),
			foreign key (`type1_id`) references `type` (`id`),
			foreign key (`type2_id`) references `type` (`id`),
			foreign key (`ability1_id`) references `ability` (`id`),
			foreign key (`ability2_id`) references `ability` (`id`),
			foreign key (`hidden_ability_id`) references `ability` (`id`),
			foreign key (`wild_item_id_common`) references `item` (`id`),
			foreign key (`wild_item_id_uncommon`) references `item` (`id`),
			foreign key (`wild_item_id_rare`) references `item` (`id`)
		);

		insert into `pokemon_form` (
			`id`, `name`, `pokemon_id`, `index`, `type1_id`, `type2_id`, `ability1_id`, `ability2_id`, `hidden_ability_id`,
			`wild_item_id_common`, `wild_item_id_uncommon`, `wild_item_id_rare`, `height`, `weight`, `color`
		)
		values
		{sql.placeholders_table(form_data)};

		create table `base_stat` (
			`pokemon_form_id` text,
			`stat_id` text,
			`value` integer not null check (`value` >= 0 and `value` <= 255),
			primary key (`pokemon_form_id`, `stat_id`),
			foreign key (`pokemon_form_id`) references `pokemon_form` (`id`),
			foreign key (`stat_id`) references `stat` (`id`)
		) without rowid;

		insert into `base_stat` (`pokemon_form_id`, `stat_id`, `value`)
		values
		{sql.placeholders_table(stat_data)};
	"""

	# can't do it all in one call to execute(), too many parameters

	db.cursor().execute(query, it.chain(
		it.chain.from_iterable(base_data),
		it.chain.from_iterable(ev_data),
		it.chain.from_iterable(egg_group_data),
		it.chain.from_iterable(form_data),
		it.chain.from_iterable(stat_data)
	))

	db.cursor().execute(f"""
		create table `level_move` (
			`pokemon_form_id` text not null,
			`level` integer check (`level` >= 0),
			`move_id` text,
			-- on conflict replace is for Medicham, which has Bide at level 1 listed twice in the PBS file
			primary key (`pokemon_form_id`, `level`, `move_id`) on conflict replace,
			foreign key (`pokemon_form_id`) references `pokemon_form` (`id`),
			foreign key (`move_id`) references `move` (`id`)
		) without rowid;
	""")

	apsw_ext.bulk_insert(db, 'level_move', ('pokemon_form_id', 'level', 'move_id'), level_move_data)

	db.cursor().execute(f"""
		create table `egg_move` (
			`pokemon_form_id` text,
			`move_id` text not null,
			primary key (`pokemon_form_id`, `move_id`),
			foreign key (`pokemon_form_id`) references `pokemon_form` (`id`),
			foreign key (`move_id`) references `move` (`id`)
		) without rowid;
	""")

	apsw_ext.bulk_insert(db, 'egg_move', ('pokemon_form_id', 'move_id'), egg_move_data)

	query = f"""
		-- Evolution applies to forms rather than Pokémon themselves, solely because of
		-- Burmy/Wormadam.

		create table `evolution` (
			`new_form_id` text primary key on conflict replace,
			`old_form_id` text not null,
			foreign key (`new_form_id`) references `pokemon_form` (`id`),
			foreign key (`old_form_id`) references `pokemon_form` (`id`)
		) without rowid;

		insert into `evolution` (`new_form_id`, `old_form_id`)
		values
		{sql.placeholders_table(evolution_data)};

		-- Pokémon evolve by one of three basic methods: levelling up, having an item used on them,
		-- or being traded. Additional requirements are encoded in the `evolution_requirement`
		-- table.
		--
		-- An evolution may have multiple linked methods, in which case any of those methods will
		-- work (this is only used for Leafeon and Glaceon).
		
		create table `evolution_method` (
			`id` integer primary key,
			`evolution_id` text,
			`method` text not null check (`method` in ('level', 'item', 'trade')),
			foreign key (`evolution_id`) references `pokemon_form` (`id`)
		);

		insert into `evolution_method` (`id`, `evolution_id`, `method`)
		values
		{sql.placeholders_table(evolution_method_data)};

		create table `evolution_requirement` (
			`method_id` integer,
			`class` text not null check (`class` in (
				'level', 'item',
				'friendship', 'held_item', 'time', 'stat_cmp',
				'random', 'leftover',
				'gender', 'teammate', 'move', 'location',
				'trademate',
				'teammate_type', 'cancel', 'move_type', 'weather'
			)),
			primary key (`method_id`, `class`),
			foreign key (`method_id`) references `evolution_method` (`id`)
		) without rowid;

		insert into `evolution_requirement` (`method_id`, `class`)
		values
		{sql.placeholders_table(evolution_requirement_data)};

		-- The Pokémon must be at or above the given level.
		create table `evolution_requirement_level` (
			`method_id` integer,
			`class` text check (`class` = 'level'),
			`level` integer not null check (`level` >= 1),
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`)
		) without rowid;

		insert into `evolution_requirement_level` (`method_id`, `class`, `level`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['level'])};

		-- The item used on the Pokémon must be the given item.
		create table `evolution_requirement_item` (
			`method_id` integer,
			`class` text check (`class` = 'item'),
			`item_id` text not null,
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`),
			foreign key (`item_id`) references `item` (`id`)
		) without rowid;

		insert into `evolution_requirement_item` (`method_id`, `class`, `item_id`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['item'])};

		-- 'friendship' (no table)
		-- The Pokémon must have attained a friendship value of 220 or more.

		-- The Pokémon must be holding the given item. As a side-effect, the item is consumed.
		create table `evolution_requirement_held_item` (
			`method_id` integer,
			`class` text check (`class` = 'held_item'),
			`item_id` text not null,
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`),
			foreign key (`item_id`) references `item` (`id`)
		) without rowid;

		insert into `evolution_requirement_held_item` (`method_id`, `class`, `item_id`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['held_item'])};

		-- The evolution must take place at the given time of day, which can be day, night or dusk.
		-- Note that the hours are partitioned between day and night; dusk is a sub-period of the
		-- day, not mutually exclusive with it. Dusk is checked before the other two periods, for
		-- this reason (otherwise Rockruff would never be able to evolve into its Dusk form, since
		-- Reborn removed the ability-based requirement for its evolution).
		create table `evolution_requirement_time` (
			`method_id` integer,
			`class` text check (`class` = 'time'),
			`time` text not null check (`time` in ('day', 'night', 'dusk')),
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`)
		) without rowid;

		insert into `evolution_requirement_time` (`method_id`, `class`, `time`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['time'])};

		-- Two of the Pokémon's stats must satisfy the given relation.
		create table `evolution_requirement_stat_cmp` (
			`method_id` integer,
			`class` text check (`class` = 'stat_cmp'),
			`stat1_id` text not null,
			`stat2_id` text not null,
			`operator` text not null check (`operator` in ('>', '<', '=')),
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`),
			foreign key (`stat1_id`) references `stat` (`id`),
			foreign key (`stat2_id`) references `stat` (`id`)
		) without rowid;

		insert into `evolution_requirement_stat_cmp` (`method_id`, `class`, `stat1_id`, `stat2_id`, `operator`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['stat_cmp'])};

		-- The Pokémon's personality value must belong to the given "polarity"---the polarities
		-- are two equally-sized, disjoint subsets which partition the set of all possible
		-- personality values.
		create table `evolution_requirement_random` (
			`method_id` integer,
			`class` text check (`class` = 'random'),
			`polarity` integer not null check (`polarity` in (0, 1)),
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`)
		) without rowid;

		insert into `evolution_requirement_random` (`method_id`, `class`, `polarity`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['random'])};

		-- 'leftover' (no table)
		-- There must be an empty slot in the party and a Poké Ball in the bag. As a side-effect,
		-- the Poké Ball is consumed; also, when this requirement is active, rather than replacing
		-- the original Pokémon, the evolved Pokémon simply appears in the empty slot; the original
		-- Pokémon remains in its slot, though it may evolve into something else.

		-- The Pokémon must be the given gender.
		create table `evolution_requirement_gender` (
			`method_id` integer,
			`class` text check (`class` = 'gender'),
			`gender` text check (`gender` in ('male', 'female')),
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`)
		) without rowid;

		insert into `evolution_requirement_gender` (`method_id`, `class`, `gender`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['gender'])};

		-- The Pokémon must have a Pokémon of the given species as a teammate.
		create table `evolution_requirement_teammate` (
			`method_id` integer,
			`class` text check (`class` = 'teammate'),
			`pokemon_id` text not null,
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`),
			foreign key (`pokemon_id`) references `pokemon` (`id`)
		) without rowid;

		insert into `evolution_requirement_teammate` (`method_id`, `class`, `pokemon_id`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['teammate'])};

		-- The Pokémon must know the given move.
		create table `evolution_requirement_move` (
			`method_id` integer,
			`class` text check (`class` = 'move'),
			`move_id` text not null,
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`),
			foreign key (`move_id`) references `move` (`id`)
		) without rowid;

		insert into `evolution_requirement_move` (`method_id`, `class`, `move_id`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['move'])};

		-- The evolution must take place at the given location. There can be multiple requirements
		-- of this class, in which case any of the given locations will work.
		create table `evolution_requirement_location` (
			`method_id` integer,
			`class` text check (`class` = 'location'),
			`location_id` text not null,
			primary key (`method_id`, `class`, `location_id`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`),
			foreign key (`location_id`) references `location` (`id`)
		) without rowid;

		insert into `evolution_requirement_location` (`method_id`, `class`, `location_id`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['location'])};

		-- The Pokémon must be being traded with a Pokémon of the given species.
		create table `evolution_requirement_trademate` (
			`method_id` integer,
			`class` text check (`class` = 'trademate'),
			`pokemon_id` text not null,
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`),
			foreign key (`pokemon_id`) references `pokemon` (`id`)
		) without rowid;

		insert into `evolution_requirement_trademate` (`method_id`, `class`, `pokemon_id`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['trademate'])};

		-- The Pokémon must have a teammate of the given type.
		create table `evolution_requirement_teammate_type` (
			`method_id` integer,
			`class` text check (`class` = 'teammate_type'),
			`type_id` text not null,
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`),
			foreign key (`type_id`) references `type` (`id`)
		) without rowid;

		insert into `evolution_requirement_teammate_type` (`method_id`, `class`, `type_id`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['teammate_type'])};

		-- 'cancel' (no table)
		-- This requirement does not prevent the Pokémon from attempting to evolve, but it means
		-- that the evolution will fail by default, and the player has to do what would normally be
		-- cancelling the evolution in order to make it succeed.

		-- The Pokémon must know a move of the given type.
		create table `evolution_requirement_move_type` (
			`method_id` integer,
			`class` text check (`class` = 'move_type'),
			`type_id` text not null,
			primary key (`method_id`, `class`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`),
			foreign key (`type_id`) references `type` (`id`)
		) without rowid;

		insert into `evolution_requirement_move_type` (`method_id`, `class`, `type_id`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['move_type'])};

		-- The evolution must take place in the given overworld weather.  There can be multiple
		-- requirements of this class, in which case any of the given locations will work.
		create table `evolution_requirement_weather` (
			`method_id` integer,
			`class` text check (`class` = 'weather'),
			`weather` text not null check (`weather` in ('clear', 'sun', 'rain', 'sandstorm', 'hail', 'fog', 'wind', 'storm')),
			primary key (`method_id`, `class`, `weather`),
			foreign key (`method_id`, `class`) references `evolution_requirement` (`method_id`, `class`)
		) without rowid;

		insert into `evolution_requirement_weather` (`method_id`, `class`, `weather`)
		values
		{sql.placeholders_table(evolution_requirement_subdata['weather'])};
	"""

	db.cursor().execute(query, it.chain(
		it.chain.from_iterable(evolution_data),
		it.chain.from_iterable(evolution_method_data),
		it.chain.from_iterable(evolution_requirement_data),
		it.chain.from_iterable(evolution_requirement_subdata['level']),
		it.chain.from_iterable(evolution_requirement_subdata['item']),
		it.chain.from_iterable(evolution_requirement_subdata['held_item']),
		it.chain.from_iterable(evolution_requirement_subdata['time']),
		it.chain.from_iterable(evolution_requirement_subdata['stat_cmp']),
		it.chain.from_iterable(evolution_requirement_subdata['random']),
		it.chain.from_iterable(evolution_requirement_subdata['gender']),
		it.chain.from_iterable(evolution_requirement_subdata['teammate']),
		it.chain.from_iterable(evolution_requirement_subdata['move']),
		it.chain.from_iterable(evolution_requirement_subdata['location']),
		it.chain.from_iterable(evolution_requirement_subdata['trademate']),
		it.chain.from_iterable(evolution_requirement_subdata['teammate_type']),
		it.chain.from_iterable(evolution_requirement_subdata['move_type']),
		it.chain.from_iterable(evolution_requirement_subdata['weather']),
	))
