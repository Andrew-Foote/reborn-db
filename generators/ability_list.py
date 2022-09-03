import json
from reborndb import DB
from reborndb import generate

def run():
    abilities = (json.loads(ability) for ability, in DB.H.exec('''
        select json_object('id', "id", 'name', "name", 'desc', "desc")
        from "ability" order by "name"
    '''))

    generate.render_template('abilities.html', 'ability_list.jinja2', abilities=abilities)

if __name__ == '__main__':
    run()
