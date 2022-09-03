from code import InteractiveConsole
from reborndb import DB

InteractiveConsole(locals={
	'DB': DB
}).interact()