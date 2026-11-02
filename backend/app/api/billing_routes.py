from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_current_org_member
from app.services.subscription_service import ensure_subscription, subscription_status, activate_subscription
from app.services.plan_pricing import PLAN_PRICES, plan_amount_inr
from app.services.plan_limits import PUBLIC_PLANS, PLAN_LIMITS
from app.services.razorpay_service import is_razorpay_configured, create_order, verify_and_extract
from app.services.notification_service import log_audit

router = APIRouter(prefix="/billing", tags=["billing"])
settings = get_settings()


class ActivateRequest(BaseModel):
    plan: str
    billing_cycle: str = "monthly"
    payer_type: str  # org | user


class CreateOrderRequest(BaseModel):
    plan: str
    billing_cycle: str = "monthly"
    payer_type: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def _check_payer_role(payer_type: str, role: str) -> None:
    if payer_type == "org" and role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only org owners/admins can pay with the organization account")


@router.get("/plans")
async def list_plans():
    plans = []
    for p in PUBLIC_PLANS:
        pid = p["id"]
        plans.append({
            **p,
            "limits": PLAN_LIMITS.get(pid, {}),
            "prices": PLAN_PRICES.get(pid, {}),
        })
    return {"plans": plans}


@router.get("/config")
async def billing_config():
    return {
        "razorpay_enabled": is_razorpay_configured(),
        "razorpay_key_id": settings.RAZORPAY_KEY_ID if is_razorpay_configured() else None,
        "trial_days": 5,
        "plans": PLAN_PRICES,
        "plan_catalog": PUBLIC_PLANS,
    }


@router.get("/status")
async def billing_status(user_org=Depends(get_current_org_member), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    sub = await ensure_subscription(db, member.org_id)
    return subscription_status(sub)


@router.post("/create-order")
async def create_payment_order(
    data: CreateOrderRequest,
    user_org=Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db),
):
    user, member = user_org
    _check_payer_role(data.payer_type, member.role)
    if not is_razorpay_configured():
        raise HTTPException(status_code=503, detail="Razorpay is not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")

    order = create_order(
        member.org_id, user.id, user.email, user.full_name,
        data.plan, data.billing_cycle, data.payer_type,
    )
    return order


@router.post("/verify-payment")
async def verify_payment(
    data: VerifyPaymentRequest,
    user_org=Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db),
):
    user, member = user_org
    payment = verify_and_extract(
        data.razorpay_order_id, data.razorpay_payment_id, data.razorpay_signature,
    )
    if payment["org_id"] != member.org_id:
        raise HTTPException(status_code=403, detail="Payment does not belong to this organization")
    if payment["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Payment user mismatch")

    sub = await activate_subscription(
        db, member.org_id, user.id,
        payment["plan"], payment["billing_cycle"], payment["payer_type"],
        razorpay_order_id=payment["razorpay_order_id"],
        razorpay_payment_id=payment["razorpay_payment_id"],
    )
    await log_audit(
        db, member.org_id, user.id, "subscription_activated", "subscription", sub.id,
        {"plan": payment["plan"], "payer_type": payment["payer_type"], "razorpay_payment_id": payment["razorpay_payment_id"]},
    )
    return {"message": "Payment verified and subscription activated", "subscription": subscription_status(sub)}


@router.post("/activate")
async def activate_billing_demo(
    data: ActivateRequest,
    user_org=Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db),
):
    """Demo activation when Razorpay keys are not configured (local dev only)."""
    if is_razorpay_configured():
        raise HTTPException(status_code=400, detail="Use Razorpay checkout. Demo activation is disabled when Razorpay is configured.")

    user, member = user_org
    _check_payer_role(data.payer_type, member.role)

    sub = await activate_subscription(
        db, member.org_id, user.id, data.plan, data.billing_cycle, data.payer_type,
    )
    await log_audit(
        db, member.org_id, user.id, "subscription_activated", "subscription", sub.id,
        {"plan": data.plan, "payer_type": data.payer_type, "demo": True},
    )
    return {"message": "Subscription activated (demo mode)", "subscription": subscription_status(sub)}


@router.get("/quote")
async def billing_quote(plan: str, billing_cycle: str = "monthly"):
    try:
        amount = plan_amount_inr(plan, billing_cycle)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"plan": plan, "billing_cycle": billing_cycle, "amount_inr": amount, "currency": "INR"}
