import io
import numpy as np
from parsers.rpg import common_events
from reborndb import DB
from reborndb.extractors.event_commands import unpack_event_command, create_event_command

def extract():
	common_event_list = common_events.load()
	common_event_rows = []
	event_command_data = []

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
			cmd_id = create_event_command(cmd_type, cmd_subtype, args)
			common_event_command_rows.append((event_id, cmd_i, indent, cmd_id))

	with DB.H.transaction():
		DB.H.bulk_insert(
			'common_event_command',
			('common_event_id', 'command_number', 'indent', 'command'),
			common_event_command_rows
		)
		