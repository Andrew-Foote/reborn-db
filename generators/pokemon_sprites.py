import json
from slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    for pokemon, form, genderdiff, front_sprite, back_sprite, egg_sprite, icon, egg_icon in DB.H.execscript('generators/pokemon_sprites.sql'):
        front_sprite = json.loads(front_sprite)
        back_sprite = json.loads(back_sprite)
        egg_sprite = json.loads(egg_sprite)
        icon = json.loads(icon)
        egg_icon = json.loads(egg_icon)
                
        generate.render_template(
            f'pokemon_sprites/{slugify(pokemon)}_{slugify(form)}.html',
            'pokemon_sprites.jinja2',
            pokemon=pokemon, form=form,
            genderdiff=genderdiff,
            front_sprite=front_sprite, back_sprite=back_sprite, egg_sprite=egg_sprite,
            icon=icon, egg_icon=egg_icon
        )

if __name__ == '__main__':
    run()
