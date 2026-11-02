from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import require_active_subscription
from app.services.flipkart_service import FlipkartService

router = APIRouter(prefix="/platforms/flipkart", tags=["flipkart"])


class FlipkartValidateRequest(BaseModel):
    client_id: str
    client_secret: str
    seller_id: str = ""


@router.get("/config")
async def flipkart_config():
    return {
        "configured": True,
        "sync_method": "api",
        "extension_optional": True,
        "setup_steps": [
            "Apply for Flipkart Seller API access in Seller Hub",
            "Create API credentials (Client ID + Client Secret)",
            "Paste credentials below and click Sync Reviews",
            "Optionally install Chrome extension for AI reply on seller portal",
        ],
    }


@router.post("/validate")
async def validate_flipkart(data: FlipkartValidateRequest, user_org=Depends(require_active_subscription)):
    svc = FlipkartService(data.model_dump())
    return await svc.validate_credentials()
