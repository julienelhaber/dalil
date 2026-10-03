import asyncio  # STEP 2
from contextlib import asynccontextmanager  # NEW

from fastapi import FastAPI, Request, Response, HTTPException
from app.care import handle_check, handle_reason, handle_typed_reason  # STEP 3
from app.config import settings
from app.db import init_db, upsert_inbound_user  # NEW
from app.reminders import handle_dose_reply, handle_text, scheduler_loop, send_reminder  # STEP 2
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
    kind = msg.get("type")
    if kind == "button":
        if await handle_reply_id(user, msg["button"].get("payload", "")):
            return
    elif kind == "interactive":
        reply_id = msg["interactive"].get("button_reply", {}).get("id", "")
        if await handle_reply_id(user, reply_id):
            return
    elif kind == "text":
        text = msg["text"]["body"]  # STEP 3: a reason typed after Problem comes first
        if await handle_typed_reason(user, text) or await handle_text(user, text):
            return
    who = user["name"] or "friend"
    greeting = "Welcome to Dalil" if is_new else "Welcome back"
    await send_text(msg["from"], f"{greeting}, {who}!")


async def handle_reply_id(user, reply_id):
    """Button ids look like TAKEN:12. Returns False if the id is unknown."""
    parts = reply_id.split(":")
    if parts[0] in ("TAKEN", "LATER", "PROBLEM") and len(parts) == 2:
        return await handle_dose_reply(user, parts[0], int(parts[1]))
    if parts[0] == "REASON" and len(parts) == 3:  # STEP 3
        return await handle_reason(user, int(parts[1]), parts[2])
    if parts[0] == "CHECK" and len(parts) == 2:  # STEP 3
        return await handle_check(user, int(parts[1]))
    return False


@app.get("/demo/remind/{schedule_id}")
async def demo_remind(schedule_id: int, key: str = ""):
    """Send a reminder now, for testing and the demo video."""
    if key != settings.VERIFY_TOKEN:
        raise HTTPException(status_code=403)
    return {"event_id": await send_reminder(schedule_id)}
