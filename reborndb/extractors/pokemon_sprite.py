
# -- for each form we have a normal sprite, shiny sprite, back-normal, back-shiny
# -- egg, shiny-egg. PULSE forms lack shiny sprites
# -- overworld sprites are in Graphics/Characters/pkmn_{internalname}.png
# --   some with a number before the extension, not necess related to form
# --   (e.g. charizard3.png is Cal riding Charizard)
# --   icons in Graphics/Icons/icon{number}, arranged horizontakkky wuth second two shiny
# --     and icon{number}egg.png, icon{number}f.png
# --     oh, the two are just the two frames---generally second is one pixel lower than first
# --     also, egg sprites only for non-evolutions

import re
from io import BytesIO
from PIL import Image
from reborndb import DB
from reborndb import settings

def split_image(img, width_per_part, height_per_part):
	for x in range(0, img.width, width_per_part):
		for y in range(0, img.height, height_per_part):
			cropped = img.crop((x, y, x + width_per_part, y + height_per_part))
			yield x // width_per_part, y // height_per_part, cropped

def getblob(img):
	stream = BytesIO()
	img.save(stream, 'PNG')
	stream.seek(0)
	return stream.read()

BATTLER_DIR = settings.REBORN_GRAPHICS_PATH / 'Battlers'
BATTLER_PATTERN = r'^(\d+)(f)?(Egg)?(?:_(s)?(b)?(\d+))?\.png$'
ICON_DIR = settings.REBORN_GRAPHICS_PATH / 'Icons'
ICON_PATTERN = r'^icon(\d+)(f)?(egg)?\.png$'

SPRITE_SIZE = 192
EGG_SPRITE_SIZE = ICON_SPRITE_SIZE = 64

def extract():
	blobs = {}

	for path in BATTLER_DIR.iterdir():
		m = re.match(BATTLER_PATTERN, path.name)
		if m is None: continue

		number, female, egg, shiny, back, form = m.groups()
		number = int(number)
		gender = 'Female' if female == 'f' else None
		egg = egg == 'Egg'
		shiny = shiny == 's'
		back = back == 'b'

		if form:
			assert gender is None and not egg
			form = int(form)
			type_ = 'back' if back else 'front'

			with path.open('rb') as f:
				content = f.read()

			blobs[number, form, type_, shiny, gender] = content
		else:
			assert not shiny and not back, (shiny, back)
			img = Image.open(path)
			sprite_size = EGG_SPRITE_SIZE if egg else SPRITE_SIZE

			for i, j, part in split_image(img, sprite_size, sprite_size):
				form = j if egg else j // 2
				
				if number == 678 and form == 0: # special case for Meowstic-F
				    form = 1
				    gender = None
				
				type_ = 'egg' if egg else ('back' if j % 2 else 'front')
				shiny = [False, True][i]

				# prefer to use the sprite that's in its own file
				key = (number, form, type_, shiny, gender)
				if key not in blobs: blobs[number, form, type_, shiny, gender] = getblob(part)

	rows = [(*key, blob) for key, blob in blobs.items()]

	for path in ICON_DIR.iterdir():
		m = re.match(ICON_PATTERN, path.name)
		if m is None: continue

		number, female, egg = m.groups()
		number = int(number)
		gender = 'Female' if female == 'f' else None
		egg = egg == 'egg'

		img = Image.open(path)
		sprite_size = ICON_SPRITE_SIZE

		for i, j, part in split_image(img, sprite_size, sprite_size):
			form = j
			type_, shiny = [('icon1', False), ('icon2', False), ('icon1', True), ('icon2', True)][i]
			if egg: type_ = f'egg-{type_}'
			rows.append((number, form, type_, shiny, gender, getblob(part)))
			
	with DB.H.transaction():
		DB.H.dump_as_table('pokemon_sprite_raw', ('pokemon', 'form', 'type', 'shiny', 'gender', 'sprite'), rows)

		DB.H.exec('''
			insert into "pokemon_sprite" ("pokemon", "form", "type", "shiny", "gender", "sprite")
			select "pokemon"."id", "form"."name", "sprite"."type", "sprite"."shiny", "sprite"."gender", "sprite"."sprite"
			from "pokemon_sprite_raw" as "sprite"
			join "pokemon" on "pokemon"."number" = "sprite"."pokemon"
			join "pokemon_form" as "form" on "form"."pokemon" = "pokemon"."id" and "form"."order" = "sprite"."form"
		''')

		# update sprites with a female counterpart to be explicitly male
		DB.H.exec('''
			update "pokemon_sprite" as "sprite"
			set "gender" = 'Male'
			where "sprite"."gender" is null and exists (
				select 1 from "pokemon_sprite" as "female" where
					"female"."pokemon" = "sprite"."pokemon"
					and "female"."form" = "sprite"."form"
					and "female"."type" = "sprite"."type"
					and "female"."shiny" = "sprite"."shiny"
					and "female"."gender" = 'Female'
			)
		''')