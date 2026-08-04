import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_scope
from app.database import get_db
from app.models.api_key import API_SCOPES, APIKey, generate_api_key, hash_api_key

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


def _key_response(key: APIKey, full_key: Optional[str] = None) -> dict:
    d = {
        "id": str(key.id),
        "name": key.name,
        "key_prefix": key.key_prefix,
        "scopes": json.loads(key.scopes_json) if key.scopes_json else [],
        "is_active": key.is_active,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "created_at": key.created_at.isoformat() if key.created_at else None,
    }
    if full_key is not None:
        d["key"] = full_key
    return d


def _reject_scope_escalation(user: dict, requested_scopes: list) -> None:
    """An API-key caller must never be able to mint/grant a scope it doesn't itself
    hold (ENG-039) — otherwise a narrowly-scoped key could create or widen a sibling
    key into one with broader access than its own creator intended it to have.
    JWT/browser callers are unrestricted here, matching every other owner-level
    JWT behavior in this codebase (require_scope() itself only restricts
    auth_method == "api_key" callers)."""
    if user.get("auth_method") != "api_key":
        return
    own_scopes = set(user.get("scopes", []))
    excess = [s for s in requested_scopes if s not in own_scopes]
    if excess:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot grant scopes beyond your own API key's scopes: {sorted(excess)}",
        )


async def _get_user_key(key_id: str, user: dict, db: AsyncSession) -> APIKey:
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="API key not found")

    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_uuid,
            APIKey.user_id == uuid.UUID(user["user_id"]),
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return key


@router.post("", status_code=201)
async def create_api_key(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("api_keys:write")),
):
    """
    Create an API key.  The full key is returned exactly once in this response.
    Store it securely — it cannot be retrieved again.
    """
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    if len(name) > 100:
        raise HTTPException(status_code=422, detail="name must be <= 100 characters")

    scopes = body.get("scopes", [])
    if not isinstance(scopes, list):
        raise HTTPException(status_code=422, detail="scopes must be a list")
    invalid = [s for s in scopes if s not in API_SCOPES]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid scopes: {sorted(invalid)}. Allowed: {sorted(API_SCOPES)}",
        )
    _reject_scope_escalation(user, scopes)

    expires_at = None
    if body.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(body["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="expires_at must be an ISO 8601 datetime")
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=422, detail="expires_at must be in the future")

    raw_key = generate_api_key()
    api_key = APIKey(
        user_id=uuid.UUID(user["user_id"]),
        name=name,
        key_prefix=raw_key[:10],
        key_hash=hash_api_key(raw_key),
        scopes_json=json.dumps(scopes),
        is_active=True,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Audit log: api_key.created
    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="api_key.created",
            actor_user_id=user["user_id"],
            target_type="api_key",
            target_id=str(api_key.id),
            details={"name": name, "scopes": scopes},
        )
    except Exception:
        pass

    return _key_response(api_key, full_key=raw_key)


@router.get("")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("api_keys:read")),
):
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == uuid.UUID(user["user_id"]))
        .order_by(APIKey.created_at.desc())
    )
    return {"api_keys": [_key_response(k) for k in result.scalars().all()]}


@router.get("/{key_id}")
async def get_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("api_keys:read")),
):
    key = await _get_user_key(key_id, user, db)
    return _key_response(key)


@router.patch("/{key_id}")
async def update_api_key(
    key_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("api_keys:write")),
):
    key = await _get_user_key(key_id, user, db)

    if "name" in body:
        name = body["name"].strip()
        if not name or len(name) > 100:
            raise HTTPException(status_code=422, detail="name must be 1–100 characters")
        key.name = name

    if "scopes" in body:
        scopes = body["scopes"]
        if not isinstance(scopes, list):
            raise HTTPException(status_code=422, detail="scopes must be a list")
        invalid = [s for s in scopes if s not in API_SCOPES]
        if invalid:
            raise HTTPException(status_code=422, detail=f"Invalid scopes: {sorted(invalid)}")
        _reject_scope_escalation(user, scopes)
        key.scopes_json = json.dumps(scopes)

    was_active = key.is_active
    if "is_active" in body:
        key.is_active = bool(body["is_active"])

    await db.commit()
    await db.refresh(key)

    # Audit log: api_key.revoked when deactivated
    if "is_active" in body and not key.is_active and was_active:
        try:
            from app.services.audit_service import log_audit_event as _log_audit
            await _log_audit(
                db,
                event_type="api_key.revoked",
                actor_user_id=user["user_id"],
                target_type="api_key",
                target_id=str(key.id),
                details={"name": key.name},
            )
        except Exception:
            pass

    return _key_response(key)


@router.post("/{key_id}/rotate", status_code=200)
async def rotate_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("api_keys:write")),
):
    """
    Rotate an API key: generate a new key value for the same key entry.
    The old key is immediately invalidated. The new full key is returned once.
    """
    key = await _get_user_key(key_id, user, db)

    raw_key = generate_api_key()
    key.key_prefix = raw_key[:10]
    key.key_hash = hash_api_key(raw_key)
    key.is_active = True

    await db.commit()
    await db.refresh(key)

    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="api_key.rotated",
            actor_user_id=user["user_id"],
            target_type="api_key",
            target_id=str(key.id),
            details={"name": key.name},
        )
    except Exception:
        pass

    return _key_response(key, full_key=raw_key)


@router.delete("/{key_id}", status_code=204)
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("api_keys:write")),
):
    key = await _get_user_key(key_id, user, db)
    key_name = key.name
    key_id_str = str(key.id)
    await db.delete(key)
    await db.commit()

    # Audit log: api_key.deleted
    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="api_key.deleted",
            actor_user_id=user["user_id"],
            target_type="api_key",
            target_id=key_id_str,
            details={"name": key_name},
        )
    except Exception:
        pass
