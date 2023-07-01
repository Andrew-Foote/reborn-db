import runpy
import sys
from reborndb import DB
from reborndb import settings

def run():
    #DB.H.close()
	sys.argv[1:] = ('--directory', str(settings.REBORN_DB_PATH), '--bind', '127.0.0.1')
	runpy.run_module('http.server', {'sys': sys}, '__main__')

if __name__ == '__main__':
	run(0)