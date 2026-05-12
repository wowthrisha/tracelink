import collections
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.document import Document, DocumentPage
from app.models.link import ShareLink
from app.services.link_service import LinkService
from app.services.storage import get_storage_service
from app.services.watermark import WatermarkService
from app.services.analytics_service import AnalyticsService
from app.services.policy import enforcer as policy_enforcer
from app.utils.crypto import hash_value
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/api/viewer", tags=["viewer"])
link_svc = LinkService()
watermark_svc = WatermarkService()
analytics_svc = AnalyticsService()

# ── In-process LRU cache for raw page bytes ────────────────────────────────────
# Page bytes from storage are deterministic per storage_key.  Caching them avoids
# a round-trip to S3/R2 on every viewer page request.  The visible watermark
# (which embeds session_id / viewer email) is applied *after* the cache hit, so
# no per-viewer data is ever stored here.
#
# Sizing: 50 docs × 60 pages × ~50 KB ≈ 150 MB worst-case; with LRU eviction at
# 600 entries we keep only the hottest pages in memory.
_PAGE_BYTES_CACHE: collections.OrderedDict = collections.OrderedDict()
_PAGE_BYTES_CACHE_MAX = 600


def _page_cache_get(key: str) -> Optional[bytes]:
    if key not in _PAGE_BYTES_CACHE:
        return None
    _PAGE_BYTES_CACHE.move_to_end(key)
    return _PAGE_BYTES_CACHE[key]


def _page_cache_put(key: str, value: bytes) -> None:
    _PAGE_BYTES_CACHE[key] = value
    _PAGE_BYTES_CACHE.move_to_end(key)
    if len(_PAGE_BYTES_CACHE) > _PAGE_BYTES_CACHE_MAX:
        _PAGE_BYTES_CACHE.popitem(last=False)


def clear_page_cache() -> None:
    """Flush the in-process page byte cache.  Called in tests to prevent cross-test pollution."""
    _PAGE_BYTES_CACHE.clear()


@router.get("/gate/{token}")
async def get_gate_requirements(token: str, db: AsyncSession = Depends(get_db)):
    """Return gate requirements without validating credentials. Public, no auth needed."""
    result = await db.execute(select(ShareLink).where(ShareLink.token == token))
    link = result.scalar_one_or_none()
    if not link:
        return {"status": "not_found", "requires_password": False, "requires_email": False}
    now = datetime.now(timezone.utc)
    if link.revoked_at is not None:
        return {"status": "revoked", "requires_password": False, "requires_email": False}
    if link.expires_at is not None:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            return {"status": "expired", "requires_password": False, "requires_email": False}
    if link.max_views is not None and link.view_count >= link.max_views:
        return {"status": "expired", "requires_password": False, "requires_email": False}
    return {
        "status": "active",
        "requires_password": link.password_hash is not None,
        "requires_email": bool(link.allowed_emails or link.allowed_domains),
    }


@router.post("/validate")
async def validate_link(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    token = body.get("token", "")
    password = body.get("password")
    viewer_email = body.get("email")
    existing_session_id = body.get("session_id") or None  # reuse existing session if supplied

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    validation = await link_svc.validate_link(
        db=db,
        token=token,
        password=password,
        viewer_email=viewer_email,
        analytics_svc=analytics_svc,
        ip=ip,
        user_agent=user_agent,
        existing_session_id=existing_session_id,
    )

    link = validation.link
    session_id = validation.session_id

    # Increment view count
    await link_svc.increment_view_count(db, str(link.id))

    # Log opened event
    await analytics_svc.log_event(
        db,
        link_id=link.id,
        event_type="opened",
        viewer_email=viewer_email,
        ip=ip,
        user_agent=user_agent,
        session_id=session_id,
    )

    # Fetch document
    doc_result = await db.execute(
        select(Document).where(Document.id == link.document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Build watermark text
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    watermark_text = f"{viewer_email or 'anonymous'} · {now_str} · sess:{session_id[:6]}"

    permissions_dict = {
        "can_download": False,
        "can_print": False,
        "can_copy": False,
        "can_right_click": False,
        "watermark_enabled": True,
    }
    if link.permissions:
        try:
            stored_perms = json.loads(link.permissions)
            for k, v in stored_perms.items():
                if k in permissions_dict:
                    permissions_dict[k] = bool(v)
        except:
            pass

    return {
        "session_id": session_id,
        "document_id": str(doc.id),
        "document_filename": doc.filename,
        "page_count": doc.page_count or 0,
        "watermark_text": watermark_text if permissions_dict.get("watermark_enabled", True) else None,
        "link_id": str(link.id),
        "expires_at": link.expires_at.isoformat() if link.expires_at else None,
        "permissions": permissions_dict,
    }


@router.get("/page/{link_token}/{page_number}")
@limiter.limit("120/minute")
async def get_page(
    request: Request,
    link_token: str,
    page_number: int,
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # Re-validate token (do NOT increment view_count)
    link_result = await db.execute(
        select(ShareLink).where(ShareLink.token == link_token)
    )
    link = link_result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    now = datetime.now(timezone.utc)

    if link.revoked_at is not None:
        raise HTTPException(status_code=410, detail="Link revoked")

    if link.expires_at is not None:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise HTTPException(status_code=410, detail="Link expired")

    # Re-validate IP on every page request (allowlist may have changed)
    ip = request.client.host if request.client else None
    if link.ip_allowlist:
        if not policy_enforcer.ip_is_allowed(ip, link.ip_allowlist):
            raise HTTPException(status_code=403, detail="Access denied from this IP")

    # Fetch document page
    page_result = await db.execute(
        select(DocumentPage).where(
            DocumentPage.document_id == link.document_id,
            DocumentPage.page_number == page_number,
        )
    )
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Download base image with in-process LRU cache (avoids repeated S3/R2 round-trips).
    # The visible watermark applied below is session-specific; only the raw bytes are cached.
    storage = get_storage_service()
    image_bytes = _page_cache_get(page.storage_key)
    if image_bytes is None:
        image_bytes = await storage.download_bytes(page.storage_key)
        _page_cache_put(page.storage_key, image_bytes)

    # Apply visible watermark
    now_str = now.strftime("%Y-%m-%d")
    watermark_text = f"anonymous · {now_str} · sess:{session_id[:6]}"
    watermarked = watermark_svc.apply_visible_watermark(image_bytes, watermark_text)

    # Refresh session heartbeat (keeps concurrent-session count accurate)
    if session_id:
        ip_hash = hash_value(ip) if ip else None
        await policy_enforcer.upsert_session(db, session_id, link.id, ip_hash=ip_hash)

    # Log page_viewed event
    await analytics_svc.log_event(
        db,
        link_id=link.id,
        event_type="page_viewed",
        page_number=page_number,
        session_id=session_id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    return FastAPIResponse(
        content=watermarked,
        media_type="image/webp",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
            "X-Frame-Options": "SAMEORIGIN",
        },
    )
