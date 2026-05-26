import logging
import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
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

_UNSAFE_DEFAULTS = {
    "jwt_secret": "change_me_to_a_long_random_string_in_production",
}

if settings.app_env == "production":
    _errors = []
    for _field, _placeholder in _UNSAFE_DEFAULTS.items():
        if getattr(settings, _field) == _placeholder:
            _errors.append(f"  {_field.upper()} is still set to the default placeholder value")
    if not settings.supabase_url:
        _errors.append("  SUPABASE_URL is not set")
    if "localhost" in settings.app_public_base_url:
        _errors.append("  APP_PUBLIC_BASE_URL still points to localhost")
    if "localhost" in settings.frontend_base_url:
        _errors.append("  FRONTEND_BASE_URL still points to localhost")
    if not settings.app_public_base_url.startswith("https://"):
        _errors.append("  APP_PUBLIC_BASE_URL must use HTTPS in production")
    # Warn (not block) if ALLOWED_ORIGINS still has localhost
    _localhost_origins = [o for o in settings.allowed_origins_list if "localhost" in o or "127.0.0.1" in o]
    if _localhost_origins:
        import logging as _logging
        _logging.getLogger("securedoc.startup").warning(
            "CORS: ALLOWED_ORIGINS includes localhost entries in production: %s",
            _localhost_origins,
        )
    if _errors:
        raise RuntimeError(
            "Refusing to start in production with unsafe configuration:\n"
            + "\n".join(_errors)
        )

app = FastAPI(title="SecureDoc API", version="1.0.0")


@app.on_event("startup")
async def startup():
    import logging
    _log = logging.getLogger("securedoc.startup")

    # Phase 7: switch to JSON log format in production when configured
    if settings.enable_json_logging:
        from app.middleware.json_logging import configure_json_logging
        configure_json_logging()
        _log.info("LOGGING: JSON structured logging enabled")

    # Log which storage backend is active
    from app.services.storage import _storage_service
    if _storage_service is not None and type(_storage_service).__name__ == "DemoStorageService":
        _log.warning("STORAGE: demo/local-disk mode active (/tmp/securedoc_storage/)")
    elif settings.storage_endpoint_url:
        _log.info("STORAGE: S3-compatible backend — %s", settings.storage_endpoint_url)
    else:
        _log.info("STORAGE: AWS S3 (no custom endpoint)")

    # Preload Supabase JWKS public keys
    try:
        await _fetch_jwks()
        _log.info("AUTH: JWKS loaded from %s", settings.supabase_url)
    except Exception as e:
        _log.warning("AUTH: JWKS preload failed (will retry on first request): %s", e)


@app.on_event("shutdown")
async def shutdown():
    _shutdown_log = logging.getLogger("securedoc.shutdown")
    from app.database import engine as _db_engine
    if _db_engine is not None:
        await _db_engine.dispose()
        _shutdown_log.info("DB engine disposed on shutdown")

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)
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

    Checks: db (SELECT 1), redis (PING), storage (service instantiation)
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

    # Worker — check Celery worker availability via Redis inspect
    try:
        from app.services.page_cache import get_redis_page_cache
        _rc = get_redis_page_cache()
        if _rc is not None:
            # Check for Celery worker heartbeats in Redis
            _worker_keys = await _rc._r.keys("_kombu.binding.*")
            checks["worker"] = "ok" if _worker_keys else "no_workers_detected"
        else:
            checks["worker"] = "redis_unavailable"
    except Exception:
        checks["worker"] = "unknown"

    return {"status": overall, "checks": checks, "version": "7.0.0"}

frontend_dir = "/frontend"  # mounted in Docker; fallback for local dev
if not os.path.exists(frontend_dir):
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/v/{token}")
async def view_document(token: str):
    return RedirectResponse(url=f"/static/SecureDoc.html?token={token}")

@app.get("/")
async def index():
    return RedirectResponse(url="/static/SecureDoc.html")
