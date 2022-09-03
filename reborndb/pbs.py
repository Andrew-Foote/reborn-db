# Parsers which load data from the PBS files into Python data structures.

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import partial
import re

def parse_bool(v):
    if v == 'true':
        return True

    if v == 'false':
        return False

    raise ValueError(f'cannot parse {v} as bool')

LOADER_MAP = {}

def load(name):
    return LOADER_MAP[name](name)

# The CSVs are the easiest to deal with...

# "connections.txt" and "trainers.txt" have comments in them, which we can safely ignore as they
# only contain redundant information
# "trainers.txt" might also need a second pass to structure it a bit more
def decomment(lines):
    for line in lines:
        # note that this will see hashes in quotes as the start of a comment
        # --fortunately I don't think any of the files use quotes
        line = re.match(r'\s*([^#]*)\s*(?:#.*)?', line).group(1)

        if line:
            yield line

def load_csv(name, **options):
    do_decomment = options.pop('decomment', True)

    with open(f'PBS/{name}.txt', newline='', encoding='utf-8') as f:
        return list(csv.reader((decomment(f) if do_decomment else f), **options))

for name in ('abilities', 'connections', 'items', 'moves', 'trainertypes'):
    LOADER_MAP[name] = load_csv

LOADER_MAP['btpokemon'] = partial(load_csv, delimiter=';')

# Some of the other files are basically INIs with some variations. I'm not sure if, or how
# configparser could be extended to handle them, so I'll just parse them myself.

@dataclass
class IniSection:
    header: str
    content: dict[str, str] = field(default_factory=dict)

class ParseError(Exception):
    pass

class IniParser:
    section_class = IniSection
    allow_duplicate_keys = False

    def __init__(self):
        self.result = []
        self.index = -1

    def parse_comment(self, comment):
        pass

    def parse_header(self, header):
        self.result.append(self.section_class(header=header))

    def parse_setting(self, key, value):
        if not self.result:
            raise ParseError(f'line {self.index}: setting before any section header')

        if key in self.result[-1].content:
            values = self.result[-1].content[key]

            if self.allow_duplicate_keys:
                if not isinstance(values, list):
                    values = [values]
                    self.result[-1].content[key] = values

                values.append(value)
            else:
                # there's a duplicate BattleBack in metadata.txt, so just make this a warning
                print(f'WARNING: duplicate key {key} at line {self.index}; ignoring values for all but first')
                #raise ParseError(f'line {self.index}: duplicate key {key}')
        else:
            self.result[-1].content[key] = value

    def parse_other(self, line):        
        raise ParseError(f'failed to parse line {self.index}')

    def parse(self, iterable):
        for i, line in enumerate(iterable):
            self.index = i
            line = line.strip()

            if not line:
                continue

            if (m := re.match(r'#(.*)', line)) is not None:
                self.parse_comment(m.group(1))
                continue

            if (m := re.match(r'\[(.*)\]', line)) is not None:
                self.parse_header(m.group(1))
                continue

            if (m := re.match(r'(\w+)=(.*)', line)) is not None:
                self.parse_setting(*m.group(1, 2))
                continue

            self.parse_other(line)

def load_ini(name, *, parser_class=IniParser, encoding='utf-8'):
    with open(f'PBS/{name}.txt', encoding=encoding) as f:
        parser = parser_class()
        parser.parse(f)
        return parser.result

for name in ('types', 'gen8pokemon', 'pokemon', 'trainerlists'):
    LOADER_MAP[name] = load_ini

# latin1 because it contains some és in Pokémon encoded as e9
LOADER_MAP['gen8pokemon'] = partial(load_ini, encoding='latin-1')

class TownMapParser(IniParser):
    allow_duplicate_keys = True

LOADER_MAP['townmap'] = partial(load_ini, parser_class=TownMapParser)

# A couple of them have useful information in comments immediately after the section headers.

@dataclass
class SectionWithComment:
    header: str
    comment: str = None
    content: dict[str, str] = field(default_factory=dict)

class IniWithSectionCommentsParser(IniParser):
    section_class = SectionWithComment

    def __init__(self):
        super().__init__()
        self.comment_meaningful = False

    def parse_header(self, header):
        super().parse_header(header)
        self.comment_meaningful = True

    def parse_comment(self, comment):
        if self.comment_meaningful:
            self.result[-1].comment = comment
            self.comment_meaningful = False

    def parse_setting(self, key, value):
        super().parse_setting(key, value)
        self.comment_meaningful = False

for name in ('bttrainers', 'metadata'):
    LOADER_MAP[name] = partial(load_ini, parser_class=IniWithSectionCommentsParser)

# tm.txt is a variant on the INI format which only has a single line under each section, which is
# a comma-separated set of values. It also has some above-section-level headers encoded as comments

@dataclass
class TMSection:
    header: str
    tm: str
    content: list[str] = None

class TMParser(IniParser):
    section_class = TMSection

    def __init__(self):
        super().__init__()
        self.state = 'initial'
        self.header = None

    def parse_comment(self, comment):
        comment = comment.strip()

        if self.state == 'initial':
            if set(comment.strip()) == {'='}:
                self.state = 'header_begin'
        elif self.state == 'header_begin':
            self.header = comment
            self.state = 'header_end'
        elif self.state == 'header_end':
            if not set(comment) == {'='}:
                raise ParseError(f'line {self.index}: expected a closing #==... line')

            self.state = 'initial'

    def parse_header(self, tm):
        if self.state != 'initial':
            raise ParseError(f'line {self.index}: not expecting a TM name here')

        self.result.append(self.section_class(header=self.header, tm=tm))
        self.state = 'want_pokemon_list'

    def parse_other(self, pokemon_list):
        if self.state != 'want_pokemon_list':
            raise ParseError(f'line {self.index}: not expecting a list of Pokémon here')

        self.result[-1].content = [pokemon.strip() for pokemon in pokemon_list.split(',')]
        self.state = 'initial'

LOADER_MAP['tm'] = partial(load_ini, parser_class=TMParser)

# shadowmoves.txt, trainers.txt and encounters.txt have their own unique formats
# the first is the simplest:

def load_shadowmoves(name):
    with open(f'PBS/{name}.txt', encoding='utf-8') as f:
        result = {}

        for line in f: 
            key, values = line.split('=')
            key = key.strip()
            values = [value.strip() for value in values.split(',')]
            result[key] = values

        return result

LOADER_MAP['shadowmoves'] = load_shadowmoves

# encounters.txt is something completely different

# def parse_encounters_file(f):
#     ftext = f.read()
    # state = 'expecting_hashes'
    # areas = {}
    # current_area_code = None
    # lineno = 0
    # lines = ftext.splitlines()

    # while lineno < len(lines):
    #     line = lines[lineno]

    #     if state == 'expecting_hashes':
    #         if re.match(r'#+', line) is None: 
    #             raise ValueError(f'line {lineno}: expecting hashes, instead got:\n{line}')

    #         lineno += 1
    #         state = 'expecting_area_info'

    #     elif state == 'expecting_area_info':
    #         parts = re.split(r'\s*#\s*', line)
    #         current_area_code = int(parts[0])
    #         area_name = parts[1]
    #         areas[current_area_code] = {'area_name': area_name}
    #         lineno += 1
    #         state = 'expecting_densities'

    #     elif state == 'expecting_densities':
    #         current_area = areas[current_area_code]

    #         if re.match(r'\d+,\d+,\d+', line) is None:
    #             # this is an optional line, default values are 25,10,10
    #             # (grass, cave, surf respectively)
    #             current_area['densities'] = [25, 10, 10]
    #             state = 'expecting_encounter_type'
    #         else:
    #             current_area['densities'] = list(map(int, line.split(',')))
    #             lineno += 1
    #             state = 'expecting_encounter_type'

    #     elif state == 'expecting_encounter_type':
    #         current_area = areas[current_area_code]

    #         if re.match(r'#+', line) is not None:
    #             # this area's done
    #             lineno += 1
    #             state = 'expecting_area_info'

    #         elif line not in ENCOUNTER_TYPES:
    #             raise ValueError(f'line {lineno}: expecting hashes or encounter type, instead got:\n{line}')

    #         else:
    #             if 'encounter_types' not in current_area:
    #                 current_area['encounter_types'] = {}

    #             if line in current_area['encounter_types']:
    #                 raise ValueError(f'line {lineno}: {line} encounters are defined more than once')

    #             current_area['encounter_types'][line] = []
    #             lineno += 1
    #             state = ['expecting_pokemon', line, 0]

    #     elif isinstance(state, list) and state[0] == 'expecting_pokemon':
    #         current_area = areas[current_area_code]
    #         encounter_type = state[1]
    #         slot_number = state[2]

    #         if slot_number < len(ENCOUNTER_TYPES[encounter_type]):
    #             if re.match(r'\w+,\d+(?:,\d+)?', line) is None:
    #                 raise ValueError(f'line {lineno}: expecting pokemon for slot {slot_number} in {encounter_type}, instead got:\n{line}')
    #             parts = line.split(',')
    #             pokemon = parts[0]
    #             min_level = int(parts[1])
    #             max_level = int(parts[2]) if len(parts) >= 3 else min_level
    #             current_area['encounter_types'][encounter_type].append([pokemon, min_level, max_level])
    #             lineno += 1
    #             state = ['expecting_pokemon', encounter_type, slot_number + 1]
    #         else:
    #             state = 'expecting_encounter_type'

    # return areas

# def load_encounters(name):
#     with open(f'PBS/{name}.txt', encoding='utf-8') as f:
#         return parse_encounters_file(f)

# LOADER_MAP['encounters'] = load_encounters

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

def postprocess_encounters(rows):
    areas = {}
    state = 'expecting_hashes'
    current_area_code = None
    current_area = {}
    current_enctype = None
    pokemon_index = None

    for i, row in enumerate(rows):
        if state == 'expecting_hashes':
            if len(row) != 1 or re.match(r'#+', row[0]) is None: 
                raise ValueError(f'row {i}: expecting hashes, instead got:\n{row}')

            state = 'expecting_area_info'
            continue

        if state == 'expecting_area_info':
            m = re.match(r'(\d+).*?', row[0])
            assert m is not None
            current_area_code = int(m.group(1))
            current_area = {'encounter_types': defaultdict(lambda: [])}
            areas[current_area_code] = current_area
            state = 'expecting_densities'
            continue
        
        if state == 'expecting_densities':
            try:
                current_area['densities'] = list(map(int, row))
            except ValueError:
                # this is an optional line, default values are 25,10,10
                # (grass, cave, surf respectively)
                current_area['densities'] = [25, 10, 10]
                state = 'expecting_encounter_type'
                # fallthrough, don't go to next line
            else:
                state = 'expecting_encounter_type'
                continue

        if state == 'expecting_encounter_type':
            enctype, = row

            if re.match(r'#+', enctype) is not None: # this area's done
                state = 'expecting_area_info'
                continue
            elif enctype not in ENCOUNTER_TYPES:
                raise ValueError(f'row {i}: expecting hashes or encounter type, instead got:\n{row[0]}')
            else:
                if enctype in current_area['encounter_types']:
                    raise ValueError(f'row {i}: {enctype} encounters are defined more than once')

                current_enctype = enctype
                state = 'expecting_pokemon'
                pokemon_index = 0
                continue

        if state == 'expecting_pokemon':
            assert len(row) in (2, 3)
            pokemon, min_level = row[:2]
            max_level = row[2] if len(row) == 3 else min_level
            current_area['encounter_types'][current_enctype].append([pokemon, int(min_level), int(max_level)])
            pokemon_index += 1

            if pokemon_index == len(ENCOUNTER_TYPES[current_enctype]):
                state = 'expecting_encounter_type'

    return areas

def postprocess_trainers(rows):
    state = 'expecting_trainer_type_id'
    trainers = {}
    current_trainer_id = [None, None, None]
    current_trainer = None
    current_team_size = None
    current_pokemon_index = None

    for i, row in enumerate(rows):
        if state == 'expecting_trainer_type_id':
            current_trainer_id[0], = row
            state = 'expecting_trainer_name'
        elif state == 'expecting_trainer_name':
            try:
                current_trainer_id[1], current_trainer_id[2] = row
            except ValueError:
                current_trainer_id[1], current_trainer_id[2] = *row, '0'

            current_trainer_id[0] = current_trainer_id[0].strip()
            current_trainer_id[1] = current_trainer_id[1].strip()
            current_trainer_id[2] = int(current_trainer_id[2])
            current_trainer = {}
            trainers[tuple(current_trainer_id)] = current_trainer
            state = 'expecting_team_size_and_items'
        elif state == 'expecting_team_size_and_items':
            current_team_size, *items = row
            current_team_size = int(current_team_size)
            current_trainer['items'] = dict(Counter(item for item in items if item))
            current_trainer['pokemon'] = []
            current_pokemon_index = 0
            state = 'expecting_pokemon'
        elif state == 'expecting_pokemon' and current_pokemon_index < current_team_size:
            id_, level, *row = row

            # corrections... there are a lot of these
            if current_trainer_id == ['Victoria', 'Victoria', 5] and current_pokemon_index == 2:
                # Mienfoo's form index is set to 1, but Mienfoo only has 1 form
                row[7] = ''
            elif current_trainer_id == ['SHELLY', 'Shelly', 2] and current_pokemon_index == 1:
                # Vivillon's form index is set to 2, but Vivillon only has 1 from (unless this is
                # meant to trigger one of the patterns somehow?)
                row[7] = ''
            elif current_trainer_id == ['SHELLY', 'Shelly', 3] and current_pokemon_index == 1:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['TERRA', 'T3RR4', 0] and current_pokemon_index == 2:
                # Excadrill's form index is set to 1, but Excadrill only has 1 form
                row[7] = ''
            elif current_trainer_id == ['TERRA', 'T3RR4', 1] and current_pokemon_index == 0:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['TERRA', 'T3RR4', 1] and current_pokemon_index == 1:
                # Donphan's friendship is set to 'JESUS', which was presumably intended to be the
                # nickname, I guess nobody noticed because Terra switches off the fonts for this
                # fight
                row[11] = ''
            elif current_trainer_id == ['CIEL', 'Ciel', 0] and current_pokemon_index == 3:
                # Gliscor's form index is set to 1, but Gliscor only has 1 form
                row[7] = ''
            elif current_trainer_id == ['AMARIA1', 'Amaria', 0] and current_pokemon_index == 0:
                # Starmie's form index is set to 1, but Starmie only has 1 form
                row[7] = ''
            elif current_trainer_id == ['AMARIA2', 'Amaria', 0] and current_pokemon_index == 0:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['AMARIA2', 'Amaria', 2] and current_pokemon_index == 0:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['LUCARIO', 'Pariah', 0] and current_pokemon_index == 0:
                # Lucario's gender is set to 1, when it should be "M" or "F"; Pokémon Reborn wiki
                # tells me this Lucario is female
                row[6] = 'F'
            elif current_trainer_id == ['ADRIENN', 'Adrienn', 11] and current_pokemon_index == 4:
                # Magearna's gender is set to 'Rhosyln', which was presumably intended to be the
                # nickname; it's genderless anyway
                row[6] = ''
            elif current_trainer_id == ['ACEALLSUITS', 'Ace of All Suits', 14] and current_pokemon_index == 2:
                # Bronzong's form is set to 'O', looks like a typo for 0 (Bronzong only has one
                # form anyway)
                row[7] = '0' # letter 'O' instead of number
            elif current_trainer_id == ['LIN', 'Lin', 0] and current_pokemon_index == 5:
                # Abara's form index is set to 2, it should be 1 (MultipleForms.rb does define both
                # 1 and 2 as PULSE forms with identical attributes, I've merged them for the
                # database)
                row[7] = '1'
            elif current_trainer_id == ['LIN', 'Lin', 1] and current_pokemon_index == 5:
                # same as above
                row[7] = '1'
            elif current_trainer_id == ['LIN', 'Lin', 3] and current_pokemon_index == 1:
                # Flygon's form index is set to 1, but Flygon only has 1 form
                row[7] = ''
            elif current_trainer_id == ['CORINROUGE', 'Corin-Rouge', 0] and current_pokemon_index == 2:
                # Liepard's form index is set to 1, but Liepard only has 1 form
                row[7] = ''
            elif current_trainer_id == ['CORINROUGE', 'Corin-Rouge', 1] and current_pokemon_index == 2:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['COOLTRAINER_Female', 'Carol', 0] and current_pokemon_index == 2:
                # Furfrou's form index is set to 9, but Furfrou only has 1 form
                # (or maybe it does and I just still don't quite understand how these form mappings work)
                row[7] = ''
            elif current_trainer_id == ['COOLTRAINER_Female', 'Carol', 1] and current_pokemon_index == 2:
                # Furfrou's form index is set to 8
                row[7] = ''
            elif current_trainer_id == ['COOLTRAINER_Female', 'Carol', 2] and current_pokemon_index == 3:
                # Furfrou's form index is set to 6
                row[7] = ''
            elif current_trainer_id == ['COOLTRAINER_Female', 'Carol', 4] and current_pokemon_index == 3:
                # Furfrou's form index is set to 5
                row[7] = ''
            elif current_trainer_id == ['CASS', 'Cass', 2] and current_pokemon_index == 0:
                # Naganadel's form index is set to 2, but Naganadel only has 1 form
                row[7] = ''
            elif current_trainer_id == ['TAPUKOKO', 'Tapu-Koko', 0] and current_pokemon_index == 2:
                # Genesect's form index is set to 1, but Genesect only has 1 form
                # (unless this is another Furfrou case)
                # comments say it has shock drive
                row[7] = ''
            elif current_trainer_id == ['GENESECT', 'Genesect', 2] and current_pokemon_index == 4:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['GENESECT', 'Genesect', 3] and current_pokemon_index == 4:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['GENESECT', 'Genesect', 4] and current_pokemon_index == 5:
                # Genesect's form index is set to 3
                # comments say it haas chill drive
                row[7] = ''
            elif current_trainer_id == ['GENESECT', 'Genesect', 5] and current_pokemon_index == 5:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['GENESECT', 'Genesect', 6] and current_pokemon_index == 5:
                # Genesect's form index is set to 2
                # comments say it has burn drive
                row[7] = ''
            elif current_trainer_id == ['GENESECT', 'Genesect', 7] and current_pokemon_index == 5:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['GENESECT', 'Genesect', 8] and current_pokemon_index == 5:
                # Genesect's form index is set to 4
                # comments say it has douse drive
                row[7] = ''
            elif current_trainer_id == ['GENESECT', 'Genesect', 9] and current_pokemon_index == 5:
                # same as above
                row[7] = ''
            elif current_trainer_id == ['CAMERUPT', 'Camerupt', 0] and current_pokemon_index == 3:
                # Klefki's form index is set to 1, but Klefki only has 1 form
                row[7] = ''
            elif current_trainer_id == ['TITANIA1', 'Titania', 1] and current_pokemon_index == 1:
                # Celesteela's form index is set to 1, but Celesteela only has 1 form
                row[7] = ''
            elif current_trainer_id == ['DIALGA', 'Dialga', 0] and current_pokemon_index == 4:
                # Keldeo's form index is set to 1, but Keldeo only has 1 form
                row[7] = ''
            elif current_trainer_id == ['Taka2', 'Taka', 1] and current_pokemon_index == 0:
                # Infernape's form index is set to 1, but Infernape only has 1 form
                row[7] = ''
            elif current_trainer_id == ['Taka2', 'Taka', 1] and current_pokemon_index == 4:
                # Blacephalon's form index is set to 2, but Blacephalon only has 1 form
                row[7] = ''
            elif current_trainer_id == ['ZEL3', 'Zero', 0] and current_pokemon_index == 3:
                # Dodrio's form index is set to 1, but Dodrio only has 1 form
                row[7] = ''
            elif current_trainer_id == ['BRELOOM', 'CL:4R1-C3', 1000] and current_pokemon_index == 0:
                # Genesect's form index is set to 4, but Genesect only has 1 form
                row[7] = ''
            # there are yet more... I give up

            current_trainer['pokemon'].append({
                'id': id_, 'level': level,
                'item': row[0] if len(row) >= 1 and row[0] else None,
                'moves': sum([[move.strip()] if move else [] for move in row[1:5]], start=[]),
                # plus 1 on the ability cos their indexes start from 0 while ours start at 1
                'ability': int(row[5]) + 1 if len(row) >= 6 and row[5] else None,
                'gender': {'M': 'Male', 'F': 'Female', 'U': 'Genderless'}[row[6]] if len(row) >= 7 and row[6] else None,
                'form': int(row[7]) if len(row) >= 8 and row[7] else 0,
                'shiny': len(row) >= 9 and row[8] == 'true',
                'nature': row[9] if len(row) >= 10 and row[9] else None,
                'ivs': int(row[10]) if len(row) >= 11 and row[10] else 10,
                'friendship': int(row[11]) if len(row) >= 12 and row[11] else 70,
                'nickname': row[12] if len(row) >= 13 and row[12] else None,
                'shadow': len(row) >= 14 and row[13] == 'true',
                'ball': row[14] if len(row) >= 15 and row[14] else 0,
                'hidden_power': row[15] if len(row) >= 16 and row[15] else 17, # this might not actually do anything
                'evs': {
                    'HP': int(row[16]) if len(row) >= 17 and row[16] else 0,
                    'ATK': int(row[17]) if len(row) >= 18 and row[17] else 0,
                    'DEF': int(row[18]) if len(row) >= 19 and row[18] else 0,
                    'SPD': int(row[19]) if len(row) >= 20 and row[19] else 0,
                    'SA': int(row[20]) if len(row) >= 21 and row[20] else 0,
                    'SD': int(row[21]) if len(row) >= 22 and row[21] else 0,
                }
            })

            current_pokemon_index += 1

            if current_pokemon_index == current_team_size:
                state = 'expecting_trainer_type_id'

    return trainers

LOADER_MAP['encounters'] = lambda name: postprocess_encounters(load_csv(name, decomment=False))
LOADER_MAP['trainers'] = lambda name: postprocess_trainers(load_csv(name))
