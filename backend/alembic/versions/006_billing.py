"""Add user_billing table for Stripe subscription tracking

Revision ID: 006
Revises: 005
Create Date: 2026-05-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_billing",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("subscription_status", sa.String(20), nullable=False, server_default="inactive"),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_user_billing_stripe_customer", "user_billing", ["stripe_customer_id"])
    op.create_index("ix_user_billing_stripe_sub", "user_billing", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_index("ix_user_billing_stripe_sub", table_name="user_billing")
    op.drop_index("ix_user_billing_stripe_customer", table_name="user_billing")
    op.drop_table("user_billing")
