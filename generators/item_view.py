import json
from slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    items = (json.loads(item) for item, in DB.H.exec('''
        select json_object(
            'name', "item"."name",
            'pocket', "item"."pocket",
            'buy_price', "item"."buy_price",
            'sell_price', "item"."buy_price" / 2,
            'desc', "item"."desc",
            'move', json_object('id', "move"."id", 'name', "move"."name")
        )
        from "item" 
        left join "machine_item" as "machine" on "machine"."item" = "item"."id"
        left join "move" on "move"."id" = "machine"."move"
        where "item"."code" != 0
        order by "item"."code"
    '''))

    for item in items:
        generate.render_template('item/{}.html'.format(slugify(item['name'])), 'item_view.jinja2', item=item)

if __name__ == '__main__':
    run()
