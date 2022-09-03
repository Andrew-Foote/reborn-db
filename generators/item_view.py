import json
from slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    items = (json.loads(item) for item, in DB.H.exec('''
        select json_object(
            'name', "name",
            'pocket', "pocket",
            'buy_price', "buy_price",
            'sell_price', "buy_price" / 2,
            'desc', "desc"
        )
        from "item" 
        where "code" != 0
        order by "code"
    '''))

    for item in items:
        generate.render_template('item/{}.html'.format(slugify(item['name'])), 'item_view.jinja2', item=item)

if __name__ == '__main__':
    run()
