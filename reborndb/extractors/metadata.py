# To run this script:
#   - Make sure the current working directory is the project root (the directory named `reborn-db`)
#   - Use the command
# 
#       `env\Scripts\python -m pbs_extractors.metadata

from parsers import marshal
from reborndb import DB
from reborndb import settings
from reborndb import pbs

FIELDS_WITH_DEFAULTS = {
    'bicycle_music': 'BicycleBGM',
    'surf_music': 'SurfBGM',
    'wild_battle_music': 'WildBattleBGM',
    'wild_win_music': 'WildVictoryME',
    'trainer_battle_music': 'TrainerBattleBGM',
    'trainer_win_music': 'TrainerVictoryME',
}

BOOLEAN_FIELDS = {
    'has_location_signpost': ('ShowArea', lambda r: False),
    'outdoor': ('Outdoor', lambda r: False),
    'bicycle_usable': ('Bicycle', lambda r: r['outdoor']),
    'bicycle_required': ('BicycleAlways', lambda r: False),
    'flashable': ('DarkMap', lambda r: False),
    'in_safari_zone': ('SafariMap', lambda r: False),
}

def extract():
    pbs_sections = pbs.load('metadata')
    pbs_cols_set = set()

    for section in pbs_sections:
        for key in section.content.keys():
            pbs_cols_set.add(key)

    pbs_cols = tuple(pbs_cols_set)
    pbs_rows = []

    for section in pbs_sections:
        if section.content.get('Weather', ''):
            weatherbits = section.content['Weather'].split(',')
            weatherbits[0] = f'"{weatherbits[0]}"'
            section.content['Weather'] = ','.join(weatherbits)

        pbs_rows.append((
            section.header,
            None if section.comment is None else section.comment.strip(),
            *(section.content.get(col, '') for col in pbs_cols)
        ))

    with DB.H.transaction():
        DB.H.dump_as_table('pbs_metadata', ('__header__', '__comment__', *pbs_cols), pbs_rows)

    mapinfo = marshal.load_file(settings.REBORN_DATA_PATH / 'MapInfos.rxdata').graph
    marshal_mapinfo_cols = ('name', 'scroll_x', 'scroll_y', 'order', 'expanded', 'parent_id')
    marshal_mapinfo_rows = []

    for map_id, mapinfo_for_id_ref in marshal.get_hash(mapinfo, mapinfo.root_ref(), marshal.get_fixnum).items():
        mapinfo_for_id = marshal.get_inst(mapinfo, mapinfo_for_id_ref, 'RPG::MapInfo', dict, {
            'scroll_x': marshal.get_fixnum, 'scroll_y': marshal.get_fixnum, 'name': marshal.get_string,
            'expanded': marshal.get_bool, 'order': marshal.get_fixnum, 'parent_id': marshal.get_fixnum
        })

        marshal_mapinfo_rows.append((
            map_id,
            *(mapinfo_for_id[field] for field in marshal_mapinfo_cols)
        ))

    with DB.H.transaction():
        DB.H.dump_as_table('marshal_mapinfo', ('map_id', *marshal_mapinfo_cols), marshal_mapinfo_rows)
        
        DB.H.exec('''
            insert into "map" (
                "id", "name", "pbs_name", "desc", "parent_id", "order", "expanded",
                "scroll_x", "scroll_y", "region_id", "x", "y", "has_location_signpost",
                "battle_backdrop", "outdoor", "bicycle_usable", "bicycle_required", "flashable",
                "sets_teleport_map", "sets_teleport_x", "sets_teleport_y", "underwater_map", "weather",
                "weather_chance", "in_safari_zone", "bicycle_music", "surf_music",
                "wild_battle_music", "wild_win_music", "trainer_battle_music", "trainer_win_music",
                "tileset", "width", "height", "data"
            )
            select
                "mapinfo"."map_id", "mapinfo"."name", "metadata"."__comment__", NULL,
                nullif("mapinfo"."parent_id", 0), "mapinfo"."order", "mapinfo"."expanded",
                "mapinfo"."scroll_x", "mapinfo"."scroll_y",
                "metadata"."map_position" -> '$[0]',
                "metadata"."map_position" -> '$[1]', "metadata"."map_position" -> '$[2]',
                case when "metadata"."ShowArea" = 'true' then 1 else 0 end,
                nullif("metadata"."BattleBack", ''),
                case when "metadata"."Outdoor" = 'true' then 1 else 0 end,
                case
                    when "metadata"."Bicycle" = 'true' then 1
                    when "metadata"."Bicycle" = 'false' then 0
                    when "metadata"."Outdoor" = 'true' then 1
                    else 0
                end,
                case when "metadata"."BicycleAlways" = 'true' then 1 else 0 end,
                case when "metadata"."DarkMap" = 'true' then 1 else 0 end,
                "metadata"."teleport" -> '$[0]', "metadata"."teleport" -> '$[1]', "metadata"."teleport" -> '$[2]',
                nullif("metadata"."DiveMap", ''),
                "metadata"."weather_fields" -> '$[0]', "metadata"."weather_fields" -> '$[1]',
                case when "metadata"."SafariMap" = 'true' then 1 else 0 end,
                ifnull(nullif("metadata"."BicycleBGM", ''), "global_metadata"."BicycleBGM"),
                ifnull(nullif("metadata"."SurfBGM", ''), "global_metadata"."SurfBGM"),
                ifnull(nullif("metadata"."WildBattleBGM", ''), "global_metadata"."WildBattleBGM"),
                ifnull(nullif("metadata"."WildVictoryME", ''), "global_metadata"."WildVictoryME"),
                ifnull(nullif("metadata"."TrainerBattleBGM", ''), "global_metadata"."TrainerBattleBGM"),
                ifnull(nullif("metadata"."TrainerVictoryME", ''), "global_metadata"."TrainerVictoryME"),
                "tileset"."name", "mapdata"."width", "mapdata"."height", "mapdata"."data"
            from "marshal_mapinfo" as "mapinfo"
            -- there are several mapinfos which don't have a corresponding metadata,
            -- but not the other way round (except for the global metadata)
            left join
            (
                select
                    "pbs_metadata".*,
                    json('[' || "pbs_metadata"."MapPosition" || ']') as "map_position",
                    json('[' || "pbs_metadata"."HealingSpot" || ']') as "teleport",
                    json('[' || "pbs_metadata"."Weather" || ']') as "weather_fields"
                from "pbs_metadata"
            ) as "metadata" on (
                "mapinfo"."map_id" = cast("metadata"."__header__" as integer)
            )
            join "pbs_metadata" as "global_metadata" on cast("global_metadata"."__header__" as integer) = 0
            join "marshal_mapdata" as "mapdata" on "mapdata"."map_id" = "mapinfo"."map_id"
            join "tileset" on "tileset"."id" = "mapdata"."tileset"
        ''')

    # pbs_data = pbs.load('metadata')
    # rows = []
    # defaults = {}

    # for section in pbs_data:
    # 	id_ = int(section.header)
    # 	row_as_dict = defaults if id_ == 0 else {'id': id_}

    # 	for field, pbs_field in FIELDS_WITH_DEFAULTS.items():
    # 		row_as_dict[field] = section.content.get(pbs_field, defaults.get(field))

    # 	if id_ == 0: continue
        
    # 	row_as_dict['name'] = section.comment
    # 	row_as_dict['battle_backdrop'] = section.content.get('BattleBack')

    # 	for field, (pbs_field, default_cb) in BOOLEAN_FIELDS.items():
    # 		if pbs_field in section.content:
    # 			row_as_dict[field] = pbs.parse_bool(section.content[pbs_field])
    # 		else:
    # 			row_as_dict[field] = default_cb(row_as_dict)

    # 	position_fields = ('region_id', 'x', 'y')

    # 	if (position_info := section.content.get('MapPosition')):
    # 		row_as_dict |= {field: int(value.strip()) for field, value in zip(position_fields, position_info.split(','))}
    # 	else:
    # 		row_as_dict |= {field: None for field in position_fields}

    # 	teleport_fields = ('sets_teleport_map', 'sets_teleport_x', 'sets_teleport_y')

    # 	if (teleport_info := section.content.get('HealingSpot')):
    # 		row_as_dict |= {field: int(value.strip()) for field, value in zip(teleport_fields, teleport_info.split(','))}
    # 	else:
    # 		row_as_dict |= {field: None for field in teleport_fields}

    # 	if (weather_info := section.content.get('Weather')):
    # 		weather, chance = (value.strip() for value in weather_info.split(','))
    # 		row_as_dict |= {'weather': weather, 'weather_chance': int(chance)}
    # 	else:
    # 		row_as_dict |= {'weather': None, 'weather_chance': None}

    # 	row_as_dict['underwater_map'] = int(section.content['DiveMap']) if 'DiveMap' in section.content else None

    # 	descs = {
    # 		14: 'Coral Ward pre-restoration',
    # 		27: 'Pyrous Mountain summit',
    # 		29: 'Opal Ward pre-restoration',
    # 		30: 'Apophyll Cave 1F',
    # 		36: 'Obsidia Ward pre-restoration',
    # 		40: 'Opal Ward - under Opal Bridge',
    # 		41: 'Underground Railnet - Peridot side',
    # 		46: 'Lower Peridot Ward - fisherman\'s pool',
    # 		52: 'South Peridot Alley pre-restoration',
    # 		57: 'Peridot Ward pre-restoration - Seacrest\'s garden',
    # 		58: 'North Peridot Alley pre-restoration',
    # 		97: 'Coral Ward pre-restoration',
    # 		103: 'Underground Railnet - Obsidia side', #?
    # 		105: 'Obsidia Alleyway pre-restoration',
    # 		109: 'Coral Ward pre-restoration',
    # 		128: 'Onyx Ward pre-restoration - rooftop garden',
    # 		130: 'Jasper Ward pre-restoration',
    # 		132: 'Malchous Forest Park pre-restoration',
    # 		134: 'Jasper Ward pre-restoration',
    # 		135: 'Jasper Ward pre-restoration',
    # 		137: 'Jasper Ward pre-restoration',
    # 		138: 'Jasper Ward pre-restoration',
    # 		149: 'Beryl Ward pre-restoration',
    # 		151: 'Beryl Ward pre-restoration - Cemetery path',
    # 		151: 'Beryl Cemetery pre-restoration',
    # 		165: 'North Obsidia Alleyway pre-restoration',
    # 		170: 'Lapis Alleyway pre-restoration',
    # 		177: 'Grand Stairway 1F',
    # 		196: 'Underground Railnet - north',
    # 		198: 'Yureyu Power Plant - front rooms',
    # 		206: 'Azurine Island pre-restoration',
    # 		228: 'Underground Railnet - Obsidia Slums side',
    # 		229: 'Underground Railnet - depths',
    # 	}

    # 	row_as_dict['desc'] = descs.get(id_, row_as_dict['name'])

    # 	rows.append(row_as_dict)

    # keys = tuple(rows[0].keys())

    # DB.H.bulk_insert(
    # 	'map', keys, (
    # 		tuple(row[key] for key in keys)
    # 		for row in rows
    # 	)
    # )
