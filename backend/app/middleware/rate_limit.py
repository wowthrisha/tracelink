from slowapi import Limiter
from starlette.requests import Request
from app.config import settings


def _get_real_client_ip(request: Request) -> str:
    """Return real client IP set by TrustedProxyMiddleware, falling back to direct host."""
    ip = getattr(request.state, "client_ip", None)
    if ip:
        return ip
    return request.client.host if request.client else "127.0.0.1"


# Use Redis-backed storage in production so rate limits are globally enforced
# across all api replicas, not per-process.  In development/test, fall back to
# the default in-memory store to avoid a Redis dependency during local iteration.
_storage_uri = settings.redis_url if settings.app_env == "production" else None

limiter = Limiter(key_func=_get_real_client_ip, storage_uri=_storage_uri)
