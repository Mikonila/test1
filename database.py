import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "anxiety.db"
_local = threading.local()


def get_db() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


def init_db() -> None:
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id       INTEGER UNIQUE NOT NULL,
            username    TEXT,
            first_name  TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS checkins (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            date_key   TEXT NOT NULL,
            mood       INTEGER,
            anxiety    INTEGER,
            energy     INTEGER,
            sleep      REAL,
            notes      TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, date_key)
        );

        CREATE TABLE IF NOT EXISTS journal_entries (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            prompt     TEXT,
            response   TEXT,
            tag        TEXT DEFAULT 'journal',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS exercise_logs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL REFERENCES users(id),
            exercise_type TEXT,
            seconds       INTEGER DEFAULT 0,
            created_at    TEXT DEFAULT (datetime('now'))
        );
    """)
    db.commit()


def upsert_user(tg_user: dict) -> int:
    """Insert or update user, return internal db id."""
    db = get_db()
    db.execute(
        """
        INSERT INTO users (tg_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET
            username   = excluded.username,
            first_name = excluded.first_name
        """,
        (tg_user["id"], tg_user.get("username"), tg_user.get("first_name")),
    )
    db.commit()
    row = db.execute("SELECT id FROM users WHERE tg_id=?", (tg_user["id"],)).fetchone()
    return row["id"]
