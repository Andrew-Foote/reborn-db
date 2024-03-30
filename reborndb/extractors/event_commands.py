import itertools as it
from parsers.rpg import move_route, event_command
from reborndb import DB
from scripts.populate_event_command_type_tables import type_from_getter

def move_command_ids_gen():
    cur_max = DB.H.exec11('select max("id") from "move_command"') or -1
    yield from it.count(cur_max + 1)

move_command_ids = move_command_ids_gen()

def event_command_ids_gen():
    cur_max = DB.H.exec11('select max("id") from "event_command"') or -1
    yield from it.count(cur_max + 1)

event_command_ids = event_command_ids_gen()

def unpack_move_command(cmd):
    cmd_type, *params = move_route.COMMAND_TYPES[cmd.code]
    args = []

    for param, getter in params:
        args.append((
            param,
            getattr(cmd, param),
            type_from_getter(getter, cmd_type, param)
        ))

    return cmd_type, args

def unpack_event_command(cmd):
    if isinstance(cmd, event_command.EventCommand_ConditionalBranch):
        subcode = cmd.subcode
    elif isinstance(cmd, event_command.EventCommand_ControlVariables):
        subcode = cmd.operand_type_code
    elif isinstance(cmd, event_command.EventCommand_ChangeMapSettings):
        subcode = cmd.setting_type_code
    else:
        subcode = 0

    cmd_type, cmd_subtype, *params = event_command.COMMAND_TYPES_AND_SUBTYPES[cmd.code, subcode]
    args = []

    for param, getter in params:
        args.append((
            param,
            getattr(cmd, param),
            type_from_getter(getter, cmd_type, param)
        ))

    return cmd_type, cmd_subtype, cmd.indent, args

def create_move_command(cmd_type, args):
    cmd_id = next(move_command_ids)
    DB.H.exec('insert into "move_command" ("id", "type") values (?, ?)', (cmd_id, cmd_type,))
    print('create_move_command', cmd_id, cmd_type, args)

    for param, arg, arg_type in args:
        match arg_type:
            case 'integer':
                DB.H.exec(
                    'insert into "move_command_integer_argument" ("command", "command_type", "parameter", "type", "value") values (?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, param, arg_type, int(arg))
                )
            case 'text':
                DB.H.exec(
                    'insert into "move_command_text_argument" ("command", "command_type", "parameter", "type", "value") values (?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, param, arg_type, arg)
                )
            case 'audio_file':
                DB.H.exec(
                    'insert into "move_command_audio_file_argument" ("command", "command_type", "parameter", "type", "name", "volume", "pitch") values (?, ?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, param, arg_type, arg.name, arg.volume, arg.pitch)
                )
            case 'direction':
                DB.H.exec(
                    'insert into "move_command_direction_argument" ("command", "command_type", "parameter", "type", "direction") values (?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, param, arg_type, arg.name.lower())
                )

    return cmd_id

def create_event_command(cmd_type, cmd_subtype, args):
    cmd_id = next(event_command_ids)
    
    DB.H.exec(
        'insert into "event_command" ("id", "type", "subtype") values (?, ?, ?)',
        (cmd_id, cmd_type, cmd_subtype)
    )

    print('create_event_command', cmd_id, cmd_type, cmd_subtype, args)

    for param, arg, arg_type in args:
        match arg_type:
            case 'integer':
                DB.H.exec(
                    'insert into "event_command_integer_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, int(arg))
                )
            case 'text':
                DB.H.exec(
                    'insert into "event_command_text_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg)
                )
            case 'bool':
                DB.H.exec(
                    'insert into "event_command_bool_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, int(arg))
                )
            case 'audio_file':
                DB.H.exec(
                    'insert into "event_command_audio_file_argument" ("command", "command_type", "command_subtype", "parameter", "type", "name", "volume", "pitch") values (?, ?, ?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name, arg.volume, arg.pitch)
                )
            case 'direction':
                DB.H.exec(
                    'insert into "event_command_direction_argument" ("command", "command_type", "command_subtype", "parameter", "type", "direction") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'choices_array':
                choices = arg.copy()

                while len(choices) < 4:
                    choices.append('')

                DB.H.exec(
                    'insert into "event_command_choices_array_argument" ("command", "command_type", "command_subtype", "parameter", "type", "choice1", "choice2", "choice3", "choice4") values (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, *choices)
                )
            case 'tone':
                DB.H.exec(
                    'insert into "event_command_tone_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg)
                )
            case 'color':
                DB.H.exec(
                    'insert into "event_command_color_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg)
                )
            case 'cancel_type':
                DB.H.exec(
                    'insert into "event_command_cancel_type_argument" ("command", "command_type", "command_subtype", "parameter", "type", "cancel_type") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'text_position':
                DB.H.exec(
                    'insert into "event_command_text_position_argument" ("command", "command_type", "command_subtype", "parameter", "type", "text_position") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'switch_state':
                DB.H.exec(
                    'insert into "event_command_switch_state_argument" ("command", "command_type", "command_subtype", "parameter", "type", "switch_state") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'diff_type':
                DB.H.exec(
                    'insert into "event_command_diff_type_argument" ("command", "command_type", "command_subtype", "parameter", "type", "diff_type") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'appoint_type':
                DB.H.exec(
                    'insert into "event_command_appoint_type_argument" ("command", "command_type", "command_subtype", "parameter", "type", "appoint_type") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'comparison':
                DB.H.exec(
                    'insert into "event_command_comparison_argument" ("command", "command_type", "command_subtype", "parameter", "type", "comparison") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'bound_type':
                DB.H.exec(
                    'insert into "event_command_bound_type_argument" ("command", "command_type", "command_subtype", "parameter", "type", "bound_type") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'weather':
                DB.H.exec(
                    'insert into "event_command_weather_argument" ("command", "command_type", "command_subtype", "parameter", "type", "weather") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'move_command':                
                move_cmd_type, move_cmd_args = unpack_move_command(arg)
                move_cmd_id = create_move_command(move_cmd_type, move_cmd_args)

                DB.H.exec(
                    'insert into "event_command_move_command_argument" ("command", "command_type", "command_subtype", "parameter", "type", "move_command") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, move_cmd_id)
                )
            case 'move_route':
                DB.H.exec(
                    'insert into "event_command_move_route_argument" ("command", "command_type", "command_subtype", "parameter", "type", "repeat", "skippable") values (?, ?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.repeat, arg.skippable)
                )
                
                for move_cmd_i, move_cmd in enumerate(arg.list_):
                    move_cmd_type, move_cmd_args = unpack_move_command(move_cmd)
                    move_cmd_id = create_move_command(move_cmd_type, move_cmd_args)

                    DB.H.exec(
                        'insert into "event_command_move_route_argument_move_command" ("event_command", "parameter", "move_command_number", "move_command") values (?, ?, ?, ?)', (cmd_id, param, move_cmd_i, move_cmd_id)
                    )
            case _:
                raise ValueError(f'unrecognized arg type {arg_type}')    

    return cmd_id
