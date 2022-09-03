import json
from reborndb import DB
from reborndb import generate

def run():
    area_tree = json.loads(list(DB.H.execscript('generators/area_list.sql'))[0][0])
    generate.render_template('areas.html', 'area_list.jinja2', area_tree=area_tree)

if __name__ == '__main__':
    run()
