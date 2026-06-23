import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ShareLink(Base):
    __tablename__ = "share_links"
    __table_args__ = (
        Index("ix_share_links_document_id", "document_id"),
        # Composite index added by migration 025; covers active-link queries
        # that filter on document_id AND revoked_at IS NULL.
        Index("ix_share_links_doc_revoked", "document_id", "revoked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    allowed_emails: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    allowed_domains: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    permissions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    ip_allowlist: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of IPs/CIDRs
    max_views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_concurrent_sessions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(  # type: ignore[name-defined]
        "Document", back_populates="share_links"
    )
    events: Mapped[List["AccessEvent"]] = relationship(  # type: ignore[name-defined]
        "AccessEvent", back_populates="link", cascade="all, delete-orphan"
    )
