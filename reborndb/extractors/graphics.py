import io
from PIL import Image
from parsers.rpg.basic import Direction
from reborndb import DB, settings

def getblob(img):
	stream = io.BytesIO()
	img.save(stream, 'PNG')
	stream.seek(0)
	return stream.read()

def extract_character_files():
    rows = []

    for path in (settings.REBORN_GRAPHICS_PATH / 'Characters').iterdir():
        with path.open('rb') as f:
            image = f.read()
            rows.append((path.stem.lower(), image))

    with DB.H.transaction():
        DB.H.bulk_insert('character_file', ('name', 'content'), rows)

def extract_character_images():
    names = {
        name.removesuffix('.png').lower()
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
        DB.H.bulk_insert('character_image', ('file', 'direction', 'pattern', 'content'), rows)

def extract():
    extract_character_files()
    extract_character_images()
