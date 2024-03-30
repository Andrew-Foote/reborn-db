from abc import ABC, abstractmethod
from dataclasses import dataclass, make_dataclass
from functools import partial
import inspect
from typing import Any, Type, TypeVar

from parsers import marshal
from parsers.rpg.basic import *

T = TypeVar('T')

@dataclass
class MoveCommand(ABC):
    @staticmethod
    def get(graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> Type['MoveCommand']:
        def cls(**inst_vars: Any) -> Type['MoveCommand']:
            code = inst_vars.pop('code')
            
            try:
                command_type = COMMAND_TYPES[code]
            except KeyError:
                raise ValueError(
                    f'RPG::MoveCommand object at ref {ref} has type code {code}, but this does '
                    'not correspond to any recognized command type'
                )
                
            command_type_name = command_type[0]
            subclass = globals()[f'MoveCommand_{command_type_name}']
            arg_refs = inst_vars.pop('parameters')
            inst_vars |= subclass.get_params(graph, ref, *arg_refs)
            return subclass(**inst_vars)
            
        return marshal.get_inst(graph, ref, 'RPG::MoveCommand', cls, {
            'code': marshal.get_fixnum, 'parameters': marshal.get_array
        })
        
    @abstractmethod
    def get_params(
        cls: Type[T], graph: marshal.MarshalGraph, *params: marshal.MarshalRef
    ) -> dict[str, Any]:
        ...

COMMAND_TYPES = {
    0: ('Blank',),
    1: ('MoveDown',),
    2: ('MoveLeft',),
    3: ('MoveRight',),
    4: ('MoveUp',),
    5: ('MoveLowerLeft',),
    6: ('MoveLowerRight',),
    7: ('MoveUpperLeft',),
    8: ('MoveUpperRight',),
    9: ('MoveAtRandom',),
    10: ('MoveTowardPlayer',),
    11: ('MoveAwayFromPlayer',),
    12: ('StepForward',),
    13: ('StepBackward',),
    14: ('Jump', ('x', marshal.get_fixnum), ('y', marshal.get_fixnum)),
    15: ('Wait', ('count', marshal.get_fixnum)),
    16: ('TurnDown',),
    17: ('TurnLeft',),
    18: ('TurnRight',),
    19: ('TurnUp',),
    20: ('Turn90Right',),
    21: ('Turn90Left',),
    22: ('Turn180',),
    23: ('Turn90RightOrLeft',),
    24: ('TurnAtRandom',),
    25: ('TurnTowardPlayer',),
    26: ('TurnAwayFromPlayer',),
    27: ('SwitchOn', ('switch_id', marshal.get_fixnum)),
    28: ('SwitchOff', ('switch_id', marshal.get_fixnum)),
    29: ('ChangeSpeed', ('speed', marshal.get_fixnum)),
    30: ('ChangeFreq', ('freq', marshal.get_fixnum)),
    31: ('MoveAnimationOn',),
    32: ('MoveAnimationOff',),
    33: ('StopAnimationOn',),
    34: ('StopAnimationOff',),
    35: ('DirectionFixOn',),
    36: ('DirectionFixOff',),
    37: ('ThroughOn',),
    38: ('ThroughOff',),
    39: ('AlwaysOnTopOn',),
    40: ('AlwaysOnTopOff',),
    41: (
        'Graphic',
        ('character_name', marshal.get_string), ('character_hue', marshal.get_fixnum),
        ('direction', Direction.get), ('pattern', marshal.get_fixnum)
    ),
    42: ('ChangeOpacity', ('opacity', marshal.get_fixnum)),
    43: ('ChangeBlendType', ('blend_type', marshal.get_fixnum)),
    44: ('PlaySE', ('audio', AudioFile.get)),
    45: ('Script', ('line', marshal.get_string)),
}

for code, (name, *params_with_lookups) in COMMAND_TYPES.items():
    full_name = f'MoveCommand_{name}'

    params_with_types = [
        (param, inspect.signature(lookup).return_annotation)
        for param, lookup in params_with_lookups
    ]
    
    @classmethod
    def get_params(
        cls: Type[T], graph: marshal.MarshalGraph, obj_ref: marshal.MarshalRef,
        *arg_refs: marshal.MarshalRef,
        name=name, params_with_lookups=params_with_lookups
    ) -> dict[str, Any]:
    
        param_count = len(params_with_lookups)
        arg_count = len(arg_refs)
        
        if param_count != arg_count:
            raise ValueError(
                f'RPG::MoveCommand object at ref {obj_ref} of type {name} has {arg_count} '
                f'arguments, but is supposed to have {param_count}. Argument reference list: '
                f'{arg_refs}.'
            )
        
        return {
            param: lookup(graph, arg_ref)
            for (param, lookup), arg_ref in zip(params_with_lookups, arg_refs)
        }      
    
    globals()[full_name] = make_dataclass(
        full_name, params_with_types, bases=(MoveCommand,),
        namespace={'code': code, 'short_type_name': name, 'get_params': get_params}
    )

@dataclass
class MoveRoute:
    repeat: bool
    skippable: bool
    list_: list[MoveCommand]
    
    @classmethod
    def get(cls, graph, ref):
        def cls2(**inst_vars):
            inst_vars['list_'] = inst_vars.pop('list')
            return cls(**inst_vars)
        
        return marshal.get_inst(graph, ref, 'RPG::MoveRoute', cls2, {
            'repeat': marshal.get_bool, 'skippable': marshal.get_bool,
            'list': partial(marshal.get_array, callback=MoveCommand.get)
        })
    
def unpack_move_command(cmd):
    cmd_type, *params = COMMAND_TYPES[cmd.code]
    args = []

    for param, getter in params:
        args.append((
            param,
            getattr(cmd, param),
            type_from_getter(getter, cmd_type, param)
        ))

    return cmd_type, args
