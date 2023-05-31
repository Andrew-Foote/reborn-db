import json
import re
from reborndb import DB, pbs, settings

with open(settings.REBORN_DB_PATH / 'queries' / 'special_pokemon_without_special_moves.sql') as f:
    query = f.read()

results = DB.H.exec(query).fetchall()
csv = []

with open(f'PBS/trainers.txt', newline='', encoding='utf-8') as f:
    for line in f.readlines():
        line = line.strip()
        line = re.match(r'\s*([^#]*)\s*(?:#.*)?', line).group(1)
        line = line.strip()
        csv.append(line)

for row in results:
    trainer_type, trainer_name, party_id, trainer, index, pokemon, evs, moves = row
    evs = json.loads(evs)
    evdesc = ', '.join(f'{ev["value"]} {ev["stat"]}' for ev in evs if ev["value"])
    print(f"{trainer}'s {pokemon} -", evdesc, '- no special moves')
    party_id_bit = '' if party_id == 0 else f',{party_id}'
    i = 0

    while i + 3 + index < len(csv):
        # if csv[i] == 'MELOETTA':
        #     print('BUNKUS@', f'"{csv[i + 1]}"', trainer_name, party_id_bit)

        if csv[i] == trainer_type and csv[i + 1] == f'{trainer_name}{party_id_bit}':
            j = i + 3 + index
            print(f'line {j}: {csv[j]}')
            break

        i += 1

    print()

