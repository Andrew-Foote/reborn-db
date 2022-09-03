# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       env\Scripts\python -m pbs_extractors.abilities

# from utils import apsw_ext, pbs

# def extract(db):	
# 	data = pbs.load('abilities')
# 	fields = ('code', 'id', 'name', 'desc')
# 	apsw_ext.bulk_insert(db, 'ability', fields, data)

# if __name__ == '__main__':
# 	db = apsw_ext.connect()

# 	with db:
# 		extract(db)

from reborndb import DB
from utils import pbs

def abilities():
	data = pbs.load('abilities')
	fields = ('code', 'id', 'name', 'desc')
	DB.H.bulk_insert('abilities', fields, data)
