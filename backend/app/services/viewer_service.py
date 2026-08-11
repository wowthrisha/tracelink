"""Viewer infrastructure helpers — link/doc validation, cache utilities, watermark angle."""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request

from app.config import settings
from app.services.page_cache import (
    clear_local_page_cache,
    clear_local_thumb_cache,
)

logger = logging.getLogger(__name__)


def _session_watermark_angle(session_id: str, base: float = -32.0) -> float:
    """Deterministic but session-unique watermark tilt angle within ±jitter_deg of base."""
    h = int(hashlib.sha256(session_id.encode()).hexdigest()[:8], 16)
    norm = (h % 10000) / 10000.0
    jitter = settings.watermark_angle_jitter_deg
    return base + (norm - 0.5) * 2.0 * jitter


def _check_link_active(link, now: datetime) -> None:
    """Raise 410 if the link is revoked or expired."""
    if link.revoked_at is not None:
        raise HTTPException(status_code=410, detail="Link revoked")
    if link.expires_at is not None:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise HTTPException(status_code=410, detail="Link expired")


def _check_doc_not_expired(doc, now: datetime) -> None:
    """Raise 410 if the document itself has passed its retention expiry.

    BUG-004: retention expiry (Document.expires_at / lifecycle_state, set by
    the storage/retention policy — distinct from ShareLink.expires_at) was
    previously enforced only by the daily cleanup job eventually deleting the
    row, leaving up to a 24h window (or longer if the job doesn't run) where
    an expired document was still fully viewable through any still-valid
    share link. This check makes expiry immediate at the access layer,
    matching how link expiry is already enforced in _check_link_active.
    """
    if getattr(doc, "lifecycle_state", "active") in ("expired", "deleted"):
        raise HTTPException(status_code=410, detail="Document expired")
    expires = getattr(doc, "expires_at", None)
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise HTTPException(status_code=410, detail="Document expired")


def _check_doc_ready(doc) -> None:
    """Raise 503 if the document is not yet ready."""
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


def _get_session_id(request: Request) -> Optional[str]:
    """Resolve session_id from header or cookie only — never from query parameters."""
    sid = request.headers.get("X-Session-ID", "").strip()
    if sid:
        return sid
    return request.cookies.get("sdoc_session", "").strip() or None


async def _load_toc_sidecar(sidecar_key: str):
    """Load a JSON TOC sidecar from storage. Returns list or None if absent."""
    import json as _json
    try:
        from app.services.storage import get_storage_service
        storage = get_storage_service()
        raw = await storage.download_bytes(sidecar_key)
        return _json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def clear_page_cache() -> None:
    """Flush the process-local page byte cache. Called in tests."""
    clear_local_page_cache()


def clear_thumb_cache() -> None:
    """Flush the process-local thumbnail byte cache. Called in tests."""
    clear_local_thumb_cache()


def clear_metadata_caches() -> None:
    """Flush the link/doc/page TTL metadata caches. Called in tests."""
    from app.services.viewer_cache import clear_all_caches
    clear_all_caches()
