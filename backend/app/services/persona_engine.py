import random
from typing import Optional
from app.services.humanizer import humanize_text


DEFAULT_PERSONAS = [
    {"name": "Casual Buyer", "age_range": "25-35", "location": "Mumbai", "writing_style": "terse", "typo_probability": 0.1, "vocab_level": "simple"},
    {"name": "Detailed Reviewer", "age_range": "35-45", "location": "Delhi", "writing_style": "verbose", "typo_probability": 0.02, "vocab_level": "advanced"},
    {"name": "Emoji Enthusiast", "age_range": "18-25", "location": "Bangalore", "writing_style": "emoji-heavy", "typo_probability": 0.08, "vocab_level": "simple"},
    {"name": "Professional Shopper", "age_range": "40-50", "location": "Chennai", "writing_style": "formal", "typo_probability": 0.01, "vocab_level": "advanced"},
]


def get_persona_prompt(persona: dict) -> str:
    style_map = {
        "terse": "Write very briefly, 1-2 short sentences.",
        "verbose": "Write a detailed review with 4-6 sentences covering multiple aspects.",
        "emoji-heavy": "Use 2-3 relevant emojis naturally in the review.",
        "formal": "Write in a formal, professional tone.",
        "moderate": "Write a balanced review of 2-4 sentences.",
    }
    vocab_map = {
        "simple": "Use simple everyday language.",
        "moderate": "Use normal conversational language.",
        "advanced": "Use sophisticated vocabulary.",
    }
    return (
        f"You are a {persona.get('age_range', '30-40')} year old buyer from {persona.get('location', 'India')}. "
        f"{style_map.get(persona.get('writing_style', 'moderate'), '')} "
        f"{vocab_map.get(persona.get('vocab_level', 'moderate'), '')}"
    )


def apply_persona_quirks(text: str, persona: dict) -> str:
    result = humanize_text(text, typo_prob=persona.get("typo_probability", 0.05))
    if persona.get("writing_style") == "emoji-heavy":
        emojis = ["👍", "😊", "⭐", "💯", "🎉"]
        if random.random() < 0.7:
            result += " " + random.choice(emojis)
    return result


def pick_random_persona() -> dict:
    return random.choice(DEFAULT_PERSONAS)
