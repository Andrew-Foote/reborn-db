from collections import defaultdict
from contextlib import redirect_stdout
from copy import deepcopy
import itertools as it
import json
from pathlib import Path
from reborndb import DB, altconnect, script, settings

# note: since some stuff has changed since gen 7, e.g. a lot of pokemon had base happiness
# lowered from 70 to 50, the version of the veekun pokedex checked against should be one from
# before Sw/Sh were released, e.g. the version at this commit:
# https://github.com/veekun/pokedex/commit/06aaf1b9aa496f94c207706a5d4c0b18dfa32a7c
VEEKUN_PATH = Path('C:/mystuff/mycode/veekun/pokedex/pokedex/data/pokedex.sqlite')
#VEEKUN_PATH = Path('C:/mystuff/mycode/veekun/pokedex.sqlite')

MONTEXT_PATH = Path('C:/mystuff/mycode/reborn-montext/reborn.rb')

PROPS_TO_IGNORE = (
    # irrelevant
    'BattlerAltitude', 'BattlerEnemyY', 'BattlerPlayerY'
    # not dealing with these, for now at least
    ,'dexentry', 'evolutions', 'preevo', 'shadowmoves' 
    ,'WildItemCommon', 'WildItemUncommon', 'WildItemRare'
    # ,'compatiblemoves', 'moveexceptions'
    # ,'Abilities', 'HiddenAbilities'
    # ,'BaseEXP'
)

PROPS_TO_IGNORE_FOR_BATTLE_ONLY_FORMS = (
    'GrowthRate', 'Happiness', 'EggSteps', 'EggMoves', 'Moveset', 'compatiblemoves',
    'EggGroups'
)

IGNORE_HIDDEN_VS_REGULAR_ABILITIES = False

TUTOR_OR_MACHINE_MOVES = set(DB.H.exec1('''
    select "move" from "tutor_move"
    union
    select "move" from "machine_move"
'''))  

# compatiblemoves is basically TM/HM/move tutor moves, minus some moves which every Pokémon
# is presumed compatible with (those listed below), while moveexceptions is for indicating
# exceptions where a Pokémon is not compatible with one of the presumed compatible moves
PRESUMED_COMPATIBLE_MOVES = {
    "ATTRACT", "CONFIDE", "DOUBLETEAM", "FACADE", "FRUSTRATION", "HIDDENPOWER", "PROTECT", 
    "REST", "RETURN", "ROUND", "SECRETPOWER", "SLEEPTALK", "SNORE", "SUBSTITUTE", "SWAGGER",
    "TOXIC"
}

def normalize_reborn_form_name(pokemon_id, form_name):
    form_name = (
        form_name.lower().replace(' ', '-').replace('-forme', '').replace('-form', '')
        .replace('alolan', 'alola')
        .replace('???', 'unknown') # arceus
        .replace('-cloak', '') # burmy
        .replace('-sea', '') # shellos
        .replace('-mode', '') # darmanitan
        .replace('-drive', '') # genesect
        .replace('-flower', '') # flabebe
        .replace('%', '') # zygarde
        .replace('-style', '').replace('balie', 'baile').replace("'", '') # oricorio
        .replace('-core', '') # minior
    )

    if (
        form_name == 'oncreation' # not a form
        or 'pulse' in form_name or form_name in ( # fangame-specific forms
            'aevian', 'dev', 'bot', 'purple', 'mismageon', 'meech', 'crystal'
        )
        or (form_name == 'mega' and pokemon_id in ('GARBODOR',)) # fangame-specific megas
        or form_name == 'hisuian' # veekun doesn't have data on hisuian forms
        or pokemon_id == 'SILVALLY' and form_name == 'unknown'
    ):
        return None # i.e. skip this one

    if pokemon_id not in ('DEOXYS', 'ARCEUS', 'SILVALLY'):
        form_name = form_name.replace('normal', '')

    if not form_name: # handle pokemon with form diffs in official but not reborn
        form_name = {
            'MOTHIM': 'plant',
            'SCATTERBUG': 'icy-snow',
            'SPEWPA': 'icy-snow',
            'VIVILLON': 'meadow',
            'FURFROU': 'natural',
            'PUMPKABOO': 'super',
            'GOURGEIST': 'super',
            'XERNEAS': 'active'
        }.get(pokemon_id, form_name)

    form_name = form_name.replace(f'-{pokemon_id.lower()}', '') 
    form_name = form_name.replace(f'{pokemon_id.lower()}-', '') 
    form_name = form_name.replace(pokemon_id.lower(), '') 

    form_name = {
        '!': 'exclamation', '?': 'question', # unown
        'meteor': 'red-meteor', # minior
        'dusk-mane': 'dusk', 'dawn-wings': 'dawn' # necrozma
    }.get(form_name, form_name) # unown

    return form_name

BATTLE_ONLY_FORMS = {
    (pokemon_id, normalize_reborn_form_name(pokemon_id, form_name))
    for pokemon_id, form_name
    in DB.H.exec('''
        select "pokemon", "name" from "pokemon_form" where "battle_only" = 1
    ''')
}

def normalize_reborn_data(data):
    new_data = {}

    for pokemon_id, pokemon in data.items():
        pokemon_id = {'NIDORANmA': 'NIDORANM', 'NIDORANfE': 'NIDORANF'}.get(pokemon_id, pokemon_id)  
        new_pokemon = {}
        new_data[pokemon_id] = new_pokemon

        for i, (form_name, form) in enumerate(pokemon.items()):
            form_name = normalize_reborn_form_name(pokemon_id, form_name)

            if form_name is None:
                continue

            new_form = {}
            new_pokemon[form_name] = new_form

            for prop_name, prop_value in form.items():
                if prop_name in PROPS_TO_IGNORE:
                    pass
                elif (pokemon_id, form_name) in BATTLE_ONLY_FORMS and prop_name in PROPS_TO_IGNORE_FOR_BATTLE_ONLY_FORMS:
                    pass
                elif prop_name in ('dexnum', 'BaseEXP', 'CatchRate', 'Happiness', 'EggSteps', 'Height', 'Weight'):
                    new_form[prop_name] = int(prop_value)
                elif prop_name == 'kind':
                    new_form[prop_name] = prop_value.replace(' ', '')
                elif prop_name in ('BaseStats', 'EVs'):
                    new_form[prop_name] = list(map(int, prop_value))
                elif prop_name == 'Abilities':
                    new_form[prop_name] = set(prop_value)

                    if 'HiddenAbilities' in form:
                        new_form[prop_name].add(form['HiddenAbilities'])
                elif prop_name == 'HiddenAbilities':
                    pass
                elif prop_name == 'EggMoves':
                    new_form[prop_name] = set(prop_value)
                elif prop_name == 'Moveset':
                    new_form[prop_name] = {(int(level), move) for level, move in prop_value}
                elif prop_name == 'compatiblemoves':
                    compatible = set(form['compatiblemoves']) & TUTOR_OR_MACHINE_MOVES
                    exceptions = set(form['moveexceptions'])
           
                    if pokemon_id == 'MEW':
                        # for mew all tutor/machine moves are presumed compatible
                        presumed_compatible = TUTOR_OR_MACHINE_MOVES
                    else:
                        presumed_compatible = PRESUMED_COMPATIBLE_MOVES

                    compatible.update(presumed_compatible - exceptions)
                    new_form[prop_name] = set(compatible)
                elif prop_name == 'moveexceptions':
                    pass
                else:
                    new_form[prop_name] = prop_value

            if i > 0:
                new_form0 = list(new_pokemon.items())[0][1]

                for prop_name, prop_value in new_form0.items():
                    if not (
                        prop_name in new_form
                        or (
                            (pokemon_id, form_name) in BATTLE_ONLY_FORMS
                            and prop_name in PROPS_TO_IGNORE_FOR_BATTLE_ONLY_FORMS
                        )
                        or (prop_name == 'Type2' and 'Type1' in form)
                    ):
                        new_form[prop_name] = prop_value

    return new_data

def normalize_veekun_move(move):
    if move == 'HIGHJUMPKICK':
        return 'HIJUMPKICK'

    return move

def normalize_veekun_data(data):
    new_data = {}

    for pokemon_id, pokemon in data.items():
        new_pokemon = {}
        new_data[pokemon_id] = new_pokemon

        for form_name, form in pokemon.items():
            new_form = {}
            new_pokemon[form_name] = new_form

            for prop_name, prop_value in form.items():
                if (pokemon_id, form_name) in BATTLE_ONLY_FORMS and prop_name in PROPS_TO_IGNORE_FOR_BATTLE_ONLY_FORMS:
                    pass
                elif prop_name == 'name':
                    new_form[prop_name] = prop_value[:-1] if prop_value[:-1] == 'NIDORAN' else prop_value
                elif prop_name == 'kind':
                    new_form[prop_name] = prop_value.replace(' ', '')
                elif prop_name == 'Abilities':
                    new_form[prop_name] = set(prop_value)

                    if 'HiddenAbilities' in form:
                        new_form[prop_name].add(form['HiddenAbilities'])
                elif prop_name == 'HiddenAbilities':
                    pass
                elif prop_name == 'EggMoves':
                    new_form[prop_name] = set(map(normalize_veekun_move, prop_value))
                elif prop_name == 'Moveset':
                    level_to_moves_map = defaultdict(lambda: [])
                    
                    for level, move in prop_value:
                        level_to_moves_map[level].append(normalize_veekun_move(move))

                    evo_moves = set(level_to_moves_map[0])
                    
                    level_to_moves_map[1] = [
                        move for move in level_to_moves_map[1] if move not in evo_moves
                    ]

                    new_form[prop_name] = {
                        (level, move) for level, moves in level_to_moves_map.items()
                        for move in moves
                    }
                elif prop_name == 'compatiblemoves':
                    new_form[prop_name] = set(map(normalize_veekun_move, prop_value)) & TUTOR_OR_MACHINE_MOVES
                else:
                    new_form[prop_name] = prop_value

    return new_data

####################################
####################################


def run():
    reborn_data = normalize_reborn_data(script.parse(MONTEXT_PATH))

    query_result = altconnect(VEEKUN_PATH).execscript(
        settings.REBORN_DB_PATH / 'queries' / 'extern' / 'veekun-montext.sql'
    ).fetchall()[0][0]

    veekun_data = normalize_veekun_data(json.loads(query_result))

    discreps = defaultdict(lambda: {})

    for pokemon_id, pokemon in reborn_data.items():
        try:
            veekun_pokemon = veekun_data[pokemon_id]
        except KeyError:
            raise RuntimeError(f'{pokemon_id} missing in veekun')

        for form_name, form in pokemon.items():
            try:
                veekun_form = veekun_pokemon[form_name]
            except KeyError:
                raise RuntimeError(f'{pokemon_id} ({form_name}) missing in veekun')

            checked_props = set(PROPS_TO_IGNORE)

            for prop_name, prop_value in form.items():
                # if prop_name == 'compatiblemoves' and prop_name not in veekun_form:
                #     import sys
                #     print(pokemon_id, form_name, veekun_form)
                #     sys.exit()

                veekun_value = veekun_form[prop_name]

                if prop_value != veekun_value:
                    discreps[pokemon_id, form_name][prop_name] = (prop_value, veekun_value)
    
                checked_props.add(prop_name)

            for prop_name, veekun_value in veekun_form.items():
                if prop_name not in checked_props:
                    discreps[pokemon_id, form_name][prop_name] = (None, veekun_value)

    for (pokemon_id, form_name), discreps2 in discreps.items():
        if not discreps2:
            continue

        print(f'{pokemon_id} ({form_name})')
        print('----------------------------------------------')

        for prop_name, (prop_value, veekun_value) in discreps2.items():
            print(prop_name)

            if veekun_value is None:
                print(f'  Reborn value: {prop_value}')
                print('  Veekun value: none')
            elif prop_value is None:
                print('  Reborn value: none')
                print(f'  Veekun value: {veekun_value}')
            elif prop_name in ('BaseStats', 'EVs'):
                print(f'  Reborn: {prop_value}')
                print(f'  Veekun: {veekun_value}')

                stat_name = ['HP', 'Atk', 'Def', 'SpA', 'SpD', 'Spe']

                for i, v in enumerate(prop_value):
                    if v != veekun_value[i]:
                        print(f'  {stat_name[i]}: {v} in Reborn, {veekun_value[i]} in Veekun')
            elif prop_name in ('EggMoves', 'Moveset', 'compatiblemoves'):
                reborn_not_veekun = sorted(prop_value - veekun_value)
                veekun_not_reborn = sorted(veekun_value - prop_value)

                if reborn_not_veekun: 
                    print(f'  Present in Reborn, but not Veekun: {", ".join(map(str, reborn_not_veekun))}')

                if veekun_not_reborn:
                    print(f'  Present in Veekun, but not Reborn: {", ".join(map(str, veekun_not_reborn))}')
            else:
                print(f'  Reborn value: {repr(prop_value)}')
                print(f'  Veekun value: {repr(veekun_value)}')

        print()

if __name__ == '__main__':
    with open('discreps.txt', 'w', encoding='utf-8') as f:
        with redirect_stdout(f):
            run()