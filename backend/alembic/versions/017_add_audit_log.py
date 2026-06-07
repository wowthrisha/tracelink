"""add admin_audit_log table

Revision ID: 017
Revises: 016
Create Date: 2026-06-07

Immutable audit trail for admin-plane events (SOC2 CC6.1).
"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_log_actor", "admin_audit_log", ["actor_user_id"])
    op.create_index("ix_admin_audit_log_org_id", "admin_audit_log", ["org_id"])
    op.create_index("ix_admin_audit_log_created_at", "admin_audit_log", ["created_at"])


def downgrade():
    op.drop_index("ix_admin_audit_log_created_at", "admin_audit_log")
    op.drop_index("ix_admin_audit_log_org_id", "admin_audit_log")
    op.drop_index("ix_admin_audit_log_actor", "admin_audit_log")
    op.drop_table("admin_audit_log")
