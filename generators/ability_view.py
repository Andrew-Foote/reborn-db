import json
from reborndb.slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    abilities = (json.loads(ability) for ability, in DB.H.exec('''
        select json_object(
            'name', "ability_name", 'desc', "ability_desc",
            'forms', case when count("name") = 0
                then json_array()
                else json_group_array(json_object(
                    'pokemon', "pokemon", 'name', "name", 'slot', "slot"
                ))
            end
        )
        from (
            select
                "ability"."id" as "ability_id", "ability"."name" as "ability_name",
                "ability"."desc" as "ability_desc",
                "pokemon"."name" as "pokemon", "form"."name" as "name",
                "slot"."name" as "slot"
            from "ability"
            left join "pokemon_ability" on "pokemon_ability"."ability" = "ability"."id"
            left join "ability_slot" as "slot" on "slot"."index" = "pokemon_ability"."index"
            left join "pokemon_form" as "form" on (
                "form"."pokemon" = "pokemon_ability"."pokemon"
                and "form"."name" = "pokemon_ability"."form"
            )
            left join "pokemon" as "pokemon" on "pokemon"."id" = "form"."pokemon"
            order by "pokemon"."number", "form"."order"
        ) as "subq"
        group by "ability_id"
    '''))

    for ability in abilities:
        generate.render_template('ability/{}.html'.format(slugify(ability['name'])), 'ability_view.jinja2', ability=ability)

if __name__ == '__main__':
    run()
