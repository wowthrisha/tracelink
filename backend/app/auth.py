import logging, time
from typing import Optional
import httpx, jwt
from jwt.algorithms import ECAlgorithm
from fastapi import Depends, Header, HTTPException
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

    return {"user_id": payload["sub"], "email": payload.get("email", ""), "role": payload.get("role", "authenticated")}

async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Must be: Bearer <token>")
    return await verify_supabase_token(parts[1])

async def get_optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[dict]:
    if not authorization:
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
