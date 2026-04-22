"""
sender.py — Meta Cloud API se WhatsApp message bhejta hai.

Har client ka apna:
  - phone_number_id  (Meta se mila hua)
  - access_token     (user ne connect karte waqt diya)

Dono Firebase mein client document mein stored hain.
"""
import httpx
from config import META_API_BASE
from typing import Optional

# ─── Core Send Function ──────────────────────────────────────

async def send_whatsapp_message(
    to: str,
    body: str,
    phone_number_id: str,
    access_token: str,
) -> Optional[str]:
    """
    Meta Cloud API se text message bhejo.

    Args:
        to:              Recipient number e.g. "919876543210" (no + or whatsapp:)
        body:            Message text
        phone_number_id: Client ka Meta Phone Number ID
        access_token:    Client ka Meta Access Token

    Returns:
        Message ID on success, None on failure.
    """
    # Number clean karo — sirf digits chahiye
    to_clean = to.replace("whatsapp:", "").replace("+", "").replace(" ", "")

    url = f"{META_API_BASE}/{phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                to_clean,
        "type":              "text",
        "text": {
            "preview_url": False,
            "body":        body,
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=headers)
            data = resp.json()

            if resp.status_code == 200:
                msg_id = data.get("messages", [{}])[0].get("id")
                print(f"✅ Message sent | ID: {msg_id} | To: {to_clean}")
                return msg_id
            else:
                print(f"❌ Meta API error: {data}")
                return None

    except Exception as e:
        print(f"❌ Send error: {e}")
        return None


async def send_template_message(
    to: str,
    template_name: str,
    language_code: str,
    phone_number_id: str,
    access_token: str,
    components: list = None,
) -> Optional[str]:
    """
    Meta approved template message bhejo.
    (Pehle 24 ghante ke baad ya cold outreach ke liye zaruri)
    """
    to_clean = to.replace("whatsapp:", "").replace("+", "").replace(" ", "")
    url      = f"{META_API_BASE}/{phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to":   to_clean,
        "type": "template",
        "template": {
            "name":     template_name,
            "language": {"code": language_code},
        }
    }
    if components:
        payload["template"]["components"] = components

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=headers)
            data = resp.json()
            if resp.status_code == 200:
                msg_id = data.get("messages", [{}])[0].get("id")
                print(f"✅ Template sent | ID: {msg_id}")
                return msg_id
            else:
                print(f"❌ Template error: {data}")
                return None
    except Exception as e:
        print(f"❌ Template send error: {e}")
        return None


async def mark_as_read(
    message_id: str,
    phone_number_id: str,
    access_token: str,
):
    """Message ko 'read' mark karo (blue ticks)."""
    url     = f"{META_API_BASE}/{phone_number_id}/messages"
    payload = {"messaging_product": "whatsapp", "status": "read", "message_id": message_id}
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json=payload, headers=headers)
    except Exception:
        pass


async def send_bulk_messages(
    recipients: list[dict],
    phone_number_id: str,
    access_token: str,
) -> dict:
    """
    Multiple logon ko message bhejo.
    recipients: [{"to": "919876...", "body": "Hi!"}, ...]
    """
    sent, failed, results = 0, 0, []
    for r in recipients:
        msg_id = await send_whatsapp_message(
            to=r["to"], body=r["body"],
            phone_number_id=phone_number_id,
            access_token=access_token,
        )
        if msg_id:
            sent += 1
            results.append({"to": r["to"], "status": "sent", "id": msg_id})
        else:
            failed += 1
            results.append({"to": r["to"], "status": "failed"})
    return {"sent": sent, "failed": failed, "results": results}
