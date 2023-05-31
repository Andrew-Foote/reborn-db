# OBSOLETE use trainerlists.py instead

# template:
# 
# [<three-digit ID>]
# #<TierX or Unique> (or this line may be absent)
# EndSpeechLose=<...>
# Name=<...>
# PokemonNos=<comma-separated list of Pokemon numbers>
# BeginSpeech=<...>
# Type=<TrainerType>
# EndSpeechWin=<...>

import json
from reborndb import DB, pbs

def extract():
	data = pbs.load('bttrainers')
	rows = []

	for section in data:
		# there's two entries with id 336!
		code = int(section.header)

		# there's one with no name --- ID 107. maybe this is the trainer referenced in the comment
		# at PokemonOrgBattle.rb line 1146?
		name = section.content.get('Name')

		trainer_type = section.content['Type']
		begin_speech = section.content['BeginSpeech'].strip('"')
		lose_speech = section.content['EndSpeechLose'].strip('"')
		win_speech = section.content['EndSpeechWin'].strip('"')
		pokemon = section.content['PokemonNos'].split(',')
		rows.append((code, trainer_type, name, begin_speech, lose_speech, win_speech, json.dumps(pokemon)))

	with DB.H.transaction():
		DB.H.dump_as_table(
			'pbs_bttrainers',
			('pbs_order', 'type', 'name', 'begin_speech', 'lose_speech', 'win_speech', 'pokemon_numbers'),
			rows
		)

	with DB.H.transaction():
		DB.H.exec('''
			insert into "battle_facility_trainer" ("id", "type", "name", "begin_speech", "lose_speech", "win_speech")
			select "pbs_order", "type", "name", "begin_speech", "lose_speech", "win_speech"
			from "pbs_bttrainers"
		''')

	with DB.H.transaction():
		DB.H.exec('''
			insert into "battle_facility_trainer_pokemon" ("trainer", "pokemon")
			select "trainer"."pbs_order", "pokemon"."id"
			from "pbs_bttrainers" as "trainer"
			join json_each("trainer"."pokemon_numbers") as "pokemon_number"
			join "pokemon" on "pokemon"."number" = "pokemon_number"."value"
		''')