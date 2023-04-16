import runpy
import sys
from reborndb import DB
from reborndb import settings

def run():
    #DB.H.close()
	sys.argv[1:] = ('--directory', str(settings.REBORN_DB_PATH))
	runpy.run_module('http.server', {'sys': sys}, '__main__')

if __name__ == '__main__':
	run(0)