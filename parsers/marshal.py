# https://docs.ruby-lang.org/en/master/marshal_rdoc.html

import ctypes
from collections import defaultdict
from dataclasses import dataclass, make_dataclass
from frozendict import frozendict
import itertools as it
import struct
from typing import Any, Iterable, Iterator, Optional, TextIO, Type
import dcformat

class frozendefaultdict(frozendict):
    def __init__(self, default_factory=None, *args, **kwargs):
    	super().__init__(self, *args, **kwargs)
    	self.default_factory = default_factory

    def __missing__(self, key):
        return self.default_factory()

DEBUG = False
DEBUG_LOGFILE = 'marshal-log.txt'

class MarshalObject: pass

def make_marshal_object_subclass(name: str, *fields: Iterable[tuple[str, Type]], **kwargs) -> Type:
	if not 'frozen' in kwargs: kwargs['frozen'] = True
	return make_dataclass(name, fields, bases=(MarshalObject,), **kwargs)

def make_marshal_object_singleton(name: str) -> Type:
	cls = make_marshal_object_subclass(name)
	return cls, cls()

MarshalTrue, MARSHAL_TRUE = make_marshal_object_singleton('MarshalTrue')
MarshalFalse, MARSHAL_FALSE = make_marshal_object_singleton('MarshalFalse')
MarshalNil, MARSHAL_NIL = make_marshal_object_singleton('MarshalNil')
MarshalFixnum = make_marshal_object_subclass('MarshalFixnum', ('val', int))
MarshalBignum = make_marshal_object_subclass('MarshalBignum', ('val', int))
MarshalFloat = make_marshal_object_subclass('MarshalFloat', ('val', float))
MarshalSymbol = make_marshal_object_subclass('MarshalSymbol', ('name', bytes))
MarshalClassRef = make_marshal_object_subclass('MarshalClassRef', ('name', bytes))
MarshalModuleRef = make_marshal_object_subclass('MarshalModuleRef', ('name', bytes))
MarshalClassOrModuleRef = make_marshal_object_subclass('MarshalClassOrModuleRef', ('name', bytes))
MarshalRegex = make_marshal_object_subclass('MarshalRegex', ('src', bytes), ('opts', int))
MarshalString = make_marshal_object_subclass('MarshalString', ('content', bytes))
MarshalArray = make_marshal_object_subclass('MarshalArray', ('items', tuple[MarshalObject, ...]))

MarshalHash = make_marshal_object_subclass('MarshalHash',
	('mapping', frozendict[MarshalObject, MarshalObject]), ('default', MarshalObject),
	namespace={'default': None}
)

MarshalWithInstVars = make_marshal_object_subclass('MarshalWithInstVars',
	('obj', MarshalObject), ('vars', frozendict[MarshalSymbol, MarshalObject])
)

MarshalModuleExtended = make_marshal_object_subclass('MarshalModuleExtended',
	('obj', MarshalObject), ('module', MarshalSymbol)
)

MarshalExtensionObject = make_marshal_object_subclass('MarshalExtensionObject',
	('cls', MarshalSymbol), ('state', MarshalObject)
)

MarshalClassInst = make_marshal_object_subclass('MarshalClassInst',
	('cls', MarshalSymbol), ('vars', frozendict[MarshalSymbol, MarshalObject])
)

MarshalStruct = make_marshal_object_subclass('MarshalStruct',
	('name', MarshalSymbol), ('vars', frozendict[MarshalSymbol, MarshalObject])
)

MarshalSubclassedBuiltin = make_marshal_object_subclass('MarshalSubclassedBuiltin',
	('cls', MarshalSymbol), ('obj', MarshalObject)
)

MarshalUserBytes = make_marshal_object_subclass('MarshalUserBytes',
	('cls', MarshalSymbol), ('bytes', bytes)
)

MarshalUserObject = make_marshal_object_subclass('MarshalUserObject',
	('cls', MarshalSymbol), ('obj', MarshalObject)
)

def parse_uint_le(s: Iterable[int]) -> int:
	"""Parse an iterable of bytes as an unsigned little-endian integer."""
	val = 0

	for i, digit in enumerate(s):
		val += digit * 0x100 ** i

	return val

class MarshalParseError(Exception):
	def __init__(self, offset, message):
		super().__init__(f'offset {hex(offset)}: {message}')

class MarshalParser:
	FIXNUM_SPECIAL_HEADERS: dict[tuple[int, int]] = {
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

	BIGNUM_SIGNS: dict[int, int] = {ord('+'): 1, ord('-'): -1}
	SPECIAL_FLOATS: tuple[str, ...] = ('inf', '-inf', 'nan')

	byte_length: int
	index: int
	major_version: int
	minor_version: int
	iterator: Iterator[int]
	symbols: list[MarshalSymbol]
	objects: list[MarshalObject]
	debug_log: Optional[TextIO]

	def __init__(self, bytes_: bytes):
		if len(bytes_) < 2:
			raise MarshalParseError(0, 
				f'expected a 2-byte version info header but there are only {len(bytes)} in the '
				'data'
			)
		
		self.byte_length = len(bytes_)
		self.index = 2
		self.major_version, self.minor_version = bytes_[:self.index]
		self.iterator = iter(bytes_[self.index:])
		self.symbols = []
		self.objects = []
		self.debug_log = open(DEBUG_LOGFILE, 'w') if DEBUG else None
		self.indent = 0

	def __next__(self) -> int:
		res = next(self.iterator)
		self.index += 1
		return res

	def __iter__(self) -> 'MarshalParser':
		return self

	def rem_len(self) -> int:
		return self.byte_length - self.index

	def error(self, message: str) -> None:
		raise MarshalParseError(self.index, message)

	def debug(self, message: str) -> None:
		if DEBUG:
			print((' ' * self.indent) + f'offset {hex(self.index)}: {message}', file=self.debug_log)

	# "Each object in the stream is described by a byte indicating its type followed by one or more
	# bytes describing the object."
	# --- seems it should say "zero or more"
	def parse_true(self) -> MarshalTrue:
		self.debug('parsing true')
		return MARSHAL_TRUE

	def parse_false(self) -> MarshalFalse:
		self.debug('parsing false')
		return MARSHAL_FALSE

	def parse_nil(self) -> MarshalNil:
		self.debug('parsing nil')
		return MARSHAL_NIL

	def parse_fixnum(self) -> MarshalFixnum:
		self.debug('parsing fixnum')
		header = next(self)

		if header in MarshalParser.FIXNUM_SPECIAL_HEADERS:
			length, sign = MarshalParser.FIXNUM_SPECIAL_HEADERS[header]

			if self.rem_len() < length:
				self.error(
					f'remaining data length in bytes is {self.rem_len()}, but having encountered a'
					f' fixnum with header {header} this should be at least {length}'
				)

			res = parse_uint_le(it.islice(self, length))
		else:
			# "Otherwise the first byte is a sign-extended eight-bit value with an offset. If the value
			# is positive the value is determined by subtracting 5 from the value. If the value is
			# negative the value is determined by adding 5 to the value."
			# --- bit unsure what this means
			neg = header & 0x80 # first bit
			res = header + (5 if neg else -5)

		self.debug(f'parsed fixnum: {res}')
		return MarshalFixnum(res)

	def parse_byte_seq(self) -> bytes:
		self.debug('parsing byte sequence')
		length = self.parse_fixnum().val

		if self.rem_len() < length:
			self.error(
				f'remaining data length in bytes is {self.rem_len()}, but a byte sequence of '
				'length {length} is expected'
			)

		res = bytes(it.islice(self, length))
		self.debug(f'parsed bytes: {res}')
		return res

	def parse_symbol(self) -> MarshalSymbol:
		self.debug('parsing symbol')
		# OK, the documentation was a bit confusing for me here
		# but it makes sense now: the length is encoded as a fixnum (so if it's one byte, you have to
		# add/subtract five---so 0xa corresponds to 5, the length of "hello")
		name = self.parse_byte_seq()
		res = MarshalSymbol(name)
		self.symbols.append(res)
		return res

	def parse_symbol_ref(self) -> MarshalSymbol:
		self.debug('parsing symbol reference')
		index = self.parse_fixnum().val

		try:
			return self.symbols[index]
		except IndexError:
			self.error(
				f'reference to symbol at index {index}, but only {len(self.symbols)} have been '
				'encountered so far'
			)

	def parse_object_ref(self) -> MarshalObject:
		self.debug('parsing object reference')
		index = self.parse_fixnum().val - 2 # 1-indexed... not sure why we have to minus by 2... but it works

		try:
			return self.objects[index]
		except IndexError:
			self.error(
				f'reference to object at index {index}, but only {len(self.objects)} have been '
				'encountered so far'
			)

	def add_object(self, obj: MarshalObject) -> MarshalObject:
		self.objects.append(obj)
		return obj

	def parse_symbol_with_header(self) -> MarshalSymbol:
		try:
			header = next(self)
		except StopIteration:
			self.error('expected a symbol, but there are no bytes left in the data')

		if header == ord(':'):
			return self.parse_symbol() 
		elif header == ord(';'):
			return self.parse_symbol_ref()

		self.error('expected a symbol or symbol reference')

	def parse_vars(self) -> frozendict[MarshalSymbol, MarshalObject]:
		length = self.parse_fixnum().val
		res = {}

		for _ in range(length):
			# documentation doesn't make it clear but the leading : is included with the symbol
			name = self.parse_symbol_with_header()
			val = self.parse_object()
			res[name] = val

		return frozendict(res)

	def parse_inst_vars(self) -> MarshalWithInstVars:
		self.debug('parsing object with instance variables')
		self.indent += 1
		obj = self.parse_object()
		inst_vars = self.parse_vars()
		self.indent -= 1
		return self.add_object(MarshalWithInstVars(obj, inst_vars))

	def parse_mod_ext(self) -> MarshalModuleExtended:
		self.debug('parsing object extended by module')
		self.indent += 1
		obj = self.parse_object()
		mod = self.parse_symbol_with_header()
		self.indent -= 1
		return self.add_object(ruby.MarshalModuleExtended(obj, mod))

	def parse_array(self) -> MarshalArray:
		self.debug('parsing array')
		self.indent += 1
		length = self.parse_fixnum().val
		items = tuple(self.parse_object() for _ in range(length))
		self.indent -= 1
		return self.add_object(MarshalArray(items))

	def parse_bignum(self) -> MarshalBignum:
		self.debug('parsing bignum')

		try:
			sign = MarshalParser.BIGNUM_SIGNS[next(self)]
		except StopIteration:
			self.error('expected sign byte for bignum, but there are no bytes left in the data')
		except KeyError:
			self.error('expected sign byte for bignum')

		length = self.parse_fixnum().val * 2

		if self.rem_len() < length:
			self.error(
				f'remaining data length in bytes is {self.rem_len()}, but a bignum of length '
				f'{length} is expected'
			)

		res = MarshalBignum(parse_uint_le(it.islice(self, length)))
		return self.add_object(res)

	def parse_class(self) -> MarshalClassRef:
		self.debug('parsing class ref')
		return self.add_object(MarshalClassRef(self.parse_byte_seq()))
	
	def parse_mod(self) -> MarshalModuleRef:
		self.debug('parsing module ref')
		return self.add_object(MarshalModuleRef(self.parse_byte_seq()))
	
	def parse_class_or_mod(self) -> MarshalClassOrModuleRef:
		self.debug('parsing class or module ref')
		return self.add_object(MarshalClassOrModuleRef(self.parse_byte_seq()))

	def parse_data(self) -> MarshalExtensionObject:
		self.debug('parsing data')
		self.indent += 1
		class_ = self.parse_symbol_with_header()
		state = self.parse_object()
		self.indent -= 1
		return self.add_object(MarshalExtensionObject(class_, state))

	def parse_float(self) -> MarshalFloat:
		self.debug('parsing float')
		bytes_ = self.parse_byte_seq()

		for val in MarshalParser.SPECIAL_FLOATS:
			if bytes_ == val.encode('ascii'):
				res = float(val)
				break
		else:
			# length = ctypes.sizeof(ctypes.c_double)
			# print('FLOAT LENGTH:', length)

			# if self.rem_len() < length:
			# 	self.error(
			# 		f'remaining data length in bytes is {self.rem_len()}, but a float of length '
			# 		f'{length} is expected'
			# 	)

			res, = struct.unpack('d', bytes_) # bytes(it.islice(self, length)))
			print(res)

		return self.add_object(MarshalFloat(res))

	def parse_hash(self, *, has_default: bool=False) -> MarshalHash:
		self.debug(f'parsing hash (has_default={has_default})')
		self.indent += 1
		length = self.parse_fixnum().val * 2
		# I assume it's key-val-key-val rather than key-key-val-val but the docs don't specify
		pairs = []

		for i in range(length):
			if i % 2:
				pairs[-1] = (pairs[-1][0], self.parse_object())
			else:
				pairs.append((self.parse_object(),))

		mapping = frozendict(pairs)
		default = self.parse_object() if has_default else None # I assume it's just another object
		res = MarshalHash(mapping, default)
		self.indent -= 1
		return self.add_object(res)

	def parse_default_hash(self) -> MarshalHash:
		return self.parse_hash(has_default=True)

	# There's a section for "Module and Old Module" but it's blank...?

	def parse_other_object(self) -> MarshalClassInst:
		self.debug('parsing normal object')
		self.indent += 1
		class_ = self.parse_symbol_with_header()
		inst_vars = self.parse_vars()
		self.indent -= 1
		return self.add_object(MarshalClassInst(class_, inst_vars))

	def parse_regex(self) -> MarshalRegex:
		self.debug('parsing regex')

		# "Following the type byte is a byte sequence containing the regular expression source.
		# Following the type byte is a byte containing the regular expression options (case-
		# insensitive, etc.) as a signed 8-bit value."
		# --- ??? I'm going to assume the options follow the source, that'd make sense.
		src = self.parse_byte_seq()

		try:
			opts = next(self)
		except StopIteration:
			self.error('expected a regex options byte, but there are no bytes left in the data')

		return self.add_object(MarshalRegex(src, opts))

	def parse_string(self) -> MarshalString:
		self.debug('parsing string')
		return self.add_object(MarshalString(self.parse_byte_seq()))

	def parse_struct(self) -> MarshalStruct:
		self.debug('parsing struct')
		self.indent += 1
		name = self.parse_symbol_with_header()
		struct_vars = self.parse_vars()
		self.indent -= 1
		return self.add_object(MarshalStruct(name, struct_vars))

	def parse_user_class(self) -> MarshalSubclassedBuiltin:
		self.debug('parsing user class')
		self.indent += 1
		subclass = self.parse_symbol_with_header()
		obj = self.parse_object()
		self.indent -= 1
		return self.add_object(MarshalSubclassedBuiltin(subclass, obj))

	def parse_user_bytes(self) -> MarshalUserBytes:
		self.debug('parsing user bytes')
		self.indent += 1
		class_ = self.parse_symbol_with_header()
		bytes_ = self.parse_byte_seq()
		self.indent -= 1
		return self.add_object(MarshalUserBytes(class_, bytes_))

	def parse_user_obj(self) -> MarshalUserObject:
		self.debug('parsing user object')
		self.indent += 1
		class_ = self.parse_symbol_with_header()
		obj = self.parse_object()
		self.indent -= 1
		return self.add_object(MarshalUserObject(class_, obj))

	TYPES = {
		ord('T'): 'true',
		ord('F'): 'false',
		ord('0'): 'nil',
		ord('i'): 'fixnum',
		ord(':'): 'symbol',
		ord(';'): 'symbol_ref',
		ord('@'): 'object_ref',
		ord('I'): 'inst_vars',
		ord('e'): 'mod_ext',
		ord('['): 'array',
		# 'I' (for inst vars) and 'l' (for bignum) look totally identical in the font Ruby is using for
		# its docs...
		ord('l'): 'bignum', 
		ord('c'): 'class',
		ord('m'): 'mod',
		ord('M'): 'class_or_mod',
		ord('d'): 'data',
		ord('f'): 'float',
		ord('{'): 'hash',
		ord('}'): 'default_hash',
		ord('o'): 'other_object',
		ord('/'): 'regex',
		ord('"'): 'string', # the docs have autocorrected it to “ --- but presumably they mean "
		ord('S'): 'struct',
		ord('C'): 'user_class',
		ord('u'): 'user_bytes',
		ord('U'): 'user_obj'
	}

	def parse_object(self):
		self.debug('parsing object')

		try:
			header = next(self)
		except StopIteration:
			self.error('expected an object, but there are no bytes left in the data')

		try:
			type_ = MarshalParser.TYPES[header]
		except KeyError:
			self.error(f'unrecognized type header: {hex(header)} (as char: {chr(header)})')

		return getattr(self, f'parse_{type_}')()

	def parse(self):
		res = self.parse_object()

		if self.index != self.byte_length:
			print(f'warning - unparsed data - only got to {hex(self.index)}')
			#raise MarshalParseError(self.index, 'unparsed data')

		# res = []

		# while self.index < self.byte_length:
		# 	res.append(self.parse_object())

		self.debug('finished parsing')
		return res


# No idea where to find this info in the docs, but
# http://jakegoulding.com/blog/2013/01/16/another-dip-into-rubys-marshal-format/
# says that true is UTF-8, false is US-ASCII, any other encoding is given as a raw string

RUBY_ENCODING_TO_PYTHON = {
	MARSHAL_TRUE: 'utf-8',
	MARSHAL_FALSE: 'us-ascii'
	# will have to fill in others later, as needed.
}

MarshalDecodedSymbol = make_marshal_object_subclass('MarshalDecodedSymbol', ('name', str))
MarshalDecodedClassRef = make_marshal_object_subclass('MarshalDecodedClassRef', ('name', str))
MarshalDecodedModuleRef = make_marshal_object_subclass('MarshalDecodedModuleRef', ('name', str))
MarshalDecodedClassOrModuleRef = make_marshal_object_subclass('MarshalDecodedClassOrModuleRef', ('name', str))

MarshalDecodedString = make_marshal_object_subclass('MarshalDecodedString', ('content', str))

MarshalDecodedRegex = make_marshal_object_subclass('MarshalDecodedRegex',
	('src', str), ('opts', int)
)

SYMBOL_SUBCLASS_TO_DECODED = {
	MarshalSymbol: MarshalDecodedSymbol,
	MarshalClassRef: MarshalDecodedClassRef,
	MarshalModuleRef: MarshalDecodedModuleRef,
	MarshalClassOrModuleRef: MarshalDecodedClassOrModuleRef
}

ASSUMING_UTF8 = True # can't be bothered doing this properly

def decode(obj: MarshalObject, encoding: Optional[str]=None) -> MarshalObject:
	if obj in (MARSHAL_TRUE, MARSHAL_FALSE, MARSHAL_NIL):
		return obj

	if isinstance(obj, (MarshalFixnum, MarshalBignum, MarshalFloat)):
		return obj

	if isinstance(obj,
		(MarshalSymbol, MarshalClassRef, MarshalModuleRef, MarshalClassOrModuleRef)
	):
		# The docs don't say anything about the encoding of symbols, but according to this blogpost:
		# http://jakegoulding.com/blog/2013/01/15/a-little-dip-into-rubys-marshal-format/
		# they are encoded as UTF-8. I assume classes and modules work the same way.
		return SYMBOL_SUBCLASS_TO_DECODED[type(obj)](obj.name.decode('utf-8'))

	match obj:
		case MarshalRegex(src, opts):
			return (
				(
					MarshalDecodedRegex(src.decode('utf-8'), opts)
					if ASSUMING_UTF8
					else MarshalRegex(src, opts)
				) if encoding is None
				else MarshalDecodedRegex(src.decode(encoding), opts)
			)
		case MarshalString(content):
			return (
				(
					MarshalDecodedString(content.decode('utf-8'))
					if ASSUMING_UTF8
					else MarshalString(content) 
				) if encoding is None
				else MarshalDecodedString(content.decode(encoding))
			)
		case MarshalArray(items):
			return MarshalArray(tuple(map(decode, items)))
		case MarshalHash(mapping, default):
			return MarshalHash(
				frozendict((decode(key), decode(val)) for key, val in mapping.items()),
				(None if default is None else decode(default))
			)
		case MarshalWithInstVars(obj, vars_):
			vars_ = {decode(name): decode(val) for name, val in vars_.items()}
			ruby_encoding = vars_.pop(MarshalDecodedSymbol('E'), None)
			vars_ = frozendict(vars_)

			if ruby_encoding is not None:
				encoding = RUBY_ENCODING_TO_PYTHON[ruby_encoding]
			else:
				encoding = None

			obj = decode(obj, encoding)			
			return MarshalWithInstVars(obj, vars_) if vars_ else obj
		case MarshalModuleExtended(obj, module):
			return MarshalModuleExtended(decode(obj), decode(module))
		case MarshalExtensionObject(class_, state):
			return MarshalExtensionObject(decode(class_), decode(state))
		case MarshalClassInst(class_, vars_):
			return MarshalClassInst(
				decode(class_),
				frozendict((decode(key), decode(val)) for key, val in vars_.items())
			)
		case MarshalStruct(name, vars_):
			return MarshalStruct(
				decode(name),
				frozendict((decode(key), decode(val)) for key, val in vars_.items())
			)
		case MarshalSubclassedBuiltin(class_, obj):
			return MarshalSubclassedBuiltin(decode(class_), decode(obj))
		case MarshalUserBytes(class_, bytes_):
			return MarshalUserBytes(decode(class_), bytes_)
		case MarshalUserObject(class_, obj):
			return MarshalUserObject(decode(class_), decode(obj))

	raise ValueError(f'unrecognized marshal object type: {type(obj)}')

SINGLETON_TO_PYTHON = {MARSHAL_TRUE: True, MARSHAL_FALSE: False, MARSHAL_NIL: None}

class PythonifiedMarshalObject: pass

@dataclass
class PythonifiedMarshalObjectWrapper(PythonifiedMarshalObject):
	wrapped: Any

def setattrs(obj: Any, vars_: dict[str, Any]) -> None:
	for name, val in vars_.items():
		setattr(obj, name, val)

def force_setattrs(obj: Any, vars_: dict[str, Any]) -> Any:
	try:
		setattrs(obj, vars_)
	except AttributeError:
		obj = PythonifiedMarshalObjectWrapper(obj)
		setattrs(obj, vars_)

	return obj

def pythonify(obj: MarshalObject) -> Any:
	try:
		if obj in SINGLETON_TO_PYTHON:
			return SINGLETON_TO_PYTHON[obj]
	except TypeError:
		breakpoint()

	if isinstance(obj, (
		MarshalClassRef, MarshalModuleRef, MarshalClassOrModuleRef,
		MarshalDecodedClassRef, MarshalDecodedModuleRef, MarshalDecodedClassOrModuleRef
	)):
		return obj

	extension_object_classes = {}
	classes = {}
	builtin_subclasses = {}
	user_bytes_classes = {}
	user_object_classes = {}

	match obj:
		case (
			MarshalFixnum(val) | MarshalBignum(val) | MarshalFloat(val)
			| MarshalSymbol(val) | MarshalString(val)
			| MarshalDecodedSymbol(val) | MarshalDecodedString(val) 
		):
			return val
		case MarshalRegex(src, opts):
			return obj
		case MarshalArray(items):
			return tuple(map(pythonify, items))
		case MarshalHash(mapping, default):
			pairs = tuple((pythonify(key), pythonify(val)) for key, val in mapping.items())
			
			return (
				frozendict(pairs) if default is None
				else defaultdict(pairs, lambda: default)
			)
		case MarshalWithInstVars(obj, vars_):
			obj = pythonify(obj)
			vars_ = frozendict((pythonify(name), pythonify(val)) for name, val in vars_.items())

			# if None in vars_: # idk
			# 	d = dict(vars_)
			# 	d['<None>'] = d[None]
			# 	del d[None]
			# 	vars_ = frozendict(d)

			return force_setattrs(obj, vars_)
		case MarshalModuleExtended(obj, module):
			module = pythonify(module)
			obj = pythonify(obj)
			
			return force_setattrs(obj,
				{'marshal_extends': getattr(obj, 'marshal_extends', []) + [module]}
			)
		case MarshalExtensionObject(class_, state):
			class_ = pythonify(class_)

			if class_ not in extension_object_classes:
				classes[class_] = make_dataclass(
					class_, [('state', Any)],
					bases=(PythonifiedMarshalObject,)
				)

			class_obj = classes[class_]
			return class_obj(pythonify(state))
		case MarshalClassInst(class_, vars_):
			class_ = pythonify(class_)

			if class_ not in classes:
				classes[class_] = type(class_, (PythonifiedMarshalObject,), {})

			class_obj = classes[class_]
			res = class_obj()
			res.__dict__.update({pythonify(key): pythonify(val) for key, val in vars_.items()})
			return res
		case MarshalStruct(name, vars_):
			class_ = pythonify(name)

			if class_ not in classes:
				classes[class_] = type(class_, (PythonifiedMarshalObject,), {})

			class_obj = classes[class_]
			res = class_obj()
			res.__dict__.update({pythonify(key): pythonify(val) for key, val in vars_.items})
			return res
		case MarshalSubclassedBuiltin(class_, obj):
			class_ = pythonify(class_)
			obj = pythonify(obj) # will either be a string, regex, array or hash

			if class_ not in builtin_subclasses:
				builtin_subclasses[class_] = type(class_, (type(obj),), {})

			class_obj = builtin_subclasses[class_]

			return (
				class_obj(obj.src, obj.opts) if isinstance(obj, MarshalRegex)
				else class_obj(obj)
			)
		case MarshalUserBytes(class_, bytes_):
			class_old = class_
			class_ = pythonify(class_)

			# if isinstance(class_, bytes):
			# 	print(class_old)

			# if class_ is None: # this can happen apparently
			# 	return pythonify(bytes_)

			if class_ not in user_bytes_classes:
				user_bytes_classes[class_] = make_dataclass(
					class_, [('data', bytes)],
					bases=(PythonifiedMarshalObject,)
				)

			class_obj = user_bytes_classes[class_]
			return class_obj(bytes_)
		case MarshalUserObject(class_, obj):
			class_ = pythonify(class_)

			if class_ not in user_object_classes:
				user_object_classes[class_] = make_dataclass(
					class_, [('data', Any)],
					bases=(PythonifiedMarshalObject,)
				)

			class_obj = user_object_classes[class_]
			return class_obj(pythonify(obj))
	
	raise ValueError(f'unrecognized marshal object type: {type(obj)}')

def postpythonify(obj):
	if hasattr(obj, '__class__'):
		if obj.__class__.__name__ in (
			'RPG::Map',
			'RPG::AudioFile',
			'RPG::Event',
			'RPG::Event::Page',
			'RPG::Event::Page::Condition',
			'RPG::Event::Page::Graphic',
			'RPG::MoveRoute',
			'RPG::EventCommand',
			'RPG::MoveCommand',
			'RPG::Tileset',
			'RPG::MapInfo',
			'RPG::CommonEvent',
			'PBFieldNote',
			'RPG::Item',
			'RPG::System',
			'RPG::System::Words',
			'RPG::System::TestBattler',
			'PokeBattle_Trainer',
			'PokeBattle_Pokemon',
			'PBMove'
		):
			return postpythonify({'__class_name__': obj.__class__.__name__, **obj.__dict__})

	if isinstance(obj, (dict, defaultdict)):
		old_keys = list(obj.keys())
		new_keys = {}

		for key in old_keys:
			new_keys[str(key)] = postpythonify(obj[key])
			del obj[key]

		obj.update(new_keys)
		return obj
	elif isinstance(obj, frozendict):
		return {str(key): postpythonify(value) for key, value in obj.items()}
	elif isinstance(obj, tuple):
		return tuple(postpythonify(item) for item in obj)
	else:
		return obj

def parse(bytes_, transform=None):
	parser = MarshalParser(bytes_)
	res = parser.parse()

	if transform == 'decode':
		res = decode(res)
	elif transform == 'pythonify':
		res = pythonify(decode(res))

	return res

def stringify(obj):
	return dcformat.stringify(obj)

def load(fname):
	with open(fname, 'rb') as f:
		return parse(f.read(), 'decode')

if __name__ == '__main__':
	import sys
	import json

	fname = sys.argv[1]
	transform = sys.argv[2] if len(sys.argv) >= 3 else None

	with open(fname, 'rb') as f:
		data = parse(f.read(), transform)
		print('Parsed data.')

	with open('marshal-output.txt', 'w', encoding='utf-8') as f:
		if transform == 'pythonify':
			data = postpythonify(data)
			print(json.dumps(data, indent=2, default=str), file=f)
		else:
			print(stringify(data), file=f)
