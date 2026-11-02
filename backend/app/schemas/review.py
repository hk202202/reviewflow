from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PlatformConnectionCreate(BaseModel):
    platform: str
    display_name: str
    credentials: Optional[dict] = None
    default_reply_mode: str = "template"


class PlatformConnectionResponse(BaseModel):
    id: int
    platform: str
    display_name: str
    default_reply_mode: str
    is_active: bool
    last_synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    title: str
    asin: Optional[str] = None
    platform_sku: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    reply_mode_override: Optional[str] = None

    class Config:
        from_attributes = True


class ReplyTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    body: str
    category: str = "thank_you"
    star_rating_filter: str = "any"


class ReplyTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    body: str
    category: str
    star_rating_filter: str
    usage_count: int
    last_used_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class ReplyModeSettingCreate(BaseModel):
    scope: str
    platform_connection_id: Optional[int] = None
    product_id: Optional[int] = None
    reply_mode: str
    template_id: Optional[int] = None


class ReviewCreate(BaseModel):
    reviewer_name: str
    rating: int
    body: str
    title: Optional[str] = None
    platform: Optional[str] = None
    product_name: Optional[str] = None
    product_id: Optional[int] = None
    platform_connection_id: Optional[int] = None
    review_date: Optional[datetime] = None


class ReviewResponse(BaseModel):
    id: int
    reviewer_name: str
    rating: int
    title: Optional[str] = None
    body: str
    sentiment: str
    reply_status: str
    published_reply_text: Optional[str] = None
    platform: Optional[str] = None
    product_name: Optional[str] = None
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    review_date: Optional[datetime] = None
    imported_at: datetime

    class Config:
        from_attributes = True


class GeneratedReplyCreate(BaseModel):
    review_id: int
    source: str = "ai"
    template_id: Optional[int] = None
    body: Optional[str] = None


class GeneratedReplyResponse(BaseModel):
    id: int
    review_id: int
    source: str
    body: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AIReplyRequest(BaseModel):
    review_id: int
    tone: Optional[str] = None


class AIReviewGenerateRequest(BaseModel):
    product_title: str
    product_features: Optional[str] = None
    rating_target: int = 5
    persona_id: Optional[int] = None


class PersonaCreate(BaseModel):
    name: str
    age_range: Optional[str] = None
    location: Optional[str] = None
    writing_style: str = "moderate"
    typo_probability: float = 0.05
    vocab_level: str = "moderate"


class PersonaResponse(BaseModel):
    id: int
    name: str
    age_range: Optional[str] = None
    location: Optional[str] = None
    writing_style: str
    vocab_level: str
    is_active: bool

    class Config:
        from_attributes = True


class BulkReplyRequest(BaseModel):
    review_ids: list[int]
    source: str = "template"
    template_id: Optional[int] = None


class ReviewFilterParams(BaseModel):
    platform: Optional[str] = None
    rating: Optional[int] = None
    sentiment: Optional[str] = None
    reply_status: Optional[str] = None
    is_flagged: Optional[bool] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20
