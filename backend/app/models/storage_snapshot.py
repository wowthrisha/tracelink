import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class StorageSnapshot(Base):
    """Daily point-in-time storage totals per user (and optionally per org).

    Written once per day by the cleanup worker.  Used to power the storage
    forecast chart: current + 30-day + 90-day projections are derived from
    the rolling slope of recent snapshots.
    """

    __tablename__ = "storage_snapshots"
    __table_args__ = (
        Index("ix_storage_snapshots_user_at", "user_id", "snapshot_at"),
        Index("ix_storage_snapshots_org_at", "org_id", "snapshot_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
