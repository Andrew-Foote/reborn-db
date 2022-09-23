import io
import numpy as np
from parsers.rpg import tilesets
from reborndb import DB, settings

def extract():
	tslist = tilesets.load()
	tsrows = []
	tsatrows = []
	tsfiles = set()
	autotiles = set()
	panoramas = set()

	for ts in tslist:
		tsfiles.add(ts.tileset_name)

		if ts.panorama_name:
			panorama = ts.panorama_name			
			panoramas.add(panorama)
		else:
			panorama = None

		arrayblobs = []

		for field in ('passages', 'priorities', 'terrain_tags'):
			stream = io.BytesIO()
			np.save(stream, getattr(ts, field).array)
			arrayblobs.append(stream.getvalue())

		tsrows.append((ts.name, ts.id_, ts.tileset_name, panorama, *arrayblobs))

		for i, atname in enumerate(ts.autotile_names):
			if atname:
				autotiles.add(atname)
				tsatrows.append((ts.name, i, atname))

	tsfrows = []

	for tsfname in tsfiles:
		fname = settings.REBORN_GRAPHICS_PATH / 'Tilesets'  / f'{tsfname}.png'

		with open(fname, 'rb') as f:
			tsfrows.append((tsfname, f.read()))

	atrows = []

	for autotile in autotiles:
		fname = settings.REBORN_GRAPHICS_PATH / 'Autotiles' / f'{autotile}.png'

		with open(fname, 'rb') as f:
			atrows.append((autotile, f.read()))

	panrows = []

	for panorama in panoramas:
		fname = settings.REBORN_GRAPHICS_PATH / 'Panoramas' / f'{panorama}.png'

		with open(fname, 'rb') as f:
			panrows.append((panorama, f.read()))

	with DB.H.transaction():
		DB.H.bulk_insert('tileset_file', ('name', 'content'), tsfrows)
		DB.H.bulk_insert('autotile', ('name', 'image'), atrows)
		DB.H.bulk_insert('panorama', ('name', 'image'), panrows)
		DB.H.bulk_insert('tileset', ('name', 'id', 'file', 'panorama', 'passages', 'priorities', 'terrain_tags'), tsrows)
		DB.H.bulk_insert('tileset_autotile', ('tileset', 'index', 'autotile'), tsatrows)
