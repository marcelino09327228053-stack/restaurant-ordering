"""Run separately: python tests/test_sqlite_connections.py."""
import os
import sys
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory() as folder:
    os.environ['DATABASE_URL'] = ''
    os.environ['SQLITE_PATH'] = str(Path(folder) / 'connections.db')
    from app.db import get_connection
    main = get_connection()
    main.executescript('CREATE TABLE parent(id INTEGER PRIMARY KEY); CREATE TABLE child(parent_id INTEGER REFERENCES parent(id));')
    barrier = Barrier(2)
    def check(value):
        conn = get_connection()
        try:
            assert conn is get_connection()
            assert conn is not main
            assert conn.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
            assert conn.execute('PRAGMA busy_timeout').fetchone()[0] == 30000
            assert conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1
            barrier.wait(timeout=10)
            conn.execute('INSERT INTO parent VALUES (?)', (value,))
            if value == 1:
                conn.rollback()
            else:
                conn.commit()
            return id(conn)
        finally:
            conn.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        connections = list(pool.map(check, [1, 2]))
    assert len(set(connections)) == 2
    assert [row[0] for row in main.execute('SELECT id FROM parent')] == [2]
    import sqlite3
    try:
        main.execute('INSERT INTO child VALUES (999)')
        raise AssertionError('Foreign key enforcement missing')
    except sqlite3.IntegrityError:
        main.rollback()
    main.close()
print('PASS: per-thread reuse, separate connections, WAL, busy timeout, isolated commit/rollback, foreign keys')
