import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import BigInteger, String, Integer, Enum, DateTime, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

RETENTION_POLICIES = ("30_days", "60_days", "90_days", "never")
LIFECYCLE_STATES = ("active", "archived", "expired", "deleted")
RETENTION_DAYS = {"30_days": 30, "60_days": 60, "90_days": 90, "never": None}


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_user_id", "user_id"),
        Index("ix_documents_lifecycle_state", "lifecycle_state"),
        Index("ix_documents_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("uploaded", "processing", "ready", "error", name="document_status"),
        default="uploaded",
        nullable=False,
    )
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("document_groups.id", ondelete="SET NULL"), nullable=True
    )
    file_type: Mapped[str] = mapped_column(String(10), default="pdf", nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    # Retention & lifecycle
    retention_policy: Mapped[str] = mapped_column(
        Enum(*RETENTION_POLICIES, name="retention_policy_enum"),
        nullable=False,
        default="never",
    )
    lifecycle_state: Mapped[str] = mapped_column(
        Enum(*LIFECYCLE_STATES, name="lifecycle_state_enum"),
        nullable=False,
        default="active",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Accurate total storage for this document (original + pages + thumbs + sidecars).
    # Set by the processing pipeline; NULL for documents processed before this field existed.
    # Dashboard falls back to file_size_bytes when NULL.
    storage_bytes_computed: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    pages: Mapped[List["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )
    share_links: Mapped[List["ShareLink"]] = relationship(  # type: ignore[name-defined]
        "ShareLink", back_populates="document", cascade="all, delete-orphan"
    )
    group: Mapped[Optional["DocumentGroup"]] = relationship(  # type: ignore[name-defined]
        "DocumentGroup", back_populates="documents"
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_doc_page"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    width_px: Mapped[int] = mapped_column(Integer, nullable=False)
    height_px: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship("Document", back_populates="pages")
