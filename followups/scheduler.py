"""
scheduler.py — Automatic follow-up messages schedule aur send karna

Jab naya lead aata hai → automatically follow-ups schedule hote hain.
APScheduler har 15 minute mein due follow-ups check karta hai.
"""
from datetime import datetime, timedelta
from typing import Optional
from database.db import query_docs, create_doc, update_doc
from database.models import Followup, FollowupStatus
from config import COLLECTION_FOLLOWUPS, COLLECTION_TEMPLATES, DEFAULT_FOLLOWUP_INTERVALS


async def schedule_followups(client_id: str, lead_phone: str):
    """
    Naye lead ke liye follow-up messages schedule karo.
    Day 1, Day 3, Day 7 (DEFAULT_FOLLOWUP_INTERVALS se).
    """
    templates = query_docs(
        COLLECTION_TEMPLATES,
        filters=[("client_id", "==", client_id), ("active", "==", True)]
    )
    # Default nahi, sirf follow-up ke liye templates
    followup_templates = [t for t in templates if not t.get("is_default", False)]
    now = datetime.utcnow()

    for i, days in enumerate(DEFAULT_FOLLOWUP_INTERVALS):
        scheduled_time = now + timedelta(days=days)
        template_id    = None
        message_body   = "Hi! Bas ek follow-up — kya hum aapki kisi cheez mein madad kar sakte hain? 😊"

        if followup_templates:
            tmpl         = followup_templates[i % len(followup_templates)]
            template_id  = tmpl.get("id")
            message_body = tmpl.get("message_body", message_body)

        followup = Followup(
            client_id=client_id,
            lead_phone=lead_phone,
            template_id=template_id,
            message_body=message_body,
            scheduled_at=scheduled_time.isoformat(),
            status=FollowupStatus.pending,
            attempt=i + 1,
        )
        create_doc(COLLECTION_FOLLOWUPS, followup.dict(exclude={"id"}))

    print(f"📅 {len(DEFAULT_FOLLOWUP_INTERVALS)} follow-ups scheduled for {lead_phone}")


async def process_due_followups():
    """
    Due follow-ups dhundo aur bhejo.
    APScheduler se har 15 minute mein call hota hai.
    """
    from messaging.sender import send_whatsapp_message
    from onboarding.number_manager import get_client

    now_iso = datetime.utcnow().isoformat()

    pending = query_docs(
        COLLECTION_FOLLOWUPS,
        filters=[("status", "==", FollowupStatus.pending.value)]
    )

    sent_count = 0
    for followup in pending:
        if followup["scheduled_at"] <= now_iso:
            client = get_client(followup["client_id"])
            if not client or not client.get("wa_connected"):
                print(f"⚠️  Client not connected, skipping followup for {followup['lead_phone']}")
                continue

            # Meta API ke saath bhejo
            msg_id = await send_whatsapp_message(
                to=followup["lead_phone"],
                body=followup["message_body"],
                phone_number_id=client["meta_phone_number_id"],
                access_token=client["meta_access_token"],
            )

            new_status = FollowupStatus.sent if msg_id else FollowupStatus.failed
            update_doc(COLLECTION_FOLLOWUPS, followup["id"], {
                "status":           new_status.value,
                "sent_at":          datetime.utcnow().isoformat(),
                "meta_message_id":  msg_id,
            })
            sent_count += 1

    print(f"✅ Follow-up batch: {sent_count} processed")
    return sent_count


def cancel_followups(client_id: str, lead_phone: str):
    """Lead convert ho gayi ya reply aa gayi — follow-ups cancel karo."""
    pending = query_docs(
        COLLECTION_FOLLOWUPS,
        filters=[
            ("client_id",  "==", client_id),
            ("lead_phone", "==", lead_phone),
            ("status",     "==", FollowupStatus.pending.value),
        ]
    )
    for f in pending:
        update_doc(COLLECTION_FOLLOWUPS, f["id"], {"status": FollowupStatus.cancelled.value})
    print(f"🚫 {len(pending)} follow-ups cancelled for {lead_phone}")
