"""Viewer annotation API.

Public viewer endpoints (require active session + can_annotate permission):
  GET  /api/viewer/annotations/{token}/{page}     — fetch page annotations
  POST /api/viewer/annotations/{token}            — create annotation
  PUT  /api/viewer/annotations/{token}/{id}       — update own annotation
  DELETE /api/viewer/annotations/{token}/{id}     — delete own annotation

  GET  /api/viewer/bookmarks/{token}              — fetch all bookmarks for session
  POST /api/viewer/bookmarks/{token}/{page}       — toggle bookmark (create or delete)

Uploader export (requires JWT auth + document ownership):
  GET  /api/documents/{doc_id}/annotations/export — CSV export of all annotations
"""
import csv
import io
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.annotation import ViewerAnnotation, ViewerBookmark, VALID_ANNOTATION_TYPES
from app.models.document import Document
from app.models.link import ShareLink
from app.services.policy import enforcer as policy_enforcer
from app.services.viewer_cache import link_cache, LinkSnapshot

logger = logging.getLogger(__name__)

router = APIRouter(tags=["annotations"])

# ── Pydantic schemas ──────────────────────────────────────────────────────────

_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{3,8}$")
_MAX_COMMENT_LEN = 2000


class AnnotationCreate(BaseModel):
    page_number: int
    annotation_type: str
    coords: dict
    color: Optional[str] = "#FFFF00"
    comment_text: Optional[str] = None

    @field_validator("annotation_type")
    @classmethod
    def check_type(cls, v):
        if v not in VALID_ANNOTATION_TYPES:
            raise ValueError(f"annotation_type must be one of {sorted(VALID_ANNOTATION_TYPES)}")
        return v

    @field_validator("coords")
    @classmethod
    def check_coords(cls, v):
        # Accept either {x,y,w,h} or {x1,y1,x2,y2} or {x,y} — all floats 0–1
        allowed_keys = {frozenset(["x", "y", "w", "h"]), frozenset(["x1", "y1", "x2", "y2"]), frozenset(["x", "y"])}
        if frozenset(v.keys()) not in allowed_keys:
            raise ValueError("coords must contain {x,y,w,h}, {x1,y1,x2,y2}, or {x,y}")
        for key, val in v.items():
            if not isinstance(val, (int, float)) or not (0.0 <= float(val) <= 1.0):
                raise ValueError(f"coords.{key} must be a float between 0 and 1")
        return v

    @field_validator("color")
    @classmethod
    def check_color(cls, v):
        if v is not None and not _HEX_COLOR.match(v):
            raise ValueError("color must be a hex color (e.g. #FFFF00)")
        return v

    @field_validator("comment_text")
    @classmethod
    def check_comment(cls, v):
        if v is not None and len(v) > _MAX_COMMENT_LEN:
            raise ValueError(f"comment_text must be ≤ {_MAX_COMMENT_LEN} characters")
        return v


class AnnotationUpdate(BaseModel):
    comment_text: Optional[str] = None
    color: Optional[str] = None
    coords: Optional[dict] = None

    @field_validator("color")
    @classmethod
    def check_color(cls, v):
        if v is not None and not _HEX_COLOR.match(v):
            raise ValueError("color must be a hex color")
        return v

    @field_validator("comment_text")
    @classmethod
    def check_comment(cls, v):
        if v is not None and len(v) > _MAX_COMMENT_LEN:
            raise ValueError(f"comment_text must be ≤ {_MAX_COMMENT_LEN} characters")
        return v


class BookmarkCreate(BaseModel):
    label: Optional[str] = None


# ── Shared auth helpers ───────────────────────────────────────────────────────

def _get_session_id(request: Request) -> Optional[str]:
    sid = request.headers.get("X-Session-ID", "").strip()
    if sid:
        return sid
    return request.cookies.get("sdoc_session", "").strip() or None


async def _resolve_link_and_verify_session(
    token: str,
    request: Request,
    db: AsyncSession,
    require_annotate: bool = True,
) -> tuple:
    """
    Resolve link from token, verify the session is active, and (optionally)
    confirm can_annotate is enabled.  Returns (link_row, session_id).
    """
    session_id = _get_session_id(request)
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    # Link lookup — use cache when warm
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

    # Session validity
    is_active = await policy_enforcer.is_active_session(db, snap.id, session_id)
    if not is_active:
        raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")

    # Permission check
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


def _serialize_annotation(a: ViewerAnnotation) -> dict:
    return {
        "id": a.id,
        "page_number": a.page_number,
        "annotation_type": a.annotation_type,
        "coords": json.loads(a.coords),
        "color": a.color,
        "comment_text": a.comment_text,
        "session_id": a.session_id[:6] + "…",  # only the prefix — never expose full session IDs
        "viewer_email_masked": a.viewer_email_masked,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


# ── GET annotations for page ──────────────────────────────────────────────────

@router.get("/api/viewer/annotations/{token}/{page_number}")
@limiter.limit("120/minute")
async def get_page_annotations(
    request: Request,
    token: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
):
    """Return all annotations for a page.  Any viewer with a valid session and
    can_annotate permission can read all annotations (collaborative review)."""
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)
    if page_number < 1:
        raise HTTPException(status_code=422, detail="page_number must be ≥ 1")

    rows = (
        await db.execute(
            select(ViewerAnnotation)
            .where(
                ViewerAnnotation.link_id == str(link_row.id),
                ViewerAnnotation.page_number == page_number,
            )
            .order_by(ViewerAnnotation.created_at)
        )
    ).scalars().all()

    return {
        "page_number": page_number,
        "annotations": [_serialize_annotation(a) for a in rows],
        # Flag which annotations belong to the requesting viewer so the UI
        # can show edit/delete controls only for the owner's own annotations.
        "own_session_prefix": session_id[:6],
    }


# ── POST create annotation ────────────────────────────────────────────────────

@router.post("/api/viewer/annotations/{token}", status_code=201)
@limiter.limit("60/minute")
async def create_annotation(
    request: Request,
    token: str,
    body: AnnotationCreate,
    db: AsyncSession = Depends(get_db),
):
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)

    # Validate page number against document page count
    from app.models.document import Document
    doc = (await db.execute(select(Document).where(Document.id == link_row.document_id))).scalar_one_or_none()
    if doc and doc.page_count and not (1 <= body.page_number <= doc.page_count):
        raise HTTPException(status_code=422, detail=f"page_number must be 1–{doc.page_count}")

    # Resolve masked email from the active session row
    from app.models.session import ViewerSession
    sess_row = await db.get(ViewerSession, session_id)
    masked_email = sess_row.viewer_email_masked if sess_row else None

    annot = ViewerAnnotation(
        link_id=str(link_row.id),
        session_id=session_id,
        viewer_email_masked=masked_email,
        page_number=body.page_number,
        annotation_type=body.annotation_type,
        coords=json.dumps(body.coords),
        color=body.color or "#FFFF00",
        comment_text=body.comment_text,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(annot)
    await db.commit()
    await db.refresh(annot)

    logger.info(
        "[annotation] created link=%s session=%s… page=%d type=%s",
        link_row.id, session_id[:6], body.page_number, body.annotation_type,
    )
    return _serialize_annotation(annot)


# ── PUT update own annotation ─────────────────────────────────────────────────

@router.put("/api/viewer/annotations/{token}/{annotation_id}")
@limiter.limit("60/minute")
async def update_annotation(
    request: Request,
    token: str,
    annotation_id: str,
    body: AnnotationUpdate,
    db: AsyncSession = Depends(get_db),
):
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)

    annot = await db.get(ViewerAnnotation, annotation_id)
    if annot is None or str(annot.link_id) != str(link_row.id):
        raise HTTPException(status_code=404, detail="Annotation not found")
    if annot.session_id != session_id:
        raise HTTPException(status_code=403, detail="Cannot modify another viewer's annotation")

    if body.comment_text is not None:
        annot.comment_text = body.comment_text
    if body.color is not None:
        annot.color = body.color
    if body.coords is not None:
        annot.coords = json.dumps(body.coords)
    annot.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(annot)
    return _serialize_annotation(annot)


# ── DELETE own annotation ─────────────────────────────────────────────────────

@router.delete("/api/viewer/annotations/{token}/{annotation_id}", status_code=204)
@limiter.limit("60/minute")
async def delete_annotation(
    request: Request,
    token: str,
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
):
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)

    annot = await db.get(ViewerAnnotation, annotation_id)
    if annot is None or str(annot.link_id) != str(link_row.id):
        raise HTTPException(status_code=404, detail="Annotation not found")
    if annot.session_id != session_id:
        raise HTTPException(status_code=403, detail="Cannot delete another viewer's annotation")

    await db.delete(annot)
    await db.commit()


# ── GET bookmarks for session ─────────────────────────────────────────────────

@router.get("/api/viewer/bookmarks/{token}")
@limiter.limit("60/minute")
async def get_bookmarks(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)

    rows = (
        await db.execute(
            select(ViewerBookmark)
            .where(
                ViewerBookmark.link_id == str(link_row.id),
                ViewerBookmark.session_id == session_id,
            )
            .order_by(ViewerBookmark.page_number)
        )
    ).scalars().all()

    return {
        "bookmarks": [
            {"id": b.id, "page_number": b.page_number, "label": b.label,
             "created_at": b.created_at.isoformat() if b.created_at else None}
            for b in rows
        ]
    }


# ── POST toggle bookmark ──────────────────────────────────────────────────────

@router.post("/api/viewer/bookmarks/{token}/{page_number}")
@limiter.limit("60/minute")
async def toggle_bookmark(
    request: Request,
    token: str,
    page_number: int,
    body: BookmarkCreate = BookmarkCreate(),
    db: AsyncSession = Depends(get_db),
):
    """Create bookmark if not present, delete if already bookmarked (toggle)."""
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)

    existing = (
        await db.execute(
            select(ViewerBookmark).where(
                ViewerBookmark.link_id == str(link_row.id),
                ViewerBookmark.session_id == session_id,
                ViewerBookmark.page_number == page_number,
            )
        )
    ).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        return {"action": "removed", "page_number": page_number}

    bm = ViewerBookmark(
        link_id=str(link_row.id),
        session_id=session_id,
        page_number=page_number,
        label=body.label,
        created_at=datetime.now(timezone.utc),
    )
    db.add(bm)
    await db.commit()
    await db.refresh(bm)
    return {
        "action": "added",
        "id": bm.id,
        "page_number": bm.page_number,
        "label": bm.label,
    }


# ── Uploader export ───────────────────────────────────────────────────────────

@router.get("/api/documents/{doc_id}/annotations/export")
@limiter.limit("10/minute")
async def export_annotations(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Export all annotations for a document as CSV.  Only the document owner
    (authenticated uploader) can access this endpoint."""
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(doc.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Collect all annotations across all links for this document
    from sqlalchemy import text as _sql
    rows = (
        await db.execute(
            select(
                ViewerAnnotation.id,
                ViewerAnnotation.session_id,
                ViewerAnnotation.viewer_email_masked,
                ViewerAnnotation.page_number,
                ViewerAnnotation.annotation_type,
                ViewerAnnotation.comment_text,
                ViewerAnnotation.created_at,
                ShareLink.label.label("link_label"),
            )
            .join(ShareLink, ShareLink.id == ViewerAnnotation.link_id)
            .where(ShareLink.document_id == doc.id)
            .order_by(ViewerAnnotation.created_at)
        )
    ).all()

    def _generate_csv():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "annotation_id", "link_label", "viewer_email_masked",
            "session_prefix", "page_number", "annotation_type",
            "comment_text", "created_at",
        ])
        for r in rows:
            writer.writerow([
                r.id,
                r.link_label or "",
                r.viewer_email_masked or "anonymous",
                r.session_id[:6] if r.session_id else "",
                r.page_number,
                r.annotation_type,
                r.comment_text or "",
                r.created_at.isoformat() if r.created_at else "",
            ])
        yield buf.getvalue()

    filename = f"annotations_{doc_id[:8]}.csv"
    return StreamingResponse(
        _generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
