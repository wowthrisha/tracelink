from slowapi import Limiter
from starlette.requests import Request


def _get_real_client_ip(request: Request) -> str:
    """Return real client IP set by TrustedProxyMiddleware, falling back to direct host."""
    ip = getattr(request.state, "client_ip", None)
    if ip:
        return ip
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=_get_real_client_ip)
