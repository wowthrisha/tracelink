"""Add performance indexes for session lookup

Revision ID: 020
Revises: 019
Create Date: 2026-06-07

Adds:
  - Composite index on viewer_sessions(link_id, session_id) — eliminates
    full table scans on the hot is_active_session() path under load.

Note: ix_organizations_slug was already created by migration 016.
"""
from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade():
    # Composite index for session validation hot-path:
    # is_active_session() queries WHERE link_id = ? AND session_id = ?
    op.create_index(
        "ix_viewer_sessions_link_session",
        "viewer_sessions",
        ["link_id", "session_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_viewer_sessions_link_session", table_name="viewer_sessions")
