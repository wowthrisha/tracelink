import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.webhook import WebhookEndpoint, WebhookDelivery, WEBHOOK_EVENTS
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def dispatch_webhook_event(
    db,
    user_id: str,
    event_type: str,
    data: dict,
) -> int:
    """
    Find active webhook endpoints for user_id subscribed to event_type,
    create delivery records, and queue Celery tasks.

    Returns the number of deliveries dispatched.
    Never raises — caller wraps in try/except to prevent webhook failure
    from breaking the primary operation.
    """
    if event_type not in WEBHOOK_EVENTS:
        logger.error("dispatch_webhook_event: unknown event type %r", event_type)
        return 0

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.error("dispatch_webhook_event: invalid user_id %r", user_id)
        return 0

    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.user_id == user_uuid,
            WebhookEndpoint.is_active.is_(True),
        )
    )
    endpoints = result.scalars().all()

    subscribed = [ep for ep in endpoints if event_type in ep.events]
    if not subscribed:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    deliveries_to_dispatch: list[tuple[uuid.UUID, uuid.UUID]] = []

    for ep in subscribed:
        delivery_id = uuid.uuid4()
        payload = {
            "id": str(delivery_id),
            "event": event_type,
            "created_at": now,
            "data": data,
        }
        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=ep.id,
            event_type=event_type,
            payload_json=json.dumps(payload, default=str),
            status="pending",
        )
        db.add(delivery)
        deliveries_to_dispatch.append((ep.id, delivery_id))

    # Commit all delivery records before queuing tasks.
    # Tasks use their own DB session and need the records to exist.
    await db.commit()

    dispatched = 0
    for ep_id, delivery_id in deliveries_to_dispatch:
        try:
            celery_app.send_task(
                "securedoc.deliver_webhook",
                args=[str(ep_id), str(delivery_id)],
            )
            dispatched += 1
        except Exception as exc:
            logger.error(
                "dispatch_webhook_event: failed to queue delivery %s: %s",
                delivery_id,
                exc,
            )

    return dispatched
