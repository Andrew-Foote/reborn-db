import json
from reborndb import DB
from reborndb import generate

def run():
    # we need some spritesheets

    trainers = (
        json.loads(trainer) for trainer,
        in DB.H.execscript('generators/trainer_list.sql')
    )

    generate.render_template('trainers.html', 'trainer_list.jinja2', trainers=trainers)

if __name__ == '__main__':
    run()