# Pokémon sprites are stored in Graphics/Battlers
# the filename will be the National Pokédex number, in three digits
# if there are gender differences, the female's file will have "f" appended
# the egg files have "Egg" appended (possibly after "f")
# the sprite is always 192 x 192
# x-offset will be 192 if shiny, 0 otherwise
# y-offset is 384 * form number, plus 192 if this is a back sprite

import itertools as it
from pathlib import Path
from PIL import Image
import re

NUMBER_OF_POKEMON = 807
skip_indiv = False

input_dir_path = Path('reborn_graphics/Battlers')
output_dir_path = Path('site/editable/img/pokemon')
output_dir_path.mkdir(exist_ok=True)

def split_image(img, width_per_part, height_per_part):
	for x in range(0, img.width, width_per_part):
		for y in range(0, img.height, height_per_part):
			cropped = img.crop((x, y, x + width_per_part, y + height_per_part))
			yield x // width_per_part, y // height_per_part, cropped

SPRITE_SIZE = 192
EGG_SPRITE_SIZE = 64
MAX_SHEET_HEIGHT = 65536 # seems to be a limit for Firefox
MAX_SPRITES_IN_SHEET = MAX_SHEET_HEIGHT // SPRITE_SIZE
SHEET_MODE = 'RGBA' # same as the individual sprites

sheets = []
sheet_offset = 0

for input_path in input_dir_path.iterdir():
	img = Image.open(input_path)
	input_fname = input_path.name
	m = re.match(r'(\d{3})(f?)\.png', input_fname)

	if m is not None:
		number, female = m.group(1, 2)

		for i, j, part in split_image(img, SPRITE_SIZE, SPRITE_SIZE):
			if not skip_indiv:
				part.save(output_dir_path / ('_'.join(it.chain(
					[number, str(j // 2)],
					['female'] if female else [],
					['shiny'] if [False, True][i] else [],
					['back'] if [False, True][j % 2] else []
				)) + '.png'))

			if (i, j) == (0, 0) and not female: # main sprite, add it to the sheet
				if sheet_offset % MAX_SPRITES_IN_SHEET == 0:
					sheets.append(Image.new(img.mode, (SPRITE_SIZE, SPRITE_SIZE * MAX_SPRITES_IN_SHEET), None))

				sheets[-1].paste(part, (0, (sheet_offset % MAX_SPRITES_IN_SHEET) * SPRITE_SIZE))
				sheet_offset += 1

		continue

	m = re.match(r'(\d{3})(f?)[Ee]gg\.png', input_fname)

	if m is not None:
		number, female = m.group(1, 2)

		for i, j, part in split_image(img, EGG_SPRITE_SIZE, EGG_SPRITE_SIZE):
			if not skip_indiv:
				part.save(output_dir_path / ('_'.join(it.chain(
					[number, str(j)],
					['female'] if female else [],
					['shiny'] if [True, False][i] else [],
					['egg']
				)) + '.png'))

		continue

	print(input_fname)

for i, sheet in enumerate(sheets):
	sheet.save(output_dir_path / f'sheet_{i}.png')