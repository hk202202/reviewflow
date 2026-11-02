import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_subscription
from app.models.platform import PlatformConnection
from app.services.amazon_service import AmazonService, MARKETPLACE_ENDPOINTS

router = APIRouter(prefix="/platforms/amazon", tags=["amazon"])


class AmazonValidateRequest(BaseModel):
    client_id: str
    client_secret: str
    refresh_token: str
    marketplace_id: str = "A21TJRUUN4KGV"
    region: str = "eu"
    asins: str = ""


@router.get("/config")
async def amazon_config():
    return {
        "configured": True,
        "marketplaces": [
            {"id": "A21TJRUUN4KGV", "name": "Amazon India", "region": "eu"},
            {"id": "ATVPDKIKX0DER", "name": "Amazon US", "region": "na"},
            {"id": "A1F83G8C2ARO7P", "name": "Amazon UK", "region": "eu"},
        ],
        "regions": list(MARKETPLACE_ENDPOINTS.keys()),
        "setup_steps": [
            "Register as SP-API developer at sellercentral.amazon.in (or your marketplace)",
            "Create an LWA Security Profile and SP-API application",
            "Authorize your seller account and copy the refresh token",
            "Paste LWA Client ID, Client Secret, Refresh Token, and your product ASINs below",
        ],
    }


@router.post("/validate")
async def validate_amazon(
    data: AmazonValidateRequest,
    user_org=Depends(require_active_subscription),
):
    svc = AmazonService(data.model_dump())
    result = await svc.validate_credentials()
    return result
