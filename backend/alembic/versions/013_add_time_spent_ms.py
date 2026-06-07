"""add time_spent_ms to access_events

Revision ID: 013
Revises: 012
Create Date: 2026-06-07

Adds time_spent_ms (INTEGER, nullable) to access_events for time-on-page analytics.
Backfills NULL for all existing rows (no default — historical data has no timing).
"""
from alembic import op
import sqlalchemy as sa


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "access_events",
        sa.Column("time_spent_ms", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column("access_events", "time_spent_ms")
