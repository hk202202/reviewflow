from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import require_active_subscription
from app.services.myntra_service import MyntraService

router = APIRouter(prefix="/platforms/myntra", tags=["myntra"])


class MyntraValidateRequest(BaseModel):
    api_key: str
    api_secret: str
    seller_id: str = ""


@router.get("/config")
async def myntra_config():
    return {
        "configured": True,
        "sync_method": "api",
        "extension_optional": True,
        "setup_steps": [
            "Request Myntra Seller API access from Myntra partner team",
            "Obtain API Key + API Secret for your seller account",
            "Paste credentials below and click Sync Reviews",
            "Optionally install Chrome extension for AI reply on seller portal",
        ],
    }


@router.post("/validate")
async def validate_myntra(data: MyntraValidateRequest, user_org=Depends(require_active_subscription)):
    svc = MyntraService(data.model_dump())
    return await svc.validate_credentials()
