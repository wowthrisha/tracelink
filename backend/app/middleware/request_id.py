"""
Request correlation ID middleware.

Reads X-Request-ID from incoming request (forwarded by Cloudflare/CDN)
or generates a UUID4 if absent.  Stored on request.state.request_id and
echoed in the response header.  Emits a structured access log record per
request, compatible with JSON and plaintext formatters.

Token-like path segments (20+ chars alphanumeric) are redacted in logs
to prevent accidental share-link token exposure in log aggregators.
"""
import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("securedoc.access")

_TOKEN_RE = re.compile(r"/[A-Za-z0-9_\-]{20,}(?=/|$|\?)")


def _sanitize_path(path: str) -> str:
    """Replace token-like path segments with [token] to avoid log leakage."""
    return _TOKEN_RE.sub("/[token]", path)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign or forward a request/correlation ID and emit a structured access log."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # X-Correlation-ID is set by upstream callers (API gateways, client SDKs).
        # When absent, default to the request ID so every log line has a trace anchor.
        correlation_id = request.headers.get("X-Correlation-ID") or request_id
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - t0) * 1000

        client_ip = getattr(request.state, "client_ip", None) or (
            request.client.host if request.client else "-"
        )
        sanitized_path = _sanitize_path(request.url.path)

        logger.info(
            "access method=%s path=%s status=%d ms=%.1f ip=%s req_id=%s corr_id=%s",
            request.method,
            sanitized_path,
            response.status_code,
            duration_ms,
            client_ip,
            request_id,
            correlation_id,
            extra={
                "method": request.method,
                "path": sanitized_path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 1),
                "ip": client_ip,
                "request_id": request_id,
                "correlation_id": correlation_id,
                "event": "http_request",
            },
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response
