import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.database import Base


class ViewerProfile(Base):
    """Global, cross-document identity for a viewer, keyed by their verified email.

    Created the first time a viewer validates a share link that has an email
    gate. One profile can be linked to many ViewerSession / ViewerAnnotation
    rows across many documents and uploaders — this is what makes a future
    cross-document reviewer history possible. display_name is derived from
    the email local-part at creation time (e.g. "john.doe@x.com" -> "John Doe");
    nothing here is exposed to any endpoint yet.
    """

    __tablename__ = "viewer_profiles"

    # PGUUID(as_uuid=False): every FK referencing this column (ViewerSession,
    # ViewerAnnotation) carries the id as a plain string through app code —
    # matching that representation here keeps SQLite-backed tests consistent
    # with production Postgres, mirroring the existing ViewerAnnotation.parent_id pattern.
    id: Mapped[str] = mapped_column(PGUUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )
