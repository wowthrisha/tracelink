import asyncio
import json
import logging
import time
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
from app.services.viewer_cache import (
    link_cache, doc_cache, page_cache,
    LinkSnapshot, DocSnapshot, PageSnapshot,
    text_content_cache, TEXT_CONTENT_MAX_BYTES,
)
from app.services.page_cache import (
    fetch_page_bytes, store_page_bytes,
    fetch_thumb_bytes, store_thumb_bytes,
    clear_local_page_cache, clear_local_thumb_cache,
    clear_doc_from_local_cache,
)
from app.utils.crypto import hash_value
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/api/viewer", tags=["viewer"])
link_svc = LinkService()
watermark_svc = WatermarkService()
analytics_svc = AnalyticsService()

logger = logging.getLogger(__name__)


# ── Cache helpers (backward-compatible wrappers for Phase 3 tests) ─────────────
# The actual L1 byte caches live in app.services.page_cache (Phase 4).
# These wrappers keep Phase 1/3 test imports working without change.

def clear_page_cache() -> None:
    """Flush the process-local page byte cache.  Called in tests."""
    clear_local_page_cache()


def clear_thumb_cache() -> None:
    """Flush the process-local thumbnail byte cache.  Called in tests."""
    clear_local_thumb_cache()


def clear_metadata_caches() -> None:
    """Flush the link/doc/page TTL metadata caches.  Called in tests."""
    from app.services.viewer_cache import clear_all_caches
    clear_all_caches()


def clear_doc_bytes_cache(doc_id: str) -> None:
    """Remove all L1 byte cache entries for a document.  Called on document delete."""
    clear_doc_from_local_cache(doc_id)


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


def _check_doc_ready(doc) -> None:
    """Raise 503 with a descriptive message if the document is not yet ready."""
    if doc.status == "uploaded":
        logger.warning("doc_not_ready status=uploaded doc_id=%s", getattr(doc, 'id', '?'))
        raise HTTPException(status_code=503, detail="Document is queued for processing")
    if doc.status == "processing":
        logger.warning("doc_not_ready status=processing doc_id=%s", getattr(doc, 'id', '?'))
        raise HTTPException(
            status_code=503, detail="Document is still processing, please try again shortly"
        )
    if doc.status == "error":
        logger.warning("doc_not_ready status=error doc_id=%s", getattr(doc, 'id', '?'))
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
@limiter.limit("20/minute")
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

    # validate_link stages the session upsert without committing (commit=False).
    # increment_view_count stages the view count update without committing.
    # log_event issues the single final commit that flushes all three writes atomically,
    # reducing the validate happy path from 3 DB round-trips to 1.
    validation = await link_svc.validate_link(
        db=db,
        token=token,
        password=password,
        viewer_email=viewer_email,
        analytics_svc=analytics_svc,
        ip=ip,
        user_agent=user_agent,
        existing_session_id=existing_session_id,
        commit=False,
    )

    link = validation.link
    session_id = validation.session_id

    # Stage view count increment (no commit yet)
    await link_svc.increment_view_count(db, str(link.id), commit=False)

    # Log opened event — commit=True (default) flushes session + view_count + event atomically
    await analytics_svc.log_event(
        db,
        link_id=link.id,
        event_type="opened",
        viewer_email=viewer_email,
        ip=ip,
        user_agent=user_agent,
        session_id=session_id,
        commit=True,
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
        "doc_status": doc.status,  # lets the viewer show meaningful state when not yet ready
        "doc_type": getattr(doc, "file_type", "pdf") or "pdf",  # pdf | txt | md | log
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

    # ── Link metadata (TTL-cached, 10 s) ──────────────────────────────────────
    # Skips the DB SELECT on cache hits while keeping security checks intact:
    # revoked_at and expires_at are in the snapshot and verified against the
    # current clock on every request, even on hits.
    link_snap: Optional[LinkSnapshot] = link_cache.get(link_token)
    if link_snap is None:
        _link_row = await db.execute(
            select(ShareLink).where(ShareLink.token == link_token)
        )
        _link = _link_row.scalar_one_or_none()
        if _link is None:
            raise HTTPException(status_code=404, detail="Link not found")
        link_snap = LinkSnapshot(
            id=_link.id,
            token=_link.token,
            document_id=_link.document_id,
            revoked_at=_link.revoked_at,
            expires_at=_link.expires_at,
            ip_allowlist=_link.ip_allowlist,
        )
        link_cache.put(link_token, link_snap)

    now = datetime.now(timezone.utc)
    _check_link_active(link_snap, now)

    # Re-validate IP on every page request (allowlist may have changed)
    ip = request.client.host if request.client else None
    if link_snap.ip_allowlist:
        if not policy_enforcer.ip_is_allowed(ip, link_snap.ip_allowlist):
            raise HTTPException(status_code=403, detail="Access denied from this IP")

    # ── Document metadata (TTL-cached, 60 s) ──────────────────────────────────
    _doc_key = str(link_snap.document_id)
    doc_snap: Optional[DocSnapshot] = doc_cache.get(_doc_key)
    if doc_snap is None:
        _doc_row = await db.execute(
            select(Document).where(Document.id == link_snap.document_id)
        )
        _doc = _doc_row.scalar_one_or_none()
        if _doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        doc_snap = DocSnapshot(id=_doc.id, status=_doc.status)
        # Only cache ready documents — caching non-ready statuses would lock
        # clients out for up to DOC_TTL_SEC (60 s) after the doc finishes
        # processing, because subsequent requests would hit the stale snapshot.
        if _doc.status == "ready":
            doc_cache.put(_doc_key, doc_snap)
    _check_doc_ready(doc_snap)

    # ── Page record (TTL-cached, 5 min; immutable after creation) ─────────────
    _page_key = f"{link_snap.document_id}:{page_number}"
    page_snap: Optional[PageSnapshot] = page_cache.get(_page_key)
    if page_snap is None:
        _page_row = await db.execute(
            select(DocumentPage).where(
                DocumentPage.document_id == link_snap.document_id,
                DocumentPage.page_number == page_number,
            )
        )
        _page = _page_row.scalar_one_or_none()
        if _page is None:
            raise HTTPException(status_code=404, detail="Page not found")
        page_snap = PageSnapshot(
            storage_key=_page.storage_key,
            width_px=_page.width_px,
            height_px=_page.height_px,
        )
        page_cache.put(_page_key, page_snap)

    # ── Page bytes: L1 (local) → L2 (Redis) → Storage ────────────────────────
    # Security: all auth checks above are complete before any cache access.
    # Only raw bytes (pre-watermark) are cached; the session-specific visible
    # watermark is applied below, after the cache hit.
    storage = get_storage_service()
    t0 = time.perf_counter()

    image_bytes, cache_source = await fetch_page_bytes(page_snap.storage_key)

    if image_bytes is None:
        # Both L1 and L2 missed — fetch from storage, then populate both.
        try:
            image_bytes = await storage.download_bytes(page_snap.storage_key)
            await store_page_bytes(page_snap.storage_key, image_bytes)
        except Exception as exc:
            logger.error(
                "storage_fallback_failed doc=%s page=%d key=%r error=%s",
                link_snap.document_id, page_number, page_snap.storage_key, exc,
            )
            raise HTTPException(status_code=503, detail="Page asset temporarily unavailable")

    t1 = time.perf_counter()

    # Apply visible watermark — CPU-bound PIL work offloaded to thread pool so it
    # does not block the async event loop while other requests are being served.
    now_str = now.strftime("%Y-%m-%d")
    watermark_text = f"anonymous · {now_str} · sess:{session_id[:6]}"
    watermarked = await asyncio.get_running_loop().run_in_executor(
        None,
        lambda: watermark_svc.apply_visible_watermark(image_bytes, watermark_text),
    )
    t2 = time.perf_counter()
    logger.debug(
        "page=%d cache_source=%s fetch_ms=%.1f watermark_ms=%.1f",
        page_number, cache_source, (t1 - t0) * 1000, (t2 - t1) * 1000,
    )

    # Refresh session heartbeat (throttled: only writes if >30s since last update)
    if session_id:
        ip_hash = hash_value(ip) if ip else None
        await policy_enforcer.upsert_session(db, session_id, link_snap.id, ip_hash=ip_hash)

    # Log page_viewed event and commit both heartbeat + event in a single round-trip
    await analytics_svc.log_event(
        db,
        link_id=link_snap.id,
        event_type="page_viewed",
        page_number=page_number,
        session_id=session_id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
        commit=True,  # single commit covers session heartbeat + analytics event
    )

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

    # ── Link metadata (TTL-cached, 10 s) ──────────────────────────────────────
    link_snap: Optional[LinkSnapshot] = link_cache.get(link_token)
    if link_snap is None:
        _link_row = await db.execute(
            select(ShareLink).where(ShareLink.token == link_token)
        )
        _link = _link_row.scalar_one_or_none()
        if _link is None:
            raise HTTPException(status_code=404, detail="Link not found")
        link_snap = LinkSnapshot(
            id=_link.id,
            token=_link.token,
            document_id=_link.document_id,
            revoked_at=_link.revoked_at,
            expires_at=_link.expires_at,
            ip_allowlist=_link.ip_allowlist,
        )
        link_cache.put(link_token, link_snap)

    now = datetime.now(timezone.utc)
    _check_link_active(link_snap, now)

    # ── Document metadata (TTL-cached, 60 s) ──────────────────────────────────
    _doc_key = str(link_snap.document_id)
    doc_snap: Optional[DocSnapshot] = doc_cache.get(_doc_key)
    if doc_snap is None:
        _doc_row = await db.execute(
            select(Document).where(Document.id == link_snap.document_id)
        )
        _doc = _doc_row.scalar_one_or_none()
        if _doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        doc_snap = DocSnapshot(id=_doc.id, status=_doc.status)
        if _doc.status == "ready":
            doc_cache.put(_doc_key, doc_snap)
    _check_doc_ready(doc_snap)

    # ── Page record (TTL-cached, 5 min) ───────────────────────────────────────
    _page_key = f"{link_snap.document_id}:{page_number}"
    page_snap: Optional[PageSnapshot] = page_cache.get(_page_key)
    if page_snap is None:
        _page_row = await db.execute(
            select(DocumentPage).where(
                DocumentPage.document_id == link_snap.document_id,
                DocumentPage.page_number == page_number,
            )
        )
        _page = _page_row.scalar_one_or_none()
        if _page is None:
            raise HTTPException(status_code=404, detail="Page not found")
        page_snap = PageSnapshot(
            storage_key=_page.storage_key,
            width_px=_page.width_px,
            height_px=_page.height_px,
        )
        page_cache.put(_page_key, page_snap)

    # ── Thumbnail bytes: L1 → L2 → Storage ───────────────────────────────────
    thumb_key = f"thumbs/{link_snap.document_id}/{page_number:04d}.webp"
    storage = get_storage_service()

    thumb_bytes, thumb_source = await fetch_thumb_bytes(thumb_key)
    if thumb_bytes is None:
        try:
            thumb_bytes = await storage.download_bytes(thumb_key)
            await store_thumb_bytes(thumb_key, thumb_bytes)
            thumb_source = "storage"
        except Exception:
            # Thumbnail absent (pre-thumbnail document) — fall back to full-res page bytes.
            logger.debug(
                "thumb_missing doc=%s page=%d — serving full-res fallback",
                link_snap.document_id, page_number,
            )
            thumb_bytes, thumb_source = await fetch_page_bytes(page_snap.storage_key)
            if thumb_bytes is None:
                try:
                    thumb_bytes = await storage.download_bytes(page_snap.storage_key)
                    await store_page_bytes(page_snap.storage_key, thumb_bytes)
                    thumb_source = "storage"
                except Exception as exc:
                    logger.error(
                        "storage_fallback_failed type=thumb key=%r error=%s",
                        page_snap.storage_key, exc,
                    )
                    raise HTTPException(
                        status_code=503, detail="Thumbnail asset temporarily unavailable"
                    )

    logger.debug(
        "thumb=%d cache_source=%s", page_number, thumb_source
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


@router.get("/text/{link_token}/{chunk_number}")
@limiter.limit("120/minute")
async def get_text_chunk(
    request: Request,
    link_token: str,
    chunk_number: int,
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Serve one chunk of a text document (.txt, .md, .log) as JSON.

    Security model mirrors /page:
      - Requires valid session_id
      - Validates link revocation and expiry on every request
      - Enforces IP allowlist
      - Logs analytics event (page_viewed with chunk_number as page_number)
      - Never returns raw HTML — content is a plain text string that the React
        frontend renders via auto-escaping JSX text nodes (no innerHTML)

    Response shape:
      {
        "content":      str,   # text content of the requested chunk
        "chunk_number": int,   # 1-indexed chunk number (echoed back)
        "total_chunks": int,   # total chunks in this document
        "doc_type":     str,   # "txt" | "md" | "log"
        "watermark_text": str  # session-specific watermark string
      }
    """
    from fastapi.responses import JSONResponse
    from app.services.text_processor import decode_text_safe, chunk_text
    from app.config import settings

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    if chunk_number < 1:
        raise HTTPException(status_code=400, detail="chunk_number must be ≥ 1")

    # ── Link metadata (TTL-cached, 10 s) ──────────────────────────────────────
    link_snap: Optional[LinkSnapshot] = link_cache.get(link_token)
    if link_snap is None:
        _link_row = await db.execute(
            select(ShareLink).where(ShareLink.token == link_token)
        )
        _link = _link_row.scalar_one_or_none()
        if _link is None:
            raise HTTPException(status_code=404, detail="Link not found")
        link_snap = LinkSnapshot(
            id=_link.id,
            token=_link.token,
            document_id=_link.document_id,
            revoked_at=_link.revoked_at,
            expires_at=_link.expires_at,
            ip_allowlist=_link.ip_allowlist,
        )
        link_cache.put(link_token, link_snap)

    now = datetime.now(timezone.utc)
    _check_link_active(link_snap, now)

    ip = request.client.host if request.client else None
    if link_snap.ip_allowlist:
        if not policy_enforcer.ip_is_allowed(ip, link_snap.ip_allowlist):
            raise HTTPException(status_code=403, detail="Access denied from this IP")

    # ── Document metadata (TTL-cached, 60 s) ──────────────────────────────────
    _doc_key = str(link_snap.document_id)
    doc_snap: Optional[DocSnapshot] = doc_cache.get(_doc_key)
    if doc_snap is None:
        _doc_row = await db.execute(
            select(Document).where(Document.id == link_snap.document_id)
        )
        _doc = _doc_row.scalar_one_or_none()
        if _doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        doc_snap = DocSnapshot(id=_doc.id, status=_doc.status)
        if _doc.status == "ready":
            doc_cache.put(_doc_key, doc_snap)
    _check_doc_ready(doc_snap)

    # ── Verify this is a text document ────────────────────────────────────────
    # Fetch the full document to get file_type + storage_key + page_count.
    # This is a small extra DB read compared to the PDF path, but text documents
    # don't use the DocumentPage table so there's no page-level cache to use.
    doc_row = await db.execute(
        select(Document).where(Document.id == link_snap.document_id)
    )
    doc = doc_row.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_type = getattr(doc, "file_type", "pdf") or "pdf"
    if file_type not in ("txt", "md", "log"):
        raise HTTPException(
            status_code=400,
            detail="This endpoint is for text documents only. Use /api/viewer/page for PDFs.",
        )

    total_chunks = doc.page_count or 1
    if chunk_number > total_chunks:
        raise HTTPException(status_code=404, detail="Chunk not found")

    # ── Text content: process-local cache → storage ───────────────────────────
    # Only raw decoded text is cached — the session-specific watermark_text is
    # added to the response after the cache hit (same pattern as page images).
    cached_text: Optional[str] = text_content_cache.get(doc.storage_key)
    if cached_text is None:
        storage = get_storage_service()
        try:
            raw_bytes = await storage.download_bytes(doc.storage_key)
        except Exception as exc:
            logger.error(
                "text_storage_failed doc=%s key=%r error=%s",
                doc.id, doc.storage_key, exc,
            )
            raise HTTPException(status_code=503, detail="Text content temporarily unavailable")
        cached_text = decode_text_safe(raw_bytes)
        # Only cache files within the configured size limit to protect memory
        if len(cached_text) <= TEXT_CONTENT_MAX_BYTES:
            text_content_cache.put(doc.storage_key, cached_text)

    # ── Chunk the text and return the requested slice ────────────────────────
    chunks = chunk_text(cached_text, settings.text_lines_per_chunk)
    total_chunks = len(chunks)
    if chunk_number > total_chunks:
        raise HTTPException(status_code=404, detail="Chunk not found")

    chunk_content = chunks[chunk_number - 1]

    # ── Session heartbeat ─────────────────────────────────────────────────────
    if session_id:
        ip_hash = hash_value(ip) if ip else None
        await policy_enforcer.upsert_session(db, session_id, link_snap.id, ip_hash=ip_hash)

    # ── Analytics event ───────────────────────────────────────────────────────
    now_str = now.strftime("%Y-%m-%d")
    watermark_text = f"anonymous · {now_str} · sess:{session_id[:6]}"

    await analytics_svc.log_event(
        db,
        link_id=link_snap.id,
        event_type="page_viewed",
        page_number=chunk_number,
        session_id=session_id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
        commit=True,
    )

    return JSONResponse(
        content={
            "content": chunk_content,
            "chunk_number": chunk_number,
            "total_chunks": total_chunks,
            "doc_type": file_type,
            "watermark_text": watermark_text,
        },
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "X-Content-Type-Options": "nosniff",
        },
    )
