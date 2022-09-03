# The `moves.txt` CSV has 14 columns:
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

from collections import OrderedDict
from reborndb import DB
from reborndb import pbs

FIELDS = OrderedDict((field, i) for i, field in enumerate((
	'code', 'id', 'name', 'function', 'power', 'type', 'damage_class', 'accuracy', 'pp',
	'additional_effect_chance', 'target', 'priority', 'flags', 'desc'
)))

def extract():
	data = pbs.load('moves')
	move_rows = []
	flag_rows = []

	for row in data:
		new_row = list(cell or '0' for cell in row)
		if row[FIELDS['power']] in ('0', '1'): new_row[FIELDS['power']] = None
		if row[FIELDS['accuracy']] == '0': new_row[FIELDS['accuracy']] = None
		if row[FIELDS['pp']] == '0': new_row[FIELDS['pp']] = None

		flags = row[FIELDS['flags']]
		del new_row[FIELDS['flags']]
		move_rows.append(new_row)
		
		for flag in flags:
			flag_rows.append((row[FIELDS['id']], flag))

	with DB.H.transaction():
		DB.H.bulk_insert('move', tuple(field for field in FIELDS if field != 'flags'), move_rows)
		DB.H.bulk_insert('move_flag_set', ('move', 'flag'), flag_rows)

