import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.auth import require_scope
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

logger = logging.getLogger(__name__)

_PING_INTERVAL = 15        # seconds between keepalive pings
_IDLE_TIMEOUT = 300        # close connection if no message for 5 minutes
_CHANNEL_PREFIX = "securedoc:notifications:user:"
_MAX_CONNECTIONS_PER_USER = 5  # protect against runaway SSE clients

# Process-local connection counter (per-process; acceptable for rate limiting)
_active_connections: dict[str, int] = {}


@router.get("/stream")
@limiter.limit("10/minute")
async def notification_stream(
    request: Request,
    user: dict = Depends(require_scope("documents:read")),
):
    """
    Server-Sent Events stream for real-time notifications.

    Events are published to a per-user Redis pub/sub channel when:
    - A share link is viewed (event: link.viewed)
    - A document finishes processing (event: document.processed)

    When Redis is unavailable, the stream sends only keepalive pings.
    """
    user_id = user["user_id"]

    # Enforce per-user connection limit before creating the stream
    current = _active_connections.get(user_id, 0)
    if current >= _MAX_CONNECTIONS_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"Maximum {_MAX_CONNECTIONS_PER_USER} concurrent SSE connections per user",
        )

    return StreamingResponse(
        _event_generator(request, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _event_generator(request: Request, user_id: str) -> AsyncGenerator[str, None]:
    channel = f"{_CHANNEL_PREFIX}{user_id}"
    pubsub = None

    # Acquire connection slot
    _active_connections[user_id] = _active_connections.get(user_id, 0) + 1
    logger.debug("SSE: user %s connected (active=%d)", user_id, _active_connections[user_id])

    try:
        from app.services.page_cache import get_redis_page_cache
        rc = get_redis_page_cache()
        if rc is not None:
            pubsub = rc._r.pubsub()
            await pubsub.subscribe(channel)
    except Exception as exc:
        logger.debug("SSE: could not subscribe to Redis for user %s: %s", user_id, exc)
        pubsub = None

    try:
        # Announce connection
        yield "event: connected\ndata: {}\n\n"

        idle_since = asyncio.get_event_loop().time()

        while True:
            if await request.is_disconnected():
                break

            # Idle timeout: close connection if no real message for _IDLE_TIMEOUT seconds
            if asyncio.get_event_loop().time() - idle_since > _IDLE_TIMEOUT:
                yield "event: timeout\ndata: {}\n\n"
                break

            if pubsub is not None:
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1),
                        timeout=1.0,
                    )
                    if message and message.get("type") == "message":
                        idle_since = asyncio.get_event_loop().time()
                        raw = message["data"]
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8")
                        try:
                            parsed = json.loads(raw)
                            event_type = parsed.get("event", "message")
                            event_id = parsed.get("id", "")
                            data = json.dumps(parsed.get("data", {}))
                            yield f"id: {event_id}\nevent: {event_type}\ndata: {data}\n\n"
                        except (json.JSONDecodeError, KeyError):
                            pass
                        continue
                except (asyncio.TimeoutError, Exception):
                    pass

            # Keepalive ping
            await asyncio.sleep(_PING_INTERVAL)
            if await request.is_disconnected():
                break
            yield ": ping\n\n"

    finally:
        # Release connection slot
        _active_connections[user_id] = max(0, _active_connections.get(user_id, 0) - 1)
        logger.debug("SSE: user %s disconnected (active=%d)", user_id, _active_connections.get(user_id, 0))
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass
