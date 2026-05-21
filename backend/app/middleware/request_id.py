"""
Request correlation ID middleware.

Reads X-Request-ID from incoming request (forwarded by Cloudflare/CDN)
or generates a UUID4 if absent.  Stored on request.state.request_id and
echoed in the response header.  Logs sanitized access line per request.

Token-like path segments (20+ chars alphanumeric) are redacted in logs.
"""
import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"/[A-Za-z0-9_\-]{20,}(?=/|$|\?)")


def _sanitize_path(path: str) -> str:
    return _TOKEN_RE.sub("/[token]", path)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        t0 = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "access method=%s path=%s status=%d ms=%.1f req_id=%s",
            request.method,
            _sanitize_path(request.url.path),
            response.status_code,
            ms,
            request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response
