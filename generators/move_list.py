import json
from reborndb.slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    moves = (json.loads(move) for move, in DB.H.execscript('generators/move_list.sql'))
    generate.render_template('moves.html', 'move_list.jinja2', moves=moves)

if __name__ == '__main__':
    run()
