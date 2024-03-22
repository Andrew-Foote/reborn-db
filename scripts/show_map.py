import io
import json
import math
from typing import Iterator
import numpy as np
from PIL import Image
from reborndb import DB

# Tileset "Pyrous" is the smallest (256 x 512, i.e. just 8 * 16 = 128 tiles),
# might be conveneitn for experimentation
# map 205 is also nice and small, 20 by 25

def load_array(bytes_: bytes) -> np.ndarray:
	stream = io.BytesIO()
	stream.write(bytes_)
	stream.seek(0)
	return np.load(stream)

def load_image(bytes_: bytes) -> Image.Image:
	stream = io.BytesIO()
	stream.write(bytes_)
	stream.seek(0)
	return Image.open(stream)

def split_image(
	img: Image.Image, width_per_part: int, height_per_part: int
) -> Iterator[tuple[int, int, Image.Image]]:
	
	for x in range(0, img.width, width_per_part):
		for y in range(0, img.height, height_per_part):
			cropped = img.crop((x, y, x + width_per_part, y + height_per_part))
			yield x // width_per_part, y // height_per_part, cropped

# Each map has 8 autotiles (some may be blank; at least one will always be blank).
# Each autotile corresponds to 48 different actual tiles which are pieced together
# via some voodoo.
# 8 * 48 = 384; the first 384 tile IDs are devoted to autotiles.
# Remaining IDs cover non-autotiles.

def map_image(map_id: int) -> Image.Image:
	(tileset_name, tileset_bytes, data_bytes), = DB.H.exec('''
		select
			"tileset"."name", "tileset_file"."content", "map"."data"
		from "map"
		join "tileset" on "map"."tileset" = "tileset"."name"
		join "tileset_file" on "tileset_file"."name" = "tileset"."file"
		where "map"."id" = ?
	''', (map_id,))

	autotiles = dict(DB.H.exec('''
		select "tileset_autotile"."index", "autotile"."image"
		from "tileset_autotile"
		join "autotile" on "autotile"."name" = "tileset_autotile"."autotile"
		where "tileset_autotile"."tileset" = ?
	''', (tileset_name,)))

	tileset = load_image(tileset_bytes)
	data = load_array(data_bytes)

	tilemap: list[Image.Image | None] = [None] * (384 + 8 * math.ceil(tileset.height / 32))
	print(f'{len(tilemap)} tiles')

	# add autotiles to tilemap

	for i in range(8):
		try:
			autotile = autotiles[i]
		except KeyError:
			continue

		autotile = load_image(autotile)

		# we don't know how autotiles actually work yet, so for now, just
		# take the top left 32 x 32 segment of the autotile file, and assume
		# every variant of the autotile is that

		autotile_cropped = autotile.crop((0, 0, 32, 32))
		tilemap[i * 48:i * 48 + 48] = [autotile_cropped] * 48

	# add non-autotiles to tilemap

	tiles = split_image(tileset, 32, 32)

	for x, y, tile in tiles:
		tilemap[384 + y * 8 + x] = tile

	# we need to make
	width, height, depth = data.shape # note that normally numpy arrays are height, width
	   # we will need to access with [j, i] rather than [i, j]
	print(f'width {width} tiles, height {height} tiles, depth {depth} tiles')
	size = (width * 32, height * 32)
	map_img = Image.new(tileset.mode, (size[0], size[1] * depth)) # pyrous only has depth=0
	#breakpoint()
	#map_img = Image.new(tileset.mode, (size[0], size[1] * 3))

	for k in range(depth): #range(3):
		for i in range(height):
			for j in range(width):
				tile_id = data[j, i, k]
				#print((j, i, k), tile_id)
				tile = tilemap[tile_id]
		
				if tile is not None:
					map_img.paste(tile, (j * 32, height * 32 * k + i * 32))

	return map_img

if __name__ == '__main__':
	import sys
	map_id = int(sys.argv[1])
	img = map_image(map_id)
	img.save('kingsbury-station.png')