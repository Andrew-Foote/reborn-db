import parsers.rpg.event_command as cmd
from parsers import marshal
from parsers.rpg.basic import get_bool_from_fixnum

def type_from_getter(getter, cmdtype, param):
    match (cmdtype, param):
        case ('ShowChoices', 'choices'):
            return 'array[string]'

    return {
        marshal.get_string: 'string',
        marshal.get_fixnum: 'integer',
        CancelType.get: 'cancel_type',
        TextPosition.get: 'text_position',
        get_bool_from_fixnum: 'bool',
        SwitchState.get: 'switch_state',
        DiffType.get: 'diff_type',
        AudioFile.get: 'audio_file',
        Direction.get: 'direction',
        MoveRoute.get: 'move_route',
        
    }[getter]

event_command_type_rows = []
event_command_parameter_rows = []

for cmdtype_code, cmdtype in cmd.COMMAND_TYPES.items():
    cmdtype_name, *params = cmdtype
    event_command_type_rows.append((cmdtype_name, cmdtype_code))

    for param, getter in params:
        event_command_parameter.append((cmdtype_name, param, type_from_getter(getter)))