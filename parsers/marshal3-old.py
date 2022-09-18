from dataclasses import dataclass, make_dataclass
import math
import struct
from typing import Any, get_args, Iterable, Iterator, Optional, Sequence

# handy little ruby script for testing:
#
# data = <INSERTDATAHERE>
# marshalled = Marshal.dump(data)
# ords = marshalled.chars.map { |c| c.ord }
# hexs = ords.map { |o| o.to_s(16) }
# print marshalled, "\n"
# print ords, "\n"
# print hexs

def make_singleton_dataclass(name: str) -> tuple[type, Any]:
    cls = make_dataclass(name, ())
    return cls, cls()

(RubyTrue, RUBY_TRUE), (RubyFalse, RUBY_FALSE), (RubyNil, RUBY_NIL) = map(
    make_singleton_dataclass, ('RubyTrue', 'RubyFalse', 'RubyNil')
)

RubyFixnum, RubyBignum = (
    make_dataclass(cls, [('value', int)]) for cls in ('RubyFixnum', 'RubyBignum')
)

RubyFloat = make_dataclass('RubyFloat', [('value', float)])
RubyString = make_dataclass('RubyString', [('value', bytes)])
RubyRegex = make_dataclass('RubyRegex', [('source', bytes), ('options', int)])

RubySymbol, RubyClassRef, RubyModuleRef, RubyClassOrModuleRef = (
    make_dataclass(cls, [('name', bytes)])
    for cls in ('RubySymbol', 'RubyClassRef', 'RubyModuleRef', 'RubyClassOrModuleRef')
)

# In the Marshal format, symbols and most objects (other than true, false, nil and fixnums)
# appear in full only once in a file. Subsequent occurrences just reference the earlier
# occurrence via an index. There are separate sets of indices for symbols and objects, and the
# indices for symbols start at 0, but the indices for objects start at 1.
#
# To encode a Marshal object as a graph, we need a way to refer to vertices in the graph. It is
# convenient for debugging purposes to make these references match up with those used in the
# Marshal data (where possible; of course, for true, false, nil and fixnums the vertices are not
# referenced within the Marshal data). But it's also convenient to be able to encode a reference
# as a single value which will unambiguously refer to a given vertex, without us needing to
# separately pass around information about which type of object it refers to. The following union
# of dataclasses is intended to provide both of these conveniences at once.

MarshalSymbolRef, MarshalObjectRef, MarshalValueRef = (
    make_dataclass(
        cls, [('index', int)], namespace={'__str__': lambda self: code + str(self.index)}
    ) for cls, code in (
        ('MarshalSymbolRef', 'S'), ('MarshalObjectRef', 'O'), ('MarshalValueRef', 'V')
    ) 
)

MarshalRef = MarshalSymbolRef | MarshalObjectRef | MarshalValueRef

# We switch from naming the classes 'RubyX' to 'MarshalX' here because the subsequent classes
# involve MarshalRefs and hence aren't straightforwardly just encodings of Ruby objects; they
# have to be interpreted within the object graph of a Marshal file

MarshalArray = make_dataclass('MarshalArray', [('items', tuple[MarshalRef, ...])])

MarshalHash = make_dataclass('MarshalHash', [
    ('items', tuple[tuple[MarshalRef, MarshalRef], ...]), ('default', MarshalRef)
])

MarshalVarList = tuple[tuple[MarshalSymbolRef, MarshalRef], ...]

MarshalRegObj = make_dataclass('MarshalRegObj', [('cls', MarshalSymbolRef), ('inst_vars', MarshalVarList)])
MarshalStruct = make_dataclass('MarshalStruct', [('name', MarshalSymbolRef), ('members', MarshalVarList)])
MarshalInstVars = make_dataclass('MarshalInstVars', [('obj', MarshalRef), ('inst_vars', MarshalVarList)])

MarshalUserBuiltin, MarshalWrappedExtPtr, MarshalUserObject = (
    make_dataclass(cls, [('cls', MarshalSymbolRef), ('obj', MarshalRef)])
    for cls in ('MarshalUserBuiltin', 'MarshalWrappedExtPtr', 'MarshalUserObject')
)

MarshalModuleExt = make_dataclass('MarshalModuleExt', [
    ('obj', MarshalRef), ('module', MarshalSymbolRef)
])

MarshalUserData = make_dataclass('MarshalUserData', [('cls', MarshalSymbolRef), ('data', bytes)])

MarshalLacksRef = RubyTrue | RubyFalse | RubyNil | RubyFixnum

MarshalHasObjectRef = (
    RubyBignum | RubyFloat | RubyString | RubyRegex | RubyClassRef | RubyModuleRef
    | RubyClassOrModuleRef | MarshalArray | MarshalHash | MarshalRegObj | MarshalStruct
    | MarshalUserBuiltin | MarshalWrappedExtPtr | MarshalInstVars | MarshalModuleExt
    | MarshalUserData | MarshalUserObject
)

MarshalVertex = RubySymbol | MarshalLacksRef | MarshalHasObjectRef

def get_ref_type(vertex: MarshalVertex) -> type:
    if isinstance(vertex, RubySymbol):
        return MarshalSymbolRef
    elif isinstance(vertex, get_args(MarshalLacksRef)):
        return MarshalValueRef
    else:
        return MarshalObjectRef

@dataclass
class MarshalGraph:
    """A Marshal object, represented as a graph.

    Instances of this class can also represent a graph under construction."""

    # These three lists are used for mapping references to vertices. For graphs under construction,
    # a reference may map to None (if we know that a vertex with a certain reference will be in the
    # graph, but we don't know the exact contents of the vertex yet).
    symbols: list[Optional[RubySymbol]]
    objects: list[Optional[MarshalHasObjectRef]]
    values: list[Optional[MarshalLacksRef]]

    # This dictionary is used for mapping vertices to references.
    refs: dict[MarshalVertex, MarshalRef]

    def __init__(self):
        self.symbols = []
        self.objects = []
        self.values = []
        self.refs = {}

    def get_array_and_starting_index_for_ref_type(
        self, ref_type: type
    ) -> tuple[list[Optional[MarshalRef]], int]:
        return {
            MarshalSymbolRef: (self.symbols, 0),
            MarshalObjectRef: (self.objects, 1),
            MarshalValueRef: (self.values, 0),
        }[ref_type]

    def __getitem__(self, ref: MarshalRef) -> MarshalVertex:
        array, starting_index = self.get_array_and_starting_index_for_ref_type(type(ref))
        return array[ref.index - starting_index]

    def __setitem__(self, ref: MarshalRef, vertex: MarshalVertex) -> None:
        """Replace the vertex at the given reference with a new one."""
        ref_type = type(ref)
        new_ref_type = get_ref_type(vertex)

        if new_ref_type != ref_type:
            raise ValueError(f'vertex has wrong type for the given ref')

        array, starting_index = self.get_array_and_starting_index_for_ref_type(ref_type)
        index = ref.index - starting_index
        old_vertex = array[index]
        array[index] = vertex
        if old_vertex is not None: del self.refs[old_vertex]
        self.refs[vertex] = ref

    def add(self, vertex: Optional[MarshalVertex]) -> MarshalRef:
        """Add a vertex to the graph.

        The vertex may be None, in which case None is added as a placeholder under the next
        available reference of MarshalObjectRef type (it can be replaced with the actual vertex
        later on via a call to __setitem__)."""

        try:
            ref = self.refs[vertex]
        except KeyError:
            ref_type = MarshalObjectRef if vertex is None else get_ref_type(vertex)    
            array, starting_index = self.get_array_and_starting_index_for_ref_type(ref_type)
            index = len(array) + starting_index
            ref = ref_type(index)
            array.append(vertex)

            if vertex is not None:
                self.refs[vertex] = ref
        else:
            if not isinstance(vertex, MarshalLacksRef):
                raise ValueError(
                    "add() shouldn't need to be called on a vertex which is not of "
                    "MarshalLacksRef type more than once"
                )

        return ref

    def root(self) -> MarshalVertex:
        # Since any vertex of type MarshalSymbol or MarshalLacksRef lacks children, the only way
        # one of them can be the root is if it is the only vertex in the graph. Otherwise, we
        # assume that the root is the first vertex in `self.objects`.

        if self.objects:
            res = self.objects[0]
        else:
            if len(self.symbols) > 1 or len(self.values) > 1:
                raise ValueError('graph under construction, root cannot be determined')

            if self.symbols: res = self.symbols[0]
            elif self.values: res = self.values[0]
            else: raise ValueError('empty graph')

        if res is None:
            raise ValueError('graph under construction, root vertex is not yet fully constructed')

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

    def dump(self) -> Iterator[int]:
        yield from Dumper(self)

def load(data: Iterable[int]) -> MarshalFile:
    return Loader(data).load()

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
        raise ParseError(self.offset, message)

    def load(self) -> MarshalFile:
        major_version, minor_version = self.read_bytes(2)
        self.load_object()

        if self.done:
            return MarshalFile(major_version, minor_version, self.graph)

        self.error('parsing has finished but not all of the input was consumed')

    def read_byte(self) -> int:
        try:
            byte = self.data[self.offset]
        except StopIteration:
            self.error('incomplete input')
        else:
            self.offset += 1
            return byte

    def read_bytes(self, length: int) -> Iterator[int]:
        for _ in range(length):
            yield self.read_byte()

    def read_long(self) -> int:
        header = int.from_bytes([self.read_byte()], 'little', signed=True)
        if header == 0: return 0
        header_mag = abs(header)
        header_sign = header // header_mag
        if header_mag >= 5: return header_sign * (header_mag - 5)
        return int.from_bytes(self.read_bytes(header_mag), 'little', signed=True)

    def read_byte_seq(self) -> bytes:
        length = self.read_long()
        return bytes(self.read_bytes(length))

    def load_object(self) -> MarshalRef:
        type_code = chr(self.read_byte())
        return self.load_object_without_type_code()

    def load_symbol(self) -> MarshalSymbolRef:
        type_code = chr(self.read_byte())

        if type_code not in (';', ':'):
            self.error(f'expected to be loading a symbol, but the type code is "{type_code}"')

        return self.load_object_without_type_code()

    def load_hash_items(self, *, symbol_keys=False) -> tuple[tuple[MarshalRef, MarshalRef], ...]:
        length = self.read_long()
        items = []

        for _ in range(length):
            key_ref = self.load_symbol() if symbol_keys else self.load_object()
            value_ref = self.load_object()
            items.append((key_ref, value_ref))

        return tuple(items)

    def load_vars(self) -> tuple[tuple[MarshalSymbolRef, MarshalRef], ...]:
        return self.load_hash_items(symbol_keys=True)

    def load_object_without_type_code(self) -> MarshalRef:
        type_code = chr(self.read_byte())

        if type_code == ';':
            return MarshalSymbolRef(self.read_long())
        
        if type_code  == '@':
            return MarshalObjectRef(self.read_long())

        try: vertex = {'T': RUBY_TRUE, 'F': RUBY_FALSE, '0': RUBY_NIL}[type_code]
        except KeyError: pass
        else: return self.graph.add(vertex)

        if type_code == 'i':
            return self.graph.add(RubyFixnum(self.read_long()))

        if type_code == 'l':
            sign = {'+': 1, '-': -1}[chr(self.read_byte())]
            word_length = self.read_long()
            
            return self.graph.add(RubyBignum(int.from_bytes(
                self.read_bytes(word_length * 2), 'little', signed=True
            )))

        if type_code == 'f':
            bytes_ = self.read_byte_seq()

            try:
                value = {b'inf': math.inf, b'-inf': -math.inf, b'nan': math.nan}[bytes_]
            except KeyError:
                value, = struct.unpack('d', bytes_)

            return self.graph.add(RubyFloat(value))

        if type_code == '"':
            value = self.read_byte_seq()
            return self.graph.add(RubyString(value))

        if type_code == '/':
            source = self.read_byte_seq()
            options = self.read_byte()
            return self.graph.add(RubyRegex(source, options))

        try:
            vertex_type = {
                ':': RubySymbol, 'c': RubyClassRef, 'm': RubyModuleRef, 'M': RubyClassOrModuleRef
            }[type_code]
        except KeyError:
            pass
        else:
            name = self.read_byte_seq()
            return self.graph.add(vertex_type(name))

        ref = self.graph.add(None)

        if type_code == '[':
            length = self.read_long()
            items = tuple(self.load_object() for _ in range(length))
            self.graph[ref] = MarshalArray(items)
            return ref

        if type_code == '{':
            items = self.load_hash_items()
            self.graph[ref] = MarshalHash(items, None)
            return ref

        if type_code == '}':
            items = self.load_hash_items()
            default = self.load_object()
            self.graph[ref] = MarshalHash(items, default)
            return ref
        
        if type_code == 'o':
            cls_ref = self.load_symbol()
            inst_vars = self.load_vars()
            self.graph[ref] = MarshalRegObj(cls_ref, inst_vars)
            return ref
        
        if type_code == 'S':
            name_ref = self.load_symbol()
            members = self.load_vars()
            self.graph[ref] = MarshalStruct(name_ref, members)
            return ref

        if type_code == 'I':
            obj_ref = self.load_object()
            inst_vars = self.load_vars()
            self.graph[ref] = MarshalInstVars(obj_ref, inst_vars)
            return ref

        try:
            vertex_type = {
                'C': MarshalUserBuiltin, 'd': MarshalWrappedExtPtr, 'U': MarshalUserObject
            }[type_code]
        except KeyError:
            pass
        else:
            cls_ref = self.load_symbol()
            obj_ref = self.load_object()
            self.graph[ref] = vertex_type(cls_ref, obj_ref)
            return ref

        if type_code == 'e':
            obj_ref = self.load_object()
            module_ref = self.load_symbol()
            self.graph[ref] = MarshalModuleExt(obj_ref, module_ref)
            return ref

        if type_code == 'u':
            cls_ref = self.load_symbol()
            data = self.read_byte_seq()
            self.graph[ref] = MarshalUserData(cls_ref, data)
            return ref

        self.error(f'invalid type code "{type_code}"')

###################################################################################################
# Dump
###################################################################################################

def dump_long(value: int) -> Iterator[int]:
    # https://docs.ruby-lang.org/en/master/marshal_rdoc.html
    # "There are multiple representations for many values. CRuby always outputs the
    # shortest representation possible."
    # 
    # This doesn't say anything about other implementations, and other implementations
    # exist. So doing a load and dump may in theory not preserve the exact representation for
    # other implementations.
    if value == 0:
        yield 0
    elif 0 < value < 123:
        yield value + 5
    elif -123 <= value < 0:
        yield 251 + value
    else:
        byte_length = (value.bit_length() + 7) // 8
        assert byte_length <= 4
        yield 256 - byte_length if value < 0 else byte_length
        yield from value.to_bytes(byte_length, 'little', signed=True)

def dump_byte_seq(seq: bytes) -> Iterator[int]:
    yield from dump_long(len(seq))
    yield from seq

class Dumper:
    file: MarshalFile
    visited: set[int]

    # these only exist for testing --- we want to make sure the reference numbers are preserved
    symbol_ids: list[int]
    object_ids: list[int]

    def __init__(self, file: MarshalFile) -> None:
        self.file = file
        self.visited = set()
        self.symbol_ids = []
        self.object_ids = []

    def __iter__(self):
        yield self.file.major_version
        yield self.file.minor_version
        yield from self.visit(0)

    def visit(self, vertex_id: int, *, assert_is_symbol=False) -> Iterator[int]:
        vertex = self.file.graph[vertex_id]

        try: yield ord({RubyTrue: 'T', RubyFalse: 'F', RubyNil: '0'}[vertex])
        except KeyError: pass
        else: return

        if isinstance(vertex, RubyFixnum):
            yield ord('i')
            yield from dump_long(vertex.value)
            return

        is_symbol = isinstance(vertex, RubySymbol)
        if assert_is_symbol: assert is_symbol

        if vertex_id in self.visited:
            yield ord(';') if is_symbol else ord('@')
            yield from dump_long(vertex.marshal_ref)
            return

        self.visited.add(vertex_id)
        assert vertex.marshal_ref == (len(self.symbol_ids) if is_symbol else len(self.object_ids) + 1)

        if isinstance(vertex, RubyBignum):
            yield ord('l')
            value = vertex.value
            yield ord('+' if value >= 0 else '-')
            word_length = (value.bit_length() + 15) // 16
            yield from dump_long(word_length)
            yield from value.to_bytes(word_length * 2, 'little', signed=True)
            return

        if isinstance(vertex, RubyFloat):
            yield ord('f')
            value = vertex.value
            ba = bytearray()

            if math.isnan(value):
                ba += b'nan'
            elif math.isinf(value):
                if value < 0: ba += ord('-')
                ba += b'inf'
            else:
                # this could also not be preserved by load/dump
                ba += struct.pack('d', value)

            yield from dump_byte_seq(ba)
            return

        if isinstance(vertex, RubyString):
            yield ord('"')
            yield from dump_byte_seq(vertex.value)
            return

        if isinstance(vertex, RubyRegex):
            yield ord('/')
            yield from dump_byte_seq(vertex.source)
            yield vertex.options
            return

        if isinstance(vertex, RubySymbol):
            yield ord(':')
            yield from dump_byte_seq(vertex.name)
            return

        if isinstance(vertex, RubyClassRef):
            yield ord('c')
            yield from dump_byte_seq(vertex.name)
            return

        if isinstance(vertex, RubyModuleRef):
            yield ord('m')
            yield from dump_byte_seq(vertex.name)
            return

        if isinstance(vertex, RubyClassOrModuleRef):
            yield ord('M')
            yield from dump_byte_seq(vertex.name)
            return

        if isinstance(vertex, MarshalArray):
            yield ord('[')
            items = vertex.items
            yield from dump_long(len(items))
            for item in vertex: yield from self.visit(item)
            return

        if isinstance(vertex, MarshalHash):
            yield ord('{')
            items = vertex.items
            yield from dump_long(len(items))

            for key, value in vertex.items:
                yield from self.visit(key)
                yield from self.visit(value)

            default = vertex.default

            if default is not None:
                yield from self.visit(default)

            return

        if isinstance(vertex, MarshalRegObj):
            yield ord('o')
            yield from self.visit(vertex.cls, assert_is_symbol=True)
            yield from dump_long(len(vertex.inst_vars))

            for name, value in vertex.inst_vars:
                yield from self.visit_symbol(name)
                yield from self.visit(value)

            return

        if isinstance(vertex, MarshalStruct):
            yield ord('S')
            yield from self.visit(vertex.cls, assert_is_symbol=True)
            yield from dump_long(len(vertex.inst_vars))

            for name, value in vertex.inst_vars:
                yield from self.visit(name, assert_is_symbol=True)
                yield from self.visit(value)

            return

        if isinstance(vertex, MarshalUserBuiltin):
            yield ord('C')
            yield from self.visit(vertex.cls, assert_is_symbol=True)
            yield from self.visit(vertex.obj)
            return

        if isinstance(vertex, MarshalWrappedExtPtr):
            yield ord('d')
            yield from self.visit(vertex.cls, assert_is_symbol=True)
            yield from self.visit(vertex.obj)
            return

        if isinstance(vertex, MarshalInstVars):
            yield ord('I')
            yield from self.visit(vertex.obj)
            yield from dump_long(len(vertex.inst_vars))

            for name, value in vertex.inst_vars:
                yield from self.visit(name, assert_is_symbol=True)
                yield from self.visit(value)

            return

        if isinstance(vertex, MarshalModuleExt):
            yield ord('e')
            yield from self.visit(vertex.obj)
            yield from self.visit(vertex.module, assert_is_symbol=True)
            return

        if isinstance(vertex, MarshalUserData):
            yield ord('u')
            yield from self.visit(vertex.cls, assert_is_symbol=True)
            yield from self.visit_byte_seq(vertex.data)
            return

        if isinstance(vertex, MarshalUserObject):
            yield ord('U')
            yield from self.visit(vertex.cls, assert_is_symbol=True)
            yield from self.visit(vertex.obj)
            return

###################################################################################################

def load_file(filename: str) -> MarshalFile:
    with open(filename, 'rb') as f:
        data = f.read()
        return load(data)

if __name__ == '__main__':
    from pathlib import Path
    import sys
    path = Path(sys.argv[1])
    print(load_file(str(path)))

