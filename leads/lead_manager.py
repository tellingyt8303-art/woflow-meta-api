from datetime import datetime
from typing import Optional
from database.db import query_docs, create_doc, update_doc, get_doc
from database.models import Lead, LeadStatus
from config import COLLECTION_LEADS
from followups.scheduler import schedule_followups


async def capture_or_update_lead(
    client_id: str,
    phone: str,
    name: Optional[str] = None,
) -> dict:
    """
    If lead exists → update last_seen + name if new info.
    If new lead    → create + schedule follow-ups.
    Returns the lead dict.
    """
    existing = query_docs(
        COLLECTION_LEADS,
        filters=[("client_id", "==", client_id), ("phone", "==", phone)]
    )

    now = datetime.utcnow().isoformat()

    if existing:
        lead = existing[0]
        updates = {"updated_at": now}
        if name and not lead.get("name"):
            updates["name"] = name
        update_doc(COLLECTION_LEADS, lead["id"], updates)
        lead.update(updates)
        print(f"👤 Existing lead updated: {phone}")
        return lead
    else:
        # New lead
        new_lead = Lead(
            client_id=client_id,
            phone=phone,
            name=name,
            status=LeadStatus.new,
            created_at=now,
            updated_at=now,
        )
        lead_data = new_lead.dict(exclude={"id"})
        lead_id = create_doc(COLLECTION_LEADS, lead_data)
        lead_data["id"] = lead_id
        print(f"🆕 New lead captured: {phone}")

        # Schedule automated follow-ups
        await schedule_followups(client_id=client_id, lead_phone=phone)

        return lead_data


def get_leads_for_client(client_id: str, status: Optional[str] = None) -> list:
    """Get all leads for a client, optionally filtered by status."""
    filters = [("client_id", "==", client_id)]
    if status:
        filters.append(("status", "==", status))
    return query_docs(COLLECTION_LEADS, filters=filters)


def update_lead_status(lead_id: str, status: str, notes: Optional[str] = None):
    """Update lead status and optionally add notes."""
    updates = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat()
    }
    if notes:
        updates["notes"] = notes
    update_doc(COLLECTION_LEADS, lead_id, updates)


def get_lead_stats(client_id: str) -> dict:
    """Return count of leads grouped by status for a client."""
    leads = query_docs(COLLECTION_LEADS, filters=[("client_id", "==", client_id)])
    stats = {"total": len(leads)}
    for status in LeadStatus:
        stats[status.value] = sum(1 for l in leads if l.get("status") == status.value)
    return stats
