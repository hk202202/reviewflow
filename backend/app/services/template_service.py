import re
from typing import Optional


def fill_template(body: str, context: dict) -> str:
    result = body
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", str(value or ""))
    return result


def extract_issue_keyword(body: str) -> str:
    keywords = {
        "delivery": ["delivery", "shipping", "late", "delayed", "courier"],
        "quality": ["quality", "broken", "defective", "damaged", "poor"],
        "size": ["size", "fit", "small", "large", "tight", "loose"],
        "price": ["price", "expensive", "overpriced", "cost"],
        "packaging": ["packaging", "box", "wrapped", "package"],
    }
    body_lower = body.lower()
    for issue, words in keywords.items():
        if any(w in body_lower for w in words):
            return issue
    return "general feedback"
