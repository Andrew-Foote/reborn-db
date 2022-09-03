import json
from slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    for name, pokemon in DB.H.execscript('generators/pokemon_view.sql'):
        generate.render_template(
            f'pokemon/{slugify(name)}.html',
            'pokemon_view.jinja2',
            pokemon=json.loads(pokemon)
        )

if __name__ == '__main__':
    run()
