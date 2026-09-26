import httpx
from app.config import settings

def _url() -> str:
    return f"https://graph.facebook.com/{settings.GRAPH_VERSION}/{settings.PHONE_NUMBER_ID}/messages"

async def send_text(to: str, body: str):
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(_url(), headers=headers, json=payload)
        if r.status_code >= 400:
            print("Send failed:", r.status_code, r.text)
        return r