import importlib
from pathlib import Path
import shutil

generator_names = (
	'index', 'admin', 'statcalc',
	'pokemon_list', 'pokemon_view',
	'pokemon_sprites',
	'move_list', 'move_view',
	'ability_list', 'ability_view',
	'item_list', 'item_view',
	'area_list', 'area_view',
	'trainer_list', 'trainer_view',
	'evolution_area'
)

generators = [importlib.import_module(f'.{name}', 'generators') for name in generator_names]

SITE_PATH = Path('site')
NONGENERATED_SUBPATHS = [Path('site') / sp for sp in ('db.sqlite', 'style.css', 'js', 'img')]

def run():
	# remove any files we don't need any more
	assert SITE_PATH.is_dir()

	for subpath in SITE_PATH.iterdir():
		if subpath not in NONGENERATED_SUBPATHS:
			print(f'Deleting {subpath}')

			if subpath.is_dir():
				shutil.rmtree(subpath)
			else:
				subpath.unlink()

	for name, generator in zip(generator_names, generators):
		print(f'Generating {name}...')
		generator.run()

if __name__ == '__main__':
	run()