"""PILOT 8: "my medicines": the list, and stopping a medicine. Change times and dose come next."""
from app.db import get_conn
from app.reminders import lang_of
from app.setup import medicine_detail, medicine_lines, offer_drugs
from app.texts import MED_ACTION_BUTTONS, MEDS, STOP_MED_BUTTONS
from app.whatsapp import send_buttons, send_list, send_text

# Button and menu ids: MYMED:<medicine id> opens one medicine, the others act on it
MY_MEDS_IDS = ("MYMED", "MSTOP", "MSTOPYES", "MKEEP", "MTIMES", "MDOSE", "MSAME", "MADD")


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
    if kind == "MYMED":
        with get_conn() as conn:
            detail, _ = medicine_detail(conn, med["id"], lang)
        await send_buttons(to, MEDS["what"][lang].format(medicine=name, detail=detail),
                           [(f"{k}:{med['id']}", t) for k, t in MED_ACTION_BUTTONS[lang]])
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
    else:  # MTIMES, MDOSE: the next build step
        await send_text(to, MEDS["soon"][lang])
    return True
