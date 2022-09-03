import apsw
from pathlib import Path
from reborndb import DB
from reborndb import pbs
from reborndb import settings

def extract():
	pbs_data = pbs.load('trainertypes')
	rows = []

	for row in pbs_data:
		id_ = row[1]

		code = int(row[0])
		base_prize = int(row[3]) if row[3] else 30

		out_row = [
			code,
			id_,
			row[2], # name
			base_prize, # base prize
			row[4] or None, # bg music
			row[5] or None, # win music
			row[6] or None, # intro music
			None if not row[7] or row[7] == 'Mixed' else row[7], # gender
			int(row[8]) if row[8] else base_prize, # skill
		]

		# graphics
		graphics_path = settings.REBORN_INSTALL_PATH / 'Graphics/Characters'
		padded_code = f'{code:0>3}'

		try:
			with (graphics_path / f'trainer{padded_code}.png').open('rb') as f:
				battle_sprite = f.read()
		except FileNotFoundError:
			battle_sprite = None

		# try:
		# 	# this is actually incorect, the trchar numbers have no relation to the
		# 	# trainertype codes---so ignore this column for now
		# 	with (graphics_path / f'trchar{padded_code}.png').open('rb') as f:
		# 		out_row['overworld_charset'] = f.read()
		# except FileNotFoundError:
		# 	out_row['overworld_charset'] = None

		try:
			with (graphics_path / f'trback{padded_code}.png').open('rb') as f:
				battle_back_sprite = f.read()
		except FileNotFoundError:
			battle_back_sprite = None

		out_row.extend((battle_sprite, battle_back_sprite))
		rows.append(tuple(out_row))

	with DB.H.transaction():
		DB.H.bulk_insert('trainer_type', (
			'code', 'id', 'name', 'base_prize', 'bg_music', 'win_music', 'intro_music', 'gender', 'skill',
			'battle_sprite', 'battle_back_sprite'
		), rows)

