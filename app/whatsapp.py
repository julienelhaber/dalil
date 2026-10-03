import httpx
from app.config import settings


def _url() -> str:
    return f"https://graph.facebook.com/{settings.GRAPH_VERSION}/{settings.PHONE_NUMBER_ID}/messages"


async def _post(payload: dict):
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(_url(), headers=headers, json=payload)
    if r.status_code >= 400:
        print("Send failed:", r.status_code, r.text)
    return r


async def send_text(to: str, body: str):
    return await _post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    })


async def send_template(to: str, name: str, lang: str, params: dict, payloads: list):
    components = [{
        "type": "body",
        "parameters": [
            {"type": "text", "parameter_name": k, "text": v} for k, v in params.items()
        ],
    }]
    for i, p in enumerate(payloads):
        components.append({
            "type": "button",
            "sub_type": "quick_reply",
            "index": str(i),
            "parameters": [{"type": "payload", "payload": p}],
        })
    return await _post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {"name": name, "language": {"code": lang}, "components": components},
    })


async def send_buttons(to: str, body: str, buttons: list):
    return await _post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": [
                {"type": "reply", "reply": {"id": bid, "title": title}}
                for bid, title in buttons
            ]},
        },
    })