import json
import math
from matplotlib import pyplot as plot
from reborndb import DB
from reborndb import generate
from reborndb import settings

def run():
    growth_rates = [json.loads(growth_rate) for growth_rate, in DB.H.exec('''
        select json_object(
            'id', "growth_rate"."pbs_name", 'name', "growth_rate"."name",
            'python_formula', "growth_rate"."python_formula",
            'latex_formula', "growth_rate"."latex_formula",
            'level_exp', (
                select json_group_object("level_exp"."level", "level_exp"."exp")
                from (
                    select "level_exp"."level", "level_exp"."exp"
                    from "level_exp"
                    where "level_exp"."growth_rate" = "growth_rate"."name"
                    order by "level_exp"."level"
                ) as "level_exp"
            ),
            'pokemon', (
                select json_group_array(json_object(
                    'id', "pokemon"."name", 'name', "pokemon"."name", 'icon', base64("pokemon"."icon")
                ))
                from (
                    select "pokemon"."name", "sprite"."sprite" as "icon"
                    from "pokemon"
                    join "pokemon_form" as "form" on (
                        "form"."pokemon" = "pokemon"."id" and "form"."order" = 0
                    )
                    join "pokemon_sprite" as "sprite" on (
                        "sprite"."pokemon" = "pokemon"."id" and "sprite"."form" = "form"."name"
                        and "sprite"."type" = 'icon1' and "sprite"."shiny" = 0
                        and ("sprite"."gender" is null or "sprite"."gender" = 'Male')
                    )
                    where "pokemon"."growth_rate" = "growth_rate"."name"
                    order by "pokemon"."number"
                ) as "pokemon"
            )
        )
        from "growth_rate"
        order by "growth_rate"."order"
    ''')]

    levels = range(151)
    line_styles = [
        '-', '--', '-.', ':',
        (0, (3, 2, 1, 2, 1, 2)), # dashdotdotted
        (0, (3, 2, 3, 2, 1, 2)), # dashdashdotted
    ]

    for i, growth_rate in enumerate(reversed(growth_rates)):
        formula = growth_rate['python_formula']

        for level in levels:
            if str(level) not in growth_rate['level_exp']:
                exp = eval(formula, {'level': level, 'math': math})
                growth_rate['level_exp'][str(level)] = exp

        exps = list(growth_rate['level_exp'].values())
        plot.plot(levels, exps, label=growth_rate['name'], linestyle=line_styles[i])

    plot.ticklabel_format(style='plain')
    plot.xlim(0, 150)
    plot.ylim(0, 6_000_000)
    plot.xlabel('Level')
    plot.ylabel('EXP Required')
    plot.subplots_adjust(left=.2)
    plot.legend(loc='upper left')
    plot.savefig(settings.SITE_PATH / 'growth_rate_graph.png')
    generate.render_template('growth_rates.html', 'growth_rate_list.jinja2', growth_rates=growth_rates)

if __name__ == '__main__':
    run()
