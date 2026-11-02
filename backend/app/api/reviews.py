from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from datetime import datetime, timezone
import csv
import io

from app.core.database import get_db
from app.core.security import get_current_user, get_current_org_member, require_active_subscription
from app.models.platform import PlatformConnection, Product, ReplyTemplate, ReplyModeSetting
from app.models.review import Review, GeneratedReply, Persona, GeneratedReview
from app.models.organization import Organization, Subscription
from app.models.misc import Notification, AuditLog, Webhook, ReviewRequest
from app.schemas.review import (
    PlatformConnectionCreate, PlatformConnectionResponse, ProductResponse,
    ReplyTemplateCreate, ReplyTemplateResponse, ReplyModeSettingCreate,
    ReviewCreate, ReviewResponse, GeneratedReplyCreate, GeneratedReplyResponse,
    AIReplyRequest, AIReviewGenerateRequest, PersonaCreate, PersonaResponse,
    BulkReplyRequest,
)
from app.services.ai_service import generate_reply, generate_review, analyze_sentiment
from app.services.template_service import fill_template, extract_issue_keyword
from app.services.flag_service import check_review_flags
from app.services.notification_service import notify_new_review, log_audit
from app.services.webhook_service import dispatch_webhook
from app.services.marketplace_sync import fetch_reviews_via_api
from app.services.marketplace_sync import fetch_reviews_via_api, extension_hint, EXTENSION_COMPATIBLE_PLATFORMS

router = APIRouter(tags=["reviews"])


@router.get("/platforms", response_model=list[PlatformConnectionResponse])
async def list_platforms(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(select(PlatformConnection).where(PlatformConnection.org_id == member.org_id))
    return result.scalars().all()


@router.post("/platforms", response_model=PlatformConnectionResponse)
async def create_platform(data: PlatformConnectionCreate, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    from app.services.plan_limits import enforce_platform_limit
    await enforce_platform_limit(db, member.org_id, user.id)
    import json
    conn = PlatformConnection(
        org_id=member.org_id,
        platform=data.platform,
        display_name=data.display_name,
        credentials_encrypted=json.dumps(data.credentials or {}),
        default_reply_mode=data.default_reply_mode,
    )
    db.add(conn)
    await db.flush()
    await log_audit(db, member.org_id, user.id, "platform_connected", "platform", conn.id)
    return conn


@router.post("/platforms/{conn_id}/sync")
async def sync_platform(conn_id: int, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    result = await db.execute(select(PlatformConnection).where(PlatformConnection.id == conn_id, PlatformConnection.org_id == member.org_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404)

    import json
    creds = json.loads(conn.credentials_encrypted or "{}")
    reviews_data = []

    sync_message = None
    updated_creds = None
    reviews_data, sync_message, updated_creds = await fetch_reviews_via_api(conn.platform, creds)
    if updated_creds:
        conn.credentials_encrypted = json.dumps(updated_creds)
    if conn.platform in EXTENSION_COMPATIBLE_PLATFORMS and sync_message:
        sync_message = f"{sync_message} {extension_hint(conn.platform, creds)}"

    imported = 0
    for rd in reviews_data:
        existing = await db.execute(select(Review).where(
            Review.org_id == member.org_id,
            Review.external_review_id == rd.get("external_review_id"),
        ))
        if existing.scalar_one_or_none():
            continue

        sentiment = analyze_sentiment(rd["body"], rd["rating"])
        is_flagged, flag_reason = check_review_flags(rd["body"], rd["rating"])

        review = Review(
            org_id=member.org_id,
            platform_connection_id=conn.id,
            external_review_id=rd.get("external_review_id"),
            reviewer_name=rd["reviewer_name"],
            rating=rd["rating"],
            title=rd.get("title"),
            body=rd["body"],
            sentiment=sentiment,
            platform=conn.platform,
            product_name=rd.get("product_name"),
            is_flagged=is_flagged,
            flag_reason=flag_reason,
            reply_status="escalated" if is_flagged else "pending",
        )
        db.add(review)
        imported += 1

        if rd["rating"] <= 2:
            await notify_new_review(db, member.org_id, review, user.email)

    conn.last_synced_at = datetime.now(timezone.utc)
    conn.sync_failure_count = 0
    await dispatch_webhook(db, member.org_id, "review.created", {"count": imported, "platform": conn.platform})
    result = {"imported": imported}
    if sync_message:
        result["message"] = sync_message
    return result


@router.get("/reviews")
async def list_reviews(
    platform: str | None = None, rating: int | None = None, sentiment: str | None = None,
    reply_status: str | None = None, is_flagged: bool | None = None, search: str | None = None,
    page: int = 1, page_size: int = 20,
    user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db),
):
    _, member = user_org
    query = select(Review).where(Review.org_id == member.org_id)
    if platform:
        query = query.where(Review.platform == platform)
    if rating:
        query = query.where(Review.rating == rating)
    if sentiment:
        query = query.where(Review.sentiment == sentiment)
    if reply_status:
        query = query.where(Review.reply_status == reply_status)
    if is_flagged is not None:
        query = query.where(Review.is_flagged == is_flagged)
    if search:
        query = query.where(or_(Review.body.ilike(f"%{search}%"), Review.reviewer_name.ilike(f"%{search}%")))

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    query = query.order_by(Review.imported_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    reviews = result.scalars().all()
    return {"items": [ReviewResponse.model_validate(r) for r in reviews], "total": total, "page": page, "page_size": page_size}


@router.post("/reviews", response_model=ReviewResponse)
async def create_review(data: ReviewCreate, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    sentiment = analyze_sentiment(data.body, data.rating)
    is_flagged, flag_reason = check_review_flags(data.body, data.rating)
    review = Review(
        org_id=member.org_id,
        product_id=data.product_id,
        platform_connection_id=data.platform_connection_id,
        reviewer_name=data.reviewer_name,
        rating=data.rating,
        title=data.title,
        body=data.body,
        sentiment=sentiment,
        platform=data.platform,
        product_name=data.product_name,
        is_flagged=is_flagged,
        flag_reason=flag_reason,
        reply_status="escalated" if is_flagged else "pending",
        review_date=data.review_date,
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)
    return review


@router.post("/reviews/import-csv")
async def import_csv(file: UploadFile = File(...), user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode()))
    imported = 0
    for row in reader:
        body = row.get("body") or row.get("review") or row.get("text") or ""
        rating = int(row.get("rating") or row.get("stars") or 3)
        sentiment = analyze_sentiment(body, rating)
        is_flagged, flag_reason = check_review_flags(body, rating)
        review = Review(
            org_id=member.org_id,
            reviewer_name=row.get("reviewer_name") or row.get("name") or "Anonymous",
            rating=rating,
            title=row.get("title"),
            body=body,
            sentiment=sentiment,
            platform=row.get("platform"),
            product_name=row.get("product_name") or row.get("product"),
            is_flagged=is_flagged,
            flag_reason=flag_reason,
            reply_status="escalated" if is_flagged else "pending",
        )
        db.add(review)
        imported += 1
    return {"imported": imported}


@router.get("/reviews/export-csv")
async def export_csv(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(select(Review).where(Review.org_id == member.org_id))
    reviews = result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "reviewer_name", "rating", "title", "body", "sentiment", "reply_status", "platform", "product_name", "published_reply"])
    for r in reviews:
        writer.writerow([r.id, r.reviewer_name, r.rating, r.title, r.body, r.sentiment, r.reply_status, r.platform, r.product_name, r.published_reply_text])
    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=reviews.csv"})


@router.get("/reviews/escalated")
async def list_escalated(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(select(Review).where(Review.org_id == member.org_id, Review.is_flagged == True).order_by(Review.imported_at.desc()))
    return [ReviewResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/reviews/{review_id}/resolve-flag")
async def resolve_flag(review_id: int, action: str, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    result = await db.execute(select(Review).where(Review.id == review_id, Review.org_id == member.org_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404)
    if action == "approve":
        review.is_flagged = False
        review.reply_status = "pending"
    elif action == "dismiss":
        review.is_flagged = False
        review.reply_status = "skipped"
    await log_audit(db, member.org_id, user.id, "flag_resolved", "review", review_id, {"action": action})
    return {"message": f"Flag {action}d"}


@router.get("/templates", response_model=list[ReplyTemplateResponse])
async def list_templates(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(select(ReplyTemplate).where(ReplyTemplate.org_id == member.org_id, ReplyTemplate.is_active == True))
    return result.scalars().all()


@router.post("/templates", response_model=ReplyTemplateResponse)
async def create_template(data: ReplyTemplateCreate, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    tpl = ReplyTemplate(org_id=member.org_id, created_by=user.id, **data.model_dump())
    db.add(tpl)
    await log_audit(db, member.org_id, user.id, "template_created", "template", payload={"name": data.name})
    await db.flush()
    await db.refresh(tpl)
    return tpl


@router.put("/templates/{tpl_id}", response_model=ReplyTemplateResponse)
async def update_template(tpl_id: int, data: ReplyTemplateCreate, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(select(ReplyTemplate).where(ReplyTemplate.id == tpl_id, ReplyTemplate.org_id == member.org_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404)
    for k, v in data.model_dump().items():
        setattr(tpl, k, v)
    return tpl


@router.delete("/templates/{tpl_id}")
async def delete_template(tpl_id: int, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(select(ReplyTemplate).where(ReplyTemplate.id == tpl_id, ReplyTemplate.org_id == member.org_id))
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404)
    tpl.is_active = False
    return {"message": "Template deleted"}


@router.post("/reply-modes")
async def set_reply_mode(data: ReplyModeSettingCreate, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    setting = ReplyModeSetting(org_id=member.org_id, updated_by=user.id, **data.model_dump())
    db.add(setting)
    return {"message": "Reply mode updated"}


@router.post("/ai/reply")
async def ai_reply(data: AIReplyRequest, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    result = await db.execute(select(Review).where(Review.id == data.review_id, Review.org_id == member.org_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404)

    org_result = await db.execute(select(Organization).where(Organization.id == member.org_id))
    org = org_result.scalar_one()

    body = await generate_reply(
        review.body, review.rating, review.product_name or "",
        org.brand_name or org.name, data.tone or org.brand_tone, review.platform,
    )

    reply = GeneratedReply(
        review_id=review.id, org_id=member.org_id, source="ai",
        body=body, status="draft", created_by=user.id,
    )
    db.add(reply)
    review.reply_status = "draft"
    await db.flush()
    await db.refresh(reply)
    return GeneratedReplyResponse.model_validate(reply)


@router.post("/ai/generate-review")
async def ai_generate_review(data: AIReviewGenerateRequest, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    persona_dict = None
    if data.persona_id:
        p_result = await db.execute(select(Persona).where(Persona.id == data.persona_id))
        p = p_result.scalar_one_or_none()
        if p:
            persona_dict = {"name": p.name, "age_range": p.age_range, "location": p.location,
                           "writing_style": p.writing_style, "typo_probability": p.typo_probability, "vocab_level": p.vocab_level}

    body = await generate_review(data.product_title, data.product_features or "", data.rating_target, persona_dict)
    gen = GeneratedReview(
        org_id=member.org_id, product_title=data.product_title,
        rating_target=data.rating_target, body=body, persona_id=data.persona_id,
    )
    db.add(gen)
    await db.flush()
    return {"id": gen.id, "body": body, "status": "draft"}


@router.post("/replies/apply-template")
async def apply_template(review_id: int, template_id: int, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.org_id == member.org_id))
    review = review_result.scalar_one_or_none()
    tpl_result = await db.execute(select(ReplyTemplate).where(ReplyTemplate.id == template_id, ReplyTemplate.org_id == member.org_id))
    tpl = tpl_result.scalar_one_or_none()
    if not review or not tpl:
        raise HTTPException(status_code=404)

    org_result = await db.execute(select(Organization).where(Organization.id == member.org_id))
    org = org_result.scalar_one()

    context = {
        "reviewer_name": review.reviewer_name,
        "product_name": review.product_name or "",
        "rating": str(review.rating),
        "platform": review.platform or "",
        "issue_keyword": extract_issue_keyword(review.body),
        "brand_name": org.brand_name or org.name,
    }
    body = fill_template(tpl.body, context)
    tpl.usage_count += 1
    tpl.last_used_at = datetime.now(timezone.utc)

    reply = GeneratedReply(
        review_id=review.id, org_id=member.org_id, source="template",
        template_id=tpl.id, body=body, status="draft", created_by=user.id,
    )
    db.add(reply)
    review.reply_status = "draft"
    await db.flush()
    await db.refresh(reply)
    return GeneratedReplyResponse.model_validate(reply)


@router.post("/replies/publish")
async def publish_reply(review_id: int, reply_id: int, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.org_id == member.org_id))
    review = review_result.scalar_one_or_none()
    reply_result = await db.execute(select(GeneratedReply).where(GeneratedReply.id == reply_id))
    reply = reply_result.scalar_one_or_none()
    if not review or not reply:
        raise HTTPException(status_code=404)

    review.published_reply_text = reply.body
    review.reply_status = "published"
    review.published_at = datetime.now(timezone.utc)
    reply.status = "published"
    await log_audit(db, member.org_id, user.id, "reply_published", "review", review_id, {"body": reply.body[:200]})
    await dispatch_webhook(db, member.org_id, "review.reply_published", {"review_id": review_id, "reply": reply.body[:200]})
    return {"message": "Reply published"}


@router.post("/replies/bulk")
async def bulk_reply(data: BulkReplyRequest, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    user, member = user_org
    processed = 0
    for rid in data.review_ids:
        if data.source == "template" and data.template_id:
            try:
                await apply_template(rid, data.template_id, user_org, db)
                processed += 1
            except Exception:
                pass
    return {"processed": processed}


@router.get("/personas", response_model=list[PersonaResponse])
async def list_personas(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(select(Persona).where(Persona.org_id == member.org_id, Persona.is_active == True))
    return result.scalars().all()


@router.post("/personas", response_model=PersonaResponse)
async def create_persona(data: PersonaCreate, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    persona = Persona(org_id=member.org_id, **data.model_dump())
    db.add(persona)
    await db.flush()
    await db.refresh(persona)
    return persona


@router.get("/notifications")
async def list_notifications(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(
        select(Notification).where(Notification.org_id == member.org_id)
        .order_by(Notification.created_at.desc()).limit(50)
    )
    return [{"id": n.id, "type": n.type, "title": n.title, "body": n.body, "action_url": n.action_url, "read_at": n.read_at, "created_at": n.created_at} for n in result.scalars().all()]


@router.post("/notifications/{notif_id}/read")
async def mark_read(notif_id: int, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(select(Notification).where(Notification.id == notif_id, Notification.org_id == member.org_id))
    notif = result.scalar_one_or_none()
    if notif:
        notif.read_at = datetime.now(timezone.utc)
    return {"message": "Marked as read"}


@router.get("/audit-log")
async def get_audit_log(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(
        select(AuditLog).where(AuditLog.org_id == member.org_id)
        .order_by(AuditLog.created_at.desc()).limit(100)
    )
    return [{"id": a.id, "action": a.action, "target_type": a.target_type, "target_id": a.target_id, "payload": a.payload, "created_at": a.created_at} for a in result.scalars().all()]


@router.get("/webhooks")
async def list_webhooks(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    result = await db.execute(select(Webhook).where(Webhook.org_id == member.org_id))
    return result.scalars().all()


@router.post("/webhooks")
async def create_webhook(name: str, url: str, events: str, user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    import secrets
    _, member = user_org
    event_list = [e.strip() for e in events.split(",") if e.strip()]
    wh = Webhook(org_id=member.org_id, name=name, url=url, events=event_list, secret=secrets.token_hex(32))
    db.add(wh)
    await db.flush()
    return {"id": wh.id, "name": name, "url": url}


@router.post("/review-requests")
async def create_review_request(
    recipient_email: str, product_title: str, send_after_days: int = 7,
    user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    _, member = user_org
    req = ReviewRequest(
        org_id=member.org_id,
        recipient_email=recipient_email,
        send_after=datetime.now(timezone.utc) + timedelta(days=send_after_days),
    )
    db.add(req)
    return {"message": "Review request scheduled", "id": req.id}


@router.get("/analytics")
async def get_analytics(user_org=Depends(require_active_subscription), db: AsyncSession = Depends(get_db)):
    _, member = user_org
    total = await db.execute(select(func.count(Review.id)).where(Review.org_id == member.org_id))
    pending = await db.execute(select(func.count(Review.id)).where(Review.org_id == member.org_id, Review.reply_status == "pending"))
    published = await db.execute(select(func.count(Review.id)).where(Review.org_id == member.org_id, Review.reply_status == "published"))
    positive = await db.execute(select(func.count(Review.id)).where(Review.org_id == member.org_id, Review.sentiment == "positive"))
    negative = await db.execute(select(func.count(Review.id)).where(Review.org_id == member.org_id, Review.sentiment == "negative"))
    flagged = await db.execute(select(func.count(Review.id)).where(Review.org_id == member.org_id, Review.is_flagged == True))

    platform_result = await db.execute(
        select(Review.platform, func.count(Review.id)).where(Review.org_id == member.org_id).group_by(Review.platform)
    )
    by_platform = {row[0] or "unknown": row[1] for row in platform_result.all()}

    rating_result = await db.execute(
        select(Review.rating, func.count(Review.id)).where(Review.org_id == member.org_id).group_by(Review.rating)
    )
    by_rating = {row[0]: row[1] for row in rating_result.all()}

    total_count = total.scalar() or 0
    pending_count = pending.scalar() or 0
    published_count = published.scalar() or 0
    positive_count = positive.scalar() or 0
    negative_count = negative.scalar() or 0
    flagged_count = flagged.scalar() or 0

    return {
        "total_reviews": total_count,
        "pending_replies": pending_count,
        "published_replies": published_count,
        "positive": positive_count,
        "negative": negative_count,
        "flagged": flagged_count,
        "reply_rate": round(published_count / max(total_count, 1) * 100, 1),
        "by_platform": by_platform,
        "by_rating": by_rating,
    }
