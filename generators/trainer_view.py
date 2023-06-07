import json
from reborndb.slugify import slugify
from reborndb import DB
from reborndb import generate

# some stuff we still need to resolve
# - does the ball mean anything?
    #idk
# - does the hidden power mean anything?
    #idk
# - what determines the type of hidden power? are ivs affected?
    #idk
# - why are some natures null?
    #cos they're random
# - why are a lot of genders null?
    #cos they're random
# - "Player" as a nickname
    #think we did this (Shelly's Leavanny)
# - display shiny/female sprites
    #think we did this

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
