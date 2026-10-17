"""PILOT 8: "my medicines": the list, stopping a medicine, and changing its times or dose.
The family member who set up a parent's medicines can do all of it for the parent too."""
from app.access import window_open
from app.db import get_conn
from app.reminders import lang_of
from app.setup import (cared_by, editable_for, end_chat, is_greeting, is_my_meds, is_start_over,
                       medicine_detail, medicine_info, medicine_lines, offer_drugs, parse_dose, parse_time,
                       say, set_step, two_choice)
from app.texts import (DOSE_BUTTONS, MED_ACTION_BUTTONS, MEDS, MORE_TIME_BUTTONS, SETUP, STOP_MED_BUTTONS,
                       TIME_ROWS)
from app.whatsapp import send_buttons, send_list, send_text

# Button and menu ids: MYMED:<medicine id> opens one medicine, the others act on it
# (MLIST:<user id> answers "Whose medicines?")
MY_MEDS_IDS = ("MYMED", "MSTOP", "MSTOPYES", "MKEEP", "MTIMES", "MDOSE", "MSAME", "MADD", "MLIST")
CHANGE_IDS = ("DOSE:", "TIME:", "TIMES:")  # the setup buttons a change reuses


def active_medicines(conn, patient_id):
    return conn.execute(
        "SELECT * FROM medicines WHERE patient_id = ? AND active = 1 ORDER BY id", (patient_id,)
    ).fetchall()


def brand_rows(conn, brand):
    """Every strength and box of one brand, without the MoPH list's exact duplicates (9 at most)."""
    seen, unique = set(), []
    for row in conn.execute("SELECT * FROM drug_reference WHERE brand_name = ? ORDER BY id", (brand,)):
        if (row["strength"], row["presentation"]) not in seen:
            seen.add((row["strength"], row["presentation"]))
            unique.append(row)
    return unique[:9]


def can_change(conn, user, patient_id):
    """The person who takes it, and the family member who set it up (not family added only for alerts)."""
    return patient_id == user["id"] or patient_id in {p["id"] for p in editable_for(conn, user["id"])}


def text_for(key, lang, parent=None, **args):
    """Like setup.say: the "_for" text when the list is someone else's ("I'll remind Rita")."""
    if parent and key + "_for" in MEDS:
        key += "_for"
    return MEDS[key][lang].format(patient=parent, **args)


def choices(options):
    """Up to 3 choices as buttons, more as a menu."""
    return len(options) <= 3


async def ask_whose_list(user, others):
    """Build step 3: "Whose medicines?" Mine, or someone whose medicines this person set up."""
    lang, to = lang_of(user), user["phone"]
    options = [(f"MLIST:{user['id']}", MEDS["mine"][lang])]
    options += [(f"MLIST:{p['id']}", (p["name"] or "?")[:20]) for p in others]
    if choices(options):
        await send_buttons(to, MEDS["whose"][lang], options)
    else:
        await send_list(to, MEDS["whose"][lang], SETUP["choose"][lang], [(i, t, "") for i, t in options[:10]])
    return True


async def show_list(user, patient=None):
    """Every medicine in the message, the first 9 in the menu, then "Add a medicine".
    Build step 3: someone who set up a parent's medicines picks whose list first (the parent's opens
    straight away when they have none of their own and set up only one person)."""
    lang, to = lang_of(user), user["phone"]
    with get_conn() as conn:
        others = editable_for(conn, user["id"])
        mine = active_medicines(conn, user["id"])
    if patient is None and others:
        if mine or len(others) > 1:
            return await ask_whose_list(user, others)
        patient = others[0]
    patient = patient or user
    parent = patient["name"] if patient["id"] != user["id"] else None
    with get_conn() as conn:
        meds = active_medicines(conn, patient["id"])
        lines, _ = medicine_lines(conn, patient["id"], lang)
        details = [medicine_detail(conn, m["id"], lang)[0] for m in meds[:9]]
    if not meds:
        await send_text(to, text_for("none", lang, parent))
        return True
    rows = [(f"MYMED:{m['id']}", m["display_name"], d) for m, d in zip(meds, details)]
    rows.append(("MADD", MEDS["add_row"][lang], ""))
    await send_list(to, text_for("list", lang, parent, lines=lines), MEDS["list_button"][lang], rows)
    return True


async def tell_others(user, patient_id, key, medicine_id):
    """Build step 3: a short note to the other side, only inside their 24-hour window (no template).
    Someone else changed the list: the person who takes the medicine. They changed it: their family."""
    with get_conn() as conn:
        if patient_id == user["id"]:
            people = cared_by(conn, patient_id)
        else:
            people = conn.execute("SELECT * FROM users WHERE id = ?", (patient_id,)).fetchall()
        name, _ = medicine_info(conn, medicine_id)
        details = {lang: medicine_detail(conn, medicine_id, lang)[0] for lang in ("en", "ar")}
    for person in people:
        if person["consent"] and window_open(person):  # nothing before they agree
            lang = lang_of(person)
            note = key + "_you" if person["id"] == patient_id else key
            await send_text(person["phone"], MEDS[note][lang].format(
                who=user["name"] or "?", medicine=name, detail=details[lang]))


async def handle_my_meds_reply(user, reply_id):
    """A tap on the list or on a medicine's buttons. False if the medicine no longer exists."""
    lang, to = lang_of(user), user["phone"]
    if reply_id == "MADD":
        await send_text(to, MEDS["add"][lang])
        return True
    kind, _, medicine_id = reply_id.partition(":")
    if not medicine_id.isdigit():
        return False
    if kind == "MLIST":  # the answer to "Whose medicines?"
        with get_conn() as conn:
            patient = conn.execute("SELECT * FROM users WHERE id = ?", (int(medicine_id),)).fetchone()
            allowed = patient is not None and can_change(conn, user, patient["id"])
        if not allowed:
            return False
        return await show_list(user, patient)
    with get_conn() as conn:
        med = conn.execute(
            """SELECT m.*, u.name AS patient_name FROM medicines m
               JOIN users u ON u.id = m.patient_id WHERE m.id = ?""",
            (int(medicine_id),),
        ).fetchone()
        drug = med and conn.execute(
            "SELECT brand_name FROM drug_reference WHERE id = ?", (med["drug_id"],)
        ).fetchone()
        drugs = brand_rows(conn, drug["brand_name"]) if drug else []
        allowed = med is not None and can_change(conn, user, med["patient_id"])
    if med is None:
        return False
    name = med["display_name"]
    parent = med["patient_name"] if med["patient_id"] != user["id"] else None
    if not allowed:
        await send_text(to, MEDS["not_yours"][lang].format(patient=med["patient_name"]))
        return True
    if kind == "MSAME":  # another one of a medicine already on the list: all its strengths
        if drugs:
            await offer_drugs(to, lang, drugs)
        else:
            await send_text(to, MEDS["add"][lang])
        return True
    if not med["active"]:
        await send_text(to, MEDS["already_stopped"][lang].format(medicine=name))
        return True
    with get_conn() as conn:
        detail, times = medicine_detail(conn, med["id"], lang)
    actions = [(f"{k}:{med['id']}", t) for k, t in MED_ACTION_BUTTONS[lang]]
    if kind == "MYMED":
        await send_buttons(to, text_for("what", lang, parent, medicine=name, detail=detail), actions)
    elif kind == "MSTOP":
        await send_buttons(to, text_for("stop_ask", lang, parent, medicine=name),
                           [(f"{k}:{med['id']}", t) for k, t in STOP_MED_BUTTONS[lang]])
    elif kind == "MSTOPYES":  # off, not deleted: the family can still see past doses
        with get_conn() as conn:
            conn.execute("UPDATE medicines SET active = 0 WHERE id = ?", (med["id"],))
            left = active_medicines(conn, med["patient_id"])
        await send_text(to, text_for("stopped" if left else "stopped_last", lang, parent, medicine=name))
        await tell_others(user, med["patient_id"], "note_stopped", med["id"])
    elif kind == "MKEEP":
        await send_text(to, MEDS["kept"][lang].format(medicine=name))
    elif kind == "MDOSE" and not times:  # the dose is saved with each reminder time
        await send_buttons(to, MEDS["dose_no_time"][lang].format(medicine=name), actions)
    else:  # MTIMES, MDOSE: a short chat, and nothing changes until its last answer
        step = "change_time" if kind == "MTIMES" else "change_dose"
        data = {"medicine_id": med["id"], "new_times": []}
        if parent:
            data["parent"] = parent  # setup.say then asks "When does Rita take it?"
        with get_conn() as conn:
            set_step(conn, user["id"], step, data)
        await ask_change(to, lang, step, data)
    return True


# Build step 2: changing times or the dose, with the setup questions

async def ask_change(to, lang, step, data, again=False, before=""):
    """The question of each change step, again after "hi" or a wrong answer."""
    with get_conn() as conn:
        name, times = medicine_info(conn, data["medicine_id"])
    if step == "change_other":
        await send_text(to, before + SETUP["bad_time" if again else "type_time"][lang])
        return
    if step == "change_time":  # the first time it says the times it has now
        if times and not data["new_times"]:
            body = MEDS["times_now"][lang].format(medicine=name, times=", ".join(times))
        else:
            body = say("ask_time", lang, data, medicine=name)
        if again:
            body = SETUP["time_hint"][lang] + "\n\n" + body
        rows = [(rid, title, "") for rid, title in TIME_ROWS[lang]]
        await send_list(to, before + body, SETUP["time_button"][lang], rows)
        return
    if step == "change_dose":
        body = say("ask_dose", lang, data, medicine=name)
        hint, buttons = SETUP["dose_hint"][lang], DOSE_BUTTONS[lang]
    else:  # change_more
        body = text_for("new_times", lang, data.get("parent"),
                        medicine=name, times=", ".join(data["new_times"]))
        hint, buttons = SETUP["tap_button"][lang], MORE_TIME_BUTTONS[lang]
    if again:
        body = hint + "\n\n" + body
    await send_buttons(to, before + body, buttons)


async def next_change(user, to, lang, step, data):
    with get_conn() as conn:
        set_step(conn, user["id"], step, data)
    await ask_change(to, lang, step, data)
    return True


async def save_times(user, to, lang, data):
    """The old times go off and the new ones on, together. A time that stays keeps its row."""
    medicine_id, new = data["medicine_id"], data["new_times"]
    with get_conn() as conn:
        end_chat(conn, user["id"])
        old = conn.execute(
            "SELECT id, time_of_day, dose_amount FROM schedules WHERE medicine_id = ? AND active = 1",
            (medicine_id,),
        ).fetchall()
        dose = old[0]["dose_amount"] if old else 1
        for row in old:
            if row["time_of_day"] not in new:
                conn.execute("UPDATE schedules SET active = 0 WHERE id = ?", (row["id"],))
        for time in sorted(set(new) - {r["time_of_day"] for r in old}):
            conn.execute(
                "INSERT INTO schedules (medicine_id, time_of_day, dose_amount) VALUES (?, ?, ?)",
                (medicine_id, time, dose),
            )
        name, times = medicine_info(conn, medicine_id)
        detail, _ = medicine_detail(conn, medicine_id, lang)
        patient_id = conn.execute(
            "SELECT patient_id FROM medicines WHERE id = ?", (medicine_id,)
        ).fetchone()[0]
    if old:
        await send_text(to, text_for("times_saved", lang, data.get("parent"),
                                     medicine=name, times=", ".join(times)))
    else:  # it had no time before: say the dose too
        await send_text(to, MEDS["dose_saved"][lang].format(medicine=name, detail=detail))
    await tell_others(user, patient_id, "note_changed", medicine_id)
    return True


async def save_dose(user, to, lang, data, dose):
    """One dose for every time of the medicine, as in setup."""
    with get_conn() as conn:
        end_chat(conn, user["id"])
        conn.execute(
            "UPDATE schedules SET dose_amount = ? WHERE medicine_id = ? AND active = 1",
            (dose, data["medicine_id"]),
        )
        name, _ = medicine_info(conn, data["medicine_id"])
        detail, _ = medicine_detail(conn, data["medicine_id"], lang)
        patient_id = conn.execute(
            "SELECT patient_id FROM medicines WHERE id = ?", (data["medicine_id"],)
        ).fetchone()[0]
    await send_text(to, MEDS["dose_saved"][lang].format(medicine=name, detail=detail))
    await tell_others(user, patient_id, "note_changed", data["medicine_id"])
    return True


async def handle_change(user, msg, step, data):
    """Answers in the middle of a change (setup.handle_setup sends them here). False lets main.py handle it."""
    kind = msg.get("type")
    text = msg.get("text", {}).get("body", "").strip()
    reply = msg.get("interactive", {})
    reply_id = (reply.get("button_reply") or reply.get("list_reply") or {}).get("id", "")
    with get_conn() as conn:
        med = conn.execute("SELECT active FROM medicines WHERE id = ?", (data["medicine_id"],)).fetchone()
        if not med or not med["active"] or (kind == "text" and is_my_meds(text)):
            end_chat(conn, user["id"])  # stopped in the meantime, or the list wanted again: nothing changes
            return False
    if kind == "image" or (reply_id and not reply_id.startswith(CHANGE_IDS)):
        return False  # a photo adds a medicine as usual
    to, lang = msg["from"], lang_of(user)
    if kind == "text" and is_greeting(text):
        await ask_change(to, lang, step, data, before=SETUP["continue"][lang] + "\n\n")
        return True
    if kind == "text" and is_start_over(text):
        with get_conn() as conn:
            end_chat(conn, user["id"])
        await send_text(to, MEDS["unchanged"][lang])
        return True

    if step == "change_dose":
        dose = float(reply_id.split(":")[1]) if reply_id.startswith("DOSE:") else parse_dose(text)
        if dose is None:
            await ask_change(to, lang, step, data, again=True)
            return True
        return await save_dose(user, to, lang, data, dose)

    if step == "change_more":
        if reply_id == "TIMES:more" or two_choice(text) == 0:
            return await next_change(user, to, lang, "change_time", data)
        if reply_id == "TIMES:done" or two_choice(text) == 1:
            return await save_times(user, to, lang, data)
        await ask_change(to, lang, step, data, again=True)
        return True

    if reply_id == "TIME:other":  # change_time
        return await next_change(user, to, lang, "change_other", data)
    time = reply_id.split(":", 1)[1] if reply_id.startswith("TIME:") else parse_time(text)
    if time is None:
        await ask_change(to, lang, step, data, again=True)
        return True
    data["new_times"] = sorted(set(data["new_times"]) | {time})
    return await next_change(user, to, lang, "change_more", data)
