from reborndb import DB

def run():
	with DB.H.transaction():
		DB.H.execscript('views.sql')

if __name__ == '__main__':
	run()