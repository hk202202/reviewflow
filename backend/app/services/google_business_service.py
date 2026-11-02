"""Google Business Profile OAuth + review sync."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/business.manage"]
ACCOUNTS_API = "https://mybusinessaccountmanagement.googleapis.com/v1"
LOCATIONS_API = "https://mybusinessbusinessinformation.googleapis.com/v1"
REVIEWS_API = "https://mybusiness.googleapis.com/v4"

QUOTA_ERROR = (
    "Google API rate limit hit (429). Wait 1–2 minutes, then click "
    "'Finish Setup' on the Platforms page — no need to sign in again. "
    "If this keeps happening, request a quota increase in Google Cloud Console "
    "→ IAM & Admin → Quotas → filter 'My Business Account Management API'."
)


async def _google_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict,
    max_retries: int = 3,
    **kwargs,
) -> httpx.Response:
    """Retry Google API calls on 429 with backoff."""
    last: httpx.Response | None = None
    for attempt in range(max_retries + 1):
        last = await client.request(method, url, headers=headers, **kwargs)
        if last.status_code != 429:
            return last
        if attempt < max_retries:
            wait = 45 * (attempt + 1)
            logger.warning("Google API 429 on %s — retry %s/%s in %ss", url, attempt + 1, max_retries, wait)
            await asyncio.sleep(wait)
    return last  # type: ignore[return-value]


def _raise_google_error(resp: httpx.Response, context: str) -> None:
    if resp.status_code == 429:
        raise HTTPException(status_code=429, detail=QUOTA_ERROR)
    logger.error("Google %s failed (%s): %s", context, resp.status_code, resp.text)
    raise HTTPException(
        status_code=400,
        detail=f"{context}: {resp.text[:250]}",
    )


def is_google_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def build_auth_url(state: str) -> str:
    if not is_google_configured():
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code != 200:
            logger.error("Google token exchange failed: %s", resp.text)
            raise HTTPException(status_code=400, detail="Failed to exchange Google authorization code")
        return resp.json()


async def refresh_access_token(creds: dict) -> dict:
    refresh_token = creds.get("refresh_token")
    if not refresh_token:
        return creds

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if resp.status_code != 200:
            logger.error("Google token refresh failed: %s", resp.text)
            return creds

        data = resp.json()
        creds["access_token"] = data["access_token"]
        creds["token_expiry"] = (
            datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
        ).isoformat()
        if data.get("refresh_token"):
            creds["refresh_token"] = data["refresh_token"]
    return creds


async def ensure_fresh_token(creds: dict) -> dict:
    expiry_str = creds.get("token_expiry")
    if expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
            if expiry > datetime.now(timezone.utc) + timedelta(minutes=2):
                return creds
        except ValueError:
            pass
    return await refresh_access_token(creds)


async def _auth_headers(creds: dict) -> dict:
    creds = await ensure_fresh_token(creds)
    token = creds.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail="Google access token missing — reconnect Google Business")
    return {"Authorization": f"Bearer {token}"}, creds


async def discover_account_and_location(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=60) as client:
        acct_resp = await _google_request(client, "GET", f"{ACCOUNTS_API}/accounts", headers=headers)
        if acct_resp.status_code != 200:
            _raise_google_error(acct_resp, "Could not list Google Business accounts")

        accounts = acct_resp.json().get("accounts", [])
        if not accounts:
            raise HTTPException(status_code=400, detail="No Google Business accounts found for this Google account")

        account_name = accounts[0]["name"]
        loc_resp = await _google_request(
            client,
            "GET",
            f"{LOCATIONS_API}/{account_name}/locations",
            headers=headers,
            params={"readMask": "name,title,storefrontAddress"},
        )
        if loc_resp.status_code != 200:
            _raise_google_error(loc_resp, "Could not list business locations")

        locations = loc_resp.json().get("locations", [])
        if not locations:
            raise HTTPException(
                status_code=400,
                detail="No business locations found — verify your Google Business Profile is set up",
            )

        location = locations[0]
        return {
            "account_name": account_name,
            "location_name": location["name"],
            "location_title": location.get("title", "Google Business"),
        }


def credentials_needs_setup(creds: dict) -> bool:
    return bool(creds.get("access_token") or creds.get("refresh_token")) and not creds.get("location_name")


async def complete_location_setup(creds: dict) -> dict:
    """Discover account/location using stored tokens (after quota retry)."""
    creds = await ensure_fresh_token(creds)
    token = creds.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail="Google tokens missing — reconnect Google Business")
    location_info = await discover_account_and_location(token)
    creds.update(location_info)
    return creds


def _star_to_int(star: str) -> int:
    mapping = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
    return mapping.get(star or "", 3)


class GoogleBusinessService:
    def __init__(self, credentials: dict):
        self.credentials = credentials

    async def fetch_reviews(self) -> tuple[list[dict], dict]:
        """Returns (reviews, updated_credentials)."""
        headers, self.credentials = await _auth_headers(self.credentials)
        location_name = self.credentials.get("location_name")
        if not location_name:
            raise HTTPException(status_code=400, detail="Google location not configured — reconnect Google Business")

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await _google_request(
                client,
                "GET",
                f"{REVIEWS_API}/{location_name}/reviews",
                headers=headers,
            )
            if resp.status_code != 200:
                _raise_google_error(resp, f"Google reviews API error ({resp.status_code})")

            data = resp.json()
            reviews = []
            for item in data.get("reviews", []):
                reviewer = item.get("reviewer", {}) or {}
                reviews.append({
                    "external_review_id": item.get("reviewId") or item.get("name", ""),
                    "reviewer_name": reviewer.get("displayName", "Anonymous"),
                    "rating": _star_to_int(item.get("starRating", "THREE")),
                    "title": None,
                    "body": item.get("comment") or "(No comment)",
                    "review_date": item.get("createTime") or datetime.now(timezone.utc).isoformat(),
                })
            return reviews, self.credentials

    async def post_reply(self, review_id: str, reply_text: str) -> bool:
        headers, self.credentials = await _auth_headers(self.credentials)
        location_name = self.credentials.get("location_name", "")
        review_name = f"{location_name}/reviews/{review_id}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{REVIEWS_API}/{review_name}/reply",
                headers={**headers, "Content-Type": "application/json"},
                json={"comment": reply_text},
            )
            return resp.status_code in (200, 201)


def build_credentials_from_token_response(token_data: dict, location_info: dict | None = None) -> dict:
    expiry = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
    creds = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "token_expiry": expiry.isoformat(),
    }
    if location_info:
        creds.update({
            "account_name": location_info["account_name"],
            "location_name": location_info["location_name"],
            "location_title": location_info["location_title"],
        })
    return creds
