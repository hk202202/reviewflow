from app.tasks.celery_app import celery_app
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.platform import PlatformConnection
from app.models.review import Review
from app.models.organization import Organization
from app.services.ai_service import analyze_sentiment
from app.services.flag_service import check_review_flags
from app.services.marketplace_sync import fetch_reviews_via_api
from datetime import datetime, timezone
import json

settings = get_settings()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_platform(self, connection_id: int):
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as db:
        conn = db.get(PlatformConnection, connection_id)
        if not conn or not conn.is_active:
            return {"status": "skipped"}

        try:
            creds = json.loads(conn.credentials_encrypted or "{}")
            import asyncio
            reviews_data, _, updated_creds = asyncio.get_event_loop().run_until_complete(
                fetch_reviews_via_api(conn.platform, creds)
            )
            if updated_creds:
                conn.credentials_encrypted = json.dumps(updated_creds)

            imported = 0
            for rd in reviews_data:
                existing = db.execute(select(Review).where(
                    Review.org_id == conn.org_id,
                    Review.external_review_id == rd.get("external_review_id"),
                )).scalar_one_or_none()
                if existing:
                    continue
                sentiment = analyze_sentiment(rd["body"], rd["rating"])
                is_flagged, flag_reason = check_review_flags(rd["body"], rd["rating"])
                review = Review(
                    org_id=conn.org_id,
                    platform_connection_id=conn.id,
                    external_review_id=rd.get("external_review_id"),
                    reviewer_name=rd["reviewer_name"],
                    rating=rd["rating"],
                    title=rd.get("title"),
                    body=rd["body"],
                    sentiment=sentiment,
                    platform=conn.platform,
                    is_flagged=is_flagged,
                    flag_reason=flag_reason,
                    reply_status="escalated" if is_flagged else "pending",
                )
                db.add(review)
                imported += 1

            conn.last_synced_at = datetime.now(timezone.utc)
            conn.sync_failure_count = 0
            db.commit()
            return {"status": "success", "imported": imported}
        except Exception as exc:
            conn.sync_failure_count += 1
            db.commit()
            if conn.sync_failure_count >= 3:
                pass  # notify_sync_failure would be called here
            raise self.retry(exc=exc)


@celery_app.task
def sync_all_platforms():
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as db:
        connections = db.execute(select(PlatformConnection).where(PlatformConnection.is_active == True)).scalars().all()
        for conn in connections:
            sync_platform.delay(conn.id)
    return {"synced": len(connections)}
