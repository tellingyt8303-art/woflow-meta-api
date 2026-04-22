import re
from typing import Optional

def match_keyword(text: str, keywords: list[str]) -> bool:
    """
    Returns True if any keyword appears in text (case-insensitive, whole-word or partial).
    Supports:
      - Simple words: "price", "demo"
      - Phrases: "book appointment"
      - Regex patterns (prefixed with "regex:"): "regex:pric(e|ing)"
    """
    text_lower = text.lower().strip()
    for kw in keywords:
        kw = kw.strip()
        if kw.startswith("regex:"):
            pattern = kw[6:]
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        else:
            if kw.lower() in text_lower:
                return True
    return False


def find_best_template(text: str, templates: list[dict]) -> Optional[dict]:
    """
    Given a list of template dicts (from Firestore), return the best matching one.
    Priority:
      1. Exact keyword match (longest keyword wins for specificity)
      2. Default template (is_default=True)
      3. None
    """
    active_templates = [t for t in templates if t.get("active", True)]

    best_match = None
    best_kw_len = 0

    for template in active_templates:
        keywords = template.get("trigger_keywords", [])
        if not keywords:
            continue
        for kw in keywords:
            if match_keyword(text, [kw]) and len(kw) > best_kw_len:
                best_match = template
                best_kw_len = len(kw)

    if best_match:
        return best_match

    # Fall back to default template
    for template in active_templates:
        if template.get("is_default", False):
            return template

    return None
