import os
import sqlite3
from pathlib import Path


def connect(path=None):
    path = str(path or os.getenv('FLARE_DB', 'data/flare.sqlite3'))
    if path != ':memory:':
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=5000')
    return conn


def migrate(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)')
    for path in sorted(Path(__file__).with_name('migrations').glob('*.sql')):
        if not conn.execute('SELECT 1 FROM schema_migrations WHERE version=?', (path.name,)).fetchone():
            # executescript commits first; explicit transaction makes each migration atomic.
            script = "BEGIN IMMEDIATE;\n" + path.read_text() + "\nINSERT INTO schema_migrations VALUES ('" + path.name + "');\nCOMMIT;"
            try:
                conn.executescript(script)
            except Exception:
                conn.rollback()
                raise


def get_source(conn, name):
    conn.execute('INSERT OR IGNORE INTO sources(name) VALUES (?)', (name,))
    return conn.execute('SELECT id FROM sources WHERE name=?', (name,)).fetchone()[0]
