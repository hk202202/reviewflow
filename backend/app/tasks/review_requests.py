from app.tasks.celery_app import celery_app
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.misc import ReviewRequest
from datetime import datetime, timezone
import asyncio

settings = get_settings()


@celery_app.task
def send_pending_requests():
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as db:
        pending = db.execute(
            select(ReviewRequest).where(
                ReviewRequest.status == "scheduled",
                ReviewRequest.send_after <= datetime.now(timezone.utc),
            )
        ).scalars().all()

        sent = 0
        for req in pending:
            try:
                from app.services.email_service import send_review_request_email
                asyncio.get_event_loop().run_until_complete(
                    send_review_request_email(req.recipient_email, req.recipient_name or "", "your product", "#")
                )
                req.status = "sent"
                req.sent_at = datetime.now(timezone.utc)
                sent += 1
            except Exception:
                pass
        db.commit()
    return {"sent": sent}
