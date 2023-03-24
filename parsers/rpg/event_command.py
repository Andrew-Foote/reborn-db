from abc import ABC, abstractmethod
from dataclasses import dataclass, make_dataclass
from functools import partial
import inspect
from typing import Any, Type, TypeVar

from parsers import marshal
from parsers.rpg.basic import *
from parsers.rpg.move_route import *

T = TypeVar('T')

@dataclass
class EventCommand(ABC):
    indent: int
            
    @classmethod
    def get(
        cls: Type[T], graph: marshal.MarshalGraph, ref: marshal.MarshalRef,
        *arg_refs: marshal.MarshalRef, **kwargs: Any
    ) -> Type[T]:
    
        def cls(**inst_vars: Any) -> Type['EventCommand']:
            code = inst_vars.pop('code')
            
            try:
                command_type = COMMAND_TYPES[code]
            except KeyError:
                raise ValueError(
                    f'RPG::EventCommand object at ref {ref} has type code {code}, but this does '
                    'not correspond to any recognized command type'
                )
                
            command_type_name = command_type[0]
            subclass = globals()[f'EventCommand_{command_type_name}']
            arg_refs = inst_vars.pop('parameters')
            return subclass.get(graph, ref, *arg_refs, **inst_vars)
            
        return marshal.get_inst(graph, ref, 'RPG::EventCommand', cls, {
            'code': marshal.get_fixnum, 'indent': marshal.get_fixnum,
            'parameters': marshal.get_array
        })
     
COMMAND_TYPES = {
    0: ('Blank',),
    101: ('ShowText', ('text', marshal.get_string)),
    102: (
        'ShowChoices',
        ('choices', partial(marshal.get_array, callback=marshal.get_string)),
        ('cancel_type', CancelType.get)
    ),
    103: ('InputNumber', ('var_id', marshal.get_fixnum), ('max_digits', marshal.get_fixnum)),
    104: ('ChangeTextOptions', ('pos', TextPosition.get), ('no_frame', get_bool_from_fixnum)),
    105: ('ButtonInputProcessing', ('var_id', marshal.get_fixnum)),
    106: ('Wait', ('duration', marshal.get_fixnum)), # units = frames / 2,
    108: ('Comment', ('text', marshal.get_string)),
    #111: ('ConditionalBranch',), # done manually
    112: ('Loop',),
    113: ('BreakLoop',),
    115: ('ExitEventProcessing',),
    116: ('EraseEvent',),
    117: ('CallCommonEvent', ('common_event_id', marshal.get_fixnum)),
    118: ('Label', ('id', marshal.get_string)),
    119: ('JumpToLabel', ('id', marshal.get_string)),
    121: (
        'ControlSwitches',
        # this is an inclusive range of switch IDs to set at once
        ('switch_id_lo', marshal.get_fixnum), ('switch_id_hi', marshal.get_fixnum),
        ('state', SwitchState.get)
    ),
    #122: ('ControlVariables',), # done manually
    123: ('ControlSelfSwitch', ('self_switch_ch', marshal.get_string), ('state', SwitchState.get)),
    125: (
        'ChangeGold',
        ('diff_type', DiffType.get), ('with_variable', get_bool_from_fixnum),
        ('amount', marshal.get_fixnum)
    ),
    132: ('ChangeBattleBGM', ('audio', AudioFile.get)),
    201: (
        'TransferPlayer',
        ('with_variables', get_bool_from_fixnum),
        ('map_id', marshal.get_fixnum),
        ('x', marshal.get_fixnum), ('y', marshal.get_fixnum),
        ('direction', Direction.get),
        ('no_fade', get_bool_from_fixnum)
    ),
    202: (
        'SetEventLocation',
        ('event_id', marshal.get_fixnum), # 0 for this event
        ('appoint_type', AppointType.get),
        ('x', marshal.get_fixnum), ('y', marshal.get_fixnum),
        ('direction', Direction.get)
    ),
    203: (
        'ScrollMap',
        ('direction', Direction.get),
        ('distance', marshal.get_fixnum), ('speed', marshal.get_fixnum)
    ),
    #204: ('ChangeMapSettings',), # done manually
    206: ('ChangeFogOpacity', ('opacity', marshal.get_fixnum), ('duration', marshal.get_fixnum)),
    207: (
        'ShowAnimation',
        ('event_id', marshal.get_fixnum), # -1 for this player, 0 for this event
        ('animation_id', marshal.get_fixnum)
    ),
    208: ('ChangeTransparentFlag', ('is_normal', get_bool_from_fixnum)),
    209: (
        'SetMoveRoute',
        ('target_event_id', marshal.get_fixnum,), # this can be -1 for the player
                                                  # (whatever that means)
        ('move_route', MoveRoute.get)
    ),
    210: ('WaitForMoveCompletion',),
    221: ('PrepareForTransition',),
    222: ('ExecuteTransition', ('name', marshal.get_string)),
    223: (
        'ChangeScreenColorTone',
        ('tone', partial(marshal.get_user_data, class_name='Tone')),
        ('duration', marshal.get_fixnum) # units = frames / 2
    ),
    224: (
        'ScreenFlash',
        ('color', partial(marshal.get_user_data, class_name='Color')),
        ('duration', marshal.get_fixnum) # units = frames / 2
    ),
    225: (
        'ScreenShake',
        ('power', marshal.get_fixnum), ('speed', marshal.get_fixnum),
        ('duration', marshal.get_fixnum)
    ),
    231: (
        'ShowPicture',
        ('number', marshal.get_fixnum), ('name', marshal.get_string),
        ('origin', marshal.get_fixnum),
        ('appoint_with_vars', get_bool_from_fixnum),
        ('x', marshal.get_fixnum), ('y', marshal.get_fixnum),
        ('zoom_x', marshal.get_fixnum), ('zoom_y', marshal.get_fixnum),
        ('opacity', marshal.get_fixnum), ('blend_type', marshal.get_fixnum)
    ),
    232: (
        'MovePicture',
        ('number', marshal.get_fixnum), ('duration', marshal.get_fixnum),
        ('origin', marshal.get_fixnum),
        ('appoint_with_vars', get_bool_from_fixnum),
        ('x', marshal.get_fixnum), ('y', marshal.get_fixnum),
        ('zoom_x', marshal.get_fixnum), ('zoom_y', marshal.get_fixnum),
        ('opacity', marshal.get_fixnum), ('blend_type', marshal.get_fixnum)
    ),
    235: ('ErasePicture', ('number', marshal.get_fixnum)),
    236: (
        'SetWeatherEffects',
        ('type', Weather.get), ('power', marshal.get_fixnum),
        ('duration', marshal.get_fixnum)
    ),
    241: ('PlayBGM', ('audio', AudioFile.get)),
    242: ('FadeOutBGM', ('seconds', marshal.get_fixnum)),
    245: ('PlayBGS', ('audio', AudioFile.get)),
    246: ('FadeOutBGS', ('seconds', marshal.get_fixnum)),
    247: ('MemorizeBGMOrBGS',),
    249: ('PlayME', ('audio', AudioFile.get)),
    250: ('PlaySE', ('audio', AudioFile.get)),
    251: ('StopSE',),
    314: ('RecoverAll', ('actor_id', marshal.get_fixnum)), # 0 for all party
    340: ('AbortBattle',),
    351: ('CallMenuScreen',),
    352: ('CallSaveScreen',),
    353: ('GameOver',),
    354: ('ReturnToTitleScreen',),
    355: ('Script', ('line', marshal.get_string)),
    401: ('ContinueShowText', ('text', marshal.get_string)),
    402: ('ShowChoicesWhenChoice', ('choice_index', marshal.get_fixnum), ('choice_text', marshal.get_string)),
    403: ('ShowChoicesWhenCancel',),
    404: ('ShowChoicesBranchEnd',),
    408: ('ContinueComment', ('text', marshal.get_string)),
    411: ('Else',),
    412: ('ConditionalBranchEnd',),
    413: ('RepeatAbove',),
    509: ('ContinueSetMoveRoute', ('cmd', MoveCommand.get)),
    655: ('ContinueScript', ('line', marshal.get_string)),
}

def make_getter(params_with_lookups):
    @classmethod
    def get(cls, graph, ref, *arg_refs, **inst_vars):
        #print(cls.short_type_name, params_with_lookups)
        param_count = len(params_with_lookups)
        arg_count = len(arg_refs)
        
        if param_count != arg_count:
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type {cls.short_type_name} (code '
                f'{cls.code}) has {arg_count} arguments, but is supposed to have {param_count}. '
                f'Argument reference list: {arg_refs}.'
            )
        
        inst_vars |= {
            param: lookup(graph, arg_ref)
            for (param, lookup), arg_ref in zip(params_with_lookups, arg_refs)
        }
        
        return cls(**inst_vars)

    return get

for code, (name, *params_with_lookups) in COMMAND_TYPES.items():
    full_name = f'EventCommand_{name}'

    params_with_types = [
        (param, inspect.signature(lookup).return_annotation)
        for param, lookup in params_with_lookups
    ]
        
    globals()[full_name] = make_dataclass(
        full_name, params_with_types, bases=(EventCommand,),
        namespace={'code': code, 'short_type_name': name, 'get': make_getter(params_with_lookups)}
    )

@dataclass
class EventCommand_ConditionalBranch(EventCommand, ABC):
    code = 111
    short_type_name = 'ConditionalBranch'
    
    @classmethod
    def get(cls, graph, ref, *arg_refs, **inst_vars):
        try:
            subcode_ref, *arg_refs = arg_refs
        except ValueError:
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type {cls.short_type_name} (code '
                f'{cls.code}) has no arguments, but is supposed to have at least one'
            )
            
        subcode = marshal.get_fixnum(graph, subcode_ref)        
        
        try:
            branch_type = CONDITIONAL_BRANCH_TYPES[subcode]
        except KeyError:
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type ConditionalBranch (code 111) '
                f'has {subcode} as its branch type code, but this does not correspond to any '
                'recognized branch type'
            )
        
        branch_type_name = branch_type[0]
        subclass = globals()[f'EventCommand_ConditionalBranch_{branch_type_name}']
        return subclass.get(graph, ref, *arg_refs, **inst_vars)
        
COMMAND_TYPES[111] = ('ConditionalBranch',)

CONDITIONAL_BRANCH_TYPES = {
    0: ('Switch', ('switch_id', marshal.get_fixnum), ('state', SwitchState.get)),
    1: (
        'Variable',
        ('variable_id', marshal.get_fixnum),
        ('value_is_variable', get_bool_from_fixnum),
        ('value', marshal.get_fixnum),
        ('cmp', Comparison.get)
    ),
    2: ('SelfSwitch', ('self_switch_ch', marshal.get_string), ('state', SwitchState.get)),
    # char ref is -1 for player, 0 for this event, an event id otherwise. no, i don't really know what that means
    6: ('Character', ('char_ref', marshal.get_fixnum), ('direction', Direction.get)),
    7: ('Gold', ('amount', marshal.get_fixnum), ('bound_type', BoundType.get)),
    # button is an enum but we don't know the mapping (it's in the closed-source RGSS lib)
    11: ('Button', ('button', marshal.get_fixnum)),
    12: ('Script', ('expr', marshal.get_string)),
}

def make_conditionalbranch_getter(params_with_lookups):
    @classmethod
    def get(cls, graph, ref, *arg_refs, **inst_vars):
        param_count = len(params_with_lookups)
        arg_count = len(arg_refs)
        
        if param_count != arg_count:
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type ConditionalBranch (code 111) '
                f'and branch type {cls.short_subtype_name} (code {cls.subcode}) has {arg_count} '
                f'arguments (excluding the branch type code), but is supposed to have '
                f'{param_count}. Argument reference list: {arg_refs}.'
            )
        
        inst_vars |= {
            param: lookup(graph, arg_ref)
            for (param, lookup), arg_ref in zip(params_with_lookups, arg_refs)
        }      

        return cls(**inst_vars)

    return get    

for subcode, (name, *params_with_lookups) in CONDITIONAL_BRANCH_TYPES.items():
    full_name = f'EventCommand_ConditionalBranch_{name}'
    
    params_with_types = [
        (param, inspect.signature(lookup).return_annotation)
        for param, lookup in params_with_lookups
    ]
    
    globals()[full_name] = make_dataclass(
        full_name, params_with_types, bases=(EventCommand_ConditionalBranch,),
        namespace={
            'subcode': subcode, 'short_subtype_name': name,
            'get': make_conditionalbranch_getter(params_with_lookups)
        }
    )

@dataclass
class EventCommand_ControlVariables(EventCommand, ABC):
    code = 122
    short_type_name = 'ControlVariables'
    
    var_id_hi: int
    var_id_lo: int
    assign_type: AssignType

    @classmethod
    def get(cls, graph, ref, *arg_refs, **inst_vars):
        arg_count = len(arg_refs)

        if arg_count not in (5, 6):
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type {cls.short_type_name} (code '
                f'{cls.code}) has {arg_count} arguments, but is supposed to have 5 or 6'
            )

        inst_vars |= {
            'var_id_hi': marshal.get_fixnum(graph, arg_refs[0]),
            'var_id_lo': marshal.get_fixnum(graph, arg_refs[1]),
            'assign_type': AssignType.get(graph, arg_refs[2]),
        }

        operand_type_code = marshal.get_fixnum(graph, arg_refs[3])
        arg_refs = arg_refs[4:]
        
        try:
            operand_type = OPERAND_TYPES[operand_type_code]
        except KeyError:
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type ControlVariables (code {cls.code})'
                f'has {operand_type_code} as its operand type code, but this does not correspond to'
                'any recognized operand type'
            )
        
        operand_type_name = operand_type[0]
        subclass = globals()[f'EventCommand_ControlVariables_{operand_type_name}']
        return subclass.get(graph, ref, *arg_refs, **inst_vars)

COMMAND_TYPES[122] = ('ControlVariables',)

OPERAND_TYPES = {
    0: ('InvariantOperand', ('value', marshal.get_fixnum)),
    1: ('VariableOperand', ('var_id', marshal.get_fixnum)),
    2: ('RandomNumberOperand', ('lb', marshal.get_fixnum), ('ub', marshal.get_fixnum)),
    6: ('CharacterOperand', ('attr_value', marshal.get_fixnum), ('attr_code', marshal.get_fixnum)),
    7: ('OtherOperand', ('infracode', marshal.get_fixnum))
}

def make_controlvariables_getter(params_with_lookups):
    @classmethod
    def get(cls, graph, ref, *arg_refs, **inst_vars):
        param_count = len(params_with_lookups)
        arg_count = len(arg_refs)
        
        if param_count != arg_count:
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type ControlVariables (code 122) and '
                f'operand type {cls.operand_type_name} (code {cls.operand_type_code}) has '
                f'{arg_count} arguments after the operand type code, but is supposed to have '
                f'{param_count}. Argument reference list: {arg_refs}.'
            )
        
        inst_vars |= {
            param: lookup(graph, arg_ref)
            for (param, lookup), arg_ref in zip(params_with_lookups, arg_refs)
        }

        return cls(**inst_vars)      

    return get    

for subcode, (name, *params_with_lookups) in OPERAND_TYPES.items():
    full_name = f'EventCommand_ControlVariables_{name}'
    
    params_with_types = [
        (param, inspect.signature(lookup).return_annotation)
        for param, lookup in params_with_lookups
    ]
    
    globals()[full_name] = make_dataclass(
        full_name, params_with_types, bases=(EventCommand_ControlVariables,),
        namespace={
            'operand_type_code': subcode, 'operand_type_name': name,
            'get': make_controlvariables_getter(params_with_lookups)
        }
    )

@dataclass
class EventCommand_ChangeMapSettings(EventCommand, ABC):
    code = 204
    short_type_name = 'ChangeMapSettings'

    @classmethod
    def get(cls, graph, ref, *arg_refs, **inst_vars):
        try:
            subcode_ref, *arg_refs = arg_refs
        except ValueError:
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type {cls.short_type_name} (code '
                f'{cls.code}) has no arguments, but is supposed to have at least one'
            )
            
        subcode = marshal.get_fixnum(graph, subcode_ref)        
        
        try:
            setting_type = MAP_SETTING_TYPES[subcode]
        except KeyError:
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type ChangeMapSettings (code {cls.code})'
                f'has {setting_type} as its map setting type code, but this does not correspond to'
                'any recognized map setting type'
            )
        
        setting_type_name = setting_type[0]
        subclass = globals()[f'EventCommand_ChangeMapSettings_{setting_type_name}']
        return subclass.get(graph, ref, *arg_refs, **inst_vars)

COMMAND_TYPES[204] = ('ChangeMapSettings',)

MAP_SETTING_TYPES = {
    0: ('Panorama', ('name', marshal.get_string), ('hue', marshal.get_fixnum)),
    1: (
        'Fog',
        ('name', marshal.get_string), ('hue', marshal.get_fixnum),
        ('opacity', marshal.get_fixnum), ('blend_type', marshal.get_fixnum),
        ('zoom', marshal.get_fixnum), ('sx', marshal.get_fixnum), ('sy', marshal.get_fixnum)
    ),
    2: ('BattleBack', ('name', marshal.get_string))
}

def make_changemapsettings_getter(params_with_lookups):
    @classmethod
    def get(cls, graph, ref, *arg_refs, **inst_vars):
        param_count = len(params_with_lookups)
        arg_count = len(arg_refs)
        
        if param_count != arg_count:
            raise ValueError(
                f'RPG::EventCommand object at ref {ref} of type ChangeMapSettings (code 204) and '
                f'map setting type type {cls.setting_type_name} (code {cls.setting_type_code}) has '
                f'{arg_count} arguments (excluding the map setting type code), but is supposed to have '
                f'{param_count}. Argument reference list: {arg_refs}.'
            )
        
        inst_vars |= {
            param: lookup(graph, arg_ref)
            for (param, lookup), arg_ref in zip(params_with_lookups, arg_refs)
        }      

        return cls(**inst_vars)

    return get    

for subcode, (name, *params_with_lookups) in MAP_SETTING_TYPES.items():
    full_name = f'EventCommand_ChangeMapSettings_{name}'
    
    params_with_types = [
        (param, inspect.signature(lookup).return_annotation)
        for param, lookup in params_with_lookups
    ]
    
    globals()[full_name] = make_dataclass(
        full_name, params_with_types, bases=(EventCommand_ChangeMapSettings,),
        namespace={
            'setting_type_code': subcode, 'setting_type_name': name,
            'get': make_changemapsettings_getter(params_with_lookups)
        }
    )
