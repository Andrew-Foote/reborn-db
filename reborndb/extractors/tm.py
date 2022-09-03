from collections import defaultdict
from reborndb import DB
from reborndb import pbs

COLS = ('pokemon', 'form', 'move')

def extract():
	pbs_data = pbs.load('tm')
	rows = []

	for section in pbs_data:
		move_class = section.header
		move = section.tm
		pokemons = set(section.content)

		for pokemon in pokemons:
			rows.append((move_class, pokemon, move))

	with DB.H.transaction():
		DB.H.dump_as_table('pbs_tm', ('class', 'pokemon', 'move'), rows)

		DB.H.exec('''
			insert into "machine_move" ("pokemon", "form", "move")
			select "pbs_tm"."pokemon", "form"."name", "pbs_tm"."move"
			from "pbs_tm"
			join "pokemon_form" as "form" on "form"."pokemon" = "pbs_tm"."pokemon"
			where "pbs_tm"."class" in ('TMs', 'HMs')
		''')

		DB.H.exec('''
			insert into "tutor_move" ("pokemon", "form", "move")
			select "pbs_tm"."pokemon", "form"."name", "pbs_tm"."move"
			from "pbs_tm"
			join "pokemon_form" as "form" on "form"."pokemon" = "pbs_tm"."pokemon"
			where "pbs_tm"."class" = 'Move Tutors'
		''')
