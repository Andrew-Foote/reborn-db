# The `btpokemon.txt` file is a list of Pokémon sets used to populate teams in the Battle Tower and
# similar facilities. To interpret it, I had to read the the `PokemonOrgBattle.rb` script, class
# `PBPokemon`, method `fromInspected`.
#
# The CSV has 7 columns:
# - Column 1 contains the ID of the Pokémon for the set.
# - Column 2 contains the ID of the held item for the set, or an empty string if there is no held
#   item.
# - Column 3 contains the ID the nature for the set.
# - Column 4 contains a comma-separated list of stat IDs ("HP", "ATK", "DEF",
#   "SPD", "SA" or "SD"), which determine the EV spread for the set. The Pokémon's 510 EVs will be
#   divided evenly between each of the listed stats (using floor division).
# - Column 5 contains a comma-separated list of move IDs for the set (always of size 4, although
#   move slots other than the first may be empty).
# - Column 6 contains the index of the Pokémon's form for the set (with the forms ordered as in
#   `pokemon.txt`).
# - Column 7 contains the index of the ability for the set (0 = first ability, 1 = second ability,
#   2 = third ability, with the first and second abilities ordered as in `pokemon.txt`).

import json
from reborndb import DB, pbs

def extract():
	data = pbs.load('btpokemon')
	rows = []

	for i, row in enumerate(data):
		pokemon, item, nature, evs, moves, form, ability = row
		evs = list(filter(None, evs.split(',')))
		moves = list(filter(None, moves.split(',')))
		rows.append((i, pokemon, item, nature, json.dumps(evs), json.dumps(moves), form, ability))

	with DB.H.transaction():
		DB.H.dump_as_table(
			'pbs_btpokemon',
			('pbs_order', 'pokemon', 'item', 'nature', 'evs', 'moves', 'form', 'ability'),
			rows
		)

	with DB.H.transaction():
		DB.H.exec('''
			insert into "battle_facility_set" ("id", "pokemon", "item", "nature", "form", "ability")
			select
				"btp"."pbs_order", "btp"."pokemon", "btp"."item", "btp"."nature", "form"."name",
				-- case
					-- special case for Minus and Plusle which are marked as having their second ability
					-- when they only have a primary ability and a hidden ability
					-- when "pa"."ability" is null then 1
					-- else "pa"."index"
				-- end
				"btp"."ability" + 1
			from "pbs_btpokemon" as "btp"
			join "pokemon_form" as "form" on "form"."pokemon" = "btp"."pokemon" and "form"."order" = "btp"."form"
			left join "pokemon_ability" as "pa" on "pa"."pokemon" = "form"."pokemon" and "pa"."form" = "form"."name"
				and "pa"."index" = "btp"."ability" + 1
		''')

	with DB.H.transaction():
		DB.H.exec('''
			insert into "battle_facility_set_ev_stat" ("set", "stat")
			select "btp"."pbs_order", "ev"."value"
			from "pbs_btpokemon" as "btp"
			join json_each("btp"."evs") as "ev"
			-- there are some apparent typos in the stat names, namely ATT in sets 41 and 42, and STK in set 1194;
			-- these will just be ignored
			join "stat" on "stat"."id" = "ev"."value" 
		''')

	with DB.H.transaction():
		DB.H.exec('''
			insert into "battle_facility_set_move" ("set", "index", "move")
			select "btp"."pbs_order", "move"."key", "move"."value"
			from "pbs_btpokemon" as "btp"
			join json_each("btp"."moves") as "move"
		''')

