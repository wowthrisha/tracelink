import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.middleware.trusted_proxy import TrustedProxyMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.routers import documents, links, viewer, analytics, groups, billing
from app.auth import _fetch_jwks

_IP_SALT_DEFAULT = "securedoc_ip_salt_change_in_production"

if settings.app_env == "production":
    _errors = []
    if not settings.supabase_url:
        _errors.append("  SUPABASE_URL is not set")
    if "localhost" in settings.app_public_base_url:
        _errors.append("  APP_PUBLIC_BASE_URL still points to localhost")
    if not settings.app_public_base_url.startswith("https://"):
        _errors.append("  APP_PUBLIC_BASE_URL must use HTTPS in production")
    if settings.ip_hash_salt == _IP_SALT_DEFAULT:
        _errors.append(
            "  IP_HASH_SALT is still set to the default placeholder value "
            "(generate with: python -c \"import secrets; print(secrets.token_hex(32))\")"
        )
    if _errors:
        raise RuntimeError(
            "Refusing to start in production with unsafe configuration:\n"
            + "\n".join(_errors)
        )
    # Non-fatal warnings for recommended production settings
    _warn_log = logging.getLogger("securedoc.startup")
    _localhost_origins = [o for o in settings.allowed_origins_list if "localhost" in o or "127.0.0.1" in o]
    if _localhost_origins:
        _warn_log.warning(
            "CORS: ALLOWED_ORIGINS includes localhost entries in production: %s",
            _localhost_origins,
        )
    if not settings.real_ip_header and settings.trusted_proxy_depth == 0:
        _warn_log.warning(
            "PROXY: Neither REAL_IP_HEADER nor TRUSTED_PROXY_DEPTH is set. "
            "IP allowlists and rate limiting will use the direct connection IP. "
            "Set REAL_IP_HEADER=CF-Connecting-IP if behind Cloudflare."
        )
    if not settings.https_redirect:
        _warn_log.warning(
            "HTTPS: HTTPS_REDIRECT is not enabled. "
            "Set HTTPS_REDIRECT=true to enforce HTTPS in production."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log = logging.getLogger("securedoc.startup")

    # Configure JSON logging before any log output
    if settings.enable_json_logging:
        from app.middleware.json_logging import configure_json_logging
        configure_json_logging()
        _log.info("LOGGING: JSON structured logging enabled")

    # Log which storage backend is active
    from app.services.storage import _storage_service
    if _storage_service is not None and type(_storage_service).__name__ == "DemoStorageService":
        _log.warning("STORAGE: demo/local-disk mode active (/tmp/securedoc_storage/)")
    elif settings.storage_endpoint_url:
        _log.info(
            "STORAGE: S3-compatible backend — %s (path_style=%s)",
            settings.storage_endpoint_url, settings.storage_path_style,
        )
    else:
        _log.info("STORAGE: AWS S3 (no custom endpoint)")

    # Log active CDN/proxy configuration for operator visibility
    if settings.https_redirect:
        _log.info("PROXY: HTTPS redirect active (checking X-Forwarded-Proto)")
    if settings.hsts_max_age > 0:
        _log.info("SECURITY: HSTS enabled max-age=%d", settings.hsts_max_age)
    if settings.real_ip_header:
        _log.info("PROXY: real_ip_header=%r", settings.real_ip_header)
    elif settings.trusted_proxy_depth > 0:
        _log.info("PROXY: trusted_proxy_depth=%d", settings.trusted_proxy_depth)

    # Preload Supabase JWKS public keys
    try:
        await _fetch_jwks()
        _log.info("AUTH: JWKS loaded from %s", settings.supabase_url)
    except Exception as e:
        _log.warning("AUTH: JWKS preload failed (will retry on first request): %s", e)

    yield  # ── application running ──

    _shutdown_log = logging.getLogger("securedoc.shutdown")
    from app.database import engine as _db_engine
    if _db_engine is not None:
        await _db_engine.dispose()
        _shutdown_log.info("DB engine disposed on shutdown")


app = FastAPI(title="SecureDoc API", version="8.1.0", lifespan=lifespan)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# HTTPS redirect — outermost middleware so it runs before any other processing.
# Only active when HTTPS_REDIRECT=true in .env.
if settings.https_redirect:
    from app.middleware.https_redirect import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    SecurityHeadersMiddleware,
    hsts_max_age=settings.hsts_max_age,
    static_asset_max_age=settings.static_asset_max_age,
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    TrustedProxyMiddleware,
    real_ip_header=settings.real_ip_header,
    trusted_proxy_depth=settings.trusted_proxy_depth,
)

# CORS
# Development: allow all origins (Bearer token auth doesn't need allow_credentials=True)
# Production:  restrict to ALLOWED_ORIGINS from .env
if settings.app_env == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

_log = logging.getLogger("securedoc")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    _log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# Routers
app.include_router(documents.router)
app.include_router(links.router)
app.include_router(viewer.router)
app.include_router(analytics.router)
app.include_router(groups.router)
app.include_router(billing.router)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.  Always returns HTTP 200 so load-balancers and
    tunnels can verify reachability.  The 'status' field is 'ok' when all
    components are healthy, 'degraded' when one or more checks fail.

    Checks: db (SELECT 1), redis (PING), storage (service instantiation), worker.

    Deliberately omits internal proxy/CDN configuration to prevent information
    disclosure that would aid header-spoofing attacks.
    """
    from sqlalchemy import text as _sql_text
    checks: dict = {}
    overall = "ok"

    # DB — uses the injected session (override-friendly in tests)
    try:
        await db.execute(_sql_text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "error"
        overall = "degraded"

    # Redis — PING the shared async client
    try:
        from app.services.page_cache import get_redis_page_cache
        _rc = get_redis_page_cache()
        if _rc is not None:
            await _rc._r.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not_configured"
    except Exception:
        checks["redis"] = "error"
        overall = "degraded"

    # Storage — just verify the service is instantiated (no remote call)
    try:
        from app.services.storage import get_storage_service
        _svc = get_storage_service()
        checks["storage"] = type(_svc).__name__
    except Exception:
        checks["storage"] = "error"
        overall = "degraded"

    # Worker — check Celery worker availability via a Redis SCAN (non-blocking).
    # KEYS is O(N) and blocks Redis; SCAN cursor-loops without blocking.
    # We check for Kombu queue bindings that workers register on startup.
    try:
        from app.services.page_cache import get_redis_page_cache
        _rc = get_redis_page_cache()
        if _rc is not None:
            _found = False
            _cursor = 0
            while True:
                _cursor, _keys = await _rc._r.scan(
                    _cursor, match="_kombu.binding.*", count=20
                )
                if _keys:
                    _found = True
                    break
                if _cursor == 0:
                    break
            checks["worker"] = "ok" if _found else "no_workers_detected"
        else:
            checks["worker"] = "redis_unavailable"
    except Exception:
        checks["worker"] = "unknown"

    return {"status": overall, "checks": checks, "version": "8.1.0"}


frontend_dir = "/frontend"  # mounted in Docker; fallback for local dev
if not os.path.exists(frontend_dir):
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/app")
async def serve_app(token: Optional[str] = None):
    """
    Serve the frontend SPA with environment-injected configuration.

    Supabase URL and anon key are read from environment variables at request
    time and injected into the HTML meta tags.  This prevents committing live
    credentials to the repository while keeping the frontend functional.
    """
    html_path = os.path.join(frontend_dir, "SecureDoc.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return JSONResponse(status_code=503, content={"detail": "Frontend not available"})

    # Replace placeholder values with environment-configured ones
    content = content.replace(
        'content="SECUREDOC_SUPABASE_URL"',
        f'content="{settings.supabase_url}"',
    ).replace(
        'content="SECUREDOC_SUPABASE_ANON_KEY"',
        f'content="{settings.supabase_anon_key}"',
    )

    return HTMLResponse(
        content=content,
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


@app.get("/v/{token}")
async def view_document(token: str):
    return RedirectResponse(url=f"/app?token={token}")


@app.get("/")
async def index():
    return RedirectResponse(url="/app")
