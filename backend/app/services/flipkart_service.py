import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

FLIPKART_API_BASE = "https://api.flipkart.net/sellers"


class FlipkartService:
    """API-first Flipkart seller integration. Extension is optional fallback."""

    def __init__(self, credentials: dict):
        self.credentials = credentials
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self.seller_id = credentials.get("seller_id", "")

    async def get_access_token(self) -> str | None:
        if not all([self.client_id, self.client_secret]):
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{FLIPKART_API_BASE}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            if resp.status_code == 200:
                return resp.json().get("access_token")
            logger.warning("Flipkart token exchange failed: %s", resp.status_code)
        return None

    async def validate_credentials(self) -> dict:
        token = await self.get_access_token()
        if not token:
            return {
                "valid": False,
                "message": "Invalid or missing Flipkart Seller API credentials (client id + secret from Flipkart Seller Hub).",
            }
        if not self.seller_id:
            return {"valid": True, "message": "API credentials valid. Add Seller ID to sync reviews.", "seller_id": ""}
        return {"valid": True, "message": f"Flipkart API connected for seller {self.seller_id}.", "seller_id": self.seller_id}

    async def fetch_reviews(self) -> tuple[list[dict], str]:
        token = await self.get_access_token()
        if not token:
            return self._demo_reviews(), (
                "Using demo reviews — add Flipkart Seller API credentials and click Sync. "
                "Or use the Chrome extension on seller.flipkart.com as optional fallback."
            )

        async with httpx.AsyncClient(timeout=30) as client:
            paths = [
                f"{FLIPKART_API_BASE}/v3/reviews",
                f"{FLIPKART_API_BASE}/reviews",
            ]
            for path in paths:
                resp = await client.get(
                    path,
                    headers={"Authorization": f"Bearer {token}"},
                    params={"sellerId": self.seller_id} if self.seller_id else {},
                )
                if resp.status_code != 200:
                    continue
                parsed = self._parse_reviews(resp.json())
                if parsed:
                    return parsed, f"Imported {len(parsed)} review(s) via Flipkart Seller API."

        return self._demo_reviews(), (
            "Flipkart API connected but review endpoint unavailable for your account. "
            "Use Sync after Flipkart enables review API access, or use the optional Chrome extension."
        )

    def _parse_reviews(self, data: dict) -> list[dict]:
        items = data.get("reviews") or data.get("data") or data.get("items") or []
        if not isinstance(items, list):
            return []
        reviews = []
        for item in items:
            body = item.get("reviewText") or item.get("comment") or item.get("body") or ""
            if not body:
                continue
            reviews.append({
                "external_review_id": str(item.get("reviewId") or item.get("id") or f"fk-{hash(body) % 10**10}"),
                "reviewer_name": item.get("reviewerName") or item.get("customerName") or "Flipkart Customer",
                "rating": max(1, min(5, int(item.get("rating") or item.get("stars") or 3))),
                "title": item.get("title"),
                "body": body,
                "product_name": item.get("productTitle") or item.get("product_name"),
                "review_date": item.get("reviewDate") or datetime.now(timezone.utc).isoformat(),
            })
        return reviews

    def _demo_reviews(self) -> list[dict]:
        return [
            {
                "external_review_id": "fk-demo-001",
                "reviewer_name": "Amit V.",
                "rating": 5,
                "title": "Value for money",
                "body": "Good product quality and fast Flipkart delivery. Packaging was neat.",
                "product_name": "Demo Product",
                "review_date": datetime.now(timezone.utc).isoformat(),
            },
            {
                "external_review_id": "fk-demo-002",
                "reviewer_name": "Sneha R.",
                "rating": 2,
                "title": "Not as expected",
                "body": "Product color different from listing. Would like a replacement.",
                "product_name": "Demo Product",
                "review_date": datetime.now(timezone.utc).isoformat(),
            },
        ]
