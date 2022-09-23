from parsers.rpg import system
from reborndb import DB

def extract():
	sys = system.load()
	switches = [(i + 1, name) for i, name in enumerate(sys.switches)]
	variables = [(i + 1, name) for i, name in enumerate(sys.variables)]

	with DB.H.transaction():
		DB.H.bulk_insert('game_switch', ('id', 'name'), switches)
		DB.H.bulk_insert('game_variable', ('id', 'name'), variables)