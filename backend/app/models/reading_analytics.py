"""Reading Intelligence Engine — database models.

Three tables:
  reading_sessions      — one row per viewer-session (aggregates)
  page_reading_events   — one row per page per session (per-page detail)
  document_complexity   — cached per-document complexity metrics
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, Float, ForeignKey,
    Index, Integer, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

PAGE_COMPLETION_STATES = ("unread", "started", "reading", "completed", "revisited", "skipped")


class ReadingSession(Base):
    """Aggregated reading analytics for one viewer session of one document.

    Upserted by the /api/reading/batch endpoint on every event batch.
    Metrics are recomputed from page_reading_events and stored here for
    cheap dashboard queries without re-aggregating raw page data.
    """
    __tablename__ = "reading_sessions"
    __table_args__ = (
        Index("ix_rs_link_id", "link_id"),
        Index("ix_rs_document_id", "document_id"),
        Index("ix_rs_session_id", "session_id"),
        Index("ix_rs_document_started", "document_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("share_links.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    # Timing (milliseconds)
    total_active_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_elapsed_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_idle_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_pause_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Page coverage
    pages_visited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_revisited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Reading speed model outputs
    avg_ms_per_page: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reading_speed_wpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fastest_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    slowest_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    drop_off_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confusion_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Engagement scores (0–100, computed from formula)
    engagement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    absorption_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    focus_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reading_consistency: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attention_stability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    understanding_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Interaction counts
    total_annotations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_copy_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_print_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_idle_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reading_interruptions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_pause_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tab_switch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Prediction tracking (for accuracy measurement)
    initial_estimate_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    prediction_accuracy_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    viewer_email_masked: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    page_events: Mapped[list["PageReadingEvent"]] = relationship(
        "PageReadingEvent", back_populates="reading_session",
        cascade="all, delete-orphan",
        order_by="PageReadingEvent.page_number",
    )


class PageReadingEvent(Base):
    """Per-page analytics within a single reading session.

    One row per (session_id, page_number) — upserted on each batch.
    Revisit data is accumulated (revisit_count += 1, active_time_ms += delta).
    """
    __tablename__ = "page_reading_events"
    __table_args__ = (
        Index("ix_pre_session_id", "session_id"),
        Index("ix_pre_document_page", "document_id", "page_number"),
        Index("ix_pre_reading_session", "reading_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reading_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reading_sessions.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(32), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Timestamps (ISO strings from frontend, stored as first/last visit)
    enter_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Time tracking
    active_time_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    pause_duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Engagement signals
    revisit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scroll_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zoom_level: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    fullscreen_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Interaction counts
    annotations_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    copy_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    print_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tab_switch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visibility_changes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idle_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    completion_status: Mapped[str] = mapped_column(
        Enum(*PAGE_COMPLETION_STATES, name="page_completion_status_enum"),
        nullable=False, default="unread"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    reading_session: Mapped["ReadingSession"] = relationship(
        "ReadingSession", back_populates="page_events"
    )


class DocumentComplexity(Base):
    """Cached per-document complexity metrics used by the reading speed prediction model.

    Computed once and invalidated when the document is reprocessed.
    word_count is estimated from page_count × avg_words_per_page for PDFs,
    or extracted directly for text documents.
    """
    __tablename__ = "document_complexity"

    document_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    word_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    estimated_words_per_page: Mapped[float] = mapped_column(Float, nullable=False, default=250.0)

    # Density signals (0.0 – 1.0 ratio relative to page count)
    image_density: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    table_density: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_page_length_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Complexity factor: 1.0 = average, >1.0 = harder, <1.0 = easier
    complexity_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Baseline reading speed for this document type (wpm)
    baseline_wpm: Mapped[float] = mapped_column(Float, nullable=False, default=200.0)

    # Empirical stats from collected sessions (updated as data accumulates)
    median_completion_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    p25_completion_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    p75_completion_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    session_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )
