"""Unified API-first sync for all marketplace platforms."""

from app.services.amazon_service import AmazonService
from app.services.flipkart_service import FlipkartService
from app.services.google_business_service import GoogleBusinessService
from app.services.myntra_service import MyntraService

# All platforms that support optional Chrome extension import/reply assist
EXTENSION_COMPATIBLE_PLATFORMS = {
    "amazon", "flipkart", "myntra", "meesho", "google_business",
}


async def fetch_reviews_via_api(
    platform: str, creds: dict
) -> tuple[list[dict], str | None, dict | None]:
    """
    Returns (reviews, sync_message, updated_creds).
    updated_creds is set when tokens are refreshed (e.g. Google).
    """
    if platform == "amazon":
        svc = AmazonService(creds)
        reviews, msg = await svc.fetch_reviews(creds.get("asin"))
        return reviews, msg, None

    if platform == "flipkart":
        svc = FlipkartService(creds)
        reviews, msg = await svc.fetch_reviews()
        return reviews, msg, None

    if platform == "myntra":
        svc = MyntraService(creds)
        reviews, msg = await svc.fetch_reviews()
        return reviews, msg, None

    if platform == "google_business":
        svc = GoogleBusinessService(creds)
        reviews, updated = await svc.fetch_reviews()
        return reviews, None, updated

    if platform in ("meesho",):
        return [], (
            "Meesho Seller API not yet configured. Connect via API when available, "
            "or use the optional Chrome extension on Meesho seller portal."
        ), None

    return [], f"No API sync configured for platform: {platform}", None


def extension_hint(platform: str, creds: dict) -> str:
    last = creds.get("last_extension_import")
    base = (
        f"Optional: use the ReviewFlow Chrome extension on your {platform.replace('_', ' ')} "
        "seller portal to import reviews or apply AI replies where API posting is limited."
    )
    if last:
        return f"Last extension import: {last}. {base}"
    return base
