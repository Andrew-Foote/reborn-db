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
	'event_page_trigger',
	'event_page',
	'event_page_switch_condition',
	'event_page_variable_condition',
	'event_page_self_switch_condition',
	'event_page_tile',
	'event_page_character',
	'parameter_type',
	'switch_state',
	'cancel_type',
	'appoint_type',
	'comparison',
	'bound_type',
	'diff_type',
	'text_position',
	'move_command_type',
	'move_command_parameter',
	'move_command',
	'event_page_move_command',
	'move_command_integer_argument',
	'move_command_text_argument',
	'move_command_audio_file_argument',
	'move_command_direction_argument',
	'event_command_type',
	'event_command_subtype',
	'event_command_parameter',
	'event_command',
	'common_event_command',
	'event_page_command',
	'event_command_integer_argument',
	'event_command_text_argument',
	'event_command_bool_argument',
	'event_command_audio_file_argument',
	'event_command_direction_argument',
	'event_command_choices_array_argument',
	'event_command_color_argument',
	'event_command_cancel_type_argument',
	'event_command_text_position_argument',
	'event_command_switch_state_argument',
	'event_command_diff_type_argument',
	'event_command_appoint_type_argument',
	'event_command_move_route_argument',
	'event_command_move_route_argument_move_command',
	'event_command_comparison_argument',
	'event_command_bound_type_argument',
]

def run():
	DB.H.dropall(exceptions=EXCEPTIONS)

	if os.environ.get('FULL'):
		extractor_names.append('event_encounters')
		extractor_names.append('map_data')
	elif os.environ.get('EVENT_ENCOUNTERS'):
		extractor_names.append('event_encounters')
	elif os.environ.get('MAP_DATA'):
		i = extractor_names.index('common_events')
		extractor_names.insert(i, 'map_data')
	
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