from dataclasses import dataclass
from enum import Enum
from typing import Type, TypeVar

from parsers import marshal

T = TypeVar('T')

def get_bool_from_fixnum(graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> bool:
    return bool(marshal.get_fixnum(graph,  ref))

class FixnumBasedEnum(Enum):
    @classmethod
    def get(cls: Type[T], graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> Type[T]:
        return cls(marshal.get_fixnum(graph, ref))

class SwitchState(FixnumBasedEnum):
    ON = 0
    OFF = 1

class ConditionType(FixnumBasedEnum):
    SWITCH = 0 # [switch id, 0=on/1=off]
    VARIABLE = 1 # [variable1id, 0forconstant?, variable2id, operator]
    SELF_SWITCH = 2
    TIMER = 3
    ACTOR = 4
    ENEMY = 5
    CHARACTER = 6
    GOLD = 7
    ITEM = 8
    WEAPON = 9
    ARMOR = 10
    BUTTON = 11
    SCRIPT = 12
    
class Direction(FixnumBasedEnum):
    NONE = 0
    DOWN = 2
    LEFT = 4
    RIGHT = 6
    UP = 8
    
class MoveType(FixnumBasedEnum):
    FIXED = 0
    RANDOM = 1
    APPROACH = 2
    CUSTOM = 3
    
class MoveSpeed(FixnumBasedEnum):
    SLOWEST = 1
    SLOWER = 2
    SLOW = 3
    FAST = 4
    FASTER = 5
    FASTEST = 6
    
class MoveFrequency(FixnumBasedEnum):
    LOWEST = 1
    LOWER = 2
    LOW = 3
    HIGH = 4
    HIGHER = 5
    HIGHEST = 6
    
class Trigger(FixnumBasedEnum):
    ACTION_BUTTON = 0
    PLAYER_TOUCH = 1
    EVENT_TOUCH = 2
    AUTORUN = 3
    PARALLEL_PROCESS = 4
    
@dataclass
class AudioFile:
    name: str
    volume: int
    pitch: int
    
    @classmethod
    def get(cls: Type[T], graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> Type[T]:
        return marshal.get_inst(graph, ref, 'RPG::AudioFile', cls, {
            'name': marshal.get_string, 'volume': marshal.get_fixnum, 'pitch': marshal.get_fixnum
        })
