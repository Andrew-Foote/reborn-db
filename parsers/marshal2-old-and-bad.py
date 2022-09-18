# handy little ruby script for testing:
#
# data = <INSERTDATAHERE>
# marshalled = Marshal.dump(data)
# ords = marshalled.chars.map { |c| c.ord }
# hexs = ords.map { |o| o.to_s(16) }
# print marshalled, "\n"
# print ords, "\n"
# print hexs

from abc import ABC, abstractmethod
from dataclasses import dataclass
from frozendict import frozendict
import struct
from typing import Any, Callable, Iterable, Iterator, Type

###################################################################################################
# Debugging setup
###################################################################################################

DEBUG = True
DEBUGLOG = None

if DEBUG:
    DEBUGLOG = open('marshal-log.txt', 'w')

###################################################################################################
# Dataclasses for the raw parse tree
###################################################################################################

class Parse(ABC):
    # The methods here are useful for avoiding boilerplate when defining tree transformations

    @abstractmethod
    def children(self) -> Iterable[Any]:
        """Return an iterable which contains each of the immediate children of the parse node.
        It should be possible to reconstruct the parse node from this iterable, if you know what
        type of parse node it should be."""

    @classmethod
    @abstractmethod
    def from_children(cls, children: Iterable[Any]) -> 'Parse':
        """Reconstruct a parse node from its iterable of immediate children."""

    # def map(self, callback: Callable[[Any], Any]) -> 'Parse':
    #     transformed = callback(self)
    #     children = (child.map(callback) for child in transformed.children())
    #     return transformed.__class__.from_children(children)

    def shortrep(self):
        return f'{type(self).__name__}: [{",".join((type(child).__name__ if isinstance(child, Parse) else str(child)) for child in self.children())}]'

def parse_tree_map(callback: Callable[[Any], Any], tree: Any) -> Any:
    # NB the callback should preserve Parse-ness if called on a Parse
    print(f'parse_tree_map: {type(tree)}', file=DEBUGLOG)
    if isinstance(tree, Parse):
        print(f'before callback: {tree.shortrep()}', file=DEBUGLOG)
        tree = callback(tree)
        print(f'after callback: {tree.shortrep()}', file=DEBUGLOG)

        return tree.__class__.from_children(
            parse_tree_map(callback, child)
            for child in tree.children()
        )

    return tree

@dataclass(frozen=True)
class ToplevelParse(Parse):
    major_version: int
    minor_version: int
    body: 'NonToplevelParse'
    symbols: tuple['SymbolParse', ...]
    objects: tuple[None, 'ObjectParse', ...]

    def children(self):
        yield self.major_version
        yield self.minor_version
        yield self.body
        yield self.symbols
        yield self.objects

    @classmethod
    def from_children(cls, children):
        major_version, minor_version, body, symbols, objects = children
        return ToplevelParse(major_version, minor_version, body, symbols, objects)

class NonToplevelParse(Parse, ABC):
    pass

@dataclass(frozen=True)
class FalseParse(NonToplevelParse):
    def children(self):
        yield from ()

    @classmethod
    def from_children(cls, children):
        () = children
        return FALSE_PARSE

FALSE_PARSE = FalseParse()

@dataclass(frozen=True)
class TrueParse(NonToplevelParse):
    def children(self):
        yield from ()

    @classmethod
    def from_children(cls, children):
        () = children
        return TRUE_PARSE

TRUE_PARSE = TrueParse()

@dataclass(frozen=True)
class NilParse(NonToplevelParse):
    def children(self):
        yield from ()

    @classmethod
    def from_children(cls, children):
        () = children
        return NIL_PARSE

NIL_PARSE = NilParse()

@dataclass(frozen=True)
class FixnumParse(NonToplevelParse):
    value: int

    def children(self):
        yield self.value

    @classmethod
    def from_children(cls, children):
        value, = children
        return FixnumParse(value)

@dataclass(frozen=True)
class SymbolParse(NonToplevelParse):
    index: int
    name: bytes

    def children(self):
        yield self.index
        yield self.name

    @classmethod
    def from_children(cls, children):
        index, name = children
        return SymbolParse(index, name)

@dataclass(frozen=True)
class SymbolRefParse(NonToplevelParse):
    index: int

    def children(self):
        yield self.index

    @classmethod
    def from_children(cls, children):
        index, = children
        return SymbolRefParse(index)

SymbolMaybeRefParse = SymbolParse | SymbolRefParse

@dataclass(frozen=True)
class ObjectRefParse(NonToplevelParse):
    index: int

    def children(self):
        yield self.index

    @classmethod
    def from_children(cls, children):
        index, = children
        return ObjectRefParse(index)

@dataclass(frozen=True)
class ObjectParse(NonToplevelParse, ABC):
    index: int

@dataclass(frozen=True)
class InstVarsParse(ObjectParse):
    object_: NonToplevelParse
    vars_: frozendict[SymbolMaybeRefParse, NonToplevelParse]

    def children(self):
        yield self.index
        yield self.object_

        for key, value in self.vars_.items():
            yield key
            yield value

    @classmethod
    def from_children(cls, children):
        children = list(children)
        print([type(child) for child in children], file=DEBUGLOG)
        index, object_, *kvpairs = children
        if any(isinstance(child, SymbolRefParse) for child in children): breakpoint()
        assert len(kvpairs) % 2 == 0
        return InstVarsParse(index, object_, frozendict(zip(kvpairs[::2], kvpairs[1::2])))

@dataclass(frozen=True)
class ModuleExtParse(ObjectParse):
    object_: NonToplevelParse
    module: SymbolMaybeRefParse

    def children(self):
        yield self.index
        yield self.object_
        yield self.module

    @classmethod
    def from_children(cls, children):
        index, object_, module = children
        return ModuleExtParse(index, object_, module)

@dataclass(frozen=True)
class ArrayParse(ObjectParse):
    items: tuple[NonToplevelParse, ...]

    def children(self):
        yield self.index
        yield from self.items

    @classmethod
    def from_children(cls, children):
        index, *items = children
        return ArrayParse(index, tuple(children))

@dataclass(frozen=True)
class BignumParse(ObjectParse):
    value: int

    def children(self):
        yield self.index
        yield self.value

    @classmethod
    def from_children(cls, children):
        index, value = children
        return BignumParse(index, value)

@dataclass(frozen=True)
class ClassRefParse(ObjectParse):
    name: bytes

    def children(self):
        yield self.index
        yield self.name

    @classmethod
    def from_children(cls, children):
        index, name = children
        return ClassRefParse(index, name)

@dataclass(frozen=True)
class ModuleRefParse(ObjectParse):
    name: bytes

    def children(self):
        yield self.index
        yield self.name

    @classmethod
    def from_children(cls, children):
        index, name = children
        return ModuleRefParse(index, name)

@dataclass(frozen=True)
class ClassOrModuleRefParse(ObjectParse):
    name: bytes

    def children(self):
        yield self.index
        yield self.name

    @classmethod
    def from_children(cls, children):
        index, name = children
        return ClassOrModuleRefParse(index, name)

@dataclass(frozen=True)
class DataParse(ObjectParse):
    class_: SymbolMaybeRefParse
    state_object: NonToplevelParse

    def children(self):
        yield self.index
        yield self.class_
        yield self.state_object

    @classmethod
    def from_children(cls, children):
        index, class_, state_object = children
        return DataParse(index, class_, state_object)

@dataclass(frozen=True)
class FloatParse(ObjectParse):
    value: float

    def children(self):
        yield self.index
        yield self.value

    @classmethod
    def from_children(cls, children):
        index, value = children
        return FloatParse(index, value)

@dataclass(frozen=True)
class HashParse(ObjectParse):
    mapping: frozendict[NonToplevelParse, NonToplevelParse]

    def children(self):
        yield self.index

        for key, value in self.mapping.items():
            yield key
            yield value

    @classmethod
    def from_children(cls, children):
        index, *kvpairs = children
        assert len(kvpairs) % 2 == 0
        return HashParse(index, frozendict(zip(kvpairs[::2], kvpairs[1::2])))

@dataclass(frozen=True)
class DefaultHashParse(ObjectParse):
    mapping: frozendict[NonToplevelParse, NonToplevelParse]
    default: NonToplevelParse

    def children(self):
        yield self.index

        for key, value in self.mapping.items():
            yield key
            yield value

        yield self.default

    @classmethod
    def from_children(cls, children):
        index, *kvpairs, default = children
        assert len(kvpairs) % 2 == 0
        return DefaultHashParse(index, frozendict(zip(kvpairs[::2], kvpairs[1::2])), default)

@dataclass(frozen=True)
class InstParse(ObjectParse):
    class_: SymbolMaybeRefParse
    vars_: frozendict[SymbolMaybeRefParse, NonToplevelParse]

    def children(self):
        yield self.index
        yield self.class_

        for key, value in self.vars_.items():
            yield key
            yield value

    @classmethod
    def from_children(cls, children):
        index, class_, *kvpairs = children
        assert len(kvpairs) % 2 == 0
        return InstParse(index, class_, frozendict(zip(kvpairs[::2], kvpairs[1::2])))

@dataclass(frozen=True)
class RegexParse(ObjectParse):
    content: bytes
    options: int

    def children(self):
        yield self.index
        yield self.content
        yield self.options

    @classmethod
    def from_children(cls, children):
        index, content, options = children
        return RegexParse(index, content, options)

@dataclass(frozen=True)
class DecodedRegexParse(ObjectParse):
    content: str
    options: int

    def children(self):
        yield self.index
        yield self.content
        yield self.options

    @classmethod
    def from_children(cls, children):
        index, content, options = children
        return DecodedRegexParse(index, content, options)

@dataclass(frozen=True)
class StringParse(ObjectParse):
    content: bytes

    def children(self):
        yield self.index
        yield self.content

    @classmethod
    def from_children(cls, children):
        index, content = children
        return StringParse(index, content)

@dataclass(frozen=True)
class DecodedStringParse(ObjectParse):
    content: str

    def children(self):
        yield self.index
        yield self.content

    @classmethod
    def from_children(cls, children):
        index, content = children
        return DecodedStringParse(index, content)

@dataclass(frozen=True)
class StructParse(ObjectParse):
    name: SymbolMaybeRefParse
    vars_: frozendict[SymbolMaybeRefParse, NonToplevelParse]

    def children(self):
        yield self.index
        yield self.name

        for key, value in self.vars_.items():
            yield key
            yield value

    @classmethod
    def from_children(cls, children):
        index, name, *kvpairs = children
        assert len(kvpairs) % 2 == 0
        return StructParse(index, name, frozendict(zip(kvpairs[::2], kvpairs[1::2])))

@dataclass(frozen=True)
class SubclassedBuiltinParse(ObjectParse):
    class_: SymbolMaybeRefParse
    object_: StringParse | RegexParse | ArrayParse | HashParse | DefaultHashParse

    def children(self):
        yield self.index
        yield self.class_
        yield self.object_

    @classmethod
    def from_children(cls, children):
        index, class_, object_ = children
        return SubclassedBuiltinParse(index, class_, object_)

@dataclass(frozen=True)
class UserBytesParse(ObjectParse):
    class_: SymbolMaybeRefParse
    bytes_: bytes    

    def children(self):
        yield self.index
        yield self.class_
        yield self.bytes_

    @classmethod
    def from_children(cls, children):
        index, class_, bytes_ = children
        return UserBytesParse(index, class_, bytes_)

@dataclass(frozen=True)
class UserObjectParse(ObjectParse):
    class_: SymbolMaybeRefParse
    object_: NonToplevelParse

    def children(self):
        yield self.index
        yield self.class_
        yield self.object_

    @classmethod
    def from_children(cls, children):
        index, class_, object_ = children
        return UserObjectParse(index, class_, object_)

###################################################################################################
# The parser itself
###################################################################################################

class ParseError(Exception):
    def __init__(self, offset, message):
        super().__init__(f'offset {hex(offset)}: {message}')

@dataclass(frozen=True)
class ParserState:
    src: bytes
    index: int = 0
    symbols: tuple[SymbolParse, ...] = ()
    objects: tuple[None, ObjectParse, ...] = (None,) # since the indices start at 1

    def rem_len(self) -> int:
        return len(self.src) - self.index

    def __getitem__(self, i: int | slice) -> int:
        if isinstance(i, slice):
            start = max(0, self.index if i.start is None else i.start + self.index)
            stop = min(len(self.src), len(self.src) if i.stop is None else i.stop + self.index)
            step = i.step
            return self.src[start:stop:step]

        print(f'byte at index {self.index + i}: {self.src[self.index + i]}')
        return self.src[self.index + i]

    def error(self, message: str) -> None:
        raise ParseError(self.index, message)

    # def append_symbol(self, symbol: SymbolParse) -> 'ParserState':
    #     symbols = (*self.symbols, symbol)
    #     return ParserState(self.src, self.index, symbols, self.objects)

    def append_symbol(self, name: bytes) -> tuple['ParserState', SymbolParse]:
        index = len(self.symbols)
        symbol = SymbolParse(index, name)
        symbols = (*self.symbols, symbol)
        return ParserState(self.src, self.index, symbols, self.objects), symbol

    # def append_object(self, object_: ObjectParse) -> 'ParserState':
    #     objects = (*self.objects, object_)
    #     return ParserState(self.src, self.index, self.symbols, objects)

    def append_object(self, cls: Type, *args: Any) -> tuple['ParserState', ObjectParse]:
        index = len(self.objects)
        object_ = cls(index, *args)
        objects = (*self.objects, object_)
        return ParserState(self.src, self.index, self.symbols, objects), object_

    def debug(self, message: str) -> None:
        if DEBUG:
            segment = ' '.join(hex(byte)[2:].zfill(2) for byte in self[-5:5])
            if self.index > 5: segment = '...' + segment
            if self.index < len(self.src) - 5: segment += '...' 
            print(f'{hex(self.index)} [{segment}]: {message}', file=DEBUGLOG)

def skip(state: ParserState, dist: int) -> ParserState:
    return ParserState(state.src, state.index + dist, state.symbols, state.objects)

def parse_bytes(state: ParserState, count: int) -> tuple[ParserState, bytes]:
    bytes_ = state[:count]
    state = skip(state, count)
    state.debug(f'parsed bytes: {bytes_} (length {count})')
    return state, bytes_

def parse_byte(state: ParserState) -> tuple[ParserState, int]:
    state, byte = parse_bytes(state, 1)
    state.debug(f'parsed byte: {byte} ({byte[0]})')
    return state, byte[0]

def parse_false(state: ParserState) -> tuple[ParserState, FalseParse]: return state, FALSE_PARSE
def parse_true(state: ParserState) -> tuple[ParserState, TrueParse]: return state, TRUE_PARSE
def parse_nil(state: ParserState) -> tuple[ParserState, NilParse]: return state, NIL_PARSE

FIXNUM_HEADERS: dict[tuple[int, int]] = {
    0: (0, 0),
    1: (1, 1),
    2: (2, 1),
    3: (3, 1),
    4: (4, 1),
    0xfc: (4, -1),
    0xfd: (3, -1),
    0xfe: (2, -1),
    0xff: (1, -1),
}

def uint_le_from_iterable(s: Iterable[int]) -> int:
    """Parse an iterable of bytes as an unsigned little-endian integer."""
    return sum(digit * 0x100 ** i for i, digit in enumerate(s))

def parse_fixnum(state: ParserState) -> tuple[ParserState, FixnumParse]:
    state.debug('parsing fixnum')
    state, header = parse_byte(state)

    try:
        length, sign = FIXNUM_HEADERS[header]
    except KeyError:
        length = 1
        sign = -1 if header >= 128 else 1
        state.debug(f'fixnum length {length}, sign {sign}')
        value = header - sign * 5
    else:
        state.debug(f'fixnum length {length}, sign {sign}')
        if state.rem_len() < length:
            state.error(
                f'remaining data length in bytes is {state.rem_len()}, but having encountered a'
                f' fixnum with header {header}, this should be at least {length}'
            )

        state, bytes_ = parse_bytes(state, length)
        value = uint_le_from_iterable(bytes_)

    if sign == -1:
        value = -(2 ** length - value)

    state.debug(f'parsed fixnum: {value}')
    return state, FixnumParse(value)

def parse_byte_seq(state: ParserState) -> tuple[ParserState, bytes]:
    state.debug('parsing byte sequence')
    state, length = parse_fixnum(state)

    if state.rem_len() < length.value:
        state.error(
            f'remaining data length in bytes is {state.rem_len()}, but a byte sequence of '
            f'length {length.value} is expected'
        )

    return parse_bytes(state, length.value)

def parse_symbol(state: ParserState) -> tuple[ParserState, SymbolParse]:
    state.debug('parsing symbol')
    state, name = parse_byte_seq(state)
    return state.append_symbol(name)

def parse_symbol_ref(state: ParserState) -> tuple[ParserState, SymbolRefParse]:
    state.debug('parsing symbol ref')
    state, index = parse_fixnum(state)
    return state, SymbolRefParse(index.value)

def parse_object_ref(state: ParserState) -> tuple[ParserState, ObjectRefParse]:
    state.debug('parsing object ref')
    state, index = parse_fixnum(state)
    return state, ObjectRefParse(index.value)

def parse_symbol_with_header(state: ParserState) -> tuple[ParserState, SymbolMaybeRefParse]:
    if state.rem_len() < 1:
        state.error('expected a symbol, but there are no bytes left in the input')

    state, header = parse_byte(state)

    if header == ord(':'):
        return parse_symbol(state)
    elif header == ord(';'):
        return parse_symbol_ref(state)
    else:
        state.error('expected a symbol or symbol reference')

def parse_vars(state: ParserState) -> tuple[ParserState, frozendict[SymbolMaybeRefParse, NonToplevelParse]]:
    state, length = parse_fixnum(state)
    res = {}

    for _ in range(length.value):
        state, name = parse_symbol_with_header(state)
        state, value = parse_object(state)
        res[name] = value

    return state, frozendict(res)

def parse_inst_vars(state: ParserState) -> tuple[ParserState, InstVarsParse]:
    state.debug('parsing inst vars')
    state, object_ = parse_object(state)
    state, vars_ = parse_vars(state)
    return state.append_object(InstVarsParse, object_, vars_)

def parse_module_ext(state: ParserState) -> tuple[ParserState, ModuleExtParse]:
    state.debug('parsing module extension')
    state, object_ = parse_object(state)
    state, module = parse_symbol_with_header(state)
    return state.append_object(ModuleExtParse, object_, module)

def parse_array(state: ParserState) -> tuple[ParserState, ArrayParse]:
    state.debug('parsing array')
    state, length = parse_fixnum(state)
    items = []

    for _ in range(length.value):
        state, item = parse_object(state)
        items.append(item)

    return state.append_object(ArrayParse, tuple(items))

BIGNUM_SIGNS: dict[int, int] = {ord('+'): 1, ord('-'): -1}

def parse_bignum(state: ParserState) -> tuple[ParserState, BignumParse]:
    state, header = parse_byte(state)

    if state.rem_len() < 1:
        state.error('expected a sign byte for a bignum, but there are no bytes left in the input')

    try:
        sign = BIGNUM_SIGNS[header]
    except KeyError:
        state.error(f'expected a sign byte for a bignum, got {hex(header)} instead')

    state, length_fixnum = parse_fixnum(state)
    length = length_fixnum.value * 2

    if state.rem_len() < length:
        state.error(
            f'remaining data length in bytes is {state.rem_len()}, but a bignum of length '
            f'{length} is expected'
        )

    state, bytes_ = parse_bytes(state, length)
    value = sign * uint_le_from_iterable(bytes_)
    return state.append_object(BignumParse, value)

def parse_class_ref(state: ParserState) -> tuple[ParserState, ClassRefParse]:
    state, name = parse_byte_seq(state)
    return state.append_object(ClassRefParse, name)

def parse_module_ref(state: ParserState) -> tuple[ParserState, ModuleRefParse]:
    state, name = parse_byte_seq(state)
    return state.append_object(ModuleRefParse, name)

def parse_class_or_module_ref(state: ParserState) -> tuple[ParserState, ClassOrModuleRefParse]:
    state, name = parse_byte_seq(state)
    return state.append_object(ClassOrModuleRefParse, name)

# "Data objects are wrapped pointers from ruby extensions"
# I hate to use such a vague name but if that's what's in the docs, OK then
def parse_data(state: ParserState) -> tuple[ParserState, DataParse]:
    state, class_ = parse_symbol_with_header(state)
    state, state_object = parse_object(state)
    return state.append_object(DataParser, class_, state_object)

SPECIAL_FLOATS: tuple[str, ...] = ('inf', '-inf', 'nan')

def parse_float(state: ParserState) -> tuple[ParserState, FloatParse]:
    state, bytes_ = parse_byte_seq(state)

    for special in MarshalParser.SPECIAL_FLOATS:
        if bytes_ == special.encode('ascii'):
            value = float(special)
            break
    else:
        value, = struct.unpack('d', bytes_)

    return state.append_object(FloatParse, value)

def parse_hash_underlying(state: ParserState) -> tuple[ParserState, frozendict[NonToplevelParse, NonToplevelParse]]:
    state, length_fixnum = parse_fixnum(state)
    length = length_fixnum.value * 2
    pairs = []

    for i in range(length):
        state, object_ = parse_object(state)

        if i % 2:
            pairs[-1] = (*pairs[-1], object_)
        else:
            pairs.append((object_,))

    return state, frozendict(pairs)

def parse_hash(state: ParserState) -> tuple[ParserState, HashParse]:
    state, mapping = parse_hash_underlying(state)
    return state.append_object(HashParse, mapping)

def parse_default_hash(state: ParserState) -> tuple[ParserState, DefaultHashParse]:
    state, mapping = parse_hash_underlying(state)
    state, default = parse_object(state)
    return state.append_object(DefaultHashParse, mapping, default)

def parse_inst(state: ParserState) -> tuple[ParserState, InstParse]:
    state, class_ = parse_symbol_with_header(state)
    state, vars_ = parse_vars(state)
    return state.append_object(InstParse, class_, vars_)

def parse_regex(state: ParserState) -> tuple[ParserState, RegexParse]:
    state, bytes_ = parse_byte_seq(state)

    if state.rem_len() < 1:
        state.error('expected an options byte for a regex, but there are no bytes left in the input')

    state, options = parse_byte(state)
    return state.append_object(RegexParse, bytes_, options)

def parse_string(state: ParserState) -> tuple[ParserState, StringParse]:
    state, bytes_ = parse_byte_seq(state)
    return state.append_object(StringParse, bytes_)

def parse_struct(state: ParserState) -> tuple[ParserState, StructParse]:
    state, name = parse_symbol_with_header(state)
    state, vars_ = parse_vars(state)
    return state.append_object(StructParse, name, vars_)

# "a subclass of a String, Regexp, Array or Hash"
def parse_subclassed_builtin(state: ParserState) -> tuple[ParserState, SubclassedBuiltinParse]:
    state, class_ = parse_symbol_with_header(state)
    state, object_ = parse_object(state)
    return state.append_object(SubclassedBuiltinParse, class_, object_)

def parse_user_bytes(state: ParserState) -> tuple[ParserState, UserBytesParse]:
    state, class_ = parse_symbol_with_header(state)
    state, bytes_ = parse_byte_seq(state)
    return state.append_object(UserBytesParse, class_, bytes_)

def parse_user_object(state: ParserState) -> tuple[ParserState, UserObjectParse]:
    state, class_ = parse_symbol_with_header(state)
    state, object_ = parse_object(state)
    return state.append_object(UserObjectParse, class_, object_)

OBJECT_HEADERS = {
    ord('T'): parse_true,
    ord('F'): parse_false,
    ord('0'): parse_nil,
    ord('i'): parse_fixnum,
    ord(':'): parse_symbol,
    ord(';'): parse_symbol_ref,
    ord('@'): parse_object_ref,
    ord('I'): parse_inst_vars,
    ord('e'): parse_module_ext,
    ord('['): parse_array,
    ord('l'): parse_bignum, 
    ord('c'): parse_class_ref,
    ord('m'): parse_module_ref,
    ord('M'): parse_class_or_module_ref,
    ord('d'): parse_data,
    ord('f'): parse_float,
    ord('{'): parse_hash,
    ord('}'): parse_default_hash,
    ord('o'): parse_inst,
    ord('/'): parse_regex,
    ord('"'): parse_string,
    ord('S'): parse_struct,
    ord('C'): parse_subclassed_builtin,
    ord('u'): parse_user_bytes,
    ord('U'): parse_user_object
}

def parse_object(state: ParserState) -> tuple[ParserState, NonToplevelParse]:
    state.debug('parsing object')

    if state.rem_len() < 1:
        state.error('expected an object header byte, but there are no bytes left in the input')

    state, header = parse_byte(state)

    try:
        parser = OBJECT_HEADERS[header]
    except KeyError:
        state.error(f'unrecognized type header: {hex(header)} (as char: {chr(header)})')

    return parser(state)

def parse(src: bytes) -> ToplevelParse:
    state = ParserState(src)
    state.debug('parsing toplevel')

    # Major and minor version of the Marshal format
    # (this parser is designed to work with v4.8)
    state, (major_version, minor_version) = parse_bytes(state, 2)
    state, body = parse_object(state)

    if state.rem_len() > 0:     
        state.error(f'parsing finished, but this is not the end of the input')

    return ToplevelParse(major_version, minor_version, body, state.symbols, state.objects)

###################################################################################################
# Operations on the parse tree
###################################################################################################

ParseLeaf = 

def normalize(tree: ToplevelParse) -> ToplevelParse:
    """Replaces every symbol or object node within the tree with its reference."""
    symbols = tree.symbols
    objects = tree.objects

    def visit(vertex: Any) -> Any:


def expand_atomic_refs(tree: ToplevelParse) -> ToplevelParse:
    symbols = tree.symbols
    objects = tree.objects

    def expand_vertex(vertex):
        print(type(vertex), [(type(child) if isinstance(child, Parse) else child) for child in vertex.children()], file=DEBUGLOG)

        # seems it's not expanding every symbol ref somehow?
        if isinstance(vertex, SymbolRefParse):
            print(f'is symbol ref for {symbols[vertex.index]}', file=DEBUGLOG)
            return symbols[vertex.index]

        if isinstance(vertex, ObjectRefParse):
            object_ = objects[vertex.index]

            if isinstance(object_, (
                BignumParse, ClassRefParse, ModuleRefParse, ClassOrModuleRefParse, FloatParse,
                RegexParse, StringParse, UserBytesParse
            )):
                return object_

        return vertex

    return parse_tree_map(expand_vertex, tree)

RUBY_ENCODINGS = {
    TRUE_PARSE: 'utf-8',
    FALSE_PARSE: 'us-ascii'
}

def decode(tree: ToplevelParse) -> ToplevelParse:
    for symbol in tree.symbols:
        if symbol.name == b'E':
            encoding_symbol = symbol
            break
    else:
        return tree

    def decode_vertex(vertex):
        if not isinstance(vertex, InstVarsParse):
            return vertex

        index = vertex.index
        vars_ = dict(vertex.vars_)
        encoding = vars_.pop(encoding_symbol)
        
        if encoding is None:
            return vertex
        
        encoding = RUBY_ENCODINGS[encoding]
        object_ = vertex.object_

        if isinstance(object_, RegexParse):
            object_ = DecodedRegexParse(object_.index, object_.content.decode(encoding), object_.options)
        elif isinstance(object_, StringParse):
            object_ = DecodedStringParse(object_.index, object_.content.decode(encoding))

        if vars_:
            object_ = InstVarsParse(index, object_, frozendict(vars_))

        return object_

    return parse_tree_map(decode_vertex, tree)

def decode2(tree: ToplevelParse) -> ToplevelParse:
    for symbol in tree.symbols:
        if symbol.name == b'E':
            encoding_symbol = symbol
            break
    else:
        return tree

    def transform(vertex: Any) -> Any:
        res = vertex

        if not isinstance(res, Parse):
            return res

        if isinstance(res, InstVarsParse):
            index = res.index
            vars_ = dict(res.vars_)

            try:
                encoding = vars_.pop(encoding_symbol)
            except KeyError:
                pass
            else:
                encoding = RUBY_ENCODINGS[encoding]
                res = res.object_

                if isinstance(res, RegexParse):
                    res = DecodedRegexParse(res.index, res.content.decode(encoding), res.options)
                elif isinstance(res, StringParse):
                    res = DecodedStringParse(res.index, res.content.decode(encoding))

                if vars_:
                    res = InstVarsParse(index, res, frozendict(vars_))

            return res

        children = map(transform, res.children())
        res = res.__class__.from_children(children)

    return transform(tree)

# jsonifying
# unrolling references as long as they don't have themselves as a parent (so we can safely jsonify)


###################################################################################################
# Testing/debugging
###################################################################################################

if __name__ == '__main__':
    import sys
    from dcformat import stringify

    fname = sys.argv[1]

    with open(fname, 'rb') as f:
        data = parse(f.read())
        data = decode2(data)

    with open('marshal-output.txt', 'w', encoding='utf-8') as f:
        print(stringify(data), file=f)