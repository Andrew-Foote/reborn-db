from dataclasses import dataclass
from enum import Enum
import itertools as it
from functools import partial
from typing import Any, Type, TypeVar
from typing import get_args as type_get_args

from parsers import marshal
from parsers.rpg.basic import *
from parsers.rpg.move_route import *
from parsers.rpg.event_command import *
from reborndb import settings

T = TypeVar('T')

@dataclass
class EventPageCondition:
    switch1_valid: bool
    switch2_valid: bool
    variable_valid: bool
    self_switch_valid: bool
    switch1_id: int # references a switch from System.rxdata
    switch2_id: int # references a switch from System.rxdata
    variable_id: int # references a variable from System.rxdata
    variable_value: int
    self_switch_ch: str
    
    @classmethod
    def get(cls: Type[T], graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> Type[T]:
        return marshal.get_inst(graph, ref, 'RPG::Event::Page::Condition', cls, {
            'switch1_valid': marshal.get_bool, 'switch2_valid': marshal.get_bool,
            'variable_valid': marshal.get_bool, 'self_switch_valid': marshal.get_bool,
            'switch1_id': marshal.get_fixnum, 'switch2_id': marshal.get_fixnum,
            'variable_id': marshal.get_fixnum, 'variable_value': marshal.get_fixnum,
            'self_switch_ch': marshal.get_string
        })
        
@dataclass
class EventPageGraphic:
    tile_id: int
    character_name: str
    character_hue: int
    direction: Direction
    pattern: int
    opacity: int
    blend_type: int
    
    @classmethod
    def get(cls: Type[T], graph: marshal.MarshalGraph, ref: marshal.MarshalRef) -> Type[T]:
        return marshal.get_inst(graph, ref, 'RPG::Event::Page::Graphic', cls, {
            'tile_id': marshal.get_fixnum, 'character_name': marshal.get_string,
            'character_hue': marshal.get_fixnum, 'direction': Direction.get,
            'pattern': marshal.get_fixnum, 'opacity': marshal.get_fixnum,
            'blend_type': marshal.get_fixnum
        })
    
@dataclass
class EventPage:
    condition: EventPageCondition
    graphic: EventPageGraphic
    move_type: MoveType
    move_speed: MoveSpeed
    move_frequency: MoveFrequency
    move_route: MoveRoute
    walk_anime: bool
    step_anime: bool
    direction_fix: bool
    through: bool
    always_on_top: bool
    trigger: EventPageTrigger
    list_: list[EventCommand]        
    
    @classmethod
    def get(cls, graph, ref):
        def cls2(**inst_vars):
            inst_vars['list_'] = inst_vars.pop('list')
            return cls(**inst_vars)
            
        return marshal.get_inst(graph, ref, 'RPG::Event::Page', cls2, {
            'condition': EventPageCondition.get, 'graphic': EventPageGraphic.get,
            'move_type': MoveType.get, 'move_speed': MoveSpeed.get,
            'move_frequency': MoveFrequency.get, 'move_route': MoveRoute.get,
            'walk_anime': marshal.get_bool, 'step_anime': marshal.get_bool,
            'direction_fix': marshal.get_bool, 'through': marshal.get_bool,
            'always_on_top': marshal.get_bool, 'trigger': EventPageTrigger.get,
            'list': partial(marshal.get_array, callback=EventCommand.get)
        })
        
@dataclass
class Event:
    id_: int
    name: str
    x: int
    y: int
    pages: list[EventPage]
    
    @classmethod
    def get(cls, graph, ref):
        def cls2(**inst_vars):
            inst_vars['id_'] = inst_vars.pop('id')
            return cls(**inst_vars)
                    
        return marshal.get_inst(graph, ref, 'RPG::Event', cls2, {
            'id': marshal.get_fixnum, 'name': marshal.get_string,
            'x': marshal.get_fixnum, 'y': marshal.get_fixnum,
            'pages': partial(marshal.get_array, callback=EventPage.get)
        })
    
@dataclass
class Map:
    tileset_id: int # references data in tilesets.rxdata
    width: int
    height: int
    autoplay_bgm: bool
    bgm: AudioFile
    autoplay_bgs: bool
    bgs: AudioFile
    encounter_list: list
    encounter_step: int
    data: Table
    events: dict[int, Event]
    
    def __post_init__(self):
        # Sanity checks

        assert not self.encounter_list
        assert self.encounter_step == 30

        assert self.width == self.data.width
        assert self.height == self.data.height
        assert self.data.depth == 3
        
        for event_id, event in self.events.items():
            assert event_id == event.id_
    
    @classmethod
    def get(cls, graph, ref):
        return marshal.get_inst(graph, ref, 'RPG::Map', cls, {
            'tileset_id': marshal.get_fixnum,
            'width': marshal.get_fixnum, 'height': marshal.get_fixnum, 
            'autoplay_bgm': marshal.get_bool, 'bgm': AudioFile.get,
            'autoplay_bgs': marshal.get_bool, 'bgs': AudioFile.get,
            'encounter_list': partial(marshal.get_array, callback=lambda graph, ref: ref),
            'encounter_step': marshal.get_fixnum,
            'data': partial(Table.get, expected_dimcount=3),
            'events': partial(
                marshal.get_hash, key_callback=marshal.get_fixnum, value_callback=Event.get
            )
        })    
        
    @classmethod
    def load(cls, map_id):
        path = settings.REBORN_DATA_PATH / f'Map{map_id:03}.rxdata'
        data = marshal.load_file(str(path))
        return cls.get(data.graph, data.graph.root_ref())

    @classmethod
    def load_all(cls):
        for map_id in it.count(1):
            try:
                yield map_id, cls.load(map_id)
            except FileNotFoundError:
                return

if __name__ == '__main__':
    import sys
    from PIL import Image
    from parsers.rpg import tilesets

    map_id = int(sys.argv[1])
    map_ = Map.load(map_id)

    data = map_.data
    tileset = tilesets.lookup(map_.tileset_id)
    tileset_img = Image.open(settings.REBORN_GRAPHICS_PATH / 'Tilesets' / f'{tileset.tileset_name}.png')

    def split_image(img, width_per_part, height_per_part):
        for y in range(0, img.height, height_per_part):
            for x in range(0, img.width, width_per_part):
                cropped = img.crop((x, y, x + width_per_part, y + height_per_part))
                yield cropped

    # we will solve autotiles... later
    basictiles = list(split_image(tileset_img, 32, 32))
    img = Image.new(tileset_img.mode, (data.width * 32, data.height * 32))

    for z in range(data.depth):
        for x in range(data.width):
            for y in range(data.height):
                tile_id = data[x, y, z]

                if tile_id >= 384:
                    tile = basictiles[tile_id - 384]
                    img.paste(tile, (x * 32, y * 32), tile)
