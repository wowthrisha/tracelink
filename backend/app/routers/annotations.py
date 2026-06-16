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
from app.models.annotation import ViewerAnnotation, ViewerBookmark, VALID_ANNOTATION_TYPES, FEEDBACK_TYPES, ANNOTATION_TYPES
from app.models.document import Document
from app.models.link import ShareLink
from app.models.viewer_profile import ViewerProfile
from app.services.policy import enforcer as policy_enforcer
from app.services.viewer_cache import link_cache, LinkSnapshot
from app.services.viewer_profile import derive_display_name

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


_UPLOADER_SESSION_PREFIX = "uploader:"


def _is_uploader_row(session_id: Optional[str]) -> bool:
    return bool(session_id and session_id.startswith(_UPLOADER_SESSION_PREFIX))


def _resolve_display_name(
    session_id: Optional[str],
    viewer_email: Optional[str],
    profile_display_name: Optional[str] = None,
) -> str:
    """Best-effort human name for an annotation/reply row.

    Uploader replies (session_id prefixed "uploader:") have no ViewerProfile —
    derive a name from the uploader's own email, or fall back to a generic
    label. Viewer rows prefer the persisted ViewerProfile.display_name (lets
    a future profile-edit feature override the heuristic) before falling back
    to deriving one from the email, then to "Anonymous Viewer".
    """
    if _is_uploader_row(session_id):
        return derive_display_name(viewer_email) if viewer_email else "Document Owner"
    if profile_display_name:
        return profile_display_name
    if viewer_email:
        return derive_display_name(viewer_email)
    return "Anonymous Viewer"


async def _profile_display_names(db: AsyncSession, annotations) -> dict:
    """Batch-resolve ViewerProfile.display_name for a list of annotation rows,
    avoiding one query per row."""
    ids = {str(a.viewer_profile_id) for a in annotations if a.viewer_profile_id}
    if not ids:
        return {}
    rows = (
        await db.execute(select(ViewerProfile.id, ViewerProfile.display_name).where(ViewerProfile.id.in_(ids)))
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
        "session_id": (a.session_id[:6] + "…") if a.session_id else None,  # only the prefix — never expose full session IDs
        "viewer_email_masked": a.viewer_email_masked,
        "display_name": _resolve_display_name(a.session_id, a.viewer_email, profile_display_name),
        "author_role": "uploader" if _is_uploader_row(a.session_id) else "viewer",
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }
    # Full plaintext identity (viewer_email, viewer_profile_id) is only ever
    # returned to document-owner/admin-authenticated endpoints — never to the
    # public viewer-facing annotation/thread endpoints.
    if full_identity:
        d["viewer_profile_id"] = str(a.viewer_profile_id) if a.viewer_profile_id else None
        d["viewer_email"] = a.viewer_email
    return d


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

    names = await _profile_display_names(db, rows)
    return {
        "page_number": page_number,
        "annotations": [_serialize_annotation(a, profile_display_name=names.get(str(a.viewer_profile_id))) for a in rows],
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

    # Guard: visual annotations cannot have replies. Also normalize parent_id
    # to the thread root so replies never nest more than one level deep —
    # matches get_annotation_thread, which only fetches depth-1 replies.
    if body.parent_id:
        parent_annot = await db.get(ViewerAnnotation, body.parent_id)
        if parent_annot is not None and parent_annot.annotation_type in ANNOTATION_TYPES:
            raise HTTPException(
                status_code=422,
                detail="Visual annotations (highlight/draw/rectangle/arrow) cannot have replies",
            )
        if parent_annot is not None and parent_annot.parent_id:
            body.parent_id = str(parent_annot.parent_id)

    # Validate page number against document page count
    from app.models.document import Document
    doc = (await db.execute(select(Document).where(Document.id == link_row.document_id))).scalar_one_or_none()
    if doc and doc.page_count and not (1 <= body.page_number <= doc.page_count):
        raise HTTPException(status_code=422, detail=f"page_number must be 1–{doc.page_count}")

    # Resolve viewer identity from the active session row
    from app.models.session import ViewerSession
    sess_row = await db.get(ViewerSession, session_id)
    masked_email = sess_row.viewer_email_masked if sess_row else None
    plain_email = sess_row.viewer_email if sess_row else None
    profile_id = sess_row.viewer_profile_id if sess_row else None

    annot = ViewerAnnotation(
        link_id=str(link_row.id),
        session_id=session_id,
        viewer_email_masked=masked_email,
        viewer_email=plain_email,
        viewer_profile_id=profile_id,
        page_number=body.page_number,
        annotation_type=body.annotation_type,
        coords=json.dumps(body.coords),
        color=body.color or "#FFFF00",
        comment_text=body.comment_text,
        thickness=body.thickness or 2,
        parent_id=body.parent_id or None,
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


# ── Resolve annotation (uploader-facing) ─────────────────────────────────────

@router.patch("/api/viewer/annotations/{token}/{annotation_id}/resolve")
@limiter.limit("60/minute")
async def resolve_annotation(
    request: Request,
    token: str,
    annotation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Toggle the resolved_at timestamp on an annotation.  Any session holder with
    can_annotate can mark a comment resolved; the link owner (via uploader) can
    do so from the dashboard via the JSON list endpoint."""
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db)

    annot = await db.get(ViewerAnnotation, annotation_id)
    if annot is None or str(annot.link_id) != str(link_row.id):
        raise HTTPException(status_code=404, detail="Annotation not found")

    if annot.resolved_at is None:
        annot.resolved_at = datetime.now(timezone.utc)
    else:
        annot.resolved_at = None
    annot.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(annot)
    return _serialize_annotation(annot)


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
    """List all annotations across all share links for a document.
    Only the document owner can access this endpoint.
    Supports filtering by annotation_type and resolved status."""
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(doc.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    q = (
        select(
            ViewerAnnotation,
            ShareLink.label.label("link_label"),
            ShareLink.token.label("link_token"),
        )
        .join(ShareLink, ShareLink.id == ViewerAnnotation.link_id)
        .where(ShareLink.document_id == doc.id)
    )
    if annotation_type:
        q = q.where(ViewerAnnotation.annotation_type == annotation_type)
    if resolved is True:
        q = q.where(ViewerAnnotation.resolved_at.isnot(None))
    elif resolved is False:
        q = q.where(ViewerAnnotation.resolved_at.is_(None))

    rows = (await db.execute(q.order_by(ViewerAnnotation.created_at))).all()

    names = await _profile_display_names(db, [row[0] for row in rows])
    annotations = []
    for row in rows:
        a = row[0]
        d = _serialize_annotation(a, profile_display_name=names.get(str(a.viewer_profile_id)), full_identity=True)
        d["link_label"] = row.link_label or ""
        d["link_token"] = row.link_token
        annotations.append(d)

    return {"annotations": annotations, "total": len(annotations)}


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
    if str(doc.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    # Collect all annotations across all links for this document
    rows = (
        await db.execute(
            select(
                ViewerAnnotation.id,
                ViewerAnnotation.session_id,
                ViewerAnnotation.viewer_email,
                ViewerProfile.display_name.label("profile_display_name"),
                ViewerAnnotation.page_number,
                ViewerAnnotation.annotation_type,
                ViewerAnnotation.comment_text,
                ViewerAnnotation.created_at,
                ShareLink.label.label("link_label"),
            )
            .join(ShareLink, ShareLink.id == ViewerAnnotation.link_id)
            .outerjoin(ViewerProfile, ViewerProfile.id == ViewerAnnotation.viewer_profile_id)
            .where(ShareLink.document_id == doc.id)
            .order_by(ViewerAnnotation.created_at)
        )
    ).all()

    def _generate_csv():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "annotation_id", "link_label", "reviewer_name", "reviewer_email",
            "page_number", "annotation_type", "comment_text", "created_at",
        ])
        for r in rows:
            writer.writerow([
                r.id,
                r.link_label or "",
                _resolve_display_name(r.session_id, r.viewer_email, r.profile_display_name),
                r.viewer_email or "",
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
    link_row, session_id = await _resolve_link_and_verify_session(token, request, db, require_annotate=False)

    root = await db.get(ViewerAnnotation, annotation_id)
    if root is None or str(root.link_id) != str(link_row.id):
        raise HTTPException(status_code=404, detail="Annotation not found")
    if root.annotation_type not in FEEDBACK_TYPES:
        raise HTTPException(status_code=422, detail="Thread is only available on feedback annotations (comment, sticky_note)")

    replies = (await db.execute(
        select(ViewerAnnotation)
        .where(ViewerAnnotation.parent_id == str(root.id))
        .order_by(ViewerAnnotation.created_at)
    )).scalars().all()

    names = await _profile_display_names(db, [root, *replies])
    return {
        "root": _serialize_annotation(root, profile_display_name=names.get(str(root.viewer_profile_id))),
        "replies": [
            _serialize_annotation(r, profile_display_name=names.get(str(r.viewer_profile_id))) for r in replies
        ],
        "own_session_prefix": session_id[:6],
    }


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
    any viewer share-link session. The uploader is not a link viewer, so
    routing replies through the viewer session endpoint (as before) meant a
    stale/expired viewer session produced a spurious "Session not recognized"
    401 on every reply attempt.
    """
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(doc.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    target = await db.get(ViewerAnnotation, annotation_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Annotation not found")

    link_row = (await db.execute(select(ShareLink).where(ShareLink.id == target.link_id))).scalar_one_or_none()
    if link_row is None or str(link_row.document_id) != str(doc.id):
        raise HTTPException(status_code=404, detail="Annotation not found")

    if target.annotation_type not in FEEDBACK_TYPES:
        raise HTTPException(status_code=422, detail="Replies are only allowed on feedback (comment/sticky_note) threads")

    # Always attach the reply to the thread root, even if the uploader is
    # replying to what is itself already a reply — keeps threads flat at one
    # level, matching get_annotation_thread's depth-1 fetch.
    root_id = str(target.parent_id) if target.parent_id else str(target.id)

    uploader_email = (current_user.get("email") or "").strip().lower() or None
    reply = ViewerAnnotation(
        link_id=target.link_id,
        session_id=f"{_UPLOADER_SESSION_PREFIX}{current_user['user_id']}",
        viewer_email_masked=None,
        viewer_email=uploader_email,
        viewer_profile_id=None,
        page_number=target.page_number,
        annotation_type="comment",
        coords=target.coords,
        comment_text=body.comment_text,
        thickness=2,
        parent_id=root_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    logger.info("[feedback] uploader reply created doc=%s thread=%s", doc_id, root_id)
    return _serialize_annotation(reply, full_identity=True)


# ── Uploader: list feedback (comment + sticky_note) ───────────────────────────

@router.get("/api/documents/{doc_id}/feedback")
@limiter.limit("30/minute")
async def list_document_feedback(
    request: Request,
    doc_id: str,
    resolved: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List only FEEDBACK_TYPES (comment, sticky_note) with nested replies.
    Only the document owner can access this endpoint."""
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(doc.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    q = (
        select(ViewerAnnotation, ShareLink.label.label("link_label"))
        .join(ShareLink, ShareLink.id == ViewerAnnotation.link_id)
        .where(
            ShareLink.document_id == doc.id,
            ViewerAnnotation.annotation_type.in_(list(FEEDBACK_TYPES)),
        )
    )
    if resolved is True:
        q = q.where(ViewerAnnotation.resolved_at.isnot(None))
    elif resolved is False:
        q = q.where(ViewerAnnotation.resolved_at.is_(None))

    rows = (await db.execute(q.order_by(ViewerAnnotation.created_at))).all()

    # Build top-level items with pre-fetched reply counts
    tops = [row for row in rows if row[0].parent_id is None]
    reply_rows = [row for row in rows if row[0].parent_id is not None]

    names = await _profile_display_names(db, [row[0] for row in rows])

    # Count replies per parent
    reply_counts: dict = {}
    replies_by_parent: dict = {}
    for row in reply_rows:
        a = row[0]
        pid = str(a.parent_id)
        reply_counts[pid] = reply_counts.get(pid, 0) + 1
        replies_by_parent.setdefault(pid, []).append(
            _serialize_annotation(a, profile_display_name=names.get(str(a.viewer_profile_id)), full_identity=True)
        )

    feedback = []
    for row in tops:
        a = row[0]
        d = _serialize_annotation(a, profile_display_name=names.get(str(a.viewer_profile_id)), full_identity=True)
        d["link_label"] = row.link_label or ""
        d["reply_count"] = reply_counts.get(str(a.id), 0)
        d["replies"] = replies_by_parent.get(str(a.id), [])
        feedback.append(d)

    return {"feedback": feedback, "total": len(feedback)}


# ── Uploader: feedback CSV export ─────────────────────────────────────────────

@router.get("/api/documents/{doc_id}/feedback/export")
@limiter.limit("10/minute")
async def export_feedback(
    request: Request,
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Export feedback (comment/sticky_note) as CSV. Document owner only."""
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(doc.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    rows = (await db.execute(
        select(
            ViewerAnnotation.id,
            ViewerAnnotation.session_id,
            ViewerAnnotation.viewer_email,
            ViewerProfile.display_name.label("profile_display_name"),
            ViewerAnnotation.page_number,
            ViewerAnnotation.annotation_type,
            ViewerAnnotation.comment_text,
            ViewerAnnotation.resolved_at,
            ViewerAnnotation.parent_id,
            ViewerAnnotation.created_at,
            ShareLink.label.label("link_label"),
        )
        .join(ShareLink, ShareLink.id == ViewerAnnotation.link_id)
        .outerjoin(ViewerProfile, ViewerProfile.id == ViewerAnnotation.viewer_profile_id)
        .where(
            ShareLink.document_id == doc.id,
            ViewerAnnotation.annotation_type.in_(list(FEEDBACK_TYPES)),
        )
        .order_by(ViewerAnnotation.created_at)
    )).all()

    # Count replies per parent
    reply_counts: dict = {}
    for r in rows:
        if r.parent_id:
            pid = str(r.parent_id)
            reply_counts[pid] = reply_counts.get(pid, 0) + 1

    def _gen():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Reviewer Name", "Reviewer Email", "Document", "Page",
            "Comment", "Replies", "Status", "Created At",
        ])
        for r in rows:
            if r.parent_id:
                continue  # skip replies in top-level export — one row per thread
            writer.writerow([
                _resolve_display_name(r.session_id, r.viewer_email, r.profile_display_name),
                r.viewer_email or "",
                doc.filename,
                r.page_number,
                r.comment_text or "",
                reply_counts.get(str(r.id), 0),
                "Resolved" if r.resolved_at else "Open",
                r.created_at.isoformat() if r.created_at else "",
            ])
        yield buf.getvalue()

    filename = f"feedback_{doc_id[:8]}.csv"
    return StreamingResponse(_gen(), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


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
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(doc.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    valid_filter = set(ANNOTATION_TYPES)
    if annotation_type:
        if annotation_type not in valid_filter:
            raise HTTPException(status_code=422, detail=f"annotation_type must be one of {sorted(valid_filter)}")
        valid_filter = {annotation_type}

    q = (
        select(ViewerAnnotation, ShareLink.label.label("link_label"))
        .join(ShareLink, ShareLink.id == ViewerAnnotation.link_id)
        .where(
            ShareLink.document_id == doc.id,
            ViewerAnnotation.annotation_type.in_(list(valid_filter)),
        )
        .order_by(ViewerAnnotation.created_at)
    )

    rows = (await db.execute(q)).all()
    names = await _profile_display_names(db, [row[0] for row in rows])
    annotations = []
    for row in rows:
        a = row[0]
        d = _serialize_annotation(a, profile_display_name=names.get(str(a.viewer_profile_id)), full_identity=True)
        d["link_label"] = row.link_label or ""
        annotations.append(d)

    return {"annotations": annotations, "total": len(annotations)}


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
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(doc.user_id) != str(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    rows = (await db.execute(
        select(
            ViewerAnnotation.session_id,
            ViewerAnnotation.viewer_email,
            ViewerProfile.display_name.label("profile_display_name"),
            ViewerAnnotation.page_number,
            ViewerAnnotation.annotation_type,
            ViewerAnnotation.color,
            ViewerAnnotation.created_at,
            ShareLink.label.label("link_label"),
        )
        .join(ShareLink, ShareLink.id == ViewerAnnotation.link_id)
        .outerjoin(ViewerProfile, ViewerProfile.id == ViewerAnnotation.viewer_profile_id)
        .where(
            ShareLink.document_id == doc.id,
            ViewerAnnotation.annotation_type.in_(list(ANNOTATION_TYPES)),
        )
        .order_by(ViewerAnnotation.created_at)
    )).all()

    def _gen():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["reviewer_name", "reviewer_email", "page", "annotation_type", "color", "created_at"])
        for r in rows:
            writer.writerow([
                _resolve_display_name(r.session_id, r.viewer_email, r.profile_display_name),
                r.viewer_email or "",
                r.page_number,
                r.annotation_type,
                r.color or "",
                r.created_at.isoformat() if r.created_at else "",
            ])
        yield buf.getvalue()

    filename = f"annotations_{doc_id[:8]}.csv"
    return StreamingResponse(_gen(), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
