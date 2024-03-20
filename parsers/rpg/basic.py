from dataclasses import dataclass
from enum import Enum
from typing import Type, TypeVar
import numpy as np

from parsers import marshal

T = TypeVar('T')

def get_bool_from_fixnum(graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> bool:
    return bool(marshal.get_fixnum(graph,  ref))

class FixnumBasedEnum(Enum):
    @classmethod
    def get(cls: Type[T], graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> Type[T]:
        return cls(marshal.get_fixnum(graph, ref))

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
    
class EventPageTrigger(FixnumBasedEnum):
    ACTION_BUTTON = 0
    PLAYER_TOUCH = 1
    EVENT_TOUCH = 2
    AUTORUN = 3
    PARALLEL_PROCESS = 4

class CommonEventTrigger(FixnumBasedEnum):
    NONE = 0
    AUTORUN = 1
    PARALLEL = 2
    
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

class AssignType(FixnumBasedEnum):
    SUBSTITUTE = 0
    ADD = 1
    SUBTRACT = 2
    MULTIPLY = 3
    DIVIDE = 4
    REMAINDER = 5
    
class OperandType(FixnumBasedEnum):
    INVARIANT = 0
    FROM_VARIABLE = 1
    RANDOM_NUMBER = 2
    ITEM = 3
    ACTOR = 4
    ENEMY = 5
    CHARACTER = 6
    OTHER = 7
    
class OperandSubtype(FixnumBasedEnum):
    MAP_ID = 0
    PARTY_SIZE = 1
    GOLD = 2
    STEP_COUNT = 3
    PLAY_TIME = 4
    TIMER = 5
    SAVE_COUNT = 6

class CancelType(FixnumBasedEnum):
    DISALLOW = 0
    CHOICE1 = 1
    CHOICE2 = 2
    CHOICE3 = 3
    CHOICE4 = 4
    BRANCH = 5

class AppointType(FixnumBasedEnum):
    DIRECT = 0
    VARIABLE = 1
    EXCHANGE = 2

class Comparison(FixnumBasedEnum):
    EQ = 0
    GE = 1
    LE = 2
    GT = 3
    LT = 4
    NE = 5

class Weather(FixnumBasedEnum):
    NONE = 0 
    RAIN = 1
    STORM = 2
    SNOW = 3

class BoundType(FixnumBasedEnum):
    LOWER = 0
    UPPER = 1

class DiffType(FixnumBasedEnum):
    INCREASE = 0
    DECREASE = 1

class TextPosition(FixnumBasedEnum):
    TOP = 0
    MIDDLE = 1
    BOTTOM = 2

class SelfSwitchName(Enum):
    A = 'A'
    B = 'B'
    C = 'C'
    D = 'D'

    @classmethod
    def get(cls: Type[T], graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> Type[T]:
        return cls(marshal.get_string(graph, ref))

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

@dataclass
class Table:
    bytes_: bytes
    array: np.array

    @classmethod
    def get(
        cls: Type[T], graph: marshal.MarshalGraph, ref: marshal.MarshalRef, expected_dimcount=None
    ) -> Type[T]:
    
        bytes_ = marshal.get_user_data(graph, ref, 'Table')

        # The data begins with a 32-bit signed integer giving the number of dimensions in the
        # array.
        dimcount = int.from_bytes(bytes_[:4], 'little', signed=True)
        assert 1 <= dimcount <= 3

        if expected_dimcount is not None and dimcount != expected_dimcount:
            raise ValueError(
                f'Table object at ref {ref} has {dimcount} dimensions, expected '
                f'{expected_dimcount}'
            )
 
        # Next come three more 32-bit signed integers giving the size of each dimension, in number
        # of tiles. Order is width, height, depth. If the number of dimensions is less than 3 then
        # the remaining dimensions will be 1.

        dimensions = []

        for i in range(3):
            size = int.from_bytes(bytes_[4 * (i + 1):4 * (i + 2)], 'little', signed=True)
            if i >= dimcount: assert size == 1
            dimensions.append(size)

        width, height, depth = dimensions

        # Next comes a final 32-bit signed integer which is simply equal to the product of the
        # dimensions, giving us no new information.
        datalen = int.from_bytes(bytes_[16:20], 'little', signed=True)
        assert datalen == width * height * depth

        # The remaining data consists of 16-bit signed integers, which reference tiles from the
        # map's tileset. There is one of these for each tile, and the number of tiles is equal to
        # the product of the dimensions, so the total length of the remaning data is twice the
        # integer that we just read (datalen).
        tiledata = bytes_[20:]
        assert len(tiledata) == datalen * 2

        # Tiles are arranged so that adjacent tiles have the same depth, height and width, in that
        # order of preference. Since we access the tiles via (x, y, z) coordinates this is
        # "Fortran order"---as you iterate over the data, the fastest-changing indices are the
        # earliest ones.
        array = np.ndarray(shape=(width, height, depth), dtype='h', buffer=bytes_[20:], order='F')
        return cls(bytes_, array)

    @property
    def width(self): return self.array.shape[0]

    @property
    def height(self): return self.array.shape[1]

    @property
    def depth(self): return self.array.shape[2]

    def __getitem__(self, indices):
        x, y, z = indices
        return self.array[x, y, z]

    def format(self) -> str:
        rows = []

        # maximum size expected is 5 digits

        for y in range(self.height):
            row = []

            for z in range(self.depth):
                subrow = []

                for x in range(self.width):
                    subrow.append(f'{self[x, y, z]:05}')

                row.append(' '.join(subrow))

            rows.append('\n'.join(row))

        return '\n\n'.join(rows)
