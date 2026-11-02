import re
from typing import Optional


FLAG_KEYWORDS = [
    "lawsuit", "legal action", "consumer court", "complaint", "fir",
    "ncdrc", "lawyer", "sue", "court", "police", "fraud", "scam",
    "chargeback", "refund not received", "never received", "fake product",
    "counterfeit", "dangerous", "injury", "hospital",
]

PII_PATTERNS = [
    r'\b\d{10}\b',
    r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
]


def check_review_flags(body: str, rating: int, custom_keywords: list[str] | None = None) -> tuple[bool, str | None]:
    body_lower = body.lower()
    keywords = FLAG_KEYWORDS + (custom_keywords or [])

    for kw in keywords:
        if kw.lower() in body_lower:
            return True, f"Contains sensitive keyword: '{kw}'"

    for pattern in PII_PATTERNS:
        if re.search(pattern, body):
            return True, "Contains personal information (PII)"

    if rating <= 2 and len(body) > 500:
        return True, "Long negative review — requires human review"

    anger_words = ["worst", "disgusting", "hate", "never again", "report", "boycott"]
    anger_count = sum(1 for w in anger_words if w in body_lower)
    if anger_count >= 3:
        return True, "Extreme negative sentiment detected"

    return False, None
