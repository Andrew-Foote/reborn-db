import io
from PIL import Image
from parsers.rpg.basic import Direction
from reborndb import DB, settings

def getblob(img):
	stream = io.BytesIO()
	img.save(stream, 'PNG')
	stream.seek(0)
	return stream.read()

def extract():
    names = {
        name.removesuffix('.png')
        for name in DB.H.exec1('select distinct "character_name" from "event_page_character"')
    }

    rows = []

    for name in names:
        fname = settings.REBORN_GRAPHICS_PATH / 'Characters'  / f'{name}.png'

        try:        
            with Image.open(fname) as image:
                width, height = image.size
                cellwidth = width // 4
                cellheight = height // 4

                for i in range(4):
                    for j in range(4):
                        x = cellwidth * i
                        y = cellheight * j
                        right = x + cellwidth
                        top = y + cellheight
                        cropped = image.crop((x, y, right, top))
                        rows.append((name, Direction((j + 1) * 2).name.lower(), i, getblob(cropped)))
        except FileNotFoundError: # 'invisible' is used as a name to indicate that there is no
                                  # sprite associated with the event
            continue

    with DB.H.transaction():
        DB.H.bulk_insert('character_image', ('filename', 'direction', 'pattern', 'content'), rows)
