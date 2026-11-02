from openai import AsyncOpenAI
from typing import Optional
from app.core.config import get_settings
from app.services.humanizer import humanize_text
from app.services.persona_engine import get_persona_prompt, apply_persona_quirks, pick_random_persona

settings = get_settings()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None


async def generate_reply(
    review_body: str,
    rating: int,
    product_name: str = "",
    brand_name: str = "",
    brand_tone: str = "friendly",
    platform: Optional[str] = None,
) -> str:
    if not client:
        return _fallback_reply(review_body, rating, product_name, brand_name, brand_tone)

    prompt = f"""Write a seller reply to this customer review. Be {brand_tone} and human-sounding.
Product: {product_name}
Brand: {brand_name}
Rating: {rating}/5
Review: {review_body}

Rules:
- Keep it under 150 words
- Do NOT use phrases like "certainly", "absolutely", "I hope this helps"
- Sound like a real human seller, not an AI
- Address the specific points in the review
- For negative reviews, apologize sincerely and offer a solution"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.8,
        )
        text = response.choices[0].message.content or ""
        return humanize_text(text, platform=platform)
    except Exception:
        return _fallback_reply(review_body, rating, product_name, brand_name, brand_tone)


async def generate_review(
    product_title: str,
    product_features: str = "",
    rating_target: int = 5,
    persona: Optional[dict] = None,
) -> str:
    persona = persona or pick_random_persona()
    if not client:
        return _fallback_review(product_title, rating_target, persona)

    persona_prompt = get_persona_prompt(persona)
    prompt = f"""{persona_prompt}

Write a {rating_target}-star product review for: {product_title}
Features: {product_features or 'Not specified'}

Rules:
- Sound like a genuine buyer, NOT an AI
- Match the {rating_target}-star rating in tone
- Do NOT use generic AI phrases
- Keep it natural and varied"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.9,
        )
        text = response.choices[0].message.content or ""
        return apply_persona_quirks(text, persona)
    except Exception:
        return _fallback_review(product_title, rating_target, persona)


def analyze_sentiment(body: str, rating: int) -> str:
    if rating >= 4:
        return "positive"
    if rating <= 2:
        return "negative"
    negative_words = ["bad", "terrible", "worst", "disappointed", "broken", "fake", "scam", "refund"]
    if any(w in body.lower() for w in negative_words):
        return "negative"
    positive_words = ["great", "excellent", "love", "perfect", "amazing", "best", "recommend"]
    if any(w in body.lower() for w in positive_words):
        return "positive"
    return "neutral"


def _fallback_reply(review_body: str, rating: int, product_name: str, brand_name: str, tone: str) -> str:
    if rating >= 4:
        return f"Thank you so much for your wonderful review of {product_name or 'our product'}! We're thrilled you had a great experience. — {brand_name or 'The Team'}"
    if rating == 3:
        return f"Thank you for your feedback on {product_name or 'our product'}. We appreciate you taking the time to share your experience. We're always working to improve. — {brand_name or 'The Team'}"
    return f"We're sorry to hear about your experience with {product_name or 'our product'}. We take your feedback seriously and would love to make this right. Please reach out to us directly. — {brand_name or 'The Team'}"


def _fallback_review(product_title: str, rating: int, persona: dict) -> str:
    if rating >= 4:
        return f"Really happy with {product_title}. Good quality and worth the price. Would recommend!"
    return f"Expected better from {product_title}. Not quite what I was hoping for."
