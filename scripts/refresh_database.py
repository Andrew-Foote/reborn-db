import importlib
from reborndb import DB

extractor_names = [
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

EXCEPTIONS = (
	'event_encounter',
	'marshal_map',
	'marshal_map_event',
	'marshal_map_event_page',
	'marshal_map_event_switch_condition',
	'marshal_map_event_variable_condition'
	'marshal_map_event_self_switch_condition',
	'marshal_map_event_route',
	'marshal_map_event_route_command',
	'marshal_map_event_route_command_parameter',
	'marshal_map_event_command',
	'marshal_map_event_command_parameter'
)

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