import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware.rate_limit import limiter
from app.routers import documents, links, viewer, analytics, groups
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

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


@app.get("/health")
async def health():
    return {"status": "ok"}

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
