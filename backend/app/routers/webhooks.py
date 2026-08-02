import json
import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_scope
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.webhook import WEBHOOK_EVENTS, WebhookDelivery, WebhookEndpoint
from app.services.audit_service import log_audit_event
from app.utils.ssrf_guard import validate_ssrf_url
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

_MAX_WEBHOOKS_PER_USER = 20


def _ep_response(ep: WebhookEndpoint, include_secret: bool = False) -> dict:
    d = {
        "id": str(ep.id),
        "url": ep.url,
        "description": ep.description,
        "events": ep.events,
        "is_active": ep.is_active,
        "created_at": ep.created_at.isoformat() if ep.created_at else None,
        "updated_at": ep.updated_at.isoformat() if ep.updated_at else None,
    }
    if include_secret:
        d["secret"] = ep.secret
    return d


def _validate_url(url: str) -> str:
    """Validate URL format and enforce SSRF protection."""
    return validate_ssrf_url(url)


def _validate_events(events) -> list:
    if not isinstance(events, list) or not events:
        raise HTTPException(status_code=422, detail="events must be a non-empty list")
    invalid = [e for e in events if e not in WEBHOOK_EVENTS]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event types: {sorted(invalid)}. Allowed: {sorted(WEBHOOK_EVENTS)}",
        )
    return events


async def _get_user_webhook(webhook_id: str, user: dict, db: AsyncSession) -> WebhookEndpoint:
    try:
        wh_uuid = uuid.UUID(webhook_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Webhook not found")

    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == wh_uuid,
            WebhookEndpoint.user_id == uuid.UUID(user["user_id"]),
        )
    )
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return ep


@router.post("", status_code=201)
@limiter.limit("10/minute")
async def create_webhook(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("webhooks:write")),
):
    """
    Register a webhook endpoint.  The secret is returned exactly once in this
    response — store it securely.  Subsequent GET requests omit the secret.
    """
    url = _validate_url(body.get("url", ""))
    events = _validate_events(body.get("events", []))
    description = body.get("description")
    if description and len(description) > 255:
        raise HTTPException(status_code=422, detail="description must be <= 255 characters")

    # Enforce per-user webhook endpoint cap
    existing_count_result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.user_id == uuid.UUID(user["user_id"]))
    )
    existing_count = len(existing_count_result.scalars().all())
    if existing_count >= _MAX_WEBHOOKS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"Maximum {_MAX_WEBHOOKS_PER_USER} webhook endpoints per user",
        )

    ep = WebhookEndpoint(
        user_id=uuid.UUID(user["user_id"]),
        url=url,
        secret=secrets.token_hex(32),
        description=description,
        is_active=True,
    )
    ep.events = events
    db.add(ep)
    await db.flush()

    await log_audit_event(
        db,
        event_type="webhook.created",
        actor_user_id=user["user_id"],
        target_type="webhook",
        target_id=str(ep.id),
        details={"url": ep.url, "events": events},
    )

    await db.commit()
    await db.refresh(ep)
    return _ep_response(ep, include_secret=True)


@router.get("")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("webhooks:read")),
):
    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.user_id == uuid.UUID(user["user_id"]))
        .order_by(WebhookEndpoint.created_at.desc())
    )
    return {"webhooks": [_ep_response(ep) for ep in result.scalars().all()]}


@router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("webhooks:read")),
):
    ep = await _get_user_webhook(webhook_id, user, db)
    return _ep_response(ep)


@router.patch("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("webhooks:write")),
):
    ep = await _get_user_webhook(webhook_id, user, db)

    if "url" in body:
        ep.url = _validate_url(body["url"])
    if "events" in body:
        ep.events = _validate_events(body["events"])
    if "description" in body:
        desc = body["description"]
        if desc and len(desc) > 255:
            raise HTTPException(status_code=422, detail="description must be <= 255 characters")
        ep.description = desc
    if "is_active" in body:
        ep.is_active = bool(body["is_active"])

    # SQLAlchemy won't auto-update updated_at for in-place JSON property change,
    # so touch it explicitly.
    ep.updated_at = datetime.now(timezone.utc)

    await log_audit_event(
        db,
        event_type="webhook.updated",
        actor_user_id=user["user_id"],
        target_type="webhook",
        target_id=str(ep.id),
        details={"changed": sorted(body.keys())},
    )

    await db.commit()
    await db.refresh(ep)
    return _ep_response(ep)


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("webhooks:write")),
):
    ep = await _get_user_webhook(webhook_id, user, db)
    ep_id, ep_url = str(ep.id), ep.url
    await db.delete(ep)

    await log_audit_event(
        db,
        event_type="webhook.deleted",
        actor_user_id=user["user_id"],
        target_type="webhook",
        target_id=ep_id,
        details={"url": ep_url},
    )

    await db.commit()


@router.get("/{webhook_id}/deliveries")
async def get_deliveries(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("webhooks:read")),
):
    ep = await _get_user_webhook(webhook_id, user, db)
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == ep.id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    deliveries = result.scalars().all()
    return {
        "deliveries": [
            {
                "id": str(d.id),
                "event_type": d.event_type,
                "status": d.status,
                "attempts": d.attempts,
                "response_status": d.response_status,
                "last_attempt_at": (
                    d.last_attempt_at.isoformat() if d.last_attempt_at else None
                ),
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in deliveries
        ]
    }


@router.post("/{webhook_id}/test", status_code=202)
@limiter.limit("5/minute")
async def test_webhook(
    request: Request,
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("webhooks:write")),
):
    """Send a test ping delivery to verify the endpoint URL is reachable."""
    ep = await _get_user_webhook(webhook_id, user, db)

    delivery_id = uuid.uuid4()
    payload = {
        "id": str(delivery_id),
        "event": "ping",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": {"test": True, "message": "SecureDoc webhook verification ping"},
    }
    delivery = WebhookDelivery(
        id=delivery_id,
        webhook_id=ep.id,
        event_type="ping",
        payload_json=json.dumps(payload),
        status="pending",
    )
    db.add(delivery)
    await db.commit()

    try:
        celery_app.send_task(
            "securedoc.deliver_webhook",
            args=[str(ep.id), str(delivery_id)],
        )
    except Exception:
        # Non-fatal — the delivery record already exists and will show as
        # pending/stuck, but log it: a broker-dispatch failure here would
        # otherwise be completely invisible.
        logger.error("webhooks: failed to dispatch test delivery %s for webhook %s", delivery_id, ep.id, exc_info=True)

    return {"delivery_id": str(delivery_id), "status": "queued"}
