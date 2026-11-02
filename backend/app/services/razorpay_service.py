import hmac
import hashlib
import time
import httpx
from fastapi import HTTPException

from app.core.config import get_settings
from app.services.plan_pricing import plan_amount_inr

settings = get_settings()
RAZORPAY_API = "https://api.razorpay.com/v1"


def is_razorpay_configured() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def _auth():
    return (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)


def create_order(
    org_id: int,
    user_id: int,
    user_email: str,
    user_name: str,
    plan: str,
    billing_cycle: str,
    payer_type: str,
) -> dict:
    if not is_razorpay_configured():
        raise HTTPException(status_code=503, detail="Razorpay is not configured")

    amount_inr = plan_amount_inr(plan, billing_cycle)
    amount_paise = amount_inr * 100
    receipt = f"rf_{org_id}_{int(time.time())}"

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{RAZORPAY_API}/orders",
            auth=_auth(),
            json={
                "amount": amount_paise,
                "currency": "INR",
                "receipt": receipt,
                "notes": {
                    "org_id": str(org_id),
                    "user_id": str(user_id),
                    "plan": plan,
                    "billing_cycle": billing_cycle,
                    "payer_type": payer_type,
                },
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Razorpay order failed: {resp.text}")
        order = resp.json()

    return {
        "order_id": order["id"],
        "amount": amount_paise,
        "amount_inr": amount_inr,
        "currency": "INR",
        "key_id": settings.RAZORPAY_KEY_ID,
        "prefill": {"email": user_email, "name": user_name},
        "description": f"ReviewFlow {plan.title()} ({billing_cycle})",
    }


def _verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    body = f"{order_id}|{payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_and_extract(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> dict:
    if not is_razorpay_configured():
        raise HTTPException(status_code=503, detail="Razorpay is not configured")

    if not _verify_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{RAZORPAY_API}/orders/{razorpay_order_id}", auth=_auth())
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Could not fetch order from Razorpay")
        order = resp.json()

    notes = order.get("notes") or {}
    return {
        "org_id": int(notes.get("org_id", 0)),
        "user_id": int(notes.get("user_id", 0)),
        "plan": notes.get("plan", ""),
        "billing_cycle": notes.get("billing_cycle", "monthly"),
        "payer_type": notes.get("payer_type", "user"),
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
    }
