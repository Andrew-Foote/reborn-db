from copy import deepcopy
from fractions import Fraction as frac
import json
from pathlib import Path
import re
import jinja2
from slugify import slugify
from reborndb import DB
from reborndb import settings

URL_BASE = '/reborn-db-site'

def frac_mixed(x):
    q, r = divmod(frac(x), 1)
    
    return ' '.join([
        (str(q) if q else ''),
        (f'{r.numerator}&frasl;{r.denominator}' if r else '')
    ])

def gender_ratio(male_frequency):
    if male_frequency is None:
        return 'Genderless'

    genders = ('male', 'female')
    chances = (male_frequency, 1000 - male_frequency)
    parts = [f'{chance / 10:g}% {gender}' for gender, chance in zip(genders, chances) if chance]
    return ', '.join(parts)

def pokemon_form_name(pokemon, form):
    return pokemon + (f' ({form} Form)' if form else '')

def conjunction_join(conjunction, phrases):
    phrases = list(phrases)

    if not phrases:
        raise ValueError('no phrases to join')

    if len(phrases) == 1:
        return phrases[0]

    return ', '.join(phrases[:-1]) + ' ' + conjunction + ' ' + phrases[-1]

KIND_ORDER = (
    'item', 'level', 'gender', 'friendship', 'trademate', 'time', 'held_item', 'move', 'move_type',
    'weather', 'teammate', 'teammate_type', 'stat_cmp', 'map', 'leftover', 'cancel', 'coin_flip',
)

def describe_evolution_scheme_mapless(scheme):
    scheme = deepcopy(scheme)
    del scheme['requirements']['map']
    sentence = describe_evolution_scheme(scheme, 0, '', '', '', '')

    # we're getting extremely ugly here for the sake of English grammar
    m = re.match(r'^Use (an?) (<a href=".*?">.*?</a>)(.*)', sentence)

    if m is not None:
        article, item_name, rest = m.group(1, 2, 3)
        sentence = f'use {article} {item_name} on it{rest}'
    else:
        m = re.match(r'^Level(.*)', sentence)

        if m is not None:
            rest = m.group(1)
            sentence = f'level it{rest}'
        else:
            m = re.match(r'Trade(.*)', sentence)

            if m is not None:
                rest = m.group(1)
                sentence = f'trade it{rest}'
            else:
                raise RuntimeError(f'"{sentence}"? What on earth does that mean?')

    return sentence

def describe_evolution_scheme(scheme, scheme_index, from_name, from_form, to_name, to_form):
    sentence = {'level': 'Level up', 'item': 'Use', 'trade': 'Trade'}[scheme['base_method']]
    sorted_kinds = sorted(scheme['requirements'].keys(), key=lambda v: KIND_ORDER.index(v))

    for kind in sorted_kinds:
        vs = scheme['requirements'][kind]

        if kind == 'item':
            vs = [v[0] for v in vs]
            item_names = vs#get_names(vs, 'item')
            article = 'a' + ('n' if item_names[0][0].lower() in 'aeiou' else '')
            item_names = [f'<a href="{URL_BASE}/item/{slugify(name)}.html">{name}</a>' for name in item_names]
            sentence += f' {article} ' + conjunction_join('or', item_names)
        elif kind == 'level':
            assert len(vs) == 1
            sentence += f' to at least level {vs.pop()[0]}'
        elif kind == 'gender':
            assert len(vs) == 1
            sentence += f' as {vs.pop()[0].lower()}'
        elif kind == 'friendship':
            sentence += ' with at least 220 friendship'
        elif kind == 'trademate':
            vs = [v[0] for v in vs]
            pokemon_names = vs#get_names(vs, 'pokemon')
            pokemon_names = [f'<a href="{URL_BASE}/pokemon/{slugify(name)}.html">{name}</a>' for name in pokemon_names]
            sentence += ' in exchange for ' + conjunction_join('or', pokemon_names)
        elif kind == 'time':
            vnames = [v[0] for v in vs]
            vranges = [v[1] for v in vs]
            vs = [f'{vname} ({vrange})' for vname, vrange in zip(vnames, vranges)]
            sentence += ' during ' + conjunction_join('or', vs)
        elif kind == 'held_item':
            vs = [v[0] for v in vs]
            item_names = vs#get_names(vs, 'item')
            article = 'a' + ('n' if item_names[0][0].lower() in 'aeiou' else '')
            item_names = [f'<a href="{URL_BASE}/item/{slugify(name)}.html">{name}</a>' for name in item_names]
            sentence += f' holding {article} ' + conjunction_join('or', item_names)
        elif kind == 'move':
            vs = [v[0] for v in vs]
            move_names = vs#get_names(vs, 'move')
            move_names = [f'<a href="{URL_BASE}/move/{slugify(name)}.html">{name}</a>' for name in move_names]
            sentence += ' knowing ' + conjunction_join('or', move_names)
        elif kind == 'move_type':
            vs = [v[0] for v in vs]
            type_names = vs#get_names(vs, 'type')
            article = 'a' + ('n' if type_names[0][0].lower() in 'aeiou' else '')
            type_names = [f'<a href="{URL_BASE}/type/{slugify(name)}.html">{name}</a>-' for name in type_names]
            type_names = conjunction_join('or', type_names)
            sentence += f' knowing {article} {type_names}type move'
        elif kind == 'weather':
            vs = [v[0] for v in vs]
            sentence += ' during ' + conjunction_join('or', vs)
        elif kind == 'teammate':
            vs = [v[0] for v in vs]
            pokemon_names = vs#get_names(vs, 'pokemon')
            pokemon_names = [f'<a href="{URL_BASE}/pokemon/{slugify(name)}.html">{name}</a>' for name in pokemon_names]
            sentence += ' with ' + conjunction_join('or', pokemon_names) + ' in the party'
        elif kind == 'teammate_type':
            vs = [v[0] for v in vs]
            type_names = vs#get_names(vs, 'type')
            article = 'a' + ('n' if type_names[0][0].lower() in 'aeiou' else '')
            type_names = [f'<a href="{URL_BASE}/type/{slugify(name)}.html">{name}</a>-' for name in type_names]
            type_names = conjunction_join('or', type_names)
            sentence += f' with {article} {type_names}type Pokémon in the party'
        elif kind == 'stat_cmp':
            assert len(vs) == 1
            stat1, stat2, op = vs.pop()
            op = {'<': 'less than', '>': 'greater than', '=': 'equal to'}[op]
            sentence += f' with {stat1} {op} {stat2}'
        elif kind == 'map':
            scheme_id = '_'.join((*map(slugify, (from_name, from_form, to_name, to_form)), str(scheme_index)))

            if len(vs) == 1:
                map_id, map_name = vs.pop()
                sentence += f' in <a href="{URL_BASE}/area/{map_id}.html">map {map_id} ({map_name})</a>'
            else:
                sentence += f' in certain areas (<a href="{URL_BASE}/evolution_area/{scheme_id}.html">details</a>)'
        elif kind == 'leftover':
            sentence += ' with an empty slot in the party and a Poké Ball in the bag (replaces the empty slot rather than the original Pokémon)'
        elif kind == 'cancel':
            sentence += ' (evolution fails unless the player attempts to cancel it)'
        elif kind == 'coin_flip':
            sentence += ' (50% chance)'

    return sentence

jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))

jinja_env.filters |= {
    'slug': slugify,
    'gender_ratio': gender_ratio,
    'frac_mixed': frac_mixed
}

jinja_env.globals |= {
    'len': len,
    'pokemon_form_name': pokemon_form_name,
    'describe_evolution_scheme': describe_evolution_scheme,
    'describe_evolution_scheme_mapless': describe_evolution_scheme_mapless,
    'url_base': URL_BASE
}

def render_template(path, template, **args):
    path_obj = settings.SITE_PATH / Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    #print(str(path_obj))
    template_obj = jinja_env.get_template(template)
    content = template_obj.render(**args)

    with path_obj.open('w', encoding='utf-8') as f:
        f.write(content)
