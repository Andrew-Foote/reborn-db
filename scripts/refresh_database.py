import importlib
from reborndb import DB

extractor_names = [
	'switches_and_variables',
	'tilesets',
	'common_events',
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
	'marshal_mapdata',
	'map_event',
	'event_page',
	'event_page_switch_condition',
	'event_page_variable_condition',
	'event_page_self_switch_condition',
	'event_page_tile',
	'event_page_character'
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