# Since this script takes a lot longer to run than the other extractor scripts, I'm currently
# running it manually via
#
#   env\Scripts\python -m reborndb.extractors.map_data 
#
# when necessary. At some point I need to rework the build process to incorporate this step.

# TODO: speed this up! And put the images in the database maybe.

import io
import itertools as it
from PIL import Image
import numpy as np
from parsers.rpg.map import Map
from parsers.rpg import move_route, event_command
from reborndb import DB, settings
from scripts import populate_event_command_type_tables

type_from_getter = populate_event_command_type_tables.type_from_getter

move_command_ids = it.count()
event_command_ids = it.count()

def unpack_move_command(cmd):
    cmd_type, *params = move_route.COMMAND_TYPES[cmd.code]
    args = []

    for param, getter in params:
        args.append((
            param,
            getattr(cmd, param),
            type_from_getter(getter, cmd_type, param)
        ))

    return cmd_type, args

def unpack_event_command(cmd):
    if isinstance(cmd, event_command.EventCommand_ConditionalBranch):
        subcode = cmd.subcode
    elif isinstance(cmd, event_command.EventCommand_ControlVariables):
        subcode = cmd.operand_type_code
    elif isinstance(cmd, event_command.EventCommand_ChangeMapSettings):
        subcode = cmd.setting_type_code
    else:
        subcode = 0

    cmd_type, cmd_subtype, *params = event_command.COMMAND_TYPES_AND_SUBTYPES[cmd.code, subcode]
    args = []

    for param, getter in params:
        args.append((
            param,
            getattr(cmd, param),
            type_from_getter(getter, cmd_type, param)
        ))

    return cmd_type, cmd_subtype, cmd.indent, args

def create_move_command(cmd_type, args):
    cmd_id = next(move_command_ids)
    DB.H.exec('insert into "move_command" ("id", "type") values (?, ?)', (cmd_id, cmd_type,))
    print('create_move_command', cmd_type, args)

    for param, arg, arg_type in args:
        match arg_type:
            case 'integer':
                DB.H.exec(
                    'insert into "move_command_integer_argument" ("command", "command_type", "parameter", "type", "value") values (?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, param, arg_type, int(arg))
                )
            case 'text':
                DB.H.exec(
                    'insert into "move_command_text_argument" ("command", "command_type", "parameter", "type", "value") values (?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, param, arg_type, arg)
                )
            case 'audio_file':
                DB.H.exec(
                    'insert into "move_command_audio_file_argument" ("command", "command_type", "parameter", "type", "name", "volume", "pitch") values (?, ?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, param, arg_type, arg.name, arg.volume, arg.pitch)
                )
            case 'direction':
                DB.H.exec(
                    'insert into "move_command_direction_argument" ("command", "command_type", "parameter", "type", "direction") values (?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, param, arg_type, arg.name.lower())
                )

    return cmd_id

def create_event_command(cmd_type, cmd_subtype, args):
    cmd_id = next(event_command_ids)
    DB.H.exec('insert into "event_command" ("id", "type", "subtype") values (?, ?, ?)', (cmd_id, cmd_type, cmd_subtype))
    print('create_event_command', cmd_type, cmd_subtype, args)

    for param, arg, arg_type in args:
        match arg_type:
            case 'integer':
                DB.H.exec(
                    'insert into "event_command_integer_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, int(arg))
                )
            case 'text':
                DB.H.exec(
                    'insert into "event_command_text_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg)
                )
            case 'bool':
                DB.H.exec(
                    'insert into "event_command_bool_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, int(arg))
                )
            case 'audio_file':
                DB.H.exec(
                    'insert into "event_command_audio_file_argument" ("command", "command_type", "command_subtype", "parameter", "type", "name", "volume", "pitch") values (?, ?, ?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name, arg.volume, arg.pitch)
                )
            case 'direction':
                DB.H.exec(
                    'insert into "event_command_direction_argument" ("command", "command_type", "command_subtype", "parameter", "type", "direction") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'choices_array':
                choices = arg.copy()

                while len(choices) < 4:
                    choices.append('')

                DB.H.exec(
                    'insert into "event_command_choices_array_argument" ("command", "command_type", "command_subtype", "parameter", "type", "choice1", "choice2", "choice3", "choice4") values (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, *choices)
                )
            case 'tone':
                DB.H.exec(
                    'insert into "event_command_tone_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg)
                )
            case 'color':
                DB.H.exec(
                    'insert into "event_command_color_argument" ("command", "command_type", "command_subtype", "parameter", "type", "value") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg)
                )
            case 'cancel_type':
                DB.H.exec(
                    'insert into "event_command_cancel_type_argument" ("command", "command_type", "command_subtype", "parameter", "type", "cancel_type") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'text_position':
                DB.H.exec(
                    'insert into "event_command_text_position_argument" ("command", "command_type", "command_subtype", "parameter", "type", "text_position") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'switch_state':
                DB.H.exec(
                    'insert into "event_command_switch_state_argument" ("command", "command_type", "command_subtype", "parameter", "type", "switch_state") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'diff_type':
                DB.H.exec(
                    'insert into "event_command_diff_type_argument" ("command", "command_type", "command_subtype", "parameter", "type", "diff_type") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'appoint_type':
                DB.H.exec(
                    'insert into "event_command_appoint_type_argument" ("command", "command_type", "command_subtype", "parameter", "type", "appoint_type") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'comparison':
                DB.H.exec(
                    'insert into "event_command_comparison_argument" ("command", "command_type", "command_subtype", "parameter", "type", "comparison") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'bound_type':
                DB.H.exec(
                    'insert into "event_command_bound_type_argument" ("command", "command_type", "command_subtype", "parameter", "type", "bound_type") values (?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.name.lower())
                )
            case 'move_route':
                DB.H.exec(
                    'insert into "event_command_move_route_argument" ("command", "command_type", "command_subtype", "parameter", "type", "repeat", "skippable") values (?, ?, ?, ?, ?, ?, ?)',
                    (cmd_id, cmd_type, cmd_subtype, param, arg_type, arg.repeat, arg.skippable)
                )
                
                for move_cmd_i, move_cmd in enumerate(arg.list_):
                    move_cmd_type, move_cmd_args = unpack_move_command(move_cmd)
                    move_cmd_id = create_move_command(move_cmd_type, move_cmd_args)

                    DB.H.exec(
                        'insert into "event_command_move_route_argument_move_command" ("event_command", "parameter", "move_command_number", "move_command") values (?, ?, ?, ?)', (cmd_id, param, move_cmd_i, move_cmd_id)
                    )

    return cmd_id

def load_image(bytes_):
    stream = io.BytesIO()
    stream.write(bytes_)
    stream.seek(0)
    return Image.open(stream)

def load_tilesets():
    tileset_images = {}

    for name, tileset_file in DB.H.exec('select "name", "content" from "tileset_file"'):
        img = load_image(tileset_file).convert('RGBA')
        tiles = []

        # these assertions fail --- will that cause issues?
        # assert img.height % 32 == 0, (name, img.height)
        # assert img.width % 32 == 0, (name, img.width)

        for y in range(0, img.height, 32):
            for x in range(0, img.width, 32):
                cropped = img.crop((x, y, x + 32, y + 32))
                tiles.append(cropped)

        tileset_images[name] = {'mode': img.mode, 'tiles': tiles}

    tilesets = {}

    for id_, name, filename in DB.H.exec('select "id", "name", "file" from "tileset"'):
        autotiles = [None] * 384

        for index, atfile in DB.H.exec('''
            select "tileset_autotile"."index", "autotile"."image"
            from "tileset_autotile"
            join "autotile" on "autotile"."name" = "tileset_autotile"."autotile"
            where "tileset_autotile"."tileset" = ?
        ''', (name,)):
            # at the moment we don't understand how autotiles work exactly
            # so we're just going to choose one arbitrarily
            #
            # todo: perhaps the order of the autotile variants in the image here:
            # https://forums.rpgmakerweb.com/index.php?threads/some-tricks-to-optimize-the-autotile-slots.138589/
            # is a clue?
            atimg = load_image(atfile).convert('RGBA')
            start = (index + 1) * 48
            end = start + 48

            if atimg.height == 32:
                cropped = atimg.crop((0, 0, 32, 32))
            elif atimg.height == 128:
                cropped = atimg.crop((32, 64, 64, 96))
            else:
                assert False

            autotiles[start:end] = [cropped] * 48

        tileset_image = tileset_images[filename]
        
        tilesets[id_] = {
            'mode': tileset_image['mode'],
            'tiles': autotiles + tileset_image['tiles']
        }

    return tilesets

def chonks():
    # one transaction per chonk
    chonk = []
    count = 0

    for map_id, mapdata in Map.load_all():
        chonk.append((map_id, mapdata))
        count += 1

        if count % 25 == 0:
            yield chonk
            chonk.clear()

    if count % 25:
        yield chonk

def extract():
    with DB.H.transaction():
        DB.H.exec('drop table if exists "event_command_bound_type_argument"')
        DB.H.exec('drop table if exists "event_command_comparison_argument"')
        DB.H.exec('drop table if exists "event_command_move_route_argument_move_command"')
        DB.H.exec('drop table if exists "event_command_move_route_argument"')
        DB.H.exec('drop table if exists "event_command_appoint_type_argument"')
        DB.H.exec('drop table if exists "event_command_diff_type_argument"')
        DB.H.exec('drop table if exists "event_command_switch_state_argument"')
        DB.H.exec('drop table if exists "event_command_text_position_argument"')
        DB.H.exec('drop table if exists "event_command_cancel_type_argument"')
        DB.H.exec('drop table if exists "event_command_color_argument"')
        DB.H.exec('drop table if exists "event_command_tone_argument"')
        DB.H.exec('drop table if exists "event_command_choices_array_argument"')
        DB.H.exec('drop table if exists "event_command_direction_argument"')
        DB.H.exec('drop table if exists "event_command_audio_file_argument"')
        DB.H.exec('drop table if exists "event_command_bool_argument"')
        DB.H.exec('drop table if exists "event_command_text_argument"')
        DB.H.exec('drop table if exists "event_command_integer_argument"')
        DB.H.exec('drop table if exists "event_page_command"')
        DB.H.exec('drop table if exists "event_command"')
        DB.H.exec('drop table if exists "event_command_parameter"')
        DB.H.exec('drop table if exists "event_command_subtype"')
        DB.H.exec('drop table if exists "event_command_type"')
        DB.H.exec('drop table if exists "move_command_integer_argument"')
        DB.H.exec('drop table if exists "move_command_direction_argument"')
        DB.H.exec('drop table if exists "move_command_audio_file_argument"')
        DB.H.exec('drop table if exists "move_command_text_argument"')
        DB.H.exec('drop table if exists "move_command_integer_argument"')
        DB.H.exec('drop table if exists "event_page_move_command"')
        DB.H.exec('drop table if exists "move_command"')
        DB.H.exec('drop table if exists "move_command_parameter"')
        DB.H.exec('drop table if exists "move_command_type"')
        DB.H.exec('drop table if exists "parameter_type"')
        DB.H.exec('drop table if exists "event_page_character"')
        DB.H.exec('drop table if exists "event_page_tile"')
        DB.H.exec('drop table if exists "event_page_self_switch_condition"')
        DB.H.exec('drop table if exists "event_page_variable_condition"')
        DB.H.exec('drop table if exists "event_page_switch_condition"')
        DB.H.exec('drop table if exists "event_page"')
        DB.H.exec('drop table if exists "map_event"')
        DB.H.exec('drop table if exists "marshal_mapdata"')
        DB.H.execscript('schemas/map_event.sql')
        populate_event_command_type_tables.run()
        tilesets = load_tilesets()

    rows = []

    for chonk in chonks():
        event_rows = []
        page_rows = []
        switch_rows = []
        variable_rows = []
        self_switch_rows = []
        tile_rows = []
        character_rows = []
        move_command_data = []
        event_command_data = []

        for map_id, mapdata in chonk:
            print(f'map {map_id}')
            stream = io.BytesIO()
            np.save(stream, mapdata.data.array)
            databytes = stream.getvalue()

            bgm = (None,) * 3 if mapdata.autoplay_bgm or mapdata.bgm is None else (mapdata.bgm.name, mapdata.bgm.volume, mapdata.bgm.pitch)
            bgs = (None,) * 3 if mapdata.autoplay_bgs or mapdata.bgs is None else (mapdata.bgs.name, mapdata.bgs.volume, mapdata.bgs.pitch)

            rows.append((
                map_id, mapdata.tileset_id, mapdata.width, mapdata.height, databytes,
                *bgm, *bgs
            ))

            for event in mapdata.events.values():
                event_rows.append((map_id, event.id_, event.name, event.x, event.y))

                for page_number, page in enumerate(event.pages):
                    page_id = (map_id, event.id_, page_number)

                    page_rows.append((
                        *page_id, page.trigger.name.lower(), page.move_type.name.lower(),
                        page.move_speed.name.lower(), page.move_frequency.name.lower(),
                        page.move_route.repeat, page.move_route.skippable,
                        page.walk_anime, page.step_anime, page.direction_fix, page.through, page.always_on_top
                    ))

                    if page.condition.switch1_valid:
                        switch_rows.append((*page_id, 1, page.condition.switch1_id))

                    if page.condition.switch2_valid:
                        switch_rows.append((*page_id, 2, page.condition.switch2_id))

                    if page.condition.variable_valid:
                        variable_rows.append((*page_id, page.condition.variable_id, page.condition.variable_value))

                    if page.condition.self_switch_valid:
                        self_switch_rows.append((*page_id, page.condition.self_switch_ch.value))

                    if page.graphic.tile_id != 0:
                        tile_rows.append((map_id, event.id_, page_number, page.graphic.tile_id))
                    
                    if page.graphic.character_name:
                        character_rows.append((
                            *page_id, page.graphic.character_name, page.graphic.character_hue,
                            page.graphic.direction.name.lower(), page.graphic.pattern,
                            page.graphic.opacity, page.graphic.blend_type
                        ))

                    for i, cmd in enumerate(page.move_route.list_):
                        cmd_type, args = unpack_move_command(cmd)
                        move_command_data.append((*page_id, i, (cmd_type, args)))

                    for i, cmd in enumerate(page.list_):
                        cmd_type, cmd_subtype, indent, args = unpack_event_command(cmd)

                        event_command_data.append((
                            *page_id, i,
                            (cmd_type, cmd_subtype, cmd.indent, args)
                        ))

            save_map_tiles(map_id, mapdata, tilesets)

        with DB.H.transaction(foreign_keys_enabled=False):
            # don't enforce foreign keys for this one because the map might not exist yet
            DB.H.bulk_insert('map_event', ('map_id', 'event_id', 'name', 'x', 'y'), event_rows)
            
        with DB.H.transaction():
            page_id_cols = ('map_id', 'event_id', 'page_number')

            DB.H.bulk_insert('event_page', (
                *page_id_cols, 'trigger', 'move_type', 'move_speed',
                'move_frequency', 'move_route_repeat', 'move_route_skippable',
                'moving_animation', 'stopped_animation', 'fixed_direction', 'move_through',
                'always_on_top'
            ), page_rows)

            DB.H.bulk_insert('event_page_switch_condition', (*page_id_cols, 'index', 'switch'), switch_rows)
            DB.H.bulk_insert('event_page_variable_condition', (*page_id_cols, 'variable', 'lower_bound'), variable_rows)
            DB.H.bulk_insert('event_page_self_switch_condition', (*page_id_cols, 'switch'), self_switch_rows)
            DB.H.bulk_insert('event_page_tile', (*page_id_cols, 'tile'), tile_rows)
            DB.H.bulk_insert('event_page_character', (*page_id_cols, 'character_name', 'character_hue', 'direction', 'pattern', 'opacity', 'blend_type'), character_rows)

        event_page_move_command_rows = []

        with DB.H.transaction():
            for map_id, event_id, page_no, cmd_no, (cmd_type, args) in move_command_data:
                cmd_id = create_move_command(cmd_type, args)
                event_page_move_command_rows.append((map_id, event_id, page_no, cmd_no, cmd_id))

        with DB.H.transaction():
            DB.H.bulk_insert(
                'event_page_move_command',
                ('map_id', 'event_id', 'page_number', 'command_number', 'command'), event_page_move_command_rows
            )

        event_page_command_rows = []

        with DB.H.transaction():
            for (
                map_id, event_id, page_no, cmd_no, (cmd_type, cmd_subtype, indent, args)
             ) in event_command_data:
                cmd_id = create_event_command(cmd_type, cmd_subtype, args)
                event_page_command_rows.append((map_id, event_id, page_no, cmd_no, indent, cmd_id))
            
        with DB.H.transaction():
            DB.H.bulk_insert(
                'event_page_command',
                ('map_id', 'event_id', 'page_number', 'command_number', 'indent', 'command'),
                event_page_command_rows
            )

    with DB.H.transaction():
        DB.H.dump_as_table( 'marshal_mapdata', ('map_id', 'tileset', 'width', 'height', 'data',
            'bgm_file', 'bgm_volume', 'bgm_pitch', 'bgs_file', 'bgs_volume', 'bgs_pitch'
        ), rows)

def save_map_tiles(map_id, mapdata, tilesets):
    data = mapdata.data
    tileset = tilesets[mapdata.tileset_id]
    tiles = tileset['tiles']
    img = Image.new('RGBA', (data.width * 32, data.height * 32))

    for z in range(data.depth):
        for x in range(data.width):
            for y in range(data.height):
                tile_id = data[x, y, z]

                try:
                    tile = tiles[tile_id]
                except IndexError:
                    print(map_id, tile_id) # idk why this happens

                if tile is not None:
                    img.paste(tile, (x * 32, y * 32), tile)

    img.save(settings.SITE_PATH / 'img' / 'area' / f'{map_id}.png')

if __name__ == '__main__':
    extract()