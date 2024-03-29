import importlib
import os
from reborndb import DB

extractor_names = [
	'switches_and_variables',
	'tilesets',
	'common_events',
	'metadata',
	'types',
	'abilities',
	'moves',
	'items',
	'pokemon',
	'pokemon_sprite',
	'tm',
	'encounters',
	'fossils',
	'trainertypes',
	'trainers',
	'trainerlists',
]

#extractors = [importlib.import_module(f'.{name}', 'reborndb.extractors') for name in extractor_names]

EXCEPTIONS = [
	'event_encounter',
	'encounter_common_event',
	'encounter_map_event',
    'event_encounter_ot',
    'event_encounter_extra_move_set',
    'event_encounter_form_note',
    'event_encounter_move',
	'event_encounter',
	'event_encounter_iv',
	'event_encounter_old',
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

	if os.environ.get('FULL'):
		extractor_names.append('event_encounters')
		extractor_names.append('map_data')
	elif os.environ.get('EVENT_ENCOUNTERS'):
		extractor_names.append('event_encounters')
	elif os.environ.get('MAP_DATA'):
		metadata_index = extractor_names.index('metadata')
		extractor_names.insert(metadata_index, 'map_data')
	
	print('Creating schema... ', end='')
	with DB.H.transaction(): DB.H.execscript('schema.sql')

	print('seeding... ', end ='')
	with DB.H.transaction(): DB.H.execscript('seed.sql')

	print('done.')

	extractors = [importlib.import_module(f'.{name}', 'reborndb.extractors') for name in extractor_names]

	for name, extractor in zip(extractor_names, extractors):
		print(f'Extracting {name}...')
		extractor.extract()
		
	print('post-seeding...', end='')
	with DB.H.transaction(): DB.H.execscript('post_seed.sql')

if __name__ == '__main__':
	run()