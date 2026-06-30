import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import Response as FastAPIResponse, StreamingResponse
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
)
from app.utils.crypto import hash_value
from app.middleware.rate_limit import limiter

# Service-layer helpers — imported here so tests that patch
# `app.routers.viewer.*` names continue to work without modification.
from app.services.viewer_service import (
    _check_link_active,
    _check_doc_ready,
    _get_session_id,
    _session_watermark_angle,
    clear_page_cache,
    clear_thumb_cache,
    clear_metadata_caches,
)


async def _load_toc_sidecar(sidecar_key: str):
    """Load a JSON TOC sidecar from storage. Returns list or None if absent."""
    import json as _json
    try:
        storage = get_storage_service()  # uses viewer.py's get_storage_service (patchable by tests)
        raw = await storage.download_bytes(sidecar_key)
        return _json.loads(raw.decode("utf-8"))
    except Exception:
        return None


from app.services.viewer_session_service import build_validate_response

router = APIRouter(prefix="/api/viewer", tags=["viewer"])
link_svc = LinkService()
watermark_svc = WatermarkService()
analytics_svc = AnalyticsService()

logger = logging.getLogger(__name__)


# ── Shared cache helper (kept in router so test patches of policy_enforcer work) ─

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
        raise HTTPException(status_code=404, detail="Link not found")
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
    ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")
    return await build_validate_response(db, body, ip, user_agent, link_svc, analytics_svc)


@router.get("/page/{link_token}/{page_number}")
@limiter.limit("120/minute")
async def get_page(
    request: Request,
    link_token: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
):
    session_id = _get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    # ── Session validation (SEC-03) ───────────────────────────────────────────
    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

    # ── Page bounds check against doc snapshot (avoids unnecessary DB query) ──
    if page_number < 1 or (doc_snap.page_count and page_number > doc_snap.page_count):
        raise HTTPException(status_code=404, detail="Page not found")

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
    viewer_email_masked = None
    if session_id:
        ip_hash = hash_value(ip) if ip else None
        viewer_email_masked = await policy_enforcer.upsert_session(
            db, session_id, link_snap.id, ip_hash=ip_hash
        )

    # ── Page bytes: L1 (local) → L2 (Redis) → Storage ────────────────────────
    storage = get_storage_service()
    t0 = time.perf_counter()

    image_bytes, cache_source = await fetch_page_bytes(page_snap.storage_key)

    if image_bytes is None:
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

    # Apply visible watermark + viewer forensic stamp in a single executor call.
    now_str = now.strftime("%Y-%m-%d")
    watermark_text = f"{viewer_email_masked or 'anonymous'} · {now_str} · sess:{session_id[:6]}"
    _wm_angle = _session_watermark_angle(session_id)
    _page_num = page_number

    def _apply_all_watermarks(raw: bytes) -> bytes:
        visible = watermark_svc.apply_visible_watermark(raw, watermark_text, angle=_wm_angle)
        return watermark_svc.apply_viewer_forensic_stamp(visible, session_id, _page_num)

    watermarked = await asyncio.get_running_loop().run_in_executor(None, _apply_all_watermarks, image_bytes)
    t2 = time.perf_counter()
    logger.info(
        "page_served doc=%s page=%d cache=%s fetch_ms=%.1f watermark_ms=%.1f req_id=%s",
        link_snap.document_id, page_number, cache_source,
        (t1 - t0) * 1000, (t2 - t1) * 1000,
        getattr(request.state, "request_id", "-"),
    )

    await analytics_svc.log_event(
        db,
        link_id=link_snap.id,
        event_type="page_viewed",
        page_number=page_number,
        session_id=session_id,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
        commit=True,
    )

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
@limiter.limit("120/minute")
async def get_thumb(
    request: Request,
    link_token: str,
    page_number: int,
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
    session_id = _get_session_id(request)
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

    # ── CDN offload: redirect to presigned R2 URL when enabled ───────────────
    thumb_key = f"thumbs/{link_snap.document_id}/{page_number:04d}.webp"
    storage = get_storage_service()

    if settings.cdn_thumbnail_enabled:
        try:
            presigned_url = await storage.generate_presigned_url(
                thumb_key,
                expires_in_seconds=settings.cdn_thumbnail_presign_ttl_sec,
            )
            from fastapi.responses import RedirectResponse as _Redirect
            return _Redirect(url=presigned_url, status_code=302,
                             headers={"Cache-Control": "no-store"})
        except NotImplementedError:
            pass  # backend doesn't support presigned URLs — fall through to proxy

    thumb_bytes, thumb_source = await fetch_thumb_bytes(thumb_key)
    if thumb_bytes is None:
        try:
            thumb_bytes = await storage.download_bytes(thumb_key)
            await store_thumb_bytes(thumb_key, thumb_bytes)
            thumb_source = "storage"
        except Exception:
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

    session_id = _get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

    file_type = doc_snap.file_type
    doc_id_str = str(link_snap.document_id)

    cached_toc = await get_cached_toc_async(doc_id_str)
    if cached_toc is not None:
        return _JSONResponse(
            content={"toc": cached_toc, "doc_type": file_type, "supported": True},
            headers={"Cache-Control": "no-store"},
        )

    toc_entries = []
    supported = True

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
            await store_toc_async(doc_id_str, [])
            return _JSONResponse(
                content={"toc": [], "doc_type": file_type, "supported": False},
                headers={"Cache-Control": "no-store"},
            )

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


@router.get("/download/{link_token}")
@limiter.limit("10/minute")
async def download_document(
    request: Request,
    link_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Download the document as a watermarked PDF (PDF docs) or plain text file (text docs).
    Requires an active session with can_download=true on the link.
    """
    import io as _io
    import os as _os
    import tempfile as _tempfile
    from PIL import Image as _Image

    session_id = _get_session_id(request)
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

    ip = getattr(request.state, "client_ip", None) or (request.client.host if request.client else None)
    if link.ip_allowlist:
        if not policy_enforcer.ip_is_allowed(ip, link.ip_allowlist):
            raise HTTPException(status_code=403, detail="Access denied from this IP")

    if not await policy_enforcer.is_active_session(db, link.id, session_id):
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    perms = json.loads(link.permissions) if link.permissions else {}
    if not perms.get("can_download", False):
        raise HTTPException(status_code=403, detail="Download not permitted on this link")

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

    from app.services.adapters import get_adapter as _get_adapter
    if _get_adapter(doc.file_type).viewer_mode == "text":
        raw = await storage.download_bytes(doc.storage_key)
        filename = doc.filename or f"document.{doc.file_type}"
        return FastAPIResponse(
            content=raw,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.txt"',
                "Cache-Control": "no-store",
            },
        )

    if not doc.page_count:
        raise HTTPException(status_code=404, detail="Document has no pages")

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

    from pypdf import PdfWriter, PdfReader
    loop = asyncio.get_running_loop()
    writer = PdfWriter()

    for page_row in page_rows:
        raw_bytes, _ = await fetch_page_bytes(page_row.storage_key)
        if raw_bytes is None:
            raw_bytes = await storage.download_bytes(page_row.storage_key)

        def _wm_and_encode(b: bytes) -> bytes:
            wm = watermark_svc.apply_visible_watermark(b, watermark_text)
            img = _Image.open(_io.BytesIO(wm)).convert("RGB")
            page_buf = _io.BytesIO()
            img.save(page_buf, format="PDF")
            return page_buf.getvalue()

        page_pdf_bytes = await loop.run_in_executor(None, _wm_and_encode, raw_bytes)
        reader = PdfReader(_io.BytesIO(page_pdf_bytes))
        writer.add_page(reader.pages[0])
        del page_pdf_bytes, reader

    filename = (doc.filename or "document").rsplit(".", 1)[0] + "_watermarked.pdf"

    tmp_fd, tmp_path = _tempfile.mkstemp(suffix=".pdf", prefix="sdoc_dl_")
    try:
        with _os.fdopen(tmp_fd, "wb") as tmp_f:
            writer.write(tmp_f)
        del writer
        total_size = _os.path.getsize(tmp_path)
    except Exception:
        _os.unlink(tmp_path)
        raise

    async def _stream_from_tmp():
        try:
            with open(tmp_path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    yield chunk
        finally:
            try:
                _os.unlink(tmp_path)
            except OSError:
                pass

    return StreamingResponse(
        _stream_from_tmp(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "Content-Length": str(total_size),
        },
    )


@router.get("/text/{link_token}/{chunk_number}")
@limiter.limit("120/minute")
async def get_text_chunk(
    request: Request,
    link_token: str,
    chunk_number: int,
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

    session_id = _get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    if chunk_number < 1:
        raise HTTPException(status_code=400, detail="chunk_number must be ≥ 1")

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

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

    viewer_email_masked = None
    if session_id:
        ip_hash = hash_value(ip) if ip else None
        viewer_email_masked = await policy_enforcer.upsert_session(
            db, session_id, link_snap.id, ip_hash=ip_hash
        )

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
        if len(cached_text) <= TEXT_CONTENT_MAX_BYTES:
            text_content_cache.put(storage_key, cached_text)

    _chunk_cache_key = f"{storage_key}:{settings.text_lines_per_chunk}"
    chunks: Optional[list] = chunk_array_cache.get(_chunk_cache_key)
    if chunks is None:
        chunks = chunk_text(cached_text, settings.text_lines_per_chunk)
        chunk_array_cache.put(_chunk_cache_key, chunks)

    total_chunks = len(chunks)
    if chunk_number > total_chunks:
        raise HTTPException(status_code=404, detail="Chunk not found")

    chunk_content = chunks[chunk_number - 1]

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


@router.get("/search/{link_token}")
@limiter.limit("30/minute")
async def search_document(
    request: Request,
    link_token: str,
    q: str = Query("", max_length=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Full-document text search — PDF, DOCX, and TXT formats.

    PDF/DOCX: loads text sidecar from storage (text/{doc_id}.json).
    TXT/MD/LOG: searches the text_content_cache.
    Response: { "results": [{page, snippet, offset}], "total": N, "query": str }
    """
    from fastapi.responses import JSONResponse as _JSONResponse

    session_id = _get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

    query = q.strip()
    if not query:
        return _JSONResponse(
            content={"results": [], "total": 0, "query": ""},
            headers={"Cache-Control": "no-store"},
        )

    file_type = doc_snap.file_type
    doc_id_str = str(link_snap.document_id)
    results = []
    ql = query.lower()

    if file_type in ("pdf", "docx", "doc"):
        sidecar_key = f"text/{doc_id_str}.json"
        try:
            _storage = get_storage_service()
            raw = await _storage.download_bytes(sidecar_key)
            pages_data = json.loads(raw.decode("utf-8"))
        except Exception:
            pages_data = []

        for entry in pages_data:
            text = entry.get("text", "")
            page_num = entry.get("page", 0)
            tl = text.lower()
            offset = 0
            while len(results) < 200:
                idx = tl.find(ql, offset)
                if idx == -1:
                    break
                start = max(0, idx - 60)
                end = min(len(text), idx + len(query) + 60)
                snippet = text[start:end].replace("\n", " ").strip()
                results.append({"page": page_num, "snippet": snippet, "offset": idx})
                offset = idx + len(query)
    else:
        storage_key = doc_snap.storage_key
        cached_text: Optional[str] = text_content_cache.get(storage_key)
        if cached_text is None:
            _storage = get_storage_service()
            try:
                raw_bytes = await _storage.download_bytes(storage_key)
            except Exception:
                raise HTTPException(status_code=503, detail="Document content temporarily unavailable")
            from app.services.text_processor import decode_text_safe
            cached_text = decode_text_safe(raw_bytes)
            if len(cached_text) <= TEXT_CONTENT_MAX_BYTES:
                text_content_cache.put(storage_key, cached_text)

        lines = cached_text.split("\n")
        chunk_size = settings.text_lines_per_chunk
        for chunk_num, chunk_start in enumerate(range(0, len(lines), chunk_size), start=1):
            chunk_text = "\n".join(lines[chunk_start:chunk_start + chunk_size])
            tl = chunk_text.lower()
            offset = 0
            while len(results) < 200:
                idx = tl.find(ql, offset)
                if idx == -1:
                    break
                start = max(0, idx - 60)
                end = min(len(chunk_text), idx + len(query) + 60)
                snippet = chunk_text[start:end].replace("\n", " ").strip()
                results.append({"page": chunk_num, "snippet": snippet, "offset": idx})
                offset = idx + len(query)

    return _JSONResponse(
        content={"results": results[:200], "total": len(results), "query": query},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@router.get("/links/{link_token}")
@limiter.limit("20/minute")
async def get_document_links(
    request: Request,
    link_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Return hyperlink annotation metadata for the document.

    Loaded from links/{doc_id}.json (created at processing time). Returns
    {pages: [{page, links: [{x,y,w,h,url}]}]} with normalized coordinates.
    Returns empty pages list when no sidecar exists (no links in doc).
    """
    from fastapi.responses import JSONResponse as _JSONResponse

    session_id = _get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

    doc_id_str = str(link_snap.document_id)
    sidecar_key = f"links/{doc_id_str}.json"
    try:
        _storage = get_storage_service()
        raw = await _storage.download_bytes(sidecar_key)
        raw_data = json.loads(raw.decode("utf-8"))
        # Support both old format (bare array) and new format ({"pages":[], "extracted":true})
        if isinstance(raw_data, list):
            pages_data = raw_data
            extracted = False
        else:
            pages_data = raw_data.get("pages", [])
            extracted = raw_data.get("extracted", False)
    except Exception:
        pages_data = []
        extracted = False

    return _JSONResponse(
        content={"pages": pages_data, "extracted": extracted},
        headers={"Cache-Control": "no-store"},
    )


@router.get("/words/{link_token}")
@limiter.limit("10/minute")
async def get_word_positions(
    request: Request,
    link_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Return word-level bounding boxes for search highlighting.

    Loaded from words/{doc_id}.json (created at processing time). Returns
    {pages: [{page, words: [{t,x,y,w,h}]}]} with normalized coordinates.
    Returns empty pages list when no sidecar exists.
    """
    from fastapi.responses import JSONResponse as _JSONResponse

    session_id = _get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    link_snap, doc_snap, ip, now = await _get_cached_link_and_doc(link_token, db, request)

    if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

    doc_id_str = str(link_snap.document_id)
    sidecar_key = f"words/{doc_id_str}.json"
    try:
        _storage = get_storage_service()
        raw = await _storage.download_bytes(sidecar_key)
        pages_data = json.loads(raw.decode("utf-8"))
    except Exception:
        pages_data = []

    return _JSONResponse(
        content={"pages": pages_data},
        headers={"Cache-Control": "no-store"},
    )
