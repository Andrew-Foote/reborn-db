import json
from slugify import slugify
from reborndb import DB
from reborndb import generate

def run():
    for from_name, from_form, to_name, to_form, scheme_index, scheme in DB.H.execscript('generators/evolution_area.sql'):
        scheme_id = '_'.join((*map(slugify, (from_name, from_form, to_name, to_form)), str(scheme_index)))

        generate.render_template(
            f'evolution_area/{scheme_id}.html', 'evolution_area.jinja2',
            from_name=from_name, from_form=from_form, to_name=to_name, to_form=to_form,
            scheme_index=scheme_index, scheme=json.loads(scheme)
        )

if __name__ == '__main___':
    run()