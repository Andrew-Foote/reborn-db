from reborndb import DB
from reborndb import pbs

def extract():
	data = pbs.load('abilities')
	fields = ('code', 'id', 'name', 'desc')

	with DB.H.transaction():
		DB.H.bulk_insert('ability', fields, data)
