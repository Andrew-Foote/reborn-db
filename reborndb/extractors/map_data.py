import io
import itertools as it
import numpy as np
from parsers.rpg.map import Map
from reborndb import DB, settings

def extract():
    rows = []
    event_rows = []

    for map_id, mapdata in Map.load_all():
        stream = io.BytesIO()
        np.save(stream, mapdata.data.array)
        databytes = stream.getvalue()
        rows.append((map_id, mapdata.tileset_id, mapdata.width, mapdata.height, databytes))

        for event in mapdata.events.values():
            event_rows.append((map_id, event.id_, event.name, event.x, event.y))

    with DB.H.transaction():
        DB.H.exec('drop table if exists "map_event"')
        DB.H.exec('drop table if exists "marshal_mapdata"')
        DB.H.dump_as_table('marshal_mapdata', ('map_id', 'tileset', 'width', 'height', 'data'), rows)
        DB.H.dump_as_table('map_event', ('map_id', 'event_id', 'event_name', 'x', 'y'), event_rows)

if __name__ == '__main__':
    extract()