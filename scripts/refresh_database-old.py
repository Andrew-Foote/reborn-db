import os
from utils import apsw_ext
from pbs_extractors import (
	abilities, items, metadata, types, moves, pokemon2, tm, trainertypes, trainers,
	encounters
)

# !!! TROUBLESHOOTING TIPS !!!
#   Sometimes all we get is this extremely inscrutable error:
#
#      <method 'execute' of 'apsw.Cursor' objects> returned NULL without setting an exception
#
#   Usually, this is an indication of something going wrong with foreign keys. You can test this by
#   commenting out the line in `apsw_ext.py` that executes `pragma foreign_keys = 1`.
#
#   Unfortunately, there doesn't seem to be any way to isolate the cause of the foreign key error
#   other than bisecting by commenting out sections of SQL.
#
#   Some foreign key constraint violations are reported normally; I've no clue what makes the
#   difference.

def run():
	# try:
	# 	os.remove(apsw_ext.DB_PATH)
	# except FileNotFoundError:
	# 	pass

	apsw_ext.init()
	apsw_ext.drop_all_tables_and_indexes()
	db = apsw_ext.connect()

	with db:
		apsw_ext.execute_script(db, 'schema.sql')

	with db:
		apsw_ext.execute_script(db, 'seed.sql')

	extractor_modules = (
		abilities,
		types,
		moves,
		items,
		metadata,
		pokemon2,
		tm,
		trainertypes,
		trainers,
		encounters
	)

	for module in extractor_modules:
		print(module.__name__)
		module.extract(db)

	with db:
		apsw_ext.execute_script(db, 'post_seed.sql')

if __name__ == '__main__':
	run()