import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Annotated, Optional

import httpx
import jwt
from fastapi import Depends, Header, HTTPException
from jwt.algorithms import ECAlgorithm

from app.config import settings

logger = logging.getLogger(__name__)
_jwks_cache: dict = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 3600

async def _fetch_jwks():
    global _jwks_fetched_at
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    _jwks_cache.clear()
    for jwk in data.get("keys", []):
        kid = jwk.get("kid", "default")
        _jwks_cache[kid] = ECAlgorithm.from_jwk(jwk)
    _jwks_fetched_at = time.time()
    logger.info("JWKS loaded: %d key(s)", len(_jwks_cache))

async def _get_public_key(kid: Optional[str]):
    if not _jwks_cache or time.time() - _jwks_fetched_at > _JWKS_TTL:
        await _fetch_jwks()
    if kid and kid in _jwks_cache:
        return _jwks_cache[kid]
    if len(_jwks_cache) == 1:
        return next(iter(_jwks_cache.values()))
    raise HTTPException(status_code=401, detail="Authentication failed")

async def verify_supabase_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Authentication failed")

    alg = header.get("alg", "ES256")
    if alg not in ("ES256", "RS256"):
        raise HTTPException(status_code=401, detail="Authentication failed")

    public_key = await _get_public_key(header.get("kid"))

    try:
        payload = jwt.decode(token, public_key, algorithms=[alg], audience="authenticated")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please sign in again.")
    except jwt.InvalidTokenError:
        # Try once more after refreshing JWKS (handles key rotation)
        await _fetch_jwks()
        try:
            public_key = await _get_public_key(header.get("kid"))
            payload = jwt.decode(token, public_key, algorithms=[alg], audience="authenticated")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Authentication failed")

    return {
        "user_id": payload["sub"],
        "email": payload.get("email", ""),
        "role": payload.get("role", "authenticated"),
        "scopes": [],
        "auth_method": "jwt",
    }


async def verify_api_key(raw_key: str) -> dict:
    """Validate an API key and return the same user dict shape as JWT auth."""
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    from sqlalchemy import select
    from app.models.api_key import APIKey
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active.is_(True),
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise HTTPException(status_code=401, detail="Authentication failed")

        now = datetime.now(timezone.utc)
        if api_key.expires_at:
            expires = api_key.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < now:
                raise HTTPException(status_code=401, detail="API key expired")

        scopes = json.loads(api_key.scopes_json) if api_key.scopes_json else []
        user_id = str(api_key.user_id)

        # Update last_used_at inline (single UPDATE, negligible overhead)
        try:
            api_key.last_used_at = now
            await db.commit()
        except Exception:
            pass  # Non-critical; don't fail the request

    return {
        "user_id": user_id,
        "email": "",
        "role": "authenticated",
        "scopes": scopes,
        "auth_method": "api_key",
    }


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
) -> dict:
    # X-API-Key header takes priority
    if x_api_key and x_api_key.startswith("sd_"):
        return await verify_api_key(x_api_key)

    # Bearer sd_... (API key via Authorization header)
    if authorization:
        parts = authorization.split(" ", 1)
        if (
            len(parts) == 2
            and parts[0].lower() == "bearer"
            and parts[1].startswith("sd_")
        ):
            return await verify_api_key(parts[1])

    # Standard JWT Bearer
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Must be: Bearer <token>")
    return await verify_supabase_token(parts[1])

def require_scope(scope: str):
    """
    FastAPI dependency factory that enforces API key scope.

    When a JWT user calls the route, all scopes are allowed (JWT = owner-level).
    When an API key user calls the route, the key MUST include the required scope.

    Usage:
        user: dict = Depends(require_scope("documents:write"))

    Raises 403 with a structured denial log entry when the scope is missing.
    """
    import logging as _logging
    _log = _logging.getLogger("securedoc.scope")

    async def _check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("auth_method") == "api_key":
            scopes = user.get("scopes", [])
            if scope not in scopes:
                _log.warning(
                    "scope_denied user_id=%s scope_required=%r scopes_present=%r",
                    user.get("user_id"), scope, scopes,
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"API key missing required scope: {scope}",
                )
        return user

    return _check
