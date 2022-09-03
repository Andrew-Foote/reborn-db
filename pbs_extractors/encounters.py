# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       env\Scripts\python -m pbs_extractors.encounters

import apsw
from collections import defaultdict
from fractions import Fraction as frac
import itertools as it
from utils import apsw_ext, pbs

def density_to_percentage(density):
    return (density / 250) * 100

ENCOUNTER_TYPES = {
    'Land': [20,15,12,10,10,10,5,5,5,4,2,2],
    'Cave': [20,15,12,10,10,10,5,5,5,4,2,2],
    'Water': [50,25,15,7,3],
    'RockSmash': [50,25,15,7,3],
    'OldRod': [70,30],
    'GoodRod': [60,20,20],
    'SuperRod': [40,35,15,7,3],
    'HeadbuttLow': [30,25,20,10,5,5,4,1],
    'HeadbuttHigh': [30,25,20,10,5,5,4,1],
    'LandMorning': [20,15,12,10,10,10,5,5,5,4,2,2],
    'LandDay': [20,15,12,10,10,10,5,5,5,4,2,2],
    'LandNight': [20,15,12,10,10,10,5,5,5,4,2,2],
    'BugContest': [20,15,12,10,10,10,5,5,5,4,2,2]
}

def extract(db):
    data = pbs.load('encounters')
    rows = defaultdict(lambda: [])
    collated_data = {}

    for map_id, datum in data.items():
        new_datum = {'densities': datum['densities'], 'encounter_types': {}}

        for enctype, encounters in datum['encounter_types'].items():
            new_datum['encounter_types'][enctype] = []

            chances = ENCOUNTER_TYPES[enctype]
            chances_total = sum(chances)
            per_pokemon = {}

            for slot_number, (pokemon_id, min_level, max_level) in enumerate(encounters):
                chances_per_level = per_pokemon.get(pokemon_id, {})
                chance = frac(chances[slot_number], chances_total)
                level_range = list(range(min_level, max_level + 1))
                level_count = len(level_range)

                for level in level_range:
                    chances_per_level[level] = chances_per_level.get(level, 0) + chance / level_count

                per_pokemon[pokemon_id] = chances_per_level

            for pokemon_id, chances_per_level in per_pokemon.items():
                for level, chance in chances_per_level.items():
                    new_datum['encounter_types'][enctype].append((pokemon_id, level, chance))

        collated_data[map_id] = new_datum

    base_data = []
    chance_data = []

    for map_id, datum in collated_data.items():
        grass_rate, cave_rate, water_rate = datum['densities']
        rows['map_encounter_rate'].append({'map': map_id, 'terrain': 'Grass', 'rate': grass_rate})
        rows['map_encounter_rate'].append({'map': map_id, 'terrain': 'Cave', 'rate': cave_rate})
        rows['map_encounter_rate'].append({'map': map_id, 'terrain': 'Water', 'rate': water_rate})

        for enctype, encounters in datum['encounter_types'].items():        
            for slot_number, (pokemon_id, level, chance) in enumerate(encounters):
                # for now, assume all encounters are in the Pokémon's first form

                form_name = list(db.cursor().execute(
                    'select "name" from "pokemon_form" where "pokemon" = ? and "order" = ?',
                    (pokemon_id, 0)
                ))[0][0]

                # note that if the map is an underwater map, "land" = walking in the underwater grass
                # maybe "land" isn't the most appropriate name

                # as far as I can tell from the code only HeadbuttHigh is used (
                # pbHeadbuttEffect in PokemonHiddenMoves.rb simply calls pbEncounter
                # with the HeadbuttHigh encounter type)
                if enctype == 'HeadbuttLow':
                    continue

                rows['pokemon_encounter_rate'].append({
                    'map': map_id, 'method': enctype,
                    'pokemon': pokemon_id, 'form': form_name, 'level': level,
                    'rate': str(chance)
                })

    apsw_ext.bulk_insert_multi(db, rows)

# apsw_ext.setup_error_handling()
# db = apsw.Connection('db.sqlite')

# with db:
#     db.cursor().execute(f"""
#         drop table if exists `encounter_chance`;
#         drop table if exists `encounter_rates`;
#     """)        

#     db.cursor().execute(f"""
#         create table `encounter_rates` (
#             `map_id` integer primary key,
#             `map_name` text,
#             `grass_rate` integer not null check (`grass_rate` >= 0 and `grass_rate` <= 250),
#             `cave_rate` integer not null check (`cave_rate` >= 0 and `cave_rate` <= 250),
#             `water_rate` integer not null check (`water_rate` >= 0 and `water_rate` <= 250),
#             foreign key (`map_id`) references `map` (`id`)
#         ) without rowid;
#     """)

#     apsw_ext.bulk_insert(db, 'encounter_rates', ('map_id', 'map_name', 'grass_rate', 'cave_rate', 'water_rate'), base_data)

#     db.cursor().execute(f"""
#         create table `encounter_chance` (
#             `map_id` integer,
#             `pokemon_id` text,
#             `method` text check (`method` in ('Land', 'LandMorning', 'LandDay', 'LandNight', 'Cave', 'OldRod', 'GoodRod', 'SuperRod', 'Water', 'HeadbuttLow', 'HeadbuttHigh')),
#             `level` integer not null,
#             `chance_ntor` integer not null check (`chance_ntor` >= 0),
#             `chance_dtor` integer not null check (`chance_dtor` >= 1),
#             -- primary key (`map_id`, `pokemon_id`, `method`, `level`),
#             foreign key (`map_id`) references `map` (`id`),
#             foreign key (`pokemon_id`) references `pokemon` (`id`)
#         );
#     """)

#     apsw_ext.bulk_insert(db, 'encounter_chance', ('map_id', 'pokemon_id', 'method', 'level', 'chance_ntor', 'chance_dtor'), chance_data)
