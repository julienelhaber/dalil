"""PILOT 8: "my medicines": the list, stopping a medicine, and changing its times or dose."""
from app.db import get_conn
from app.reminders import lang_of
from app.setup import (end_chat, is_greeting, is_my_meds, is_start_over, medicine_detail, medicine_info,
                       medicine_lines, offer_drugs, parse_dose, parse_time, set_step, two_choice)
from app.texts import (DOSE_BUTTONS, MED_ACTION_BUTTONS, MEDS, MORE_TIME_BUTTONS, SETUP, STOP_MED_BUTTONS,
                       TIME_ROWS)
from app.whatsapp import send_buttons, send_list, send_text

# Button and menu ids: MYMED:<medicine id> opens one medicine, the others act on it
MY_MEDS_IDS = ("MYMED", "MSTOP", "MSTOPYES", "MKEEP", "MTIMES", "MDOSE", "MSAME", "MADD")
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


def can_change(user, med):
    """Only the person who takes it, for now (the family member who set it up comes in step 3)."""
    return med["patient_id"] == user["id"]


async def show_list(user):
    """Every medicine in the message, the first 9 in the menu, then "Add a medicine"."""
    lang, to = lang_of(user), user["phone"]
    with get_conn() as conn:
        meds = active_medicines(conn, user["id"])
        lines, _ = medicine_lines(conn, user["id"], lang)
        details = [medicine_detail(conn, m["id"], lang)[0] for m in meds[:9]]
    if not meds:
        await send_text(to, MEDS["none"][lang])
        return True
    rows = [(f"MYMED:{m['id']}", m["display_name"], d) for m, d in zip(meds, details)]
    rows.append(("MADD", MEDS["add_row"][lang], ""))
    await send_list(to, MEDS["list"][lang].format(lines=lines), MEDS["list_button"][lang], rows)
    return True


async def handle_my_meds_reply(user, reply_id):
    """A tap on the list or on a medicine's buttons. False if the medicine no longer exists."""
    lang, to = lang_of(user), user["phone"]
    if reply_id == "MADD":
        await send_text(to, MEDS["add"][lang])
        return True
    kind, _, medicine_id = reply_id.partition(":")
    if not medicine_id.isdigit():
        return False
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
    if med is None:
        return False
    name = med["display_name"]
    if not can_change(user, med):
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
        await send_buttons(to, MEDS["what"][lang].format(medicine=name, detail=detail), actions)
    elif kind == "MSTOP":
        await send_buttons(to, MEDS["stop_ask"][lang].format(medicine=name),
                           [(f"{k}:{med['id']}", t) for k, t in STOP_MED_BUTTONS[lang]])
    elif kind == "MSTOPYES":  # off, not deleted: the family can still see past doses
        with get_conn() as conn:
            conn.execute("UPDATE medicines SET active = 0 WHERE id = ?", (med["id"],))
            left = active_medicines(conn, med["patient_id"])
        await send_text(to, MEDS["stopped" if left else "stopped_last"][lang].format(medicine=name))
    elif kind == "MKEEP":
        await send_text(to, MEDS["kept"][lang].format(medicine=name))
    elif kind == "MDOSE" and not times:  # the dose is saved with each reminder time
        await send_buttons(to, MEDS["dose_no_time"][lang].format(medicine=name), actions)
    else:  # MTIMES, MDOSE: a short chat, and nothing changes until its last answer
        step = "change_time" if kind == "MTIMES" else "change_dose"
        data = {"medicine_id": med["id"], "new_times": []}
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
            body = SETUP["ask_time"][lang].format(medicine=name)
        if again:
            body = SETUP["time_hint"][lang] + "\n\n" + body
        rows = [(rid, title, "") for rid, title in TIME_ROWS[lang]]
        await send_list(to, before + body, SETUP["time_button"][lang], rows)
        return
    if step == "change_dose":
        body = SETUP["ask_dose"][lang].format(medicine=name)
        hint, buttons = SETUP["dose_hint"][lang], DOSE_BUTTONS[lang]
    else:  # change_more
        body = MEDS["new_times"][lang].format(medicine=name, times=", ".join(data["new_times"]))
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
    if old:
        await send_text(to, MEDS["times_saved"][lang].format(medicine=name, times=", ".join(times)))
    else:  # it had no time before: say the dose too
        await send_text(to, MEDS["dose_saved"][lang].format(medicine=name, detail=detail))
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
    await send_text(to, MEDS["dose_saved"][lang].format(medicine=name, detail=detail))
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
