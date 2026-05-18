"""Add file_type column to documents for text document support (Phase 5)

Revision ID: 009
Revises: 008
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "documents",
        sa.Column(
            "file_type",
            sa.String(10),
            nullable=False,
            server_default="pdf",
        ),
    )
    op.create_index("ix_documents_file_type", "documents", ["file_type"])


def downgrade():
    op.drop_index("ix_documents_file_type", "documents")
    op.drop_column("documents", "file_type")
