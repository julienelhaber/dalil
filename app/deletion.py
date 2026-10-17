"""PILOT 8, build step 4: "delete my data". Everything Dalil saved about the person goes:
their medicines, times, answers, family links and chat. A parent whose medicines they set up keeps them,
unless the parent never agreed to Dalil: then nobody owns that list, so the parent goes too."""
import json
import re

from rapidfuzz import fuzz, process

from app.access import window_open
from app.db import get_conn
from app.reminders import lang_of
from app.setup import ARABIC_PLAIN, plain
from app.texts import DELETE, DELETE_BUTTONS, DELETE_WORDS
from app.whatsapp import send_buttons, send_text

DELETE_PLAIN = {w.translate(ARABIC_PLAIN) for w in DELETE_WORDS}
DELETE_LATIN = [w for w in DELETE_WORDS if w.isascii()]


def is_delete(text):
    """delete my data, امحي معلوماتي... and small typos in Latin letters, as in is_my_meds."""
    t = plain(text).translate(ARABIC_PLAIN)
    if t in DELETE_PLAIN:
        return True
    return (re.fullmatch(r"[a-z0-9' ]{8,}", t) is not None
            and process.extractOne(t, DELETE_LATIN, scorer=fuzz.ratio, score_cutoff=85) is not None)


def their_parents(conn, user_id):
    """The people this person looks after, whether they set up their medicines, and whether each goes too."""
    parents = conn.execute(
        """SELECT u.*, c.can_edit FROM care_links c JOIN users u ON u.id = c.patient_id
           WHERE c.caregiver_id = ? ORDER BY c.id""",
        (user_id,),
    ).fetchall()
    result = []
    for p in parents:
        others = conn.execute(
            "SELECT COUNT(*) FROM care_links WHERE patient_id = ? AND caregiver_id != ?", (p["id"], user_id)
        ).fetchone()[0]
        never_agreed = not p["consent"] and not p["language"]  # the language is set when someone agrees
        result.append((p, p["can_edit"], p["can_edit"] and never_agreed and others == 0))
    return result


async def handle_delete(user, msg):
    """Runs before consent, so it also works after STOP. Returns True if the message was handled here."""
    to, lang = msg["from"], lang_of(user)
    reply_id = msg.get("interactive", {}).get("button_reply", {}).get("id", "")
    if reply_id == "DELETE:no":
        await send_text(to, DELETE["kept"][lang])
        return True
    if reply_id == "DELETE:yes":
        await delete_everything(user)
        await send_text(to, DELETE["deleted"][lang])
        return True
    if msg.get("type") != "text" or not is_delete(msg["text"]["body"]):
        return False
    with get_conn() as conn:
        parents = their_parents(conn, user["id"])
    lines = [DELETE["ask_goes" if goes else "ask_keeps"][lang].format(parent=p["name"] or "?")
             for p, set_up, goes in parents if set_up]
    await send_buttons(to, "\n\n".join([DELETE["ask"][lang]] + lines), DELETE_BUTTONS[lang])
    return True


async def delete_everything(user):
    uid, who = user["id"], user["name"] or "?"
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (uid,)).fetchone()
        if row is None:  # an old Yes button after the data was already deleted
            return
        family = conn.execute(
            """SELECT u.* FROM care_links c JOIN users u ON u.id = c.caregiver_id WHERE c.patient_id = ?""",
            (uid,),
        ).fetchall()
        parents = their_parents(conn, uid)
        gone = [uid] + [p["id"] for p, _, goes in parents if goes]
        tell = [(f, "note_family") for f in family] + [(p, "note_parent") for p, _, goes in parents if not goes]
        # a family member in the middle of adding a medicine for someone who is going
        for f in family:
            chat = conn.execute("SELECT data FROM conversations WHERE user_id = ?", (f["id"],)).fetchone()
            if chat and json.loads(chat["data"] or "{}").get("parent_id") in gone:
                conn.execute("DELETE FROM conversations WHERE user_id = ?", (f["id"],))
        for person_id in gone:  # medicines, times, answers, links, access and chat go with the user row
            conn.execute("DELETE FROM users WHERE id = ?", (person_id,))
    for person, key in tell:
        if person["id"] not in gone and person["consent"] and window_open(person):
            await send_text(person["phone"], DELETE[key][lang_of(person)].format(who=who))
