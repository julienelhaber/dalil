import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "dalil.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY,
    phone           TEXT UNIQUE,
    wa_user_id      TEXT UNIQUE,
    name            TEXT,
    language        TEXT CHECK (language IN ('ar', 'en', 'fr')),
    channel         TEXT NOT NULL DEFAULT 'whatsapp'
                    CHECK (channel IN ('whatsapp', 'sms')),
    consent         INTEGER NOT NULL DEFAULT 0 CHECK (consent IN (0, 1)),
    last_inbound_at TEXT,
    created_at      TEXT NOT NULL,
    CHECK (phone IS NOT NULL OR wa_user_id IS NOT NULL)
);
"""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def find_user(conn, wa_user_id: str | None, phone: str | None):
    if wa_user_id:
        row = conn.execute(
            "SELECT * FROM users WHERE wa_user_id = ?", (wa_user_id,)
        ).fetchone()
        if row:
            return row
    if phone:
        return conn.execute(
            "SELECT * FROM users WHERE phone = ?", (phone,)
        ).fetchone()
    return None


def upsert_inbound_user(wa_user_id: str | None, phone: str | None,
                        name: str | None = None):
    """Find or create the sender and record the inbound time.
    Returns (user_row, is_new)."""
    if phone:
        phone = phone.lstrip("+")
    now = now_utc()
    with get_conn() as conn:
        user = find_user(conn, wa_user_id, phone)
        if user is None:
            cur = conn.execute(
                """INSERT INTO users (phone, wa_user_id, name,
                                      last_inbound_at, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (phone, wa_user_id, name, now, now),
            )
            user_id, is_new = cur.lastrowid, True
        else:
            user_id, is_new = user["id"], False
            conn.execute(
                """UPDATE users
                   SET last_inbound_at = ?,
                       phone      = COALESCE(phone, ?),
                       wa_user_id = COALESCE(wa_user_id, ?),
                       name       = COALESCE(name, ?)
                   WHERE id = ?""",
                (now, phone, wa_user_id, name, user_id),
            )
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return user, is_new