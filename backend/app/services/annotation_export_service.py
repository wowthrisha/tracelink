"""CSV export generators for annotations, feedback, reviewer activity, and visual annotations."""
import csv
import io
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import ViewerAnnotation, FEEDBACK_TYPES, ANNOTATION_TYPES
from app.models.document import Document
from app.models.link import ShareLink
from app.models.viewer_profile import ViewerProfile
from app.services.annotation_service import (
    _is_uploader_row,
    _resolve_display_name,
    _profile_display_names,
)
from app.services.annotation_filter_service import (
    _parse_filter_date,
    _thread_matches_filters,
    _as_aware_utc,
)


async def build_annotations_export(db: AsyncSession, doc: Document):
    """Return (generator, filename) for all annotations CSV."""
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

    def _gen():
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

    filename = f"annotations_{str(doc.id)[:8]}.csv"
    return _gen(), filename


async def build_feedback_export(
    db: AsyncSession,
    doc: Document,
    resolved: Optional[bool],
    search: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    page_number: Optional[int],
    author_role: Optional[str],
    reviewer: Optional[str],
):
    """Return (generator, filename) for feedback conversations CSV."""
    from fastapi import HTTPException
    if author_role is not None and author_role not in ("viewer", "uploader"):
        raise HTTPException(status_code=422, detail="author_role must be 'viewer' or 'uploader'")

    df = _parse_filter_date(date_from)
    dt_ = _parse_filter_date(date_to, end_of_day=True)

    q = (
        select(ViewerAnnotation)
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

    rows = (await db.execute(q.order_by(ViewerAnnotation.created_at))).scalars().all()
    names = await _profile_display_names(db, rows)

    tops = [a for a in rows if a.parent_id is None]
    replies_by_parent: dict = {}
    for a in rows:
        if a.parent_id:
            replies_by_parent.setdefault(str(a.parent_id), []).append(a)

    search_l = search.strip().lower() if search else None

    def _text_matches(a: ViewerAnnotation, name: str) -> bool:
        if not search_l:
            return True
        haystack = " ".join(filter(None, [a.comment_text, name, a.viewer_email])).lower()
        return search_l in haystack

    def _fmt_date(dt: Optional[datetime]) -> str:
        return dt.strftime("%d %b %Y") if dt else ""

    def _gen():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Document", "Page", "Reviewer", "Reviewer Email", "Conversation",
            "Status", "First Comment", "Last Activity",
        ])
        for root in tops:
            thread_msgs = [root, *replies_by_parent.get(str(root.id), [])]
            if not _thread_matches_filters(
                thread_msgs, date_from=df, date_to=dt_,
                page_number=page_number, author_role=author_role, reviewer_email=reviewer,
            ):
                continue
            thread_names = {
                str(m.id): names.get(str(m.viewer_profile_id)) or _resolve_display_name(m.session_id, m.viewer_email)
                for m in thread_msgs
            }
            if search_l and not any(_text_matches(m, thread_names[str(m.id)]) for m in thread_msgs):
                continue
            status = "Resolved" if root.resolved_at else "Open"
            conversation = "\n\n".join(
                f"[{'Uploader' if _is_uploader_row(m.session_id) else 'Viewer'}]\n{m.comment_text or ''}"
                for m in thread_msgs
            )
            first_comment = root.created_at
            last_activity = max(
                (m.created_at for m in thread_msgs if m.created_at), default=root.created_at
            )
            writer.writerow([
                doc.filename,
                root.page_number,
                thread_names[str(root.id)],
                root.viewer_email or "",
                conversation,
                status,
                _fmt_date(first_comment),
                _fmt_date(last_activity),
            ])
        yield buf.getvalue()

    safe_name = re.sub(r'[^A-Za-z0-9._-]+', '_', doc.filename.rsplit('.', 1)[0])[:60] or "document"
    filename = f"feedback_conversations_{safe_name}.csv"
    return _gen(), filename


async def build_reviewer_activity_export(db: AsyncSession, doc: Document):
    """Return (generator, filename) for reviewer activity CSV."""
    rows = (
        await db.execute(
            select(ViewerAnnotation)
            .join(ShareLink, ShareLink.id == ViewerAnnotation.link_id)
            .where(
                ShareLink.document_id == doc.id,
                ViewerAnnotation.annotation_type.in_(list(FEEDBACK_TYPES)),
            )
            .order_by(ViewerAnnotation.created_at)
        )
    ).scalars().all()
    names = await _profile_display_names(db, rows)

    reviewers: dict = {}
    for a in rows:
        if _is_uploader_row(a.session_id):
            continue
        key = a.viewer_email or f"anon:{a.session_id}"
        name = names.get(str(a.viewer_profile_id)) or _resolve_display_name(a.session_id, a.viewer_email)
        entry = reviewers.setdefault(key, {
            "name": name, "email": a.viewer_email or "",
            "comment_count": 0, "reply_count": 0, "last_activity": None,
        })
        if a.parent_id is None:
            entry["comment_count"] += 1
        else:
            entry["reply_count"] += 1
        created_at = _as_aware_utc(a.created_at)
        if created_at and (entry["last_activity"] is None or created_at > entry["last_activity"]):
            entry["last_activity"] = created_at

    def _gen():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Reviewer Name", "Reviewer Email", "Document",
            "Comment Count", "Reply Count", "Last Activity",
        ])
        for entry in sorted(
            reviewers.values(),
            key=lambda e: e["last_activity"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        ):
            writer.writerow([
                entry["name"],
                entry["email"],
                doc.filename,
                entry["comment_count"],
                entry["reply_count"],
                entry["last_activity"].isoformat() if entry["last_activity"] else "",
            ])
        yield buf.getvalue()

    filename = f"reviewer_activity_{str(doc.id)[:8]}.csv"
    return _gen(), filename


async def build_visual_annotations_export(db: AsyncSession, doc: Document):
    """Return (generator, filename) for visual annotations CSV."""
    rows = (
        await db.execute(
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
        )
    ).all()

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

    filename = f"annotations_{str(doc.id)[:8]}.csv"
    return _gen(), filename
