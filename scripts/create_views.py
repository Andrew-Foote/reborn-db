from reborndb import DB

EXCEPTIONS = [
	'evolution',
	'evolution_trcl',
	'evolution_requirement_display',
]

def run():
	with DB.H.transaction():
		DB.H.drop_all_views(exceptions=EXCEPTIONS)
		DB.H.execscript('views.sql')

if __name__ == '__main__':
	run()