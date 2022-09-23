from dataclasses import dataclass
from parsers import marshal
from reborndb import settings
    
@dataclass
class System:
    switches: list[str]
    variables: list[str]

    def switch_name(self, id_: int) -> str:
        return self.switches[id_ - 1]

    def variable_name(self, id_: int) -> str:
        return self.variables[id_ - 1]
        
    @classmethod
    def get(cls, graph, ref):
        arrays = {'switches': [], 'variables': []}
        switches = []
        variables = []

        system = graph[ref]

        if (
            isinstance(system, marshal.MarshalRegObj)
            and marshal.get_symbol(graph, system.cls) != 'RPG::System'
        ):
            raise ValueError(f'the object at ref {ref} is not a RPG::System object')
        
        for key_ref, value_ref in system.inst_vars:
            name = marshal.get_symbol(graph, key_ref)
            assert name[0] == '@'

            try:
                array = arrays[name[1:]]
                refs = marshal.get_array(graph, value_ref)

                if not graph[refs[0]] == marshal.RUBY_NIL:
                    raise ValueError(f'expected first element of array at ref {value_ref} to be nil')

                for ref in refs[1:]:
                    array.append(marshal.get_string(graph, ref))
            except KeyError:
                pass

        return cls(**arrays)

def load():
    data = marshal.load_file(settings.REBORN_DATA_PATH / 'System.rxdata')
    return System.get(data.graph, data.graph.root_ref())

