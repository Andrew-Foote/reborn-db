from parsers.rpg import common_events as rpg_common_events
from parsers.rpg import map as rpg_map

# Rayquaza roaming is set in Settings.rb --- some other useful info there too

def scripts(cmds):
	script = ''

	for cmd in cmds:
		if cmd.short_type_name == 'Script':
			script = cmd.line
		elif cmd.short_type_name == 'ContinueScript':
			script.append('\n' + cmd.line)
		else:
			if script:
				yield script
				script = ''

wild_re = re.compile(
	r'''pbWildBattle\s*\(
		\s*(?P<species>.*?)\s*,
		\s*(?P<level>.*?)\s*,
		\s*(?P<var_id>.*?)\s*
	\)''',
	re.X
)

trade_re = re.compile(
	r'''pbStartTrade\s*\('
	\)''',
	re.X
)

gift_re = re.compile(
	r'''(?P<poke_var>\w+)\s*=\s*PokeBattle_Pokemon.new\s*\(
		\s*(?P<species>.*?)\s*,
		\s*(?P<level>.*?)\s*
	\)''',
	re.X
)

def parse_species(species):
	m = re.match(r'(?:PBSpecies:):(\w+)', species)

	if m is None:
		raise ValueError(f'unexpected species string: {species}')

	return m.group(1)

for event in rpg_common_events.load():
	for script in scripts(cmds):
		m = re.match(wild_re, script)

		if m is not None:
			species = m.groupdict()['species']
			level = m.groupdict()['level']
			var_id = m.groupdict()['var_id']
			print(species, level, var_id)

			# look up further info in PokemonEncounterModifiers.rgb
			


for map_id, map_ in Map.load_all():
	print(f'Map {map_id_}')