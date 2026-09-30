from contextlib import asynccontextmanager  # NEW

from fastapi import FastAPI, Request, Response, HTTPException
from app.config import settings
from app.db import init_db, upsert_inbound_user  # NEW
from app.whatsapp import send_text


@asynccontextmanager  # NEW
async def lifespan(app: FastAPI):  # NEW
    init_db()  # NEW: create dalil.db + tables on startup
    yield  # NEW


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

                # NEW: reply based on new vs returning
                who = user["name"] or "friend"
                if is_new:
                    reply = f"Welcome to Dalil, {who}!"
                else:
                    reply = f"Welcome back, {who}!"
                await send_text(sender, reply)
    return {"status": "ok"}