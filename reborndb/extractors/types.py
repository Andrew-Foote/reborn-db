from reborndb import DB
from reborndb import settings
from reborndb import pbs

def extract():
	data = pbs.load('types')
	type_rows = []
	type_effect_rows = []

	for section in data:
		code = int(section.header)
		id_ = section.content['InternalName']
		name = section.content['Name']
		is_pseudo = pbs.parse_bool(section.content.get('IsPseudoType', 'false'))
		damage_class = ['Physical', 'Special'][pbs.parse_bool(section.content.get('IsSpecialType', 'false'))]
		
		icon_name = 'Qmark' if is_pseudo else id_.capitalize()
		icon_path = settings.REBORN_GRAPHICS_PATH / f'Icons/field{icon_name}.png'
		with open(icon_path, 'rb') as f: icon = f.read()

		type_rows.append((code, id_, name, is_pseudo, damage_class, icon))

		multipliers = {'Weaknesses': 2, 'Resistances': 0.5, 'Immunities': 0}

		for key, multiplier in multipliers.items():
			for other_id in section.content.get(key, '').split(','):
				other_id = other_id.strip()
				if not other_id: continue
				type_effect_rows.append((other_id, id_, multiplier))

	with DB.H.transaction():
		DB.H.bulk_insert('type', ('code', 'id', 'name', 'is_pseudo', 'damage_class', 'icon'), type_rows)
		DB.H.bulk_insert('type_effect', ('attacking_type', 'defending_type', 'multiplier'), type_effect_rows)

if __name__ == '__main__':
	extract()