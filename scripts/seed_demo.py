from app.config import settings
from app.db import get_conn, init_db, now_utc

# MoPH code, name shown to the user, pack size, reminder times (Beirut)
GEORGES_MEDS = [
    ("11468", "Gastrimut 20mg", 28, ["08:00"]),
    ("1602", "Tamiflu 75mg", 10, ["09:00", "21:00"]),
    ("4699", "Glucophage 850mg", 30, ["13:00"]),
    ("3531", "Amlor 5mg", 30, ["20:00"]),
]


def upsert_user(conn, phone, name, language):
    row = conn.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
    if row:
        conn.execute(
            "UPDATE users SET name = ?, language = ?, consent = 1 WHERE id = ?",
            (name, language, row["id"]),
        )
        return row["id"]
    cur = conn.execute(
        """INSERT INTO users (phone, name, language, consent, created_at)
           VALUES (?, ?, ?, 1, ?)""",
        (phone, name, language, now_utc()),
    )
    return cur.lastrowid


def main():
    if not (settings.DEMO_GEORGES_PHONE and settings.DEMO_RITA_PHONE):
        raise SystemExit("Add DEMO_GEORGES_PHONE and DEMO_RITA_PHONE to .env")
    init_db()
    now = now_utc()
    with get_conn() as conn:
        georges = upsert_user(conn, settings.DEMO_GEORGES_PHONE, "Georges", "ar")
        rita = upsert_user(conn, settings.DEMO_RITA_PHONE, "Rita", "en")
        conn.execute(
            """INSERT OR IGNORE INTO care_links (caregiver_id, patient_id, created_at)
               VALUES (?, ?, ?)""",
            (rita, georges, now),
        )
        conn.execute("DELETE FROM medicines WHERE patient_id = ?", (georges,))
        for code, name, pack, times in GEORGES_MEDS:
            drug = conn.execute(
                "SELECT id FROM drug_reference WHERE moph_code = ?", (code,)
            ).fetchone()
            if drug is None:
                print("Not in the drug list:", code, name)
            cur = conn.execute(
                """INSERT INTO medicines (patient_id, drug_id, display_name,
                                         pack_size, tablets_left, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (georges, drug["id"] if drug else None, name, pack, pack, now),
            )
            for t in times:
                conn.execute(
                    "INSERT INTO schedules (medicine_id, time_of_day) VALUES (?, ?)",
                    (cur.lastrowid, t),
                )
    print(f"Seeded Georges (user {georges}) and Rita (user {rita})")


if __name__ == "__main__":
    main()