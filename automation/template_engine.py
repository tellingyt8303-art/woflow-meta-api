from typing import Optional, Tuple
from database.db import query_docs
from config import COLLECTION_TEMPLATES
from automation.keyword_matcher import find_best_template

def render_template(template_body: str, lead: dict, client: dict) -> str:
    """
    Replace placeholders in template body with actual values.
    Supported placeholders:
      {name}        → lead name
      {phone}       → lead phone
      {business}    → client business name
      {industry}    → client industry
    """
    replacements = {
        "{name}":      lead.get("name") or "there",
        "{phone}":     lead.get("phone", ""),
        "{business}":  client.get("business_name", ""),
        "{industry}":  client.get("industry", ""),
    }
    msg = template_body
    for placeholder, value in replacements.items():
        msg = msg.replace(placeholder, str(value))
    return msg


def process_message(
    client_id: str,
    incoming_text: str,
    lead: dict,
    client: dict,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Main function called by webhook.
    Returns: (reply_text, template_id) or (None, None) if no reply needed.
    """
    # Load all active templates for this client
    templates = query_docs(
        COLLECTION_TEMPLATES,
        filters=[("client_id", "==", client_id), ("active", "==", True)]
    )

    if not templates:
        print(f"⚠️  No templates found for client {client_id}")
        return None, None

    # Find best matching template
    matched = find_best_template(incoming_text, templates)

    if not matched:
        print(f"ℹ️  No matching template for: {incoming_text!r}")
        return None, None

    # Render the template
    reply = render_template(
        template_body=matched["message_body"],
        lead=lead,
        client=client,
    )

    return reply, matched.get("id")
