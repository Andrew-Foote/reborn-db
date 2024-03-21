import atexit
import base64
from fractions import Fraction as frac
import json
from pathlib import Path
import apsw
from reborndb.connection import Connection
from reborndb import settings

def handle_error(errcode: int, message: str) -> None:
    errstr = apsw.mapping_result_codes[errcode & 255]
    extended = errcode # & ~ 255 [was in the example in the APSW docs but seems to be wrong]
    extended_errstr = apsw.mapping_extended_result_codes.get(extended, "")
    print(f'SQLITE_LOG: {message} ({errcode}) {errstr} {extended_errstr}')

apsw.config(apsw.SQLITE_CONFIG_LOG, handle_error)

def altconnect(db_path: Path):
    return Connection(db_path)

connection = None

def connect() -> Connection:
    """Return the database connection, creating it if necessary.

    Once the connection has been created, the cost of calling this method is negligible, so you
    should just use this method repeatedly rather than passing around a db object."""

    global connection

    if connection is None:
        connection = Connection(settings.DB_PATH)
        connection.exec('pragma synchronous = off')

        @atexit.register
        def handle_exit() -> None:
            if connection is not None:
                print('Analyzing database usage...', end=' ')
                connection.close(settings.DB_ANALYSIS_LIMIT)
                print('done.')

        @connection.register_function('is_frac', 1, True)
        def sql_function_is_frac(x: apsw.SQLiteValue) -> int:
            """Check whether a value is a fraction."""
            try:
                frac(x)
            except ValueError:
                return 0
            else:
                return 1

        @connection.register_function('frac2real', 1, True)
        def sql_function_frac2real(x: apsw.SQLiteValue) -> float:
            return float(frac(x))

        @connection.register_function('frac_mul', 2, True)
        def sql_function_frac_mul(x: apsw.SQLiteValue, y: apsw.SQLiteValue) -> str:
            """Multiply two fractions."""
            return str(frac(x) * frac(y))

        @connection.register_function('frac_div', 2, True)
        def sql_function_frac_div(x: apsw.SQLiteValue, y: apsw.SQLiteValue) -> str:
            """Divide two fractions."""
            return str(frac(x) / frac(y))
            
        @connection.register_aggregate('frac_sum', 1)
        def sql_aggregate_frac_sum() -> tuple[
            frac, apsw.AggregateStep, apsw.AggregateFinal
        ]:
            
            result = [frac(0)]
        
            def step(result: frac, val: int) -> None:
                result[0] += frac(val)
            
            return frac(0), step, lambda result: str(result[0])

        @connection.register_collation('frac')
        def sql_collation_frac(x: str, y: str) -> int:
            """Compare two fractions."""
            return (frac(x) > frac(y)) - (frac(x) < frac(y))

        @connection.register_function('base64', 1, True)
        def sql_function_base64(blob: str | None) -> str | None:
            """Encode a blob as base64."""
            return None if blob is None else base64.b64encode(blob).decode('ascii')

        @connection.register_aggregate('df2tree')
        def sql_aggregate_df2tree() -> tuple[
            apsw.AggregateT, apsw.AggregateStep, apsw.AggregateFinal
        ]:

            """Group a set of rows representing nodes into a JSON tree structure.

            Each row must have exactly two columns, the first being the index of the node, and the
            second being the node itself, which must be valid JSON. The rows must be ordered
            depth-first.

            The tree will have a structure like

              [{"node": ..., "children": [{"node": ...}, ...]}, ...]"""

            def step(subtrees: apsw.AggregateT, level: apsw.SQLiteValue, node: apsw.SQLiteValue) -> None:
                if level < len(subtrees):
                    subtree = []
                    subtrees[level + 1:] = [subtree]
                    subtrees[level].append({'node': json.loads(node), 'children': subtree})
                else:
                    raise ValueError('level jumped by more than 1')

            return [[]], step, lambda subtrees: json.dumps(subtrees[0])

        @connection.register_aggregate('evolution_schemes')
        def sql_aggregate_evolution_schemes():
            def step(schemes, base_method, reqs):
                reqs = json.loads(reqs)

                for i, scheme in enumerate(schemes):
                    if (
                        scheme['base_method'] == base_method
                        and set(scheme['requirements'].keys()) == set(reqs.keys())
                    ):
                        new_reqs = {
                            kind: tuple(dict.fromkeys(v + (tuple(reqs[kind]),)))
                            #kind: v | {tuple(reqs[kind])}
                            for kind, v in scheme['requirements'].items()
                        }

                        if sum(1 for vs in new_reqs.values() if len(vs) > 1) <= 1:
                            scheme['requirements'] = new_reqs
                            break
                else:
                    schemes.append({
                        'base_method': base_method,
                        'requirements': {kind: (tuple(v),) for kind, v in reqs.items()}
                        #'requirements': {kind: {tuple(v)} for kind, v in reqs.items()}
                    })

            def bunga(schemes):
                r = json.dumps(schemes, default=tuple)
                return r

            return [], step, bunga

        print(f'Database initialized.')

    return connection

# a bit of magic so we can refer to the database as `DB.H`
# (simply importing `connection` doesn't work because Python globals are only global within their
# parent module's scope)

class _ConnectionHandle:
    @property
    def H(self) -> Connection:
        return connect()

DB: _ConnectionHandle = _ConnectionHandle()