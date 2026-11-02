from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, get_current_org_member, require_active_subscription
from app.models.user import User
from app.models.organization import Organization, OrgMember, OrgInvitation, SSOConfiguration
from app.models.misc import Notification, AuditLog, TotpCredential
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse, UserResponse, OrgResponse,
    InviteRequest, AcceptInviteRequest, SSOConfigRequest, TotpVerifyRequest,
    OrgListItem, SwitchOrgRequest, CreateOrgRequest,
)
from app.services.auth_service import (
    register_user, login_user, invite_member, accept_invite, setup_totp, verify_totp,
    list_user_organizations, switch_organization, create_organization_for_user,
)
from app.services.subscription_service import ensure_subscription, subscription_status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user, org, token = await register_user(db, data.email, data.password, data.full_name, data.org_name, data.account_type)
    return TokenResponse(access_token=token, user_id=user.id, org_id=org.id)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user, token, requires_2fa = await login_user(db, data.email, data.password, data.totp_code, data.org_id)
    if requires_2fa:
        return TokenResponse(access_token="", user_id=0, org_id=0, requires_2fa=True)
    member_result = await db.execute(
        select(OrgMember)
        .where(OrgMember.user_id == user.id, OrgMember.is_active == True)
        .order_by(OrgMember.joined_at.desc())
    )
    member = member_result.scalars().first()
    if not member:
        raise HTTPException(status_code=403, detail="No organization membership")
    return TokenResponse(access_token=token, user_id=user.id, org_id=member.org_id)


@router.get("/organizations", response_model=list[OrgListItem])
async def get_organizations(
    user_org=Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db),
):
    user, member = user_org
    return await list_user_organizations(db, user.id, member.org_id)


@router.post("/switch-org", response_model=TokenResponse)
async def switch_org(
    data: SwitchOrgRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = await switch_organization(db, user.id, data.org_id)
    return TokenResponse(access_token=token, user_id=user.id, org_id=data.org_id)


@router.post("/organizations", response_model=TokenResponse)
async def create_organization(
    data: CreateOrgRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org, token = await create_organization_for_user(db, user.id, data.org_name, user.account_type or "agency")
    return TokenResponse(access_token=token, user_id=user.id, org_id=org.id)


@router.get("/me")
async def get_me(
    user_org=Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db),
):
    user, member = user_org
    org_result = await db.execute(select(Organization).where(Organization.id == member.org_id))
    org = org_result.scalar_one()
    sub = await ensure_subscription(db, member.org_id)
    from app.services.plan_limits import get_account_context
    account_ctx = await get_account_context(db, user.id, member.org_id, user.account_type or "seller")
    return {
        "user": UserResponse.model_validate(user),
        "org": OrgResponse.model_validate(org),
        "role": member.role,
        "permissions": member.permissions,
        "subscription": subscription_status(sub),
        "account": account_ctx,
    }


@router.get("/account-context")
async def account_context(user_org=Depends(get_current_org_member), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    from app.services.plan_limits import get_account_context
    return await get_account_context(db, user.id, member.org_id, user.account_type or "seller")


@router.post("/invite")
async def invite(data: InviteRequest, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    if member.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    from app.services.plan_limits import enforce_team_limit
    await enforce_team_limit(db, member.org_id, user.id)
    invite_obj = await invite_member(db, member.org_id, data.email, data.role, user.id)
    return {"message": "Invitation sent", "email": data.email}


@router.get("/invitations")
async def list_invitations(user_org=Depends(get_current_org_member), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(
        select(OrgInvitation).where(
            OrgInvitation.org_id == member.org_id,
            OrgInvitation.accepted_at.is_(None),
        )
    )
    invites = result.scalars().all()
    return [{"id": i.id, "email": i.invited_email, "role": i.role, "created_at": i.created_at} for i in invites]


@router.post("/accept-invite")
async def accept(data: AcceptInviteRequest, db: AsyncSession = Depends(get_db)):
    user, token = await accept_invite(db, data.token, data.password, data.full_name)
    member_result = await db.execute(
        select(OrgMember)
        .where(OrgMember.user_id == user.id, OrgMember.is_active == True)
        .order_by(OrgMember.joined_at.desc())
    )
    member = member_result.scalars().first()
    if not member:
        raise HTTPException(status_code=403, detail="No organization membership")
    return TokenResponse(access_token=token, user_id=user.id, org_id=member.org_id)


@router.get("/team")
async def list_team(user_org=Depends(get_current_org_member), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(
        select(OrgMember, User).join(User, OrgMember.user_id == User.id).where(
            OrgMember.org_id == member.org_id
        )
    )
    members = []
    for m, u in result.all():
        members.append({
            "id": m.id, "user_id": u.id, "email": u.email, "full_name": u.full_name,
            "role": m.role, "is_active": m.is_active, "joined_at": m.joined_at,
            "last_login_at": u.last_login_at,
        })
    return members


@router.patch("/team/{member_id}")
async def update_member(member_id: int, role: str, user_org=Depends(get_current_org_member), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    if member.role not in ("owner", "admin"):
        raise HTTPException(status_code=403)
    result = await db.execute(select(OrgMember).where(OrgMember.id == member_id, OrgMember.org_id == member.org_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404)
    target.role = role
    return {"message": "Role updated"}


@router.delete("/team/{member_id}")
async def deactivate_member(member_id: int, user_org=Depends(get_current_org_member), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    if member.role not in ("owner", "admin"):
        raise HTTPException(status_code=403)
    result = await db.execute(select(OrgMember).where(OrgMember.id == member_id, OrgMember.org_id == member.org_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404)
    target.is_active = False
    return {"message": "Member deactivated"}


@router.get("/sso/{slug}")
async def get_sso_config(slug: str, db: AsyncSession = Depends(get_db)):
    org_result = await db.execute(select(Organization).where(Organization.slug == slug))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    sso_result = await db.execute(select(SSOConfiguration).where(SSOConfiguration.org_id == org.id, SSOConfiguration.is_active == True))
    sso = sso_result.scalar_one_or_none()
    return {
        "org_name": org.name,
        "sso_enabled": sso is not None,
        "provider": sso.provider if sso else None,
        "sso_url": sso.sso_url if sso else None,
    }


@router.post("/sso/config")
async def configure_sso(data: SSOConfigRequest, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    if member.role != "owner":
        raise HTTPException(status_code=403)
    existing = await db.execute(select(SSOConfiguration).where(SSOConfiguration.org_id == member.org_id))
    sso = existing.scalar_one_or_none()
    if sso:
        for k, v in data.model_dump(exclude_unset=True).items():
            if k == "client_secret":
                sso.client_secret_encrypted = v
            else:
                setattr(sso, k, v)
    else:
        payload = data.model_dump()
        if "client_secret" in payload:
            payload["client_secret_encrypted"] = payload.pop("client_secret")
        sso = SSOConfiguration(org_id=member.org_id, **payload)
        db.add(sso)
    return {"message": "SSO configured"}


@router.post("/2fa/setup")
async def setup_2fa(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await setup_totp(db, user.id)
    return result


@router.post("/2fa/verify")
async def verify_2fa(data: TotpVerifyRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await verify_totp(db, user.id, data.code)
    return {"message": "2FA enabled"}


@router.post("/onboarding/complete")
async def complete_onboarding(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user.onboarding_completed = True
    return {"message": "Onboarding completed"}
