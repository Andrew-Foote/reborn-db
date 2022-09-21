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
            
    @staticmethod
    def get(graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> Type['EventCommand']:
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
            inst_vars |= subclass.get_params(graph, ref, *arg_refs)
            return subclass(**inst_vars)
            
        return marshal.get_inst(graph, ref, 'RPG::EventCommand', cls, {
            'code': marshal.get_fixnum, 'indent': marshal.get_fixnum,
            'parameters': marshal.get_array
        })
        
    @abstractmethod
    def get_params(
        cls: Type[T], graph: marshal.MarshalGraph, *params: marshal.MarshalRef
    ) -> dict[str, Any]:
        ...

COMMAND_TYPES = {
    0: ('Blank',),
    101: ('ShowText', ('text', marshal.get_string)),
    106: ('Wait', ('duration', marshal.get_fixnum)), # units = frames / 2,
    117: ('CallCommonEvent', ('common_event_id', marshal.get_fixnum)),
    #111: ('ConditionalBranch',), # done manually
    201: (
        'TransferPlayer',
        ('with_variables', get_bool_from_fixnum),
        ('map_id', marshal.get_fixnum),
        ('x', marshal.get_fixnum), ('y', marshal.get_fixnum),
        ('direction', Direction.get),
        ('no_fade', get_bool_from_fixnum)
    ),
    209: (
        'SetMoveRoute',
        ('target_event_id', marshal.get_fixnum,), # this can be -1 for the player
                                                  # (whatever that means)
        ('move_route', MoveRoute.get)
    ),
    223: (
        'ChangeScreenColorTone',
        ('tone', partial(marshal.get_user_data, class_name='Tone')),
        ('duration', marshal.get_fixnum) # units = frames / 2
    ),
    250: ('PlaySE', ('audio', AudioFile.get)),
    340: ('AbortBattle',),
    351: ('CallMenuScreen',),
    352: ('CallSaveScreen',),
    353: ('GameOver',),
    354: ('ReturnToTitleScreen',),
    355: ('Script', ('line', marshal.get_string)),
    401: ('ContinueShowText', ('text', marshal.get_string)),
    509: ('ContinueSetMoveRoute', ('cmd', MoveCommand.get)),
    655: ('ContinueScript', ('line', marshal.get_string)),
}

for code, (name, *params_with_lookups) in COMMAND_TYPES.items():
    full_name = f'EventCommand_{name}'

    params_with_types = [
        (param, inspect.signature(lookup).return_annotation)
        for param, lookup in params_with_lookups
    ]
    
    @classmethod
    def get_params(
        cls: Type[T], graph: marshal.MarshalGraph, obj_ref: marshal.MarshalRef,
        *arg_refs: marshal.MarshalRef,
        params_with_lookups=params_with_lookups
    ) -> dict[str, Any]:
    
        param_count = len(params_with_lookups)
        arg_count = len(arg_refs)
        
        if param_count != arg_count:
            raise ValueError(
                f'RPG::EventCommand object at ref {obj_ref} of type {cls.short_type_name} (code '
                f'{cls.code}) has {arg_count} arguments, but is supposed to have {param_count}. '
                f'Argument reference list: {arg_refs}.'
            )
        
        return {
            param: lookup(graph, arg_ref)
            for (param, lookup), arg_ref in zip(params_with_lookups, arg_refs)
        }      
    
    globals()[full_name] = make_dataclass(
        full_name, params_with_types, bases=(EventCommand,),
        namespace={'code': code, 'short_type_name': name, 'get_params': get_params}
    )

@dataclass
class EventCommand_ConditionalBranch(EventCommand, ABC):
    code = 111
    short_type_name = 'ConditionalBranch'
    
    @classmethod
    def get_params(
        cls: Type[T], graph: marshal.MarshalGraph, obj_ref: marshal.MarshalRef,
        *arg_refs: marshal.MarshalRef
    ) -> dict[str, Any]:
        
        if not arg_refs:
            raise ValueError(
                f'RPG::EventCommand object at ref {obj_ref} of type {cls.short_type_name} (code '
                f'{cls.code}) has no arguments, but is supposed to have at least one'
            )
        
        subcode = marshal.get_fixnum(graph, arg_refs[0])
        
        try:
            branch_type = CONDITIONAL_BRANCH_TYPES[subcode]
        except KeyError:
            raise ValueError(
                f'RPG::EventCommand object at ref {obj_ref} of type ConditionalBranch (code 111) '
                f'has {subcode} as its branch type code, but this does not correspond to any '
                'recognized branch type'
            )
        
        branch_type_name = branch_type[0]
        subclass = globals()[f'EventCommand_ConditionalBranch_{branch_type_name}']
        arg_refs = arg_refs[1:]
        return subclass.get_condition_params(graph, obj_ref, *arg_refs)
        
    @abstractmethod
    def get_condition_params(
        cls: Type[T], graph: marshal.MarshalGraph, obj_ref: marshal.MarshalRef,
        *arg_refs: marshal.MarshalRef
    ) -> dict[str, Any]:
        ...
        
COMMAND_TYPES[111] = ('ConditionalBranch',)

CONDITIONAL_BRANCH_TYPES = {
    0: ('Switch', ('switch_id', marshal.get_fixnum), ('value', SwitchState.get)),
    # char ref is -1 for player, 0 for this event, an event id otherwise. no, i don't really know what that means
    6: ('Character', ('char_ref', marshal.get_fixnum), ('direction', Direction.get)),
    12: ('Script', ('expr', marshal.get_string)),
}

for subcode, (name, *params_with_lookups) in CONDITIONAL_BRANCH_TYPES.items():
    full_name = f'EventCommand_ConditionalBranch_{name}'
    
    params_with_types = [
        (param, inspect.signature(lookup).return_annotation)
        for param, lookup in params_with_lookups
    ]
    
    @classmethod
    def get_condition_params(
        cls: Type[T], graph: marshal.MarshalGraph, obj_ref: marshal.MarshalRef,
        *arg_refs: marshal.MarshalRef,
        params_with_lookups=params_with_lookups
    ) -> dict[str, Any]:
    
        param_count = len(params_with_lookups)
        arg_count = len(arg_refs)
        
        if param_count != arg_count:
            raise ValueError(
                f'RPG::EventCommand object at ref {obj_ref} of type ConditionalBranch (code 111) '
                f'and branch type {cls.short_subtype_name} (code {cls.subcode}) has {arg_count} '
                f'arguments (excluding the branch type code), but is supposed to have '
                f'{param_count}. Argument reference list: {arg_refs}.'
            )
        
        return {
            param: lookup(graph, arg_ref)
            for (param, lookup), arg_ref in zip(params_with_lookups, arg_refs)
        }      
    
    globals()[full_name] = make_dataclass(
        full_name, params_with_types, bases=(EventCommand_ConditionalBranch,),
        namespace={
            'subcode': subcode, 'short_subtype_name': name,
            'get_condition_params': get_condition_params
        }
    )
