import json
import re
from datetime import datetime

from app.access import window_open  # PILOT 4
from app.db import find_user, get_conn, now_utc
from app.photo import drug_name, find_drugs, save_medicine  # PILOT 3
from app.reminders import BEIRUT, lang_of, word_action
from app.texts import (DONE_WORDS, DOSE_BUTTONS, FAMILY_BUTTONS, FOR_WHOM_BUTTONS, FOR_WHOM_WORDS,
                       INVITED, INVITED_PARENT, MORE_MED_BUTTONS, MORE_TIME_BUTTONS, NO_WORDS,
                       NOT_FOUND_BUTTONS, PARENT_LANG_BUTTONS, SETUP, TEXTS, TIME_ROWS, YES_NO, YES_WORDS)
from app.whatsapp import send_buttons, send_list, send_template, send_text

# PILOT 3: button and menu ids that belong to the setup chat (PILOT 4: + FAMILY:, PILOT 5: + PLANG:)
SETUP_IDS = ("FOR:", "MED_", "DOSE:", "TIME:", "TIMES:", "MORE:", "FAMILY:", "PLANG:")
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")
KEEP = ("for", "parent_id", "parent")  # PILOT 5: what stays in the chat data from one medicine to the next
HALF = {"half", "nos", "nus", "noss", "نص", "نصف", "½"}


def needs_setup(conn, user_id):
    """A new person: no medicines of their own, and nobody they look after.
    PILOT 5: and nobody setting up medicines for them."""
    has_meds = conn.execute(
        "SELECT 1 FROM medicines WHERE patient_id = ?", (user_id,)
    ).fetchone()
    is_caregiver = conn.execute(
        "SELECT 1 FROM care_links WHERE caregiver_id = ?", (user_id,)
    ).fetchone()
    is_cared_for = conn.execute(
        "SELECT 1 FROM care_links WHERE patient_id = ?", (user_id,)
    ).fetchone()
    return not has_meds and not is_caregiver and not is_cared_for


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


def looked_after(conn, user_id):
    """PILOT 4: the people this person gets alerts for."""
    return conn.execute(
        """SELECT u.* FROM care_links c JOIN users u ON u.id = c.patient_id
           WHERE c.caregiver_id = ? ORDER BY c.id""",
        (user_id,),
    ).fetchall()


def cared_by(conn, user_id):
    """PILOT 5: the family members who get this person's alerts."""
    return conn.execute(
        """SELECT u.* FROM care_links c JOIN users u ON u.id = c.caregiver_id
           WHERE c.patient_id = ? ORDER BY c.id""",
        (user_id,),
    ).fetchall()


def names(rows):
    return ", ".join(r["name"] or "?" for r in rows)


def invited_line(user):
    """PILOT 4: shown above the consent message when someone added this person as family.
    PILOT 5: or set up medicines for them. Only before their first Yes (language is set then)."""
    if user["language"]:
        return ""
    with get_conn() as conn:
        patients = looked_after(conn, user["id"])
        carers = cared_by(conn, user["id"])
    line = ""
    if carers:
        line += INVITED_PARENT.format(carers=names(carers)) + "\n\n"
    if patients:
        line += INVITED.format(patients=names(patients)) + "\n\n"
    return line


def patient_of(user, data):
    """PILOT 5: whose medicines these are: the parent in the family path, else the person writing."""
    if not data.get("parent_id"):
        return user
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (data["parent_id"],)).fetchone()


def keep(data):
    return {k: v for k, v in data.items() if k in KEEP}


def say(key, lang, data, **args):
    """PILOT 5: in the family path, ask about the parent ("does Georges take") instead of "you"."""
    if data.get("parent") and key + "_for" in SETUP:
        key += "_for"
    return SETUP[key][lang].format(parent=data.get("parent"), **args)


def two_choice(text):
    """Typed 1 or 2 for a two-button question: 0, 1 or None."""
    return {"1": 0, "2": 1}.get(text.translate(DIGITS).strip())


def yes_no(text):
    """PILOT 4: typed 1 / yes / eh -> 0, 2 / no / la -> 1, else None."""
    word = text.strip().lower().strip(".!?,،")
    if word in YES_WORDS:
        return 0
    if word in NO_WORDS:
        return 1
    return two_choice(text)


def parse_phone(text):
    """PILOT 4: 03 123 456, +961 3 123 456, 9613123456, 00961... -> digits with the country code, else None."""
    t = text.translate(DIGITS).strip()
    if not t or re.search(r"[^\d\s+\-().]", t):
        return None
    digits = re.sub(r"\D", "", t)
    if digits.startswith("00"):
        digits = digits[2:]
    elif not t.startswith("+") and not digits.startswith("961"):
        digits = "961" + digits.lstrip("0")  # a Lebanese number typed without 961
    if digits.startswith("9610"):  # +961 03 123 456
        digits = "961" + digits[4:]
    if digits.startswith("961"):
        return digits if len(digits) in (10, 11) else None
    return digits if 8 <= len(digits) <= 15 else None


def shared_contact(msg):
    """PILOT 4: a contact card shared from the phone's address book -> (name, phone), else None."""
    for card in msg.get("contacts", []):
        name = card.get("name", {}).get("formatted_name") or card.get("name", {}).get("first_name")
        for p in card.get("phones", []):
            phone = p.get("wa_id") or parse_phone(p.get("phone", ""))
            if name and phone:
                return name[:40], phone
    return None


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


def medicine_lines(conn, patient_id, lang):
    """Each medicine with its dose and times, and every reminder time."""
    lines, all_times = [], []
    meds = conn.execute(
        "SELECT id, display_name FROM medicines WHERE patient_id = ? AND active = 1 ORDER BY id",
        (patient_id,),
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
    return "\n".join(lines), all_times


def first_reminder(all_times, lang):
    """Today at the next time still ahead, else tomorrow at the earliest."""
    now = datetime.now(BEIRUT).strftime("%H:%M")
    later = sorted(t for t in all_times if t > now)
    if later:
        return SETUP["today"][lang].format(time=later[0])
    return SETUP["tomorrow"][lang].format(time=min(all_times, default="--:--"))


async def start_setup(user, to, lang):
    """Right after someone agrees: a new person starts with their name.
    user is the row from before the Yes, so user["language"] is empty the first time."""
    with get_conn() as conn:
        patients = looked_after(conn, user["id"])  # PILOT 4
        carers = cared_by(conn, user["id"])  # PILOT 5
        new = needs_setup(conn, user["id"])
        if new:
            set_step(conn, user["id"], "name", {})
        lines, all_times = medicine_lines(conn, user["id"], lang)
    if patients:  # PILOT 4: a family member who just agreed
        await send_text(to, SETUP["family_ready"][lang].format(patients=names(patients)))
        for p in patients:
            if p["consent"] and window_open(p):
                await send_text(p["phone"], SETUP["family_agreed"][lang_of(p)].format(family=user["name"]))
    if carers and lines and not user["language"]:  # PILOT 5: first Yes of a parent set up by family
        await send_text(to, SETUP["parent_ready"][lang].format(
            lines=lines, first=first_reminder(all_times, lang)))
        for c in carers:
            if c["consent"] and window_open(c):
                await send_text(c["phone"], SETUP["parent_agreed"][lang_of(c)].format(
                    parent=user["name"], first=first_reminder(all_times, lang_of(c))))
    if new:
        await send_text(to, SETUP["ask_name"][lang])


async def tell_carers_no(user):
    """PILOT 5: a parent tapped No on their first consent message: tell the family who set it up."""
    if user["language"]:
        return
    with get_conn() as conn:
        carers = cared_by(conn, user["id"])
    for c in carers:
        if c["consent"] and window_open(c):
            await send_text(c["phone"], SETUP["parent_said_no"][lang_of(c)].format(parent=user["name"]))


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
    else:
        await offer_drugs(to, lang, drugs)  # PILOT 4: moved into its own function
    return True


async def offer_drugs(to, lang, drugs):
    """One match: Yes / No. Several: a menu to pick from."""
    if len(drugs) == 1:
        drug = drugs[0]
        yes, no = YES_NO[lang]
        question = TEXTS["confirm"][lang].format(name=drug_name(drug), pack=drug["presentation"])
        await send_buttons(to, question, [(f"MED_YES:{drug['id']}", yes), ("MED_NO", no)])
        return
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


async def offer_medicine(user, text):
    """PILOT 4: after setup, a typed medicine name adds a medicine, like a photo does.
    Returns False when the text is not a medicine in the MoPH list."""
    if word_action(text):
        return False
    drugs = find_drugs(text)
    if not drugs:
        return False
    await offer_drugs(user["phone"], lang_of(user), drugs)
    return True


async def medicine_chosen(user, to, lang, data, drug_id=None, typed=None):
    """Save the medicine (after the double-dose check), then ask the dose."""
    patient = patient_of(user, data)  # PILOT 5: the parent in the family path
    helper = user if patient["id"] != user["id"] else None
    medicine_id = await save_medicine(patient, drug_id, typed, helper)
    if medicine_id is None:  # same medicine twice: the warning was sent, nothing saved
        if "for" in data:
            with get_conn() as conn:
                set_step(conn, user["id"], "more_meds", keep(data))
            await send_buttons(to, SETUP["next_or_done"][lang], MORE_MED_BUTTONS[lang])
        return True
    data = keep(data)  # PILOT 5: keeps the parent too
    data["medicine_id"] = medicine_id
    with get_conn() as conn:
        set_step(conn, user["id"], "dose", data)
    await ask_dose(to, lang, data)
    return True


async def ask_dose(to, lang, data, again=False):
    with get_conn() as conn:
        name, _ = medicine_info(conn, data["medicine_id"])
    body = say("ask_dose", lang, data, medicine=name)  # PILOT 5
    if again:
        body = SETUP["dose_hint"][lang] + "\n\n" + body
    await send_buttons(to, body, DOSE_BUTTONS[lang])


async def ask_time(to, lang, data, again=False):
    with get_conn() as conn:
        name, _ = medicine_info(conn, data["medicine_id"])
    body = say("ask_time", lang, data, medicine=name)  # PILOT 5
    if again:
        body = SETUP["time_hint"][lang] + "\n\n" + body
    rows = [(rid, title, "") for rid, title in TIME_ROWS[lang]]
    await send_list(to, body, SETUP["time_button"][lang], rows)


async def ask_more_times(to, lang, data, again=False):
    with get_conn() as conn:
        name, times = medicine_info(conn, data["medicine_id"])
    body = say("time_saved", lang, data, medicine=name, times=", ".join(times))  # PILOT 5
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
            set_step(conn, user["id"], "more_meds", keep(data))
        else:  # a medicine added after setup
            end_chat(conn, user["id"])
    if "for" in data:
        await send_buttons(to, SETUP["med_saved"][lang].format(**args), MORE_MED_BUTTONS[lang])
    else:
        await send_text(to, SETUP["saved_alone"][lang].format(**args))
    return True


async def finish_setup(user, to, lang, data=None):
    """Done: show every medicine with its times, and when the first reminder comes."""
    data = data or {}
    patient = patient_of(user, data)  # PILOT 5
    with get_conn() as conn:
        lines, all_times = medicine_lines(conn, patient["id"], lang)  # PILOT 5: moved into its own function
        end_chat(conn, user["id"])
    first = first_reminder(all_times, lang)
    if patient["id"] == user["id"]:
        await send_text(to, SETUP["summary"][lang].format(name=user["name"], lines=lines, first=first))
        return True
    # PILOT 5: set up for a parent. Their reminders start when they agree (or now, if they already did)
    parent = data["parent"]
    if patient["consent"]:
        after = SETUP["parent_active"][lang].format(parent=parent, first=first)
    elif await send_invite(user, patient, data):
        after = SETUP["parent_invited"][lang].format(parent=parent)
    else:  # the template is not approved yet, or WhatsApp refused it: the parent writes first
        after = SETUP["parent_invite"][lang].format(parent=parent)
    await send_text(to, SETUP["summary_for"][lang].format(parent=parent, lines=lines, next=after))
    return True


# PILOT 4: the family alert question ("For me" path)

async def ask_family(to, lang, again=False):
    body = SETUP["family_ask"][lang]
    if again:
        body = SETUP["tap_button"][lang] + "\n\n" + body
    await send_buttons(to, body, FAMILY_BUTTONS[lang])


def find_or_add(conn, name, phone):
    """The user with this number, new if the number is not on Dalil yet (PILOT 5: from add_family)."""
    person = find_user(conn, None, phone)
    if person is None:
        cur = conn.execute(
            "INSERT INTO users (phone, name, created_at) VALUES (?, ?, ?)",
            (phone, name, now_utc()),
        )
        return conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.execute("UPDATE users SET name = COALESCE(name, ?) WHERE id = ?", (name, person["id"]))
    conn.execute(
        """UPDATE access SET status = 'approved', decided_at = ?
           WHERE user_id = ? AND status = 'pending'""",
        (now_utc(), person["id"]),
    )  # someone added by an approved person needs no approval
    return person


async def add_family(user, to, lang, name, phone):
    """Link the family member (a new user if the number is not on Dalil yet), then finish."""
    with get_conn() as conn:
        family = find_or_add(conn, name, phone)
        conn.execute(
            "INSERT OR IGNORE INTO care_links (caregiver_id, patient_id, created_at) VALUES (?, ?, ?)",
            (family["id"], user["id"], now_utc()),
        )
    if family["consent"]:  # already uses Dalil: alerts start now
        await send_text(to, SETUP["family_linked"][lang].format(family=name))
        if window_open(family):
            await send_text(family["phone"],
                            SETUP["family_added_you"][lang_of(family)].format(patient=user["name"]))
    else:  # WhatsApp needs them to write first, and they agree like everyone else
        await send_text(to, SETUP["family_invite"][lang].format(family=name))
    return await finish_setup(user, to, lang)


async def family_contact(user, to, lang, msg, parent_data=None):
    """A shared contact card at the name or number question (PILOT 5: or the parent's)."""
    contact = shared_contact(msg)
    if contact is None:
        await send_text(to, SETUP["parent_name" if parent_data is not None else "family_name"][lang])
        return True
    name, phone = contact
    if phone == user["phone"]:
        await send_text(to, SETUP["own_phone"][lang].format(family=name))
        return True
    if parent_data is not None:
        return await add_parent(user, to, lang, parent_data, name, phone)
    return await add_family(user, to, lang, name, phone)


# PILOT 5: the family path: the parent's name and number, then their medicines

async def send_invite(user, parent, data):
    """The family_invite template asks the parent to agree. False if WhatsApp refused it."""
    language = data.get("parent_lang", "ar")
    r = await send_template(
        parent["phone"], "family_invite", language,
        {"patient_name": parent["name"], "caregiver_name": user["name"]},
        [f"INVITE:yes:{language}", f"INVITE:no:{language}"],
    )
    return r.status_code < 400


async def ask_parent_lang(to, lang, data, again=False):
    body = SETUP["parent_lang"][lang].format(parent=data["parent"])
    if again:
        body = SETUP["tap_button"][lang] + "\n\n" + body
    await send_buttons(to, body, PARENT_LANG_BUTTONS[lang])

async def add_parent(user, to, lang, data, name, phone):
    """Link the person the medicines are for (new if not on Dalil yet), then the medicine loop."""
    with get_conn() as conn:
        parent = find_or_add(conn, name, phone)
        conn.execute(
            "INSERT OR IGNORE INTO care_links (caregiver_id, patient_id, created_at) VALUES (?, ?, ?)",
            (user["id"], parent["id"], now_utc()),
        )
        data.update(parent_id=parent["id"], parent=name)
        set_step(conn, user["id"], "medicine", data)
    await send_text(to, say("ask_medicine", lang, data))
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
        if reply_id == "MED_NONE":  # PILOT 4: a name typed after setup, not in the menu
            await send_text(to, SETUP["photo_no"][lang])
            return True
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
        if choice == "family":  # PILOT 5: first, who the medicines are for
            with get_conn() as conn:
                set_step(conn, user["id"], "parent_name", data)
            await send_text(to, SETUP["parent_name"][lang])
            return True
        with get_conn() as conn:
            set_step(conn, user["id"], "medicine", data)
        await send_text(to, SETUP["ask_medicine"][lang])
        return True

    # PILOT 5: the family path
    if step == "parent_name":
        if kind == "contacts":
            return await family_contact(user, to, lang, msg, data)
        if not text or len(text) > 40:
            await send_text(to, SETUP["parent_name"][lang])
            return True
        data["parent"] = text
        with get_conn() as conn:
            set_step(conn, user["id"], "parent_phone", data)
        await send_text(to, SETUP["parent_phone"][lang].format(parent=text))
        return True

    if step == "parent_phone":
        if kind == "contacts":
            return await family_contact(user, to, lang, msg, data)
        phone = parse_phone(text)
        if phone is None:
            await send_text(to, SETUP["bad_phone"][lang])
            return True
        if phone == user["phone"]:
            await send_text(to, SETUP["own_phone"][lang].format(family=data["parent"]))
            return True
        return await add_parent(user, to, lang, data, data["parent"], phone)

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
        if reply_id == "MORE:done" or two_choice(text) == 1 or text.lower() in DONE_WORDS:
            if data.get("for") == "me":  # PILOT 4: ask about a family member first
                with get_conn() as conn:
                    set_step(conn, user["id"], "family", data)
                await ask_family(to, lang)
                return True
            if data.get("parent_id") and not patient_of(user, data)["consent"]:  # PILOT 5: for the invite
                with get_conn() as conn:
                    set_step(conn, user["id"], "parent_lang", data)
                await ask_parent_lang(to, lang, data)
                return True
            return await finish_setup(user, to, lang, data)  # PILOT 5: data has the parent
        if text:  # PILOT 4: a medicine name typed instead of tapping "Add another"
            return await typed_name(user, to, lang, data, text)
        body = SETUP["tap_button"][lang] + "\n\n" + SETUP["next_or_done"][lang]
        await send_buttons(to, body, MORE_MED_BUTTONS[lang])
        return True

    # PILOT 5: the parent's language, for the invite and the reminders
    if step == "parent_lang":
        choice = {"PLANG:ar": 0, "PLANG:en": 1}.get(reply_id)
        if choice is None:
            choice = two_choice(text)
        if choice is None:
            await ask_parent_lang(to, lang, data, again=True)
            return True
        data["parent_lang"] = ("ar", "en")[choice]
        return await finish_setup(user, to, lang, data)

    # PILOT 4: the family alert question
    if step == "family":
        choice = {"FAMILY:yes": 0, "FAMILY:no": 1}.get(reply_id)
        if choice is None:
            choice = yes_no(text)
        if choice == 1:
            return await finish_setup(user, to, lang)
        if choice is None:
            await ask_family(to, lang, again=True)
            return True
        with get_conn() as conn:
            set_step(conn, user["id"], "family_name", data)
        await send_text(to, SETUP["family_name"][lang])
        return True

    if step == "family_name":
        if kind == "contacts":
            return await family_contact(user, to, lang, msg)
        if not text or len(text) > 40:
            await send_text(to, SETUP["family_name"][lang])
            return True
        data["family_name"] = text
        with get_conn() as conn:
            set_step(conn, user["id"], "family_phone", data)
        await send_text(to, SETUP["family_phone"][lang].format(family=text))
        return True

    if step == "family_phone":
        if kind == "contacts":
            return await family_contact(user, to, lang, msg)
        phone = parse_phone(text)
        if phone is None:
            await send_text(to, SETUP["bad_phone"][lang])
            return True
        if phone == user["phone"]:
            await send_text(to, SETUP["own_phone"][lang].format(family=data["family_name"]))
            return True
        return await add_family(user, to, lang, data["family_name"], phone)

    return False
