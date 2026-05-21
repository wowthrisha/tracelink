"""
Security headers middleware for production hardening.

Uses dict.get + conditional set so route-level headers (viewer Cache-Control,
X-Content-Type-Options) are not overridden.

CSP tuned for SecureDoc:
  - React 18 from unpkg CDN
  - Google Fonts
  - Supabase auth API
  - Blob URLs for in-browser page image rendering
  - No unsafe-eval; no inline scripts (inline script moved to api.js)
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

_SECURITY_HEADERS: dict = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Content-Security-Policy": _CSP,
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            if key not in response.headers:
                response.headers[key] = value
        # Static asset cache headers
        path = request.url.path
        if path.startswith("/static/"):
            if path.endswith(".html"):
                response.headers["Cache-Control"] = "no-cache, must-revalidate"
            elif path.endswith(".js") or path.endswith(".css"):
                response.headers["Cache-Control"] = "public, max-age=3600"
                if "Vary" not in response.headers:
                    response.headers["Vary"] = "Accept-Encoding"
        return response
