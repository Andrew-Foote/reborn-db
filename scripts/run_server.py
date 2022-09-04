import runpy
import sys
from reborndb import DB

def run():
    #DB.H.close()
	sys.argv[1:] = ('--directory', 'D:/Code/reborn-db')
	runpy.run_module('http.server', {'sys': sys}, '__main__')

if __name__ == '__main__':
	run(0)