from app.db import get_conn
from app.reminders import lang_of
from app.setup import invited_line, start_setup  # PILOT 2 (PILOT 4: invited_line)
from app.texts import CONSENT_BUTTONS, CONSENT_NO, CONSENT_PROMPT, STOP_WORDS, TEXTS
from app.whatsapp import send_buttons, send_text


def set_consent(user_id, consent, language=None):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET consent = ?, language = COALESCE(?, language) WHERE id = ?",
            (consent, language, user_id),
        )


async def handle_consent(user, msg):
    """Consent comes before everything else. Returns True if the message was handled here."""
    to = msg["from"]
    reply_id = msg.get("interactive", {}).get("button_reply", {}).get("id", "")
    text = msg.get("text", {}).get("body", "").strip().lower().strip(".!")
    if reply_id.startswith("CONSENT:"):
        choice = reply_id.split(":")[1]
        if choice == "no":
            set_consent(user["id"], 0)
            await send_text(to, CONSENT_NO)
        else:
            set_consent(user["id"], 1, choice)
            await send_text(to, TEXTS["consent_yes"][choice])
            await start_setup(user, to, choice)  # PILOT 2: new people go on to setup
        return True
    if text in STOP_WORDS:
        set_consent(user["id"], 0)
        await send_text(to, TEXTS["stopped"][lang_of(user)])
        return True
    if not user["consent"]:
        await send_buttons(to, invited_line(user) + CONSENT_PROMPT, CONSENT_BUTTONS)  # PILOT 4
        return True
    return False
