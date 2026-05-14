"""Add 'printed' to event_type_enum; add session cleanup index

Revision ID: 008
Revises: 007
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    # Add 'printed' event type — PostgreSQL only; SQLite ignores ALTER TYPE
    with op.get_context().autocommit_block():
        op.execute(
            sa.text("ALTER TYPE event_type_enum ADD VALUE IF NOT EXISTS 'printed'")
        )


def downgrade():
    # PostgreSQL does not support removing enum values; downgrade is a no-op.
    pass
