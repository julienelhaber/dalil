import asyncio
import re

from rapidfuzz import fuzz, process
from rapidocr_onnxruntime import RapidOCR

from app.care import caregivers
from app.db import get_conn, now_utc
from app.reminders import lang_of
from app.texts import TEXTS, YES_NO
from app.whatsapp import download_media, send_buttons, send_text

ENGINE = RapidOCR()


def number(text):
    m = re.search(r"\d+(?:[.,]\d+)?", text or "")
    return float(m.group().replace(",", ".")) if m else None


def drug_name(drug):
    return f"{drug['brand_name'].title()} {drug['strength'] or ''}".strip()


def read_box(image):
    """OCR a box photo. Returns the best drug_reference row, or None if unsure."""
    result, _ = ENGINE(image)
    if not result:
        return None
    with get_conn() as conn:
        brands = [r[0] for r in conn.execute("SELECT DISTINCT brand_name FROM drug_reference")]
    best = (0, 0, "")
    for box, text, _ in result:
        height = box[3][1] - box[0][1]
        for word in re.sub(r"[^A-Za-zÀ-ÿ\- ]", " ", text).split():
            if len(word) >= 4:
                brand, score, _ = process.extractOne(word.upper(), brands, scorer=fuzz.ratio)
                best = max(best, (score, height, brand))
    score, _, brand = best
    if score < 80:
        return None
    text = re.sub(r"[^0-9A-Za-zÀ-ÿ.,/%+\- ]", " ", " ".join(r[1] for r in result))
    numbers = {number(n) for n in re.findall(r"\d+(?:[.,]\d+)?", text)}  # STEP 7
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM drug_reference WHERE brand_name = ? ORDER BY id", (brand,)
        ).fetchall()
    # STEP 7: keep the rows whose strength and pack size are printed on the box
    rows = [r for r in rows if number(r["strength"]) in numbers] or rows
    rows = [r for r in rows if r["pack_size"] in numbers] or rows
    return rows[0]


async def handle_photo(user, media_id):
    lang = lang_of(user)
    image = await download_media(media_id)
    drug = await asyncio.to_thread(read_box, image)
    if drug is None:
        await send_text(user["phone"], TEXTS["not_sure"][lang])
        return True
    question = TEXTS["confirm"][lang].format(name=drug_name(drug), pack=drug["presentation"])
    if drug["price_lbp"]:
        question += "\n" + TEXTS["price"][lang].format(price=f"{drug['price_lbp']:,}")
    yes, no = YES_NO[lang]
    await send_buttons(user["phone"], question, [(f"MED_YES:{drug['id']}", yes), ("MED_NO", no)])
    return True


async def handle_med_no(user):
    await send_text(user["phone"], TEXTS["declined"][lang_of(user)])
    return True


async def handle_med_yes(user, drug_id):
    """User confirmed the box: check it against their medicines."""
    lang = lang_of(user)
    with get_conn() as conn:
        drug = conn.execute("SELECT * FROM drug_reference WHERE id = ?", (drug_id,)).fetchone()
        current = conn.execute(
            """SELECT m.display_name, d.ingredients FROM medicines m
               JOIN drug_reference d ON d.id = m.drug_id
               WHERE m.patient_id = ? AND m.active = 1""",
            (user["id"],),
        ).fetchall()
        family = caregivers(conn, user["id"])
    if drug is None:
        return False
    new = drug_name(drug)
    if not drug["ingredients"]:
        await send_text(user["phone"], TEXTS["unknown"][lang].format(new=new))
        return True
    ingredients = set(drug["ingredients"].split(";"))
    for med in current:
        shared = ingredients & set((med["ingredients"] or "").split(";"))
        if shared:
            args = {"new": new, "old": med["display_name"],
                    "shared": ", ".join(sorted(shared)), "patient": user["name"]}
            await send_text(user["phone"], TEXTS["same"][lang].format(**args))
            for c in family:
                await send_text(c["phone"], TEXTS["same_family"][lang_of(c)].format(**args))
            return True
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO medicines (patient_id, drug_id, display_name,
                                     pack_size, tablets_left, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user["id"], drug_id, new, drug["pack_size"], drug["pack_size"], now_utc()),
        )
    await send_text(user["phone"], TEXTS["added"][lang].format(new=new))
    return True
