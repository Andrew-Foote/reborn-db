from fractions import Fraction as frac
import itertools as it
import re
from reborndb.generate import slugify
from reborndb import DB
from reborndb import pbs
from reborndb import script

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

def get_form_map():
    script_data = script.parse(script.get_path('MultipleForms.rb'))
    form_map = {}

    for pokemon, section in script_data.items():
        pokemon = re.match('PBSpecies::(.*)', pokemon).group(1)
        proc = section.get('OnCreation')
        if proc is None: continue

        # Burmy/Wormadam
        # Note: each battle has a stack of fields---the top one is the one currently
        # seen, but if it's removed, the old one will take over
        # There's a base field effect for each map based on the battle back
        # Surfing adds Water Surface to the top of the stack, encounters
        # on tiles with the terrain tag PBTerrain::PokePuddle add Murkwater Surface
        # to the top of the stack
        # The :Forced_Field_Effect game variable may add something else to the top
        # of the stack
        m = re.match(r'\s*begin #horribly stupid.*end\s*', proc, flags=re.DOTALL)

        if m is not None:
            form_map[(pokemon, None)] = f'''
                <p><sup><a name="form-note-$ID">$ID</a></sup> Form determined by field effect at start of battle.</p>
                <ul>
                <li>Electric Terrain, Chess Board, Big Top Arena, Corrosive Field,
                Corrosive Mist Field, Factory Field, Short-circuit Field, Wasteland, Glitch Field,
                Murkwater Surface, Holy Field, Mirror Arena, New World, Inverse Field,
                Psychic Terrain:
                <a href="/pokemon/{slugify(pokemon)}.html#trash-cloak">Trash Cloak</a>.</li>
                <li>Grassy Terrain, Misty Terrain, Burning Field, Swamp Field, Rainbow Field,
                Forest Field, Water Surface, Underwater, Fairy Tale Field, Flower Garden Field,
                Starlight Arena:
                <a href="/pokemon/{slugify(pokemon)}.html#plant-cloak">Plant Cloak</a>.</li>
                <li>Dark Crystal Cavern, Desert Field, Icy Field, Rocky Field, Super-heated Field,
                Ashen Beach, Cave, Crystal Cavern, Mountain, Snowy Mountain, Dragon's Den:
                <a href="/pokemon/{slugify(pokemon)}.html#sandy-cloak">Sandy Cloak</a>.</li>
                </ul>
                <p>If there is no field effect in play, then the form is determined as follows
                (the conditions apply in the given order):</p>
                <ol>
                    <li>If the player is underwater (having used Dive): Trash Cloak.</li>
                        <!-- all underwater maps are outdoor -->
                    <li>If the encounter method for the encounter is Cave: Sandy Cloak.</li>
                    <li>If the area of the encounter is not an outdoor area: Trash Cloak.</li>
                    <li>If the tile the encounter was initiated on has a "Rock" or "Sand" terrain tag: Sandy Cloak.</li>
                    <li>Otherwise: Plant Cloak.</li>
                </ol>
            '''
            continue

        # Lycanroc
        m = re.match(r'\s*daytime.*?end\s*', proc, flags=re.DOTALL)

        if m is not None:
            form_map[(pokemon, None)] = '''
                <p><sup><a name="form-note-$ID">$ID</a></sup> Form determined by time of day.</p>
                <ul>
                <li>Day (excluding dusk): <a href="/pokemon/lycanroc.html#midday">Midday Form</a>.</li>
                <li>Dusk: <a href="/pokemon/lycanroc.html#dusk">Dusk Form</a>.</li>
                <li>Night: <a href="/pokemon/lycanroc.html#midnight">Midnight Form</a>.</li>
                </ul>
            '''
            continue

        # form is determined randomly (so we'll make separate entries for each one and split the
        # chances evenly)
        m = re.match(r'\s*rand\((\d+)\)\s*', proc)

        if m is not None:
            form_count = m.group(1)
            form_count = int(form_count)
            # None = all maps
            form_map[(pokemon, None)] = tuple(range(form_count))
            continue

        # One list of maps to determine a disjunction between two forms
        one_map_list_pat = (
            r'\s*maps\s*=\s*\[(.*?)\]\s*(?:#.*)?'
            r'\s*if\s+\$game_map\s*&&\s*maps\.include\?\s*\(\s*\$game_map\.map_id\s*\)'
            r'\s*next\s+(\d+)\s+else\s+next\s+(\d+)\s+end\s*'
        )

        # Same as above but with ternary conditional
        one_map_list_pat2 = (
            r'\s*maps\s*=\s*\[(.*?)\]\s*(?:#.*)?'
            r'\s*next\s+\$game_map\s*&&\s*maps\.include\?\s*\(\s*\$game_map\.map_id\s*\)'
            r'\s*\?\s*(\d+)\s*:\s*(\d+)\s*'
        )

        m1 = re.match(one_map_list_pat, proc)
        m2 = re.match(one_map_list_pat2, proc)

        if m1 is not None or m2 is not None:
            m = m2 if m1 is None else m1
            map_list, map_form, other_form = m.group(1, 2, 3)
            maps = [int(mapp.strip()) for mapp in map_list.split(',') if mapp.strip()]

            for mapp in maps:
                form_map[(pokemon, mapp)] = (map_form,)

            form_map[(pokemon, None)] = (other_form,) # None for default form, it's probably always
                                                      # 0 but just to be safe
            continue

        # Deerling is part random and part map-based. Just put it as null for now, but
        # I'm still making matching groups for that info in case I want to do something
        # with it eventually
        deerling_pat = (
            r'\s*maps\s*=\s*\[(.*?)\]\s*case\s+rand\(\s*2\s*\)'
            r'\s*when\s+0\s+then\s+next\s+\$game_map\s*&&'
            r'\s*maps\.include\?\(\$game_map\.map_id\)\s*\?\s*(\d+)\s*:\s*(\d+)'
            r'\s*when\s+1\s+then\s+next\s+\$game_map\s*&&'
            r'\s*maps\.include\?\(\$game_map\.map_id\)\s*\?\s*(\d+)\s*:\s*(\d+)'
            r'\s*end\s*'
        )

        m = re.match(deerling_pat, proc)

        if m is not None:
            map_list, map_form1, other_form1, map_form2, other_form2 = m.group(1, 2, 3, 4, 5)
            maps = [int(mapp.strip()) for mapp in map_list.split(',') if mapp.strip()]

            for mapp in maps:
                form_map[(pokemon, mapp)] = (map_form1, map_form2)

            form_map[(pokemon, None)] = (other_form1, other_form2)
            continue

        # 3 options (one is galarian so we don't really care)
        two_map_lists_pat = (
            r'\s*aMaps\s*=\s*\[(.*?)\]\s*gMaps\s*=\s*\[(.*?)\]\s*(?:#.*)?'
            r'\s*if\s+\$game_map\s*&&\s*aMaps\.include\?\s*\(\s*\$game_map\.map_id\s*\)'
            r'\s*next\s+(\d+)'
            r'\s+elsif\s+\$game_map\s*&&\s*gMaps\.include\?\s*\(\s*\$game_map\.map_id\s*\)'
            r'\s*next\s+(\d+)'
            r'\s+else\s+next\s+(\d+)\s+end\s*'
        )

        m = re.match(two_map_lists_pat, proc)

        if m is not None:
            amap_list, gmap_list, amap_form, gmap_form, other_form = m.group(1, 2, 3, 4, 5)
            amaps = [int(mapp.strip()) for mapp in amap_list.split(',') if mapp.strip()]
            gmaps = [int(mapp.strip()) for mapp in gmap_list.split(',') if mapp.strip()]

            for amap in amaps:
                form_map[(pokemon, amap)] = (amap_form,)

            for gmap in gmaps:
                form_map[(pokemon, gmap)] = (gmap_form,)

            form_map[(pokemon, None)] = (other_form,)
            continue

        # Marowak, also part-random part-area
        marowak_pat = (
            r'\s*chancemaps\s*=\s*\[(.*?)\]\s*(?:#.*)?'
            r'\s*if\s+\$game_map\s*&&\s*chancemaps\.include\?\s*\(\s*\$game_map\.map_id\s*\)'
            r'\s*randomnum\s*=\s*rand\(2\)\s*if\s+randomnum\s*==\s*1\s*next\s+(\d+)'
            r'\s*elsif\s+randomnum\s*==\s*0\s+next\s+(\d+)\s+end\s+else\s+next\s+(\d+)\s+end\s*'
        )

        m = re.match(marowak_pat, proc)

        if m is not None:
            map_list, map_form1, map_form2, other_form = m.group(1, 2, 3, 4)
            maps = [int(mapp.strip()) for mapp in map_list.split(',') if mapp.strip()]

            for mapp in maps:
                form_map[(pokemon, mapp)] = (map_form1, map_form2)

            form_map[(pokemon, None)] = (other_form,)
            continue

        breakpoint()

    return form_map

def extract():
    form_map = get_form_map()
    data = pbs.load('encounters')
    map_rows = []
    pokemon_rows = []
    form_note_rows = set()
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
        map_rows.append((map_id, 'Grass', grass_rate))
        map_rows.append((map_id, 'Cave', cave_rate))
        map_rows.append((map_id, 'Water', water_rate))

        for enctype, encounters in datum['encounter_types'].items():        
            for slot_number, (pokemon_id, level, chance) in enumerate(encounters):
                # note that if the map is an underwater map, "land" = walking in the underwater grass
                # maybe "land" isn't the most appropriate name

                # as far as I can tell from the code only HeadbuttHigh is used (
                # pbHeadbuttEffect in PokemonHiddenMoves.rb simply calls pbEncounter
                # with the HeadbuttHigh encounter type)
                if enctype == 'HeadbuttLow':
                    continue

                if (pokemon_id, map_id) in form_map:
                    forms = form_map[pokemon_id, map_id]
                elif (pokemon_id, None) in form_map:
                    forms = form_map[pokemon_id, None]
                else:
                    forms = (0,)

                if isinstance(forms, str):
                    form_note_rows.add((pokemon_id, forms))
                    forms = (None,)

                for form in forms:
                    pokemon_rows.append((
                        map_id, enctype, pokemon_id, form, level, str(chance / len(forms))
                    ))

    with DB.H.transaction():
        DB.H.bulk_insert(
            'map_encounter_rate',
            ('map', 'terrain', 'rate'),
            map_rows
        )

        DB.H.dump_as_table(
            'pbs_pokemon_encounter_rate',
            ('map', 'method', 'pokemon', 'form', 'level', 'rate'),
            pokemon_rows
        )

        DB.H.exec('''
            insert into "pokemon_encounter_rate" ("map", "method", "pokemon", "form", "level", "rate")
            select
                "rate"."map", "rate"."method"
                ,"rate"."pokemon", "form"."name"
                ,"rate"."level", "rate"."rate"
            from "pbs_pokemon_encounter_rate" as "rate"
            left join "pokemon_form" as "form" on (
                "form"."pokemon" = "rate"."pokemon" and "form"."order" = "rate"."form"
            )
        ''')

        DB.H.bulk_insert(
            'pokemon_encounter_form_note',
            ('pokemon', 'note'),
            form_note_rows
        )