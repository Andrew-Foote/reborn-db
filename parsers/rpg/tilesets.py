from dataclasses import dataclass
from functools import partial
from parsers import marshal
from reborndb import settings
from parsers.rpg.basic import *
    
# Each tile is a 32 x 32 section of the tileset file.
# The tileset file is always 256 pixels wide, i.e. 8 tiles wide,
# but can be any multiple of 32 pixels high.
# I'm guessing the tile IDs are allocated left-to-right, top-to-bottom.
# We should be able to turn a map data table into an image, then...

@dataclass
class Tileset:
    id_: int
    name: str
    tileset_name: str # note: distinct from name... this is the one that corresponds to the actual file
    autotile_names: list[str] # may contain empty strings for absence
    panorama_name: str # empty string for absence
    panorama_hue: int
    fog_name: str # empty string for absence (all Reborn tilesets have empty string for this)
    fog_hue: int
    fog_opacity: int
    fog_blend_type: int
    fog_zoom: int
    fog_sx: int
    fog_sy: int
    battleback_name: str # empty string for absence (all Reborn tilesets have empty string for this)
    passages: Table  
    priorities: Table
    terrain_tags: Table

    @classmethod
    def get(cls, graph, ref):
        def cls2(**inst_vars):
            inst_vars['id_'] = inst_vars.pop('id')
            return cls(**inst_vars)

        return marshal.get_inst(graph, ref, 'RPG::Tileset', cls2, {
            'id': marshal.get_fixnum, 'name': marshal.get_string,
            'tileset_name': marshal.get_string,
            'autotile_names': partial(marshal.get_array, callback=marshal.get_string),
            'panorama_name': marshal.get_string, 'panorama_hue': marshal.get_fixnum,
            'fog_name': marshal.get_string, 'fog_hue': marshal.get_fixnum,
            'fog_opacity': marshal.get_fixnum, 'fog_blend_type': marshal.get_fixnum,
            'fog_zoom': marshal.get_fixnum,
            'fog_sx': marshal.get_fixnum, 'fog_sy': marshal.get_fixnum,
            'battleback_name': marshal.get_string,
            'passages': partial(Table.get, expected_dimcount=1),
            'priorities': partial(Table.get, expected_dimcount=1),
            'terrain_tags': partial(Table.get, expected_dimcount=1)
        })

_tilesets = None

def load():
    global _tilesets

    if _tilesets is None:
        _tilesets = []

        graph = marshal.load_file(settings.REBORN_DATA_PATH / 'tilesets.rxdata').graph
        refs = marshal.get_array(graph, graph.root_ref())

        if not graph[refs[0]] == marshal.RUBY_NIL:
            raise ValueError(f'expected first element of tileset array to be nil')

        for ref in refs[1:]:
            tileset = Tileset.get(graph, ref)
            _tilesets.append(tileset)

    return _tilesets

def lookup(id_: int):
    tilesets = load()
    return tilesets[id_ - 1]

if __name__ == '__main__':
    tilesets = load()
