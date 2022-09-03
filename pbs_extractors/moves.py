# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       `env\Scripts\python -m pbs_extractors.moves`

# The `moves.txt` CSV has 7 columns:
# - Column 1 contains a number for identifying the move.
# - Column 2 contains the uppercase ID of the move.
# - Column 3 contains the move's display name.
# - Column 4 contains the move's "function code". This is a textual value which determines a
#   subclass of the `PokeBattle_Move` class (defined in `PokeBattle_Move.rb`) which the move will
#   be instantiated as. The subclasses are defined in `PokeBattle_MoveEffects.rb` and have names of
#   the form `PokeBattle_Move_{code}` where `{code}` is the function code.
# - Column 5 contains the move's base power, or 0 if it's a status move, or 1 if it has variable
#   base power, or the power of a single hit if it's a multi-hit move.
# - Column 6 contains the ID of the move's type.
# - Column 7 contains the move's damage class, either "Physical", "Special", or "Status".
# - Column 8 contains the move's accuracy (with 0 meaning "always hits").
# - Column 9 contains the move's max PP, before any PP-adding items are applied. Moves that can be
#   used indefinitely (Struggle) are defined as having a max PP of 0.
# - Column 10 contains the move's additional effect chance, as a percentage. This is 0 if there's
#   no additional effect.
# - Column 11 contains the move's target, which is an enum with these values:
#   00 = single target
#   01 = no target
#   02 = single opponent selected randomly
#   04 = all opponents
#   08 = all available targets except self
#   10 = self
#   20 = both sides (status move)
#   40 = user's side (status move)
#   80 = opponent's side (status move)
#   100 = ally
#   200 = ally or self
#   400 = single opponent
#   800 = single opponent opposite user
# - Column 12 contains the move's priority.
# - Column 13 contains various single-letter flags.
#   a = physical contact
#   b = protectable
#   c = magic coatable
#   d = snatchable [mutex with c]
#   e = mirror moveable
#   f = may flinch w/ item
#   g = thaws user
#   h = high crit chance
#   i = biting
#   j = punching
#   k = sound
#   l = powder
#   m = pulse
#   n = bomb
# - Column 14 contains the move description.

import apsw
from collections import defaultdict
from utils import apsw_ext, pbs

FIELDS = (
	'code', 'id', 'name', 'function', 'power', 'type', 'damage_class', 'accuracy', 'pp',
	'additional_effect_chance', 'target', 'priority', 'flags', 'desc'
)

def extract(db):
	pbs_data = pbs.load('moves')
	rows = defaultdict(lambda: [])


	for row in pbs_data:
		row_dict = {field: value for field, value in zip(FIELDS, row)}

		for field in ('code', 'power', 'accuracy', 'pp', 'additional_effect_chance', 'priority'):
			row_dict[field] = int(row_dict[field])

		if row_dict['power'] in (0, 1): row_dict['power'] = None
		if row_dict['accuracy'] == 0: row_dict['accuracy'] = None
		if row_dict['pp'] == 0: row_dict['pp'] = None

		flags = row_dict.pop('flags', '')
		rows['move'].append(row_dict)

		for flag in flags:
			rows['move_flag_set'].append({'move': row_dict['id'], 'flag': flag})

	apsw_ext.bulk_insert_multi(db, rows)

