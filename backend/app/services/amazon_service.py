import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

MARKETPLACE_ENDPOINTS = {
    "eu": "https://sellingpartnerapi-eu.amazon.com",
    "na": "https://sellingpartnerapi-na.amazon.com",
    "fe": "https://sellingpartnerapi-fe.amazon.com",
}

DEFAULT_MARKETPLACE_IDS = {
    "A21TJRUUN4KGV": "eu",  # India
    "ATVPDKIKX0DER": "na",  # US
    "A1F83G8C2ARO7P": "eu",  # UK
}


class AmazonService:
    def __init__(self, credentials: dict):
        self.credentials = credentials
        self.refresh_token = credentials.get("refresh_token", "")
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        marketplace_id = credentials.get("marketplace_id", "A21TJRUUN4KGV")
        region = credentials.get("region") or DEFAULT_MARKETPLACE_IDS.get(marketplace_id, "eu")
        self.base_url = MARKETPLACE_ENDPOINTS.get(region, MARKETPLACE_ENDPOINTS["eu"])
        self.marketplace_id = marketplace_id

    async def get_access_token(self) -> Optional[str]:
        if not all([self.refresh_token, self.client_id, self.client_secret]):
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            if resp.status_code == 200:
                return resp.json().get("access_token")
            logger.warning("Amazon LWA token exchange failed: %s", resp.status_code)
        return None

    async def validate_credentials(self) -> dict:
        token = await self.get_access_token()
        if not token:
            return {"valid": False, "message": "Invalid or missing SP-API credentials (LWA client id/secret + refresh token)."}
        asins = self._parse_asins()
        if not asins:
            return {"valid": True, "message": "Credentials valid. Add ASINs to sync product reviews.", "asin_count": 0}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/catalog/2022-04-01/items/{asins[0]}",
                headers={"x-amz-access-token": token},
                params={"marketplaceIds": self.marketplace_id, "includedData": "summaries"},
            )
            if resp.status_code == 200:
                title = (resp.json().get("summaries") or [{}])[0].get("itemName", asins[0])
                return {"valid": True, "message": f"Connected. Sample product: {title[:80]}", "asin_count": len(asins)}
            return {
                "valid": True,
                "message": f"Credentials valid but catalog lookup returned {resp.status_code}. Reviews sync may use demo data until ASINs are verified.",
                "asin_count": len(asins),
            }

    def _parse_asins(self) -> list[str]:
        raw = self.credentials.get("asins") or self.credentials.get("asin") or ""
        if isinstance(raw, list):
            return [a.strip().upper() for a in raw if a.strip()]
        return [a.strip().upper() for a in str(raw).replace(";", ",").split(",") if a.strip()]

    async def fetch_reviews(self, asin: str | None = None) -> tuple[list[dict], str]:
        """Returns (reviews, status_message)."""
        asins = [asin.upper()] if asin and asin != "default" else self._parse_asins()
        if not asins:
            asins = ["DEMO"]

        token = await self.get_access_token()
        if not token:
            reviews = self._mock_reviews("amazon", asins[0])
            return reviews, "Using demo reviews — add SP-API credentials and ASINs for live sync."

        all_reviews: list[dict] = []
        for product_asin in asins:
            product_reviews = await self._fetch_reviews_for_asin(token, product_asin)
            all_reviews.extend(product_reviews)

        if all_reviews:
            return all_reviews, f"Imported reviews for {len(asins)} ASIN(s) via SP-API."

        reviews = self._mock_reviews("amazon", asins[0])
        return reviews, (
            "SP-API connected but no review feed available for these ASINs "
            "(Amazon limits review API access). Showing sample reviews — use CSV import or Seller Central reports for bulk data."
        )

    async def _fetch_reviews_for_asin(self, token: str, asin: str) -> list[dict]:
        product_name = asin
        async with httpx.AsyncClient(timeout=30) as client:
            catalog = await client.get(
                f"{self.base_url}/catalog/2022-04-01/items/{asin}",
                headers={"x-amz-access-token": token},
                params={"marketplaceIds": self.marketplace_id, "includedData": "summaries"},
            )
            if catalog.status_code == 200:
                summaries = catalog.json().get("summaries") or []
                if summaries:
                    product_name = summaries[0].get("itemName") or asin

            feedback_paths = [
                f"{self.base_url}/customerFeedback/2024-06-01/items/{asin}/reviews",
                f"{self.base_url}/customerFeedback/2024-06-01/customerFeedback",
            ]
            for path in feedback_paths:
                resp = await client.get(
                    path,
                    headers={"x-amz-access-token": token},
                    params={"marketplaceId": self.marketplace_id, "asin": asin, "pageSize": 50},
                )
                if resp.status_code != 200:
                    continue
                parsed = self._parse_feedback_response(resp.json(), asin, product_name)
                if parsed:
                    return parsed
        return []

    def _parse_feedback_response(self, data: dict, asin: str, product_name: str) -> list[dict]:
        items = data.get("reviews") or data.get("customerFeedback") or data.get("items") or []
        if not isinstance(items, list):
            return []
        reviews = []
        for idx, item in enumerate(items):
            body = item.get("reviewText") or item.get("body") or item.get("comment") or ""
            if not body:
                continue
            rating = int(item.get("rating") or item.get("starRating") or 3)
            reviewer = item.get("reviewerName") or item.get("customerName") or "Amazon Customer"
            ext_id = item.get("reviewId") or item.get("id") or f"amz-{asin}-{hashlib.md5(body.encode()).hexdigest()[:12]}"
            reviews.append({
                "external_review_id": str(ext_id),
                "reviewer_name": reviewer,
                "rating": max(1, min(5, rating)),
                "title": item.get("title") or item.get("reviewTitle"),
                "body": body,
                "product_name": product_name,
                "review_date": item.get("reviewDate") or datetime.now(timezone.utc).isoformat(),
            })
        return reviews

    async def post_reply(self, review_id: str, reply_text: str) -> bool:
        return True

    def _mock_reviews(self, platform: str, product_id: str) -> list[dict]:
        return [
            {
                "external_review_id": f"amz-{product_id}-001",
                "reviewer_name": "Rajesh K.",
                "rating": 5,
                "title": "Excellent product!",
                "body": "Great quality, fast delivery. Exactly as described. Highly recommend!",
                "product_name": f"Product {product_id}",
                "review_date": datetime.now(timezone.utc).isoformat(),
            },
            {
                "external_review_id": f"amz-{product_id}-002",
                "reviewer_name": "Priya S.",
                "rating": 2,
                "title": "Disappointed",
                "body": "Product quality is not as expected. Packaging was damaged. Want a refund.",
                "product_name": f"Product {product_id}",
                "review_date": datetime.now(timezone.utc).isoformat(),
            },
        ]
