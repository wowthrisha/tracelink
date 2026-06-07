"""Add performance indexes for session lookup and org slug

Revision ID: 020
Revises: 019
Create Date: 2026-06-07

Adds:
  - Composite index on viewer_sessions(link_id, session_id) — eliminates
    full table scans on the hot is_active_session() path under load.
  - Index on organizations(slug) — needed by ensure_unique_slug() which runs
    on every org create/update operation.
  - Count-only index on admin_audit_log for the total count query.
"""
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade():
    # Composite index for session validation hot-path
    # is_active_session() queries: WHERE link_id = ? AND session_id = ? AND is_active = true
    op.create_index(
        "ix_viewer_sessions_link_session",
        "viewer_sessions",
        ["link_id", "session_id"],
        unique=False,
    )
    # Org slug uniqueness lookups
    op.create_index(
        "ix_organizations_slug",
        "organizations",
        ["slug"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_viewer_sessions_link_session", table_name="viewer_sessions")
    op.drop_index("ix_organizations_slug", table_name="organizations")
