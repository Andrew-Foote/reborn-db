# template:
# 
# [<three-digit ID>]
# #<TierX or Unique> (or this line may be absent)
# EndSpeechLose=<...>
# Name=<...>
# PokemonNos=<comma-separated list of Pokemon numbers>
# BeginSpeech=<...>
# Type=<TrainerType>
# EndSpeechWin=<...>

from collections import defaultdict
import json
from parsers import marshal
from reborndb import DB, settings

def extract():
    graph = marshal.load_file(settings.REBORN_DATA_PATH / 'trainerlists.dat').graph
    rows = defaultdict(lambda: [])

    lists_ = marshal.get_array(graph, graph.root_ref())

    for list_id, list_ref in enumerate(lists_):
        (
            trainers_ref, pokemons_ref, challenges_ref,
            trainers_fname_ref, pokemon_fname_ref, is_default_ref
        ) = marshal.get_array(graph, list_ref)

        trainers_fname = marshal.get_string(graph, trainers_fname_ref)
        pokemon_fname = marshal.get_string(graph, pokemon_fname_ref)
        is_default = marshal.get_bool(graph, is_default_ref)
        rows['trainer_list'].append((list_id, trainers_fname, pokemon_fname, is_default))

        trainers = marshal.get_array(graph, trainers_ref)

        for trainer_id, trainer_ref in enumerate(trainers):
            (
                type_ref, name_ref, begin_ref,
                win_ref, lose_ref, pokemon_ref
            ) = marshal.get_array(graph, trainer_ref)

            trainer_type = marshal.get_fixnum(graph, type_ref)

            if graph[name_ref] == marshal.RUBY_NIL:
                name = None
            else:
                name = marshal.get_string(graph, name_ref)

            begin_speech = marshal.get_string(graph, begin_ref)
            win_speech = marshal.get_string(graph, win_ref)
            lose_speech = marshal.get_string(graph, lose_ref)

            trainer_pokemon = [
                marshal.get_fixnum(graph, trainer_pokemon_ref)
                for trainer_pokemon_ref in marshal.get_array(graph, pokemon_ref)
            ]
            
            rows['marshal_battle_facility_trainer'].append((
                list_id, trainer_id, trainer_type, name,
                begin_speech, win_speech, lose_speech,
                json.dumps(trainer_pokemon)
            ))

        pokemons = marshal.get_array(graph, pokemons_ref)

        for pokemon_id, pokemon_ref in enumerate(pokemons):
            pokemon = marshal.get_inst(graph, pokemon_ref, 'PBPokemon', dict, {
                'species': marshal.get_fixnum, 'item': marshal.get_fixnum, 'nature': marshal.get_fixnum,
                'move1': marshal.get_fixnum, 'move2': marshal.get_fixnum,
                'move3': marshal.get_fixnum, 'move4': marshal.get_fixnum,
                'ev': marshal.get_fixnum, 'form': marshal.get_fixnum, 'ability': marshal.get_fixnum
            })

            pokemon['ev'] = [i for i, b in enumerate(reversed(bin(pokemon['ev'])[2:])) if b == '1']

            rows['marshal_battle_facility_pokemon'].append((
                list_id, pokemon_id, pokemon['species'], pokemon['item'], pokemon['nature'],
                pokemon['move1'], pokemon['move2'], pokemon['move3'], pokemon['move4'],
                json.dumps(pokemon['ev']), pokemon['form'], pokemon['ability']
            ))

        challenges = marshal.get_array(graph, challenges_ref)

        for challenge_ref in challenges:
            challenge = marshal.get_string(graph, challenge_ref)
            rows['trainer_list_challenge'].append((list_id, challenge))

    with DB.H.transaction():
        DB.H.bulk_insert(
            'trainer_list',
            ('id', 'trainers_file', 'pokemon_file', 'is_default'),
            rows['trainer_list']
        )

        DB.H.bulk_insert(
            'trainer_list_challenge', ('list', 'challenge'), rows['trainer_list_challenge']
        )

    with DB.H.transaction():
        DB.H.dump_as_table(
            'marshal_battle_facility_trainer',
            ('list', 'index', 'type', 'name', 'begin_speech', 'win_speech', 'lose_speech', 'pokemon_numbers'),
            rows['marshal_battle_facility_trainer']
        )

    with DB.H.transaction():
        DB.H.exec('''
            insert into "battle_facility_trainer" ("list", "index", "type", "name", "begin_speech", "win_speech", "lose_speech")
            select
                "mbt"."list", "mbt"."index", "type"."id", "mbt"."name",
                "mbt"."begin_speech", "mbt"."win_speech", "mbt"."lose_speech"
            from "marshal_battle_facility_trainer" as "mbt"
            join "trainer_type" as "type" on "type"."code" = "mbt"."type"
        ''')

    with DB.H.transaction():
        DB.H.exec('''
            insert into "battle_facility_trainer_pokemon" ("list", "trainer_index", "pokemon_index", "pokemon")
            select "mbt"."list", "mbt"."index", "pokemon_number"."key", "pokemon"."id"
            from "marshal_battle_facility_trainer" as "mbt"
            join json_each("mbt"."pokemon_numbers") as "pokemon_number"
            join "pokemon" on "pokemon"."number" = "pokemon_number"."value"
        ''')

    with DB.H.transaction():
        DB.H.dump_as_table(
            'marshal_battle_facility_pokemon',
            (
                'list', 'index', 'number', 'item', 'nature', 'move1', 'move2', 'move3', 'move4',
                'evs', 'form', 'ability'
            ),
            rows['marshal_battle_facility_pokemon']
        )

    with DB.H.transaction():
        DB.H.exec('''
            insert into "battle_facility_set" (
                "list", "index", "pokemon", "item", "nature", "form", "ability"
            )
            select
                "btp"."list", "btp"."index", "pokemon"."id", "item"."id", "nature"."id", "form"."name",
                "btp"."ability" + 1
            from "marshal_battle_facility_pokemon" as "btp"
            join "pokemon" on "pokemon"."number" = "btp"."number"
            left join "item" on "item"."code" = "btp"."item"
            join "nature" on "nature"."code" = "btp"."nature"
            join "pokemon_form" as "form" on "form"."pokemon" = "pokemon"."id" and "form"."order" = "btp"."form"
        ''')

    with DB.H.transaction():
        DB.H.exec('''
            insert into "battle_facility_set_ev_stat" ("list", "set_index", "stat")
            select "btp"."list", "btp"."index", "stat"."id"
            from "marshal_battle_facility_pokemon" as "btp"
            join json_each("btp"."evs") as "ev"
            -- there are some apparent typos in the stat names, namely ATT in sets 41 and 42, and STK in set 1194;
            -- these will just be ignored
            join "stat" on "stat"."order" = "ev"."value" 
        ''')

    with DB.H.transaction():
        DB.H.exec('''
            insert into "battle_facility_set_move" ("list", "set_index", "move_index", "move")
            select "btp"."list", "btp"."index", "move_code"."key", "move"."id"
            from "marshal_battle_facility_pokemon" as "btp"
            join json_each(
                json_array("btp"."move1", "btp"."move2", "btp"."move3", "btp"."move4")
            ) as "move_code" on "move_code"."value" != 0
            join "move" on "move"."code" = "move_code"."value"
        ''')
