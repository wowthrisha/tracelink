"""Analytics performance: composite index on access_events(link_id, created_at)

Revision ID: 012
Revises: 011
Create Date: 2026-06-04

Rationale:
  The most common analytics queries filter by link_id (or link_id IN (...))
  and either order by created_at DESC or filter by created_at >= cutoff.

  With separate single-column indexes on link_id and created_at, PostgreSQL
  must choose one index and post-filter on the other column.  At ~2M rows
  (reachable in a month at 5,000-user scale), analytics queries can take
  5–30 seconds without this index.

  A composite index on (link_id, created_at DESC) covers:
    - GET /api/analytics/events  → WHERE link_id IN (...) ORDER BY created_at DESC
    - blocked24h queries          → WHERE link_id IN (...) AND created_at >= ?
    - All GROUP BY link_id queries → WHERE link_id IN (...) [any event filter]

  The existing single-column ix_access_events_link_id is kept because PostgreSQL
  uses single-column indexes for range scans not satisfied by the composite.

  Also adds ix_documents_status_updated for the orphan-requeue periodic task:
    SELECT id FROM documents WHERE status='uploaded' AND updated_at < ?
  This prevents a full table scan every 5 minutes.
"""
from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Primary analytics index: covers link_id filter + created_at ordering/range.
    # DESC on created_at matches the ORDER BY created_at DESC used in get_events().
    op.create_index(
        "ix_access_events_link_id_created",
        "access_events",
        ["link_id", sa.text("created_at DESC")],
    )

    # Secondary index: orphan-requeue query scans documents by status + updated_at.
    # Runs every 5 minutes via Celery Beat; without an index it is a full table scan.
    op.create_index(
        "ix_documents_status_updated",
        "documents",
        ["status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_status_updated", table_name="documents")
    op.drop_index("ix_access_events_link_id_created", table_name="access_events")
