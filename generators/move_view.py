import json
from slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    moves = (json.loads(move) for move, in DB.H.execscript('generators/move_view.sql'))

    for move in moves:
        generate.render_template('move/{}.html'.format(slugify(move['name'])), 'move_view.jinja2', move=move)

if __name__ == '__main__':
    run()
