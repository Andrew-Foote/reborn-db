import json
from reborndb import generate
from reborndb import DB

def run():
    pokemons = [json.loads(pokemon) for pokemon, in DB.H.exec('''
        select json_object(
            'id', "pokemon"."id", 'name', "pokemon"."name", 'form', "form"."name",
            'baseStats', (
                select json_group_array(json_object(
                    'stat', "base_stat"."stat", 'value', "base_stat"."value"
                ))
                from "base_stat"
                where
                    "base_stat"."pokemon" = "form"."pokemon"
                    and "base_stat"."form" = "form"."name"
            )
        )
        from "pokemon_form" as "form" join "pokemon" on "pokemon"."id" = "form"."pokemon"
        order by "pokemon"."number", "form"."order"
    ''')]
    
    natures = [json.loads(nature) for nature, in DB.H.exec('''
        select json_object(
            'id', "id", 'name', "name",
            'increasedStat', "increased_stat", 'decreasedStat', "decreased_stat"
        ) from "nature" order by "code"
    ''')]
    
    stats = [json.loads(stat) for stat, in DB.H.exec('''
        select json_object('id', "id", 'name', "name") from "stat" order by "order"
    ''')]
    
    generate.render_template(
        'statcalc.html', 'statcalc.jinja2',
        pokemons=pokemons, natures=natures, stats=stats
    )

if __name__ == '__main___':
    run()