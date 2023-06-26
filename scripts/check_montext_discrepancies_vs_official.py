from collections import defaultdict
from contextlib import redirect_stdout
from copy import deepcopy
import json
from pathlib import Path
from reborndb import DB, altconnect, script, settings

# note: since some stuff has changed since gen 7, e.g. a lot of pokemon had base happiness
# lowered from 70 to 50, the version of the veekun pokedex checked against should be one from
# before Sw/Sh were released, e.g. the version at this commit:
# https://github.com/veekun/pokedex/commit/06aaf1b9aa496f94c207706a5d4c0b18dfa32a7c
VEEKUN_PATH = Path('C:/mystuff/mycode/veekun/pokedex/pokedex/data/pokedex.sqlite')

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

IGNORE_HIDDEN_VS_REGULAR_ABILITIES = False

# I'm guessing at what compatiblemoves and moveexceptions are, but I think compatiblemoves
# is basically TM/HM/move tutor moves, minus some moves which every Pokémon is presumed
# compatible with (those listed below), while moveexceptions is for indicating exceptions
# where a Pokémon is not compatible with one of the presumed compatible moves
PRESUMED_COMPATIBLE_MOVES = {
    "ATTRACT", "CONFIDE", "DOUBLETEAM", "FACADE", "FRUSTRATION", "HIDDENPOWER", "PROTECT", 
    "REST", "RETURN", "ROUND", "SLEEPTALK", "SUBSTITUTE", "SWAGGER", "TOXIC"
}

def normalize_compatible_moves(data):
    new_data = {}

    for pokemon_id, pokemon in data.items():
        new_pokemon = {}

        for form_name, form in pokemon.items():
            if form_name == 'OnCreation':
                new_pokemon['OnCreation'] = form
                continue

            new_form = deepcopy(form)

            if 'compatiblemoves' in form:
                compatible = set(form['compatiblemoves'])
                exceptions = set(form['moveexceptions'])

                if pokemon_id == 'MEW':
                    # for mew all tutor/machine moves are presumed compatible
                    presumed_compatible = set(DB.H.exec1('''
                        select "move" from "tutor_move"
                        union
                        select "move" from "machine_move"
                    '''))
                else:
                    presumed_compatible = PRESUMED_COMPATIBLE_MOVES

                compatible.update(presumed_compatible - exceptions)
                new_form['compatiblemoves'] = sorted(compatible)
                del new_form['moveexceptions']
            new_pokemon[form_name] = new_form

        new_data[pokemon_id] = new_pokemon

    return new_data

def normalize_forms(data):
    # copy any attributes from the primary (first) form to secondary forms, 
    # as long as that attribute isn't already there
    # except for Type2, if Type1 is present!
    # likewise HiddenAbilities, if Abilities is present

    new_data = {}

    for pokemon_id, pokemon in data.items():
        pokemon = list(pokemon.items())
        form0 = pokemon[0][1]
        new_pokemon = {pokemon[0][0]: form0}

        for form_name, form in pokemon[1:]:
            if form_name == 'OnCreation':
                new_pokemon['OnCreation'] = form
                continue

            new_form = deepcopy(form)

            for prop_name, prop_value in form0.items():
                if prop_name not in form and not (
                    (prop_name == 'Type2' and 'Type1' in form)
                    or (prop_name == 'HiddenAbilities' and 'Abilities' in form)
                ):
                    new_form[prop_name] = prop_value

            new_pokemon[form_name] = new_form

        new_data[pokemon_id] = new_pokemon

    return new_data

def normalize_pokemon_id(pokemon_id):
    return {'NIDORANmA': 'NIDORANM', 'NIDORANfE': 'NIDORANF'}.get(pokemon_id, pokemon_id)

def normalize_form_name(pokemon_id, form_name):
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

def normalize_veekun_move(move):
    if move == 'HIGHJUMPKICK':
        return 'HIJUMPKICK'

    return move

def run():
    reborn_data = script.parse(MONTEXT_PATH)
    reborn_data = normalize_compatible_moves(reborn_data)
    reborn_data = normalize_forms(reborn_data)

    query_result = altconnect(VEEKUN_PATH).execscript(
        settings.REBORN_DB_PATH / 'queries' / 'extern' / 'veekun-montext.sql'
    ).fetchall()[0][0]

    veekun_data = json.loads(query_result)

    discreps = defaultdict(lambda: {})

    for pokemon_id, pokemon in reborn_data.items():
        pokemon_id = normalize_pokemon_id(pokemon_id)

        try:
            veekun_pokemon = veekun_data[pokemon_id]
        except KeyError:
            raise RuntimeError(f'{pokemon_id} missing in veekun')

        for form_name, form in pokemon.items():
            form_name = normalize_form_name(pokemon_id, form_name)
        
            if form_name is None:
                continue

            try:
                veekun_form = veekun_pokemon[form_name]
            except KeyError:
                raise RuntimeError(f'{pokemon_id} ({form_name}) missing in veekun')

            checked_props = set(PROPS_TO_IGNORE)

            for prop_name, prop_value in form.items():
                if prop_name in PROPS_TO_IGNORE:
                    continue

                if prop_name not in veekun_form:
                    if prop_name == 'EggMoves' and (
                        # this is an error on veekun's side --- veekun doesn't have alolan form egg move data
                        form_name == 'alola'
                        # unevolved mega forms have egg moves in the reborn data, but not in veekun
                        # --- but since mega forms can't be hatched anyway this is an irrelevant difference
                        or form_name == 'mega'
                        or pokemon_id == 'CASTFORM'
                    ):
                        continue

                    discreps[pokemon_id, form_name][prop_name] = (prop_value, None)
                    continue

                veekun_value = veekun_form[prop_name]

                if prop_name in ('dexnum', 'BaseEXP', 'CatchRate', 'Happiness', 'EggSteps', 'Height', 'Weight'):
                    prop_value = int(prop_value)
                elif prop_name in ('BaseStats', 'EVs'):
                    prop_value = list(map(int, prop_value))
                elif prop_name in ('EggMoves', 'compatiblemoves'):
                    # we don't care about order
                    prop_value = set(prop_value)
                    veekun_value = set(map(normalize_veekun_move, veekun_value))
                elif prop_name == 'Moveset':
                    prop_value = {(int(level), move) for level, move in prop_value}
                    veekun_value = {(level, normalize_veekun_move(move)) for level, move in veekun_value}
                elif prop_name == 'kind':
                    # we don't care about "TinyRaccoon" vs "Tiny Raccoon", etc.
                    prop_value = prop_value.replace(' ', '')
                    veekun_value = veekun_value.replace(' ', '')

                if prop_value != veekun_value:
                    # veekun has the gender sign, reborn doesn't --- not really important
                    if prop_name == 'name' and pokemon_id in ('NIDORANM', 'NIDORANF'):
                        continue

                    # ignore compatiblemoves present in Reborn but not Veekun, as Veekun seems
                    # to just be missing the info for a lot of these moves
                    if prop_name == 'compatiblemoves' and veekun_value.issubset(prop_value):
                        checked_props.add('compatiblemoves')
                        continue

                    discreps[pokemon_id, form_name][prop_name] = (prop_value, veekun_value)
    
                checked_props.add(prop_name)

            for prop_name, veekun_value in veekun_form.items():
                if prop_name not in checked_props:
                    if (
                        prop_name == 'HiddenAbilities' and IGNORE_HIDDEN_VS_REGULAR_ABILITIES
                        and 'Abilities' in discreps[pokemon_id, form_name]
                    ):
                        reborn_abils, veekun_abils = discreps[pokemon_id, form_name]['Abilities']

                        if reborn_abils == veekun_abils + [veekun_value]:
                            del discreps[pokemon_id, form_name]['Abilities']
                            continue

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

                if reborn_not_veekun and prop_name != 'compatiblemoves': 
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