import io
import numpy as np
from parsers.rpg import common_events
from reborndb import DB
from reborndb.extractors.event_commands import unpack_event_command, create_event_command

def extract():
    common_event_list = common_events.load()
    common_event_rows = []
    event_command_data = []

    DB.H.exec('delete from "common_event"')

    # DB.H.exec('create index if not exists "common_event_command_idx_command" on "common_event_command" ("command")')

    # DB.H.exec('create index if not exists "event_command_move_route_argument_move_command_idx_move_command" on "event_command_move_route_argument_move_command" ("move_command")')

    # DB.H.exec('create index if not exists "event_command_move_command_argument_idx_move_command" on "event_command_move_command_argument" ("move_command")')
    
    # DB.H.exec('create index if not exists "event_page_move_command_idx_command" on "event_page_move_command" ("command")')
    
    # DB.H.exec('create index if not exists "event_page_command_idx_command" on "event_page_command" ("command")')

    # with DB.H.transaction(foreign_keys_enabled=False):
    #     for arg_type in ('integer', 'text', 'audio_file', 'direction'):
    #         DB.H.exec(f'delete from move_command_{arg_type}_argument as "arg" where exists (select * from "common_event_command" as "cec" join "event_command_move_route_argument_move_command" as "acmd" on "acmd"."event_command" = "cec"."command" and "acmd"."parameter" = "arg"."parameter" and "acmd"."move_command" = "arg"."command")')

    #         DB.H.exec(f'delete from move_command_{arg_type}_argument as "arg" where exists (select * from "common_event_command" as "cec" join "event_command_move_command_argument" as "mcarg" on "mcarg"."command" = "cec"."command" and "mcarg"."parameter" = "arg"."parameter" and "mcarg"."move_command" = "arg"."command")')

    #     DB.H.exec('delete from "move_command" as "mcmd" where exists (select * from "common_event_command" as "cec" join "event_command_move_route_argument_move_command" as "acmd" on "acmd"."event_command" = "cec"."command" where "acmd"."move_command" = "mcmd"."id")')

    #     DB.H.exec('delete from "event_command_move_route_argument_move_command" as "cmd" where exists (select * from "common_event_command" as "cec" where "cec"."command" = "cmd"."event_command")')
        
    #     DB.H.exec('delete from "move_command" as "mcmd" where exists (select * from "common_event_command" as "cec" join "event_command_move_command_argument" as "arg" on "arg"."command" = "cec"."command" where "arg"."move_command" = "mcmd"."id")')

    #     for arg_type in DB.H.exec1('select "name" from "parameter_type"'):
    #         DB.H.exec(f'delete from "event_command_{arg_type}_argument" as "arg" where exists (select * from "common_event_command" as "cec" where "cec"."command" = "arg"."command")')

    #     DB.H.exec(f'delete from "event_command" as "ec" where exists (select * from "common_event_command" as "cec" where "cec"."command" = "ec"."id")')
    #     DB.H.exec(f'delete from "common_event_command"')

    for event in common_event_list:
        common_event_rows.append((
            event.id_, event.name, event.trigger.name.lower(), event.switch_id
        ))

        for i, cmd in enumerate(event.list_):
            cmd_type, cmd_subtype, indent, args = unpack_event_command(cmd)
            
            event_command_data.append((
                event.id_, i,
                (cmd_type, cmd_subtype, indent, args)
            ))

    with DB.H.transaction():
        DB.H.bulk_insert('common_event', ('id', 'name', 'trigger', 'switch'), common_event_rows)

    common_event_command_rows = []

    with DB.H.transaction():
        for event_id, cmd_i, (cmd_type, cmd_subtype, indent, args) in event_command_data:
            print(f'{event_id}, {cmd_i}: create_event_command({cmd_type}, {cmd_subtype}, {args})')
            cmd_id = create_event_command(cmd_type, cmd_subtype, args)
            common_event_command_rows.append((event_id, cmd_i, indent, cmd_id))

    with DB.H.transaction():
        DB.H.bulk_insert(
            'common_event_command',
            ('common_event_id', 'command_number', 'indent', 'command'),
            common_event_command_rows
        )
        