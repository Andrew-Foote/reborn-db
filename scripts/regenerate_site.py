import importlib
from pathlib import Path
import shutil
from reborndb import settings

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

NONGENERATED_SUBPATHS = [settings.SITE_PATH / sp for sp in ('.git', '.gitignore', 'db.sqlite', 'style.css', 'js', 'img')]

def run():
	# remove any files we don't need any more
	assert settings.SITE_PATH.is_dir()

	for subpath in settings.SITE_PATH.iterdir():
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