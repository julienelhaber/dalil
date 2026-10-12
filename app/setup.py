import json

from app.db import get_conn, now_utc
from app.reminders import lang_of
from app.texts import FOR_WHOM_BUTTONS, FOR_WHOM_WORDS, SETUP
from app.whatsapp import send_buttons, send_text


def needs_setup(conn, user_id):
    """A new person: no medicines of their own, and nobody they look after."""
    has_meds = conn.execute(
        "SELECT 1 FROM medicines WHERE patient_id = ?", (user_id,)
    ).fetchone()
    is_caregiver = conn.execute(
        "SELECT 1 FROM care_links WHERE caregiver_id = ?", (user_id,)
    ).fetchone()
    return not has_meds and not is_caregiver


def set_step(conn, user_id, step, data):
    """Remember where this person is in the setup chat."""
    conn.execute(
        """INSERT INTO conversations (user_id, step, data, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT (user_id) DO UPDATE SET step = excluded.step,
               data = excluded.data, updated_at = excluded.updated_at""",
        (user_id, step, json.dumps(data), now_utc()),
    )


async def start_setup(user, to, lang):
    """Right after someone agrees: a new person starts with their name."""
    with get_conn() as conn:
        if not needs_setup(conn, user["id"]):
            return
        set_step(conn, user["id"], "name", {})
    await send_text(to, SETUP["ask_name"][lang])


async def ask_for_whom(to, lang, name, again=False):
    body = SETUP["for_whom"][lang].format(name=name)
    if again:
        body = SETUP["tap_button"][lang] + "\n\n" + body
    await send_buttons(to, body, FOR_WHOM_BUTTONS[lang])


async def handle_setup(user, msg):
    """Answers from someone in the middle of setup. Returns True if handled here."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT step, data FROM conversations WHERE user_id = ?", (user["id"],)
        ).fetchone()
    if row is None:
        return False
    step, data = row["step"], json.loads(row["data"])
    to, lang = msg["from"], lang_of(user)
    text = msg.get("text", {}).get("body", "").strip()
    reply_id = msg.get("interactive", {}).get("button_reply", {}).get("id", "")

    if step == "name":
        if not text or len(text) > 40:  # a photo, a button, or not a name
            await send_text(to, SETUP["ask_name"][lang])
            return True
        with get_conn() as conn:
            conn.execute("UPDATE users SET name = ? WHERE id = ?", (text, user["id"]))
            set_step(conn, user["id"], "for_whom", data)
        await ask_for_whom(to, lang, text)
        return True

    if step == "for_whom":
        if reply_id.startswith("FOR:"):
            choice = reply_id.split(":")[1]
        else:
            choice = FOR_WHOM_WORDS.get(text)
        if choice is None:
            await ask_for_whom(to, lang, user["name"], again=True)
            return True
        data["for"] = choice
        with get_conn() as conn:
            set_step(conn, user["id"], "medicine", data)
        await send_text(to, SETUP["ask_medicine"][lang])
        return True

    return False  # the medicine step is built in Pilot step 3
