"""Add composite index on webhook_deliveries(webhook_id, created_at)

Revision ID: 027
Revises: 026
Create Date: 2026-07-21

get_deliveries() (routers/webhooks.py) filters on webhook_id and orders by
created_at DESC. The existing (webhook_id)-only index doesn't cover the sort,
so Postgres does an extra sort pass once a webhook accumulates many
deliveries. Found during the V6.0 engineering-governance scalability review.
"""
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_webhook_deliveries_webhook_created",
        "webhook_deliveries",
        ["webhook_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_webhook_created", table_name="webhook_deliveries")
