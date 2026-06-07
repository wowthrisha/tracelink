import json
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_CHANNEL_PREFIX = "securedoc:notifications:user:"
_MAX_PAYLOAD_BYTES = 4096


def _user_channel(user_id: str) -> str:
    return f"{_CHANNEL_PREFIX}{user_id}"


async def publish_notification(user_id: str, event_type: str, data: dict) -> bool:
    """
    Publish a notification to the per-user Redis channel.

    Returns True if published, False if Redis unavailable.
    Never raises — callers must not fail if notifications are unavailable.
    """
    try:
        from app.services.page_cache import get_redis_page_cache
        rc = get_redis_page_cache()
        if rc is None:
            return False

        payload = json.dumps(
            {
                "id": str(uuid.uuid4()),
                "event": event_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "data": data,
            },
            default=str,
        )
        if len(payload.encode()) > _MAX_PAYLOAD_BYTES:
            logger.warning(
                "notification_service: payload for %s exceeds %d bytes — truncating data",
                event_type, _MAX_PAYLOAD_BYTES,
            )
            return False

        channel = _user_channel(user_id)
        await rc._r.publish(channel, payload)
        return True

    except Exception as exc:
        logger.debug("notification_service: publish failed for user %s: %s", user_id, exc)
        return False
