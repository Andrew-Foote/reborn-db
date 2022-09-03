import runpy
import sys
from reborndb import DB

def run():
    #DB.H.close()
	sys.argv[1:] = ('--directory', 'site')
	runpy.run_module('http.server', {'sys': sys}, '__main__')

if __name__ == '__main__':
	run(0)