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

CREATE TABLE IF NOT EXISTS care_links (
    id                  INTEGER PRIMARY KEY,
    caregiver_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_on_missed     INTEGER NOT NULL DEFAULT 1 CHECK (alert_on_missed IN (0, 1)),
    alert_after_minutes INTEGER NOT NULL DEFAULT 60,
    created_at          TEXT NOT NULL,
    UNIQUE (caregiver_id, patient_id),
    CHECK (caregiver_id != patient_id)
);

CREATE TABLE IF NOT EXISTS drug_reference (
    id          INTEGER PRIMARY KEY,
    moph_code   TEXT UNIQUE,
    brand_name  TEXT NOT NULL,
    ingredients TEXT,
    strength    TEXT,
    form        TEXT,
    pack_size   TEXT,
    price_lbp   INTEGER
);

CREATE TABLE IF NOT EXISTS voice_clips (
    id          INTEGER PRIMARY KEY,
    recorded_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_path   TEXT NOT NULL,
    wa_media_id TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS medicines (
    id           INTEGER PRIMARY KEY,
    patient_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    drug_id      INTEGER REFERENCES drug_reference(id),
    display_name TEXT NOT NULL,
    pack_size    INTEGER,
    tablets_left REAL,
    active       INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id            INTEGER PRIMARY KEY,
    medicine_id   INTEGER NOT NULL REFERENCES medicines(id) ON DELETE CASCADE,
    time_of_day   TEXT NOT NULL
                  CHECK (time_of_day GLOB '[0-2][0-9]:[0-5][0-9]'),
    dose_amount   REAL NOT NULL DEFAULT 1,
    voice_clip_id INTEGER REFERENCES voice_clips(id) ON DELETE SET NULL,
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS dose_events (
    id           INTEGER PRIMARY KEY,
    schedule_id  INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    due_at       TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'taken', 'later', 'missed')),
    reason       TEXT CHECK (reason IN ('forgot', 'ran_out', 'side_effect',
                                        'cost', 'other')),
    reply_text   TEXT,
    responded_at TEXT,
    UNIQUE (schedule_id, due_at)
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