from abc import ABC
import base64
from collections import OrderedDict
from dataclasses import dataclass, make_dataclass
from enum import Enum
from frozendict import frozendict
from functools import partial
import locale
import math
import re
import struct
from typing import Any, Callable, ClassVar, get_args, Iterable, Iterator, Optional, Sequence

# handy little ruby script for testing:
#
# data = <INSERTDATAHERE>
# marshalled = Marshal.dump(data)
# ords = marshalled.chars.map { |c| c.ord }
# hexs = ords.map { |o| o.to_s(16) }
# print marshalled, "\n"
# print ords, "\n"
# print hexs

DEBUG = True
DEBUGLOG = None

if DEBUG:
    DEBUGLOG = open('marshal-log.txt', 'w')

def debug(message: str) -> None:
    if DEBUG: print(message, file=DEBUGLOG)

###################################################################################################
# References
###################################################################################################

# In the Marshal format, symbols and most objects (other than true, false, nil and fixnums)
# appear in full only once in a file. Subsequent occurrences just reference the earlier
# occurrence via an index. There are separate sets of indices for symbols and objects, and the
# indices for symbols start at 0, but the indices for objects start at 1.
# (Actually, 0 is used as the index for the whole object. And since cycles are possible, there
# could be an object reference to 0.)
#
# To encode a Marshal object as a graph, we need a way to refer to vertices in the graph. It is
# convenient for debugging purposes to make these references match up with those used in the
# Marshal data (where possible; of course, for true, false, nil and fixnums the vertices are not
# referenced within the Marshal data). But it's also convenient to be able to encode a reference
# as a single value which will unambiguously refer to a given vertex, without us needing to
# separately pass around information about which type of object it refers to. The following union
# of dataclasses is intended to provide both of these conveniences at once.

class MarshalRefType(Enum):
    VALUE = 'V'
    SYMBOL = 'S'
    OBJECT = 'O'

@dataclass(frozen=True)
class MarshalRef:
    type_: MarshalRefType
    index: int

    def __str__(self):
        return f'{self.type_.value}{self.index}'

    def __repr__(self):
        return f'ref({repr(str(self))})'

def ref(s: str) -> MarshalRef:
    return MarshalRef(MarshalRefType(s[0]), int(s[1:]))

###################################################################################################
# Vertices
###################################################################################################

class MarshalVertex(ABC): pass

# Vertices of the following types are simple values, which cannot have references to them within
# the Marshal format, and are referenced in our parsed format by references of type
# MarshalRefType.VALUE. Comparison of these vertices is based on their component values, rather
# than object identity. None of them can have instance variables or be extended by a module.
# 
# (In Ruby, attempting to load Marshal data where any of these values are augmented by instance
# variables results in a "can't modify frozen class" erorr. If they are augmented by a module
# extension, then for fixnums it also fails with "can't define singleton", while for true, false
# and nil it works but the extension is not preserved on dumping.)

@dataclass(frozen=True)
class RubyTrue(MarshalVertex): pass
RUBY_TRUE = RubyTrue()

@dataclass(frozen=True)
class RubyFalse(MarshalVertex): pass
RUBY_FALSE = RubyFalse()

@dataclass(frozen=True)
class RubyNil(MarshalVertex): pass
RUBY_NIL = RubyNil()

@dataclass(frozen=True)
class RubyFixnum(MarshalVertex):
    value: int

MarshalLacksRef = RubyTrue | RubyFalse | RubyNil | RubyFixnum

# Vertices of the following types have comparison based on their component values, like those of
# the previous types, but can also be referenced within the Marshal format. This means that values
# like [1.2, 1.2] or [:a, :a] will be serialized with an object link in the second item, even
# the two items have the appearance of being constructed separately. Also like the previous vertex
# types, they can't have instance variables or be extended by a module.
# 
# (Extending a float with instance variables gives "can't modify frozen class". For symbols and
# class/module refs it gives no error but isn't preserved on dumping. Extending a float or symbol
# with a module gives "can't define singleton", while for clas/module refs it gives no error but
# isn't preserved on dumping.)

# Floats, symbols, class/module refs

@dataclass(frozen=True)
class RubyFloat(MarshalVertex):
    value: float

# I was unable to find clear information about how the names of Ruby symbols and class/module
# references are supposed to be encoded, so for the lack of a better option, the names are stored
# as bytes and a `decoded_name` method is provided which will decode the name to UTF-8 (with
# invalid bytes escaped via surrogates).

@dataclass(frozen=True)
class RubySymbol(MarshalVertex):
    name: bytes
    def decoded_name(self) -> str: return self.name.decode('utf-8', 'surrogateescape')

@dataclass(frozen=True)
class RubyClassRef(MarshalVertex):
    name: bytes
    def decoded_name(self) -> str: return self.name.decode('utf-8', 'surrogateescape')

@dataclass(frozen=True)
class RubyModuleRef(MarshalVertex):
    name: bytes
    def decoded_name(self) -> str: return self.name.decode('utf-8', 'surrogateescape')

@dataclass(frozen=True)
class RubyClassOrModuleRef(MarshalVertex):
    name: bytes
    def decoded_name(self) -> str: return self.name.decode('utf-8', 'surrogateescape')

# For all subsequently-defined vertex types, comparison is based on object identity. 

# Bignums are unique in that although their comparison is based on object identity, they can't have
# instance variables or be extended by a module. (Attempting to do so gives a "can't modify frozen
# class" or "can't define singleton" error, respectively.)
@dataclass(frozen=True, eq=False)
class RubyBignum(MarshalVertex):
    value: int

# For all subsequently-defined vertex types, extension by instance variables or modules is
# possible. Note that even if the "e" comes before the "I" in the loaded data, it will be
# normalized to have "I" before "e" in the output.

# It seems safer to use a list of key-value pairs rather than a dictionary here, since the keys are
# really references to keys (not the keys themselves) and we don't know how exactly how Ruby is
# going to hash the values. 
MarshalPairSeq = list[tuple[MarshalRef, MarshalRef]]

@dataclass(frozen=True, eq=False)
class MarshalExtensibleVertex(MarshalVertex, ABC):
    # The instance variables of the Ruby object
    inst_vars: MarshalPairSeq # keys should have type_=MarshalRefType.SYMBOL

    # A list of modules which the Ruby object is extended by ("innermost" first, in terms of how
    # the Marshal format is structured).
    module_ext: list[MarshalRef] # should have type_=MarshalRefType.SYMBOL
    
    # turns out we don't need these methods right now, though maybe we will in future
    #def deref_inst_vars(self, graph: 'MarshalGraph') -> Iterator[tuple[RubySymbol, Optional[MarshalVertex]]]:
        #for key_ref, value_ref in self.inst_vars:
            #key = graph[key_ref]
            #assert isinstance(key, RubySymbol) # for mypy
            #yield key, graph[value_ref]
            #
    #def deref_module_ext(self, graph: 'MarshalGraph') -> Iterator[RubySymbol]:
        #for module_ref in self.module_ext:
            #module = graph[module_ref]
            #assert isinstance(module, RubySymbol) # for mypy
            #yield module    

@dataclass(frozen=True, eq=False)
class RubyString(MarshalExtensibleVertex):
    value: bytes

@dataclass(frozen=True, eq=False)
class RubyRegex(MarshalExtensibleVertex):
    source: bytes
    options: set[re.RegexFlag]
                
# All the following vertex types are non-atomic: their content is just references to other
# vertices. (As such they can't really be said to be representations of Ruby objects, taken on
# their own; they only make sense in the context of the Marshal object graph, and so their names
# are in the format MarshalX rather than RubyX.)

@dataclass(frozen=True, eq=False)
class MarshalArray(MarshalExtensibleVertex):
    items: list[MarshalRef]

@dataclass(frozen=True, eq=False)
class MarshalHash(MarshalExtensibleVertex):
    items: MarshalPairSeq
    default: Optional[MarshalRef]

# Regular objects have the same instance variables as other objects; they just have a special
# syntax for the instance variables. Variables from both "I" and "o" will be merged.
@dataclass(frozen=True, eq=False)
class MarshalRegObj(MarshalExtensibleVertex):
    cls: MarshalRef # should have type_ == MarshalRefType.SYMBOL

# Members are distinct from ordinary instance variables.
@dataclass(frozen=True, eq=False)
class MarshalStruct(MarshalExtensibleVertex):
    name: MarshalRef # should have type_ == MarshalRefType.SYMBOL
    members: MarshalPairSeq # keys should have type_ == MarshalRefType.SYMBOL

@dataclass(frozen=True, eq=False)
class MarshalWrappedExtPtr(MarshalExtensibleVertex):
    cls: MarshalRef # should have type_ == MarshalRefType.SYMBOL
    obj: MarshalRef

@dataclass(frozen=True, eq=False)
class MarshalUserBuiltin(MarshalExtensibleVertex):
    cls: MarshalRef # should have type_ == MarshalRefType.SYMBOL
    obj: MarshalRef

@dataclass(frozen=True, eq=False)
class MarshalUserObject(MarshalExtensibleVertex):
    cls: MarshalRef # should have type_ == MarshalRefType.SYMBOL
    obj: MarshalRef

@dataclass(frozen=True, eq=False)
class MarshalUserData(MarshalExtensibleVertex):
    cls: MarshalRef # should have type_ == MarshalRefType.SYMBOL
    data: bytes

def vertex_ref_type(vertex: MarshalVertex) -> MarshalRefType:
    if isinstance(vertex, RubySymbol):
        return MarshalRefType.SYMBOL
    elif isinstance(vertex, get_args(MarshalLacksRef)):
        return MarshalRefType.VALUE
    else:
        return MarshalRefType.OBJECT

@dataclass
class MarshalGraph:
    """A Marshal object, represented as a graph.

    Instances of this class can also represent a graph under construction."""

    # These three lists are used for mapping references to vertices. For graphs under construction,
    # a reference may map to None (if we know that a vertex with a certain reference will be in the
    # graph, but we don't know the exact contents of the vertex yet).
    vertices: dict[MarshalRefType, list[Optional[MarshalVertex]]]

    @property
    def values(self): return self.vertices[MarshalRefType.VALUE]

    @property
    def symbols(self): return self.vertices[MarshalRefType.SYMBOL]

    @property
    def objects(self): return self.vertices[MarshalRefType.OBJECT]

    # This dictionary is used for mapping vertices to references.
    refs: dict[MarshalVertex, MarshalRef]

    def __init__(self):
        self.vertices = {ref_type: [] for ref_type in MarshalRefType}
        self.refs = {}

    def __getitem__(self, ref: MarshalRef) -> Optional[MarshalVertex]:
        return self.vertices[ref.type_][ref.index]

    def __setitem__(self, ref: MarshalRef, vertex: MarshalVertex) -> None:
        """Replace the vertex at the given reference with a new one."""
        ref_type = ref.type_
        new_ref_type = vertex_ref_type(vertex)
        if new_ref_type != ref_type: raise ValueError(f'vertex has wrong type for the given ref')
        array = self.vertices[ref_type]
        index = ref.index
        old_vertex = array[index]
        array[index] = vertex
        if old_vertex is not None: del self.refs[old_vertex]
        self.refs[vertex] = ref

    def add(self, vertex: Optional[MarshalVertex]) -> MarshalRef:
        """Add a vertex to the graph.

        The vertex may be None, in which case None is added as a placeholder under the next
        available reference of MarshalObjectRef type (it can be replaced with the actual vertex
        later on via a call to __setitem__)."""
        ref_type = MarshalRefType.OBJECT if vertex is None else vertex_ref_type(vertex)    

        if vertex is None or vertex not in self.refs:
            array = self.vertices[ref_type]
            index = len(array)
            ref = MarshalRef(ref_type, index)
            array.append(vertex)

            if vertex is not None:
                self.refs[vertex] = ref

            return ref
        
        if ref_type != MarshalRefType.VALUE:
             raise ValueError(
                 "add() shouldn't need to be called on a vertex which is not of "
                 "MarshalLacksRef type more than once"
             )
        
        return self.refs[vertex]
        
    def root_ref(self) -> MarshalRef:
        # Since any vertex of type MarshalSymbol or MarshalLacksRef lacks children, the only way
        # one of them can be the root is if it is the only vertex in the graph. Otherwise, we
        # assume that the root is the first vertex in `self.objects`.
        if self.objects: return ref('O0')
        
        if len(self.symbols) + len(self.values) > 1:
            raise ValueError('graph under construction, root cannot be determined')
        
        if self.symbols: return ref('S0')
        if self.values: return ref('V0')

        raise ValueError('graph under construction, has no vertices in it yet')

    def root(self) -> MarshalVertex:
        res = self[self.root_ref()]

        if res is None:
            raise ValueError('root not yet fully constructed')

        return res

@dataclass
class MarshalFile:
    """The parsed result of a call to Ruby's `Marshal.dump` function.

    The result of such a call is a byte-string where the first two bytes encode the major and minor
    version of Marshal that was used (major first, minor seond), and the remaining bytes encode a
    single Ruby object. After parsing, the major and minor version are stored in the
    `major_version` and `minor_version` attributes of the resulting `MarshalFile` object, while the
    Ruby object is encoded as a rooted graph whose vertices are stored in the `vertices` attribute,
    with the root vertex being the first vertex in this list.

    The vertices are encoded as `MarshalVertex` objects. These come in various types. The following
    are leaf types:

       `RubyTrue`, `RubyFalse`, `RubyNil`, `RubyFixnum`, `RubyBignum`, `RubyFloat`, `RubyString`,
       `RubyRegex`, `RubySymbol`, `RubyClassRef`, `RubyModuleRef`, `RubyClassOrModuleRef`

    The others have one or more children.

    Attributes:
      - `major_version`, `minor_version`: the Marshal version information.
      - `vertices`: the vertices in the 
      - `tree`: the structure of the Ruby object, with all 
      - `table`: the lookup table for mapping from the IDs in `tree` to their corresponding
        `RubyObject` objects.

    vertices should be keyed by MarshalRefs
    """
    major_version: int
    minor_version: int
    graph: MarshalGraph

    # def dump(self) -> Iterator[int]:
    #     yield from Dumper(self)

###################################################################################################
# Load
###################################################################################################

class ParseError(Exception):
    def __init__(self, offset: int, message: str) -> None:
        super().__init__(f'offset {hex(offset)}: {message}')

class Loader:
    data: Sequence[int]
    offset: int
    graph: MarshalGraph

    def __init__(self, data: Sequence[int]) -> None:
        self.data = data
        self.offset = 0
        self.graph = MarshalGraph()

    @property
    def done(self):
        return self.offset >= len(self.data)

    def error(self, message: str) -> None:
        raise ParseError(self.offset, message) from None
        
    def warning(self, message: str) -> None:
        print(f'WARNING: {hex(self.offset)}: {message}')

    def debug(self, message: str) -> None:
        if DEBUG:
            segment = ' '.join(
                hex(byte)[2:].zfill(2)
                for byte in self.data[max(0, self.offset - 5):self.offset + 5]
            )

            if self.offset > 5: segment = '...' + segment
            if self.offset < len(self.data) - 5: segment += '...' 
            print(f'{hex(self.offset)} [{segment}]: {message}', file=DEBUGLOG)

    def load(self) -> MarshalFile:
        self.debug('begin load')
        major_version, minor_version = self.read_bytes(2)
        self.load_object()
        self.debug('end load')

        if self.done:
            return MarshalFile(major_version, minor_version, self.graph)

        self.error('parsing has finished but not all of the input was consumed')
        assert False

    def read_byte(self) -> int:
        try:
            byte = self.data[self.offset]
        except IndexError:
            self.error('incomplete input')
            assert False
        else:
            self.offset += 1
            return byte

    def read_bytes(self, length: int) -> Iterator[int]:
        for _ in range(length):
            yield self.read_byte()

    def read_long(self) -> int:
        """"
        >>> Loader([0]).read_long()
        0
        >>> Loader([1]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x1: incomplete input
        >>> Loader([1, 0]).read_long()
        0
        >>> Loader([1, 255]).read_long()
        255
        >>> Loader([2]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x1: incomplete input
        >>> Loader([2, 0]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x2: incomplete input
        >>> Loader([2, 0, 255]).read_long()
        65280
        >>> Loader([3]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x1: incomplete input
        >>> Loader([3, 0, 0]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x3: incomplete input
        >>> Loader([3, 0, 0, 255]).read_long()
        16711680
        >>> Loader([4]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x1: incomplete input
        >>> Loader([4, 0, 0, 0]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x4: incomplete input
        >>> Loader([4, 0, 0, 0, 255]).read_long()
        4278190080
        >>> Loader([5]).read_long()
        0
        >>> Loader([6]).read_long()
        1
        >>> Loader([127]).read_long()
        122
        >>> Loader([128]).read_long()
        -123
        >>> Loader([250]).read_long()
        -1
        >>> Loader([251]).read_long()
        0
        >>> Loader([252]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x1: incomplete input
        >>> Loader([252, 255, 255, 255]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x4: incomplete input
        >>> Loader([252, 255, 255, 255, 0]).read_long()
        -4278190081
        >>> Loader([253]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x1: incomplete input
        >>> Loader([253, 255, 255]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x3: incomplete input
        >>> Loader([253, 255, 255, 0]).read_long()
        -16711681
        >>> Loader([254]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x1: incomplete input
        >>> Loader([254, 255]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x2: incomplete input
        >>> Loader([254, 255, 0]).read_long()
        -65281
        >>> Loader([255]).read_long()
        Traceback (most recent call last):
            ...
        ParseError: offset 0x1: incomplete input
        >>> Loader([255, 0]).read_long()
        -256
        >>> Loader([255, 255]).read_long()
        -1
        """
        header = int.from_bytes([self.read_byte()], 'little', signed=True)
        if header == 0: return 0
        header_mag = abs(header)
        header_sign = header // header_mag
        if header_mag >= 5: return header_sign * (header_mag - 5)
        value = int.from_bytes(self.read_bytes(header_mag), 'little')
        return value if header_sign == 1 else -(2**(8*header_mag) - value)
        
    def read_byte_seq(self) -> bytes:
        length = self.read_long()
        return bytes(self.read_bytes(length))

    def read_float(self) -> float:
        """
        >>> Loader([8, 105, 110, 102]).read_float() # b'inf'
        inf
        >>> Loader([9, 45, 105, 110, 102]).read_float() # b'-inf'
        -inf
        >>> Loader([8, 110, 97, 110]).read_float() # b'nan'
        nan
        >>> Loader([8, 73, 78, 70]).read_float() # b'INF'
        0.0
        >>> Loader([9, 45, 73, 78, 70]).read_float() # b'-INF'
        0.0
        >>> Loader([8, 78, 65, 78]).read_float() # b'NAN'
        0.0
        >>> Loader([0]).read_float() # b''
        0.0
        >>> Loader([6, 48]).read_float() # b'0'
        0.0
        >>> Loader([8, 49, 46, 49]).read_float() # b'1.1'
        1.1
        >>> Loader([10, 49, 46, 49, 101, 50]).read_float() # b'1.1e2'
        110.0
        >>> Loader([10, 49, 46, 49, 69, 50]).read_float() # b'1.1E2'
        110.0
        >>> Loader([10, 48, 120, 49, 46, 49]).read_float() # b'0x1.1'
        1.0625
        >>> Loader([12, 48, 120, 49, 46, 49, 112, 50]).read_float() # b'0x1.1p2'
        4.25
        >>> Loader([12, 48, 120, 49, 46, 49, 80, 50]).read_float() # b'0x1.1P2'
        4.25
        """
        bytes_ = self.read_byte_seq()

        try:
            return {b'inf': math.inf, b'-inf': -math.inf, b'nan': math.nan}[bytes_]
        except KeyError:
            # The format here is not very precisely defined. All we know is that "the byte sequence
            # contains a C double (loadable by strtod(3))". However, the behaviour of strtod
            # depends on the locale. I'd imagine it also may not be implemented exactly in
            # accordance with the C standard. Perhaps Ruby defines its own version of strtod, but
            # I can't be bothered trying to find out if that is the case. Testing reveals some
            # apparent divergence from the standard: non-lowercase variants of 'inf', '-inf' and
            # 'nan' aren't understood, so they are loaded as 0.0, rather than as inf, -inf and nan.
            # But otherwise it seems to work as described at
            # https://man7.org/linux/man-pages/man3/strtod.3.html.
            #
            # Python has the locale.atof() function, which does locale-aware interpretation of
            # strings and floats. Unlike Ruby's Marshal.load, it raises an error if there are
            # are trailing characters after parsing, it can't handle hexadecimal notation, and it
            # parses inf, -inf and nan without case-sensitivity. But we can work around that by
            # doing some preprocessing of the string ourselves.
            #
            # So for now, I'm just going to use locale.atof(), though I'm not really sure how
            # robust this approach is.

            s = bytes_.decode('us-ascii')
            if not s or s.lower() in ('inf', '-inf', 'nan'): return 0.0
            point = locale.localeconv()['decimal_point']
            assert isinstance(point, str) # for mypy
            point = '\\' + point
            decimal_exp_pat = r'[Ee][+\-]?\d+'
            decimal_pat = fr'\d+(?:{point}\d*)?(?:{decimal_exp_pat})?'
            bin_exp_pat = r'[Pp][+\-]?\d+'
            hex_pat = fr'(0[xX])[\da-fA-f]+(?:{point}[\da-fA-f]*)?(?:{bin_exp_pat})?'
            m = re.match(fr'^\s*[+\-]?(?:{hex_pat}|{decimal_pat})', s)

            if m is None:
                self.error(f'invalid byte sequence for float: {bytes_!r}')
                assert False

            s, is_hex = m.group(0, 1)

            if is_hex:
                s = locale.delocalize(s)
                return float.fromhex(s)

            return locale.atof(s)

    REGEX_OPTIONS_TABLE: ClassVar[list[re.RegexFlag]] = [re.I, re.X, re.M]

    def read_regex_options(self) -> set[re.RegexFlag]:
        bits = self.read_byte()
        res = set()
        
        for i in range(8):
            bits, is_set = divmod(bits, 2)
            
            if is_set:
                try:
                    flag = self.REGEX_OPTIONS_TABLE[i]
                except IndexError:
                    self.warning(
                        f'{i}th bit in regex options byte is set, but this does not correspond to '
                        'a recognized flag and will be ignored'
                    )
                else:
                    res.add(flag)
        
        return res

    def load_object(self) -> MarshalRef:
        """
        It can handle cyclic references:
        >>> loader = Loader([91, 6, 64, 0])
        >>> loader.load_object()
        ref('O0')
        >>> loader.graph.values
        []
        >>> loader.graph.symbols
        []
        >>> loader.graph.objects
        [MarshalArray(inst_vars=[], module_ext=[], items=[ref('O0')])]

        Arrays loaded separately are treated as distinct, and assigned separate indexes:
        >>> loader = Loader([91, 7, 91, 0, 91, 0])
        >>> loader.load_object()
        ref('O0')
        >>> loader.graph.values
        []
        >>> loader.graph.symbols
        []
        >>> loader.graph.objects
        [MarshalArray(inst_vars=[], module_ext=[], items=[ref('O1'), ref('O2')]), MarshalArray(inst_vars=[], module_ext=[], items=[]), MarshalArray(inst_vars=[], module_ext=[], items=[])]
        >>> loader.graph.refs[loader.graph.objects[1]]
        ref('O1')
        >>> loader.graph.refs[loader.graph.objects[2]]
        ref('O2')

        But arrays linked by references are identical:
        >>> loader = Loader([91, 7, 91, 0, 64, 6])
        >>> loader.load_object()
        ref('O0')
        >>> loader.graph.values
        []
        >>> loader.graph.symbols
        []
        >>> loader.graph.objects
        [MarshalArray(inst_vars=[], module_ext=[], items=[ref('O1'), ref('O1')]), MarshalArray(inst_vars=[], module_ext=[], items=[])]
        """
        type_code = chr(self.read_byte())
        return self.load_object_without_type_code(type_code)

    def load_symbol(self) -> MarshalRef: # return value should have type_ == MarshalRefType.SYMBOL
        type_code = chr(self.read_byte())

        if type_code not in (';', ':'):
            self.error(f'expected to be loading a symbol, but the type code is "{type_code}"')

        return self.load_object_without_type_code(type_code)

    def load_hash_items(self, *, symbol_keys=False) -> list[tuple[MarshalRef, MarshalRef]]:
        length = self.read_long()
        self.debug(f'list of pairs of length {length}')
        items = []

        for _ in range(length):
            key_ref = self.load_symbol() if symbol_keys else self.load_object()
            value_ref = self.load_object()
            items.append((key_ref, value_ref))

        return items

    # keys of return value should have type_ == MarshalRefType.SYMBOL
    def load_vars(self) -> list[tuple[MarshalRef, MarshalRef]]:
        return self.load_hash_items(symbol_keys=True)

    def load_object_without_type_code(self, type_code: str) -> MarshalRef:
        if type_code == ';':
            index = self.read_long()
            ref = MarshalRef(MarshalRefType.SYMBOL, index)
            self.debug(f'-> {ref}: {self.graph[ref]}')
            return ref
        
        if type_code == '@':
            index = self.read_long()
            ref = MarshalRef(MarshalRefType.OBJECT, index)
            self.debug(f'-> {ref}: {self.graph[ref]}')
            return ref

        try: vertex = {'T': RUBY_TRUE, 'F': RUBY_FALSE, '0': RUBY_NIL}[type_code]
        except KeyError: pass
        else:
            ref = self.graph.add(vertex)
            self.debug(f'{ref}: {self.graph[ref]}')
            return ref

        if type_code == 'i':
            ref = self.graph.add(RubyFixnum(self.read_long()))
            self.debug(f'{ref}: {self.graph[ref]}')
            return ref

        if type_code == 'l':
            sign = {'+': 1, '-': -1}[chr(self.read_byte())]
            word_length = self.read_long()
            
            ref = self.graph.add(RubyBignum(int.from_bytes(
                self.read_bytes(word_length * 2), 'little', signed=True
            )))

            self.debug(f'{ref}: {self.graph[ref]}')
            return ref

        if type_code == 'f':
            ref = self.graph.add(RubyFloat(self.read_float()))
            self.debug(f'{ref}: {self.graph[ref]}')
            return ref

        if type_code == '"':
            bytes_ = self.read_byte_seq()
            ref = self.graph.add(RubyString([], [], bytes_))
            self.debug(f'{ref}: {self.graph[ref]}')
            return ref

        if type_code == '/':
            source = self.read_byte_seq()
            options = self.read_regex_options()
            ref = self.graph.add(RubyRegex([], [], source, options))
            self.debug(f'{ref}: {self.graph[ref]}')
            return ref

        try:
            vertex_type = {
                ':': RubySymbol, 'c': RubyClassRef, 'm': RubyModuleRef, 'M': RubyClassOrModuleRef
            }[type_code]
        except KeyError:
            pass
        else:
            name = self.read_byte_seq()
            ref = self.graph.add(vertex_type(name))
            self.debug(f'{ref}: {self.graph[ref]}')
            return ref
            
        if type_code == 'I':
            self.debug('object with inst vars')
            ref = self.load_object()
            obj = self.graph[ref]
            inst_vars = self.load_vars()
            
            if isinstance(obj, MarshalExtensibleVertex):
                obj.inst_vars.extend(inst_vars)
            else:
                self.warning(f'found instance variables attached to an object of type {type(obj)}; these will be ignored')
                            
            return ref            

        if type_code == 'e':
            # so it turns out that the documentation at
            # https://ruby-doc.org/core-3.1.2/doc/marshal_rdoc.html
            # has the parts in the wrong order? it says the symbol containing the name of the
            # module comes after the object, but it actually comes before -_-

            self.debug('object extended by module')
            module_ref = self.load_symbol()
            ref = self.load_object()
            obj = self.graph[ref]
            
            if isinstance(obj, MarshalExtensibleVertex):
                obj.module_ext.append(module_ref)
            else:
                self.warning(f'found object of type {type(obj)}) extended by a module; this will be ignored')
                
            return ref

        ref = self.graph.add(None)
        self.debug(f'{ref} begin')

        if type_code == '[':
            length = self.read_long()
            self.debug(f'array of length {length}')
            items = [self.load_object() for _ in range(length)]
            self.graph[ref] = MarshalArray([], [], items)
            self.debug(f'{ref} end')
            return ref

        if type_code == '{':
            self.debug('hash without default')
            pairs = self.load_hash_items()
            self.graph[ref] = MarshalHash([], [], pairs, None)
            self.debug(f'{ref} end')
            return ref

        if type_code == '}':
            self.debug('hash with default')
            pairs = self.load_hash_items()
            self.debug(f'default for {ref}')
            default = self.load_object()
            self.graph[ref] = MarshalHash([], [], pairs, default)
            self.debug(f'{ref} end')
            return ref
        
        if type_code == 'o':
            self.debug('regular object')
            cls_ref = self.load_symbol()
            inst_vars = self.load_vars()
            self.graph[ref] = MarshalRegObj(inst_vars, [], cls_ref)
            self.debug(f'{ref} end')
            return ref
        
        if type_code == 'S':
            self.debug('struct')
            name_ref = self.load_symbol()
            members = self.load_vars()
            self.graph[ref] = MarshalStruct([], [], name_ref, members)
            self.debug(f'{ref} end')
            return ref
            
        try:
            vertex_type2 = {
                'C': MarshalUserBuiltin, 'd': MarshalWrappedExtPtr, 'U': MarshalUserObject
            }[type_code]
        except KeyError:
            pass
        else:
            self.debug(f'{vertex_type2} wrapper')
            cls_ref = self.load_symbol()
            obj_ref = self.load_object()
            self.graph[ref] = vertex_type2([], [], cls_ref, obj_ref)
            self.debug(f'{ref} end')
            return ref
            
        if type_code == 'u':
            self.debug('user data')
            cls_ref = self.load_symbol()
            data = self.read_byte_seq()
            self.graph[ref] = MarshalUserData([], [], cls_ref, data)
            self.debug(f'{ref} end')
            return ref

        self.error(f'invalid type code "{type_code}"')
        assert False

###################################################################################################
# Dump
###################################################################################################
# Forget about this for now (and possibly for ever)

# def dump_long(value: int) -> Iterator[int]:
#     # https://docs.ruby-lang.org/en/master/marshal_rdoc.html
#     # "There are multiple representations for many values. CRuby always outputs the
#     # shortest representation possible."
#     # 
#     # This doesn't say anything about other implementations, and other implementations
#     # exist. So doing a load and dump may in theory not preserve the exact representation for
#     # other implementations.
#     if value == 0:
#         yield 0
#     elif 0 < value < 123:
#         yield value + 5
#     elif -123 <= value < 0:
#         yield 251 + value
#     else:
#         byte_length = (value.bit_length() + 7) // 8
#         assert byte_length <= 4
#         yield 256 - byte_length if value < 0 else byte_length
#         yield from value.to_bytes(byte_length, 'little', signed=True)

# def dump_byte_seq(seq: bytes) -> Iterator[int]:
#     yield from dump_long(len(seq))
#     yield from seq

# class Dumper:
#     file: MarshalFile
#     visited: set[int]

#     # these only exist for testing --- we want to make sure the reference numbers are preserved
#     symbol_ids: list[int]
#     object_ids: list[int]

#     def __init__(self, file: MarshalFile) -> None:
#         self.file = file
#         self.visited = set()
#         self.symbol_ids = []
#         self.object_ids = []

#     def __iter__(self):
#         yield self.file.major_version
#         yield self.file.minor_version
#         yield from self.visit(0)

#     def visit(self, vertex_id: MarshalRef, *, assert_is_symbol=False) -> Iterator[int]:
#         vertex = self.file.graph[vertex_id]

#         try: yield ord({RubyTrue: 'T', RubyFalse: 'F', RubyNil: '0'}[vertex])
#         except KeyError: pass
#         else: return

#         if isinstance(vertex, RubyFixnum):
#             yield ord('i')
#             yield from dump_long(vertex.value)
#             return

#         is_symbol = isinstance(vertex, RubySymbol)
#         if assert_is_symbol: assert is_symbol

#         if vertex_id in self.visited:
#             yield ord(';') if is_symbol else ord('@')
#             yield from dump_long(vertex.marshal_ref)
#             return

#         self.visited.add(vertex_id)
#         assert vertex.marshal_ref == (len(self.symbol_ids) if is_symbol else len(self.object_ids) + 1)

#         if isinstance(vertex, RubyBignum):
#             yield ord('l')
#             value = vertex.value
#             yield ord('+' if value >= 0 else '-')
#             word_length = (value.bit_length() + 15) // 16
#             yield from dump_long(word_length)
#             yield from value.to_bytes(word_length * 2, 'little', signed=True)
#             return

#         if isinstance(vertex, RubyFloat):
#             yield ord('f')
#             value = vertex.value
#             ba = bytearray()

#             if math.isnan(value):
#                 ba += b'nan'
#             elif math.isinf(value):
#                 if value < 0: ba += ord('-')
#                 ba += b'inf'
#             else:
#                 # this could also not be preserved by load/dump
#                 ba += struct.pack('d', value)

#             yield from dump_byte_seq(ba)
#             return

#         if isinstance(vertex, RubyString):
#             yield ord('"')
#             yield from dump_byte_seq(vertex.value)
#             return

#         if isinstance(vertex, RubyRegex):
#             yield ord('/')
#             yield from dump_byte_seq(vertex.source)
#             yield vertex.options
#             return

#         if isinstance(vertex, RubySymbol):
#             yield ord(':')
#             yield from dump_byte_seq(vertex.name)
#             return

#         if isinstance(vertex, RubyClassRef):
#             yield ord('c')
#             yield from dump_byte_seq(vertex.name)
#             return

#         if isinstance(vertex, RubyModuleRef):
#             yield ord('m')
#             yield from dump_byte_seq(vertex.name)
#             return

#         if isinstance(vertex, RubyClassOrModuleRef):
#             yield ord('M')
#             yield from dump_byte_seq(vertex.name)
#             return

#         if isinstance(vertex, MarshalArray):
#             yield ord('[')
#             items = vertex.items
#             yield from dump_long(len(items))
#             for item in vertex: yield from self.visit(item)
#             return

#         if isinstance(vertex, MarshalHash):
#             yield ord('{')
#             items = vertex.items
#             yield from dump_long(len(items))

#             for key, value in vertex.items:
#                 yield from self.visit(key)
#                 yield from self.visit(value)

#             default = vertex.default

#             if default is not None:
#                 yield from self.visit(default)

#             return

#         if isinstance(vertex, MarshalRegObj):
#             yield ord('o')
#             yield from self.visit(vertex.cls, assert_is_symbol=True)
#             yield from dump_long(len(vertex.inst_vars))

#             for name, value in vertex.inst_vars:
#                 yield from self.visit_symbol(name)
#                 yield from self.visit(value)

#             return

#         if isinstance(vertex, MarshalStruct):
#             yield ord('S')
#             yield from self.visit(vertex.cls, assert_is_symbol=True)
#             yield from dump_long(len(vertex.inst_vars))

#             for name, value in vertex.inst_vars:
#                 yield from self.visit(name, assert_is_symbol=True)
#                 yield from self.visit(value)

#             return

#         if isinstance(vertex, MarshalUserBuiltin):
#             yield ord('C')
#             yield from self.visit(vertex.cls, assert_is_symbol=True)
#             yield from self.visit(vertex.obj)
#             return

#         if isinstance(vertex, MarshalWrappedExtPtr):
#             yield ord('d')
#             yield from self.visit(vertex.cls, assert_is_symbol=True)
#             yield from self.visit(vertex.obj)
#             return

#         if isinstance(vertex, MarshalInstVars):
#             yield ord('I')
#             yield from self.visit(vertex.obj)
#             yield from dump_long(len(vertex.inst_vars))

#             for name, value in vertex.inst_vars:
#                 yield from self.visit(name, assert_is_symbol=True)
#                 yield from self.visit(value)

#             return

#         if isinstance(vertex, MarshalModuleExt):
#             yield ord('e')
#             yield from self.visit(vertex.obj)
#             yield from self.visit(vertex.module, assert_is_symbol=True)
#             return

#         if isinstance(vertex, MarshalUserData):
#             yield ord('u')
#             yield from self.visit(vertex.cls, assert_is_symbol=True)
#             yield from self.visit_byte_seq(vertex.data)
#             return

#         if isinstance(vertex, MarshalUserObject):
#             yield ord('U')
#             yield from self.visit(vertex.cls, assert_is_symbol=True)
#             yield from self.visit(vertex.obj)
#             return

###################################################################################################
# The following helper functions are used for fetching data from the graph via a reference while
# asserting that the referenced vertex has a particular type/format. They are conveniences which
# simplify the process of inspecting the graph in the most common cases; they aren't designed to
# handle every possible situation (for example, the `get_string` method expects the string to have
# no instance variables other than the one for the encoding; if you are dealing with string data
# that may have other instance variables added to it for some reason, you should write your own
# version of the `get_string` method to deal with that).

Lookup = Callable[[MarshalGraph, MarshalRef], Any]

def get_ref(graph: MarshalGraph, ref: MarshalRef) -> MarshalRef:
    return ref

def get_bool(graph: MarshalGraph, ref: MarshalRef) -> bool:
    return {RUBY_TRUE: True, RUBY_FALSE: False}[graph[ref]]    

def get_fixnum(graph: MarshalGraph, ref: MarshalRef) -> int:
    vertex = graph[ref]
    assert isinstance(vertex, RubyFixnum)
    return vertex.value

def get_symbol(graph: MarshalGraph, ref: MarshalRef) -> str:
    vertex = graph[ref]
    assert isinstance(vertex, RubySymbol)
    return vertex.name.decode('utf-8', 'surrogateescape')

def get_inst_vars(graph: MarshalGraph, ref: MarshalRef) -> OrderedDict[str, MarshalRef]:
    vertex = graph[ref]
    
    if not isinstance(vertex, MarshalExtensibleVertex):
        raise ValueError(f'vertex at {ref} does not have instance variables')
    
    inst_vars = {}
    
    for key_ref, value_ref in vertex.inst_vars:
        name = get_symbol(graph, key_ref)
        inst_vars[name] = value_ref
        
    return inst_vars

def get_encoding(graph: MarshalGraph, ref: MarshalRef) -> str:
    vertex = graph[ref]
    
    if vertex == RUBY_TRUE: return 'utf-8'
    if vertex == RUBY_FALSE: return 'us-ascii'
    
    if not isinstance(vertex, RubyString):
        raise ValueError('cannot read non-boolean, non-string vertex as encoding')
        
    if vertex.inst_vars or vertex.module_ext:
        raise ValueError(
            'this Ruby string which I think is an encoding name string has instance variables '
            'and/or is extended by modules, which probably means it\'s not actually an encoding '
            'name and the loaded Marshal data was corrupt'
        )
        
    try:           
        name = vertex.value.decode('us-ascii')
    except UnicodeDecodeError:
        raise ValueError(
            'this Ruby string which I think is an encoding name is not ASCII-decodable, which '
            'probably means it\'s not actually an encoding name and the loaded Marshal data was '
            'corrupt'
        )
        
    # that's right, we simply assume that Python will understand the name in the same way as Ruby
    return name

def get_encoding_from_inst_vars(
    graph: MarshalGraph, ref: MarshalRef
) -> tuple[Optional[str], MarshalPairSeq]:

    vertex = graph[ref]
    new_inst_vars = []
    encoding = None
    
    for key_ref, value_ref in vertex.inst_vars:
        if get_symbol(graph, key_ref) == 'E':
            encoding = get_encoding(graph, value_ref)
        else:
            new_inst_vars.append((key_ref, value_ref))
        
    return encoding, new_inst_vars
        
def get_string(graph: MarshalGraph, ref: MarshalRef) -> str:
    vertex = graph[ref]
    assert isinstance(vertex, RubyString)
    encoding, inst_vars = get_encoding_from_inst_vars(graph, ref)
    decode_args = ('utf-8', 'surrogateescape') if encoding is None else (encoding,)
    assert not inst_vars
    return vertex.value.decode(*decode_args)

def get_array(graph: MarshalGraph, ref: MarshalRef, callback: Lookup=get_ref) -> list:
    vertex = graph[ref]
    assert isinstance(vertex, MarshalArray)
    assert not vertex.inst_vars
    assert not vertex.module_ext
    return [callback(graph, item_ref) for item_ref in vertex.items]
    
def get_atom(graph: MarshalGraph, ref: MarshalRef) -> None | bool | int | float | str:
    vertex = graph[ref]
    
    try:
        return {RUBY_NIL: None, RUBY_TRUE: True, RUBY_FALSE: False}[vertex]
    except KeyError:
        pass

    if isinstance(vertex, RubyFixnum): return vertex.value
    if isinstance(vertex, RubyBignum): return vertex.value
    if isinstance(vertex, RubyFloat): return vertex.value

    if isinstance(vertex, RubyString): return get_string(graph, ref)
    
def get_hash(
    graph: MarshalGraph, ref: MarshalRef, key_callback: Lookup=get_ref, value_callback: Lookup=get_ref
) -> dict:

    vertex = graph[ref]
    assert isinstance(vertex, MarshalHash)
    assert not vertex.inst_vars
    assert not vertex.module_ext
    assert vertex.default is None
    
    return {
        key_callback(graph, key_ref): value_callback(graph, value_ref)
        for key_ref, value_ref in vertex.items
    }

def get_inst(
    graph: MarshalGraph, ref: MarshalRef, class_name: str, ctor: Callable[..., Any],
    inst_var_callbacks: dict[str, Lookup]
) -> Any:

    vertex = graph[ref]

    if not isinstance(vertex, MarshalRegObj):
        raise ValueError(f'vertex at ref {ref} is not a regular object')

    actual_class_name = get_symbol(graph, vertex.cls)
    
    if actual_class_name != class_name:
        raise ValueError(
            f'expected an instance of \'{class_name}\', got an instance of \'{actual_class_name}\''
        )
    
    assert not vertex.module_ext
    inst_vars = {}
    
    for key_ref, value_ref in vertex.inst_vars:
        key = get_symbol(graph, key_ref)
        assert key[0] == '@'
        mainkey = key[1:]
        
        try:
            callback = inst_var_callbacks[mainkey]
        except KeyError:
            raise ValueError(f'unexpected instance variable "{mainkey}" for class "{class_name}"')
        else:
            value = callback(graph, value_ref)
            inst_vars[mainkey] = value
            
    for key in inst_var_callbacks.keys():
        if key not in inst_vars:
            raise ValueError(f'expected instance variable "{key}" for class "{class_name}"')
            
    return ctor(**inst_vars)

def get_user_data(graph: MarshalGraph, ref: MarshalRef, class_name: str) -> bytes:
    vertex = graph[ref]
    assert isinstance(vertex, MarshalUserData)
    assert get_symbol(graph, vertex.cls) == class_name
    assert not vertex.inst_vars
    assert not vertex.module_ext
    return vertex.data
        
###################################################################################################        
        
# important that we only use hashable stuff --- Ruby may have arrays/hashes as hash keys
# (hence why this is only Json-ish)
Jsonish = bool | None | int | float | str | tuple['Jsonish', ...] | frozendict[str, 'Jsonish']

class JsonishFormatter:
    """Formats a Marshal object graph into a Python object whose structure can be inspected using
    `json.dumps`.
    
    This may be a lossy transformation. (It might not be, but no particular care has been taken to
    make sure it isn't lossy.)"""
    graph: MarshalGraph
    seen: set[MarshalRef]
    
    def __init__(self, graph: MarshalGraph):
        self.graph = graph
        self.seen = set()

    def format(self) -> Jsonish:
        return self.format_at(self.graph.root_ref())
        
    REGEX_OPTIONS_TABLE = {re.I: 'i', re.X: 'x', re.M: 'm'}
        
    def format_at(self, ref: MarshalRef) -> Jsonish:
        if ref.type_ == MarshalRefType.OBJECT and ref in self.seen:
            # maybe would be better to only do the deref if it's a parent
            return frozendict({'deref': str(ref)})
        else:
            self.seen.add(ref)
        
        vertex = self.graph[ref]
        if vertex == RUBY_TRUE: return True
        if vertex == RUBY_FALSE: return False
        if vertex == RUBY_NIL: return None
        if isinstance(vertex, (RubyFixnum, RubyBignum, RubyFloat)): return vertex.value
        
        if isinstance(vertex, (RubySymbol, RubyClassRef, RubyModuleRef, RubyClassOrModuleRef)):
            return vertex.decoded_name()
            
        assert isinstance(vertex, MarshalExtensibleVertex)
            
        res = {'ref': str(ref)}
        inst_vars = vertex.inst_vars
        module_ext = vertex.module_ext
                    
        if isinstance(vertex, RubyString):
            encoding, inst_vars = get_encoding_from_inst_vars(self.graph, ref)
            decode_args = ('utf-8', 'surrogateescape') if encoding is None else (encoding,)
            res |= {'type': 'string', 'value': vertex.value.decode(*decode_args)}
        elif isinstance(vertex, RubyRegex):
            encoding, inst_vars = get_encoding_from_inst_vars(self.graph, ref)
            decode_args = ('utf-8', 'surrogateescape') if encoding is None else (encoding,)

            res |= {
                'type': 'regex',
                'source': vertex.source.decode(*decode_args),
                'options': ''.join(self.REGEX_OPTIONS_TABLE[flag] for flag in vertex.options)
            }
        elif isinstance(vertex, MarshalArray):
            res |= {'type': 'array', 'items': tuple(self.format_at(ref) for ref in vertex.items)}
        elif isinstance(vertex, MarshalHash):
            res['items'] = frozendict({
                self.format_at(key_ref): self.format_at(value_ref)
                for key_ref, value_ref in vertex.items
            })
            
            if vertex.default is None:
                res['type'] = 'hash'
            else:
                res |= {'type': 'default_hash', 'default': self.format_at(vertex.default)}
        elif isinstance(vertex, MarshalRegObj):
            res |= {'type': 'object', 'class': self.format_at(vertex.cls)}
        elif isinstance(vertex, MarshalStruct):
            res |= {'type': 'struct', 'name': self.format_at(vertex.name), 'members': frozendict({
                self.format_at(key_ref): self.format_at(value_ref)
                for key_ref, value_ref in vertex.members
            })}
        elif isinstance(vertex, MarshalWrappedExtPtr):
            res |= {
                'type': 'data',
                'class': self.format_at(vertex.cls),
                'wraps': self.format_at(vertex.obj)
            }
        elif isinstance(vertex, MarshalUserBuiltin):
            res |= {
                'type': 'user_builtin',
                'class': self.format_at(vertex.cls),
                'wraps': self.format_at(vertex.obj)
            }
        elif isinstance(vertex, MarshalUserObject):
            res |= {
                'type': 'user_object',
                'class': self.format_at(vertex.cls),
                'wraps': self.format_at(vertex.obj)
            }
        elif isinstance(vertex, MarshalUserData):
            res |= {
                'type': 'user_data',
                'class': self.format_at(vertex.cls),
                'data': base64.b64encode(vertex.data).decode('us-ascii')
            }
            
        res['inst_vars'] = {}
            
        for key_ref, value_ref in inst_vars:
            key = self.format_at(key_ref)
            value = self.format_at(value_ref)            
            res['inst_vars'][key] = value
            
        res['inst_vars'] = frozendict(res['inst_vars'])
        res['module_ext'] = tuple(self.format_at(module_ref) for module_ref in module_ext)
        
        return frozendict(res)
        
###################################################################################################

def load(data: Sequence[int]) -> MarshalFile:
    return Loader(data).load()

def load_file(filename: str) -> MarshalFile:
    with open(filename, 'rb') as f:
        data = f.read()
        return load(data)

# why do all the prettyprinters suck. fine, i'll write my own
# this should be suitable for pasting into an online json viewing tool --- my favourite is
# http://jsonviewer.stack.hu/ although https://jsonformatter.curiousconcept.com/# is good for
# when it doesn't validate 
def dump_jsonish(data):
    LIMIT = 120
    
    def json_dumps(data):
        if data in (None, True, False) or isinstance(data, (int, float, str)):
            return json.dumps(data)

        # if data is None: return 'null'
        # if data is True: return 'true'
        # if data is False: return 'false'
        # if isinstance(data, (int, float)): return str(data)
        # if isinstance(data, str): return json.dumps(data)
        #     repr_ = repr(data)
        #     return f'"{repr_[1:-1]}"'
            
        if isinstance(data, (list, tuple)):
            itemreps = [json_dumps(item) for item in data]
            return '[' + ', '.join(itemreps) + ']'
            
        if isinstance(data, (dict, frozendict)):
            keyreps = [json_dumps(key) for key in data.keys()]
            valuereps = [json_dumps(value) for value in data.values()]
            pairreps = [f'{keyrep}: {valuerep}' for keyrep, valuerep in zip(keyreps, valuereps)]
            return '{' + ', '.join(pairreps) + '}'
            
        assert False
    
    #json_dumps = partial(json.dumps, default=dict) # convert frozendicts to dicts
    
    def dumplines(data, indent, prefix, suffix):
        res = []
        
        #if data is None: return [prefix + 'null' + suffix]
        #if data is True: return [prefix + 'true' + suffix]
        #if data is False: return [prefix + 'false' + suffix]
        #if isinstance(data, (int, float)): return [prefix + str(data) + suffix]
        #if isinstance(data, str): return [prefix + '"' + data + '"' + suffix]
        
        if data is None or isinstance(data, (bool, int, float, str)):
            #if isinstance(data, str):
                #data = data.encode('utf-8', 'surrogateescape')
                
            return [prefix + json_dumps(data) + suffix]
    
        if isinstance(data, (tuple, list)):
            oneline = prefix + json_dumps(data) + suffix
            if len(oneline) <= LIMIT: return [oneline]
            innerindent = indent + ' '
            innerlines = []
            
            for i, item in enumerate(data):
                innersuffix = ',' if i < len(data) - 1 else ''
                innerlines.extend(dumplines(item, innerindent, innerindent, innersuffix))
            
            return [prefix + '[', *innerlines, indent + ']' + suffix]
            
        if isinstance(data, (dict, frozendict)):
            oneline = prefix + json_dumps(data) + suffix
            if len(oneline) <= LIMIT: return [oneline]
            innerindent = indent + ' '
            innerlines = []
            
            for i, (key, value) in enumerate(data.items()):
                innersuffix = ',' if i < len(data) - 1 else ''
                
                key_oneline = innerindent + json_dumps(key) + ': '
                value_oneline = json_dumps(value) + innersuffix
                keyvalue_oneline = key_oneline + value_oneline

                if len(keyvalue_oneline) <= LIMIT:
                    # both key and value on one line
                    innerlines.append(keyvalue_oneline)
                    continue
                
                key_lines = dumplines(key, innerindent, innerindent, ': ' + value_oneline)
                value_lines = dumplines(value, innerindent, key_oneline, innersuffix)

                if len(value_lines[0]) <= LIMIT:
                    # key in one line, value on multiple lines
                    innerlines.extend(value_lines)
                    continue
                
                if len(key_lines[-1]) <= LIMIT:
                    # key in multiple lines, value on one line
                    innerlines.extend(key_lines)
                    continue
                    
                # both key and value on multiple lines
                key_lines = dumplines(key, innerindent, innerindent, ': ')
                value_lines = dumplines(value, innerindent, key_lines[-1], innersuffix)
                innerlines.extend(key_lines[:-1])
                innerlines.extend(value_lines)
                                                    
            return [prefix + '{', *innerlines, indent + '}' + suffix]
            
        raise ValueError(f'{data} is not jsonish enough')
            
    return '\n'.join(dumplines(data, '', '', ''))


if __name__ == '__main__':
    import doctest
    doctest.testmod()

    from pathlib import Path
    import json
    import pprint
    import sys
    
    path = Path(sys.argv[1])
    graph = load_file(str(path)).graph

    with open('marshal-output.txt', 'w', encoding='utf-8') as f:
        data = JsonishFormatter(graph).format()
        print(dump_jsonish(data), file=f)
