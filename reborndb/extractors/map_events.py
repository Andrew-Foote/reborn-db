from dataclasses import dataclass
from parsers import marshal
from typing import Any, Callable, Protocol

Dereffer = Callable[[marshal.MarshalGraph, marshal.MarshalRef], Any]

def get_bool(graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> bool:
    return {marshal.RUBY_TRUE: True, marshal.RUBY_FALSE: False}[graph[vertex]]

def get_fixnum(graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> int:
    vertex = graph[vertex]
    assert isinstance(vertex, marshal.RubyFixnum)
    return vertex.value

def get_symbol(graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> str:
    vertex = graph[vertex]
    assert isinstance(vertex, marshal.RubySymbol)
    return vertex.name.decode('utf-8', 'surrogateescape')

def array_from_ref(
    graph: marshal.MarshalGraph, ref: marshal.MarshalRef, callback: Dereffer
) -> list[Any]:
    vertex = graph[vertex]
    assert isinstance(vertex, marshal.MarshalArray)
    assert not vertex.inst_vars
    assert not vertex.module_ext
    return [callback(graph, item_ref) for item_ref in vertex.items]
    
def hash_from_ref(
    graph: marshal.MarshalGraph, ref: marshal.MarshalRef,
    key_callback: Dereffer, value_callback: Dereffer
) -> dict[marshal.MarshalRef, marshal.MarshalRef]:
    vertex = graph[vertex]
    assert isinstance(vertex, marshal.MarshalHash)
    assert not vertex.inst_vars
    assert not vertex.module_ext
    assert vertex.default is None
    
    return {
        key_callback(graph, key_ref): value_callback(graph, value_ref)
        for key_ref, value_ref in vertex.items
    }

class KwargsCallable(Protocol):
    def __call__(self, **kwargs: Any) -> Any:
        ...

def get_inst(
    graph: marshal.MarshalGraph, ref: marshal.MarshalRef,
    class_name: str, ctor: KwargsCallable,
    inst_var_callbacks: dict[str, Dereffer]
) -> Any:
    vertex = graph[vertex]
    assert isinstance(vertex, marshal.MarshalRegObj)
    assert get_symbol(graph, vertex.cls) == class_name
    assert not vertex.module_ext
    inst_vars = {}
    
    for key_ref, value_ref in vertex.inst_vars:
        key = get_symbol(graph, key_ref)
        assert key[0] == '@'
        mainkey = key[1:]
        
        try:
            callback = inst_var_callbacks[mainkey]
        except KeyError:
            raise ValueError(f'unexpected instance variable "{mainkey}" for class "{class_name}")
        else:
            value = callback(graph, value_ref)
            inst_vars[mainkey] = value
            
    for key in inst_var_callbacks.keys():
        if key not in inst_vars:
            raise ValueError(f'expected instance variable "{key}" for class "{class_name}")
            
    return ctor(**inst_vars)
    
@dataclass
class Map:
    tileset_id: int
    width: int
    height: int
    autoplay_bgm: bool
    bgm: AudioFile
    autoplay_bgs: bool
    bgs: AudioFile
    encounter_list: list
    encounter_step: int
    data: bytes
    events: list[Event]
    
    @classmethod
    def get(cls, graph, ref):
        def fail(): assert False
        def get_encounter_list(graph, ref):
            array = get_array(graph, ref)
        
        return get_inst(graph, ref, 'RPG::Map', cls, {
            'tileset_id': get_fixnum, 'width': get_fixnum, 'height': get_fixnum, 
            'autoplay_bgm': get_bool, 'bgm': AudioFile.get,
            'autoplay_bgs': get_bool, 'bgs': AudioFile.get,
            'encounter_list': partial(get_array, callback=fail),
            'encounter_step': 
        })
        
        vertex = graph[ref]
        assert isinstance(vertex, marshal.MarshalRegObj)
        assert symbol_from_ref(vertex.cls) == 'RPG::Map'
        assert not vertex.module_ext
        attrs = {}
        
        for key_ref, value_ref in vertex.inst_vars:
            key = symbol_from_ref(key_ref)
            
            if key == '@tileset_id':
                attrs['tileset_id'] = fixnum_from_ref(value_ref)
            elif key == '@width':
                attrs['width'] = fixnum_from_ref(value_ref)
            elif key == '@height':
                attrs['height'] = fixnum_from_ref(value_ref)
            elif key == '@autoplay_bgm':
                attrs['autoplay_bgm'] = bool_from_ref(value_ref)
            elif key == '@bgm':
                attrs['bgm'] = AudioFile.from_ref(value_ref)
            elif key == '@autoplay_bgs':
                attrs['autoplay_bgs'] = bool_from_ref(value_ref)
            elif key == '@bgs':
                attrs['bgs'] = AudioFile.from_ref(value_ref)
            elif key == '@encounter_list':
                assert not array_from_ref(value_ref)
            elif key == '@encounter_step':
                assert fixnum_from_ref(value_ref) == 30
            elif key == '@data':
                value = graph[value_ref]
                assert symbol_from_ref(value.cls) == 'Table'
                attrs['data'] = value.data
            elif key == '@events':
                hash = hash_from_ref(value_ref)
                
                for key_ref, value_ref in hash.items():
                    
        
        ('@tileset_id', '@width', '@height', '@autoplay_bgm', '@bgm', '@autoplay_bgs', '@bgs', '@encounter_list', '@encounter_step', '@data', '@events')
        
        expecting
        
        
    ref = graph.root_ref()
    vertex = graph[ref]
    assert isinstance(vertex, marshal.MarshalRegObj)
    assert graph[vertex.cls].name == b'RPG::Map'
    assert not vertex.module_ext
    expecting = ('@tileset_id', '@width', '@height', '@autoplay_bgm', '@bgm', '@autoplay_bgs', '@bgs', '@encounter_list', '@encounter_step', '@data', '@events')
   
    for key_ref, value_ref in vertex.inst_vars:
        name = graph[key_ref].name
        
        if name.decode(')
        

def extract_file(path):
    data = marshal.load_file(str(path))

 ('@tileset_id', '@width', '@height', '@autoplay_bgm', '@bgm', '@autoplay_bgs',
  '@bgs', '@encounter_list', '@encounter_step', '@data', '@events')
   

MAP_DATA_PATH_PAT = r'Map(\d{3}).rxdata'

for data_file in REBORN_DATA_PATH.iterdir():
    rows = defaultdict(lambda: []) # per file because it takes too much memory if we put data for all maps in one array
    
    is_map_data = re.match(MAP_DATA_PATH_PAT, data_file.name)
    if not is_map_data: continue
    map_id = int(is_map_data.group(1))
    print(str(data_file))
    map_row = [map_id]
    data = marshal.load_file(str(path))
    assert data.major_version == 4
    assert data.minor_version == 8
    graph = data.graph
    ref = graph.root_ref()
    vertex = graph[ref]
    assert isinstance(vertex, marshal.MarshalRegObj)
    assert graph[vertex.cls].name == b'RPG::Map'
    assert not vertex.module_ext
    expecting = ('@tileset_id', '@width', '@height', '@autoplay_bgm', '@bgm', '@autoplay_bgs', '@bgs', '@encounter_list', '@encounter_step', '@data', '@events')
   
    for key_ref, value_ref in vertex.inst_vars:
        name = graph[key_ref].name
        
        if name.decode(')