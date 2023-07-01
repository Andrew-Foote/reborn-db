import re
from parsers.rpg import common_events as rpg_common_events
from parsers.rpg import map as rpg_map
from parsers.rpg.basic import AssignType, Comparison, SwitchState
from parsers.rpg.event_command import EventCommand_Script
from reborndb import DB, settings

# Rayquaza roaming is set in Settings.rb --- some other useful info there too

TABULA_RASA_UNOWN_FORM_NOTE = '''<p><sup><a name="event-form-note-$ID">$ID</a></sup>
Form cycles through the letters in the word ELECTRIC, GRASSY, MISTY or PSYCHIC, depending on which
room in Victory Road you entered the area from (ruby = ELECTRIC, emerald = GRASSY, sapphire =
MISTY, amethyst = PSYCHIC).'''

def parse_species(species):
    m = re.match(r'(?:PBSpecies:)?:(\w+)', species)

    if m is None:
        raise ValueError(f'unexpected species string: {species}')

    return m.group(1)

def parse_trainer_id(trainer_id):
    return '$RANDOM' if trainer_id == '$Trainer.getForeignID' else trainer_id   

def process_line(poke_var, line, datum):    
    line = line.strip()

    if not line:
        return True

    m = re.match(fr'{poke_var}.ot\s*=\s*"(?P<ot>.*?)"', line)

    if m is not None:
        datum['ot'] = m.groupdict()['ot']
        return True

    m = re.match(fr'{poke_var}.trainerID\s*=\s*(?P<trainer_id>[^\s]*)', line)

    if m is not None:
        datum['trainer_id'] = parse_trainer_id(m.groupdict()['trainer_id'])
        return True

    m = re.match(fr'{poke_var}.pbLearnMove\(:(?P<move_id>\w+)\)', line)

    if m is not None:
        move_id = m.groupdict()['move_id']

        if 'moves' in datum:
            datum['moves'].append(move_id)
        else:
            datum['moves'] = [move_id]

        return True

    m = re.match(fr'{poke_var}.form\s*=\s*(?P<form_id>\d+)', line)

    if m is not None:
        form_id = m.groupdict()['form_id']
        datum['form'] = form_id
        return True

    # this isn't working (maybe it'll work now)
    m = re.match(fr'{poke_var}.iv\[(\d+)\]\s*=\s*(\d+)', line)

    if m is not None:
        if 'iv' in datum:
            datum['iv'][m.group(1)] = m.group(2)
        else:
            datum['iv'] = {m.group(1): m.group(2)}
        return True

    m = re.match(fr'{poke_var}.hp\s*=\s*(\d+)', line)

    if m is not None:
        datum['hp'] = m.group(1)
        return True

    m = re.match(fr'{poke_var}.setItem\(:(\w+)\)', line)

    if m is not None:
        datum['held_item'] = m.group(1)
        return True

    m = re.match(fr'{poke_var}.item\s*=\s*PBItems::(?P<item_id>\w+)', line)

    if m is not None:
        datum['held_item'] = m.groupdict()['item_id']
        return True

    m = re.match(fr'{poke_var}.happiness\s*=\s*(\d+)', line)

    if m is not None:
        datum['friendship'] = m.group(1)
        return True

    m = re.match(fr'{poke_var}.abilityflag\s*=\s*(\d+)', line)

    if m is not None:
        datum['ability_slot'] = m.group(1)
        return True

    if line == f'{poke_var}.resetMoves':
        return True

    if line == f'{poke_var}.makeMale':
        datum['gender'] = 'Male'
        return True

    if line == f'{poke_var}.makeFemale':
        datum['gender'] = 'Female'
        return True

    return False

def parse_encounter_modifiers():
    with open(settings.REBORN_INSTALL_PATH / 'Scripts' / 'PokemonEncounterModifiers.rb') as f:
        src = f.read()

    m = re.search(r'case \$game_variables\[232\]', src)
    assert m is not None
    src = src[m.end():]

    var_id = None
    result = {}

    for line in src.splitlines():
        if not line: continue

        m = re.match(r'\s*when\s+(?P<var_id>\d+)', line)

        if m is not None:
            var_id = int(m.groupdict()['var_id'])
            assert var_id not in result
            result[var_id] = {}
            continue

        m = re.match(r'\s*when\s*120..145', line)

        if m is not None:
            # tabula rasa unown, special case
            var_id = 120
            continue

        assert var_id is not None, line

        if process_line('pokemon', line, result[var_id]):
            continue

        # var 21 = distorted space malamar
        if var_id == 21:
            result[var_id]['move_preference'] = 'TOPSYTURVY'
            continue

        if var_id == 120: # don't error on tabula rasa unown bit
            continue

        assert False, f'unexpected line {line}'

    return result

def cmds_with_unified_scripts(cmds):
    new_cmds = []
    script = None

    for cmd in cmds:
        if script is None:
            if cmd.short_type_name == 'Script':
                script = cmd.line
            else:
                yield cmd
        else:
            if cmd.short_type_name == 'ContinueScript':
                script += '\n' + cmd.line
            else:
                yield EventCommand_Script(indent=cmd.indent, line=script)
                script = None

                if cmd.short_type_name == 'Script':
                    script = cmd.line
                else:
                    yield cmd

    if script is not None:
        yield EventCommand_Script(indent=0, line=script)

WILD_RE = re.compile(
    r'''pbWildBattle\s*\(
        \s*(?P<species>.*?)\s*,
        \s*(?P<level>.*?)\s*
        (?:,\s*(?P<var_id>.*?))?
    \s*\)''',
    re.X
)

TRADE_RE = re.compile(
    r'''pbStartTrade\s*\(
        \s*pbGet\(1\)\s*,
        \s*(?P<species>.*?)\s*,
        \s*"(?P<nickname>.*?)"\s*,
        \s*"(?P<ot>.*?)"
    \s*\)''',
    re.X
)

TRADE_MOD_RE = re.compile(r'(?P<poke_var>\w+)\s*=\s*pbGetPokemon\(1\)')

GIFT_RE = re.compile(
    r'''(?P<poke_var>\w+)\s*=\s*PokeBattle_Pokemon.new\s*\(
        \s*(?P<species>.*?)\s*,
        \s*(?P<level>.*?)
    \s*\)''',
    re.X
)

GIFT_RE2 = re.compile(
    r'''pbAddPokemon\s*\(
        \s*(?P<species>.*?)\s*,
        \s*(?P<level>.*?)
    \s*\)''',
    re.X
)

EGG_RE = re.compile(r'(?P<poke_var>\w+)\s*=\s*Kernel\.pbGenerateEgg\s*\(\s*(?P<species>.*?)\s*\)')

INTERESTING_PATS = (WILD_RE, TRADE_RE, GIFT_RE, GIFT_RE2, EGG_RE)

def script_is_interesting(script):
    return any(re.search(pat, script) is not None for pat in INTERESTING_PATS)
    
def interesting_scripts(cmds):
    start_cmd = None
    appendix_start_cmd = None

    wild_mod_val = 0
    egg_trade = False

    script = ''
    appendix = None
    appendix_cur_outcome = None

    def flush_script(i):
        nonlocal script, appendix, appendix_cur_outcome

        if script:
            yield start_cmd, i, wild_mod_val, script, egg_trade, appendix
            script = ''
            appendix = None
            appendix_cur_outcome = None

    i = 0

    for i, cmd in enumerate(cmds_with_unified_scripts(cmds)):
        if (
            cmd.short_type_name == 'ControlVariables'
            and 232 in range(cmd.var_id_lo, cmd.var_id_hi + 1)
        ):
            yield from flush_script(i)   

            # command changes wild_mod_val
            if cmd.assign_type == AssignType.SUBSTITUTE and cmd.operand_type_name == 'InvariantOperand':
                wild_mod_val = cmd.value
            elif cmd.assign_type == AssignType.SUBSTITUTE and cmd.operand_type_name == 'RandomNumberOperand':
                wild_mod_val = range(cmd.lb, cmd.ub + 1)
            elif cmd.assign_type == AssignType.ADD and cmd.operand_type_name == 'VariableOperand' and cmd.var_id == 779:
                # tabula rasa unown (var 120)
                pass
            else:
                assert False, cmd
        elif (
            cmd.short_type_name == 'ControlSwitches'
            and 540 in range(cmd.switch_id_lo, cmd.switch_id_hi + 1)
        ):
            yield from flush_script(i)

            # command changes egg_trade
            if cmd.state == SwitchState.ON:
                egg_trade = True
            else:
                egg_trade = False
        elif not script:
            # haven't found a script yet
            if (
                cmd.short_type_name == 'Script'
                and script_is_interesting(cmd.line)
            ):
                start_cmd = i
                script = cmd.line
            elif (
                cmd.short_type_name == 'ConditionalBranch'
                and cmd.short_subtype_name == 'Script'
                and script_is_interesting(cmd.expr)
            ):
                start_cmd = i
                script = cmd.expr
        elif script and appendix is None:
            # is there an appendix?
            if cmd.short_type_name == 'Script' and re.search(TRADE_MOD_RE, cmd.line) is not None:
                # yes but it's just an extra script
                appendix = cmd.line
                yield from flush_script(i + 1)
            elif (
                cmd.short_type_name == 'ControlVariables'
                and 62 in range(cmd.var_id_lo, cmd.var_id_hi + 1)
                and cmd.assign_type == AssignType.SUBSTITUTE
                and cmd.operand_type_name == 'RandomNumberOperand'
            ):
                appendix_start_cmd = i
                appendix = {outcome: '' for outcome in range(cmd.lb, cmd.ub + 1)}
            else:
                # no there isn't
                yield from flush_script(i)
        elif appendix is not None and appendix_cur_outcome is None:
            if (
                cmd.short_type_name == 'ConditionalBranch'
                and cmd.short_subtype_name == 'Variable'
                and cmd.variable_id == 62
                and not cmd.value_is_variable
                and cmd.cmp == Comparison.EQ
            ):
                appendix_cur_outcome = cmd.value
            else: 
                print(f'cancelling appendix: {appendix}')
                print(f'because: expected conditionalbranch, got {cmd}')
                appendix = None
                yield from flush_script(appendix_start_cmd)
        elif appendix_cur_outcome is not None and not appendix[appendix_cur_outcome]:
            if cmd.short_type_name == 'Script':
                appendix[appendix_cur_outcome] = cmd.line
            else:
                print(f'cancelling appendix: {appendix}')
                print(f'because: expected script, got {cmd}')
                appendix = None
                yield from flush_script(appendix_start_cmd)
        elif appendix_cur_outcome is not None and appendix[appendix_cur_outcome]:
            if cmd.short_type_name == 'Blank':
                pass
            elif cmd.short_type_name == 'Else':
                appendix_cur_outcome = None
            else: # cmd.short_type_name == 'ConditionalBranchEnd':
                yield from flush_script(i)

    yield from flush_script(i)

def iterscriptlines(script):
    delimiter_stack = []
    line = ''

    DELIMITER_MAP = {'(': ')', "'": "'", '"': '"'}

    for c in script:
        #print(c, delimiter_stack)
        if delimiter_stack:
            line += c

            delimiter = delimiter_stack[-1]

            if c == DELIMITER_MAP[delimiter]:
                delimiter_stack.pop()
            elif c in ('(', "'", '"'):
                delimiter_stack.append(c)
        else:
            if c in ('\n', ';'):
                yield line
                line = ''
            elif c in ('(', "'", '"'):
                line += c
                delimiter_stack.append(c)
            else:
                line += c

    if line:
        yield line

def extract():
    encounter_modifiers = parse_encounter_modifiers()
    rows = []
    common_event_rows = []
    map_event_rows = []
    form_note_rows = []
    ot_rows = []
    set_rows = []
    move_rows = []
    iv_rows = []

    next_id = 0

    def get_next_id():
        nonlocal next_id
        result = next_id
        next_id += 1
        return result

    next_set_id = 0

    def get_next_set_id():
        nonlocal next_set_id
        result = next_set_id
        next_set_id += 1
        return result

    def add_rows(datum):
        encounter_id = get_next_id()

        if 'map_id' in datum:
            map_event_rows.append((encounter_id, datum['map_id'], datum['event_id'], datum['event_page']))
        else:
            common_event_rows.append((encounter_id, datum['event_id']))

        if 'form_note' in datum:
            form = None
            form_note_rows.append((encounter_id, datum['form_note']))
        else:
            form = datum.get('form', 0)

        rows.append((
            encounter_id, datum['start_cmd'], datum['end_cmd'], datum['species'], form,
            datum.get('level'), datum['type'], datum.get('nickname'), datum.get('hp'), datum.get('gender'),
            datum.get('held_item'), datum.get('friendship'), datum.get('ability_slot'),
            datum.get('move_preference')
        ))

        if datum.get('ot'):
            ot_rows.append((encounter_id, datum['ot'], datum.get('trainer_id')))

        moves = datum.get('moves', [])

        if moves:
            if not isinstance(moves[0], list):
                moves = [moves]

            for set_ in moves:
                set_id = get_next_set_id()
                set_rows.append((set_id, encounter_id))

                for i, move in enumerate(set_):
                    move_rows.append((set_id, move, i))

        ivs = datum.get('iv', {})

        for stat_index, value in ivs.items():
            iv_rows.append((encounter_id, stat_index, value))

    def apply_modifiers(modifiers, datum):
        nonmovekeys = {k for m in modifiers for k in m.keys() if k != 'moves'}

        for k in nonmovekeys:
            assert len({m[k] for m in modifiers}) == 1, f'disparate values for key {k}; {modifiers}'

        datum['moves'] = [m['moves'] for m in modifiers]

        for k in nonmovekeys:
            datum[k] = modifiers[0][k]

    def parse_command_script(script, datum, wild_mod_val, egg_trade, appendix):
        start_cmd = datum['start_cmd']
        end_cmd = datum['end_cmd']

        m = re.search(WILD_RE, script)

        if m is not None:
            #datum['repeatable'] = 'var_id' not in m.groupdict() # tropius doesn't have this but i think ame regards this as a bug (based on what she said on her stream)
            datum['type'] = 'battle'
            datum['species'] = parse_species(m.groupdict()['species'])
            print(f"{start_cmd}--{end_cmd}: {datum['species']}, battle")
            datum['level'] = m.groupdict()['level']

            if wild_mod_val == 120: # tabula rasa unown
                datum['form_note'] = TABULA_RASA_UNOWN_FORM_NOTE

            return True

        m = re.search(GIFT_RE, script)

        if m is not None:
            datum['species'] = parse_species(m.groupdict()['species'])

            if datum['species'] == 'DARKRAI':
                # print('>>>>>>>DARKRAI')
                # print(script)
                # print('DARKRAI<<<<<<<<')
                return False # Ignore Shiv's fake Darkrai gift

            print(f"{start_cmd}--{end_cmd}: {datum['species']}, gift (maybe trade)")
            datum['level'] = m.groupdict()['level']
            poke_var = m.groupdict()['poke_var']

            for line in iterscriptlines(script[m.end():]):
                line = line.strip()

                if process_line(poke_var, line, datum):
                    continue

                m = re.match(fr'\s*pbStartTrade\s*\(\s*pbGet\(1\)\s*,\s*{poke_var}\s*,\s*"(?P<nickname>.*?)"\s*,\s*"(?P<ot>.*?)"\s*\)', line)

                if m is not None:
                    print('...is trade')
                    datum['type'] = 'trade'
                    datum['nickname'] = m.groupdict()['nickname']
                    datum['ot'] = m.groupdict()['ot']
                    datum['trainer_id'] = '$RANDOM'

                    if egg_trade:
                        datum['level'] = 0

                    continue

                if line == f'pbAddPokemon({poke_var})':
                    datum['type'] = 'gift'
                    print('...is gift')
                    continue

                assert False, f'unexpected line {line}; script:\n{script}'

            return True

        m = re.search(GIFT_RE2, script)

        if m is not None:
            species = m.groupdict()['species']

            if species == 'pbGet(16)': # fossil gift in spinel town --- handled separately
                return False
            else:
                datum['species'] = parse_species(species)
                print(f"{start_cmd}--{end_cmd}: {datum['species']}, gift")
                datum['level'] = m.groupdict()['level']
                datum['type'] = 'gift'        
                return True

        m = re.search(TRADE_RE, script)

        if m is not None:
            datum['type'] = 'trade'
            datum['species'] = parse_species(m.groupdict()['species'])
            print(f"{start_cmd}--{end_cmd}: {datum['species']}, trade")
            datum['nickname'] = m.groupdict()['nickname']
            datum['ot'] = m.groupdict()['ot']
            datum['trainer_id'] = '$RANDOM'

            if egg_trade:
                datum['level'] = 0

            if appendix and isinstance(appendix, str):
                m = re.search(TRADE_MOD_RE, appendix)
                assert m is not None, appendix
                poke_var = m.groupdict()['poke_var']

                for line in iterscriptlines(appendix[m.end():]):
                    if process_line(poke_var, line, datum):
                        continue

                    assert False, f'unexpected line {line}; script:\n{script}'

            return True

        m = re.search(EGG_RE, script)

        if m is not None:
            datum['species'] = parse_species(m.groupdict()['species'])
            print(f"{start_cmd}--{end_cmd}: {datum['species']}, egg gift")
            datum['level'] = 0
            poke_var = m.groupdict()['poke_var']

            for line in iterscriptlines(script[m.end():]):
                if process_line(poke_var, line, datum):
                    continue

                if line == f'pbAddPokemonSilent({poke_var})':
                    datum['type'] = 'gift'
                    continue

                assert False, f'unexpected line {line}; script:\n{script}'

            return True

        return False
        
    def process_commands(cmds, base_datum):
        for start_cmd, end_cmd, wild_mod_val, script, egg_trade, appendix in interesting_scripts(cmds):
            print('>>>>>>>>>>>', wild_mod_val, egg_trade)
            print(script)
            print('<<<<<<<<<<<')
            print(appendix)
            print('~~~~~~~~~~~')

            datum = base_datum.copy()
            datum['start_cmd'] = start_cmd
            datum['end_cmd'] = end_cmd

            if isinstance(wild_mod_val, range):
                modifiers = [encounter_modifiers[v] for v in wild_mod_val]
                apply_modifiers(modifiers, datum)
            elif wild_mod_val:
                datum |= encounter_modifiers[wild_mod_val]

            if parse_command_script(script, datum, wild_mod_val, egg_trade, appendix):
                if appendix and isinstance(appendix, dict):
                    modifiers = []

                    for outcome, outcomescript in appendix.items():
                        modifiers.append({})
                        lines = list(iterscriptlines(outcomescript))
                        m = re.match(r'(\w+)\s*=\s*pbGetPokemon\(1\)', lines[0])

                        if m is None:
                            assert False, f'unexpected line: {line}; in appendix outcome {outcome}, script: \n{script}'

                        poke_var = m.group(1)

                        for line in lines[1:]:
                            if not process_line(poke_var, line, modifiers[-1]):
                                assert False, f'unexpected line: {line}; in appendix outcome {outcome}, script: \n{script}'

                    apply_modifiers(modifiers, datum)

                add_rows(datum)

    for event in rpg_common_events.load():
        print(f'Common event {event.id_}')
        process_commands(event.list_, {'event_id': event.id_})

    # print(rows)
    # print(common_event_rows)
    # print(ot_rows)
    # print(move_rows)

    for map_id, map_ in rpg_map.Map.load_all():
    # for map_id, map_ in [
    #     #(353, rpg_map.Map.load(353)),
    #     #(11, rpg_map.Map.load(11)),
    #     #(153, rpg_map.Map.load(153)),
    #     #(412, rpg_map.Map.load(412)), # absol isn't picking up the wildmod
    #     (154, rpg_map.Map.load(154)) # mime jr isn't getting all its moves
    # ]:
        print(f'Map {map_id}')

        for event_id, event in map_.events.items():
            for page_number, page in enumerate(event.pages):
                #print(f'MAP {map_id}, EVENT {event_id}, PAGE {page_number}')
                process_commands(page.list_, {'map_id': map_id, 'event_id': event_id, 'event_page': page_number})

    with DB.H.transaction(foreign_keys_enabled=False):
        for table in (
             'event_encounter', 'encounter_common_event', 'encounter_map_event',
            'event_encounter_ot', 'event_encounter_extra_move_set', 'event_encounter_move',
            'event_encounter_form_note', 'event_encounter_iv'
        ):
            DB.H.exec(f'delete from {table}')

    with DB.H.transaction():
        DB.H.exec(f'drop table if exists "event_encounter_raw"')

        DB.H.dump_as_table(
            'event_encounter_raw',
            (
                'id', 'start_event_command', 'end_event_command', 'pokemon', 'form', 'level', 'type', 
                'nickname', 'hp', 'gender', 'held_item', 'friendship', 'ability', 'move_preference'
            ),
            rows
        )

        DB.H.exec(f'drop table if exists "event_encounter_iv_raw"')

        DB.H.dump_as_table(
            'event_encounter_iv_raw',
            ('encounter', 'stat', 'value'),
            iv_rows
        )

    with DB.H.transaction():
        DB.H.exec('''
            insert into "event_encounter" (
                "id", "start_event_command", "end_event_command", "pokemon", "form", "level", "type",
                "nickname", "hp", "gender", "held_item", "friendship", "ability", "move_preference"
            )
            select
                "raw"."id", "raw"."start_event_command", "raw"."end_event_command", "raw"."pokemon",
                "form"."name", "raw"."level", "raw"."type", "raw"."nickname", "raw"."hp", "raw"."gender",
                "raw"."held_item", "raw"."friendship", "raw"."ability" + 1, "raw"."move_preference"
            from "event_encounter_raw" as "raw"
            left join "pokemon_form" as "form" on (
                "form"."pokemon" = "raw"."pokemon" and "form"."order" = "raw"."form"
            )
        ''')

    with DB.H.transaction():
        DB.H.bulk_insert(
            'encounter_common_event',
            ('encounter', 'event'),
            common_event_rows
        )

    with DB.H.transaction():
        DB.H.bulk_insert(
            'encounter_map_event',
            ('encounter', 'map', 'event', 'event_page'),
            map_event_rows
        )

    with DB.H.transaction():
        DB.H.bulk_insert(
            'event_encounter_form_note',
            ('encounter', 'note'),
            form_note_rows
        )

    with DB.H.transaction():
        DB.H.bulk_insert(
            'event_encounter_ot',
            ('encounter', 'ot', 'trainer_id'),
            ot_rows
        )

    with DB.H.transaction():
        DB.H.bulk_insert(
            'event_encounter_extra_move_set',
            ('id', 'encounter'),
            set_rows
        )

    with DB.H.transaction():
        DB.H.bulk_insert(
            'event_encounter_move',
            ('set', 'move', 'index'),
            move_rows
        )

    with DB.H.transaction():
        DB.H.exec('''
            insert into "event_encounter_iv" ("encounter", "stat", "value")
            select
                "raw"."encounter", "stat"."id", "raw"."value"
            from "event_encounter_iv_raw" as "raw"
            join "stat" on "stat"."order" = "raw"."stat"
        ''')

if __name__ == '__main__':
    #print(parse_encounter_modifiers())
    extract()
