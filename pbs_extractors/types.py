# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       `env\Scripts\python -m pbs_extractors.types

from reborndb import DB
from reborndb import pbs

def extract(db):
	data = pbs.load('types')
	types = []
	type_effects = []

	for section in data:
		code = int(section.header)
		id_ = section.content['InternalName']
		name = section.Content['Name']
		is_pseudo = pbs.parse_bool(section.content.get('IsPseudoType', 'false'))
		damage_class = ['Physical', 'Special'][pbs.parse_bool(section.content.get('IsSpecialType', 'false'))]
		types.append((code, id_, name, is_pseudo, damage_class))

		multipliers = {'Weaknesses': 2, 'Resistances': 0.5, 'Immunities': 0}

		for key, multiplier in multipliers.items():
			for other_id in section.content.get(key, '').split(','):
				other_id = other_id.strip()
				if not other_id: continue
				type_effects.append((other_id, id_, multiplier))

	DB.H.bulk_insert('type', ('code', 'id', 'name', 'is_pseudo', 'damage_class'), types)
	DB.H.bulk_insert('type_effect', ('attacking_type', 'defending_type', 'multiplier'), type_effects)
