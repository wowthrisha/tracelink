"""add document groups

Revision ID: 002
Revises: 001
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # document_groups table
    op.create_table(
        "document_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Add group_id FK to documents
    op.add_column(
        "documents",
        sa.Column("group_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_documents_group_id",
        "documents",
        "document_groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add permissions column to share_links if not already present
    op.execute("ALTER TABLE share_links ADD COLUMN IF NOT EXISTS permissions TEXT")


def downgrade() -> None:
    op.drop_constraint("fk_documents_group_id", "documents", type_="foreignkey")
    op.drop_column("documents", "group_id")
    op.drop_table("document_groups")
