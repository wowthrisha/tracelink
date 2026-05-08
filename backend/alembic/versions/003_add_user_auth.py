"""add user_id to documents and created_by to share_links

Revision ID: 003
Revises: 002
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id (nullable) to documents
    op.add_column(
        "documents",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_index("idx_documents_user_id", "documents", ["user_id"])

    # Add created_by (nullable) to share_links
    op.add_column(
        "share_links",
        sa.Column("created_by", sa.UUID(), nullable=True),
    )


def downgrade() -> None:
    op.drop_index("idx_documents_user_id", table_name="documents")
    op.drop_column("documents", "user_id")
    op.drop_column("share_links", "created_by")
