import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

API_SCOPES = frozenset({
    "documents:read",
    "documents:write",
    "links:read",
    "links:write",
    "analytics:read",
    "webhooks:read",
    "webhooks:write",
    # ENG-039: orgs/api_keys/billing previously had no scope taxonomy at all,
    # so those routers could only ever use bare authentication (any valid API
    # key, regardless of granted scopes, had full access) — see
    # docs/security/API_AUTHORIZATION_MATRIX.md for the full audit.
    "organizations:read",
    "organizations:write",
    "api_keys:read",
    "api_keys:write",
    "billing:read",
    "billing:write",
})

_KEY_PREFIX = "sd_"
_KEY_HEX_LEN = 48  # 24 random bytes → 48 hex chars


def generate_api_key() -> str:
    """Generate a new API key in sd_<48-hex> format."""
    import secrets
    return _KEY_PREFIX + secrets.token_hex(24)


def hash_api_key(key: str) -> str:
    """Return SHA-256 hex digest of the key."""
    import hashlib
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class APIKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_key_hash", "key_hash", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scopes_json: Mapped[str] = mapped_column("scopes", Text, nullable=False, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
