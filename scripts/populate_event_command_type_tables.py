import parsers.rpg.event_command as cmd
from parsers import marshal
from parsers.rpg.basic import (
    get_bool_from_fixnum, CancelType, TextPosition, SwitchState, DiffType, AudioFile, AppointType,
    Direction, Weather, Comparison, BoundType
)
from parsers.rpg.move_route import MoveRoute, MoveCommand
from reborndb import DB

def type_from_getter(getter, cmdtype, param):
    match (cmdtype, param):
        case ('ShowChoices', 'choices'):
            return 'choices_array'
        case ('ChangeScreenColorTone', 'tone'):
            return 'tone'
        case ('ScreenFlash', 'color'):
            return 'color'

    return {
        marshal.get_string: 'text',
        marshal.get_fixnum: 'integer',
        CancelType.get: 'cancel_type',
        TextPosition.get: 'text_position',
        get_bool_from_fixnum: 'bool',
        SwitchState.get: 'switch_state',
        DiffType.get: 'diff_type',
        AudioFile.get: 'audio_file',
        AppointType.get: 'appoint_type',
        Direction.get: 'direction',
        MoveRoute.get: 'move_route',
        Weather.get: 'weather',
        MoveCommand.get: 'move_command',
        Comparison.get: 'comparison',
        BoundType.get: 'bound_type'
    }[getter]

def run():
    event_command_type_rows = []
    event_command_subtype_rows = []
    event_command_parameter_rows = []

    for cmdtype_code, cmdtype in cmd.COMMAND_TYPES.items():
        cmdtype_name, *params = cmdtype

        if cmdtype_name in ('ConditionalBranch', 'ControlVariables', 'ChangeMapSettings'):
            continue

        event_command_type_rows.append((cmdtype_name, cmdtype_code))
        event_command_subtype_rows.append((cmdtype_name, '', 0))

        for param, getter in params:
            event_command_parameter_rows.append((
                cmdtype_name, '', param,
                type_from_getter(getter, cmdtype_name, param)
            ))

    event_command_type_rows.append(('ConditionalBranch', 111))

    for cmdtype_code, cmdtype in cmd.CONDITIONAL_BRANCH_TYPES.items():
        cmdtype_name, *params = cmdtype
        event_command_subtype_rows.append(('ConditionalBranch', cmdtype_name, cmdtype_code))

        for param, getter in params:
            event_command_parameter_rows.append((
                'ConditionalBranch', cmdtype_name, param,
                type_from_getter(getter, 'ConditionalBranch', param)
            ))

    event_command_type_rows.append(('ControlVariables', 122))

    for cmdtype_code, cmdtype in cmd.OPERAND_TYPES.items():
        cmdtype_name, *params = cmdtype
        event_command_subtype_rows.append(('ControlVariables', cmdtype_name, cmdtype_code))

        for param, getter in params:
            event_command_parameter_rows.append((
                'ControlVariables', cmdtype_name, param,
                type_from_getter(getter, 'ControlVariables', param)
            ))

    event_command_type_rows.append(('ChangeMapSettings', 204))

    for cmdtype_code, cmdtype in cmd.MAP_SETTING_TYPES.items():
        cmdtype_name, *params = cmdtype
        event_command_subtype_rows.append(('ChangeMapSettings', cmdtype_name, cmdtype_code))

        for param, getter in params:
            event_command_parameter_rows.append((
                'ChangeMapSettings', cmdtype_name, param,
                type_from_getter(getter, 'ChangeMapSettings', param)
            ))

    with DB.H.transaction():
        DB.H.bulk_insert('event_command_type', ('name', 'code'), event_command_type_rows)

        DB.H.bulk_insert(
            'event_command_subtype',
            ('command_type', 'name', 'code'),
            event_command_subtype_rows
        )

        DB.H.bulk_insert(
            'event_command_parameter',
            ('command_type', 'command_subtype', 'name', 'type'),
            event_command_parameter_rows
        )