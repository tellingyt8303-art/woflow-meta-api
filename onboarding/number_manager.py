"""
number_manager.py — Client ka WhatsApp number Meta se connect karna

Har client ke Firebase document mein yeh fields hote hain:
  - meta_phone_number_id  → Meta ka Phone Number ID
  - meta_access_token     → Permanent Access Token
  - whatsapp_number       → e.g. "+919876543210"
  - business_name         → Business ka naam

identify_client_by_phone_id() webhook mein use hota hai —
har incoming message ke phone_number_id se client dhundta hai.
"""
import httpx
from datetime import datetime
from typing import Optional
from database.db import query_docs, create_doc, update_doc, get_doc
from database.models import Client
from config import COLLECTION_CLIENTS, META_API_BASE


# ─── Webhook ke liye — Phone ID se Client dhundo ─────────────

def identify_client_by_phone_id(phone_number_id: str) -> Optional[dict]:
    """
    Incoming webhook mein Meta phone_number_id aata hai.
    Us se match karke client return karo.
    """
    results = query_docs(
        COLLECTION_CLIENTS,
        filters=[
            ("meta_phone_number_id", "==", phone_number_id),
            ("active", "==", True),
        ]
    )
    return results[0] if results else None


# ─── Client ID se Client dhundo ──────────────────────────────

def get_client(client_id: str) -> Optional[dict]:
    return get_doc(COLLECTION_CLIENTS, client_id)


# ─── Naya Client Register karo ───────────────────────────────

def register_client(client_data: dict) -> str:
    """
    Naya business client register karo.
    client_data mein yeh fields hone chahiye:
      - name, email, business_name
      - meta_phone_number_id
      - meta_access_token
      - whatsapp_number
    """
    data = {**client_data, "active": True, "created_at": datetime.utcnow().isoformat()}
    doc_id = create_doc(COLLECTION_CLIENTS, data)
    print(f"✅ Client registered: {data.get('business_name')} | PhoneID: {data.get('meta_phone_number_id')}")
    return doc_id


# ─── WhatsApp Connect — Meta se Phone Info Verify karo ───────

async def verify_and_save_whatsapp(
    client_id: str,
    phone_number_id: str,
    access_token: str,
) -> dict:
    """
    User ne dashboard mein Phone Number ID + Access Token diya.
    Meta API se verify karo aur Firebase mein save karo.

    Returns: {"success": True, "number": "+91...", "name": "..."}
    """
    url     = f"{META_API_BASE}/{phone_number_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(url, headers=headers)
            data = resp.json()

        if resp.status_code != 200 or "error" in data:
            return {"success": False, "error": data.get("error", {}).get("message", "Invalid credentials")}

        # Meta se number details
        display_number = data.get("display_phone_number", "")
        verified_name  = data.get("verified_name", "")

        # Firebase mein update karo
        update_doc(COLLECTION_CLIENTS, client_id, {
            "meta_phone_number_id": phone_number_id,
            "meta_access_token":    access_token,
            "whatsapp_number":      display_number,
            "wa_verified_name":     verified_name,
            "wa_connected":         True,
            "wa_connected_at":      datetime.utcnow().isoformat(),
        })

        print(f"✅ WhatsApp connected: {display_number} for client {client_id}")
        return {"success": True, "number": display_number, "name": verified_name}

    except Exception as e:
        print(f"❌ WhatsApp verify error: {e}")
        return {"success": False, "error": str(e)}


# ─── WhatsApp Disconnect ─────────────────────────────────────

def disconnect_whatsapp(client_id: str):
    """Client ka WhatsApp number disconnect karo."""
    update_doc(COLLECTION_CLIENTS, client_id, {
        "meta_phone_number_id": None,
        "meta_access_token":    None,
        "wa_connected":         False,
        "wa_disconnected_at":   datetime.utcnow().isoformat(),
    })


# ─── Sabhi Active Clients ────────────────────────────────────

def list_all_clients(active_only: bool = True) -> list:
    filters = [("active", "==", True)] if active_only else []
    return query_docs(COLLECTION_CLIENTS, filters=filters)
