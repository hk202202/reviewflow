"""Plan limits for direct sellers and agencies."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.organization import OrgMember, Subscription, Organization
from app.models.platform import PlatformConnection

PLAN_RANK = {
    "trial": 0,
    "solo": 1,
    "growth": 2,
    "professional": 3,
    "enterprise": 4,
}

PLAN_LIMITS = {
    "trial": {
        "label": "Trial",
        "segment": "seller",
        "audience": "Direct seller",
        "max_companies": 1,
        "max_platforms_per_org": 1,
        "max_team_members": 1,
        "max_reviews_mo": 50,
        "max_ai_replies_mo": 10,
    },
    "solo": {
        "label": "Solo",
        "segment": "seller",
        "audience": "Direct seller",
        "max_companies": 1,
        "max_platforms_per_org": 2,
        "max_team_members": 1,
        "max_reviews_mo": 500,
        "max_ai_replies_mo": 100,
    },
    "growth": {
        "label": "Business",
        "segment": "seller",
        "audience": "Direct seller",
        "max_companies": 1,
        "max_platforms_per_org": 5,
        "max_team_members": 2,
        "max_reviews_mo": 500,
        "max_ai_replies_mo": 200,
    },
    "professional": {
        "label": "Agency",
        "segment": "agency",
        "audience": "Agency",
        "max_companies": 10,
        "max_platforms_per_org": 20,
        "max_team_members": 5,
        "max_reviews_mo": 5000,
        "max_ai_replies_mo": 2000,
    },
    "enterprise": {
        "label": "Agency Pro",
        "segment": "agency",
        "audience": "Agency",
        "max_companies": None,
        "max_platforms_per_org": None,
        "max_team_members": None,
        "max_reviews_mo": None,
        "max_ai_replies_mo": None,
    },
}

PUBLIC_PLANS = [
    {
        "id": "solo",
        "name": "Solo",
        "audience": "Direct seller",
        "description": "One brand, one login — perfect for individual Amazon/Flipkart sellers.",
        "highlights": ["1 company", "2 platforms", "500 reviews/mo", "100 AI replies/mo"],
    },
    {
        "id": "growth",
        "name": "Business",
        "audience": "Direct seller",
        "description": "Growing stores with more products and a small team.",
        "highlights": ["1 company", "5 platforms", "500 reviews/mo", "2 team members"],
        "popular": False,
    },
    {
        "id": "professional",
        "name": "Agency",
        "audience": "Agency",
        "description": "Manage multiple client brands from one login.",
        "highlights": ["10 companies", "20 platforms each", "5 team seats", "Client invites"],
        "popular": True,
    },
    {
        "id": "enterprise",
        "name": "Agency Pro",
        "audience": "Agency",
        "description": "Unlimited clients, SSO, and dedicated support.",
        "highlights": ["Unlimited companies", "Unlimited platforms", "SSO", "Dedicated CSM"],
    },
]


def limits_for_plan(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])


def _higher_plan(a: str, b: str) -> str:
    return a if PLAN_RANK.get(a, 0) >= PLAN_RANK.get(b, 0) else b


def _under_limit(current: int, maximum: int | None) -> bool:
    if maximum is None:
        return True
    return current < maximum


async def count_owned_companies(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(OrgMember.id)).where(
            OrgMember.user_id == user_id,
            OrgMember.role == "owner",
            OrgMember.is_active == True,
        )
    )
    return result.scalar() or 0


async def get_user_effective_plan(db: AsyncSession, user_id: int) -> str:
    result = await db.execute(
        select(Subscription.plan)
        .join(OrgMember, OrgMember.org_id == Subscription.org_id)
        .where(OrgMember.user_id == user_id, OrgMember.role == "owner", OrgMember.is_active == True)
    )
    effective = "trial"
    for (plan,) in result.all():
        effective = _higher_plan(effective, plan if plan in PLAN_RANK else "trial")
    return effective


async def get_account_context(db: AsyncSession, user_id: int, current_org_id: int, account_type: str) -> dict:
    effective_plan = await get_user_effective_plan(db, user_id)
    limits = limits_for_plan(effective_plan)
    owned = await count_owned_companies(db, user_id)

    orgs_result = await db.execute(
        select(Organization, OrgMember.role, func.count(PlatformConnection.id))
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .outerjoin(PlatformConnection, PlatformConnection.org_id == Organization.id)
        .where(OrgMember.user_id == user_id, OrgMember.is_active == True)
        .group_by(Organization.id, OrgMember.role)
        .order_by(Organization.name)
    )
    organizations = [
        {
            "id": org.id,
            "name": org.name,
            "role": role,
            "platform_count": platform_count or 0,
            "is_current": org.id == current_org_id,
        }
        for org, role, platform_count in orgs_result.all()
    ]

    max_companies = limits["max_companies"]
    can_add_company = max_companies is None or owned < max_companies
    if account_type == "seller" and effective_plan in ("trial", "solo", "growth"):
        can_add_company = owned < 1
    elif account_type == "agency" and effective_plan == "trial":
        can_add_company = owned < 3

    platform_result = await db.execute(
        select(func.count(PlatformConnection.id)).where(PlatformConnection.org_id == current_org_id)
    )
    platform_count = platform_result.scalar() or 0

    team_result = await db.execute(
        select(func.count(OrgMember.id)).where(OrgMember.org_id == current_org_id, OrgMember.is_active == True)
    )
    team_count = team_result.scalar() or 0

    show_company_switcher = len(organizations) > 1 or account_type == "agency" or can_add_company

    return {
        "account_type": account_type,
        "effective_plan": effective_plan,
        "plan_label": limits["label"],
        "limits": limits,
        "owned_companies": owned,
        "can_add_company": can_add_company,
        "platform_count": platform_count,
        "team_count": team_count,
        "can_add_platform": _under_limit(platform_count, limits["max_platforms_per_org"]),
        "can_invite_member": _under_limit(team_count, limits["max_team_members"]),
        "show_company_switcher": show_company_switcher,
        "organizations": organizations,
    }


async def enforce_company_limit(db: AsyncSession, user_id: int, account_type: str) -> None:
    effective = await get_user_effective_plan(db, user_id)
    limits = limits_for_plan(effective)
    max_c = limits["max_companies"]
    if account_type == "seller" and effective in ("trial", "solo", "growth"):
        max_c = 1
    elif account_type == "agency" and effective == "trial":
        max_c = 3
    owned = await count_owned_companies(db, user_id)
    if max_c is not None and owned >= max_c:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "company_limit",
                "message": f"Your {limits['label']} plan allows {max_c} company(ies). Upgrade to Agency to manage multiple clients.",
                "billing_url": "/settings/billing",
                "effective_plan": effective,
            },
        )


async def enforce_platform_limit(db: AsyncSession, org_id: int, user_id: int) -> None:
    effective = await get_user_effective_plan(db, user_id)
    limits = limits_for_plan(effective)
    max_p = limits["max_platforms_per_org"]
    if max_p is None:
        return
    result = await db.execute(
        select(func.count(PlatformConnection.id)).where(PlatformConnection.org_id == org_id)
    )
    count = result.scalar() or 0
    if count >= max_p:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "platform_limit",
                "message": f"Platform limit reached ({max_p}) on your {limits['label']} plan. Upgrade to add more.",
                "billing_url": "/settings/billing",
            },
        )


async def enforce_team_limit(db: AsyncSession, org_id: int, user_id: int) -> None:
    effective = await get_user_effective_plan(db, user_id)
    limits = limits_for_plan(effective)
    max_t = limits["max_team_members"]
    if max_t is None:
        return
    result = await db.execute(
        select(func.count(OrgMember.id)).where(OrgMember.org_id == org_id, OrgMember.is_active == True)
    )
    count = result.scalar() or 0
    if count >= max_t:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "team_limit",
                "message": f"Team member limit reached ({max_t}) on your {limits['label']} plan.",
                "billing_url": "/settings/billing",
            },
        )
