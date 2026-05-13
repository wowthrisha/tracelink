import collections
import json
import logging
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

logger = logging.getLogger(__name__)

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

# Thumbnails are ~5 KB each; 2 000 entries ≈ 10 MB.  Larger cache budget because
# thumbnails are loaded on every sidebar render for every page of every document.
_THUMB_BYTES_CACHE: collections.OrderedDict = collections.OrderedDict()
_THUMB_BYTES_CACHE_MAX = 2000


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


def _thumb_cache_get(key: str) -> Optional[bytes]:
    if key not in _THUMB_BYTES_CACHE:
        return None
    _THUMB_BYTES_CACHE.move_to_end(key)
    return _THUMB_BYTES_CACHE[key]


def _thumb_cache_put(key: str, value: bytes) -> None:
    _THUMB_BYTES_CACHE[key] = value
    _THUMB_BYTES_CACHE.move_to_end(key)
    if len(_THUMB_BYTES_CACHE) > _THUMB_BYTES_CACHE_MAX:
        _THUMB_BYTES_CACHE.popitem(last=False)


def clear_page_cache() -> None:
    """Flush the in-process page byte cache.  Called in tests to prevent cross-test pollution."""
    _PAGE_BYTES_CACHE.clear()


def clear_thumb_cache() -> None:
    """Flush the in-process thumbnail byte cache.  Called in tests."""
    _THUMB_BYTES_CACHE.clear()


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _check_link_active(link: ShareLink, now: datetime) -> None:
    """Raise 410 if the link is revoked or expired.  Extracted to avoid duplication."""
    if link.revoked_at is not None:
        raise HTTPException(status_code=410, detail="Link revoked")
    if link.expires_at is not None:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise HTTPException(status_code=410, detail="Link expired")


def _check_doc_ready(doc: Document) -> None:
    """Raise 503 with a descriptive message if the document is not yet ready."""
    if doc.status == "uploaded":
        raise HTTPException(status_code=503, detail="Document is queued for processing")
    if doc.status == "processing":
        raise HTTPException(
            status_code=503, detail="Document is still processing, please try again shortly"
        )
    if doc.status == "error":
        raise HTTPException(status_code=503, detail="Document processing failed")


# ── Routes ────────────────────────────────────────────────────────────────────

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

    # Fetch page dimensions — returned to the frontend so it can pre-size
    # placeholder slots without additional API calls.  Only populated when
    # the document is ready; empty list otherwise.
    pages_meta: list[dict] = []
    if doc.status == "ready":
        pages_result = await db.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == doc.id)
            .order_by(DocumentPage.page_number)
        )
        pages_meta = [
            {
                "page_number": p.page_number,
                "width_px": p.width_px,
                "height_px": p.height_px,
            }
            for p in pages_result.scalars().all()
        ]

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
        except Exception:
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
        "pages": pages_meta,
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
    _check_link_active(link, now)

    # Re-validate IP on every page request (allowlist may have changed)
    ip = request.client.host if request.client else None
    if link.ip_allowlist:
        if not policy_enforcer.ip_is_allowed(ip, link.ip_allowlist):
            raise HTTPException(status_code=403, detail="Access denied from this IP")

    # Guard: document must be fully processed before pages are accessible
    doc_result = await db.execute(
        select(Document).where(Document.id == link.document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    _check_doc_ready(doc)

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
        try:
            image_bytes = await storage.download_bytes(page.storage_key)
            _page_cache_put(page.storage_key, image_bytes)
        except Exception as exc:
            logger.error(
                "Storage download failed for document %s page %d key %r: %s",
                link.document_id, page_number, page.storage_key, exc,
            )
            raise HTTPException(status_code=503, detail="Page asset temporarily unavailable")

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


@router.get("/thumb/{link_token}/{page_number}")
@limiter.limit("300/minute")
async def get_thumb(
    request: Request,
    link_token: str,
    page_number: int,
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Serve a narrow (200 px wide) thumbnail of a document page for sidebar navigation.

    Security model matches /page: requires valid session, checks revocation/expiry,
    and verifies the document is ready.  Thumbnails are served from a separate LRU
    cache and are not watermarked — they are too small to read meaningful content from
    and are used only for navigation, not document viewing.

    If the thumbnail asset is missing (e.g., a document processed before thumbnail
    generation was introduced), the full-resolution page bytes are served as a fallback.
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    link_result = await db.execute(
        select(ShareLink).where(ShareLink.token == link_token)
    )
    link = link_result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    now = datetime.now(timezone.utc)
    _check_link_active(link, now)

    # Document status guard
    doc_result = await db.execute(
        select(Document).where(Document.id == link.document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    _check_doc_ready(doc)

    # Page existence check
    page_result = await db.execute(
        select(DocumentPage).where(
            DocumentPage.document_id == link.document_id,
            DocumentPage.page_number == page_number,
        )
    )
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Thumbnail key is deterministic: thumbs/{doc_id}/{page:04d}.webp
    thumb_key = f"thumbs/{link.document_id}/{page_number:04d}.webp"
    storage = get_storage_service()

    thumb_bytes = _thumb_cache_get(thumb_key)
    if thumb_bytes is None:
        try:
            thumb_bytes = await storage.download_bytes(thumb_key)
            _thumb_cache_put(thumb_key, thumb_bytes)
        except Exception:
            # Thumbnail absent (pre-thumbnail document) — fall back to full-res page
            logger.debug(
                "Thumbnail not found for document %s page %d — serving full-res fallback",
                link.document_id, page_number,
            )
            thumb_bytes = _page_cache_get(page.storage_key)
            if thumb_bytes is None:
                try:
                    thumb_bytes = await storage.download_bytes(page.storage_key)
                    _page_cache_put(page.storage_key, thumb_bytes)
                except Exception as exc:
                    logger.error(
                        "Storage download failed for fallback thumb key %r: %s",
                        page.storage_key, exc,
                    )
                    raise HTTPException(
                        status_code=503, detail="Thumbnail asset temporarily unavailable"
                    )

    return FastAPIResponse(
        content=thumb_bytes,
        media_type="image/webp",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )
