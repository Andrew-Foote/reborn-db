import apsw
import base64
from fractions import Fraction as frac
import itertools as it
import sys
import traceback
from reborndb import sql

# Callbacks which SQLite will use for storing frac objects

def is_frac(x):
	try:
		frac(x)
	except ValueError:
		return 0

	return 1

def frac_collate(x, y):
	if frac(x) < frac(y):
		return -1
	
	if frac(x) > frac(y):
		return 1
	
	return 0

def frac_mul(x, y):
	return str(frac(x) * frac(y))

def b64encode(blob):
	if blob is None:
		return None

	return base64.b64encode(blob).decode('ascii')

INITED = False

def error_handler(errcode, message):
	errstr = apsw.mapping_result_codes[errcode & 255]
	extended = errcode # & ~ 255 [was in the example in the APSW docs but seems to be wrong]
	extended_errstr = apsw.mapping_extended_result_codes.get(extended, "")
	print(f'SQLITE_LOG: {message} ({errcode}) {errstr} {extended_errstr}')

def init():
	global INITED

	if not INITED:	
		apsw.config(apsw.SQLITE_CONFIG_LOG, error_handler)
		INITED = True

def exit(db):
	db.cursor().execute('PRAGMA analysis_limit=400')
	db.cursor().execute('PRAGMA optimize')

DB_PATH = 'site/db.sqlite'
DB_DICT = {}

def connect(fname=DB_PATH, *, force_new=False, force_global=False, foreign_keys=1):
	"""Return a SQLite database connection.

	If `force_new` is `False` (the default), an existing database connection with the same settings
	will be reused, if it exists. The settings are the values of the arguments to this function
	other than `force_new` and `force_global`.

	If `force_global` is `True`, then when this function does return a new database connection, it
	will also replace the currently-registered existing database connection with the same settings
	with the new one, if there is one. By default the existing one is left alone so that subsequent
	connections may still reuse it."""

	settings = (('fname', fname), ('foreign_keys', foreign_keys))

	if not force_new and settings in DB_DICT:
		return DB_DICT[settings]
	
	db = apsw.Connection(fname)
	db.cursor().execute(f'pragma foreign_keys = {foreign_keys}')

	db.createcollation('frac', frac_collate)
	db.createscalarfunction('is_frac', is_frac, 1, True)
	db.createscalarfunction('frac_mul', frac_mul, 2, True)
	db.createscalarfunction('base64', b64encode, 1, True)

	if settings not in DB_DICT or force_global:
		DB_DICT[settings] = db

	return db

def drop_all_tables_and_indexes():
	# Use a new connection, both to turn off foreign key constraint enforcement, and to ensure that
	# the "drop table" statements don't fail due to another statement on the same connection still
	# being active
	db = connect(force_new=True, foreign_keys=0)

	# The indexes SQLite automatically generates for "primary key" and "unique" constraints, which
	# are identifiable by having an "sqlite_" prefix to their name, can't be deleted as indexes
	# (they get deleted along with the table they're on).
	schema = list(db.cursor().execute(
		'''
			select "name", "type", "tbl_name" from "sqlite_master"
			where "type" in (?, ?, ?) and not ("type" = ? and "name" like ?)
		''',
		('table', 'index', 'view', 'index', 'sqlite_%')
	))

	tables = set()

	with db:
		for name, object_type, table in schema:
			match object_type:
				case 'table':
					tables.add(name)
				case 'index':
					db.cursor().execute(f'drop index {name}')
				case 'view':
					db.cursor().execute(f'drop view {name}')

		for table in tables:
			db.cursor().execute(f'drop table {table}')

def execute_script(db, fname):
	with open(fname, encoding="utf-8") as f:
		s = f.read()
		return db.cursor().execute(s)

class ExplicitRollback(Exception):
	pass

class BulkInsertError(Exception):
	def __init__(self, orig, row=None):
		self.orig = orig
		self.row = row

	def __str__(self):
		if self.row is None:
			message = 'bulk insert failed (no single row could be identified as the cause; it might be an intermittent error)'
		else:
			message = f'insert failed for this row:\n  {self.row}'

		return f'{message}\nOriginal exception:\n' + ''.join(traceback.format_exception(self.orig))

POTENTIAL_SQL_ERRORS = (apsw.SQLError, apsw.ConstraintError, SystemError, TypeError)

def bulk_insert(db, table, columns, data):
	if not data:
		raise ValueError('bulk insert of empty dataset')

	rows_per_stmt = 32766 // len(columns)

	for i in range(0, len(data) // rows_per_stmt + 1):
		chunk = data[i * rows_per_stmt:(i + 1) * rows_per_stmt]
		#print(f'rows_per_stmt {rows_per_stmt}, column count {len(columns)}, chunk size {len(chunk)}')

		query = 'insert into `{}` ({})\nvalues\n{};'.format(
			table,
			', '.join(f'`{column}`' for column in columns),
			sql.placeholders_table(chunk)
		)

		#db.cursor().execute(query, it.chain.from_iterable(chunk))

		try:
			db.cursor().execute(query, it.chain.from_iterable(chunk))
		except POTENTIAL_SQL_ERRORS as e:
			# for i in range(1, len(chunk) + 1):
			# 	subchunk = chunk[:i]

			# 	query = 'insert into `{}` ({})\nvalues\n{}'.format(
			# 		table,
			# 		', '.join(f'`{column}`' for column in columns),
			# 		sql.placeholders_table(subchunk)
			# 	)

			# 	class RollbackWithoutException(Exception):
			# 		pass

			# 	try:
			# 		with db:
			# 			db.cursor().execute(query, it.chain.from_iterable(subchunk))
			# 			raise RollbackWithoutException
			# 	except POTENTIAL_SQL_ERRORS:
			# 		raise BulkInsertError(e, {column: value for column, value in zip(columns, subchunk[-1])}) from None
			# 	except RollbackWithoutException:
			# 		pass

			# raise BulkInstertError(e) from None

			def test(lb, ub):
				subchunk = chunk[lb:ub]

				query = 'insert into "{}" ({}) values {};'.format(
					table,
					', '.join(f'"{column}"' for column in columns),
					sql.placeholders_table(subchunk)
				)

				try:
					with db:
						db.cursor().execute(query, it.chain.from_iterable(subchunk))
						raise ExplicitRollback
				except POTENTIAL_SQL_ERRORS:
					return 'fail'
				except ExplicitRollback:
					return 'pass'

			# ok, it's standard binary search if we can guarantee that
			# we find the leftmost element
			# 0 = pass, 1 = fail, we're trying to find the leftmost 1
			# our array consists of all the indices we can test (i.e. 0 ... n inclusive, so n + 1 elements)
			# 

			lb, ub = 0, len(chunk)

			while lb < ub:
				print(lb, ub)
				m = (lb + ub) // 2
				status = test(0, m + 1)

				if status == 'pass':
					lb = m + 1
				else:
					ub = m

			row = chunk[lb]
			raise BulkInsertError(e, {column: value for column, value in zip(columns, row)}) from None


			# shoddy implementation of binary search follows...
			# for given lb, ub we can test all the rows from lb and ub and see
			# if we get "pass" (no exception found) or "fail" (exception found)
			# we want to find the first "fail", i.e. the unique "fail" preceded only by "pass"es
			# so we take a midpoint and check if it fails or not
			# if [lb:ub] fails for some given lb, ub, what do we know?
			#   - the failure is somewhere within that range
			# [lb:ub] passes - the failure is above ub

			# lb = 0
			# prev_ub = None
			# ub = len(chunk)
			# prev_mid = None
			# mid = 0
			# status = 'fail'

			# while lb != ub and prev_mid != prev_ub:
			# 	print(lb, ub, status, prev_mid, prev_ub)
			# 	input()
			# 	prev_mid = mid
			# 	mid = lb + (ub - lb) // 2
			# 	status = test(lb, ub)
				
			# 	if status == 'fail':
			# 		prev_ub = ub
			# 		ub = mid
			# 	elif status == 'pass':
			# 		lb = prev_mid
			# 		ub = prev_ub

			# print(lb, ub, status, prev_mid, prev_ub)
			# row = chunk[lb]
			# raise BulkInsertError(e, {column: value for column, value in zip(columns, row)}) from None

def bulk_insert_multi(db, rows, *, in_transaction=False):
	for table, table_rows in rows.items():
		if not table_rows:
			continue

		columns = table_rows[0].keys()
		rows_as_lists = []

		for row in table_rows:
			if not set(columns).issubset(set(row.keys())):
				raise ValueError('row missing values for columns ' + ', '.join(f'"{col}"' for col in set(columns) - set(row.keys())) + f'\n  {row}')

			rows_as_lists.append([row[column] for column in columns])

		# By default, each table will be done in a separate transaction, as that's most convenient
		# for debugging foreign key issues.
		if not in_transaction:
			with db:
				bulk_insert(db, table, columns, rows_as_lists)