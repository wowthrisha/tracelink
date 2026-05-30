"""Add viewer_email_masked to viewer_sessions for forensic watermark provenance

Revision ID: 010
Revises: 009
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "viewer_sessions",
        sa.Column("viewer_email_masked", sa.String(255), nullable=True),
    )


def downgrade():
    op.drop_column("viewer_sessions", "viewer_email_masked")
