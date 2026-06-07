import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

AUDIT_EVENT_TYPES = frozenset({
    "org.created",
    "org.updated",
    "org.deleted",
    "member.added",
    "member.role_changed",
    "member.removed",
    "api_key.created",
    "api_key.revoked",
    "api_key.deleted",
    "document.deleted",
    "link.revoked",
})


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"
    __table_args__ = (
        Index("ix_admin_audit_log_actor", "actor_user_id"),
        Index("ix_admin_audit_log_org_id", "org_id"),
        Index("ix_admin_audit_log_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
