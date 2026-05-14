"""Harden schema: user_id NOT NULL, performance indexes

Revision ID: 007
Revises: 006
Create Date: 2026-05-13 00:00:00.000000

Changes:
  - documents.user_id: remove any orphaned rows, then set NOT NULL
  - Add index: documents(user_id)
  - Add index: share_links(document_id)
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Remove documents with NULL user_id (orphaned — inaccessible in the app
    #    since every query filters on user_id). Do this before adding the constraint.
    op.execute("DELETE FROM documents WHERE user_id IS NULL")

    # 2. Make user_id NOT NULL
    op.alter_column(
        "documents",
        "user_id",
        existing_type=sa.UUID(),
        nullable=False,
    )

    # 3. Indexes for hot query paths
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_share_links_document_id", "share_links", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_share_links_document_id", table_name="share_links")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.alter_column(
        "documents",
        "user_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
