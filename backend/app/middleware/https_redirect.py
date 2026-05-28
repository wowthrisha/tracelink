"""
Proxy-aware HTTPS redirect middleware.

Unlike Starlette's built-in HTTPSRedirectMiddleware (which inspects the
direct TCP connection), this middleware reads the X-Forwarded-Proto header
set by the upstream proxy/CDN (Cloudflare, Railway, nginx).  This is the
correct approach when the app always receives plain HTTP from the proxy but
the original client connection was HTTPS.

Activation:
  Set HTTPS_REDIRECT=true in .env.  Leave False during development.

Exclusions:
  /health — health-checks from load-balancers must always reach the app.
  WebSocket upgrade requests — not yet redirected (safe default).

Security note:
  Only enable this when ALL traffic must come through a TLS-terminating proxy.
  If direct HTTP access to the host is possible (no forced-TLS at the proxy),
  the redirect is meaningful.  If the proxy already blocks HTTP (Cloudflare
  "Always Use HTTPS" rule), this middleware adds defence-in-depth.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse


_EXCLUDED_PATHS = {"/health"}


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP requests to HTTPS by checking X-Forwarded-Proto."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        # Check what protocol the *client* used (as reported by the proxy).
        proto = request.headers.get("x-forwarded-proto", "").lower().split(",")[0].strip()
        if proto == "http":
            url = request.url
            https_url = url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=301)

        return await call_next(request)
