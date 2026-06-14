import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_RETRY_COUNTDOWNS = [60, 300, 1800, 10800]  # 1 min, 5 min, 30 min, 3 hours
_TIMEOUT_SECONDS = 10.0


def sign_payload(secret: str, body: bytes) -> str:
    """Return HMAC-SHA256 signature in 'sha256=<hex>' format."""
    h = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    return f"sha256={h.hexdigest()}"


def _countdown(attempt: int) -> int:
    return _RETRY_COUNTDOWNS[min(attempt, len(_RETRY_COUNTDOWNS) - 1)]


@celery_app.task(
    bind=True,
    name="securedoc.deliver_webhook",
    max_retries=4,
)
def deliver_webhook(self, webhook_id: str, delivery_id: str):
    from app.workers.tasks import _run_async
    return _run_async(_deliver_async(self, webhook_id, delivery_id))


async def _deliver_async(task, webhook_id: str, delivery_id: str):
    from sqlalchemy import select
    from app.models.webhook import WebhookEndpoint, WebhookDelivery
    from app.workers.tasks import _get_db_session_factory

    session_factory = _get_db_session_factory()

    # Load endpoint and delivery — separate query to keep session short
    async with session_factory() as db:
        ep = (
            await db.execute(
                select(WebhookEndpoint).where(
                    WebhookEndpoint.id == uuid.UUID(webhook_id)
                )
            )
        ).scalar_one_or_none()

        delivery = (
            await db.execute(
                select(WebhookDelivery).where(
                    WebhookDelivery.id == uuid.UUID(delivery_id)
                )
            )
        ).scalar_one_or_none()

        if not ep or not delivery:
            logger.warning(
                "deliver_webhook: missing endpoint=%s or delivery=%s",
                webhook_id, delivery_id,
            )
            return {"skipped": True, "reason": "not_found"}

        if not ep.is_active:
            delivery.status = "skipped"
            await db.commit()
            logger.info("deliver_webhook: endpoint %s inactive — skipped", webhook_id)
            return {"skipped": True, "reason": "inactive"}

        url = ep.url
        secret = ep.secret
        event_type = delivery.event_type
        payload_json = delivery.payload_json

    # Re-validate URL immediately before delivery to defeat DNS rebinding.
    # An attacker can register a webhook pointing at a public hostname they
    # control, pass SSRF validation at registration time, then flip the DNS
    # record to a private IP (e.g. 169.254.169.254) before Celery fires.
    # Re-checking here closes that TOCTOU window.
    try:
        from app.utils.ssrf_guard import validate_ssrf_url as _ssrf_check
        _ssrf_check(url)
    except Exception as _ssrf_exc:
        logger.warning(
            "deliver_webhook: SSRF re-validation blocked delivery url=%s "
            "delivery_id=%s: %s — marking permanent failure",
            url, delivery_id, _ssrf_exc,
        )
        session_factory2 = _get_db_session_factory()
        async with session_factory2() as _db:
            from sqlalchemy import select as _sel2
            _dlv = (
                await _db.execute(
                    _sel2(WebhookDelivery).where(WebhookDelivery.id == uuid.UUID(delivery_id))
                )
            ).scalar_one_or_none()
            if _dlv:
                _dlv.status = "failed"
                _dlv.response_body = f"SSRF re-validation blocked: {_ssrf_exc}"[:500]
                await _db.commit()
        return {"skipped": True, "reason": "ssrf_blocked"}

    # Perform HTTP delivery (outside DB session to avoid holding connection)
    body_bytes = payload_json.encode("utf-8")
    signature = sign_payload(secret, body_bytes)
    now = datetime.now(timezone.utc)

    response_status = None
    response_body = None
    success = False
    should_retry = False

    try:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            resp = client.post(
                url,
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-SecureDoc-Signature": signature,
                    "X-SecureDoc-Event": event_type,
                    "X-SecureDoc-Delivery": delivery_id,
                    "User-Agent": "SecureDoc-Webhook/1.0",
                },
            )
        response_status = resp.status_code
        response_body = (resp.text or "")[:500]
        success = 200 <= resp.status_code < 300
        # Retry on server errors and rate limiting only (not 4xx client errors)
        should_retry = not success and (resp.status_code >= 500 or resp.status_code == 429)

    except httpx.RequestError as exc:
        logger.warning("deliver_webhook: request error url=%s: %s", url, exc)
        response_body = str(exc)[:500]
        success = False
        should_retry = True

    # Persist delivery outcome
    async with session_factory() as db:
        delivery = (
            await db.execute(
                select(WebhookDelivery).where(
                    WebhookDelivery.id == uuid.UUID(delivery_id)
                )
            )
        ).scalar_one_or_none()

        if delivery:
            delivery.attempts += 1
            delivery.last_attempt_at = now
            delivery.response_status = response_status
            delivery.response_body = response_body

            if success:
                delivery.status = "success"
            elif should_retry and task.request.retries >= task.max_retries:
                delivery.status = "failed"
            elif should_retry:
                delivery.status = "pending"
            else:
                # Non-retryable client error (4xx excluding 429)
                delivery.status = "failed"

            await db.commit()

            if success:
                logger.info(
                    "deliver_webhook: success delivery=%s event=%s status=%s",
                    delivery_id, event_type, response_status,
                )
            elif delivery.status == "failed":
                logger.error(
                    "deliver_webhook: permanently failed delivery=%s event=%s "
                    "after %d attempt(s) last_status=%s",
                    delivery_id, event_type, delivery.attempts, response_status,
                )

    if should_retry and not success:
        raise task.retry(
            countdown=_countdown(task.request.retries),
            exc=Exception(f"delivery failed: HTTP {response_status}"),
        )

    return {"success": success, "response_status": response_status}
