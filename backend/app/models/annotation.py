import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, DateTime, ForeignKey, Text, Index, UniqueConstraint, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.database import Base


VALID_ANNOTATION_TYPES = frozenset({"highlight", "comment", "bookmark", "rectangle", "arrow", "sticky_note", "draw"})

FEEDBACK_TYPES = frozenset({"comment", "sticky_note"})
ANNOTATION_TYPES = frozenset({"highlight", "draw", "rectangle", "arrow"})


class ViewerAnnotation(Base):
    """Overlay annotation created by a viewer on a specific page of a shared document.

    Coordinates (coords JSON) are normalized 0–1 floats relative to page width/height:
      highlight / rectangle / bookmark: {x, y, w, h}
      arrow:                             {x1, y1, x2, y2}
      comment:                           {x, y}  (pin position)

    Security invariant: session_id ties each row to its owner.  The API layer
    enforces that only the creating session may PUT/DELETE its own annotations.
    The CASCADE on link_id ensures all viewer data is wiped on link revocation.
    """

    __tablename__ = "viewer_annotations"
    __table_args__ = (
        Index("ix_viewer_annotations_link_page", "link_id", "page_number"),
        Index("ix_viewer_annotations_session", "session_id"),
        Index("ix_viewer_annotations_profile", "viewer_profile_id"),
        # Added by migration 023; covers reply-thread lookup (WHERE parent_id = ?).
        Index("ix_viewer_annotations_parent", "parent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("share_links.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    viewer_email_masked: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Plaintext email + resolved global profile, copied from the session at
    # creation time. Never exposed outside document-owner-authenticated
    # endpoints — see _serialize_annotation in routers/annotations.py.
    viewer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    viewer_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=False),
        ForeignKey("viewer_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    annotation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    coords: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    comment_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thickness: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=2)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=False),
        ForeignKey("viewer_annotations.id", ondelete="CASCADE"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )


class ViewerBookmark(Base):
    """A viewer's bookmark on a specific page.

    Unique per (link_id, session_id, page_number) — toggling a bookmark at the
    same page simply deletes the existing row rather than creating a duplicate.
    """

    __tablename__ = "viewer_bookmarks"
    __table_args__ = (
        UniqueConstraint("link_id", "session_id", "page_number", name="uq_viewer_bookmark_per_page"),
        Index("ix_viewer_bookmarks_link_session", "link_id", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("share_links.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
