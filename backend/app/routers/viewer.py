import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
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
from app.config import settings
from app.services.policy import enforcer as policy_enforcer
from app.services.viewer_cache import (
    link_cache, doc_cache, page_cache,
    LinkSnapshot, DocSnapshot, PageSnapshot,
    text_content_cache, TEXT_CONTENT_MAX_BYTES,
    chunk_array_cache,
)
from app.services.page_cache import (
    fetch_page_bytes, store_page_bytes,
    fetch_thumb_bytes, store_thumb_bytes,
    clear_local_page_cache, clear_local_thumb_cache,
)
from app.utils.crypto import hash_value
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/api/viewer", tags=["viewer"])
link_svc = LinkService()
watermark_svc = WatermarkService()
analytics_svc = AnalyticsService()

logger = logging.getLogger(__name__)


def _session_watermark_angle(session_id: str, base: float = -32.0) -> float:
    """Derive a deterministic but session-unique watermark tilt angle.

    Same session always produces the same angle (stable across page loads),
    but different sessions get slightly different angles within ±jitter_deg
    of the base.  This makes composite-removal attacks harder — an attacker
    would need to align multiple differently-angled watermark layers.
    """
    h = int(hashlib.sha256(session_id.encode()).hexdigest()[:8], 16)
    norm = (h % 10000) / 10000.0           # 0.0 – 1.0, uniform
    jitter = settings.watermark_angle_jitter_deg
    return base + (norm - 0.5) * 2.0 * jitter  # base ± jitter_deg


# ── Cache helpers (backward-compatible wrappers used in tests) ────────────────

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


async def _get_cached_link_and_doc(
    link_token: str,
    db: AsyncSession,
    request: Request,
) -> tuple:
    """
    3-stage cache-first lookup shared by all viewer content endpoints.

    Stages:
      1. Link metadata — L1 TTL cache (10 s) or DB SELECT
      2. Revocation + expiry check against current clock
      3. IP allowlist enforcement
      4. Document metadata — L1 TTL cache (60 s) or DB SELECT
      5. Document ready check

    Returns (link_snap, doc_snap, client_ip, now).
    Raises HTTPException on any access control failure.
    """
    link_snap: Optional[LinkSnapshot] = link_cache.get(link_token)
    if link_snap is None:
        _link_row = await db.execute(select(ShareLink).where(ShareLink.token == link_token))
        _link = _link_row.scalar_one_or_none()
        if _link is None:
            raise HTTPException(status_code=404, detail="Link not found")
        link_snap = LinkSnapshot(
            id=_link.id, token=_link.token, document_id=_link.document_id,
            revoked_at=_link.revoked_at, expires_at=_link.expires_at,
            ip_allowlist=_link.ip_allowlist,
        )
        link_cache.put(link_token, link_snap)

    now = datetime.now(timezone.utc)
    _check_link_active(link_snap, now)

    ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else None)
    if link_snap.ip_allowlist:
        if not policy_enforcer.ip_is_allowed(ip, link_snap.ip_allowlist):
            raise HTTPException(status_code=403, detail="Access denied from this IP")

    _doc_key = str(link_snap.document_id)
    doc_snap: Optional[DocSnapshot] = doc_cache.get(_doc_key)
    if doc_snap is None:
        _doc_row = await db.execute(select(Document).where(Document.id == link_snap.document_id))
        _doc = _doc_row.scalar_one_or_none()
        if _doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        doc_snap = DocSnapshot(
            id=_doc.id, status=_doc.status,
            file_type=_doc.file_type or "pdf",
            storage_key=_doc.storage_key,
            page_count=_doc.page_count,
        )
        if _doc.status == "ready":
            doc_cache.put(_doc_key, doc_snap)
    _check_doc_ready(doc_snap)

    return link_snap, doc_snap, ip, now


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

    ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else None)
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

    # concurrency detection — log a warning when concurrent sessions exceed
    # the configured threshold.  Detection-only: never blocks legitimate access.
    try:
        from app.config import settings as _settings
        if _settings.max_concurrent_sessions_per_link > 0:
            _count = await policy_enforcer.active_session_count(db, link.id)
            if _count > _settings.max_concurrent_sessions_per_link:
                logger.warning(
                    "high_concurrent_sessions link_id=%s count=%d threshold=%d",
                    link.id, _count, _settings.max_concurrent_sessions_per_link,
                )
    except Exception:
        pass  # concurrency check must never block the validate response

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

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    # ── Session validation (SEC-03) ───────────────────────────────────────────
    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

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

    # ── Session heartbeat + email retrieval ───────────────────────────────────
    # Moved BEFORE watermarking so the viewer's masked email can be burned into
    # the page image instead of the generic "anonymous" placeholder.
    viewer_email_masked = None
    if session_id:
        ip_hash = hash_value(ip) if ip else None
        viewer_email_masked = await policy_enforcer.upsert_session(
            db, session_id, link_snap.id, ip_hash=ip_hash
        )

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
    # angle is session-specific (deterministic per session, varies across
    # sessions) to deter composite-removal attacks.
    now_str = now.strftime("%Y-%m-%d")
    watermark_text = f"{viewer_email_masked or 'anonymous'} · {now_str} · sess:{session_id[:6]}"
    _wm_angle = _session_watermark_angle(session_id)
    watermarked = await asyncio.get_running_loop().run_in_executor(
        None,
        lambda: watermark_svc.apply_visible_watermark(image_bytes, watermark_text, angle=_wm_angle),
    )
    t2 = time.perf_counter()
    # structured log with doc_id, cache source, and latency breakdown
    logger.info(
        "page_served doc=%s page=%d cache=%s fetch_ms=%.1f watermark_ms=%.1f req_id=%s",
        link_snap.document_id, page_number, cache_source,
        (t1 - t0) * 1000, (t2 - t1) * 1000,
        getattr(request.state, "request_id", "-"),
    )

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

    # X-Cache-Status header lets CDN operators see hit/miss without
    # parsing logs.  "HIT" = served from L1/L2 cache; "MISS" = fetched from storage.
    cache_status = "HIT" if cache_source in ("local", "redis") else "MISS"

    return FastAPIResponse(
        content=watermarked,
        media_type="image/webp",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Cache-Status": cache_status,
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

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    # ── Session validation (SEC-01) ───────────────────────────────────────────
    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

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
        "thumb_served doc=%s page=%d cache=%s req_id=%s",
        link_snap.document_id, page_number, thumb_source,
        getattr(request.state, "request_id", "-"),
    )

    # X-Cache-Status for CDN/ops visibility
    thumb_cache_status = "HIT" if thumb_source in ("local", "redis") else "MISS"

    return FastAPIResponse(
        content=thumb_bytes,
        media_type="image/webp",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
            "X-Cache-Status": thumb_cache_status,
        },
    )


@router.get("/toc/{link_token}")
@limiter.limit("60/minute")
async def get_toc(
    request: Request,
    link_token: str,
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a table of contents for the document — works for all supported formats.

    Security model: valid session, link revocation/expiry, IP allowlist.

    Response:
      { "toc": [...TocEntry dicts...], "doc_type": str, "supported": bool }

    Routing per format:
      pdf   → TOC sidecar from storage (toc/{doc_id}.json), or empty
      docx  → TOC sidecar (heading styles) if present, else empty (no text fallback)
      doc   → TOC sidecar if present, else inline text extraction
      txt/md/log → inline text extraction (fast, from text_content_cache)

    TOC entries are cached via toc/cache.py (L1 TTL=5 min, L2 Redis TTL=5 min).
    """
    from fastapi.responses import JSONResponse as _JSONResponse
    from app.services.toc.cache import get_cached_toc_async, store_toc_async
    from app.config import settings as _settings

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    # ── Session validation (SEC-01) ───────────────────────────────────────────
    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

    file_type = doc_snap.file_type
    doc_id_str = str(link_snap.document_id)

    # ── TOC cache (L1 → L2 Redis) ─────────────────────────────────────────────
    cached_toc = await get_cached_toc_async(doc_id_str)
    if cached_toc is not None:
        return _JSONResponse(
            content={"toc": cached_toc, "doc_type": file_type, "supported": True},
            headers={"Cache-Control": "no-store"},
        )

    toc_entries = []
    supported = True

    # ── PDF and DOCX/DOC: try TOC sidecar first ───────────────────────────────
    from app.services.adapters import get_adapter as _get_adapter
    _toc_adapter = _get_adapter(file_type)
    if _toc_adapter.supports_toc_sidecar():
        sidecar_key = f"toc/{doc_id_str}.json"
        sidecar_entries = await _load_toc_sidecar(sidecar_key)
        if sidecar_entries is not None:
            toc_entries = sidecar_entries
            await store_toc_async(doc_id_str, toc_entries)
            return _JSONResponse(
                content={"toc": toc_entries, "doc_type": file_type, "supported": True},
                headers={"Cache-Control": "no-store"},
            )
        if not _toc_adapter.toc_fallback_to_text():
            # No sidecar and no text fallback (PDF) = no bookmarks
            await store_toc_async(doc_id_str, [])
            return _JSONResponse(
                content={"toc": [], "doc_type": file_type, "supported": False},
                headers={"Cache-Control": "no-store"},
            )
        # DOC without sidecar: fall through to text extraction

    # ── Text-based extraction (TXT, MD, LOG, and DOC without sidecar) ───
    storage_key = doc_snap.storage_key
    cached_text: Optional[str] = text_content_cache.get(storage_key)
    if cached_text is None:
        storage = get_storage_service()
        try:
            raw_bytes = await storage.download_bytes(storage_key)
        except Exception as exc:
            logger.error("toc_storage_failed doc=%s key=%r error=%s", doc_snap.id, storage_key, exc)
            raise HTTPException(status_code=503, detail="Document content temporarily unavailable")
        from app.services.text_processor import decode_text_safe
        cached_text = decode_text_safe(raw_bytes)
        if len(cached_text) <= TEXT_CONTENT_MAX_BYTES:
            text_content_cache.put(storage_key, cached_text)

    from app.services.toc.extractor import extract_toc_for_document
    toc_entries = await extract_toc_for_document(
        file_type,
        text_content=cached_text,
        lines_per_chunk=_settings.text_lines_per_chunk,
    )

    await store_toc_async(doc_id_str, toc_entries)
    return _JSONResponse(
        content={"toc": toc_entries, "doc_type": file_type, "supported": bool(toc_entries)},
        headers={"Cache-Control": "no-store"},
    )


async def _load_toc_sidecar(sidecar_key: str):
    """Load a JSON TOC sidecar from storage. Returns list or None if absent."""
    import json as _json
    try:
        storage = get_storage_service()
        raw = await storage.download_bytes(sidecar_key)
        return _json.loads(raw.decode("utf-8"))
    except Exception:
        return None


@router.get("/download/{link_token}")
@limiter.limit("10/minute")
async def download_document(
    request: Request,
    link_token: str,
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Download the document as a watermarked PDF (PDF docs) or plain text file (text docs).
    Requires an active session with can_download=true on the link.
    """
    import io as _io
    from PIL import Image as _Image

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # Validate link
    _link_row = await db.execute(select(ShareLink).where(ShareLink.token == link_token))
    link = _link_row.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")

    now = datetime.now(timezone.utc)
    if link.revoked_at:
        raise HTTPException(status_code=410, detail="Link revoked")
    if link.expires_at:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise HTTPException(status_code=410, detail="Link expired")

    # IP allowlist — must be enforced consistently on ALL viewer endpoints.
    # Without this check, a viewer whose IP changed after session creation
    # (e.g., moved networks or switched VPN) could still download the document.
    ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else None)
    if link.ip_allowlist:
        if not policy_enforcer.ip_is_allowed(ip, link.ip_allowlist):
            raise HTTPException(status_code=403, detail="Access denied from this IP")

    # Check download permission
    perms = json.loads(link.permissions) if link.permissions else {}
    if not perms.get("can_download", False):
        raise HTTPException(status_code=403, detail="Download not permitted on this link")

    # Validate active session
    if not await policy_enforcer.is_active_session(db, link.id, session_id):
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Fetch document
    _doc_row = await db.execute(select(Document).where(Document.id == link.document_id))
    doc = _doc_row.scalar_one_or_none()
    if doc is None or doc.status != "ready":
        raise HTTPException(status_code=404, detail="Document not ready")

    storage = get_storage_service()
    now_str = now.strftime("%Y-%m-%d")
    watermark_text = f"downloaded · {now_str} · sess:{session_id[:6]}"

    await analytics_svc.log_event(
        db, link_id=link.id, event_type="download_attempt",
        session_id=session_id, ip=ip,
        user_agent=request.headers.get("user-agent"), commit=True,
    )

    # ── Text document ──────────────────────────────────────────────────────────
    from app.services.adapters import get_adapter as _get_adapter
    if _get_adapter(doc.file_type).viewer_mode == "text":
        raw = await storage.download_bytes(doc.storage_key)
        # DOC is stored as converted text after processing; DOCX is image-mode after D2
        filename = doc.filename or f"document.{doc.file_type}"
        return FastAPIResponse(
            content=raw,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.txt"',
                "Cache-Control": "no-store",
            },
        )

    # ── PDF document: fetch all pages, watermark, assemble PDF via PIL ─────────
    if not doc.page_count:
        raise HTTPException(status_code=404, detail="Document has no pages")

    # Guard against memory exhaustion: assembling a watermarked PDF requires
    # loading all pages as RGBA PIL images simultaneously (~20 MB each at 150 DPI).
    # A 500-page PDF would need ~10 GB RAM on the API server.
    # Refuse downloads that exceed the configured page limit.
    _limit = settings.max_download_pages_pdf
    if _limit > 0 and doc.page_count > _limit:
        raise HTTPException(
            status_code=413,
            detail=(
                f"PDF download is limited to {_limit} pages. "
                f"This document has {doc.page_count} pages. "
                "Contact the document owner for a split version."
            ),
        )

    pages_result = await db.execute(
        select(DocumentPage)
        .where(DocumentPage.document_id == doc.id)
        .order_by(DocumentPage.page_number)
    )
    page_rows = pages_result.scalars().all()
    if not page_rows:
        raise HTTPException(status_code=404, detail="Pages not found")

    pil_images = []
    loop = asyncio.get_running_loop()
    for page_row in page_rows:
        raw_bytes, _ = await fetch_page_bytes(page_row.storage_key)
        if raw_bytes is None:
            raw_bytes = await storage.download_bytes(page_row.storage_key)
        watermarked = await loop.run_in_executor(
            None, lambda b=raw_bytes: watermark_svc.apply_visible_watermark(b, watermark_text)
        )
        pil_images.append(_Image.open(_io.BytesIO(watermarked)).convert("RGB"))

    buf = _io.BytesIO()
    pil_images[0].save(buf, format="PDF", save_all=True, append_images=pil_images[1:])
    pdf_bytes = buf.getvalue()

    filename = (doc.filename or "document").rsplit(".", 1)[0] + "_watermarked.pdf"
    return FastAPIResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
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

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    # ── Session validation (SEC-03) ───────────────────────────────────────────
    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

    # ── Verify this is a text document (uses cached DocSnapshot — no extra DB read) ──
    file_type = doc_snap.file_type
    from app.services.adapters import get_adapter as _get_adapter
    if _get_adapter(file_type).viewer_mode != "text":
        raise HTTPException(
            status_code=400,
            detail="This endpoint is for text/word documents only. Use /api/viewer/page for PDFs.",
        )

    total_chunks = doc_snap.page_count or 1
    if chunk_number > total_chunks:
        raise HTTPException(status_code=404, detail="Chunk not found")

    storage_key = doc_snap.storage_key

    # ── Session heartbeat + email retrieval (before analytics) ───────────────
    viewer_email_masked = None
    if session_id:
        ip_hash = hash_value(ip) if ip else None
        viewer_email_masked = await policy_enforcer.upsert_session(
            db, session_id, link_snap.id, ip_hash=ip_hash
        )

    # ── Text content: process-local cache → storage ───────────────────────────
    # Only raw decoded text is cached — the session-specific watermark_text is
    # added to the response after the cache hit (same pattern as page images).
    cached_text: Optional[str] = text_content_cache.get(storage_key)
    if cached_text is None:
        storage = get_storage_service()
        try:
            raw_bytes = await storage.download_bytes(storage_key)
        except Exception as exc:
            logger.error(
                "text_storage_failed doc=%s key=%r error=%s",
                doc_snap.id, storage_key, exc,
            )
            raise HTTPException(status_code=503, detail="Text content temporarily unavailable")
        cached_text = decode_text_safe(raw_bytes)
        # Only cache files within the configured size limit to protect memory
        if len(cached_text) <= TEXT_CONTENT_MAX_BYTES:
            text_content_cache.put(storage_key, cached_text)

    # ── Chunk the text (cached to avoid O(n) re-split on every request) ──────
    _chunk_cache_key = f"{storage_key}:{settings.text_lines_per_chunk}"
    chunks: Optional[list] = chunk_array_cache.get(_chunk_cache_key)
    if chunks is None:
        chunks = chunk_text(cached_text, settings.text_lines_per_chunk)
        chunk_array_cache.put(_chunk_cache_key, chunks)

    total_chunks = len(chunks)
    if chunk_number > total_chunks:
        raise HTTPException(status_code=404, detail="Chunk not found")

    chunk_content = chunks[chunk_number - 1]

    # ── Analytics event ───────────────────────────────────────────────────────
    now_str = now.strftime("%Y-%m-%d")
    watermark_text = f"{viewer_email_masked or 'anonymous'} · {now_str} · sess:{session_id[:6]}"

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
