import json
from slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    moves = list(DB.H.execscript('generators/move_view.sql'))

    for move_id, move in moves:
        generate.render_template(
            'move/{}.html'.format(move_id),
            'move_view.jinja2',
            move=json.loads(move)
        )

if __name__ == '__main__':
    run()
