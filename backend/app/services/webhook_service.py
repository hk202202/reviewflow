import json
import hashlib
import hmac
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.misc import Webhook


async def dispatch_webhook(db: AsyncSession, org_id: int, event: str, data: dict):
    result = await db.execute(
        select(Webhook).where(
            Webhook.org_id == org_id,
            Webhook.is_active == True,
        )
    )
    webhooks = result.scalars().all()

    for wh in webhooks:
        if event not in (wh.events or []):
            continue
        payload = {"event": event, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}
        signature = hmac.new(wh.secret.encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    wh.url,
                    json=payload,
                    headers={"X-ReviewFlow-Signature": signature, "Content-Type": "application/json"},
                )
                if resp.status_code >= 400:
                    wh.failure_count += 1
                else:
                    wh.last_triggered_at = datetime.now(timezone.utc)
                    wh.failure_count = 0
        except Exception:
            wh.failure_count += 1
