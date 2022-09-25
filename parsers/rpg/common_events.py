from dataclasses import dataclass
from functools import partial
from parsers import marshal
from reborndb import settings
from parsers.rpg.basic import *
from parsers.rpg.event_command import *

@dataclass
class CommonEvent:
    id_: int
    name: str
    trigger: CommonEventTrigger
    switch_id: int
    list_: list[EventCommand]

    @classmethod
    def get(cls, graph, ref):
        def cls2(**inst_vars):
            inst_vars['id_'] = inst_vars.pop('id')
            inst_vars['list_'] = inst_vars.pop('list')
            return cls(**inst_vars)

        return marshal.get_inst(graph, ref, 'RPG::CommonEvent', cls2, {
            'id': marshal.get_fixnum, 'name': marshal.get_string,
            'trigger': CommonEventTrigger.get, 'switch_id': marshal.get_fixnum,
            'list': partial(marshal.get_array, callback=EventCommand.get)
        })

_common_events = None

def load():
    global _common_events

    if _common_events is None:
        _common_events = []

        graph = marshal.load_file(settings.REBORN_DATA_PATH / 'CommonEvents.rxdata').graph
        refs = marshal.get_array(graph, graph.root_ref())

        if not graph[refs[0]] == marshal.RUBY_NIL:
            raise ValueError(f'expected first element of common events array to be nil')

        for ref in refs[1:]:
            event = CommonEvent.get(graph, ref)
            _common_events.append(event)

    return _common_events

def lookup(id_: int):
    common_events = load()
    return common_events[id_ - 1]

if __name__ == '__main__':
    common_events = load()
