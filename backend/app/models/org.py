import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ORG_ROLES = ("viewer", "editor", "admin", "owner")
_ROLE_RANK = {r: i for i, r in enumerate(ORG_ROLES)}


def role_gte(role: str, minimum: str) -> bool:
    """Return True if role >= minimum in the hierarchy."""
    return _ROLE_RANK.get(role, -1) >= _ROLE_RANK.get(minimum, 999)


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        Index("ix_organizations_slug", "slug", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    saml_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    custom_domain: Mapped[Optional[str]] = mapped_column(String(253), nullable=True, unique=True)
    custom_domain_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    custom_domain_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    memberships: Mapped[list["OrgMembership"]] = relationship(
        "OrgMembership", back_populates="org", cascade="all, delete-orphan"
    )


class OrgMembership(Base):
    __tablename__ = "org_memberships"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_memberships_org_user"),
        Index("ix_org_memberships_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="viewer")
    invited_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    org: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
