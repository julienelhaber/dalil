import json
import re
from datetime import datetime

from app.db import get_conn, now_utc
from app.photo import drug_name, find_drugs, save_medicine  # PILOT 3
from app.reminders import BEIRUT, lang_of
from app.texts import (DOSE_BUTTONS, FOR_WHOM_BUTTONS, FOR_WHOM_WORDS, MORE_MED_BUTTONS,
                       MORE_TIME_BUTTONS, NOT_FOUND_BUTTONS, SETUP, TEXTS, TIME_ROWS, YES_NO)
from app.whatsapp import send_buttons, send_list, send_text

# PILOT 3: button and menu ids that belong to the setup chat
SETUP_IDS = ("FOR:", "MED_", "DOSE:", "TIME:", "TIMES:", "MORE:")
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
HALF = {"half", "nos", "nus", "noss", "نص", "نصف", "½"}


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


def end_chat(conn, user_id):
    conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))


def two_choice(text):
    """Typed 1 or 2 for a two-button question: 0, 1 or None."""
    return {"1": 0, "2": 1}.get(text.translate(DIGITS).strip())


def parse_dose(text):
    """1, 1.5, ٢, half, nos -> a number of pills between 0 and 10, else None."""
    t = text.translate(DIGITS).strip().lower()
    if t in HALF:
        return 0.5
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(pills?|tabs?|tablets?|حبة|حبات)?", t)
    if not m:
        return None
    dose = float(m.group(1).replace(",", "."))
    return dose if 0 < dose <= 10 else None


def parse_time(text):
    """8, 8:30, 21.00, 9pm, ٨:٣٠ -> "HH:MM", else None."""
    t = text.translate(DIGITS).strip().lower().replace(" ", "")
    m = re.fullmatch(r"(\d{1,2})(?:[:.h](\d{2}))?(am|pm)?", t)
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2) or 0)
    if m.group(3) == "pm" and hour < 12:
        hour += 12
    if m.group(3) == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def dose_text(dose, lang):
    if lang == "ar":
        return {0.5: "نص حبة", 1: "حبة وحدة", 2: "حبتين"}.get(dose, f"{dose:g} حبات")
    if dose == 0.5:
        return "half a pill"
    return f"{dose:g} pill" + ("" if dose == 1 else "s")


def medicine_info(conn, medicine_id):
    """The medicine's name and its reminder times, earliest first."""
    name = conn.execute(
        "SELECT display_name FROM medicines WHERE id = ?", (medicine_id,)
    ).fetchone()["display_name"]
    times = [r["time_of_day"] for r in conn.execute(
        """SELECT time_of_day FROM schedules
           WHERE medicine_id = ? AND active = 1 ORDER BY time_of_day""",
        (medicine_id,),
    )]
    return name, times


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


# PILOT 3: everything below is the medicine loop

async def typed_name(user, to, lang, data, text):
    """The person typed a medicine name: confirm it, or let them pick from a list."""
    data["typed"] = text[:40]
    with get_conn() as conn:
        set_step(conn, user["id"], "medicine", data)
    drugs = find_drugs(text)
    if not drugs:
        await send_buttons(to, SETUP["not_found"][lang].format(name=data["typed"]),
                           NOT_FOUND_BUTTONS[lang])
    elif len(drugs) == 1:
        drug = drugs[0]
        yes, no = YES_NO[lang]
        question = TEXTS["confirm"][lang].format(name=drug_name(drug), pack=drug["presentation"])
        await send_buttons(to, question, [(f"MED_YES:{drug['id']}", yes), ("MED_NO", no)])
    else:
        rows, titles = [], set()
        for drug in drugs:
            title = drug_name(drug)
            if title in titles:  # same name, another box size
                title = f"{title} ({drug['presentation']})"
            titles.add(title)
            details = " · ".join(x for x in (drug["presentation"], drug["form"]) if x)
            rows.append((f"MED_YES:{drug['id']}", title, details))
        rows.append(("MED_NONE", SETUP["none_row"][lang], ""))
        await send_list(to, SETUP["which"][lang], SETUP["choose"][lang], rows)
    return True


async def medicine_chosen(user, to, lang, data, drug_id=None, typed=None):
    """Save the medicine (after the double-dose check), then ask the dose."""
    medicine_id = await save_medicine(user, drug_id, typed)
    if medicine_id is None:  # same medicine twice: the warning was sent, nothing saved
        if "for" in data:
            with get_conn() as conn:
                set_step(conn, user["id"], "more_meds", {"for": data["for"]})
            await send_buttons(to, SETUP["next_or_done"][lang], MORE_MED_BUTTONS[lang])
        return True
    data = {k: v for k, v in data.items() if k == "for"}
    data["medicine_id"] = medicine_id
    with get_conn() as conn:
        set_step(conn, user["id"], "dose", data)
    await ask_dose(to, lang, data)
    return True


async def ask_dose(to, lang, data, again=False):
    with get_conn() as conn:
        name, _ = medicine_info(conn, data["medicine_id"])
    body = SETUP["ask_dose"][lang].format(medicine=name)
    if again:
        body = SETUP["dose_hint"][lang] + "\n\n" + body
    await send_buttons(to, body, DOSE_BUTTONS[lang])


async def ask_time(to, lang, data, again=False):
    with get_conn() as conn:
        name, _ = medicine_info(conn, data["medicine_id"])
    body = SETUP["ask_time"][lang].format(medicine=name)
    if again:
        body = SETUP["time_hint"][lang] + "\n\n" + body
    rows = [(rid, title, "") for rid, title in TIME_ROWS[lang]]
    await send_list(to, body, SETUP["time_button"][lang], rows)


async def ask_more_times(to, lang, data, again=False):
    with get_conn() as conn:
        name, times = medicine_info(conn, data["medicine_id"])
    body = SETUP["time_saved"][lang].format(medicine=name, times=", ".join(times))
    if again:
        body = SETUP["tap_button"][lang] + "\n\n" + body
    await send_buttons(to, body, MORE_TIME_BUTTONS[lang])


async def add_time(user, to, lang, data, time):
    """Save one reminder time: from now on the scheduler sends it every day."""
    with get_conn() as conn:
        exists = conn.execute(
            """SELECT 1 FROM schedules
               WHERE medicine_id = ? AND time_of_day = ? AND active = 1""",
            (data["medicine_id"], time),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO schedules (medicine_id, time_of_day, dose_amount) VALUES (?, ?, ?)",
                (data["medicine_id"], time, data["dose"]),
            )
        set_step(conn, user["id"], "more_times", data)
    await ask_more_times(to, lang, data)
    return True


async def medicine_done(user, to, lang, data):
    """All times for this medicine are in."""
    with get_conn() as conn:
        name, times = medicine_info(conn, data["medicine_id"])
        args = {"medicine": name, "dose": dose_text(data["dose"], lang), "times": ", ".join(times)}
        if "for" in data:  # in setup: next medicine, or finish
            set_step(conn, user["id"], "more_meds", {"for": data["for"]})
        else:  # a medicine added after setup
            end_chat(conn, user["id"])
    if "for" in data:
        await send_buttons(to, SETUP["med_saved"][lang].format(**args), MORE_MED_BUTTONS[lang])
    else:
        await send_text(to, SETUP["saved_alone"][lang].format(**args))
    return True


async def finish_setup(user, to, lang):
    """Done: show every medicine with its times, and when the first reminder comes."""
    lines, all_times = [], []
    with get_conn() as conn:
        meds = conn.execute(
            "SELECT id, display_name FROM medicines WHERE patient_id = ? AND active = 1 ORDER BY id",
            (user["id"],),
        ).fetchall()
        for med in meds:
            rows = conn.execute(
                """SELECT time_of_day, dose_amount FROM schedules
                   WHERE medicine_id = ? AND active = 1 ORDER BY time_of_day""",
                (med["id"],),
            ).fetchall()
            if rows:
                times = [r["time_of_day"] for r in rows]
                all_times += times
                lines.append(SETUP["line"][lang].format(
                    medicine=med["display_name"], dose=dose_text(rows[0]["dose_amount"], lang),
                    times=", ".join(times)))
            else:
                lines.append(SETUP["line_no_time"][lang].format(medicine=med["display_name"]))
        end_chat(conn, user["id"])
    now = datetime.now(BEIRUT).strftime("%H:%M")
    later = sorted(t for t in all_times if t > now)
    if later:
        first = SETUP["today"][lang].format(time=later[0])
    else:
        first = SETUP["tomorrow"][lang].format(time=min(all_times, default="--:--"))
    await send_text(to, SETUP["summary"][lang].format(
        name=user["name"], lines="\n".join(lines), first=first))
    return True


async def handle_setup(user, msg):
    """Answers from someone in the middle of setup. Returns True if handled here."""
    kind = msg.get("type")
    text = msg.get("text", {}).get("body", "").strip()
    reply = msg.get("interactive", {})
    reply_id = (reply.get("button_reply") or reply.get("list_reply") or {}).get("id", "")  # PILOT 3
    if kind == "button" or (reply_id and not reply_id.startswith(SETUP_IDS)):
        return False  # PILOT 3: reminder buttons and the rest are not part of setup
    with get_conn() as conn:
        row = conn.execute(
            "SELECT step, data FROM conversations WHERE user_id = ?", (user["id"],)
        ).fetchone()
    to, lang = msg["from"], lang_of(user)
    data = json.loads(row["data"]) if row else {}

    if reply_id.startswith("MED_YES:"):  # PILOT 3: a confirmed medicine, in setup or after
        return await medicine_chosen(user, to, lang, data, drug_id=int(reply_id.split(":")[1]))
    if row is None:
        return False
    step = row["step"]

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

    # PILOT 3: the medicine loop
    if step in ("medicine", "more_meds"):
        if kind == "image":
            return False  # photo.py reads the box and asks Yes / No
        if reply_id == "MED_NO":
            with get_conn() as conn:
                set_step(conn, user["id"], "medicine", data)
            await send_text(to, SETUP["photo_no"][lang])
            return True
    if step == "medicine":
        if reply_id == "MED_NONE":
            await send_buttons(to, SETUP["not_found"][lang].format(name=data.get("typed", "")),
                               NOT_FOUND_BUTTONS[lang])
            return True
        if reply_id == "MED_TYPED" and data.get("typed"):
            return await medicine_chosen(user, to, lang, data, typed=data["typed"])
        if reply_id == "MED_RETYPE":
            await send_text(to, SETUP["retype"][lang])
            return True
        if text:
            return await typed_name(user, to, lang, data, text)
        await send_text(to, SETUP["ask_next"][lang])
        return True

    if step == "dose":
        if reply_id.startswith("DOSE:"):
            dose = float(reply_id.split(":")[1])
        else:
            dose = parse_dose(text)
        if dose is None:
            await ask_dose(to, lang, data, again=True)
            return True
        data["dose"] = dose
        with get_conn() as conn:
            set_step(conn, user["id"], "time", data)
        await ask_time(to, lang, data)
        return True

    if step == "time":
        if reply_id == "TIME:other":
            with get_conn() as conn:
                set_step(conn, user["id"], "other_time", data)
            await send_text(to, SETUP["type_time"][lang])
            return True
        time = reply_id.split(":", 1)[1] if reply_id.startswith("TIME:") else parse_time(text)
        if time is None:
            await ask_time(to, lang, data, again=True)
            return True
        return await add_time(user, to, lang, data, time)

    if step == "other_time":
        time = parse_time(text)
        if time is None:
            await send_text(to, SETUP["bad_time"][lang])
            return True
        return await add_time(user, to, lang, data, time)

    if step == "more_times":
        if reply_id == "TIMES:more" or two_choice(text) == 0:
            with get_conn() as conn:
                set_step(conn, user["id"], "time", data)
            await ask_time(to, lang, data)
            return True
        if reply_id == "TIMES:done" or two_choice(text) == 1:
            return await medicine_done(user, to, lang, data)
        await ask_more_times(to, lang, data, again=True)
        return True

    if step == "more_meds":
        if reply_id == "MORE:add" or two_choice(text) == 0:
            with get_conn() as conn:
                set_step(conn, user["id"], "medicine", data)
            await send_text(to, SETUP["ask_next"][lang])
            return True
        if reply_id == "MORE:done" or two_choice(text) == 1:
            return await finish_setup(user, to, lang)
        body = SETUP["tap_button"][lang] + "\n\n" + SETUP["next_or_done"][lang]
        await send_buttons(to, body, MORE_MED_BUTTONS[lang])
        return True

    return False
