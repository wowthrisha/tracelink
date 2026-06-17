import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.database import Base


class ViewerSession(Base):
    """Tracks active viewer sessions for concurrent-session enforcement."""

    __tablename__ = "viewer_sessions"
    __table_args__ = (
        Index("ix_viewer_sessions_link_id", "link_id"),
        Index("ix_viewer_sessions_last_seen", "last_seen_at"),
        Index("ix_viewer_sessions_profile", "viewer_profile_id"),
        # Composite index added by migration 020; covers the per-request
        # session-validation hot path (WHERE link_id = ? AND session_id = ?).
        Index("ix_viewer_sessions_link_session", "link_id", "session_id"),
    )

    session_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("share_links.id", ondelete="CASCADE"), nullable=False
    )
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    viewer_email_masked: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Plaintext email, captured only when the link's email gate validated it.
    # Never exposed outside the document-owner-authenticated feedback/annotation
    # dashboards — viewer-facing responses must keep using viewer_email_masked.
    viewer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    viewer_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=False),
        ForeignKey("viewer_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
