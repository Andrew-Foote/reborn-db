import json
from reborndb import DB
from reborndb import generate

def run():
    areas = ((id_, json.loads(area)) for id_, area in DB.H.execscript('generators/area_view.sql'))

    for id_, area in areas:
        generate.render_template(f'area/{id_}.html', 'area_view.jinja2', area=area)

if __name__ == '__main___':
    run()