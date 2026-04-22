"""
routes.py — REST API endpoints for dashboard + admin

Authentication: Firebase ID Token (Bearer header)
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from firebase_admin import auth as firebase_auth
from datetime import datetime

from database.models import (
    Client, Lead, Template, Followup,
    UserCreate, LeadStatus, WhatsAppConnectRequest
)
from database.db import create_doc, get_doc, update_doc, query_docs
from config import (
    COLLECTION_CLIENTS, COLLECTION_LEADS, COLLECTION_MESSAGES,
    COLLECTION_TEMPLATES, COLLECTION_FOLLOWUPS
)
from onboarding.number_manager import (
    register_client, list_all_clients,
    verify_and_save_whatsapp, disconnect_whatsapp, get_client
)
from leads.lead_manager import get_leads_for_client, update_lead_status, get_lead_stats
from followups.scheduler import process_due_followups, cancel_followups
from messaging.sender import send_whatsapp_message

router = APIRouter()

# ─── Auth Helper ─────────────────────────────────────────────

async def verify_token(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    try:
        return firebase_auth.verify_id_token(authorization.split(" ")[1])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

# ─── Auth ────────────────────────────────────────────────────

@router.post("/auth/register")
async def register_user(user: UserCreate):
    """Firebase mein naya user banao + client document create karo."""
    try:
        fb_user = firebase_auth.create_user(
            email=user.email, password=user.password, display_name=user.name
        )
        # Client document bhi banao
        client_id = register_client({
            "name":          user.name,
            "email":         user.email,
            "business_name": user.business_name,
            "firebase_uid":  fb_user.uid,
        })
        # User document mein client_id link karo
        create_doc("users", {
            "uid": fb_user.uid, "email": user.email,
            "name": user.name, "client_id": client_id,
            "created_at": datetime.utcnow().isoformat(),
        }, doc_id=fb_user.uid)
        return {"uid": fb_user.uid, "client_id": client_id, "message": "Registered"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ─── WhatsApp Connect / Disconnect ───────────────────────────

@router.post("/whatsapp/connect/{client_id}")
async def connect_whatsapp(
    client_id: str,
    req: WhatsAppConnectRequest,
    user=Depends(verify_token)
):
    """
    User dashboard se Phone Number ID + Access Token submit karta hai.
    Meta API se verify karke Firebase mein save karo.
    """
    result = await verify_and_save_whatsapp(
        client_id=client_id,
        phone_number_id=req.phone_number_id,
        access_token=req.access_token,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/whatsapp/disconnect/{client_id}")
async def disconnect_wa(client_id: str, user=Depends(verify_token)):
    disconnect_whatsapp(client_id)
    return {"message": "WhatsApp disconnected"}

@router.get("/whatsapp/status/{client_id}")
async def wa_status(client_id: str, user=Depends(verify_token)):
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return {
        "connected":      client.get("wa_connected", False),
        "number":         client.get("whatsapp_number"),
        "verified_name":  client.get("wa_verified_name"),
        "connected_at":   client.get("wa_connected_at"),
    }

# ─── Send Manual Message ─────────────────────────────────────

@router.post("/messages/send/{client_id}")
async def send_manual_message(
    client_id: str,
    payload: dict,
    user=Depends(verify_token)
):
    """Dashboard se manually message bhejo."""
    client = get_client(client_id)
    if not client or not client.get("wa_connected"):
        raise HTTPException(status_code=400, detail="WhatsApp not connected")

    msg_id = await send_whatsapp_message(
        to=payload["to"],
        body=payload["body"],
        phone_number_id=client["meta_phone_number_id"],
        access_token=client["meta_access_token"],
    )
    if not msg_id:
        raise HTTPException(status_code=500, detail="Message send failed")
    return {"message_id": msg_id, "status": "sent"}

# ─── Templates ───────────────────────────────────────────────

@router.post("/templates")
async def create_template(template: Template, user=Depends(verify_token)):
    data = {**template.dict(exclude={"id"}), "created_at": datetime.utcnow().isoformat()}
    tid  = create_doc(COLLECTION_TEMPLATES, data)
    return {"id": tid}

@router.get("/templates/{client_id}")
async def list_templates(client_id: str, user=Depends(verify_token)):
    return query_docs(COLLECTION_TEMPLATES, filters=[("client_id", "==", client_id)])

@router.put("/templates/{template_id}")
async def update_template(template_id: str, data: dict, user=Depends(verify_token)):
    update_doc(COLLECTION_TEMPLATES, template_id, data)
    return {"message": "Updated"}

@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, user=Depends(verify_token)):
    from database.db import delete_doc
    delete_doc(COLLECTION_TEMPLATES, template_id)
    return {"message": "Deleted"}

# ─── Leads ───────────────────────────────────────────────────

@router.get("/leads/{client_id}")
async def get_leads(client_id: str, status: Optional[str] = None, user=Depends(verify_token)):
    return get_leads_for_client(client_id, status)

@router.put("/leads/{lead_id}/status")
async def set_lead_status(lead_id: str, status: str, notes: Optional[str] = None, user=Depends(verify_token)):
    if status not in [s.value for s in LeadStatus]:
        raise HTTPException(status_code=400, detail="Invalid status")
    update_lead_status(lead_id, status, notes)
    return {"message": "Updated"}

@router.get("/leads/{client_id}/stats")
async def lead_stats(client_id: str, user=Depends(verify_token)):
    return get_lead_stats(client_id)

# ─── Messages ────────────────────────────────────────────────

@router.get("/messages/{client_id}")
async def get_messages(client_id: str, lead_phone: Optional[str] = None, user=Depends(verify_token)):
    filters = [("client_id", "==", client_id)]
    if lead_phone:
        filters.append(("lead_phone", "==", lead_phone))
    return query_docs(COLLECTION_MESSAGES, filters=filters, limit=200)

# ─── Follow-ups ──────────────────────────────────────────────

@router.get("/followups/{client_id}")
async def get_followups(client_id: str, status: Optional[str] = None, user=Depends(verify_token)):
    filters = [("client_id", "==", client_id)]
    if status:
        filters.append(("status", "==", status))
    return query_docs(COLLECTION_FOLLOWUPS, filters=filters)

@router.post("/followups/process")
async def trigger_followups(user=Depends(verify_token)):
    count = await process_due_followups()
    return {"processed": count}

@router.delete("/followups/{client_id}/{lead_phone}")
async def cancel_lead_followups(client_id: str, lead_phone: str, user=Depends(verify_token)):
    cancel_followups(client_id, lead_phone)
    return {"message": "Cancelled"}

# ─── Dashboard Summary ───────────────────────────────────────

@router.get("/dashboard/{client_id}")
async def dashboard(client_id: str, user=Depends(verify_token)):
    client     = get_client(client_id)
    lead_stats = get_lead_stats(client_id)
    pending_fu = query_docs(COLLECTION_FOLLOWUPS, filters=[
        ("client_id", "==", client_id), ("status", "==", "pending")
    ])
    recent_msg = query_docs(COLLECTION_MESSAGES, filters=[
        ("client_id", "==", client_id)
    ], limit=10)
    templates  = query_docs(COLLECTION_TEMPLATES, filters=[
        ("client_id", "==", client_id), ("active", "==", True)
    ])
    return {
        "whatsapp": {
            "connected":     client.get("wa_connected", False),
            "number":        client.get("whatsapp_number"),
            "verified_name": client.get("wa_verified_name"),
        },
        "leads":            lead_stats,
        "pending_followups": len(pending_fu),
        "recent_messages":  recent_msg,
        "active_templates": len(templates),
    }

# ─── Admin — All Clients ─────────────────────────────────────

@router.get("/admin/clients")
async def admin_clients(user=Depends(verify_token)):
    return list_all_clients()

@router.put("/admin/clients/{client_id}/suspend")
async def suspend_client(client_id: str, user=Depends(verify_token)):
    update_doc(COLLECTION_CLIENTS, client_id, {"active": False})
    return {"message": "Suspended"}

@router.put("/admin/clients/{client_id}/restore")
async def restore_client(client_id: str, user=Depends(verify_token)):
    update_doc(COLLECTION_CLIENTS, client_id, {"active": True})
    return {"message": "Restored"}
