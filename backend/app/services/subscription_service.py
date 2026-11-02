import math
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.organization import Subscription, Organization

TRIAL_DAYS = 5


def utcnow():
    return datetime.now(timezone.utc)


async def get_org_subscription(db: AsyncSession, org_id: int) -> Subscription | None:
    result = await db.execute(select(Subscription).where(Subscription.org_id == org_id))
    return result.scalar_one_or_none()


async def ensure_subscription(db: AsyncSession, org_id: int) -> Subscription:
    sub = await get_org_subscription(db, org_id)
    if sub:
        if sub.trial_ends_at is None:
            org_result = await db.execute(select(Organization).where(Organization.id == org_id))
            org = org_result.scalar_one_or_none()
            base = org.created_at if org else utcnow()
            sub.trial_ends_at = base + timedelta(days=TRIAL_DAYS)
            if not sub.paid_at:
                sub.status = "trialing" if utcnow() < sub.trial_ends_at else "expired"
        return sub
    sub = Subscription(
        org_id=org_id,
        plan="trial",
        status="trialing",
        billing_cycle="monthly",
        trial_ends_at=utcnow() + timedelta(days=TRIAL_DAYS),
    )
    db.add(sub)
    await db.flush()
    return sub


def has_feature_access(sub: Subscription, now: datetime | None = None) -> bool:
    now = now or utcnow()
    if sub.paid_at is not None:
        return True
    if sub.trial_ends_at and now < sub.trial_ends_at:
        return True
    return False


def subscription_status(sub: Subscription, now: datetime | None = None) -> dict:
    now = now or utcnow()
    paid = sub.paid_at is not None
    trial_end = sub.trial_ends_at
    period_end = sub.current_period_end

    if paid:
        access = "active"
        if period_end and now < period_end:
            days_left = max(1, math.ceil((period_end - now).total_seconds() / 86400))
        else:
            days_left = None
    elif trial_end and now < trial_end:
        access = "trialing"
        days_left = max(1, math.ceil((trial_end - now).total_seconds() / 86400))
    else:
        access = "expired"
        days_left = 0

    return {
        "access": access,
        "plan": sub.plan,
        "status": sub.status,
        "billing_cycle": sub.billing_cycle,
        "trial_ends_at": trial_end.isoformat() if trial_end else None,
        "period_ends_at": period_end.isoformat() if period_end else None,
        "paid_at": sub.paid_at.isoformat() if sub.paid_at else None,
        "days_left": days_left,
        "has_access": has_feature_access(sub, now),
        "payer_type": sub.payer_type,
        "paid_by_user_id": sub.paid_by_user_id,
    }


def require_access(sub: Subscription) -> None:
    if not has_feature_access(sub):
        raise HTTPException(
            status_code=402,
            detail={
                "code": "trial_expired",
                "message": f"Your {TRIAL_DAYS}-day trial has ended. Subscribe to continue using ReviewFlow.",
                "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                "billing_url": "/settings/billing",
            },
        )


async def activate_subscription(
    db: AsyncSession,
    org_id: int,
    user_id: int,
    plan: str,
    billing_cycle: str,
    payer_type: str,
    razorpay_order_id: str | None = None,
    razorpay_payment_id: str | None = None,
) -> Subscription:
    if payer_type not in ("org", "user"):
        raise HTTPException(status_code=400, detail="payer_type must be 'org' or 'user'")
    if plan not in ("solo", "growth", "professional", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid plan")
    if billing_cycle not in ("monthly", "biannual", "annual"):
        raise HTTPException(status_code=400, detail="Invalid billing cycle")

    sub = await ensure_subscription(db, org_id)
    now = utcnow()
    period_days = {"monthly": 30, "biannual": 180, "annual": 365}[billing_cycle]

    sub.plan = plan
    sub.billing_cycle = billing_cycle
    sub.status = "active"
    sub.paid_at = now
    sub.payer_type = payer_type
    sub.paid_by_user_id = user_id
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=period_days)
    if razorpay_order_id:
        sub.razorpay_order_id = razorpay_order_id
    if razorpay_payment_id:
        sub.razorpay_payment_id = razorpay_payment_id
    await db.flush()
    return sub
