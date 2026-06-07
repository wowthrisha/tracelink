"""
Security headers middleware for production hardening.

Uses dict.setdefault so route-level headers (viewer Cache-Control,
X-Content-Type-Options) are not overridden.

CSP tuned for SecureDoc:
  - React 18.3.1 from unpkg CDN — allowlisted by exact SHA-384 content hash,
    not by domain.  A CDN-compromise delivering different bytes is blocked.
  - Google Fonts
  - Supabase auth API
  - Blob URLs for in-browser page image rendering
  - No unsafe-eval; no inline scripts (inline script moved to api.js)

HSTS (opt-in via HSTS_MAX_AGE > 0 in config):
  Enable once HTTPS is confirmed stable on your domain.
  Set to 31536000 (1 year) for production.

Cross-origin hardening:
  - Cross-Origin-Opener-Policy: same-origin (Spectre isolation)
  - X-Permitted-Cross-Domain-Policies: none (Flash/PDF cross-domain block)
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# SHA-384 content hashes for React 18.3.1 UMD production builds loaded from unpkg.
# These are the exact hashes from the <script integrity="..."> attributes in SecureDoc.html.
# Any CDN-delivered script with a different content hash will be blocked by CSP,
# even if it comes from the same domain.
_REACT_HASH = "sha384-DGyLxAyjq0f9SPpVevD6IgztCFlnMF6oW/XQGmfe+IsZ8TqEiDrcHkMLKI6fiB/Z"
_REACT_DOM_HASH = "sha384-gTGxhz21lVGYNMcdJOyq01Edg0jhn/c22nsx0kyqP0TxaV5WVdsSH1fSDUf5YJj1"

_CSP = (
    "default-src 'none'; "
    f"script-src 'self' '{_REACT_HASH}' '{_REACT_DOM_HASH}'; "
    "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "connect-src 'self' https://*.supabase.co; "
    "img-src 'self' blob: data:; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

_BASE_SECURITY_HEADERS: dict = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Content-Security-Policy": _CSP,
    "Cross-Origin-Opener-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, hsts_max_age: int = 0, static_asset_max_age: int = 3600):
        super().__init__(app)
        self._hsts_max_age = hsts_max_age
        self._static_asset_max_age = static_asset_max_age

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for key, value in _BASE_SECURITY_HEADERS.items():
            if key not in response.headers:
                response.headers[key] = value

        # HSTS — only inject when configured (>0) and request was HTTPS.
        # Checking X-Forwarded-Proto ensures we don't set HSTS on plain-HTTP
        # responses to Cloudflare/proxy health checks.
        if self._hsts_max_age > 0:
            proto = request.headers.get("x-forwarded-proto", "").lower().split(",")[0].strip()
            is_https = (request.url.scheme == "https") or (proto == "https")
            if is_https and "Strict-Transport-Security" not in response.headers:
                response.headers["Strict-Transport-Security"] = (
                    f"max-age={self._hsts_max_age}; includeSubDomains; preload"
                )

        # Static asset cache headers
        path = request.url.path
        if path.startswith("/static/"):
            if path.endswith(".html"):
                response.headers["Cache-Control"] = "no-cache, must-revalidate"
            elif path.endswith(".js") or path.endswith(".css"):
                max_age = self._static_asset_max_age
                response.headers["Cache-Control"] = (
                    f"public, max-age={max_age}, stale-while-revalidate=60"
                )
                if "Vary" not in response.headers:
                    response.headers["Vary"] = "Accept-Encoding"

        return response
