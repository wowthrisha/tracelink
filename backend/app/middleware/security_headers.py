"""
Security headers middleware for production hardening.

Uses dict.setdefault so route-level headers (viewer Cache-Control,
X-Content-Type-Options) are not overridden.

CSP tuned for SecureDoc:
  - React 18 from unpkg CDN
  - Google Fonts
  - Supabase auth API
  - Blob URLs for in-browser page image rendering
  - No unsafe-eval; no inline scripts (inline script moved to api.js)

Phase 8 additions:
  - HSTS (opt-in via HSTS_MAX_AGE > 0 in config)
  - Cross-Origin-Opener-Policy to harden against Spectre-style attacks
  - X-Permitted-Cross-Domain-Policies to block Flash/PDF cross-domain reads
  - Configurable static asset cache lifetime
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_CSP = (
    "default-src 'none'; "
    "script-src 'self' https://unpkg.com; "
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
    # Phase 8: harden against cross-origin attacks (Spectre side-channel isolation)
    "Cross-Origin-Opener-Policy": "same-origin",
    # Phase 8: block Flash/legacy plugin cross-domain reads
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
                    f"max-age={self._hsts_max_age}; includeSubDomains"
                )

        # Static asset cache headers
        path = request.url.path
        if path.startswith("/static/"):
            if path.endswith(".html"):
                # HTML files: always revalidate (user always gets latest viewer)
                response.headers["Cache-Control"] = "no-cache, must-revalidate"
            elif path.endswith(".js") or path.endswith(".css"):
                # JS/CSS: public cache with configurable max-age + Vary for compression
                max_age = self._static_asset_max_age
                response.headers["Cache-Control"] = (
                    f"public, max-age={max_age}, stale-while-revalidate=60"
                )
                if "Vary" not in response.headers:
                    response.headers["Vary"] = "Accept-Encoding"

        return response
