from collections import defaultdict
import json
import re
from parsers import marshal
from reborndb import DB
from reborndb.settings import REBORN_DATA_PATH

#class _DB: pass
#DB = _DB()
#DB.H = altconnect('events.db')

def parse_marshal_fixnum(val):
    assert isinstance(val, marshal.MarshalFixnum), type(val)
    return val.val

def parse_marshal_bool(val):
    assert isinstance(val, (marshal.MarshalTrue, marshal.MarshalFalse)), type(val)
    return marshal.pythonify(val)

def parse_marshal_string(val):
    assert isinstance(val, marshal.MarshalDecodedString), type(val)
    return val.content

def parse_marshal_array(val):
    assert isinstance(val, marshal.MarshalArray), type(val)
    return val.items

expected_keys_map = {
    'RPG::Map':  {
        '@tileset_id', '@width', '@height', '@autoplay_bgm', '@bgm', '@autoplay_bgs', '@bgs',
        '@encounter_list', '@encounter_step', '@data', '@events'
    },
    'RPG::AudioFile': {'@name', '@volume', '@pitch'},
    'RPG::Event': {'@id', '@name', '@x', '@y', '@pages'},
    'RPG::Event::Page': {
        '@condition', '@graphic', '@move_type', '@move_speed', '@move_frequency', '@move_route',
        '@walk_anime', '@step_anime', '@direction_fix', '@through', '@always_on_top', '@trigger',
        '@list'
    },
    'RPG::Event::Page::Condition': {
        '@switch1_valid', '@switch2_valid', '@variable_valid', '@self_switch_valid',
        '@switch1_id', '@switch2_id', '@variable_id', '@variable_value', '@self_switch_ch'
    },
    'RPG::Event::Page::Graphic': {
        '@tile_id', '@character_name', '@character_hue', '@direction', '@pattern', '@opacity',
        '@blend_type'
    },
    'RPG::MoveRoute': {'@repeat', '@skippable', '@list'},
    'RPG::MoveCommand': {'@code', '@parameters'},
    'RPG::EventCommand': {'@code', '@indent', '@parameters'}
}

columns = {
    'marshal_map': (
        'id', 'tileset', 'width', 'height',
        'autoplay_bgm', 'bgm_name', 'bgm_volume', 'bgm_pitch',
        'autoplay_bgs', 'bgs_name', 'bgs_volume', 'bgs_pitch',
        'data'
    ),
    'marshal_map_event': ('map', 'id', 'name', 'x', 'y'),
    'marshal_map_event_page': (
        'map', 'event', 'number',
        'tile', 'character', 'character_hue', 'character_direction', 'character_pattern',
        'character_opacity', 'character_blend_type',
        'move_type', 'move_speed', 'move_frequency',
        'walk_anime', 'step_anime', 'direction_fix', 'through', 'always_on_top',
        'trigger'
    ),
    'marshal_map_event_switch_condition': ('map', 'event', 'page', 'switch'),
    'marshal_map_event_variable_condition': ('map', 'event', 'page', 'variable', 'value'),
    'marshal_map_event_self_switch_condition': ('map', 'event', 'page', 'switch'),
    'marshal_map_event_route': ('map', 'event', 'page', 'repeat', 'skippable'),
    'marshal_map_event_route_command': ('map', 'event', 'page', 'number', 'code'),
    'marshal_map_event_route_command_parameter': ('map', 'event', 'page', 'command', 'number', 'value', 'simpvalue'),
    'marshal_map_event_command': ('map', 'event', 'page', 'number', 'code', 'indent'),
    'marshal_map_event_command_parameter': ('map', 'event', 'page', 'command', 'number', 'value', 'simpvalue')
}

for table, cols in columns.items():
    DB.H.exec(f'drop table if exists {table}')
    #DB.H.dump_as_table(table, cols, [])

def parse_marshal_class_inst(val, expected_class):
    if isinstance(val, marshal.MarshalCyclicRef):
        # who knows?
        pass

    assert isinstance(val, marshal.MarshalClassInst), type(val)
    assert val.cls.name == expected_class, val.cls.name
    inst_vars = {key.name: val for key, val in val.vars.items()}
    attrs = set(inst_vars.keys())
    expected_keys = expected_keys_map[expected_class]
    assert attrs == expected_keys, attrs
    return inst_vars

def parse_arbitrary_marshal_object(val):
    stringified = marshal.stringify(param)
    pythonified = marshal.pythonify(param)

    if isinstance(pythonified, (bool, int, float, str)):
        simpvalue = pythonified
    else:
        simpvalue = None

    return (stringified, simpvalue)

map_data_path_pattern = r'Map(\d{3}).rxdata'

#for data_file in REBORN_DATA_PATH.iterdir():
#   rows = defaultdict(lambda: []) # per file because it takes too much memory if we put data for all maps in one array
#
#   is_map_data = re.match(map_data_path_pattern, data_file.name)
#   if not is_map_data: continue
#   map_id = int(is_map_data.group(1))
#   print(str(data_file))
#   map_row = [map_id]
#
#   data = marshal.load(data_file)
#   data = parse_marshal_class_inst(data, 'RPG::Map')
#
#   map_row.append(parse_marshal_fixnum(data['@tileset_id']))
#   map_row.append(parse_marshal_fixnum(data['@width']))
#   map_row.append(parse_marshal_fixnum(data['@height']))
#
#   for key in ('bgm', 'bgs'):
#       map_row.append(parse_marshal_bool(data[f'@autoplay_{key}']))
#       bgdata = parse_marshal_class_inst(data[f'@{key}'], 'RPG::AudioFile')        
#
#       map_row.append(parse_marshal_string(bgdata['@name']))
#       map_row.append(parse_marshal_fixnum(bgdata['@volume']))
#       map_row.append(parse_marshal_fixnum(bgdata['@pitch']))
#
#   encounter_list = parse_marshal_array(data['@encounter_list'])
#   assert not encounter_list, encounter_list
#
#   encounter_step = parse_marshal_fixnum(data['@encounter_step'])
#   assert encounter_step == 30, encounter_step
#
#   assert isinstance(data['@data'], marshal.MarshalUserBytes), type(data['@data'])
#   assert data['@data'].cls.name == 'Table', data['@data'].cls
#   map_row.append(data['@data'].bytes)
#
#   assert isinstance(data['@events'], marshal.MarshalHash), type(data['@events'])
#   events = {key: val for key, val in data['@events'].mapping.items()}
#
#   for key, val in events.items():
#       event_id = parse_marshal_fixnum(key)
#       event_row = [map_id, event_id]
#       event = parse_marshal_class_inst(val, 'RPG::Event')
#
#       event_id_attr = parse_marshal_fixnum(event['@id'])
#       assert event_id_attr == event_id, (event_id, event_id_attr)
#
#       event_row.append(parse_marshal_string(event['@name']))
#       event_row.append(parse_marshal_fixnum(event['@x']))
#       event_row.append(parse_marshal_fixnum(event['@y']))
#
#       pages = parse_marshal_array(event['@pages'])
#       
#       for page_number, page in enumerate(event['@pages'].items):
#           page = parse_marshal_class_inst(page, 'RPG::Event::Page')
#           page_id = (map_id, event_id, page_number)
#           page_row = [*page_id]
#
#           condition = parse_marshal_class_inst(page['@condition'], 'RPG::Event::Page::Condition')
#           switch_conditions = []
#
#           for i in range(1, 2):
#               if parse_marshal_bool(condition[f'@switch{i}_valid']):
#                   switch_id = parse_marshal_fixnum(condition[f'@switch{i}_id'])
#                   switch_conditions.append(switch_id)
#
#           for switch_id in switch_conditions:
#               rows['marshal_map_event_switch_condition'].append((*page_id, switch_id))
#
#           if parse_marshal_bool(condition['@variable_valid']):
#               rows['marshal_map_event_variable_condition'].append((
#                   *page_id,
#                   parse_marshal_fixnum(condition['@variable_id']),
#                   parse_marshal_fixnum(condition['@variable_value'])
#               ))
#
#           if parse_marshal_bool(condition['@self_switch_valid']):
#               rows['marshal_map_event_self_switch_condition'].append((
#                   *page_id, parse_marshal_string(condition['@self_switch_ch'])
#               ))
#
#           graphic = parse_marshal_class_inst(page['@graphic'], 'RPG::Event::Page::Graphic')
#           page_row.append(parse_marshal_fixnum(graphic['@tile_id']))
#           page_row.append(parse_marshal_string(graphic['@character_name']))
#           page_row.append(parse_marshal_fixnum(graphic['@character_hue']))
#           page_row.append(parse_marshal_fixnum(graphic['@direction']))
#           page_row.append(parse_marshal_fixnum(graphic['@pattern']))
#           page_row.append(parse_marshal_fixnum(graphic['@opacity']))
#           page_row.append(parse_marshal_fixnum(graphic['@blend_type']))
#
#           move_type = parse_marshal_fixnum(page['@move_type'])
#           page_row.append(move_type)
#           page_row.append(parse_marshal_fixnum(page['@move_speed']))
#           page_row.append(parse_marshal_fixnum(page['@move_frequency']))
#
#           if move_type == 3:
#               route = parse_marshal_class_inst(page['@move_route'], 'RPG::MoveRoute')
#   
#               rows['marshal_map_event_route'].append((
#                   *page_id,
#                   parse_marshal_bool(route['@repeat']),
#                   parse_marshal_bool(route['@skippable'])
#               ))
#
#               commands  = parse_marshal_array(route['@list'])
#
#               for command_number, command in enumerate(commands):
#                   command = parse_marshal_class_inst(command, 'RPG::MoveCommand')
#
#                   rows['marshal_map_event_route_command'].append((
#                       *page_id, command_number, parse_marshal_fixnum(command['@code'])
#                   ))
#
#                   params = parse_marshal_array(command['@parameters'])
#
#                   for param_number, param in enumerate(params):
#                       rows['marshal_map_event_route_command_parameter'].append((
#                           *page_id, command_number, param_number, *parse_arbitrary_marshal_object(param)
#                       ))
#
#           page_row.append(parse_marshal_bool(page['@walk_anime']))
#           page_row.append(parse_marshal_bool(page['@step_anime']))
#           page_row.append(parse_marshal_bool(page['@direction_fix']))
#           page_row.append(parse_marshal_bool(page['@through']))
#           page_row.append(parse_marshal_bool(page['@always_on_top']))
#           page_row.append(parse_marshal_fixnum(page['@trigger']))
#
#           commands = parse_marshal_array(page['@list'])
#
#           for command_number, command in enumerate(commands):
#               command = parse_marshal_class_inst(command, 'RPG::EventCommand')
#
#               rows['marshal_map_event_command'].append((
#                   *page_id, command_number,
#                   parse_marshal_fixnum(command['@code']),
#                   parse_marshal_fixnum(command['@indent'])
#               ))
#
#               params = parse_marshal_array(command['@parameters'])
#
#               for param_number, param in enumerate(params):
#                   rows['marshal_map_event_command_parameter'].append((
#                       *page_id, command_number, param_number,
#                       *parse_arbitrary_marshal_object(param)
#                   ))
#
#           rows['marshal_map_event_page'].append(page_row)
#
#       rows['marshal_map_event'].append(event_row)
#
#   rows['marshal_map'].append(map_row)
#
#   with DB.H.transaction():
#       for table, content in rows.items():
#           DB.H.bulk_insert(table, columns[table], content)