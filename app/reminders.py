import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config import settings
from app.db import get_conn, now_utc
from app.texts import DOSE_UNIT, REASON_BUTTONS, TEXTS, WORDS
from app.whatsapp import send_buttons, send_template, send_text

BEIRUT = ZoneInfo("Asia/Beirut")
WINDOW = timedelta(minutes=10)


def lang_of(row):
    return "ar" if row["language"] == "ar" else "en"


def event_info(conn, event_id):
    return conn.execute(
        """SELECT e.id,
                  e.status,
                  e.due_at,
                  e.reason,
                  e.reply_text,
                  s.dose_amount,
                  m.id AS medicine_id,
                  m.display_name,
                  u.id AS user_id,
                  u.phone,
                  u.name,
                  u.language
           FROM dose_events e
                    JOIN schedules s ON s.id = e.schedule_id
                    JOIN medicines m ON m.id = s.medicine_id
                    JOIN users u ON u.id = m.patient_id
           WHERE e.id = ?""",
        (event_id,),
    ).fetchone()


async def send_event(event_id):
    with get_conn() as conn:
        info = event_info(conn, event_id)
    lang = lang_of(info)
    await send_template(
        info["phone"], "dose_reminder", lang,
        {"patient_name": info["name"], "medicine": info["display_name"],
         "dose": f"{info['dose_amount']:g} {DOSE_UNIT[lang]}"},
        [f"TAKEN:{event_id}", f"LATER:{event_id}", f"PROBLEM:{event_id}"],
    )


async def send_reminder(schedule_id, due=None):
    due = due or datetime.now(BEIRUT)
    due_at = due.astimezone(timezone.utc).isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO dose_events (schedule_id, due_at) VALUES (?, ?)",
            (schedule_id, due_at),
        )
        event_id = cur.lastrowid if cur.rowcount else None
    if event_id:
        await send_event(event_id)
    return event_id


async def send_due_reminders():
    now = datetime.now(BEIRUT)
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT s.id, s.time_of_day
               FROM schedules s
                        JOIN medicines m ON m.id = s.medicine_id
                        JOIN users u ON u.id = m.patient_id
               WHERE s.active = 1
                 AND m.active = 1
                 AND u.consent = 1"""
        ).fetchall()
    for row in rows:
        hour, minute = map(int, row["time_of_day"].split(":"))
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if timedelta(0) <= now - due <= WINDOW:
            await send_reminder(row["id"], due)


async def resend_later():
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.LATER_MINUTES)
    cutoff = cutoff.isoformat(timespec="seconds")
    with get_conn() as conn:
        # STEP 9: only for patients who still agree (not after STOP)
        rows = conn.execute(
            """SELECT e.id FROM dose_events e
               JOIN schedules s ON s.id = e.schedule_id
               JOIN medicines m ON m.id = s.medicine_id
               JOIN users u ON u.id = m.patient_id
               WHERE e.status = 'later' AND e.responded_at <= ? AND u.consent = 1""",
            (cutoff,),
        ).fetchall()
        for row in rows:  # STEP 9
            conn.execute("UPDATE dose_events SET status = 'pending' WHERE id = ?", (row["id"],))
    for row in rows:
        await send_event(row["id"])


async def scheduler_loop():
    from app.care import alert_unanswered  # STEP 6: imported here because care.py imports this file
    while True:
        try:
            await send_due_reminders()
            await resend_later()
            await alert_unanswered()  # STEP 6
        except Exception as e:
            print("Scheduler error:", e)
        await asyncio.sleep(30)


def word_action(text):
    word = text.strip().lower().strip(".!?,،()")
    if len(word.split()) != 1:
        return None
    for action, keys in WORDS.items():
        if word in keys or any(len(k) > 1 and word.startswith(k) for k in keys):
            return action
    return None


def open_event_id(conn, user_id):
    row = conn.execute(
        """SELECT e.id
           FROM dose_events e
                    JOIN schedules s ON s.id = e.schedule_id
                    JOIN medicines m ON m.id = s.medicine_id
           WHERE m.patient_id = ?
             AND e.status IN ('pending', 'later')
           ORDER BY e.due_at DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    return row["id"] if row else None


async def handle_dose_reply(user, action, event_id=None):
    """action is TAKEN, LATER or PROBLEM. Returns False if there is no dose to answer."""
    with get_conn() as conn:
        event_id = event_id or open_event_id(conn, user["id"])
        info = event_info(conn, event_id) if event_id else None
        if info is None or info["user_id"] != user["id"]:
            return False
        status = {"TAKEN": "taken", "LATER": "later", "PROBLEM": "missed"}[action]
        conn.execute(
            "UPDATE dose_events SET status = ?, responded_at = ? WHERE id = ?",
            (status, now_utc(), event_id),
        )
        if action == "TAKEN" and info["status"] != "taken":
            conn.execute(
                "UPDATE medicines SET tablets_left = tablets_left - ? WHERE id = ?",
                (info["dose_amount"], info["medicine_id"]),
            )
    lang, to, medicine = lang_of(info), info["phone"], info["display_name"]
    if action == "TAKEN":
        await send_text(to, TEXTS["taken"][lang].format(medicine=medicine))
    elif action == "LATER":
        await send_text(to, TEXTS["later"][lang].format(minutes=settings.LATER_MINUTES))
    else:
        buttons = [(f"REASON:{event_id}:{key}", title) for key, title in REASON_BUTTONS[lang]]
        await send_buttons(to, TEXTS["problem"][lang].format(medicine=medicine), buttons)
    return True


async def handle_text(user, text):
    """Typed reply to a reminder. Returns False if the user has no open dose."""
    action = word_action(text)
    if action:
        return await handle_dose_reply(user, action)
    with get_conn() as conn:
        event_id = open_event_id(conn, user["id"])
        info = event_info(conn, event_id) if event_id else None
    if info is None:
        return False
    help_text = TEXTS["help"][lang_of(info)].format(medicine=info["display_name"])
    await send_text(info["phone"], help_text)
    return True