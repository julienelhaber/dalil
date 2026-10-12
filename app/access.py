from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db import get_conn, now_utc
from app.texts import (ACCESS_PENDING, ACCESS_REJECTED, ACCESS_WAITING, ADMIN, ADMIN_WORDS,
                       CONSENT_BUTTONS, CONSENT_PROMPT)
from app.whatsapp import send_buttons, send_text


def is_admin(user):
    return bool(settings.ADMIN_PHONE) and user["phone"] == settings.ADMIN_PHONE


def access_status(conn, user_id):
    """No row means approved: people from before this step, and the demo users."""
    row = conn.execute("SELECT status FROM access WHERE user_id = ?", (user_id,)).fetchone()
    return row["status"] if row else "approved"


def who(user):
    return f"{user['name'] or 'No name'} (+{user['phone']})"


def window_open(user):
    """WhatsApp only allows normal messages within 24 hours of the person's last message."""
    if not user["last_inbound_at"]:
        return False
    last = datetime.fromisoformat(user["last_inbound_at"])
    return datetime.now(timezone.utc) - last < timedelta(hours=24)


async def ask_admin(user):
    """Send the admin one request with Approve / Reject buttons."""
    await send_buttons(
        settings.ADMIN_PHONE,
        ADMIN["new"].format(who=who(user)),
        [(f"APPROVE:{user['id']}", "Approve"), (f"REJECT:{user['id']}", "Reject")],
    )


async def list_pending(admin):
    """The admin typed "pending": send every waiting request again."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT u.* FROM users u JOIN access a ON a.user_id = u.id
               WHERE a.status = 'pending' ORDER BY a.requested_at""",
        ).fetchall()
    if not rows:
        await send_text(admin["phone"], ADMIN["none"])
    for row in rows:
        await ask_admin(row)


async def decide(admin, target_id, approve):
    """The admin tapped Approve or Reject."""
    with get_conn() as conn:
        target = conn.execute("SELECT * FROM users WHERE id = ?", (target_id,)).fetchone()
        status = access_status(conn, target_id) if target else None
        if status == "pending":
            conn.execute(
                "UPDATE access SET status = ?, decided_at = ? WHERE user_id = ?",
                ("approved" if approve else "rejected", now_utc(), target_id),
            )
    if target is None:
        return
    if status != "pending":
        await send_text(admin["phone"], ADMIN["already"].format(who=who(target), status=status))
        return
    can_write = bool(target["phone"]) and window_open(target)
    if approve and can_write:
        await send_buttons(target["phone"], CONSENT_PROMPT, CONSENT_BUTTONS)
        await send_text(admin["phone"], ADMIN["approved"].format(who=who(target)))
    elif approve:
        await send_text(admin["phone"], ADMIN["approved_later"].format(who=who(target)))
    else:
        if can_write:
            await send_text(target["phone"], ACCESS_REJECTED)
        await send_text(admin["phone"], ADMIN["rejected"].format(who=who(target)))


async def handle_access(user, msg, is_new):
    """Runs before consent. Returns True if the message was handled here."""
    reply_id = msg.get("interactive", {}).get("button_reply", {}).get("id", "")
    if reply_id.startswith(("APPROVE:", "REJECT:")):
        if is_admin(user):
            action, target_id = reply_id.split(":")
            await decide(user, int(target_id), action == "APPROVE")
        return True  # anyone else tapping these buttons is ignored
    if is_admin(user):
        text = msg.get("text", {}).get("body", "").strip().lower()
        if text in ADMIN_WORDS:
            await list_pending(user)
            return True
        return False
    with get_conn() as conn:
        status = access_status(conn, user["id"])
    if status == "approved":
        return False
    if status == "pending" and is_new:
        await send_text(msg["from"], ACCESS_PENDING)
        await ask_admin(user)
    elif status == "pending":
        await send_text(msg["from"], ACCESS_WAITING)
    return True  # rejected numbers get no answer