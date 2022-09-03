import apsw
from collections import defaultdict
from pathlib import Path
from utils import apsw_ext, pbs
from settings import REBORN_INSTALL_PATH

def extract(db):
	pbs_data = pbs.load('trainertypes')
	rows = defaultdict(lambda: [])

	for row in pbs_data:
		id_ = row[1]

		code = int(row[0])
		base_prize = int(row[3]) if row[3] else 30

		out_row = {
			'code': code,
			'id': id_,
			'name': row[2],
			'base_prize': base_prize,
			'bg_music': row[4] or None,
			'win_music': row[5] or None,
			'intro_music': row[6] or None,
			'gender': None if not row[7] or row[7] == 'Mixed' else row[7],
			'skill': int(row[8]) if row[8] else base_prize,
		}

		# graphics
		graphics_path = REBORN_INSTALL_PATH / 'Graphics/Characters'
		padded_code = f'{code:0>3}'

		try:
			with (graphics_path / f'trainer{padded_code}.png').open('rb') as f:
				out_row['battle_sprite'] = f.read()
		except FileNotFoundError:
			out_row['battle_sprite'] = None

		try:
			# this is actually incorect, the trchar numbers have no relation to the
			# trainertype codes---so ignore this column for now
			with (graphics_path / f'trchar{padded_code}.png').open('rb') as f:
				out_row['overworld_charset'] = f.read()
		except FileNotFoundError:
			out_row['overworld_charset'] = None

		try:
			with (graphics_path / f'trback{padded_code}.png').open('rb') as f:
				out_row['battle_back_sprite'] = f.read()
		except FileNotFoundError:
			out_row['battle_back_sprite'] = None

		rows['trainer_type'].append(out_row)

	apsw_ext.bulk_insert_multi(db, rows)

