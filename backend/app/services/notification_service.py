from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.misc import Notification, AuditLog
from app.services.email_service import (
    send_new_review_alert, send_sync_failure_alert, send_quota_warning,
)
from app.core.config import get_settings

settings = get_settings()


async def create_notification(
    db: AsyncSession,
    org_id: int,
    type: str,
    title: str,
    body: str,
    user_id: int | None = None,
    action_url: str | None = None,
    send_email_to: str | None = None,
    email_fn=None,
) -> Notification:
    notif = Notification(
        org_id=org_id,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        action_url=action_url,
    )
    db.add(notif)

    if send_email_to and email_fn:
        sent = await email_fn(send_email_to)
        if sent:
            notif.email_sent_at = datetime.now(timezone.utc)

    return notif


async def notify_new_review(db: AsyncSession, org_id: int, review, admin_email: str):
    reply_url = f"{settings.FRONTEND_URL}/reviews/{review.id}"
    await create_notification(
        db, org_id, "new_review",
        f"New {review.rating}-star review from {review.reviewer_name}",
        review.body[:200],
        action_url=reply_url,
        send_email_to=admin_email if review.rating <= 2 else None,
        email_fn=lambda email: send_new_review_alert(
            email, review.reviewer_name, review.rating, review.body, reply_url
        ) if review.rating <= 2 else None,
    )


async def notify_sync_failure(db: AsyncSession, org_id: int, platform: str, admin_email: str):
    reconnect_url = f"{settings.FRONTEND_URL}/platforms"
    await create_notification(
        db, org_id, "sync_failed",
        f"Sync failed for {platform}",
        f"Could not sync reviews from {platform} after 3 attempts.",
        action_url=reconnect_url,
        send_email_to=admin_email,
        email_fn=lambda email: send_sync_failure_alert(email, platform, reconnect_url),
    )


async def log_audit(
    db: AsyncSession,
    org_id: int,
    actor_user_id: int,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    payload: dict | None = None,
    ip_address: str | None = None,
):
    entry = AuditLog(
        org_id=org_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
