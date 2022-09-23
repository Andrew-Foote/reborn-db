import importlib
from reborndb import DB

extractor_names = [
	'switches_and_variables',
	'tilesets',
	'abilities',
	'types',
	'moves',
	'items',
	'metadata',
	'pokemon',
	'pokemon_sprite',
	'encounters',
	'tm',
	'trainertypes',
	'trainers',
]

extractors = [importlib.import_module(f'.{name}', 'reborndb.extractors') for name in extractor_names]

EXCEPTIONS = [
	'event_encounter',
	'marshal_mapdata'
]

def run():
	DB.H.dropall(exceptions=EXCEPTIONS)
	
	print('Creating schema... ', end='')
	with DB.H.transaction(): DB.H.execscript('schema.sql')

	print('seeding... ', end ='')
	with DB.H.transaction(): DB.H.execscript('seed.sql')

	print('done.')

	for name, extractor in zip(extractor_names, extractors):
		print(f'Extracting {name}...')
		extractor.extract()
		
	print('post-seeding...', end='')
	with DB.H.transaction(): DB.H.execscript('post_seed.sql')

if __name__ == '__main__':
	run()