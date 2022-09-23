from dataclasses import fields
from enum import Enum
import io
import parsers.rpg.map as rpg
from parsers.rpg import system

SYSTEM = system.load()

class Printer:
    def __init__(self):
        self.stream = io.StringIO()

    def print(self, *args):
        print(*args, file=self.stream)

    def onoff(self, value: bool) -> str:
        return ['off', 'on'][value]

    def format_var(self, id_):
        return f'[{id_}:{SYSTEM.variable_name(id_)}]'

    def format_switch(self, id_):
        return f'[{id_}:{SYSTEM.switch_name(id_)}]'

    def format_enum(self, val):
        return val.name.lower()

    def format_audio(self, audio: rpg.AudioFile):
        return f'"{audio.name}"; volume {audio.volume}; pitch {audio.pitch}'

    def format_cmd(self, cmd: rpg.EventCommand):
        nameparts = cmd.__class__.__name__.split('_')
        res = '_'.join(nameparts[1:])

        datafields = [field for field in fields(cmd) if field.name != 'indent']

        if datafields:
            fieldbits = []

            for datafield in datafields:
                value = getattr(cmd, datafield.name)

                if datafield.type == bytes:
                    value = '<binary data>'
                elif issubclass(value.__class__, Enum):
                    value = self.format_enum(value)
                else:
                    value = str(value)

                fieldbits.append(datafield.name + ' = ' + value)

            res += ' [{}]'.format(', '.join(fieldbits))

        return res

    def print_page_cond(self, cond: rpg.EventPageCondition):
        parts = []

        if cond.switch1_valid: parts.append(f'switch {self.format_switch(cond.switch1_id)} on')
        if cond.switch2_valid: parts.append(f'switch {self.format_switch(cond.switch2_id)} on')

        if cond.variable_valid:
            parts.append(f'variable {self.format_var(cond.variable_id)} >= {cond.variable_value}')

        if cond.self_switch_valid:
            parts.append(f'self switch "{cond.self_switch_ch}" on')

        if parts:
            self.print('Requires', ' and '.join(parts))

    def print_page_graphic(self, graphic: rpg.EventPageGraphic):
        parts = []

        if graphic.tile_id != 0:
            self.print(f'Tile {graphic.tile_id}')
        elif graphic.character_name:
            parts = [
                f'hue {graphic.character_hue}',
                f'direction {self.format_enum(graphic.direction)}',
                f'pattern {graphic.pattern}',
                f'opacity {graphic.opacity}',
                f'blend type {graphic.blend_type}'
            ]

            self.print('Character {} [{}]'.format(graphic.character_name, ', '.join(parts)))

    def print_map(self, m: rpg.Map):
        self.print(f'Tileset ID: {m.tileset_id}')
        self.print(f'Dimensions: {m.width} x {m.height}')
        self.print(f'Background music: {self.format_audio(m.bgm)}; autoplay {self.onoff(m.autoplay_bgm)}')
        self.print(f'Background sound effect: {self.format_audio(m.bgs)}; autoplay {self.onoff(m.autoplay_bgs)}')
        self.print()

        for event_id, event in m.events.items():
            header = f'Event {event_id} ({event.name}) at ({event.x}, {event.y})'
            self.print(header)
            self.print('=' * len(header))

            for page_number, page in enumerate(event.pages):
                self.print(f'Page {page_number} [trigger: {self.format_enum(page.trigger)}]')
                self.print_page_cond(page.condition)
                self.print_page_graphic(page.graphic)

                movement = [
                    f'type {self.format_enum(page.move_type)}',
                    f'speed {self.format_enum(page.move_speed)}',
                    f'frequency {self.format_enum(page.move_frequency)}',
                ]

                self.print(
                    self.format_enum(page.move_type).capitalize(), 'movement,',
                    self.format_enum(page.move_speed), 'speed,',
                    self.format_enum(page.move_frequency), 'frequency'
                )

                options = [name for name, opt in (
                    ('moving animation', page.walk_anime),
                    ('stopped animation', page.step_anime),
                    ('fixed direction', page.direction_fix),
                    ('move through', page.through),
                    ('always on top', page.always_on_top)
                ) if opt]

                self.print('Options:', ', '.join(options))

                if page.list_:
                    self.print('Commands:')

                    for command_number, command in enumerate(page.list_):
                        indent = ' ' * command.indent
                        self.print(f'{indent}{command_number} {self.format_cmd(command)}')
                else:
                    self.print('No commands')

                self.print()

            self.print()

    def read(self):
        self.stream.seek(0)
        return self.stream.read()

if __name__ == '__main__':
    import sys
    from reborndb import settings
    map_id = int(sys.argv[1])
    path = settings.REBORN_DATA_PATH / f'Map{map_id:03}.rxdata'
    map_ = rpg.Map.load(path)
    printer = Printer()
    printer.print_map(map_)

    with open('mapdata-formatted.txt', 'w') as f:
        print(f'MAP {map_id}\n', file=f)
        print(printer.read(), file=f)
