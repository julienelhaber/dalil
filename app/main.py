import asyncio  # STEP 2
from contextlib import asynccontextmanager  # NEW

from fastapi import FastAPI, Request, Response, HTTPException
from app.access import handle_access  # PILOT 1
from app.care import handle_check, handle_reason, handle_typed_reason  # STEP 3
from app.config import settings
from app.consent import handle_consent  # STEP 5
from app.deletion import handle_delete  # PILOT 8: delete my data
from app.db import init_db, upsert_inbound_user  # NEW
from app.photo import handle_med_no, handle_photo  # STEP 4 (PILOT 3: MED_YES moved to setup.py)
from app.reminders import handle_dose_reply, handle_text, scheduler_loop, send_reminder  # STEP 2
from app.mymeds import MY_MEDS_IDS, handle_my_meds_reply, show_list  # PILOT 8
from app.setup import handle_setup, is_my_meds, offer_medicine  # PILOT 2 (PILOT 4, PILOT 8)
from app.texts import TEXTS  # STEP 5
from app.whatsapp import send_text


@asynccontextmanager  # NEW
async def lifespan(app: FastAPI):  # NEW
    init_db()  # NEW: create dalil.db + tables on startup
    task = asyncio.create_task(scheduler_loop())  # STEP 2: check reminders every 30 s
    yield  # NEW
    task.cancel()  # STEP 2


app = FastAPI(lifespan=lifespan)  # CHANGED


@app.get("/webhook")
async def verify(request: Request):
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == settings.VERIFY_TOKEN:
        return Response(content=p.get("hub.challenge"), media_type="text/plain")
    raise HTTPException(status_code=403)


@app.post("/webhook")
async def receive(request: Request):
    data = await request.json()
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = value.get("contacts", [])  # NEW
            contact = contacts[0] if contacts else {}  # NEW
            for msg in value.get("messages", []):
                sender = msg["from"]

                # NEW: who is this?
                phone = sender if sender.isdigit() else None
                wa_user_id = contact.get("user_id") or msg.get("from_user_id")
                name = contact.get("profile", {}).get("name")

                user, is_new = upsert_inbound_user(wa_user_id, phone, name)

                # STEP 2: answer the message (an error never breaks the webhook)
                try:
                    await handle_message(user, msg, is_new)
                except Exception as e:
                    print("Handle error:", e)
    return {"status": "ok"}


# STEP 2: everything below is new
async def handle_message(user, msg, is_new):
    if await handle_access(user, msg, is_new):  # PILOT 1: new numbers wait for the admin
        return
    if await handle_delete(user, msg):  # PILOT 8: before consent, so it works after STOP too
        return
    if await handle_consent(user, msg):  # STEP 5: consent and STOP come first
        return
    if await handle_setup(user, msg):  # PILOT 2: people in the middle of setup
        return
    kind = msg.get("type")
    if kind == "button":
        if await handle_reply_id(user, msg["button"].get("payload", "")):
            return
    elif kind == "interactive":
        reply = msg["interactive"]  # PILOT 8: menu rows too ("my medicines")
        reply_id = (reply.get("button_reply") or reply.get("list_reply") or {}).get("id", "")
        if await handle_reply_id(user, reply_id):
            return
    elif kind == "image":  # STEP 4
        if await handle_photo(user, msg["image"]["id"]):
            return
    elif kind == "text":
        text = msg["text"]["body"]  # STEP 3: a reason typed after Problem comes first
        if ((is_my_meds(text) and await show_list(user))  # PILOT 8
                or await handle_typed_reason(user, text)
                or await offer_medicine(user, text)  # PILOT 4: a medicine name typed after setup
                or await handle_text(user, text)):
            return
    lang = "ar" if user["language"] == "ar" else "en"  # STEP 5: help instead of "Welcome back"
    await send_text(msg["from"], TEXTS["menu"][lang])


async def handle_reply_id(user, reply_id):
    """Button ids look like TAKEN:12. Returns False if the id is unknown."""
    parts = reply_id.split(":")
    if parts[0] in ("TAKEN", "LATER", "PROBLEM") and len(parts) == 2:
        return await handle_dose_reply(user, parts[0], int(parts[1]))
    if parts[0] == "REASON" and len(parts) == 3:  # STEP 3
        return await handle_reason(user, int(parts[1]), parts[2])
    if parts[0] == "CHECK" and len(parts) == 2:  # STEP 3
        return await handle_check(user, int(parts[1]))
    if parts[0] in MY_MEDS_IDS:  # PILOT 8
        return await handle_my_meds_reply(user, reply_id)
    if parts[0] == "MED_NO":  # STEP 4
        return await handle_med_no(user)
    return False


@app.get("/demo/remind/{schedule_id}")
async def demo_remind(schedule_id: int, key: str = ""):
    """Send a reminder now, for testing and the demo video."""
    if key != settings.VERIFY_TOKEN:
        raise HTTPException(status_code=403)
    return {"event_id": await send_reminder(schedule_id)}
