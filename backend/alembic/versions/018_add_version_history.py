"""add version and parent_document_id to documents

Revision ID: 018
Revises: 017
Create Date: 2026-06-07

Enables document version history. Existing documents get version=1 and
parent_document_id=NULL (no history chain — they are the root versions).
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "documents",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "documents",
        sa.Column("parent_document_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_documents_parent_id",
        "documents",
        "documents",
        ["parent_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_documents_parent_id", "documents", ["parent_document_id"])


def downgrade():
    op.drop_index("ix_documents_parent_id", "documents")
    op.drop_constraint("fk_documents_parent_id", "documents", type_="foreignkey")
    op.drop_column("documents", "parent_document_id")
    op.drop_column("documents", "version")
