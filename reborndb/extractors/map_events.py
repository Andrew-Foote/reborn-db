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

def get_array(
    graph: marshal.MarshalGraph, ref: marshal.MarshalRef, callback: Dereffer
) -> list[Any]:
    vertex = graph[vertex]
    assert isinstance(vertex, marshal.MarshalArray)
    assert not vertex.inst_vars
    assert not vertex.module_ext
    return [callback(graph, item_ref) for item_ref in vertex.items]
    
def get_hash(
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

def get_user_data(graph: marshal.MarshalGraph, ref: marshal.MarshalRef, class_name: str) -> bytes:
    vertex = graph[vertex]
    assert isinstance(vertex, marshal.MarshalUserData)
    assert get_symbol(graph, vertex.cls) == class_name
    assert not vertex.inst_vars
    assert not vertex.module_ext
    return vertex.data
    
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
        def get_encounter_list(graph, ref):
            items = get_array(graph, ref, lambda x: x)
            assert not items
            
        def get_encounter_step(graph, ref):
            value = get_fixnum(graph, ref)
            assert value == 30
                    
        return get_inst(graph, ref, 'RPG::Map', cls, {
            'tileset_id': get_fixnum, 'width': get_fixnum, 'height': get_fixnum, 
            'autoplay_bgm': get_bool, 'bgm': AudioFile.get,
            'autoplay_bgs': get_bool, 'bgs': AudioFile.get,
            'encounter_list': get_encounter_list,
            'encounter_step': get_encounter_step,
            'data': partial(get_user_data, class_name='Table'),
            'events': partial(get_array, callback=Event.get)
        })    

def extract_file(path):
    data = marshal.load_file(str(path))
