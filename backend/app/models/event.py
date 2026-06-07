import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Enum, DateTime, ForeignKey, Text, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

EVENT_TYPES = (
    "opened",
    "page_viewed",
    "print_attempt",
    "copy_attempt",
    "right_click_attempt",
    "download_attempt",
    "completed",
    "printed",              # successful print (can_print=True)
    "access_denied",
    "password_wrong",
    "expired",
    "revoked",
    "max_views_reached",
    "ip_blocked",
    "session_limit_reached",
)

# Event types that the viewer frontend is permitted to log via POST /api/analytics/events.
# All other event types are logged exclusively server-side.
VIEWER_LOGGABLE_EVENTS = frozenset({
    "print_attempt",
    "copy_attempt",
    "right_click_attempt",
    "download_attempt",
    "completed",
    "printed",              # successful print (can_print=True)
})


class AccessEvent(Base):
    __tablename__ = "access_events"
    __table_args__ = (
        Index("ix_access_events_created_at", "created_at"),
        Index("ix_access_events_link_id", "link_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("share_links.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        Enum(*EVENT_TYPES, name="event_type_enum"), nullable=False
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_spent_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    viewer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(
        "metadata", Text, nullable=True
    )  # JSON stored as text
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    link: Mapped["ShareLink"] = relationship(  # type: ignore[name-defined]
        "ShareLink", back_populates="events"
    )
