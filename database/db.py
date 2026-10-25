"""SQLite access (built-in sqlite3 only). Every query elsewhere in the app is parameterized."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def db_path() -> str:
    return os.getenv("PLACETRACK_DB", str(ROOT / "placetrack.db"))


def connect(path: str = None) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced.

    isolation_level=None puts the driver in autocommit mode so that transactions are
    controlled explicitly by transaction() below.
    """
    conn = sqlite3.connect(path or db_path(), isolation_level=None, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """BEGIN IMMEDIATE ... COMMIT, or ROLLBACK if anything raises. Not re-entrant."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def init_db(conn: sqlite3.Connection, seed_samples: bool = True) -> None:
    """Create tables if missing (safe to call on every start) and seed sample drives once."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("PRAGMA foreign_keys = ON")
    if seed_samples:
        from database.seed import seed_sample_drives
        seed_sample_drives(conn)
