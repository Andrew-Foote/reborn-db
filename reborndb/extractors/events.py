import json
import re
from parsers import marshal
from reborndb import DB, REBORN_DATA_PATH

def map_path(id_):
	return REBORN_DATA_PATH / f'Map{id_:0>3}.rxdata'

# we should also look at commonevents

map_ids = DB.H.exec('select "id" from "map" order by "id"')
rows = []

for map_id, in map_ids:
	print(f'Map {map_id}')
	data = marshal.load(map_path(map_id))
	data = {marshal.pythonify(key): val for key, val in data.vars.items()}
	events = data['@events']

	for event_id, event in events.mapping.items():
		event_id = marshal.pythonify(event_id)
		event_vars = {marshal.pythonify(key): val for key, val in event.vars.items()}
		name = marshal.pythonify(event_vars['@name'])
		pages = event_vars['@pages']

		for page_number, page in enumerate(pages.items):
			page_vars = {marshal.pythonify(key): val for key, val in page.vars.items()}
			commands = page_vars['@list']
			state = 'initial'
			statevars = {}

			for command_number, command in enumerate(commands.items):
				command_vars = {marshal.pythonify(key): val for key, val in command.vars.items()}
				code = marshal.pythonify(command_vars['@code'])
				params = marshal.pythonify(command_vars['@parameters'])

				if state == 'initial':
					if code == 355:
						if params == ('pbWildBattle(',):
							state = 'wild_battle'
							statevars = {'command_number': command_number}
						elif params == ('pbStartTrade(',):
							state = 'trade'
							statevars = {'command_number': command_number}
						elif params == ('poke=PokeBattle_Pokemon.new(',):
							state = 'gift'
							statevars = {'command_number': command_number}
				elif state == 'wild_battle':
					assert code == 655
					assert len(params) == 1
					m = re.match(r'PBSpecies::(\w+),(\d+),(\d+)\)', params[0])
					assert m is not None
					species, level, var_id = m.group(1, 2, 3) # NB var_id seems to always be 117
					print(map_id, event_id, species, 'battle')
					
					rows.append((
						map_id, event_id, page_number, statevars['command_number'], species, 0, level, 'battle',
						None, None, json.dumps([]), None, json.dumps({}), None, None, None, None
					))

					state = 'initial'
				elif state == 'gift':
					assert code == 655, (map_id, event_id, page_number, command_number)
					assert len(params) == 1
					m = re.match(r'(?:PBSpecies:)?:(\w+),(\d+)\)', params[0])
					assert m is not None, params[0]
					species, level = m.group(1, 2)
					print(map_id, event_id, species, 'gift')
					#rows.append((map_id, event_id, page_number, command_number, species, level, 1))
					state = 'gift2'
					statevars['species'] = species
					statevars['level'] = level
				elif state == 'gift2':
					assert code == 655
					assert len(params) == 1
					param = params[0]
					m = re.match(r'poke.ot\s*=\s*"(.*?)"', param)

					if m is not None:
						statevars['ot'] = m.group(1)
						continue

					m = re.match(r'poke.trainerID\s*=\s*(.*)', param)

					if m is not None:
						statevars['trainer_id'] = m.group(1)
						continue

					m = re.match(r'poke.pbLearnMove\(:(\w+)\)', param)

					if m is not None:
						if 'moves' in statevars:
							statevars['moves'].append(m.group(1))
						else:
							statevars['moves'] = [m.group(1)]
						continue

					m = re.match(r'poke.form\s*=\s*(\d+)', param)

					if m is not None:
						statevars['form'] = m.group(1)
						continue

					m = re.match(r'poke.iv\[(\d+)]\s*=\s*(\d+)', param)

					if m is not None:
						if 'iv' in statevars:
							statevars['iv'][m.group(1)] = m.group(2)
						else:
							statevars['iv'] = {m.group(1): m.group(2)}
						continue

					m = re.match(r'poke.hp\s*=\s*(\d+)', param)

					if m is not None:
						statevars['hp'] = m.group(1)
						continue

					m = re.match(r'poke.setItem\(:(\w+)\)', param)

					if m is not None:
						statevars['held_item'] = m.group(1)
						continue

					m = re.match(r'poke.happiness\s*=\s*(\d+)', param)

					if m is not None:
						statevars['happiness'] = m.group(1)
						continue

					m = re.match(r'poke.abilityflag\s*=\s*(\d+)', param)

					if m is not None:
						statevars['ability'] = m.group(1)
						continue

					if param == 'poke.resetMoves':
						continue

					if param == 'poke.makeMale':
						statevars['gender'] = 'Male'
						continue

					if param == 'poke.makeFemale':
						statevars['gender'] = 'Female'
						continue

					if param == 'pbStartTrade(':
						state = 'trade'
						continue

					assert param == 'pbAddPokemon(poke)', param

					rows.append((
						map_id, event_id, page_number,
						statevars['command_number'], statevars['species'], statevars.get('form', 0), statevars['level'],
						'gift', statevars.get('ot'), statevars.get('trainer_id'),
						json.dumps(statevars.get('moves', [])), statevars.get('gender'),
						json.dumps(statevars.get('iv', {})), statevars.get('hp'), statevars.get('held_item'),
						statevars.get('happiness'), statevars.get('ability')
					))

					state = 'initial'
					statevars = {}
				elif state == 'trade':
					assert code == 655
					assert params == ('pbGet(1),',)
					state = 'trade2'
				elif state == 'trade2':
					assert code == 655
					
					if 'species' in statevars:
						assert params == ('poke,',)
					else:
						assert len(params) == 1
						m = re.match(r'PBSpecies::(\w+),', params[0])
						assert m is not None
						statevars['species'] = m.group(1)

					print(map_id, event_id, statevars['species'], 'trade')
					state = 'trade3'
				elif state == 'trade3':
					assert code == 655
					assert len(params) == 1
					m = re.match(r'"(.*?)"', params[0])
					assert m is not None
					statevars['nickname'] = m.group(1)
					state = 'trade4'
				elif state == 'trade4':
					assert code == 655
					assert len(params) == 1
					m = re.match(r'"(.*?)"', params[0])
					assert m is not None
					statevars['trainer_name'] = m.group(1)
					state = 'trade5'
				elif state == 'trade5':
					assert code == 655
					assert params == (')',)

					rows.append((
						map_id, event_id, page_number,
						statevars['command_number'], statevars['species'],
						statevars.get('form', 0), statevars.get('level', None),
						'trade',
						# tstrictly speaking we need to look up the trainer name and get ot and id from there
						statevars.get('trainer_name'), statevars.get('trainer_name'),
						json.dumps(statevars.get('moves', [])), statevars.get('gender'),
						json.dumps(statevars.get('iv', {})),
						statevars.get('hp'), statevars.get('held_item'), statevars.get('happiness'),
						statevars.get('ability')
					))

					state = 'initial'
					statevars = {}


with DB.H.transaction():
	DB.H.dump_as_table(
		'event_encounter',
		(
			'map_id', 'event_id', 'page_index', 'command_index', 'pokemon', 'form', 'level', 'type', 
			'ot', 'trainer_id', 'moves', 'gender', 'ivs', 'hp', 'held_item', 'friendship', 'ability'
		),
		rows
	)