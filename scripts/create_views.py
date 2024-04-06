from reborndb import DB

EXCEPTIONS = [
	'evolution',
	'evolution_trcl',
	'evolution_requirement_display',
	'trainer_single_battle_command',
	'trainer_double_battle_command',
	'map_event_comment',
	'common_event_comment',
	'trainer_event',
]

def run():
	with DB.H.transaction():
		DB.H.drop_all_views(exceptions=EXCEPTIONS)
		DB.H.execscript('views.sql')

if __name__ == '__main__':
	run()