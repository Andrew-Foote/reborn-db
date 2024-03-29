from contextlib import contextmanager
import apsw

class Connection:
    def __init__(self, db_path):
        self.apsw = apsw.Connection(str(db_path))
        self.apsw.enable_load_extension(True)
        self.apsw.load_extension('C:/programs/sqlean/define')
        self.apsw.load_extension('C:/programs/sqlean/regexp')
        self.exec('pragma foreign_keys = 1')
        
        # i don't remember why i commented this out#
#    def close(self):
#        self.analyze()
#        self.apsw.close()

    def register_function(self, name, argcount, deterministic):
        def decorator(callback):
            self.apsw.createscalarfunction(name, callback, argcount, deterministic=deterministic)
            return callback

        return decorator

    def register_aggregate(self, name, argcount=-1):
        def decorator(callback):
            self.apsw.createaggregatefunction(name, callback, argcount)
            return callback

        return decorator

    def register_collation(self, name):
        def decorator(callback):
            self.apsw.createcollation(name, callback)
            return callback

        return decorator

    def exec(self, query, params=None):
        """Execute an SQL query on the database using a fresh cursor.

        As far as I can tell, there is no appreciable performance benefit to reusing cursors
        between queries, so you might as well always use this method and forget that cursors
        exist."""
        return self.apsw.cursor().execute(query, params)

    def execscript(self, path, params=None):
        with open(path, encoding='utf-8') as f:
            return self.exec(f.read(), params)

    def exec1(self, query, params=None):
        """Execute an SQL query that returns rows with one column each, and return an iterator over
        the column values.
        
        Raises an error if a row has more than one column, when that row is encountered."""
        for val, in self.exec(query, params): yield val

    def exec11(self, query, params=None):
        """Execute an SQL query that returns a single row with a single column, and return the
        value in the row. If no matching row can be found then None is returned."""
        
        for val, in self.exec(query, params): return val

    def analyze(self, limit):
        self.exec(f'pragma analysis_limit = {limit}')
        self.exec('pragma optimize')

    @contextmanager
    def transaction(self, *, foreign_keys_enabled=None):
        """Return a context manager that will begin a transaction on entry and end it on exit.
        
        If the user wants to temporarily disable foreign keys for the duration of the transaction
        (or enable it, if foreign keys are currently disabled) then they can do so by passing
        `True` or `False` for the `foreign_keys_enabled` argument. Enabling or disabling foreign
        keys is a no-op in SQLite when it occurs within a transaction, so this method is designed
        to encourage the user to do the enabled or disabling at the transaction boundary in order
        to avoid nasty surprises."""

        foreign_keys_already_enabled = None

        if foreign_keys_enabled is not None:
            foreign_keys_already_enabled = bool(self.exec11(f'pragma foreign_keys'))

            if foreign_keys_already_enabled != foreign_keys_enabled:
                self.exec(f'pragma foreign_keys = {int(foreign_keys_enabled)}')

        with self.apsw:
            yield None

        if foreign_keys_enabled is not None and foreign_keys_already_enabled != foreign_keys_enabled:
            self.exec(f'pragma foreign_keys = {int(foreign_keys_already_enabled)}')

    def dropall(self, exceptions=()):
        """Drop all tables and views, resetting the database to an empty state. (Indexes and
        triggers will automatically be deleted when their parent tables are deleted.)
        
        This only works outside of a transaction.

        You can select some tables or views to keep with the exceptions parameter.
        """

        exception_placeholders = ', '.join('?' for _ in exceptions)

        with self.transaction(foreign_keys_enabled=False):
            views = [name for name, in self.exec(
                f'select "name" from "sqlite_master" where "type" = ? and "name" not in ({exception_placeholders})',
                ('view', *exceptions)
            )]

            for view in views:
                print(f'dropping view {view}')
                self.exec(f'drop view {view}')

            tables = [name for name, in self.exec(
                f'select "name" from "sqlite_master" where "type" = ? and "name" not like ? and "name" not in ({exception_placeholders})',
                ('table', 'sqlite_%', *exceptions)
            )]

            for table in tables:
                print(f'dropping table {table}')
                self.exec(f'drop table {table}')

            # No need to delete indexes and triggers separately; they get deleted along with their
            # parent tables.

    def quote(self, name):
        return f'"{name}"'

    def bulk_insert(self, table, columns, data, *, debug=False):
        """Do a bulk insert into a table of data given in a simple row-by-row format.

        This method will execute one query per row, so make sure to call it within a transaction to
        avoid abysmal performance.

        Note that for complex bulk inserts where you are not simply copying the data directly into
        the table, it's best to do it in two steps: first, write the data into an intermediate
        table using `dump_as_table`, then call `exec` and write out an `insert` statement that uses
        the data from that temp table."""

        collist = '' if columns is None else ' ({})'.format(', '.join(map(self.quote, columns)))
        placeholders = ', '.join(('?',) * len(columns))

        for row in data:
            query = f'insert into {table}{collist} values ({placeholders})'
            if debug: print(query, row)
            self.exec(query, row)

    def dump_as_table(self, name, columns, data):
        if columns is None:
            numcols = len(data[0])
            columns = tuple(f'col{i}' for i in range(numcols))

        collist = ', '.join(map(self.quote, columns))
        self.exec('create table {} ({})'.format(name, collist))
        self.bulk_insert(name, columns, data)

    def last_insert_rowid(self):
        return self.apsw.last_insert_rowid()