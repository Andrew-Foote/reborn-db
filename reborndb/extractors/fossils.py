import re
from parsers.rpg import map as rpg_map
from reborndb import DB, pbs, settings

def extract():
	path = settings.REBORN_INSTALL_PATH / 'Data' / 'Map242.rxdata'

	map_ = rpg_map.Map.load(242)
	event = map_.events[11]
	page = event.pages[0]

	state = 'not found comment yet'
	script_lines = []

	for cmd in page.list_:
		if state == 'not found comment yet':
			if cmd.short_type_name == 'Comment' and cmd.text == 'Convert fossil into species now.':
				state = 'found comment'
		elif state == 'found comment':
			assert cmd.short_type_name == 'Script'
			script_lines.append(cmd.line)
			state = 'reading script'
		elif state == 'reading script':
			if cmd.short_type_name == 'ContinueScript':
				script_lines.append(cmd.line)
			else:
				break
		else:
			assert False

	script = '\n'.join(script_lines)
	#print(script)
	m = re.match(r'arr\s*=\s*\[(.*)\]', script, re.S)
	items = m.group(1).split(',')
	items = [item.strip(' \n:') for item in items]
	rows = []

	for i in range(len(items) // 2):
		rows.append((items[2 * i], items[2 * i + 1]))

	#print(rows)

	DB.H.bulk_insert(
	    'fossil',
	    ('item', 'pokemon'),
	    rows
	)

if __name__ == '__main__':
	extract()