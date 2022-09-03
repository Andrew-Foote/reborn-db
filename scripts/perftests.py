# A few performance tests to check that I understand how SQL/SQLite/APSW work correctly.
#
# I was wondering if it was faster to do an entire bulk insert with a single call to execute(), or
# break it up per row but use the same cursor for each row, or to just insert each row at a time on
# a separate cursor. (In each case, on a single connection and within a single transaction, since
# I already know that it's much faster that way.)

from abc import ABC
import apsw
from pathlib import Path
import statistics
import time

test_cases = []
DB_PATH = Path('test.db')
ROW_COUNT = 2500

class TestCase(ABC):
    def setup(self): ...
    def teardown(self): ...
    def run(self): ...

    def timeit(self):
        #t = timeit.timeit('self.setup(); self.run()', 'import gc; gc.enable()', number=25, globals={'self': self})
        ts = []

        for _ in range(10):
            self.setup()
            t0 = time.perf_counter()
            self.run()
            t1 = time.perf_counter()
            ts.append(t1 - t0)
            self.teardown()

        print('{}: time in seconds: mean {:.2f} s, min {:.2f} s, max {:.2f} s'.format(
            self.__class__.__name__, statistics.mean(ts), min(ts), max(ts) 
        ))

def test_case(cls):
    test_cases.append(cls)

@test_case
class SingleQuery(TestCase):
    def setup(self): 
        DB_PATH.unlink(missing_ok=True)
        self.db = apsw.Connection(str(DB_PATH))
        self.db.cursor().execute('create table x (y)')

    def teardown(self):
        self.db.close()

    def run(self):
        with self.db:
            self.db.cursor().execute(
                'insert into x (y) values {}'.format(','.join(f'({y})' for y in range(ROW_COUNT)))
            )

@test_case
class SingleCursor(TestCase):
    def setup(self):
        DB_PATH.unlink(missing_ok=True)
        self.db = apsw.Connection(str(DB_PATH))
        self.db.cursor().execute('create table x (y)')
        self.cursor = self.db.cursor()
    
    def teardown(self):
        self.db.close()

    def run(self):
        with self.db:
            for y in range(ROW_COUNT):
                self.cursor.execute('insert into x (y) values (?)', (y,))

@test_case
class SingleConnection(TestCase):
    def setup(self):
        DB_PATH.unlink(missing_ok=True)
        self.db = apsw.Connection(str(DB_PATH))
        self.db.cursor().execute('create table x (y)')
    
    def teardown(self):
        self.db.close()

    def run(self):
        with self.db:
            for y in range(ROW_COUNT):
                self.db.cursor().execute('insert into x (y) values (?)', (y,))

# The results seem to indicate that... it basically doesn't matter which of these ways you do it.
# I guess for inserts like this, I should just do it whatever way's simplest (probably one cursor
# per row most of the time, but it might vary depending on the context of the surrounding code).
#
# For selects, it's probably desirable to do everything in one query, simply because that means we
# have to do less post-processing on the query result in Python, which is relatively slow.

@test_case
class Join(TestCase):
    def setup(self):
        DB_PATH.unlink(missing_ok=True)
        self.db = apsw.Connection(str(DB_PATH))

        with self.db:
            self.db.cursor().execute('create table x (id, name, y_id); create table y (id, name);')

            for i in range(ROW_COUNT):
                self.db.cursor().execute('insert into x (id, name, y_id) values (?, ?, ?)', (i, i, i))
                self.db.cursor().execute('insert into y (id, name) values (?, ?)', (i, i))

    def teardown(self):
        self.db.close()

    def run(self):
        with self.db:
            data = list(self.db.cursor().execute(
                'select x.name, y.name from x join y on y.id = x.y_id'
            ))

@test_case
class NPlusOne(TestCase):
    def setup(self):
        DB_PATH.unlink(missing_ok=True)
        self.db = apsw.Connection(str(DB_PATH))

        with self.db:
            self.db.cursor().execute('create table x (id, name, y_id); create table y (id, name);')

            for i in range(ROW_COUNT):
                self.db.cursor().execute('insert into x (id, name, y_id) values (?, ?, ?)', (i, i, i))
                self.db.cursor().execute('insert into y (id, name) values (?, ?)', (i, i))

    def teardown(self):
        self.db.close()

    def run(self):
        with self.db:
            #fulldata = []
            data = self.db.cursor().execute('select name, y_id from x')

            for x_name, y_id in data:
                y_name = list(self.db.cursor().execute('select name from y where id = ?', (y_id,)))[0][0]
                #fulldata.append((x_name, y_name))

# NPlusOne does take considerably longer, but I suspect it's mainly because it involves more action from Python
# in fact I suppose we could profile that

for tc in test_cases:
    tc().timeit()
