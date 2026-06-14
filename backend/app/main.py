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
from app.middleware.metrics import PrometheusMiddleware
from app.routers import documents, links, viewer, analytics, groups, billing, webhooks, api_keys, orgs, admin, notifications, auth as auth_router
from app.auth import _fetch_jwks

_IP_SALT_DEFAULT = "securedoc_ip_salt_change_in_production"
_DOMAIN_SALT_DEFAULT = "securedoc_domain_salt_change_in_production"

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
    if settings.domain_verify_salt == _DOMAIN_SALT_DEFAULT:
        _errors.append(
            "  DOMAIN_VERIFY_SALT is still set to the default placeholder value "
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
    if settings.hsts_max_age == 0:
        _errors.append(
            "  HSTS_MAX_AGE is 0 (disabled). "
            "Set HSTS_MAX_AGE=31536000 to enable HSTS. "
            "Without HSTS, browsers can be downgraded to HTTP via MITM attacks. "
            "The header is only sent over HTTPS so this is safe to enable now."
        )
    if _errors:
        raise RuntimeError(
            "Refusing to start in production with unsafe configuration:\n"
            + "\n".join(_errors)
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log = logging.getLogger("securedoc.startup")

    # Configure JSON logging before any log output
    if settings.enable_json_logging:
        from app.middleware.json_logging import configure_json_logging
        configure_json_logging()
        _log.info("LOGGING: JSON structured logging enabled")

    # OpenTelemetry tracing (no-op when endpoint not configured)
    from app.telemetry import setup_tracing, instrument_app
    setup_tracing(settings.otel_exporter_otlp_endpoint, settings.otel_service_name)
    instrument_app(app)

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

    # Warn loudly in dev mode about missing critical config so operators get
    # immediate feedback instead of a silent 401 blackout on every request.
    if not settings.supabase_url:
        _log.error(
            "AUTH: SUPABASE_URL is not set — every authenticated API call will return 401. "
            "Set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file."
        )
    if not settings.supabase_anon_key:
        _log.error(
            "AUTH: SUPABASE_ANON_KEY is not set — the frontend login form will fail. "
            "Set SUPABASE_ANON_KEY in your .env file."
        )
    _storage_creds_are_test = (
        settings.storage_access_key_id in ("test_key", "")
        or settings.storage_secret_access_key in ("test_secret", "")
    )
    if _storage_creds_are_test and os.getenv("USE_DEMO_STORAGE") != "1":
        _log.error(
            "STORAGE: storage_access_key_id / storage_secret_access_key are still set to "
            "test/default values — uploads will fail with storage errors. "
            "Set real credentials in .env or set USE_DEMO_STORAGE=1 for local testing."
        )

    # Preload Supabase JWKS public keys
    if settings.supabase_url:
        try:
            await _fetch_jwks()
            _log.info("AUTH: JWKS loaded from %s", settings.supabase_url)
        except Exception as e:
            _log.warning("AUTH: JWKS preload failed (will retry on first request): %s", e)
    else:
        _log.warning("AUTH: Skipping JWKS preload — SUPABASE_URL not configured")

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

# Prometheus — must be innermost of the non-route middleware so it sees
# the real request after proxy headers are resolved.
app.add_middleware(PrometheusMiddleware)

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
app.include_router(auth_router.router)
app.include_router(documents.router)
app.include_router(links.router)
app.include_router(viewer.router)
app.include_router(analytics.router)
app.include_router(groups.router)
app.include_router(billing.router)
app.include_router(webhooks.router)
app.include_router(api_keys.router)
app.include_router(orgs.router)
app.include_router(admin.router)
app.include_router(notifications.router)


@app.get("/metrics", include_in_schema=False)
async def metrics(request: Request):
    """
    Prometheus metrics endpoint.

    Protected by:
      1. METRICS_TOKEN bearer token (when configured)
      2. METRICS_ALLOWED_IPS IP allowlist (default: 127.0.0.1, ::1)

    When neither is configured (blank token + empty allowed IPs), the endpoint
    is accessible by anyone — suitable only for isolated internal deployments.
    """
    import ipaddress as _ipaddress

    client_ip = getattr(request.state, "client_ip", None) or (
        request.client.host if request.client else "unknown"
    )

    # Token check (takes priority over IP allowlist)
    if settings.metrics_token:
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != settings.metrics_token:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    elif settings.metrics_allowed_ips:
        # IP allowlist check — supports individual IPs and CIDR ranges
        allowed = False
        for entry in settings.metrics_allowed_ips.split(","):
            entry = entry.strip()
            if not entry:
                continue
            try:
                if "/" in entry:
                    if _ipaddress.ip_address(client_ip) in _ipaddress.ip_network(entry, strict=False):
                        allowed = True
                        break
                else:
                    if client_ip == entry:
                        allowed = True
                        break
            except ValueError:
                continue
        if not allowed:
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})

    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response as _Response
    from app.metrics import active_sessions
    from app.services.viewer_cache import session_cache
    active_sessions.set(len(session_cache._data))
    return _Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
        headers={"Cache-Control": "no-store"},
    )


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

    # Auth — check Supabase URL is configured (no network call; just config presence)
    checks["auth_configured"] = bool(settings.supabase_url and settings.supabase_anon_key)
    if not checks["auth_configured"]:
        overall = "degraded"

    # Storage credentials — flag test defaults
    _test_creds = (
        settings.storage_access_key_id in ("test_key", "")
        or settings.storage_secret_access_key in ("test_secret", "")
    )
    checks["storage_credentials"] = "test_defaults" if _test_creds else "configured"
    if _test_creds and os.getenv("USE_DEMO_STORAGE") != "1":
        overall = "degraded"

    return {"status": overall, "checks": checks, "version": "8.1.0"}


@app.get("/api/diagnostics", include_in_schema=False)
async def diagnostics():
    """
    Operator diagnostics endpoint — returns configuration status without
    exposing secret values.  Accessible without auth so operators can check
    config before auth is working.  Never returns actual key/secret values.
    """
    _test_creds = (
        settings.storage_access_key_id in ("test_key", "")
        or settings.storage_secret_access_key in ("test_secret", "")
    )
    _demo_storage = os.getenv("USE_DEMO_STORAGE") == "1"

    issues = []
    if not settings.supabase_url:
        issues.append("SUPABASE_URL not set — all authenticated API calls will return 401")
    if not settings.supabase_anon_key:
        issues.append("SUPABASE_ANON_KEY not set — frontend login will fail")
    if _test_creds and not _demo_storage:
        issues.append(
            "Storage credentials are test defaults — uploads will fail. "
            "Set STORAGE_ACCESS_KEY_ID and STORAGE_SECRET_ACCESS_KEY, or USE_DEMO_STORAGE=1"
        )
    if not settings.redis_url or settings.redis_url == "redis://localhost:6379/0":
        issues.append("REDIS_URL appears to be default — Celery workers may not connect in production")

    return {
        "status": "ready" if not issues else "misconfigured",
        "issues": issues,
        "config": {
            "supabase_url_set": bool(settings.supabase_url),
            "supabase_anon_key_set": bool(settings.supabase_anon_key),
            "storage_credentials": "test_defaults" if _test_creds else "configured",
            "demo_storage_mode": _demo_storage,
            "app_env": settings.app_env,
            "app_public_base_url": settings.app_public_base_url,
        },
    }


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

    # Cache-bust the bundle URL so browsers pick up new deploys immediately.
    # Hash is based on the bundle file's mtime — changes on every deploy.
    bundle_path = os.path.join(frontend_dir, "dist", "app.bundle.js")
    try:
        bundle_mtime = int(os.path.getmtime(bundle_path))
    except OSError:
        bundle_mtime = 0
    content = content.replace(
        'src="/static/dist/app.bundle.js"',
        f'src="/static/dist/app.bundle.js?v={bundle_mtime}"',
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
