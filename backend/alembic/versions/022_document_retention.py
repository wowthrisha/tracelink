"""Add document retention lifecycle and storage snapshots

Revision ID: 022
Revises: 021
Create Date: 2026-06-15

Changes:
  documents:
    - retention_policy  ENUM(30_days|60_days|90_days|never)  default 'never'
    - lifecycle_state   ENUM(active|archived|expired|deleted) default 'active'
    - expires_at        TIMESTAMPTZ nullable — computed from created_at + policy
    - last_viewed_at    TIMESTAMPTZ nullable — updated by cleanup worker from events
    - last_accessed_at  TIMESTAMPTZ nullable — updated by cleanup worker from events
    - storage_bytes_computed BIGINT nullable — set by processing pipeline

  storage_snapshots (new):
    Daily point-in-time storage totals per user/org; drives the forecast chart.
    id, user_id, org_id, total_bytes, document_count, snapshot_at

Security:
  - Cascade deletes from documents still handle all child rows (pages, links,
    events, sessions, annotations).  Storage key deletion is handled by the
    cleanup worker via the retention service, NOT by a DB trigger.

Indexes:
  - (lifecycle_state)             — cleanup worker query: WHERE state IN (...)
  - (expires_at)                  — cleanup worker query: WHERE expires_at < NOW()
  - (user_id, snapshot_at)        — forecast query per user
  - (org_id, snapshot_at)         — forecast query per org
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None

_uuid = PGUUID(as_uuid=False)


def upgrade():
    bind = op.get_bind()

    # Create enum types (PostgreSQL); ignored on SQLite (VARCHAR fallback)
    retention_enum = sa.Enum(
        "30_days", "60_days", "90_days", "never",
        name="retention_policy_enum",
    )
    lifecycle_enum = sa.Enum(
        "active", "archived", "expired", "deleted",
        name="lifecycle_state_enum",
    )
    retention_enum.create(bind, checkfirst=True)
    lifecycle_enum.create(bind, checkfirst=True)

    op.add_column(
        "documents",
        sa.Column(
            "retention_policy",
            retention_enum,
            nullable=False,
            server_default="never",
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "lifecycle_state",
            lifecycle_enum,
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "documents",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("storage_bytes_computed", sa.BigInteger, nullable=True),
    )

    op.create_index("ix_documents_lifecycle_state", "documents", ["lifecycle_state"])
    op.create_index("ix_documents_expires_at", "documents", ["expires_at"])

    op.create_table(
        "storage_snapshots",
        sa.Column("id", _uuid, primary_key=True),
        sa.Column("user_id", _uuid, nullable=False),
        sa.Column("org_id", _uuid, nullable=True),
        sa.Column("total_bytes", sa.BigInteger, nullable=False),
        sa.Column("document_count", sa.Integer, nullable=False),
        sa.Column(
            "snapshot_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_storage_snapshots_user_at",
        "storage_snapshots",
        ["user_id", "snapshot_at"],
    )
    op.create_index(
        "ix_storage_snapshots_org_at",
        "storage_snapshots",
        ["org_id", "snapshot_at"],
    )


def downgrade():
    op.drop_index("ix_storage_snapshots_org_at", table_name="storage_snapshots")
    op.drop_index("ix_storage_snapshots_user_at", table_name="storage_snapshots")
    op.drop_table("storage_snapshots")

    op.drop_index("ix_documents_expires_at", table_name="documents")
    op.drop_index("ix_documents_lifecycle_state", table_name="documents")

    op.drop_column("documents", "storage_bytes_computed")
    op.drop_column("documents", "last_accessed_at")
    op.drop_column("documents", "last_viewed_at")
    op.drop_column("documents", "expires_at")
    op.drop_column("documents", "lifecycle_state")
    op.drop_column("documents", "retention_policy")

    bind = op.get_bind()
    sa.Enum(name="lifecycle_state_enum").drop(bind, checkfirst=True)
    sa.Enum(name="retention_policy_enum").drop(bind, checkfirst=True)
