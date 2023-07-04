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

from collections import OrderedDict
import re
from reborndb import DB, pbs, settings

def get_pocket_names():
    path = settings.REBORN_INSTALL_PATH / 'Scripts' / 'Reborn' / 'Settings.rb'

    with path.open(encoding='utf-8') as f:
        src = f.read()

    pat = re.compile(r'''
        def\s+pbPocketNames;\s*return\s*\[\s*""\s*,
        \s*(?P<args>.*?)
        \s*\];\s*end
    ''', re.X | re.S)

    m = re.search(pat, src)
    if m is None: breakpoint()
    args = m.groupdict()['args'].split(',')
    parsed_args = []

    for arg in args:
        m = re.match(r'\s*_INTL\("(.*?)"\)', arg)
        if m is None: breakpoint()
        parsed_args.append(m.group(1))

    return parsed_args

FIELDS = OrderedDict((field, i) for i, field in enumerate((
    'code', 'id', 'name', 'pocket', 'buy_price', 'desc', 'out_battle_usability',
    'in_battle_usability', 'type', 'move'
)))

CODE_FIELDS = {
    'pocket': get_pocket_names(), #['Items', 'Medicine', 'Poké Balls', 'TMs & HMs', 'Berries', 'Mail', 'Battle Items', 'Key Items'],
    'out_battle_usability': ['None', 'PokemonOnce', 'DirectOnce', 'TM', 'HM', 'PokemonReusable'],
    'in_battle_usability': ['None', 'PokemonOnce', 'DirectOnce', 'PokemonReusable', 'DirectReusable'],
    'type': ['Other', 'Mail', 'Mail2', 'SnagBall', 'PokeBall', 'Berry', 'KeyItem', 'EvolutionStone', 'Fossil', 'Apricorn', 'Gem', 'Mulch', 'MegaStone']
}

def extract():
    pbs_data = pbs.load('items')
    item_rows = []
    machine_rows = []

    for row in pbs_data:
        row = (*row, *['' for _ in range(len(FIELDS) - len(row))])
        new_row = list(row)
        new_row[FIELDS['pocket']] = CODE_FIELDS['pocket'][int(row[FIELDS['pocket']]) - 1]

        for field in ('out_battle_usability', 'in_battle_usability', 'type'):
            new_row[FIELDS[field]] = CODE_FIELDS[field][int(row[FIELDS[field]])]

        move = row[FIELDS['move']]
        del new_row[FIELDS['move']]

        item_rows.append(new_row)

        if move:
            m = re.match(r'^TM(X?)(\d+)$', new_row[FIELDS['name']])
            machine_type = 'tmx' if m.group(1) else 'tm'
            machine_number = int(m.group(2))
            
            machine_rows.append((
                new_row[FIELDS['id']], new_row[FIELDS['pocket']],
                machine_type, machine_number, move
            ))

    with DB.H.transaction():
       DB.H.bulk_insert('item', tuple(field for field in FIELDS if field != 'move'), item_rows)
        
       DB.H.bulk_insert(
            'machine_item',
            ('item', 'pocket', 'type', 'number', 'move'),
            machine_rows
        )