import json
from reborndb import DB
from reborndb import generate

def run():
    move_tutors = [json.loads(mt) for mt in DB.H.exec1('''
        select json_object(
            'move', json_object(
                'id', "move"."id",
                'name', "move"."name"
            ),
            'cost_is_monetary', "mtv"."cost_is_monetary",
            'cost_quantity', "mtv"."cost_quantity",
            'cost_item', case when "mtv"."cost_item" is null
                then null
                else json_object(
                    'id', "item"."id",
                    'name', "item"."name"
                )
            end,
            'sprite', base64("mtv"."sprite"),
            'map', json_object(
                'id', "map"."id",
                'name', "map"."name"
            )
        )
        from "move_tutor_v" as "mtv"
        join "move" on "move"."id" = "mtv"."move"
        join "map" on "map"."id" = "mtv"."map"
        left join "item" on "mtv"."cost_item" is not null and "item"."id" = "mtv"."cost_item"
        order by "map"."id", "move"."name"
    ''')]

    print(move_tutors)
    
    generate.render_template('move_tutors.html', 'move_tutor_list.jinja2', move_tutors=move_tutors)

if __name__ == '__main__':
    run()
