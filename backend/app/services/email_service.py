import json
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional
from app.core.config import get_settings

settings = get_settings()


async def send_email(to: str, subject: str, html: str) -> bool:
    if not settings.RESEND_API_KEY:
        print(f"[EMAIL] To: {to} | Subject: {subject}")
        return True
    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


async def send_invite_email(to: str, org_name: str, invite_url: str) -> bool:
    html = f"""
    <h2>You've been invited to join {org_name} on ReviewFlow</h2>
    <p>Click the link below to accept your invitation:</p>
    <a href="{invite_url}">Accept Invitation</a>
    <p>This link expires in 7 days.</p>
    """
    return await send_email(to, f"Join {org_name} on ReviewFlow", html)


async def send_new_review_alert(to: str, reviewer: str, rating: int, body: str, reply_url: str) -> bool:
    stars = "⭐" * rating
    html = f"""
    <h2>New {rating}-Star Review Received {stars}</h2>
    <p><strong>From:</strong> {reviewer}</p>
    <p><strong>Review:</strong> {body[:500]}</p>
    <a href="{reply_url}">Reply Now</a>
    """
    return await send_email(to, f"New {rating}-star review from {reviewer}", html)


async def send_sync_failure_alert(to: str, platform: str, reconnect_url: str) -> bool:
    html = f"""
    <h2>Platform Sync Failed</h2>
    <p>We couldn't sync reviews from <strong>{platform}</strong> after 3 attempts.</p>
    <a href="{reconnect_url}">Reconnect Platform</a>
    """
    return await send_email(to, f"ReviewFlow: {platform} sync failed", html)


async def send_quota_warning(to: str, used: int, limit: int, upgrade_url: str) -> bool:
    pct = int(used / limit * 100) if limit else 100
    html = f"""
    <h2>AI Quota Warning ({pct}% used)</h2>
    <p>You've used {used} of {limit} AI replies this month.</p>
    <a href="{upgrade_url}">Upgrade Plan</a>
    """
    return await send_email(to, f"ReviewFlow: AI quota at {pct}%", html)


async def send_review_request_email(to: str, name: str, product: str, review_url: str) -> bool:
    html = f"""
    <h2>Hi {name or 'there'},</h2>
    <p>We hope you're enjoying your recent purchase of <strong>{product}</strong>!</p>
    <p>Would you mind sharing your experience? It helps other buyers make informed decisions.</p>
    <a href="{review_url}">Leave a Review</a>
    <p><small><a href="#">Unsubscribe</a></small></p>
    """
    return await send_email(to, f"How was your {product}?", html)
