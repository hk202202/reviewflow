import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

MYNTRA_API_BASE = "https://api.myntra.com/v1/sellers"


class MyntraService:
    """API-first Myntra seller integration. Extension is optional fallback."""

    def __init__(self, credentials: dict):
        self.credentials = credentials
        self.api_key = credentials.get("api_key", "")
        self.api_secret = credentials.get("api_secret", "")
        self.seller_id = credentials.get("seller_id", "")

    async def get_access_token(self) -> str | None:
        if not all([self.api_key, self.api_secret]):
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{MYNTRA_API_BASE}/auth/token",
                json={"api_key": self.api_key, "api_secret": self.api_secret},
            )
            if resp.status_code == 200:
                return resp.json().get("access_token") or resp.json().get("token")
            logger.warning("Myntra token exchange failed: %s", resp.status_code)
        return None

    async def validate_credentials(self) -> dict:
        token = await self.get_access_token()
        if not token:
            return {
                "valid": False,
                "message": "Invalid or missing Myntra Seller API credentials. Contact Myntra partner team for API access.",
            }
        if not self.seller_id:
            return {"valid": True, "message": "API credentials valid. Add Seller ID to sync reviews."}
        return {"valid": True, "message": f"Myntra API connected for seller {self.seller_id}."}

    async def fetch_reviews(self) -> tuple[list[dict], str]:
        token = await self.get_access_token()
        if not token:
            return self._demo_reviews(), (
                "Using demo reviews — add Myntra Seller API credentials and click Sync. "
                "Or use the Chrome extension on Myntra seller portal as optional fallback."
            )

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{MYNTRA_API_BASE}/reviews",
                headers={"Authorization": f"Bearer {token}"},
                params={"seller_id": self.seller_id} if self.seller_id else {},
            )
            if resp.status_code == 200:
                parsed = self._parse_reviews(resp.json())
                if parsed:
                    return parsed, f"Imported {len(parsed)} review(s) via Myntra Seller API."

        return self._demo_reviews(), (
            "Myntra API connected but review feed unavailable. "
            "Use the optional Chrome extension on seller.myntra.com to import reviews."
        )

    def _parse_reviews(self, data: dict) -> list[dict]:
        items = data.get("reviews") or data.get("data") or []
        if not isinstance(items, list):
            return []
        reviews = []
        for item in items:
            body = item.get("reviewText") or item.get("feedback") or item.get("body") or ""
            if not body:
                continue
            reviews.append({
                "external_review_id": str(item.get("id") or f"my-{hash(body) % 10**10}"),
                "reviewer_name": item.get("customerName") or "Myntra Customer",
                "rating": max(1, min(5, int(item.get("rating") or 3))),
                "title": item.get("title"),
                "body": body,
                "product_name": item.get("productName") or item.get("styleName"),
                "review_date": item.get("createdAt") or datetime.now(timezone.utc).isoformat(),
            })
        return reviews

    def _demo_reviews(self) -> list[dict]:
        return [
            {
                "external_review_id": "my-demo-001",
                "reviewer_name": "Kavya M.",
                "rating": 5,
                "title": "Perfect fit",
                "body": "Love the fabric and fit. True to size chart on Myntra.",
                "product_name": "Demo Style",
                "review_date": datetime.now(timezone.utc).isoformat(),
            },
            {
                "external_review_id": "my-demo-002",
                "reviewer_name": "Rohan D.",
                "rating": 3,
                "title": "Average",
                "body": "Quality is okay but delivery took longer than expected.",
                "product_name": "Demo Style",
                "review_date": datetime.now(timezone.utc).isoformat(),
            },
        ]
