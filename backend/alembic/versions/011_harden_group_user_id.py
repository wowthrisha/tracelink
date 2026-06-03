"""Harden document_groups: user_id NOT NULL

Revision ID: 011
Revises: 010
Create Date: 2026-06-03

Changes:
  - document_groups.user_id: remove orphaned rows, then set NOT NULL
  - Matches the hardening applied to documents.user_id in migration 007
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove groups with no owner (orphaned — no query path reaches them)
    op.execute("DELETE FROM document_groups WHERE user_id IS NULL")

    op.alter_column(
        "document_groups",
        "user_id",
        existing_type=sa.UUID(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "document_groups",
        "user_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
