import json
from datetime import timedelta
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, decode_token, require_active_subscription
from app.models.platform import PlatformConnection
from app.services.google_business_service import (
    is_google_configured,
    build_auth_url,
    exchange_code,
    discover_account_and_location,
    build_credentials_from_token_response,
    complete_location_setup,
    credentials_needs_setup,
    QUOTA_ERROR,
)
from app.services.notification_service import log_audit

router = APIRouter(prefix="/platforms/google", tags=["google"])
settings = get_settings()


@router.get("/config")
async def google_config():
    return {
        "configured": is_google_configured(),
        "redirect_uri": settings.GOOGLE_REDIRECT_URI if is_google_configured() else None,
    }


@router.get("/status")
async def google_status(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.org_id == member.org_id,
            PlatformConnection.platform == "google_business",
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        return {"connected": False, "needs_setup": False}
    creds = json.loads(conn.credentials_encrypted or "{}")
    return {
        "connected": True,
        "needs_setup": credentials_needs_setup(creds),
        "display_name": conn.display_name,
        "connection_id": conn.id,
    }


@router.get("/auth-url")
async def google_auth_url(user_org=Depends(require_active_subscription)):
    user, member = user_org
    state = create_access_token(
        {"sub": str(user.id), "org_id": member.org_id, "purpose": "google_oauth"},
        expires_delta=timedelta(minutes=15),
    )
    return {"auth_url": build_auth_url(state)}


@router.post("/finish-setup")
async def google_finish_setup(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.org_id == member.org_id,
            PlatformConnection.platform == "google_business",
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No Google Business connection found — connect Google first")

    creds = json.loads(conn.credentials_encrypted or "{}")
    if not credentials_needs_setup(creds) and creds.get("location_name"):
        return {"message": "Already configured", "display_name": conn.display_name}

    try:
        creds = await complete_location_setup(creds)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    conn.credentials_encrypted = json.dumps(creds)
    conn.display_name = creds.get("location_title", conn.display_name)
    conn.is_active = True
    conn.sync_failure_count = 0
    await log_audit(db, member.org_id, user.id, "platform_setup_completed", "platform", conn.id)
    await db.commit()
    return {"message": "Google Business location linked", "display_name": conn.display_name}


async def _save_google_connection(db, org_id, user_id, creds, display_name="Google Business"):
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.org_id == org_id,
            PlatformConnection.platform == "google_business",
        )
    )
    conn = result.scalar_one_or_none()
    if conn:
        conn.display_name = display_name
        conn.credentials_encrypted = json.dumps(creds)
        conn.is_active = True
        conn.sync_failure_count = 0
    else:
        conn = PlatformConnection(
            org_id=org_id,
            platform="google_business",
            display_name=display_name,
            credentials_encrypted=json.dumps(creds),
            default_reply_mode="template",
            is_active=True,
        )
        db.add(conn)
    await db.flush()
    await log_audit(db, org_id, user_id, "platform_connected", "platform", conn.id, {"platform": "google_business", "oauth": True})
    await db.commit()
    return conn


@router.get("/callback")
async def google_callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
    db: AsyncSession = Depends(get_db),
):
    frontend = settings.FRONTEND_URL.rstrip("/")

    if error:
        return RedirectResponse(f"{frontend}/platforms?google_error={quote(error)}")
    if not code or not state:
        return RedirectResponse(f"{frontend}/platforms?google_error=missing_code")

    try:
        payload = decode_token(state)
    except HTTPException:
        return RedirectResponse(f"{frontend}/platforms?google_error=invalid_state")

    if payload.get("purpose") != "google_oauth":
        return RedirectResponse(f"{frontend}/platforms?google_error=invalid_state")

    user_id = int(payload["sub"])
    org_id = int(payload["org_id"])

    try:
        token_data = await exchange_code(code)
        try:
            location_info = await discover_account_and_location(token_data["access_token"])
            creds = build_credentials_from_token_response(token_data, location_info)
            display_name = location_info.get("location_title", "Google Business")
            await _save_google_connection(db, org_id, user_id, creds, display_name)
            return RedirectResponse(f"{frontend}/platforms?google=connected")
        except HTTPException as e:
            if e.status_code == 429:
                # Save tokens so user can finish setup without re-authenticating
                creds = build_credentials_from_token_response(token_data)
                await _save_google_connection(db, org_id, user_id, creds, "Google Business (pending)")
                return RedirectResponse(f"{frontend}/platforms?google=pending_setup")
            raise
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, str) else str(e.detail)
        return RedirectResponse(f"{frontend}/platforms?google_error={quote(detail)}")
    except Exception as e:
        return RedirectResponse(f"{frontend}/platforms?google_error={quote(str(e)[:200])}")
