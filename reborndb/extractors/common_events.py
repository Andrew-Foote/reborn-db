import io
import numpy as np
from parsers.rpg import common_events
from reborndb import DB, settings

def extract():
	eventlist = common_events.load()
	eventrows = []

	for event in eventlist:
		eventrows.append((event.id_, event.name, event.trigger.name.lower(), event.switch_id))

	with DB.H.transaction():
		DB.H.bulk_insert('common_event', ('id', 'name', 'trigger', 'switch'), eventrows)