from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    org_name: str
    account_type: str = "seller"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None
    org_id: Optional[int] = None


class CreateOrgRequest(BaseModel):
    org_name: str


class SwitchOrgRequest(BaseModel):
    org_id: int


class OrgListItem(BaseModel):
    id: int
    name: str
    slug: str
    brand_name: Optional[str] = None
    role: str
    platform_count: int = 0
    is_current: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    org_id: int
    requires_2fa: bool = False


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    onboarding_completed: bool = False
    account_type: str = "seller"

    class Config:
        from_attributes = True


class OrgResponse(BaseModel):
    id: int
    name: str
    slug: str
    brand_name: Optional[str] = None
    logo_url: Optional[str] = None
    brand_tone: str = "friendly"

    class Config:
        from_attributes = True


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class AcceptInviteRequest(BaseModel):
    token: str
    password: str
    full_name: str


class SSOConfigRequest(BaseModel):
    provider: str
    protocol: str
    metadata_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    issuer_url: Optional[str] = None
    sso_url: Optional[str] = None
    is_active: bool = False


class TotpSetupResponse(BaseModel):
    secret: str
    qr_uri: str
    backup_codes: list[str]


class TotpVerifyRequest(BaseModel):
    code: str
