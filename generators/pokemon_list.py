import json
from reborndb import DB
from reborndb import generate

def run():
    pokemons = (json.loads(pokemon) for pokemon, in DB.H.exec('''
        select json_object(
            'number', "pokemon"."number",
            'name', "pokemon"."name",
            'sprite', base64("sprite"."sprite")
        ) from "pokemon"
        join "pokemon_form" as "form" on
            "form"."pokemon" = "pokemon"."id"
            and "form"."order" = 0
        join "pokemon_sprite" as "sprite" on
            "sprite"."pokemon" = "pokemon"."id"
            and "sprite"."form" = "form"."name"
            and "sprite"."type" = 'front'
            and "sprite"."shiny" = 0
            and ("sprite"."gender" is null or "sprite"."gender" = 'Male')
        order by "number"
    '''))

    generate.render_template('pokemon.html', 'pokemon_list.jinja2', pokemons=pokemons)

if __name__ == '__main__':
    run()