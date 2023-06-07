import json
from reborndb.slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    for trainer, in DB.H.execscript('generators/battle_facility_trainer_view.sql'):
        trainer = json.loads(trainer)
        name = trainer['name']

        generate.render_template(
            f'battle_facility_trainer/{slugify(name)}.html',
            'battle_facility_trainer_view.jinja2',
            trainer=trainer
        )

if __name__ == '__main__':
    run()
