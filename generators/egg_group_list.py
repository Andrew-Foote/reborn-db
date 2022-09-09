import json
from reborndb import DB
from reborndb import generate

def run():
    egg_groups = [json.loads(egg_group) for egg_group, in DB.H.exec('''
        select json_object(
            'id', "egg_group"."pbs_name", 'name', "egg_group"."name",
            'pokemon', (
                select json_group_array(json_object(
                    'id', "pokemon"."name", 'name', "pokemon"."name", 'icon', base64("pokemon"."icon")
                ))
                from (
                    select "pokemon"."name", "sprite"."sprite" as "icon"
                    from "pokemon"
                    join "pokemon_egg_group" on (
                        "pokemon_egg_group"."pokemon" = "pokemon"."id"
                        and "pokemon_egg_group"."egg_group" = "egg_group"."name"
                    )
                    join "pokemon_form" as "form" on (
                        "form"."pokemon" = "pokemon"."id" and "form"."order" = 0
                    )
                    join "pokemon_sprite" as "sprite" on (
                        "sprite"."pokemon" = "pokemon"."id" and "sprite"."form" = "form"."name"
                        and "sprite"."type" = 'icon1' and "sprite"."shiny" = 0
                        and ("sprite"."gender" is null or "sprite"."gender" = 'Male')
                    )
                    order by "pokemon"."number"
                ) as "pokemon"
            )
        )
        from "egg_group"
    ''')]
    
    generate.render_template('egg_groups.html', 'egg_group_list.jinja2', egg_groups=egg_groups)

if __name__ == '__main__':
    run()
