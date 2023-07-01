import re
from reborndb import DB, pbs, settings

COLS = ('pokemon', 'form', 'move')

def parse_form_modifiers():
    with open(settings.REBORN_INSTALL_PATH / 'Scripts' / 'PokemonItems.rb') as f:
        src = f.read()

    # (move_class, pokemon, form_index, move)
    compat_rows = []

    # (pokemon, form_index, move)
    incompat_rows = []

    # time for some extremely dodgy ad-hoc parsing

    start_pat = re.compile(r'''
        def\s+pbSpeciesCompatible\?\s*\(\s*species\s*,\s*move\s*,\s*pokemon\s*\)\s+
            ret\s*=\s*false\s*
            return\s+false\s+if\s+species\s*<=\s*0\s+
            case\s+species\s+
                when\s*
    ''', re.X)

    m0 = re.search(start_pat, src)
    if m0 is None: breakpoint()
    src = src[m0.end():]

    end_pat = re.compile(r'''
            \s*end\s+
        end\s+
        return\s+false\s+if\s+!\s*\$cache\.tm_data\[move\]
    ''', re.X)

    m1 = re.search(end_pat, src)
    assert m1 is not None
    src = src[:m1.start()]

    clauses = re.split(r'\s*end\s+when\s*', src)

    for clause in clauses:
        pokemon_m = re.match(r'PBSpecies::(\w+)\s*(?:#[^\n]*)?\s*', clause)
        assert pokemon_m is not None
        pokemon = pokemon_m.group(1)
        clause = clause[pokemon_m.end():]
        clause = clause.removeprefix('if')
        clause = clause.strip()
        subclauses = re.split(r'\s*end\s*elsif\s*', clause)

        for subclause in subclauses:
            form_m = re.match(r'pokemon\.form\s*==\s*(\d+)\s*(?:#.*)?\s*', subclause)
            assert form_m is not None
            form_index = form_m.group(1)
            subclause = subclause[form_m.end():]
            subclause = subclause.removeprefix('if')
            subclause = subclause.removesuffix('end')
            subclause = subclause.strip()

            # only Aevian Misdreavus/Mismagius splits here
            infraclauses = re.split(r'\s*end\s*if\s*', subclause)
            assert len(infraclauses) in (1, 2)

            for infraclause in infraclauses:
                if infraclause.endswith('return true'):
                    polarity = True
                    infraclause = infraclause.removesuffix('return true')
                elif infraclause.endswith('return false'):
                    polarity = False
                    infraclause = infraclause.removesuffix('return true')
                else: 
                    # Alolan Rattata's infraclause doesn't end with return false, hence doesn't
                    # actually do anything; this is surely a bug, but nonetheless let's take it into
                    # account
                    polarity = None

                infraclause = infraclause.strip()

                if polarity is not None:
                    array_m = re.match(re.compile(r'''
                        arrayToConstant\(\s*
                            PBMoves,\s*(?:\#[^\n]*)?\s*
                            \[\s*(?:\#[^\n]*)?\s*
                                (.*?)\s*
                            \]\s*
                        \)\.include\?\(move\)
                    ''', re.X | re.S), infraclause)

                    if array_m is not None: # Aevian Misdreavus/Mismagius
                        assert polarity
                        movelist = array_m.group(1)
                        parts = re.split(r'\s*#\s*Move Tutors\s*', movelist)
                        assert len(parts) == 2
                        
                        compat_rows.extend(
                            ('TMs', pokemon, form_index, move.strip().removeprefix(':'))
                            for move in parts[0].split(',') if move.strip()
                        )

                        compat_rows.extend(
                            ('Move Tutors', pokemon, form_index, move.strip().removeprefix(':'))
                            for move in parts[1].split(',') if move.strip()
                        )
                    else:
                        if polarity:
                            breakpoint()

                        moves = re.split(r'\s*\|\|\s*', infraclause)

                        for move in moves:
                            move_m = re.match(r'\(move == PBMoves::(\w+)\)', move)
                            if move_m is None:
                                breakpoint()
                            incompat_rows.append((pokemon, form_index, move_m.group(1)))

    return compat_rows, incompat_rows

def extract():
    pbs_data = pbs.load('tm')
    pbs_rows = []

    for section in pbs_data:
        move_class = section.header
        move = section.tm
        pokemons = set(section.content)

        for pokemon in pokemons:
            pbs_rows.append((move_class, pokemon, move))

    compat_rows, incompat_rows = parse_form_modifiers()

    with DB.H.transaction():
        DB.H.exec('drop table if exists "pbs_tm"');
        DB.H.exec('drop table if exists "compatible_move_overrides"');
        DB.H.exec('drop table if exists "incompatible_move_overrides"');
        DB.H.exec('delete from "machine_move"');
        DB.H.exec('delete from "tutor_move"');

    with DB.H.transaction():
        DB.H.dump_as_table('pbs_tm', ('class', 'pokemon', 'move'), pbs_rows)
        DB.H.dump_as_table('compatible_move_overrides', ('class', 'pokemon', 'form_index', 'move'), compat_rows)
        DB.H.dump_as_table('incompatible_move_overrides', ('pokemon', 'form_index', 'move'), incompat_rows)

    with DB.H.transaction():
        DB.H.exec('''
            insert into "machine_move" ("pokemon", "form", "move")
            select "pbs_tm"."pokemon", "form"."name", "pbs_tm"."move"
            from "pbs_tm"
            join "pokemon_form" as "form" on "form"."pokemon" = "pbs_tm"."pokemon"
            left join "incompatible_move_overrides" as "incompat" on
                "incompat"."pokemon" = "form"."pokemon" and "incompat"."form_index" = "form"."order"
                and "incompat"."move" = "pbs_tm"."move"
            where "pbs_tm"."class" in ('TMs', 'HMs') and "incompat"."move" is null
            union
            select "compat"."pokemon", "form"."name", "compat"."move"
            from "compatible_move_overrides" as "compat"
            join "pokemon_form" as "form" on
                "form"."pokemon" = "compat"."pokemon" and "form"."order" = "compat"."form_index"
            where "compat"."class" = 'TMs'
        ''')

    with DB.H.transaction():
        DB.H.exec('''
            insert into "tutor_move" ("pokemon", "form", "move")
            select "pbs_tm"."pokemon", "form"."name", "pbs_tm"."move"
            from "pbs_tm"
            join "pokemon_form" as "form" on "form"."pokemon" = "pbs_tm"."pokemon"
            left join "incompatible_move_overrides" as "incompat" on (
                "incompat"."pokemon" = "form"."pokemon" and "incompat"."form_index" = "form"."order"
                and "incompat"."move" = "pbs_tm"."move"
            )
            where "pbs_tm"."class" = 'Move Tutors' and "incompat"."move" is null
            union
            select "compat"."pokemon", "form"."name", "compat"."move"
            from "compatible_move_overrides" as "compat"
            join "pokemon_form" as "form" on
                "form"."pokemon" = "compat"."pokemon" and "form"."order" = "compat"."form_index"
            where "compat"."class" = 'Move Tutors'
        ''')
        
    # with DB.H.transaction():
    #     DB.H.exec('drop table "pbs_tm"');
    #     DB.H.exec('drop table "compatible_move_overrides"');
    #     DB.H.exec('drop table "incompatible_move_overrides"');

if __name__ == '__main__':
    extract()