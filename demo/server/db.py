"""One connection per transaction, parameterized values, foreign keys enabled."""
import sqlite3
from contextlib import contextmanager
from . import config

RUNTIME_ACTIONS = {
    sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_INSERT,
    sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE, sqlite3.SQLITE_TRANSACTION,
    sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE,
}


def authorize_runtime(action, first, second, database, source):
    if action == sqlite3.SQLITE_FUNCTION and second in {'load_extension', 'readfile', 'writefile'}:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK if action in RUNTIME_ACTIONS else sqlite3.SQLITE_DENY


@contextmanager
def transaction():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA busy_timeout = 15000')
    conn.execute('PRAGMA trusted_schema = OFF')
    conn.set_authorizer(authorize_runtime)
    try:
        conn.execute('BEGIN IMMEDIATE')
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()

def initialize():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.DB_PATH) as c:
        c.executescript((config.HERE / 'schema.sql').read_text(encoding='utf-8'))
        if 'read_mode' not in {r[1] for r in c.execute('PRAGMA table_info(proofs)')}:
            c.execute("ALTER TABLE proofs ADD COLUMN read_mode TEXT NOT NULL DEFAULT '讀取方式未記錄，請核對'")

def audit(c, actor, case_id, kind, entity, action):
    c.execute('INSERT INTO audit_events(actor_id,case_id,entity_type,entity_id,action,created_at) VALUES(?,?,?,?,?,?)',
              (actor, case_id, kind, entity, action, config.stamp()))
