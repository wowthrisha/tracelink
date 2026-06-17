"""Core annotation auth helpers, display-name resolution, and serialization."""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import ViewerAnnotation
from app.models.link import ShareLink
from app.models.viewer_profile import ViewerProfile
from app.services.policy import enforcer as policy_enforcer
from app.services.viewer_cache import link_cache, LinkSnapshot
from app.services.viewer_profile import derive_display_name

logger = logging.getLogger(__name__)

_UPLOADER_SESSION_PREFIX = "uploader:"


def _get_session_id(request: Request) -> Optional[str]:
    sid = request.headers.get("X-Session-ID", "").strip()
    if sid:
        return sid
    return request.cookies.get("sdoc_session", "").strip() or None


def _is_uploader_row(session_id: Optional[str]) -> bool:
    return bool(session_id and session_id.startswith(_UPLOADER_SESSION_PREFIX))


def _resolve_display_name(
    session_id: Optional[str],
    viewer_email: Optional[str],
    profile_display_name: Optional[str] = None,
) -> str:
    """Best-effort human name for an annotation/reply row."""
    if _is_uploader_row(session_id):
        return derive_display_name(viewer_email) if viewer_email else "Document Owner"
    if profile_display_name:
        return profile_display_name
    if viewer_email:
        return derive_display_name(viewer_email)
    return "Anonymous Viewer"


async def _profile_display_names(db: AsyncSession, annotations) -> dict:
    """Batch-resolve ViewerProfile.display_name, avoiding one query per row."""
    ids = {str(a.viewer_profile_id) for a in annotations if a.viewer_profile_id}
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(ViewerProfile.id, ViewerProfile.display_name).where(ViewerProfile.id.in_(ids))
        )
    ).all()
    return {str(r.id): r.display_name for r in rows}


def _serialize_annotation(
    a: ViewerAnnotation,
    profile_display_name: Optional[str] = None,
    full_identity: bool = False,
) -> dict:
    d = {
        "id": str(a.id),
        "page_number": a.page_number,
        "annotation_type": a.annotation_type,
        "coords": json.loads(a.coords),
        "color": a.color,
        "comment_text": a.comment_text,
        "thickness": a.thickness,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "parent_id": str(a.parent_id) if a.parent_id else None,
        "session_id": (a.session_id[:6] + "…") if a.session_id else None,
        "viewer_email_masked": a.viewer_email_masked,
        "display_name": _resolve_display_name(a.session_id, a.viewer_email, profile_display_name),
        "author_role": "uploader" if _is_uploader_row(a.session_id) else "viewer",
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
    # Full plaintext identity is only returned to document-owner endpoints.
    if full_identity:
        d["viewer_profile_id"] = str(a.viewer_profile_id) if a.viewer_profile_id else None
        d["viewer_email"] = a.viewer_email
    return d


async def _resolve_link_and_verify_session(
    token: str,
    request: Request,
    db: AsyncSession,
    require_annotate: bool = True,
) -> tuple:
    """Resolve link from token, verify session is active, check can_annotate.
    Returns (link_row, session_id)."""
    session_id = _get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    snap: Optional[LinkSnapshot] = link_cache.get(token)
    if snap is None:
        row = (await db.execute(select(ShareLink).where(ShareLink.token == token))).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Link not found")
        snap = LinkSnapshot(
            id=row.id, token=row.token, document_id=row.document_id,
            revoked_at=row.revoked_at, expires_at=row.expires_at,
            ip_allowlist=row.ip_allowlist,
        )
        link_cache.put(token, snap)

    now = datetime.now(timezone.utc)
    if snap.revoked_at is not None:
        raise HTTPException(status_code=410, detail="Link revoked")
    if snap.expires_at is not None:
        exp = snap.expires_at if snap.expires_at.tzinfo else snap.expires_at.replace(tzinfo=timezone.utc)
        if exp < now:
            raise HTTPException(status_code=410, detail="Link expired")

    is_active = await policy_enforcer.is_active_session(db, snap.id, session_id)
    if not is_active:
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

    if require_annotate:
        link_row = (await db.execute(select(ShareLink).where(ShareLink.id == snap.id))).scalar_one_or_none()
        if link_row is None:
            raise HTTPException(status_code=404, detail="Link not found")
        perms = json.loads(link_row.permissions) if link_row.permissions else {}
        if not perms.get("can_annotate", False):
            raise HTTPException(status_code=403, detail="Annotations are not enabled for this link")
        return link_row, session_id

    link_row = (await db.execute(select(ShareLink).where(ShareLink.id == snap.id))).scalar_one_or_none()
    return link_row, session_id
