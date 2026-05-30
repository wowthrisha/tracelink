import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ViewerSession(Base):
    """Tracks active viewer sessions for concurrent-session enforcement."""

    __tablename__ = "viewer_sessions"
    __table_args__ = (
        Index("ix_viewer_sessions_link_id", "link_id"),
        Index("ix_viewer_sessions_last_seen", "last_seen_at"),
    )

    session_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("share_links.id", ondelete="CASCADE"), nullable=False
    )
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    viewer_email_masked: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
