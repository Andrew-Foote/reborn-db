import json
from slugify import slugify
from reborndb import DB
from reborndb import generate

# some stuff we still need to resolve
# - does the ball mean anything?
# - does the hidden power mean anything?
# - what determines the type of hidden power? are ivs affected?
# - why are some natures null?
# - why are a lot of genders null?
# - "Player" as a nickname
# - display shiny/female sprites

def run():
    for trainer, in DB.H.execscript('generators/trainer_view.sql'):
        trainer = json.loads(trainer)
        name = trainer['name']

        generate.render_template(
            f'trainer/{slugify(name)}.html',
            'trainer_view.jinja2',
            trainer=trainer
        )

if __name__ == '__main__':
    run()
