import apsw
from collections import defaultdict
from fractions import Fraction as frac
import functools as ft
import jinja2
import json
import operator
from pathlib import Path
import re
import slugify
from reborndb import apsw_ext

def frac_mixed(x):
    q, r = divmod(frac(x), 1)
    
    return ' '.join([
        (str(q) if q else ''),
        (f'{r.numerator}&frasl;{r.denominator}' if r else '')
    ])

def run():
    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
    jinja_env.filters['slug'] = slugify.slugify
    jinja_env.filters['frac_mixed'] = frac_mixed

    def render_template(name, **args):
        return jinja_env.get_template(name).render(**args)

    apsw_ext.init()
    db = apsw_ext.connect()

    print('db connected')

    # def get_evolution_root(pokemon_id):
    #   """Return the ID of the first Pokémon in the evolution tree of the one with the ID
    #   `pokemon_id`, or `None` if it does not belong to any evolution tree."""
    #   result = pokemon_id

    #   while (evolves_from := list(db.cursor().execute(
    #       'select "evolves_from" from "pokemon" where "id" = ?', 
    #       (result,)
    #   ))[0][0]) is not None:
    #       result = evolves_from

    #   if result == pokemon_id: # didn't find any Pokémon earlier in the evolutionary chain
    #       if not list(db.cursor().execute(
    #           'select "id" from "pokemon" where "evolves_from" = ?',
    #           (result,)
    #       )): # there are no Pokémon later in the evolutionary chain either
    #           result = None

    #   return result

    def get_evolution_root(pokemon, form):
        """Return the ID of the first Pokémon in the evolution tree of the one with the ID
        `pokemon_id`, or `None` if it does not belong to any evolution tree."""
        result = pokemon, form

        while (evolves_from := list(db.cursor().execute('''
            select "pem"."from", "pem"."from_form"
            from "pokemon_evolution_method" as "pem"
            where "pem"."to" = ? and "pem"."to_form" = ?
        ''', result))):
            result = evolves_from[0]

        if result == (pokemon, form): # didn't find any Pokémon earlier in the evolutionary chain
            if not list(db.cursor().execute('''
                select exists (
                    select 1
                    from "pokemon_evolution_method" as "pem"
                    where "pem"."from" = ? and "pem"."from_form" = ?
                )
            ''', result))[0][0]:
                # there are no Pokémon later in the evolutionary chain either
                result = None

        return result

    def get_evolution_tree(root_id, form_name):
        tree = {'root': {'id': root_id, 'form': form_name}, 'branches': defaultdict(lambda: {'methods': []})}
        tree['root']['name'] = list(db.cursor().execute('select "name" from "pokemon" where "id" = ?', (root_id,)))[0][0]

        ungrouped_branches = list(db.cursor().execute('''
            select "pem"."to", "pem"."to_form", "pem"."method"
            from "pokemon_evolution_method" as "pem"
            join "pokemon" on "pokemon"."id" = "pem"."to"
            where "pem"."from" = ? and "pem"."from_form" = ?
            order by "pokemon"."number"
        ''', (root_id, form_name)))

        for pokemon, form, method in ungrouped_branches:
            tree['branches'][pokemon, form]['methods'].append(method)

        for (pokemon, form), branch in tree['branches'].items():
            # we need to look at the methods array
            # select method, requirements for each of those
            # see if we can consolidate with ORs

            branch['methods'] = describe_method(branch['methods'], pokemon, form)
            branch['result'] = get_evolution_tree(pokemon, form)

        tree['branches'] = list(tree['branches'].values())

        return tree

    def conjunction_join(conjunction, phrases):
        phrases = list(phrases)

        if not phrases:
            raise ValueError('no phrases to join')

        if len(phrases) == 1:
            return phrases[0]

        return ', '.join(phrases[:-1]) + ' ' + conjunction + ' ' + phrases[-1]

    def describe_method(method_ids, pokemon, form):
        methods = [
            {'id': id_, 'base_method': base_method, 'requirement_kind': requirement_kind}
            for id_, base_method, requirement_kind
            in db.cursor().execute(
                '''
                    select "method"."id", "method"."base_method", "requirement"."kind"
                    from "evolution_method" as "method"
                    join "evolution_requirement" as "requirement" on "requirement"."method" = "method"."id"
                    where "method"."id" in ({})
                '''.format(', '.join('?' for _ in method_ids)),
                method_ids
            )
        ]

        grouped_by_method_id = defaultdict(lambda: {'requirements': {}})

        for method in methods:
            if method['id'] not in grouped_by_method_id:
                grouped_by_method_id[method['id']]['base_method'] = method['base_method']
                grouped_by_method_id[method['id']]['requirements'][method['requirement_kind']] = ()

        grouped_by_requirement_kind = defaultdict(lambda: [])

        for method in methods:
            grouped_by_requirement_kind[method['requirement_kind']].append(method)

        for kind, methods in grouped_by_requirement_kind.items():
            if list(db.cursor().execute(
                'select exists (select 1 from "sqlite_master" where "type" = ? and "name" = ?)',
                ('table', f'evolution_requirement_{kind}')
            ))[0][0]:
                for method_id, _, *args in db.cursor().execute(
                    '''
                        select * from "evolution_requirement_{}"
                        where "method" in ({})
                    '''.format(kind, ', '.join('?' for _ in methods)),
                    [method['id'] for method in methods]
                ):
                    grouped_by_method_id[method_id]['requirements'][kind] = tuple(args)

        grouped_by_base_method = defaultdict(lambda: {})

        for method_id, method in grouped_by_method_id.items():
            grouped_by_base_method[method['base_method']][method_id] = method

        schemes = []

        for method_id, method in grouped_by_method_id.items():
            # does its "scheme" match one of those we already have?
            # the scheme consists of requirement keys mapped to sets of values
            # a scheme match is where the keys match, and appending the new method's values
            # does not result in more than one set having size > 1
            for i, scheme in enumerate(schemes):
                if (
                    scheme['base_method'] == method['base_method']
                    and set(scheme['requirements'].keys()) == set(method['requirements'].keys())
                ):
                    new_requirements = {k: v | {method['requirements'][k]} for k, v in scheme['requirements'].items()}

                    if len([vs for vs in new_requirements.values() if len(vs) > 1]) <= 1:
                        scheme['requirements'] = new_requirements
                        break
            else:
                # no match found for any existing scheme, so make a new scheme
                schemes.append({
                    'base_method': method['base_method'],
                    'requirements': {kind: {v} for kind, v in method['requirements'].items()}
                })

        sentences = []

        KIND_ORDER = (
            'item', 'level', 'gender', 'friendship', 'trademate', 'time', 'held_item', 'move', 'move_type',
            'weather', 'teammate', 'teammate_type', 'stat_cmp', 'map', 'leftover', 'cancel', 'coin_flip',
        )

        for scheme_index, scheme in enumerate(schemes):    
            # multiplex_kind = list(scheme['requirements'].keys())[0]
            # this might not be necessary
            # for k, vs in scheme['requirements'].items():
            #   if len(vs) > 1:
            #       multiplex_kind = k

            sentence = {'level': 'Level up', 'item': 'Use', 'trade': 'Trade'}[scheme['base_method']]
            sorted_kinds = sorted(scheme['requirements'].keys(), key=lambda v: KIND_ORDER.index(v))
            
            def get_names(ids, table, name_col='name', id_col='id'):
                placeholders = ', '.join('?' for _ in ids)

                return [name for name, in db.cursor().execute(
                    f'select "{name_col}" from "{table}" where "{id_col}" in ({placeholders})',
                    ids
                )]

            for kind in sorted_kinds:
                vs = scheme['requirements'][kind]

                if kind == 'item':
                    vs = [v[1] for v in vs]
                    item_names = get_names(vs, 'item')
                    article = 'a' + ('n' if item_names[0][0].lower() in 'aeiou' else '')
                    item_names = [f'<a href="/item/{slugify.slugify(name)}.html">{name}</a>' for name in item_names]
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
                    vs = [v[1] for v in vs]
                    pokemon_names = get_names(vs, 'pokemon')
                    pokemon_names = [f'<a href="/pokemon/{slugify.slugify(name)}.html">{name}</a>' for name in pokemon_names]
                    sentence += ' in exchange for ' + conjunction_join('or', pokemon_names)
                elif kind == 'time':
                    vs = [v[0] for v in vs]
                    sentence += ' during ' + conjunction_join('or', get_names(vs, 'time_of_day', 'desc', 'name'))
                elif kind == 'held_item':
                    vs = [v[0] for v in vs]
                    item_names = get_names(vs, 'item')
                    article = 'a' + ('n' if item_names[0][0].lower() in 'aeiou' else '')
                    item_names = [f'<a href="/item/{slugify.slugify(name)}.html">{name}</a>' for name in item_names]
                    sentence += f' holding {article} ' + conjunction_join('or', item_names)
                elif kind == 'move':
                    vs = [v[0] for v in vs]
                    move_names = get_names(vs, 'move')
                    move_names = [f'<a href="/move/{slugify.slugify(name)}.html">{name}</a>' for name in move_names]
                    sentence += ' knowing ' + conjunction_join('or', move_names)
                elif kind == 'move_type':
                    vs = [v[0] for v in vs]
                    type_names = get_names(vs, 'type')
                    article = 'a' + ('n' if type_names[0][0].lower() in 'aeiou' else '')
                    type_names = [f'<a href="/type/{slugify.slugify(name)}.html">{name}</a>-' for name in type_names]
                    type_names = conjunction_join('or', type_names)
                    sentence += f' knowing {article} {type_names}type move'
                elif kind == 'weather':
                    vs = [v[0] for v in vs]
                    sentence += ' during ' + conjunction_join('or', get_names(vs, 'weather', 'desc', 'name'))
                elif kind == 'teammate':
                    vs = [v[0] for v in vs]
                    pokemon_names = get_names(vs, 'pokemon')
                    pokemon_names = [f'<a href="/pokemon/{slugify.slugify(name)}.html">{name}</a>' for name in pokemon_names]
                    sentence += ' with ' + conjunction_join('or', pokemon_names) + ' in the party'
                elif kind == 'teammate_type':
                    vs = [v[0] for v in vs]
                    type_names = get_names(vs, 'type')
                    article = 'a' + ('n' if type_names[0][0].lower() in 'aeiou' else '')
                    type_names = [f'<a href="/type/{slugify.slugify(name)}.html">{name}</a>-' for name in type_names]
                    type_names = conjunction_join('or', type_names)
                    sentence += f' with {article} {type_names}type Pokémon in the party'
                elif kind == 'stat_cmp':
                    assert len(vs) == 1
                    stat1, stat2, op = vs.pop()
                    stat1, stat2 = get_names((stat1, stat2), 'stat')
                    op = {'<': 'less than', '>': 'greater than', '=': 'equal to'}
                    sentence += f' with {stat1} {op} {stat2}'
                elif kind == 'map':
                    vs = [v[0] for v in vs]
                    pokemon_name, = get_names([pokemon], 'pokemon')
                    pokemon_slug = slugify.slugify(pokemon_name)
                    form_slug = slugify.slugify(form)
                    sentence_without_map_cond = sentence

                    # we're getting extremely ugly here for the sake of English grammar
                    m = re.match(r'^Use (an?) (<a href=".*?">.*?</a>)(.*)', sentence_without_map_cond)

                    if m is not None:
                        article, item_name, rest = m.group(1, 2, 3)
                        sentence_without_map_cond = f'use {article} {item_name} on it{rest}'
                    else:
                        m = re.match(r'^Level(.*)', sentence_without_map_cond)

                        if m is not None:
                            rest = m.group(1)
                            sentence_without_map_cond = f'level it{rest}'
                        else:
                            m = re.match(r'Trade(.*)', sentence_without_map_cond)

                            if m is not None:
                                rest = m.group(1)
                                sentence_without_map_cond = f'trade it{rest}'
                            else:
                                raise RuntimeError(f'"{sentence_without_map_cond}"? What on earth does that mean?')

                    sentence += f' in certain areas (<a href="/evolution_area/{pokemon_slug}/{form_slug}/{scheme_index}.html">details</a>)'

                    # horrendously ugly code follows. there's definitely a better way to organize this
                    # but I'm too lazy at the moment
                    @controller(f'evolution_area/{pokemon_slug}/{form_slug}/{scheme_index}.html')
                    def _(vs=vs):
                        from_forms = list(db.cursor().execute('''
                            select distinct "pokemon"."name", "pem"."from_form" from "pokemon_evolution_method" as "pem"
                            join "pokemon" on "pokemon"."id" = "pem"."from"
                            where "pem"."to" = ? and "pem"."to_form" = ?
                        ''', (pokemon, form)))

                        from_forms = [
                            (
                                f'<a href="/pokemon/{pokemon_name}.html#{form_name}">{pokemon_name}'
                                + (f' ({form_name} Form)' if form_name else '')
                                + '</a>'
                            )
                            for pokemon_name, form_name in from_forms
                        ]

                        from_forms_string = conjunction_join('or', from_forms)
                        map_names = get_names(vs, 'map')

                        return render_template(
                            'evolution_area.jinja2', to_name=pokemon_name, to_form=form,
                            from_forms_string=from_forms_string, scheme_desc=sentence_without_map_cond,
                            maps=[{'id': id_, 'name': name} for id_, name in zip(vs, map_names)]
                        )
                elif kind == 'leftover':
                    sentence += ' with an empty slot in the party and a Poké Ball in the bag (replaces the empty slot rather than the original Pokémon)'
                elif kind == 'cancel':
                    sentence += ' (evolution fails unless the player attempts to cancel it)'
                elif kind == 'coin_flip':
                    sentence += ' (50% chance)'

            sentences.append(sentence)

        return sentences

    WRITERS = []

    def controller(path):
        def decorator(fun):
            @ft.wraps(fun)
            def wrapped():
                path_obj = 'site' / Path(path)
                path_obj.parent.mkdir(parents=True, exist_ok=True)

                with path_obj.open('w', encoding='utf-8') as f:
                    content = fun()
                    f.write(content)

            WRITERS.append(wrapped)
            wrapped._reborn_db_path = path
            return wrapped
        return decorator

    @controller('index.html')
    def _():
        return render_template('index.jinja2')

    @controller('pokemon.html')
    def _():
        with db:
            pokemons = [{'number': number, 'name': name} for number, name in db.cursor().execute(
                'select `number`, `name` from pokemon order by `number`'
            )]

        return render_template('pokemon_list.jinja2', pokemons=pokemons)

    def display_gender_ratio(male_chance):
        if male_chance is None:
            return 'Genderless'

        genders = ('male', 'female')
        chances = (male_chance, 1000 - male_chance)
        parts = [f'{chance / 10:g}% {gender}' for gender, chance in zip(genders, chances) if chance]
        return ', '.join(parts)

    WILD_HELD_ITEM_RARITY_TO_PERCENTAGE = {
        'Common': 50,
        'Uncommon': 5,
        'Rare': 1,
    }

    print('generating pokemon pages')

    with db:
        for id_, name in db.cursor().execute('select "id", "name" from "pokemon" order by "number"'):
            slug = slugify.slugify(name)

            @controller(f'pokemon/{slug}.html')
            def _(id_=id_, name=name):
                with db:
                    pokemon = [
                        {
                            'number': number, 'id': id_, 'name': name, 'category': category, 
                            'gender_ratio': display_gender_ratio(male_chance),
                            'hatch_steps': hatch_steps, 'base_friendship': base_friendship, 'base_exp': base_exp,
                            'growth_rate': growth_rate
                        }
                        for number, id_, name, category, male_chance, hatch_steps, base_friendship, base_exp, growth_rate
                        in db.cursor().execute(
                            '''select "pokemon"."number", "pokemon"."id", "pokemon"."name", "category", "male_frequency",
                            "hatch_steps", "base_friendship", "base_exp", "growth_rate"."name"
                            from "pokemon" join "growth_rate" on "growth_rate"."name" = "pokemon"."growth_rate"
                            where "pokemon"."id" = ?''',
                            (id_,)
                        )
                    ]

                    assert len(pokemon) == 1
                    pokemon = pokemon[0]

                    pokemon['egg_groups'] = [{'name': name} for name, in db.cursor().execute('''
                        select "name" from "egg_group"
                        join "pokemon_egg_group" on "pokemon_egg_group"."egg_group" = "egg_group"."name"
                        where "pokemon_egg_group"."pokemon" = ?
                    ''', (pokemon['id'],))]

                    prev_pokemon = [{'number': number, 'name': name} for number, name in db.cursor().execute(
                        'select "number", "name" from "pokemon" where "number" + 1 = ?',
                        (pokemon['number'],)
                    )]

                    assert len(prev_pokemon) <= 1
                    prev_pokemon = prev_pokemon[0] if prev_pokemon else None

                    next_pokemon = [{'number': number, 'name': name} for number, name in db.cursor().execute(
                            'select "number", "name" from "pokemon" where "number" - 1 = ?',
                            (pokemon['number'],)
                    )]

                    assert len(next_pokemon) <= 1
                    next_pokemon = next_pokemon[0] if next_pokemon else None

                    forms = [
                        {
                            'name': name, 'index': index, 'type1': type1_id, 'type2': type2_id,
                            'ability1': {'name': ability1_name, 'desc': ability1_desc}, 'ability2': {'name': ability2_name, 'desc': ability2_desc},
                            'hidden_ability': {'name': hidden_ability_name, 'desc': hidden_ability_desc},
                            'height_m': height / 100, 'height_inches': round(height * 0.3937),
                            'weight_kg': weight / 10, 'weight_pounds': round(weight * 0.2205),
                            'catch_rate': catch_rate, 'pokedex_entry': pokedex_entry, 'wild_always_held_item': wild_always_held_item,
                            'base_hp': base_hp, 'base_atk': base_atk, 'base_def': base_def, 'base_spe': base_spe, 'base_sa': base_sa, 'base_sd': base_sd, 'bst': bst,
                            'hp_ev': hp_ev or 0, 'atk_ev': atk_ev or 0, 'def_ev': def_ev or 0, 'spe_ev': spe_ev or 0, 'sa_ev': sa_ev or 0, 'sd_ev': sd_ev or 0,
                            'evtot': evtot
                        }
                        for (
                            name, index, type1_id, type2_id, ability1_name, ability1_desc, ability2_name, ability2_desc,
                            hidden_ability_name, hidden_ability_desc,
                            height, weight, catch_rate, pokedex_entry, wild_always_held_item,
                            base_hp, base_atk, base_def, base_spe, base_sa, base_sd, bst, hp_ev, atk_ev, def_ev, spe_ev,
                            sa_ev, sd_ev, evtot
                        ) in db.cursor().execute(
                            '''
                                select "form"."name", "form"."order", "type1"."type", "type2"."type",
                                "ability1"."name", "ability1"."desc", "ability2"."name", "ability2"."desc",
                                "hidden_ability"."name", "hidden_ability"."desc", "form"."height", "form"."weight",
                                "catch_rate", "pokedex_entry", "form"."wild_always_held_item",
                                "hp"."value", "atk"."value", "def"."value", "spe"."value", "sa"."value", "sd"."value",
                                "hp"."value" + "atk"."value" + "def"."value" + "spe"."value" + "sa"."value" + "sd"."value" as "bst",
                                ifnull("hp_ev"."value", 0), ifnull("atk_ev"."value", 0), ifnull("def_ev"."value", 0), ifnull("spe_ev"."value", 0), ifnull("sa_ev"."value", 0), ifnull("sd_ev"."value", 0),
                                ifnull("hp_ev"."value", 0) + ifnull("atk_ev"."value", 0) + ifnull("def_ev"."value", 0) + ifnull("spe_ev"."value", 0) + ifnull("sa_ev"."value", 0) + ifnull("sd_ev"."value", 0) as "evtot"
                                from "pokemon_form" as "form"
                                join "pokemon_type" as "type1" on "type1"."pokemon" = "form"."pokemon" and "type1"."form" = "form"."name" and "type1"."index" = 1
                                left join "pokemon_type" as "type2" on "type2"."pokemon" = "form"."pokemon" and "type2"."form" = "form"."name" and "type2"."index" = 2
                                join "pokemon_ability" as "pability1" on "pability1"."pokemon" = "form"."pokemon" and "pability1"."form" = "form"."name" and "pability1"."index" = 1
                                join "ability" as "ability1" on "ability1"."id" = "pability1"."ability"
                                left join "pokemon_ability" as "pability2" on "pability2"."pokemon" = "form"."pokemon" and "pability2"."form" = "form"."name" and "pability2"."index" = 2
                                left join "ability" as "ability2" on "ability2"."id" = "pability2"."ability"
                                left join "pokemon_ability" as "pability3" on "pability3"."pokemon" = "form"."pokemon" and "pability3"."form" = "form"."name" and "pability3"."index" = 3
                                left join "ability" as "hidden_ability" on "hidden_ability"."id" = "pability3"."ability"
                                join "base_stat" as "hp" on "hp"."pokemon" = "form"."pokemon" and "hp"."form" = "form"."name" and "hp"."stat" = 'HP'
                                join "base_stat" as "atk" on "atk"."pokemon" = "form"."pokemon" and "atk"."form" = "form"."name" and "atk"."stat" = 'ATK'
                                join "base_stat" as "def" on "def"."pokemon" = "form"."pokemon" and "def"."form" = "form"."name" and "def"."stat" = 'DEF'
                                join "base_stat" as "spe" on "spe"."pokemon" = "form"."pokemon" and "spe"."form" = "form"."name" and "spe"."stat" = 'SPD'
                                join "base_stat" as "sa" on "sa"."pokemon" = "form"."pokemon" and "sa"."form" = "form"."name" and "sa"."stat" = 'SA'
                                join "base_stat" as "sd" on "sd"."pokemon" = "form"."pokemon" and "sd"."form" = "form"."name" and "sd"."stat" = 'SD'
                                left join "ev_yield" as "hp_ev" on "hp_ev"."pokemon" = "form"."pokemon" and "hp_ev"."form" = "form"."name" and "hp_ev"."stat" = 'HP'
                                left join "ev_yield" as "atk_ev" on "atk_ev"."pokemon" = "form"."pokemon" and "atk_ev"."form" = "form"."name" and "atk_ev"."stat" = 'ATK'
                                left join "ev_yield" as "def_ev" on "def_ev"."pokemon" = "form"."pokemon" and "def_ev"."form" = "form"."name" and "def_ev"."stat" = 'DEF'
                                left join "ev_yield" as "spe_ev" on "spe_ev"."pokemon" = "form"."pokemon" and "spe_ev"."form" = "form"."name" and "spe_ev"."stat" = 'SPD'
                                left join "ev_yield" as "sa_ev" on "sa_ev"."pokemon" = "form"."pokemon" and "sa_ev"."form" = "form"."name" and "sa_ev"."stat" = 'SA'
                                left join "ev_yield" as "sd_ev" on "sd_ev"."pokemon" = "form"."pokemon" and "sd_ev"."form" = "form"."name" and "sd_ev"."stat" = 'SD'
                                where "form"."pokemon" = ? order by "form"."order"
                            ''',
                            (id_,)
                        )
                    ]

                    pokemon['multiple_forms'] = len(forms) > 1

                    for form in forms:
                        if form['type2'] is None:
                            type_effect = [(multiplier, type_) for type_, multiplier in db.cursor().execute(
                                "select `attacking_type`, `multiplier` from `type_effect` where `defending_type` = ?",
                                (form['type1'],)
                            )]
                        else:
                            type_effect = [(multiplier, type_) for type_, multiplier in db.cursor().execute(
                                """
                                    select `id`, ifnull(`type1_effect`.`multiplier`, 1) * ifnull(`type2_effect`.`multiplier`, 1) from `type`
                                    left join `type_effect` as `type1_effect` on `type1_effect`.`attacking_type` = `id` and `type1_effect`.`defending_type` = ?
                                    left join `type_effect` as `type2_effect` on `type2_effect`.`attacking_type` = `id` and `type2_effect`.`defending_type` = ?
                                    where ifnull(`type1_effect`.`multiplier`, 1) * ifnull(`type2_effect`.`multiplier`, 1) != 1
                                """,
                                (form['type1'], form['type2'])
                            )]

                        form['type_effect'] = defaultdict(lambda: [])
                        multiplier_map = {4: 'double_weak', 2: 'weak', 0.5: 'resist', 0.25: 'double_resist', 0: 'immune'}

                        for multiplier, type_ in type_effect:
                            form['type_effect'][multiplier_map[float(multiplier)]].append(type_)

                        form['level_moves'] = [
                            {'level': level, 'name': name} for level, name in db.cursor().execute(
                                """
                                    select "level", "name" from "level_move" join "move" on "id" = "move"
                                    where "pokemon" = ? and "form" = ? order by "level"
                                """,
                                (id_, form['name'])
                            )
                        ]

                        if form['wild_always_held_item'] != 'DUMMY':
                            name = db.cursor().execute('select "name" from "item" where "id" = ?', (form['wild_always_held_item'],)).fetchall()[0][0]
                            form['wild_held_items'] = [{'name': name, 'rarity': 100}]
                        else:
                            form['wild_held_items'] = [
                                {'name': name, 'rarity': WILD_HELD_ITEM_RARITY_TO_PERCENTAGE[rarity]} for name, rarity in db.cursor().execute(
                                    '''select "item"."name", "wild_held_item"."rarity" from "wild_held_item"
                                    join "item" on "item"."id" = "wild_held_item"."item"
                                    join "wild_held_item_rarity" on "wild_held_item_rarity"."name" = "wild_held_item"."rarity"
                                    where "wild_held_item"."pokemon" = ? and "wild_held_item"."form" = ?
                                    order by "wild_held_item_rarity"."order"''',
                                    (id_, form['name'])
                                )
                            ]

                        evolution_root = get_evolution_root(pokemon['id'], form['name'])

                        if evolution_root is not None:
                            form['evolution'] = get_evolution_tree(*evolution_root)

                        form['egg_moves'] = [
                            name for name, in db.cursor().execute("""
                                select "name" from "egg_move" join "move" on "id" = "move"
                                where "pokemon" = ? and "form" = ? order by "move"
                            """, ((id_, form['name']) if evolution_root is None else evolution_root)
                        )]

                        form['machine_moves'] = [
                            {'item': item, 'name': name} for item, name in db.cursor().execute("""
                                select "item"."name", "move"."name" from "machine_move" join "move" on "move"."id" = "machine_move"."move"
                                left join "item_move" on "item_move"."move" = "move"."id" join "item" on "item"."id" = "item_move"."item"
                                where "machine_move"."pokemon" = ? and "machine_move"."form" = ? order by "item"."name"
                            """, (id_, form['name']))
                        ]

                        form['tutor_moves'] = [
                            name for name, in db.cursor().execute("""
                                select "name" from "tutor_move" join "move" on "id" = "move"
                                where "pokemon" = ? and "form" = ? order by "move"
                            """, (id_, form['name']))
                        ]

                        form['encounters'] = [
                            {
                                'map_id': map_id, 'map_name': map_name, 'method': method,
                                'min_level': min_level, 'max_level': max_level, 'rate': frac(rate) * 100
                            }
                            for map_id, map_name, method, min_level, max_level, rate
                            in db.cursor().execute('''
                                select "per"."map", "map"."name", "em"."desc",
                                "per"."min_level", "per"."max_level", "per"."rate"
                                from "pokemon_encounter_rate_by_level_range" as "per"
                                join "map" on "map"."id" = "per"."map"
                                join "encounter_method" as "em" on "em"."name" = "per"."method"
                                where "per"."pokemon" = ? and "per"."form" = ?
                                order by "per"."map", "em"."order", "per"."rate" collate "frac" desc,
                                "per"."min_level", "per"."max_level"
                            ''', (id_, form['name']))
                        ]

                    pokemon['forms'] = forms
                    return render_template('pokemon_view.jinja2', pokemon=pokemon, prev_pokemon=prev_pokemon, next_pokemon=next_pokemon)

    @controller('admin.html')
    def _():
        return render_template('admin.jinja2')

    @controller('areas.html')
    def _():
        with db:
            areas = [{'id': id_, 'name': name} for id_, name in db.cursor().execute(
                'select "id", "name" from "map"'
            )]

        return render_template('area_list.jinja2', areas=areas)

    with db:
        areas = (json.loads(area) for area, in db.cursor().execute('''
            select json_object(
                'id', "map_id", 'name', "map_name",
                'encounters', json_group_array(json_object(
                    'method', "method", 'pokemon', "pokemon", 'form', "form",
                    'min_level', "min_level", 'max_level', "max_level", 'rate', "rate"
                ))
            )
            from (
                select
                    "map"."id" as "map_id", "map"."name" as "map_name",
                    "method"."desc" as "method",
                    "pokemon"."name" as "pokemon", "form"."name" as "form",
                    "encounter"."min_level", "encounter"."max_level",
                    frac_mul("encounter"."rate", '100') as "rate"
                from "map"
                join "pokemon_encounter_rate_by_level_range" as "encounter"
                    on "encounter"."map" = "map"."id"
                join "encounter_method" as "method" on "method"."name" = "encounter"."method"
                join "pokemon_form" as "form" on (
                    "form"."pokemon" = "encounter"."pokemon" and "form"."name" = "encounter"."form"
                )
                join "pokemon" on "pokemon"."id" = "form"."pokemon"
                order by
                    "map"."id", "method"."order", "encounter"."rate" collate "frac" desc,
                    "pokemon"."number", "form"."order"
            ) as "subq"
            group by "map_id"
        '''))

        for area in areas:
            @controller('area/{}.html'.format(area['id']))
            def _(area=area):
                with db:
                    return render_template('area_view.jinja2', area=area)

    @controller('type_chart.html')
    def _():
        with db:
            types = list(type_ for type_, in db.cursor().execute('select `name` from `type` where `is_pseudo` = 0'))

            type_chart_lines = db.cursor().execute("""
                select `attacking_type`.`name`, `defending_type`.`name`, `multiplier` from `type_effect`
                join `type` as `attacking_type` on `attacking_type`.`id` = `type_effect`.`attacking_type`
                join `type` as `defending_type` on `defending_type`.`id` = `type_effect`.`defending_type`
            """)

            type_chart = {
                (attacking_type, defending_type): multiplier
                for attacking_type, defending_type, multiplier in type_chart_lines
            }

        return render_template('type_chart.jinja2', types=types, type_chart=type_chart)

    def do_writers():
        for writer in WRITERS:
            writer()

    do_writers()

if __name__ == '__main__':
    run()