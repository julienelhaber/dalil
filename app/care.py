from datetime import datetime, timedelta, timezone

from app.db import get_conn
from app.reminders import BEIRUT, event_info, lang_of, word_action
from app.texts import REASON_BUTTONS, TEXTS
from app.whatsapp import send_template, send_text


def caregivers(conn, patient_id):
    return conn.execute(
        """SELECT u.* FROM care_links c JOIN users u ON u.id = c.caregiver_id
           WHERE c.patient_id = ? AND c.alert_on_missed = 1 AND u.consent = 1""",
        (patient_id,),
    ).fetchall()


def due_time(info):
    return datetime.fromisoformat(info["due_at"]).astimezone(BEIRUT).strftime("%H:%M")


async def handle_reason(user, event_id, reason, text=None):
    """Patient said why they missed a dose: tell their caregivers."""
    with get_conn() as conn:
        info = event_info(conn, event_id)
        if info is None or info["user_id"] != user["id"]:
            return False
        if info["reason"]:
            return True
        conn.execute(
            "UPDATE dose_events SET reason = ?, reply_text = ? WHERE id = ?",
            (reason, text, event_id),
        )
        family = caregivers(conn, user["id"])
    lang, medicine = lang_of(info), info["display_name"]
    names = ", ".join(c["name"] for c in family)
    reply = TEXTS["thanks"][lang].format(names=names) if family else TEXTS["thanks_alone"][lang]
    if reason == "side_effect":
        reply += "\n\n" + TEXTS["side_effect"][lang].format(medicine=medicine)
    await send_text(info["phone"], reply)
    await alert_family(info, family)  # STEP 6
    return True


# STEP 6: new
async def alert_family(info, family):
    for c in family:
        await send_template(
            c["phone"], "caregiver_alert", lang_of(c),
            {"caregiver_name": c["name"], "patient_name": info["name"],
             "medicine": info["display_name"], "due_time": due_time(info)},
            [f"CHECK:{info['id']}"],
        )


# STEP 6: new
async def alert_unanswered():
    """No answer long after a reminder: mark the dose missed and tell the family."""
    with get_conn() as conn:
        # STEP 9: skip patients who typed STOP (2 new lines in the query: JOIN users, u.consent = 1)
        rows = conn.execute(
            """SELECT DISTINCT e.id FROM dose_events e
               JOIN schedules s ON s.id = e.schedule_id
               JOIN medicines m ON m.id = s.medicine_id
               JOIN users u ON u.id = m.patient_id
               JOIN care_links c ON c.patient_id = m.patient_id
               JOIN users cu ON cu.id = c.caregiver_id  -- PILOT 4: only family who agreed
               WHERE e.status = 'pending' AND c.alert_on_missed = 1 AND u.consent = 1
                 AND cu.consent = 1 AND m.active = 1  -- PILOT 8: not for a stopped medicine
                 AND datetime(e.due_at, '+' || c.alert_after_minutes || ' minutes')
                     <= datetime('now')
                 AND datetime(e.due_at) >= datetime('now', '-3 hours')"""
        ).fetchall()
        for row in rows:
            conn.execute("UPDATE dose_events SET status = 'missed' WHERE id = ?", (row["id"],))
    for row in rows:
        with get_conn() as conn:
            info = event_info(conn, row["id"])
            family = caregivers(conn, info["user_id"])
        await alert_family(info, family)


async def handle_typed_reason(user, text):
    """Free text right after tapping Problem is the reason."""
    if word_action(text):
        return False
    since = datetime.now(timezone.utc) - timedelta(minutes=30)
    with get_conn() as conn:
        row = conn.execute(
            """SELECT e.id FROM dose_events e
               JOIN schedules s ON s.id = e.schedule_id
               JOIN medicines m ON m.id = s.medicine_id
               WHERE m.patient_id = ? AND e.status = 'missed'
                 AND e.reason IS NULL AND e.responded_at >= ?
               ORDER BY e.responded_at DESC LIMIT 1""",
            (user["id"], since.isoformat(timespec="seconds")),
        ).fetchone()
    if row is None:
        return False
    return await handle_reason(user, row["id"], "other", text)


async def handle_check(user, event_id):
    """Caregiver tapped "I'll check" on an alert."""
    with get_conn() as conn:
        info = event_info(conn, event_id)
        linked = info and conn.execute(
            "SELECT 1 FROM care_links WHERE caregiver_id = ? AND patient_id = ?",
            (user["id"], info["user_id"]),
        ).fetchone()
    if not linked:
        return False
    lang = lang_of(user)
    # STEP 6: a dose with no answer has no reason
    args = {"patient": info["name"], "medicine": info["display_name"], "time": due_time(info)}
    if info["reason"] is None:
        text = TEXTS["no_answer"][lang].format(**args)
    else:
        reason = info["reply_text"] or dict(REASON_BUTTONS[lang]).get(info["reason"], "?")
        text = TEXTS["details"][lang].format(reason=reason, **args)
    await send_text(user["phone"], text)
    await send_text(info["phone"], TEXTS["checking"][lang_of(info)].format(name=user["name"]))
    return True
