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


UNITS = {"MG", "G", "ML", "MCG", "UI", "IU", "TAB", "TABS", "CAP", "CAPS"}  # PILOT 3


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


def find_drugs(text):
    """PILOT 3: a typed medicine name. Up to 9 drug_reference rows, closest first."""
    words = re.sub(r"[^A-Za-zÀ-ÿ\- ]", " ", text).upper().split()
    query = " ".join(w for w in words if w not in UNITS)
    if len(query) < 3:
        return []
    numbers = {number(n) for n in re.findall(r"\d+(?:[.,]\d+)?", text)}
    with get_conn() as conn:
        brands = [r[0] for r in conn.execute("SELECT DISTINCT brand_name FROM drug_reference")]
        scored = []
        for brand in brands:
            score = fuzz.ratio(query, brand)
            if brand.startswith((query + " ", query + "-")):  # CONCOR -> CONCOR PLUS
                score = max(score, 92)
            if score >= 80:
                scored.append((-score, len(brand), brand))
        rows = []
        for _, _, brand in sorted(scored)[:5]:
            rows += conn.execute(
                "SELECT * FROM drug_reference WHERE brand_name = ? ORDER BY id", (brand,)
            ).fetchall()
    seen, unique = set(), []
    for row in rows:  # the MoPH list has some exact duplicates
        key = (row["brand_name"], row["strength"], row["presentation"])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    if numbers:  # "amlor 5" keeps the 5mg rows
        unique = [r for r in unique if number(r["strength"]) in numbers] or unique
    return unique[:9]


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


async def save_medicine(user, drug_id, typed_name=None):
    """PILOT 3: double-dose check, then save. Returns the new medicine id, or None if not saved."""
    lang = lang_of(user)
    with get_conn() as conn:
        drug = None
        if drug_id:
            drug = conn.execute("SELECT * FROM drug_reference WHERE id = ?", (drug_id,)).fetchone()
        current = conn.execute(
            """SELECT m.display_name, d.ingredients FROM medicines m
               LEFT JOIN drug_reference d ON d.id = m.drug_id
               WHERE m.patient_id = ? AND m.active = 1""",
            (user["id"],),
        ).fetchall()
        family = caregivers(conn, user["id"])
    if drug is None and not typed_name:
        return None
    new = drug_name(drug) if drug else typed_name
    ingredients = set(((drug and drug["ingredients"]) or "").split(";")) - {""}
    for med in current:
        shared = ingredients & set((med["ingredients"] or "").split(";"))
        if shared:
            args = {"new": new, "old": med["display_name"],
                    "shared": ", ".join(sorted(shared)), "patient": user["name"]}
            await send_text(user["phone"], TEXTS["same"][lang].format(**args))
            for c in family:
                await send_text(c["phone"], TEXTS["same_family"][lang_of(c)].format(**args))
            return None
    if current and not ingredients:  # nothing to compare with in our data
        await send_text(user["phone"], TEXTS["unknown"][lang].format(new=new))
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO medicines (patient_id, drug_id, display_name,
                                     pack_size, tablets_left, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user["id"], drug["id"] if drug else None, new,
             drug["pack_size"] if drug else None, drug["pack_size"] if drug else None, now_utc()),
        )
    return cur.lastrowid
