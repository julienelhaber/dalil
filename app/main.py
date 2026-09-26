from fastapi import FastAPI, Request, Response, HTTPException
from app.config import settings
from app.whatsapp import send_text

app = FastAPI()

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
            for msg in value.get("messages", []):
                sender = msg["from"]
                if msg["type"] == "text":
                    await send_text(sender, f"Dalil heard: {msg['text']['body']}")
                else:
                    await send_text(sender, f"Dalil got a {msg['type']} message.")
    return {"status": "ok"}