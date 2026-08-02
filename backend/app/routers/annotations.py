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
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.metrics import annotations_total
from app.middleware.rate_limit import limiter
from app.models.annotation import VALID_ANNOTATION_TYPES
from app.routers.documents import _get_accessible_document
from app.services.annotation_service import (
    _resolve_link_and_verify_session,
    _serialize_annotation,
    _resolve_display_name,
)
from app.services.annotation_thread_service import (
    fetch_thread,
    create_uploader_reply,
    fetch_feedback_list,
    fetch_feedback_reviewers,
)
from app.services.annotation_export_service import (
    build_annotations_export,
    build_feedback_export,
    build_reviewer_activity_export,
    build_visual_annotations_export,
)
from app.services.viewer_annotation_service import (
    fetch_page_annotations,
    create_viewer_annotation,
    update_viewer_annotation,
    delete_viewer_annotation,
    toggle_resolve_annotation,
    fetch_document_annotations,
    fetch_visual_annotations,
)
from app.services.viewer_bookmark_service import (
    fetch_bookmarks,
    toggle_bookmark,
)

# Re-exported for test-import compatibility
__all__ = [
    "_serialize_annotation",
    "_resolve_display_name",
]

logger = __import__("logging").getLogger(__name__)

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
    thickness: Optional[int] = 2
    parent_id: Optional[str] = None

    @field_validator("annotation_type")
    @classmethod
    def check_type(cls, v):
        if v not in VALID_ANNOTATION_TYPES:
            raise ValueError(f"annotation_type must be one of {sorted(VALID_ANNOTATION_TYPES)}")
        return v

    @field_validator("coords")
    @classmethod
    def check_coords(cls, v):
        # draw annotations send {points: [{x, y}, ...]} — validate separately
        if frozenset(v.keys()) == frozenset(["points"]):
            pts = v["points"]
            if not isinstance(pts, list) or len(pts) < 2:
                raise ValueError("coords.points must be a list of at least 2 {x,y} objects")
            for i, p in enumerate(pts):
                if not isinstance(p, dict) or set(p.keys()) != {"x", "y"}:
                    raise ValueError(f"coords.points[{i}] must be {{x, y}}")
                for k in ("x", "y"):
                    if not isinstance(p[k], (int, float)) or not (0.0 <= float(p[k]) <= 1.0):
                        raise ValueError(f"coords.points[{i}].{k} must be a float 0–1")
            return v
        # Accept {x,y,w,h}, {x1,y1,x2,y2}, or {x,y} — all floats 0–1
        allowed_keys = {
            frozenset(["x", "y", "w", "h"]),
            frozenset(["x1", "y1", "x2", "y2"]),
            frozenset(["x", "y"]),
        }
        if frozenset(v.keys()) not in allowed_keys:
            raise ValueError("coords must contain {x,y,w,h}, {x1,y1,x2,y2}, {x,y}, or {points:[{x,y}...]}")
        for key, val in v.items():
            if not isinstance(val, (int, float)) or not (0.0 <= float(val) <= 1.0):
                raise ValueError(f"coords.{key} must be a float between 0 and 1")
        return v

    @field_validator("thickness")
    @classmethod
    def check_thickness(cls, v):
        if v is not None and (not isinstance(v, int) or v < 1 or v > 20):
            raise ValueError("thickness must be an integer between 1 and 20")
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


class AnnotationReplyCreate(BaseModel):
    comment_text: str

    @field_validator("comment_text")
    @classmethod
    def check_comment(cls, v):
        if not v or not v.strip():
            raise ValueError("comment_text is required")
        if len(v) > _MAX_COMMENT_LEN:
            raise ValueError(f"comment_text must be ≤ {_MAX_COMMENT_LEN} characters")
        return v


# ── GET annotations for page ──────────────────────────────────────────────────

@router.get("/api/viewer/annotations/{token}/{page_number}")
@limiter.limit("120/minute")
async def get_page_annotations(
    request: Request,
    token: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
):
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)
    return await fetch_page_annotations(db, str(link_row.id), session_id, page_number)


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
    result = await create_viewer_annotation(db, link_row, session_id, body)
    annotations_total.labels(annotation_type=body.type, action="create").inc()
    return result


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
    return await update_viewer_annotation(db, link_row, session_id, annotation_id, body)


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
    await delete_viewer_annotation(db, link_row, session_id, annotation_id)
    annotations_total.labels(annotation_type="unknown", action="delete").inc()


# ── GET bookmarks for session ─────────────────────────────────────────────────

@router.get("/api/viewer/bookmarks/{token}")
@limiter.limit("60/minute")
async def get_bookmarks(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)
    return await fetch_bookmarks(db, str(link_row.id), session_id)


# ── POST toggle bookmark ──────────────────────────────────────────────────────

@router.post("/api/viewer/bookmarks/{token}/{page_number}")
@limiter.limit("60/minute")
async def toggle_bookmark_route(
    request: Request,
    token: str,
    page_number: int,
    body: BookmarkCreate = BookmarkCreate(),
    db: AsyncSession = Depends(get_db),
):
    """Create bookmark if not present, delete if already bookmarked (toggle)."""
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)
    return await toggle_bookmark(db, str(link_row.id), session_id, page_number, body.label)


# ── Resolve annotation (any viewer session on this link — not owner-restricted;
#    the owner-restricted equivalent is resolve_feedback() below, gated by
#    document ownership) ────────────────────────────────────────────────────

@router.patch("/api/viewer/annotations/{token}/{annotation_id}/resolve")
@limiter.limit("60/minute")
async def resolve_annotation(
    request: Request,
    token: str,
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
):
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)
    return await toggle_resolve_annotation(db, link_row, annotation_id)


# ── Uploader: list all annotations for a document (JSON) ─────────────────────

@router.get("/api/documents/{doc_id}/annotations")
@limiter.limit("30/minute")
async def list_document_annotations(
    request: Request,
    doc_id: str,
    annotation_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    return await fetch_document_annotations(db, doc, annotation_type, resolved)


# ── Uploader export ───────────────────────────────────────────────────────────

@router.get("/api/documents/{doc_id}/annotations/export")
@limiter.limit("10/minute")
async def export_annotations(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    gen, filename = await build_annotations_export(db, doc)
    return StreamingResponse(
        gen, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Viewer: get annotation thread ─────────────────────────────────────────────

@router.get("/api/viewer/annotations/{token}/{annotation_id}/thread")
@limiter.limit("60/minute")
async def get_annotation_thread(
    request: Request,
    token: str,
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return an annotation and all its depth-1 replies.
    Viewer auth only — requires active session (can_annotate not required)."""
    from app.models.annotation import ViewerAnnotation
    link_row, session_id = await _resolve_link_and_verify_session(
        token, request, db, require_annotate=False
    )
    root = await db.get(ViewerAnnotation, annotation_id)
    if root is None or str(root.link_id) != str(link_row.id):
        raise HTTPException(status_code=404, detail="Annotation not found")
    return await fetch_thread(db, root, link_row, session_id)


# ── Uploader: reply to a feedback thread (dashboard JWT, no viewer session) ──

@router.post("/api/documents/{doc_id}/feedback/{annotation_id}/reply", status_code=201)
@limiter.limit("30/minute")
async def reply_to_feedback(
    request: Request,
    doc_id: str,
    annotation_id: str,
    body: AnnotationReplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Uploader reply to a viewer's feedback thread.

    Authenticated via the dashboard JWT only — deliberately independent of
    any viewer share-link session.
    """
    from app.models.annotation import ViewerAnnotation
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    target = await db.get(ViewerAnnotation, annotation_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return await create_uploader_reply(db, target, doc, body.comment_text, current_user)


# ── Uploader: resolve / unresolve a feedback thread ─────────────────────────

@router.patch("/api/documents/{doc_id}/feedback/{annotation_id}/resolve")
@limiter.limit("30/minute")
async def resolve_feedback(
    request: Request,
    doc_id: str,
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models.annotation import ViewerAnnotation
    from app.models.link import ShareLink
    from datetime import datetime, timezone
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    annot = await db.get(ViewerAnnotation, annotation_id)
    if annot is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    link = await db.get(ShareLink, annot.link_id)
    if link is None or str(link.document_id) != str(doc.id):
        raise HTTPException(status_code=404, detail="Annotation not found")
    annot.resolved_at = None if annot.resolved_at is not None else datetime.now(timezone.utc)
    annot.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(annot)
    from app.services.annotation_service import _serialize_annotation
    return _serialize_annotation(annot)


# ── Uploader: list feedback (comment + sticky_note) ───────────────────────────

@router.get("/api/documents/{doc_id}/feedback")
@limiter.limit("30/minute")
async def list_document_feedback(
    request: Request,
    doc_id: str,
    resolved: Optional[bool] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page_number: Optional[int] = None,
    author_role: Optional[str] = None,
    reviewer: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    return await fetch_feedback_list(
        db, doc, resolved, search, date_from, date_to, page_number, author_role, reviewer
    )


# ── Uploader: distinct reviewers for the Feedback filter dropdown ────────────

@router.get("/api/documents/{doc_id}/feedback/reviewers")
@limiter.limit("30/minute")
async def list_feedback_reviewers(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    return await fetch_feedback_reviewers(db, doc)


# ── Uploader: feedback CSV export ─────────────────────────────────────────────

@router.get("/api/documents/{doc_id}/feedback/export")
@limiter.limit("10/minute")
async def export_feedback(
    request: Request,
    doc_id: str,
    resolved: Optional[bool] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page_number: Optional[int] = None,
    author_role: Optional[str] = None,
    reviewer: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    gen, filename = await build_feedback_export(
        db, doc, resolved, search, date_from, date_to, page_number, author_role, reviewer
    )
    return StreamingResponse(
        gen, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Uploader: reviewer activity CSV export ────────────────────────────────────

@router.get("/api/documents/{doc_id}/feedback/export-reviewer-activity")
@limiter.limit("10/minute")
async def export_reviewer_activity(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    gen, filename = await build_reviewer_activity_export(db, doc)
    return StreamingResponse(
        gen, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Uploader: list visual annotations only ────────────────────────────────────

@router.get("/api/documents/{doc_id}/annotations-visual")
@limiter.limit("30/minute")
async def list_visual_annotations(
    request: Request,
    doc_id: str,
    annotation_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List only ANNOTATION_TYPES (highlight/draw/rectangle/arrow). Document owner only."""
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    return await fetch_visual_annotations(db, doc, annotation_type)


# ── Uploader: visual annotations CSV export ───────────────────────────────────

@router.get("/api/documents/{doc_id}/annotations-visual/export")
@limiter.limit("10/minute")
async def export_visual_annotations(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Export visual annotations (highlight/draw/rectangle/arrow) as CSV. Document owner only."""
    try:
        doc_uuid = doc_id if isinstance(doc_id, uuid.UUID) else uuid.UUID(doc_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await _get_accessible_document(doc_uuid, current_user, db)
    gen, filename = await build_visual_annotations_export(db, doc)
    return StreamingResponse(
        gen, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
