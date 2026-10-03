import pandas as pd

from app.db import DB_PATH, get_conn, init_db

DATA = DB_PATH.parent / "data"


def clean(value):
    if pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).split()) or None


def main():
    init_db()
    drugs = pd.read_excel(DATA / "moph_marketed.xls", engine="xlrd")
    extra = pd.read_csv(DATA / "ingredients_demo.csv")
    extra = {r.brand_name.strip().upper(): r for r in extra.itertuples()}

    rows = []
    for _, d in drugs.iterrows():
        brand = clean(d["Brand name"])
        if not brand:
            continue
        presentation = clean(d["Presentation"])
        pack = int(presentation) if presentation and presentation.isdigit() else None
        price = d["Public Price LL"]
        info = extra.get(brand.upper())
        rows.append((
            clean(d["Code"]), brand, clean(d["Strength"]), presentation, pack,
            clean(d["Form"]),
            None if pd.isna(price) else int(round(price)),
            info.ingredients if info else None,
            info.drug_class if info else None,
        ))

    with get_conn() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO drug_reference
               (moph_code, brand_name, strength, presentation, pack_size,
                form, price_lbp, ingredients, drug_class)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        total, matched = conn.execute(
            "SELECT COUNT(*), COUNT(ingredients) FROM drug_reference"
        ).fetchone()
    print(f"Loaded {total} drugs, {matched} with ingredients")


if __name__ == "__main__":
    main()