"""Add ip_allowlist, max_concurrent_sessions to share_links; add viewer_sessions table; extend event_type enum

Revision ID: 004
Revises: 003
Create Date: 2026-05-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── share_links: new policy columns ──────────────────────────────────────
    op.add_column(
        "share_links",
        sa.Column("ip_allowlist", sa.Text(), nullable=True),
    )
    op.add_column(
        "share_links",
        sa.Column("max_concurrent_sessions", sa.Integer(), nullable=True),
    )

    # ── viewer_sessions table ─────────────────────────────────────────────────
    op.create_table(
        "viewer_sessions",
        sa.Column("session_id", sa.String(32), primary_key=True),
        sa.Column(
            "link_id",
            sa.UUID(),
            sa.ForeignKey("share_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_viewer_sessions_link_id", "viewer_sessions", ["link_id"])
    op.create_index("ix_viewer_sessions_last_seen", "viewer_sessions", ["last_seen_at"])

    # ── Extend event_type enum with new values ────────────────────────────────
    # PostgreSQL requires enum values to be added outside a transaction.
    # Alembic wraps upgrade() in a transaction by default; use op.execute with
    # the COMMIT workaround or configure transaction_per_migration=False.
    # The simplest portable approach: use op.execute in non-transactional mode.
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        # These must be run outside a transaction block in older PG versions.
        # In PG 12+ they work inside a transaction.
        conn.execute(
            sa.text("ALTER TYPE event_type_enum ADD VALUE IF NOT EXISTS 'ip_blocked'")
        )
        conn.execute(
            sa.text(
                "ALTER TYPE event_type_enum ADD VALUE IF NOT EXISTS 'session_limit_reached'"
            )
        )
    # SQLite: enum is stored as VARCHAR, no DDL change needed.


def downgrade() -> None:
    op.drop_index("ix_viewer_sessions_last_seen", table_name="viewer_sessions")
    op.drop_index("ix_viewer_sessions_link_id", table_name="viewer_sessions")
    op.drop_table("viewer_sessions")
    op.drop_column("share_links", "max_concurrent_sessions")
    op.drop_column("share_links", "ip_allowlist")
    # Note: PostgreSQL does not support removing enum values.
    # Downgrade cannot reverse the enum extension without dropping and recreating it.
