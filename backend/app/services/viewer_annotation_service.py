"""Viewer-facing and owner-facing annotation CRUD operations."""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import ViewerAnnotation, ANNOTATION_TYPES
from app.models.document import Document
from app.models.link import ShareLink
from app.models.session import ViewerSession
from app.services.annotation_service import (
    _profile_display_names,
    _serialize_annotation,
)

logger = logging.getLogger(__name__)


async def fetch_page_annotations(
    db: AsyncSession,
    link_id: str,
    session_id: str,
    page_number: int,
) -> dict:
    if page_number < 1:
        raise HTTPException(status_code=422, detail="page_number must be ≥ 1")

    rows = (
        await db.execute(
            select(ViewerAnnotation)
            .where(
                ViewerAnnotation.link_id == link_id,
                ViewerAnnotation.page_number == page_number,
            )
            .order_by(ViewerAnnotation.created_at)
        )
    ).scalars().all()

    names = await _profile_display_names(db, rows)
    return {
        "page_number": page_number,
        "annotations": [
            _serialize_annotation(a, profile_display_name=names.get(str(a.viewer_profile_id)))
            for a in rows
        ],
        "own_session_prefix": session_id[:6],
    }


async def create_viewer_annotation(
    db: AsyncSession,
    link_row,
    session_id: str,
    body,
) -> dict:
    """body is an AnnotationCreate pydantic model."""
    if body.parent_id:
        parent_annot = await db.get(ViewerAnnotation, body.parent_id)
        if parent_annot is not None and parent_annot.annotation_type in ANNOTATION_TYPES:
            raise HTTPException(
                status_code=422,
                detail="Visual annotations (highlight/draw/rectangle/arrow) cannot have replies",
            )
        if parent_annot is not None and parent_annot.parent_id:
            body.parent_id = str(parent_annot.parent_id)

    doc = (
        await db.execute(select(Document).where(Document.id == link_row.document_id))
    ).scalar_one_or_none()
    if doc and doc.page_count and not (1 <= body.page_number <= doc.page_count):
        raise HTTPException(status_code=422, detail=f"page_number must be 1–{doc.page_count}")

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


async def update_viewer_annotation(
    db: AsyncSession,
    link_row,
    session_id: str,
    annotation_id: str,
    body,
) -> dict:
    """body is an AnnotationUpdate pydantic model."""
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


async def delete_viewer_annotation(
    db: AsyncSession,
    link_row,
    session_id: str,
    annotation_id: str,
) -> None:
    annot = await db.get(ViewerAnnotation, annotation_id)
    if annot is None or str(annot.link_id) != str(link_row.id):
        raise HTTPException(status_code=404, detail="Annotation not found")
    if annot.session_id != session_id:
        raise HTTPException(status_code=403, detail="Cannot delete another viewer's annotation")

    await db.delete(annot)
    await db.commit()


async def toggle_resolve_annotation(
    db: AsyncSession,
    link_row,
    annotation_id: str,
) -> dict:
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


async def fetch_document_annotations(
    db: AsyncSession,
    doc: Document,
    annotation_type: Optional[str],
    resolved: Optional[bool],
) -> dict:
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
        d = _serialize_annotation(
            a, profile_display_name=names.get(str(a.viewer_profile_id)), full_identity=True
        )
        d["link_label"] = row.link_label or ""
        d["link_token"] = row.link_token
        annotations.append(d)

    return {"annotations": annotations, "total": len(annotations)}


async def fetch_visual_annotations(
    db: AsyncSession,
    doc: Document,
    annotation_type: Optional[str],
) -> dict:
    from app.models.annotation import ANNOTATION_TYPES

    valid_filter = set(ANNOTATION_TYPES)
    if annotation_type:
        if annotation_type not in valid_filter:
            raise HTTPException(
                status_code=422, detail=f"annotation_type must be one of {sorted(valid_filter)}"
            )
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
        d = _serialize_annotation(
            a, profile_display_name=names.get(str(a.viewer_profile_id)), full_identity=True
        )
        d["link_label"] = row.link_label or ""
        annotations.append(d)

    return {"annotations": annotations, "total": len(annotations)}
