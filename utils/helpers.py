from datetime import datetime
import re

def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to 'whatsapp:+XXXXXXXXXXX' format.
    Handles:
      +919876543210   → whatsapp:+919876543210
      919876543210    → whatsapp:+919876543210
      09876543210     → whatsapp:+919876543210  (India)
      whatsapp:+91... → whatsapp:+919876543210  (already normalized)
    """
    if phone.startswith("whatsapp:"):
        return phone
    digits = re.sub(r"\D", "", phone)
    if not digits.startswith("+"):
        digits = f"+{digits}"
    return f"whatsapp:{digits}"


def is_valid_phone(phone: str) -> bool:
    """Basic check: must have 10-15 digits."""
    digits = re.sub(r"\D", "", phone)
    return 10 <= len(digits) <= 15


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def truncate(text: str, max_len: int = 100) -> str:
    """Truncate a string for logging/display."""
    return text if len(text) <= max_len else text[:max_len] + "..."


def safe_get(d: dict, *keys, default=None):
    """Safely traverse nested dict keys."""
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current
