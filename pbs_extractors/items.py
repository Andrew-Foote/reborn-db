# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       `env\Scripts\python -m pbs_extractors.items`

# The `items.txt` CSV has 11 (EDIT: 10) columns:
# - Column 1 contains a number for identifying the item.
# - Column 2 contains the uppercase ID of the item.
# - Column 3 contains the item's display name.
# - Column 4 contains the item's plural display name.
#     This appears to not be present in Reborn.
# - Column 5 contains the item's type, which determines its bag pcoket.
#   (1 = Items, 2 = Medicine, 3 = Poké Balls, 4 - TMs & HMs, 5 = Berries, 6 = Mail, 7 = Battle Items, 8 = Key Items)
# - Column 6 contains the item's buy price. (Sell price is half)
# - Column 7 contains the item's description (may be quoted, with backslash-escaping for quotes witihin)
# - Column 8 contains a value determining usability out of battle.
#   0 = Not usable outside battle
#   1 = Usable on Pokémon in party, disappears after use
#   2 = Usable outside of battle, not on Pokémon
#   3 = TM
#   4 = HM
#   5 = Usable on Pokémon in party, doesn't disappear after use
# - Column 9 contains a value determining usability in battle
#   0 = Not usable in battle
#   1 = Usable on party Pokémon in battle, disappears
#   2 = Usable directly, disappears (e.g. Poké Ball, X Accuracy, Poké Doll)
#   3 = Usable on party Pokémon, doesn't disappear
#   4 = Usable directly, doesn't disappear
# - Column 10 contains a value detemring item type
#   0 = None of below
#   1 = Mail / 2 = Mail with images of holder and two othe rparty Pokémon
#   3 = Snag Ball / 4 = Poké Ball / 5 = Berry / 6 = Key Item
#   7 = Evo stone / 8 = Fossil / 9 = Apricorn / 10 = Elemental gem
#   11 = Mulch / 12 = Mega Stone (not incl. Red/Blue Orb)
# - Column 11 = Move taught (for TMs/HMs)

from collections import defaultdict
from utils import apsw_ext, pbs

FIELDS = ('code', 'id', 'name', 'pocket', 'buy_price', 'desc', 'out_battle_usability', 'in_battle_usability', 'type', 'move')

CODE_FIELDS = {
	'pocket': ['Items', 'Medicine', 'Poké Balls', 'TMs & HMs', 'Berries', 'Mail', 'Battle Items', 'Key Items'],
	'out_battle_usability': ['None', 'PokemonOnce', 'DirectOnce', 'TM', 'HM', 'PokemonReusable'],
	'in_battle_usability': ['None', 'PokemonOnce', 'DirectOnce', 'PokemonReusable', 'DirectReusable'],
	'type': ['Other', 'Mail', 'Mail2', 'SnagBall', 'PokeBall', 'Berry', 'KeyItem', 'EvolutionStone', 'Fossil', 'Apricorn', 'Gem', 'Mulch', 'MegaStone']
}

def extract(db):
	pbs_data = pbs.load('items')
	rows = defaultdict(lambda: [])

	for row in pbs_data:
		if len(row) < len(FIELDS):
			row = (*row, *['' for _ in range(len(FIELDS) - len(row))])

		row_as_dict = {field: value for field, value in zip(FIELDS, row)}

		for field in ('code', 'pocket', 'buy_price', 'out_battle_usability', 'in_battle_usability', 'type'):
			row_as_dict[field] = int(row_as_dict[field])

		row_as_dict['pocket'] -= 1

		for field in ('pocket', 'out_battle_usability', 'in_battle_usability', 'type'):
			row_as_dict[field] = CODE_FIELDS[field][row_as_dict[field]]

		move = row_as_dict.pop('move')
		rows['item'].append(row_as_dict)

		if move:
			rows['item_move'].append({
				'item': row_as_dict['id'],
				'pocket': row_as_dict['pocket'],
				'move': move
			})

	apsw_ext.bulk_insert_multi(db, rows)

if __name__ == '__main__':	
	db = apsw_ext.connect()

	with db:
		extract(db)