from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator
import apsw

Collation = Callable[[str, str], int]

class Connection:
    def __init__(self, db_path: Path) -> None:
        self.apsw = apsw.Connection(str(db_path))
        self.exec('pragma foreign_keys = 1')
        
        # i don't remember why i commented this out#
    def close(self, analysis_limit: int) -> None:
       self.analyze(analysis_limit)
       self.apsw.close()

    def register_function(
        self, name: str, argcount: int, deterministic: bool
    ) -> Callable[[apsw.ScalarProtocol], apsw.ScalarProtocol]:
    
        def decorator(callback: apsw.ScalarProtocol) -> apsw.ScalarProtocol:
            self.apsw.create_scalar_function(name, callback, argcount, deterministic=deterministic)
            return callback

        return decorator

    def register_aggregate(
        self, name: str, argcount: int=-1
    ) -> Callable[[apsw.AggregateFactory], apsw.AggregateFactory]:
        
        def decorator(callback: apsw.AggregateFactory) -> apsw.AggregateFactory:
            self.apsw.create_aggregate_function(name, callback, argcount)
            return callback

        return decorator
    
    def register_collation(self, name: str) -> Callable[[Collation], Collation]:
        def decorator(callback: Collation) -> Collation:
            self.apsw.create_collation(name, callback)
            return callback

        return decorator

    def exec(self, query: str, params: apsw.Bindings | None=None) -> apsw.Cursor:
        """Execute an SQL query on the database using a fresh cursor.

        As far as I can tell, there is no appreciable performance benefit to reusing cursors
        between queries, so you might as well always use this method and forget that cursors
        exist."""
        return self.apsw.cursor().execute(query, params)

    def execscript(self, path: Path, params: apsw.Bindings | None=None) -> apsw.Cursor:
        with open(path, encoding='utf-8') as f:
            return self.exec(f.read(), params)

    def exec1(self, query: str, params: apsw.Bindings | None=None) -> Iterator[apsw.SQLiteValue]:
        """Execute an SQL query that returns rows with one column each, and return an iterator over
        the column values.
        
        Raises an error if a row has more than one column, when that row is encountered."""
        for val, in self.exec(query, params): yield val

    def exec11(self, query: str, params: apsw.Bindings | None=None) -> apsw.SQLiteValue:
        """Execute an SQL query that returns a single row with a single column, and return the
        value in the row. If no matching row can be found then None is returned."""
        
        for val, in self.exec(query, params): return val

    def analyze(self, limit: int) -> None:
        self.exec(f'pragma analysis_limit = {limit}')
        self.exec('pragma optimize')

    @contextmanager
    def transaction(self, *, foreign_keys_enabled: bool | None=None) -> Iterator[None]:
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

        if (
            foreign_keys_enabled is not None
            and foreign_keys_already_enabled is not None
            and foreign_keys_already_enabled != foreign_keys_enabled
        ):
            self.exec(f'pragma foreign_keys = {int(foreign_keys_already_enabled)}')

    def dropall(self, exceptions: tuple[str, ...]=()) -> None:
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

    def quote(self, name: str) -> str:
        return f'"{name}"'

    def bulk_insert(
        self,
        table: str,
        columns: tuple[str, ...] | None,
        data: tuple[tuple[str, ...], ...],
        *,
        debug: bool=False
    ) -> None:
        
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

    def dump_as_table(
        self,
        name: str,
        columns: tuple[str, ...] | None,
        data: tuple[tuple[str, ...], ...]
    ) -> None:
        
        if columns is None:
            numcols = len(data[0])
            columns = tuple(f'col{i}' for i in range(numcols))

        collist = ', '.join(map(self.quote, columns))
        self.exec('create table {} ({})'.format(name, collist))
        self.bulk_insert(name, columns, data)