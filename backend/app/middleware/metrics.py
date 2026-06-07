"""
Prometheus middleware — records HTTP request counts and latencies.

Placed as the outermost application middleware (after CORS, before TrustedProxy)
so it measures wall-clock time from first byte received to last byte sent.

Path normalization via app.metrics.normalize_path() prevents label cardinality
explosion from unique tokens, UUIDs, and page numbers.
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics import http_requests_total, http_request_duration_seconds, normalize_path


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path_pattern = normalize_path(request.url.path)
        method = request.method
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            status_code = "500"
            raise
        finally:
            duration = time.perf_counter() - start
            http_requests_total.labels(
                method=method,
                path_pattern=path_pattern,
                status_code=status_code,
            ).inc()
            http_request_duration_seconds.labels(
                method=method,
                path_pattern=path_pattern,
            ).observe(duration)

        return response
