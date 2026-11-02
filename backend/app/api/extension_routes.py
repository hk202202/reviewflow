import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_subscription
from app.models.platform import PlatformConnection
from app.models.review import Review
from app.services.ai_service import analyze_sentiment
from app.services.flag_service import check_review_flags
from app.services.notification_service import log_audit, notify_new_review
from app.services.webhook_service import dispatch_webhook

router = APIRouter(prefix="/extension", tags=["extension"])

from app.services.marketplace_sync import EXTENSION_COMPATIBLE_PLATFORMS


class ExtensionReviewItem(BaseModel):
    external_review_id: str | None = None
    reviewer_name: str = "Anonymous"
    rating: int = Field(ge=1, le=5, default=3)
    title: str | None = None
    body: str
    product_name: str | None = None
    review_date: str | None = None


class ExtensionImportRequest(BaseModel):
    platform: str
    platform_connection_id: int
    reviews: list[ExtensionReviewItem]


def _stable_review_id(platform: str, body: str, reviewer: str, rating: int) -> str:
    digest = hashlib.md5(f"{platform}:{reviewer}:{rating}:{body[:200]}".encode()).hexdigest()[:16]
    return f"{platform}-{digest}"


@router.get("/info")
async def extension_info():
    return {
        "optional": True,
        "description": "Chrome extension is an optional add-on for all platforms — import reviews and apply AI replies on any seller portal when API posting is limited.",
        "supported_platforms": sorted(EXTENSION_COMPATIBLE_PLATFORMS),
        "features": ["import_reviews", "ai_reply_assist", "works_alongside_api_sync"],
    }


@router.get("/connections")
async def list_extension_connections(
    user_org=Depends(require_active_subscription),
    db: AsyncSession = Depends(get_db),
):
    _, member = user_org
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.org_id == member.org_id,
            PlatformConnection.platform.in_(EXTENSION_COMPATIBLE_PLATFORMS),
            PlatformConnection.is_active == True,
        )
    )
    connections = result.scalars().all()
    return [
        {"id": c.id, "platform": c.platform, "display_name": c.display_name}
        for c in connections
    ]


@router.post("/import-reviews")
async def import_extension_reviews(
    data: ExtensionImportRequest,
    user_org=Depends(require_active_subscription),
    db: AsyncSession = Depends(get_db),
):
    user, member = user_org
    if data.platform not in EXTENSION_COMPATIBLE_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Platform must be one of: {', '.join(sorted(EXTENSION_COMPATIBLE_PLATFORMS))}",
        )

    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.id == data.platform_connection_id,
            PlatformConnection.org_id == member.org_id,
            PlatformConnection.platform == data.platform,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Platform connection not found")

    if not data.reviews:
        raise HTTPException(status_code=400, detail="No reviews to import")

    imported = 0
    skipped = 0
    for item in data.reviews:
        ext_id = item.external_review_id or _stable_review_id(
            data.platform, item.body, item.reviewer_name, item.rating
        )
        existing = await db.execute(
            select(Review).where(Review.org_id == member.org_id, Review.external_review_id == ext_id)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        sentiment = analyze_sentiment(item.body, item.rating)
        is_flagged, flag_reason = check_review_flags(item.body, item.rating)
        review_date = None
        if item.review_date:
            try:
                review_date = datetime.fromisoformat(item.review_date.replace("Z", "+00:00"))
            except ValueError:
                review_date = None

        review = Review(
            org_id=member.org_id,
            platform_connection_id=conn.id,
            external_review_id=ext_id,
            reviewer_name=item.reviewer_name,
            rating=item.rating,
            title=item.title,
            body=item.body,
            review_date=review_date,
            sentiment=sentiment,
            platform=data.platform,
            product_name=item.product_name,
            is_flagged=is_flagged,
            flag_reason=flag_reason,
            reply_status="escalated" if is_flagged else "pending",
        )
        db.add(review)
        imported += 1
        if item.rating <= 2:
            await notify_new_review(db, member.org_id, review, user.email)

    conn.last_synced_at = datetime.now(timezone.utc)
    conn.sync_failure_count = 0
    creds = json.loads(conn.credentials_encrypted or "{}")
    creds["last_extension_import"] = datetime.now(timezone.utc).isoformat()
    creds["last_extension_import_count"] = imported
    conn.credentials_encrypted = json.dumps(creds)

    await log_audit(db, member.org_id, user.id, "extension_import", "platform", conn.id, {"imported": imported})
    await dispatch_webhook(db, member.org_id, "review.created", {"count": imported, "platform": data.platform, "source": "extension"})

    return {"imported": imported, "skipped": skipped, "total_received": len(data.reviews)}
