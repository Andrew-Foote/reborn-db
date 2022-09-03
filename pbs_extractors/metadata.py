# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       `env\Scripts\python -m pbs_extractors.metadata

from collections import defaultdict
from utils import apsw_ext, pbs

FIELDS_WITH_DEFAULTS = {
	'bicycle_music': 'BicycleBGM',
	'surf_music': 'SurfBGM',
	'wild_battle_music': 'WildBattleBGM',
	'wild_win_music': 'WildVictoryME',
	'trainer_battle_music': 'TrainerBattleBGM',
	'trainer_win_music': 'TrainerVictoryME',
}

BOOLEAN_FIELDS = {
	'has_location_signpost': ('ShowArea', lambda r: False),
	'outdoor': ('Outdoor', lambda r: False),
	'bicycle_usable': ('Bicycle', lambda r: r['outdoor']),
	'bicycle_required': ('BicycleAlways', lambda r: False),
	'flashable': ('DarkMap', lambda r: False),
	'in_safari_zone': ('SafariMap', lambda r: False),
}

def extract(db):
	pbs_data = pbs.load('metadata')
	rows = defaultdict(lambda: [])
	defaults = {}

	for section in pbs_data:
		id_ = int(section.header)
		row_as_dict = defaults if id_ == 0 else {'id': id_}

		for field, pbs_field in FIELDS_WITH_DEFAULTS.items():
			row_as_dict[field] = section.content.get(pbs_field, defaults.get(field))

		if id_ == 0: continue
		
		row_as_dict['name'] = section.comment
		row_as_dict['battle_backdrop'] = section.content.get('BattleBack')

		for field, (pbs_field, default_cb) in BOOLEAN_FIELDS.items():
			if pbs_field in section.content:
				row_as_dict[field] = pbs.parse_bool(section.content[pbs_field])
			else:
				row_as_dict[field] = default_cb(row_as_dict)

		position_fields = ('region_id', 'x', 'y')

		if (position_info := section.content.get('MapPosition')):
			row_as_dict |= {field: int(value.strip()) for field, value in zip(position_fields, position_info.split(','))}
		else:
			row_as_dict |= {field: None for field in position_fields}

		teleport_fields = ('sets_teleport_map', 'sets_teleport_x', 'sets_teleport_y')

		if (teleport_info := section.content.get('HealingSpot')):
			row_as_dict |= {field: int(value.strip()) for field, value in zip(teleport_fields, teleport_info.split(','))}
		else:
			row_as_dict |= {field: None for field in teleport_fields}

		if (weather_info := section.content.get('Weather')):
			weather, chance = (value.strip() for value in weather_info.split(','))
			row_as_dict |= {'weather': weather, 'weather_chance': int(chance)}
		else:
			row_as_dict |= {'weather': None, 'weather_chance': None}

		row_as_dict['underwater_map'] = int(section.content['DiveMap']) if 'DiveMap' in section.content else None

		descs = {
			14: 'Coral Ward pre-restoration',
			27: 'Pyrous Mountain summit',
			29: 'Opal Ward pre-restoration',
			30: 'Apophyll Cave 1F',
			36: 'Obsidia Ward pre-restoration',
			40: 'Opal Ward - under Opal Bridge',
			41: 'Underground Railnet - Peridot side',
			46: 'Lower Peridot Ward - fisherman\'s pool',
			52: 'South Peridot Alley pre-restoration',
			57: 'Peridot Ward pre-restoration - Seacrest\'s garden',
			58: 'North Peridot Alley pre-restoration',
			97: 'Coral Ward pre-restoration',
			103: 'Underground Railnet - Obsidia side', #?
			105: 'Obsidia Alleyway pre-restoration',
			109: 'Coral Ward pre-restoration',
			128: 'Onyx Ward pre-restoration - rooftop garden',
			130: 'Jasper Ward pre-restoration',
			132: 'Malchous Forest Park pre-restoration',
			134: 'Jasper Ward pre-restoration',
			135: 'Jasper Ward pre-restoration',
			137: 'Jasper Ward pre-restoration',
			138: 'Jasper Ward pre-restoration',
			149: 'Beryl Ward pre-restoration',
			151: 'Beryl Ward pre-restoration - Cemetery path',
			151: 'Beryl Cemetery pre-restoration',
			165: 'North Obsidia Alleyway pre-restoration',
			170: 'Lapis Alleyway pre-restoration',
			177: 'Grand Stairway 1F',
			196: 'Underground Railnet - north',
			198: 'Yureyu Power Plant - front rooms',
			206: 'Azurine Island pre-restoration',
			228: 'Underground Railnet - Obsidia Slums side',
			229: 'Underground Railnet - depths',
		}

		row_as_dict['desc'] = descs.get(id_, row_as_dict['name'])

		rows['map'].append(row_as_dict)

	apsw_ext.bulk_insert_multi(db, rows)

if __name__ == '__main__':
	db = apsw_ext.connect()

	with db:
		extract(db)
