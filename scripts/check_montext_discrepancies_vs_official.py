from collections import defaultdict
from contextlib import redirect_stdout
from copy import deepcopy
import itertools as it
import json
from pathlib import Path
from reborndb import DB, altconnect, script, settings

def fs(*args):
    return frozenset(args)

# note: since some stuff has changed since gen 7, e.g. a lot of pokemon had base happiness
# lowered from 70 to 50, the version of the veekun pokedex checked against should be one from
# before Sw/Sh were released, e.g. the version at this commit:
# https://github.com/veekun/pokedex/commit/06aaf1b9aa496f94c207706a5d4c0b18dfa32a7c
# (BUT we also need to check against a more recent version for moves, because that commit
# is missing USUM move tutors and stuff...)
VEEKUN_PATH = Path('C:/mystuff/mycode/veekun/pokedex/pokedex/data/pokedex.sqlite')

MONTEXT_PATH = Path('C:/mystuff/mycode/reborn-montext')

PROPS_TO_IGNORE = fs(
    # irrelevant
    'BattlerAltitude', 'BattlerEnemyY', 'BattlerPlayerY'
    # not important
    ,'EggSteps', 'shadowmoves'
    # Veekun's data on this is not reliable enough
    # (Veekun seems to give base form color for all forms which is incorrect)
    ,'Color'
    # not dealing with these, for now at least
    ,'dexentry', 'evolutions', 'preevo'
    #,'WildItemCommon', 'WildItemUncommon', 'WildItemRare'
    ,'toobig' # Reju-specific
)

PROPS_TO_IGNORE_FOR_BATTLE_ONLY_FORMS = fs(
    'GrowthRate', 'Happiness', 'EggSteps', 'EggMoves', 'Moveset', 'compatiblemoves',
    'EggGroups', 'WildItemCommon', 'WildItemUncommon', 'WildItemRare', 'WildItems'
)

INTENTIONAL_DISCREPS = fs(
    # special chars in names
    ('NIDORANM', '', 'name', 'Nidoran', 'Nidoran♂'),
    ('NIDORANF', '', 'name', 'Nidoran', 'Nidoran♀'),
    ('FARFETCHD', '', 'name', "Farfetch'd", "Farfetch’d"),
    # "Overcoat added so the ability index is maintained on evolution, don't worry about it  - Fal"
    ('METAPOD', '', 'Abilities', fs('SHEDSKIN', 'OVERCOAT'), fs('SHEDSKIN')),
    ('KAKUNA', '', 'Abilities', fs('SHEDSKIN', 'OVERCOAT'), fs('SHEDSKIN')),
    ('PUPITAR', '', 'Abilities', fs('SHEDSKIN', 'ROCKHEAD'), fs('SHEDSKIN')),
    ('SILCOON', '', 'Abilities', fs('SHEDSKIN', 'OVERCOAT'), fs('SHEDSKIN')),
    ('CASCOON', '', 'Abilities', fs('SHEDSKIN', 'OVERCOAT'), fs('SHEDSKIN')),
    ('FERROSEED', '', 'Abilities', fs('IRONBARBS', 'ANTICIPATION'), fs('IRONBARBS')),
    ('SPEWPA', 'icy-snow', 'Abilities', fs('SHEDSKIN', 'OVERCOAT', 'FRIENDGUARD'), fs('SHEDSKIN', 'FRIENDGUARD')),
    # Apparently, according to Bulbapedia, the games internally treat Zygarde 50% as two separate
    # forms, depending on which ability it has. The same goes for Zygarde 10%. Veekun
    # reflects this by distinguishing the two 50% forms as "zygarde" (with Aura Break) and
    # "zygarde-50" (with Power Construct); however, it doesn't distinguish the two 10% forms.
    # What Reborn/Reju/Deso do is a freasonable simplification of this situation.
    ('ZYGARDE', '50', 'Abilities', fs('AURABREAK', 'POWERCONSTRUCT'), fs('POWERCONSTRUCT')),
    ('ZYGARDE', '10', 'Abilities', fs('AURABREAK', 'POWERCONSTRUCT'), fs('POWERCONSTRUCT')),
    ('ZYGARDE', 'complete', 'Abilities', fs('AURABREAK', 'POWERCONSTRUCT'), fs('POWERCONSTRUCT')),
    # due to this being used as the primary form in the file, even though it's battle-only,
    # so not marked as carrying an item in veekun (though veekun does have the item on the meteor forms)
    ('MINIOR', 'red', 'WildItems', (None, 'STARPIECE', None), None)
)

TUTOR_OR_MACHINE_MOVES = fs(*DB.H.exec1('''
    select "move" from "tutor_move"
    union
    select "move" from "machine_move"
'''))  

# compatiblemoves is basically TM/HM/move tutor moves, minus some moves which every Pokémon
# is presumed compatible with (those listed below), while moveexceptions is for indicating
# exceptions where a Pokémon is not compatible with one of the presumed compatible moves
PRESUMED_COMPATIBLE_MOVES = fs(
    "ATTRACT", "CONFIDE", "DOUBLETEAM", "FACADE", "FRUSTRATION", "HIDDENPOWER", "PROTECT", 
    "REST", "RETURN", "ROUND",
    "SECRETPOWER",
    "SLEEPTALK", "SNORE", "SUBSTITUTE", "SWAGGER",
    "TOXIC"
)

IGNORE_IF_COMPATIBLE_IN_REBORN_BUT_NOT_VEEKUN = fs(
    # stopped being a TM/tutor move in Gen 7, so Veekun doesn't have it for mons/forms
    # introduced post-Gen 6
    'SECRETPOWER',
    # only exists as an event move prior to Gen 8 so Veekun doesn't have it 
    'CELEBRATE',
)

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
        # rejuvenation-specific attributes that occur here that are not forms
        or form_name in ('defaultform', 'riftform', 'primalform', 'megaform', 'ultraform')
        or 'pulse' in form_name or form_name in ( # fangame-specific forms
            'aevian', 'dev', 'bot', 'purple', 'mismageon', 'meech', 'crystal'
        )
        or (form_name == 'mega' and pokemon_id in ('GARBODOR',)) # fangame-specific megas
        or form_name in ( # rejuvenation-specific (gosh there's a lot of these)
            'giga', 'monstrosity', 'tazer/partner', 'tuff-puff', 'zombie',
            'amalgamation', 'rift', 'partner', 'dark-gardevoir', 'angel-of-death',
            'fallen-angel', 'rusty-amalgamation', 'kawopudunga',
            'lunatone-dominant-fusion', 'solrock-dominant-fusion',
            'guardian-spirit', 'guardian', 'dexoy', 'west-aevian', 'east-aevian', 'released',
            'master-of-nightmares',
            'hand-of-convulsion', 'hand-of-incineration', 'hand-of-detonation',
            'hand-of-obliteration', 'broken-master',
            'big-betty', 'white-striped', 'coffee-gregus', 'crescents', 'rift-egg',
            'suspended-rift', 'unleashed-rift', 'rift-talon', 'rift-talon-2', 'augmented',
            'goomink', 'goomink-hero', 'goomink-actual-hero',
            'rocky-aevian', 'fiery-aevian', 'icy-aevian'
        ) 
        or (form_name == 'origin' and pokemon_id != 'GIRATINA') # rejuvenation-specific
        or form_name == 'hisuian' # veekun doesn't have data on hisuian forms
        or 'galarian' in form_name # nor galarian... well it does but we haven't pulled it yet
        or (pokemon_id == 'SILVALLY' and form_name == 'unknown')
        or (
            pokemon_id in ('FLABEBE', 'FLOETTE', 'FLORGES')
            and form_name in ('black', 'green')
        ) # reju-specific
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

BATTLE_ONLY_FORMS = fs(*(
    (pokemon_id, normalize_reborn_form_name(pokemon_id, form_name))
    for pokemon_id, form_name
    in DB.H.exec('''
        select "pokemon", "name" from "pokemon_form" where "battle_only" = 1
    ''')
))

# little tweak since these form's names have been changed from Broken to Busted
BATTLE_ONLY_FORMS |= fs(
    ('MIMIKYU', 'busted'),
    ('MINIOR', 'blue'), ('MINIOR', 'green'), ('MINIOR', 'indigo'),
    ('MINIOR', 'orange'), ('MINIOR', 'yellow'), ('MINIOR', 'violet')
) 

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
                elif prop_name in fs('dexnum', 'BaseEXP', 'CatchRate', 'Happiness', 'EggSteps'):
                    new_form[prop_name] = int(prop_value)
                elif prop_name in fs('Height', 'Weight'):
                    new_form[prop_name] = float(prop_value)
                elif prop_name == 'kind':
                    new_form[prop_name] = prop_value.replace(' ', '')
                elif prop_name in fs('BaseStats', 'EVs'):
                    new_form[prop_name] = tuple(map(int, prop_value))
                elif prop_name == 'Abilities':
                    new_form[prop_name] = fs(*prop_value)

                    if 'HiddenAbilities' in form:
                        new_form[prop_name] |= fs(form['HiddenAbilities'])
                elif prop_name == 'HiddenAbilities':
                    pass
                elif prop_name in ('EggMoves', 'EggGroups'):
                    new_form[prop_name] = fs(*prop_value)
                elif prop_name == 'Moveset':
                    new_form[prop_name] = fs(*((int(level), move) for level, move in prop_value))
                elif prop_name == 'compatiblemoves':
                    compatible = fs(*form['compatiblemoves']) & TUTOR_OR_MACHINE_MOVES
                    exceptions = fs(*form['moveexceptions'])
           
                    if pokemon_id == 'MEW':
                        # for mew all tutor/machine moves are presumed compatible
                        presumed_compatible = TUTOR_OR_MACHINE_MOVES
                    else:
                        presumed_compatible = PRESUMED_COMPATIBLE_MOVES

                    compatible = compatible | (presumed_compatible - exceptions)
                    new_form[prop_name] = compatible
                elif prop_name == 'moveexceptions':
                    pass
                elif prop_name.startswith('WildItem'):
                    new_form['WildItems'] = (
                        form.get('WildItemCommon'),
                        form.get('WildItemUncommon'),
                        form.get('WildItemRare')
                    )
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
                elif prop_name in fs('Height', 'Weight'):
                    new_form[prop_name] = float(prop_value)
                elif prop_name == 'kind':
                    new_form[prop_name] = prop_value.replace(' ', '')
                elif prop_name in fs('BaseStats', 'EVs'):
                    new_form[prop_name] = tuple(prop_value)
                elif prop_name == 'Abilities':
                    new_form[prop_name] = fs(*prop_value)

                    if 'HiddenAbilities' in form:
                        new_form[prop_name] |= fs(form['HiddenAbilities'])
                elif prop_name == 'HiddenAbilities':
                    pass
                elif prop_name == 'EggMoves':
                    new_form[prop_name] = fs(*map(normalize_veekun_move, prop_value))
                elif prop_name == 'Moveset':
                    level_to_moves_map = defaultdict(lambda: [])
                    
                    for level, move in prop_value:
                        level_to_moves_map[level].append(normalize_veekun_move(move))

                    evo_moves = fs(*level_to_moves_map[0])
                    
                    level_to_moves_map[1] = [
                        move for move in level_to_moves_map[1] if move not in evo_moves
                    ]

                    new_form[prop_name] = fs(*(
                        (level, move) for level, moves in level_to_moves_map.items()
                        for move in moves
                    ))
                elif prop_name == 'compatiblemoves':
                    new_form[prop_name] = fs(*map(normalize_veekun_move, prop_value)) & TUTOR_OR_MACHINE_MOVES
                elif prop_name == 'EggGroups':
                    new_form[prop_name] = fs(*prop_value)
                elif prop_name.startswith('WildItem'):
                    new_form['WildItems'] = (
                        form.get('WildItemCommon'),
                        form.get('WildItemUncommon'),
                        form.get('WildItemRare')
                    )
                else:
                    new_form[prop_name] = prop_value

    return new_data

####################################
####################################

def run(game):
    #reborn_data = normalize_reborn_data(script.parse(MONTEXT_PATH / f'{game}.rb'))
    reborn_data = normalize_reborn_data(script.parse(MONTEXT_PATH / f'montext.rb'))

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
                if prop_name not in veekun_form:
                    discreps[pokemon_id, form_name][prop_name] = (prop_value, None)
                    checked_props.add(prop_name)
                    continue

                veekun_value = veekun_form[prop_name]

                if prop_name == 'compatiblemoves':
                    prop_value = prop_value - (
                        IGNORE_IF_COMPATIBLE_IN_REBORN_BUT_NOT_VEEKUN - veekun_value
                    )

                if prop_name == 'WildItems':
                    # seems veekun incorrectly has all 100% wild held items as 5% wild held
                    # items for Gen 7
                    if (
                        prop_value[0] is not None
                        and all(i == prop_value[0] for i in prop_value[1:] + (veekun_value[1],))
                    ):
                        veekun_value = prop_value

                if prop_value != veekun_value:
                    discreps[pokemon_id, form_name][prop_name] = (prop_value, veekun_value)
    
                checked_props.add(prop_name)

            for prop_name, veekun_value in veekun_form.items():
                if prop_name not in checked_props:
                    discreps[pokemon_id, form_name][prop_name] = (None, veekun_value)

    for (pokemon_id, form_name), discreps2 in discreps.items():
        discreps2 = {
            prop_name: (prop_value, veekun_value)
            for prop_name, (prop_value, veekun_value) in discreps2.items()
            if (pokemon_id, form_name, prop_name, prop_value, veekun_value) not in INTENTIONAL_DISCREPS
        }

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
                if isinstance(prop_value, frozenset):
                    prop_value = set(prop_value)
                if isinstance(veekun_value, frozenset):
                    veekun_value = set(veekun_value)

                print(f'  Reborn value: {repr(prop_value)}')
                print(f'  Veekun value: {repr(veekun_value)}')

        print()

if __name__ == '__main__':
    # for game in ('reborn', 'reju', 'deso'):
    #     # it breaks on reju/deso currently because of the Gen VIII Pokémon
    #     # TODO: maybe use multiple copies of veekun, one for each generation,
    #     # to deal with this
    #     if game != 'reborn': continue

    #     with open(f'discreps-{game}.txt', 'w', encoding='utf-8') as f:
    #         with redirect_stdout(f):
    #             run(game)

    with open('discreps.txt', 'w', encoding='utf-8') as f:
        with redirect_stdout(f):
            run('reborn')