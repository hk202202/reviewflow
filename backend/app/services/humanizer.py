import re
import random
from typing import Optional


AI_PHRASES_TO_REMOVE = [
    "certainly", "absolutely", "I hope this helps", "I'd be happy to",
    "feel free to", "please don't hesitate", "rest assured",
    "we appreciate your feedback", "thank you for bringing this to our attention",
]

PLATFORM_VOCAB = {
    "amazon": ["great value", "fast shipping", "as described", "Prime delivery"],
    "flipkart": ["value for money", "fast delivery", "good packaging", "Flipkart assured"],
    "myntra": ["perfect fit", "great quality", "stylish", "Myntra experience"],
    "google_business": ["visit us again", "local business", "our team"],
}


def humanize_text(text: str, platform: Optional[str] = None, typo_prob: float = 0.0) -> str:
    result = text
    for phrase in AI_PHRASES_TO_REMOVE:
        result = re.sub(re.escape(phrase), "", result, flags=re.IGNORECASE)

    if platform and platform in PLATFORM_VOCAB:
        if random.random() < 0.3:
            vocab = random.choice(PLATFORM_VOCAB[platform])
            result = result.rstrip(".") + f" — {vocab}."

    sentences = re.split(r'(?<=[.!?])\s+', result)
    if len(sentences) > 2 and random.random() < 0.4:
        idx = random.randint(0, len(sentences) - 2)
        sentences[idx], sentences[idx + 1] = sentences[idx + 1], sentences[idx]
    result = " ".join(sentences)

    if typo_prob > 0 and random.random() < typo_prob:
        words = result.split()
        if words:
            idx = random.randint(0, len(words) - 1)
            word = words[idx]
            if len(word) > 3:
                char_idx = random.randint(1, len(word) - 2)
                words[idx] = word[:char_idx] + word[char_idx + 1] + word[char_idx] + word[char_idx + 1:]
                result = " ".join(words)

    result = re.sub(r'\s+', ' ', result).strip()
    return result
