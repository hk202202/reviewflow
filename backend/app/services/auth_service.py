import secrets
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
import pyotp
import qrcode
import io
import base64
import json

from app.models.user import User
from app.models.organization import Organization, OrgMember, OrgInvitation, Subscription, SSOConfiguration
from app.models.misc import TotpCredential
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import get_settings
from app.services.email_service import send_invite_email
from app.services.notification_service import log_audit

settings = get_settings()


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug[:50]


async def register_user(db: AsyncSession, email: str, password: str, full_name: str, org_name: str, account_type: str = "seller"):
    if account_type not in ("seller", "agency"):
        account_type = "seller"
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=email, hashed_password=hash_password(password), full_name=full_name, account_type=account_type)
    db.add(user)
    await db.flush()

    slug = slugify(org_name)
    base_slug = slug
    counter = 1
    while True:
        check = await db.execute(select(Organization).where(Organization.slug == slug))
        if not check.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(name=org_name, slug=slug, brand_name=org_name)
    db.add(org)
    await db.flush()

    member = OrgMember(org_id=org.id, user_id=user.id, role="owner")
    db.add(member)

    trial_end = datetime.now(timezone.utc) + timedelta(days=5)
    sub = Subscription(
        org_id=org.id, plan="trial", status="trialing", trial_ends_at=trial_end,
    )
    db.add(sub)
    await db.flush()

    token = create_access_token({"sub": str(user.id), "org_id": org.id})
    return user, org, token


async def login_user(db: AsyncSession, email: str, password: str, totp_code: str | None = None, preferred_org_id: int | None = None):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    totp_result = await db.execute(select(TotpCredential).where(TotpCredential.user_id == user.id))
    totp = totp_result.scalar_one_or_none()
    if totp and totp.is_verified:
        if not totp_code:
            return None, None, True
        import json
        from cryptography.fernet import Fernet
        key = settings.ENCRYPTION_KEY[:32].ljust(32, '0').encode()
        f = Fernet(base64.urlsafe_b64encode(key))
        secret = f.decrypt(totp.secret_encrypted.encode()).decode()
        if not pyotp.TOTP(secret).verify(totp_code, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    member = None
    if preferred_org_id:
        preferred = await db.execute(
            select(OrgMember).where(
                OrgMember.user_id == user.id,
                OrgMember.org_id == preferred_org_id,
                OrgMember.is_active == True,
            )
        )
        member = preferred.scalar_one_or_none()

    if not member:
        member_result = await db.execute(
            select(OrgMember)
            .where(OrgMember.user_id == user.id, OrgMember.is_active == True)
            .order_by(OrgMember.joined_at.desc())
        )
        member = member_result.scalars().first()
    if not member:
        raise HTTPException(status_code=403, detail="No organization membership")

    user.last_login_at = datetime.now(timezone.utc)
    token = create_access_token({"sub": str(user.id), "org_id": member.org_id})
    return user, token, False


async def list_user_organizations(db: AsyncSession, user_id: int, current_org_id: int | None = None) -> list[dict]:
    from sqlalchemy import func
    from app.models.platform import PlatformConnection

    result = await db.execute(
        select(Organization, OrgMember.role, func.count(PlatformConnection.id))
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .outerjoin(PlatformConnection, PlatformConnection.org_id == Organization.id)
        .where(OrgMember.user_id == user_id, OrgMember.is_active == True)
        .group_by(Organization.id, OrgMember.role)
        .order_by(Organization.name)
    )
    orgs = []
    for org, role, platform_count in result.all():
        orgs.append({
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "brand_name": org.brand_name,
            "role": role,
            "platform_count": platform_count or 0,
            "is_current": org.id == current_org_id,
        })
    return orgs


async def switch_organization(db: AsyncSession, user_id: int, org_id: int) -> str:
    result = await db.execute(
        select(OrgMember).where(
            OrgMember.user_id == user_id,
            OrgMember.org_id == org_id,
            OrgMember.is_active == True,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return create_access_token({"sub": str(user_id), "org_id": org_id})


async def create_organization_for_user(db: AsyncSession, user_id: int, org_name: str, account_type: str = "agency") -> tuple[Organization, str]:
    from app.services.plan_limits import enforce_company_limit

    await enforce_company_limit(db, user_id, account_type)
    slug = slugify(org_name)
    base_slug = slug
    counter = 1
    while True:
        check = await db.execute(select(Organization).where(Organization.slug == slug))
        if not check.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(name=org_name, slug=slug, brand_name=org_name)
    db.add(org)
    await db.flush()

    member = OrgMember(org_id=org.id, user_id=user_id, role="owner")
    db.add(member)

    trial_end = datetime.now(timezone.utc) + timedelta(days=5)
    sub = Subscription(
        org_id=org.id, plan="trial", status="trialing", trial_ends_at=trial_end,
    )
    db.add(sub)
    await db.flush()

    token = create_access_token({"sub": str(user_id), "org_id": org.id})
    await log_audit(db, org.id, user_id, "organization_created", "organization", org.id)
    return org, token


async def invite_member(db: AsyncSession, org_id: int, email: str, role: str, invited_by: int):
    token = secrets.token_urlsafe(32)
    invite = OrgInvitation(
        org_id=org_id,
        invited_email=email,
        role=role,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        invited_by=invited_by,
    )
    db.add(invite)

    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one()
    invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={token}"
    await send_invite_email(email, org.name, invite_url)
    await log_audit(db, org_id, invited_by, "member_invited", "user", payload={"email": email, "role": role})
    return invite


async def accept_invite(db: AsyncSession, token: str, password: str, full_name: str):
    result = await db.execute(select(OrgInvitation).where(OrgInvitation.token == token))
    invite = result.scalar_one_or_none()
    if not invite or invite.accepted_at:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitation expired")

    user_result = await db.execute(select(User).where(User.email == invite.invited_email))
    user = user_result.scalar_one_or_none()
    if not user:
        user = User(email=invite.invited_email, hashed_password=hash_password(password), full_name=full_name)
        db.add(user)
        await db.flush()

    member = OrgMember(org_id=invite.org_id, user_id=user.id, role=invite.role, invited_by=invite.invited_by)
    db.add(member)
    invite.accepted_at = datetime.now(timezone.utc)

    access_token = create_access_token({"sub": str(user.id), "org_id": invite.org_id})
    return user, access_token


async def setup_totp(db: AsyncSession, user_id: int) -> dict:
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=f"user-{user_id}", issuer_name="ReviewFlow")

    from cryptography.fernet import Fernet
    key = settings.ENCRYPTION_KEY[:32].ljust(32, '0').encode()
    f = Fernet(base64.urlsafe_b64encode(key))
    encrypted = f.encrypt(secret.encode()).decode()

    backup_codes = [secrets.token_hex(4) for _ in range(8)]
    backup_encrypted = f.encrypt(json.dumps(backup_codes).encode()).decode()

    existing = await db.execute(select(TotpCredential).where(TotpCredential.user_id == user_id))
    cred = existing.scalar_one_or_none()
    if cred:
        cred.secret_encrypted = encrypted
        cred.backup_codes_encrypted = backup_encrypted
        cred.is_verified = False
    else:
        cred = TotpCredential(user_id=user_id, secret_encrypted=encrypted, backup_codes_encrypted=backup_encrypted)
        db.add(cred)

    return {"secret": secret, "qr_uri": uri, "backup_codes": backup_codes}


async def verify_totp(db: AsyncSession, user_id: int, code: str) -> bool:
    result = await db.execute(select(TotpCredential).where(TotpCredential.user_id == user_id))
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=400, detail="2FA not set up")

    from cryptography.fernet import Fernet
    key = settings.ENCRYPTION_KEY[:32].ljust(32, '0').encode()
    f = Fernet(base64.urlsafe_b64encode(key))
    secret = f.decrypt(cred.secret_encrypted.encode()).decode()

    if pyotp.TOTP(secret).verify(code, valid_window=1):
        cred.is_verified = True
        cred.enabled_at = datetime.now(timezone.utc)
        return True
    raise HTTPException(status_code=400, detail="Invalid code")
