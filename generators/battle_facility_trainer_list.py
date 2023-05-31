import json
from reborndb import DB
from reborndb import generate

def run():
    trainers = (
        json.loads(trainer) for trainer,
        in DB.H.execscript('generators/battle_facility_trainer_list.sql')
    )

    generate.render_template(
        'battle_facility_trainers.html', 'battle_facility_trainer_list.jinja2',
        trainers=trainers
    )

if __name__ == '__main__':
    run()