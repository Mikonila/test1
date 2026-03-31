import os
import sqlite3
from pathlib import Path
from threading import local

DB_PATH = Path(__file__).parent / "data" / "anxiety_support.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_local = local()


def get_db() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _local.conn = conn
    return _local.conn


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date_key TEXT NOT NULL,
            mood INTEGER NOT NULL,
            anxiety_level INTEGER NOT NULL,
            energy_level INTEGER,
            sleep_hours REAL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, date_key),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            mood_tag TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS exercise_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            intensity INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS relief_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            technique TEXT NOT NULL,
            before_level INTEGER,
            after_level INTEGER,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_checkins_user_date ON checkins(user_id, date_key);
        CREATE INDEX IF NOT EXISTS idx_journal_user_created ON journal_entries(user_id, created_at);
    """)
    db.commit()


def upsert_user(tg_user: dict) -> sqlite3.Row:
    db = get_db()
    db.execute(
        """
        INSERT INTO users (telegram_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            last_seen_at = CURRENT_TIMESTAMP
        """,
        (
            str(tg_user.get("id")),
            tg_user.get("username"),
            tg_user.get("first_name"),
            tg_user.get("last_name"),
        ),
    )
    db.commit()
    return db.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (str(tg_user.get("id")),)
    ).fetchone()


init_db()
