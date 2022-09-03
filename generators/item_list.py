import json
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

    generate.render_template('items.html', 'item_list.jinja2', items=items)

if __name__ == '__main__':
    run()
