"""
Safe client IP extraction when running behind a reverse proxy (Cloudflare, etc.).

Stores the resolved IP on request.state.client_ip for use by:
  - Rate limiter key_func
  - Analytics IP hashing
  - IP allowlist enforcement

Strategies (controlled by config):
  real_ip_header      — read a single trusted header (e.g. "CF-Connecting-IP")
  trusted_proxy_depth — rightmost-N from X-Forwarded-For (N=1 = one proxy hop)
  default             — use request.client.host directly (no proxy trust)
"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class TrustedProxyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, real_ip_header: str = "", trusted_proxy_depth: int = 0):
        super().__init__(app)
        self._header = real_ip_header.strip()
        self._depth = max(0, int(trusted_proxy_depth))

    async def dispatch(self, request: Request, call_next):
        request.state.client_ip = self._resolve(request)
        return await call_next(request)

    def _resolve(self, request: Request):
        if self._header:
            val = request.headers.get(self._header, "").strip()
            if val:
                return val.split(",")[0].strip()

        if self._depth > 0:
            xff = request.headers.get("X-Forwarded-For", "").strip()
            if xff:
                parts = [p.strip() for p in xff.split(",") if p.strip()]
                # depth=N means N trusted proxy hops appended to the right.
                # The real client IP is at index len(parts) - depth - 1.
                idx = len(parts) - self._depth - 1
                if 0 <= idx < len(parts):
                    return parts[idx]

        return request.client.host if request.client else None
