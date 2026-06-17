"""Annotation thread, feedback list, feedback reviewer, and uploader reply logic."""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import ViewerAnnotation, FEEDBACK_TYPES
from app.models.document import Document
from app.models.link import ShareLink
from app.services.annotation_service import (
    _UPLOADER_SESSION_PREFIX,
    _is_uploader_row,
    _resolve_display_name,
    _profile_display_names,
    _serialize_annotation,
)
from app.services.annotation_filter_service import (
    _parse_filter_date,
    _thread_matches_filters,
)

logger = logging.getLogger(__name__)


async def fetch_thread(
    db: AsyncSession,
    root: ViewerAnnotation,
    link_row,
    session_id: str,
) -> dict:
    if root.annotation_type not in FEEDBACK_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Thread is only available on feedback annotations (comment, sticky_note)",
        )
    replies = (
        await db.execute(
            select(ViewerAnnotation)
            .where(ViewerAnnotation.parent_id == str(root.id))
            .order_by(ViewerAnnotation.created_at)
        )
    ).scalars().all()

    names = await _profile_display_names(db, [root, *replies])
    return {
        "root": _serialize_annotation(root, profile_display_name=names.get(str(root.viewer_profile_id))),
        "replies": [
            _serialize_annotation(r, profile_display_name=names.get(str(r.viewer_profile_id)))
            for r in replies
        ],
        "own_session_prefix": session_id[:6],
    }


async def create_uploader_reply(
    db: AsyncSession,
    target: ViewerAnnotation,
    doc: Document,
    comment_text: str,
    current_user: dict,
) -> dict:
    link_row = (
        await db.execute(select(ShareLink).where(ShareLink.id == target.link_id))
    ).scalar_one_or_none()
    if link_row is None or str(link_row.document_id) != str(doc.id):
        raise HTTPException(status_code=404, detail="Annotation not found")

    if target.annotation_type not in FEEDBACK_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Replies are only allowed on feedback (comment/sticky_note) threads",
        )

    # Keep threads flat at depth-1 regardless of which message the uploader replied to
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
        comment_text=comment_text,
        thickness=2,
        parent_id=root_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    logger.info("[feedback] uploader reply created doc=%s thread=%s", doc.id, root_id)
    return _serialize_annotation(reply, full_identity=True)


async def fetch_feedback_list(
    db: AsyncSession,
    doc: Document,
    resolved: Optional[bool],
    search: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    page_number: Optional[int],
    author_role: Optional[str],
    reviewer: Optional[str],
) -> dict:
    from app.models.annotation import FEEDBACK_TYPES

    if author_role is not None and author_role not in ("viewer", "uploader"):
        raise HTTPException(status_code=422, detail="author_role must be 'viewer' or 'uploader'")

    df = _parse_filter_date(date_from)
    dt_ = _parse_filter_date(date_to, end_of_day=True)

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

    tops = [row for row in rows if row[0].parent_id is None]
    reply_rows = [row for row in rows if row[0].parent_id is not None]
    names = await _profile_display_names(db, [row[0] for row in rows])

    reply_counts: dict = {}
    replies_by_parent: dict = {}
    replies_raw_by_parent: dict = {}
    for row in reply_rows:
        a = row[0]
        pid = str(a.parent_id)
        reply_counts[pid] = reply_counts.get(pid, 0) + 1
        replies_by_parent.setdefault(pid, []).append(
            _serialize_annotation(a, profile_display_name=names.get(str(a.viewer_profile_id)), full_identity=True)
        )
        replies_raw_by_parent.setdefault(pid, []).append(a)

    search_l = search.strip().lower() if search else None

    def _text_matches(a: ViewerAnnotation, name: str) -> bool:
        if not search_l:
            return True
        haystack = " ".join(filter(None, [a.comment_text, name, a.viewer_email])).lower()
        return search_l in haystack

    feedback = []
    for row in tops:
        a = row[0]
        thread_msgs = [a, *replies_raw_by_parent.get(str(a.id), [])]
        if not _thread_matches_filters(
            thread_msgs, date_from=df, date_to=dt_,
            page_number=page_number, author_role=author_role, reviewer_email=reviewer,
        ):
            continue
        if search_l:
            names_for_thread = [
                names.get(str(m.viewer_profile_id)) or _resolve_display_name(m.session_id, m.viewer_email)
                for m in thread_msgs
            ]
            if not any(_text_matches(m, n) for m, n in zip(thread_msgs, names_for_thread)):
                continue

        d = _serialize_annotation(
            a, profile_display_name=names.get(str(a.viewer_profile_id)), full_identity=True
        )
        d["link_label"] = row.link_label or ""
        d["reply_count"] = reply_counts.get(str(a.id), 0)
        d["replies"] = replies_by_parent.get(str(a.id), [])
        feedback.append(d)

    return {"feedback": feedback, "total": len(feedback)}


async def fetch_feedback_reviewers(db: AsyncSession, doc: Document) -> dict:
    from app.models.annotation import FEEDBACK_TYPES

    rows = (
        await db.execute(
            select(ViewerAnnotation, ShareLink.label.label("link_label"))
            .join(ShareLink, ShareLink.id == ViewerAnnotation.link_id)
            .where(
                ShareLink.document_id == doc.id,
                ViewerAnnotation.annotation_type.in_(list(FEEDBACK_TYPES)),
            )
        )
    ).all()
    annots = [row[0] for row in rows if not _is_uploader_row(row[0].session_id)]
    names = await _profile_display_names(db, annots)

    seen: dict = {}
    for a in annots:
        if not a.viewer_email:
            continue
        key = a.viewer_email.lower()
        if key not in seen:
            seen[key] = names.get(str(a.viewer_profile_id)) or _resolve_display_name(a.session_id, a.viewer_email)

    reviewers = [{"email": email, "name": name} for email, name in seen.items()]
    reviewers.sort(key=lambda r: r["name"].lower())
    return {"reviewers": reviewers}
