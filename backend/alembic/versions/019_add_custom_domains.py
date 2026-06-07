"""add custom domain fields to organizations

Revision ID: 019
Revises: 018
Create Date: 2026-06-07

Adds custom_domain, custom_domain_verified, custom_domain_verified_at to
organizations. Allows orgs to use their own domain for share link URLs.
"""
from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "organizations",
        sa.Column("custom_domain", sa.String(253), nullable=True),
    )
    op.create_unique_constraint(
        "uq_organizations_custom_domain",
        "organizations",
        ["custom_domain"],
    )
    op.add_column(
        "organizations",
        sa.Column(
            "custom_domain_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("custom_domain_verified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("organizations", "custom_domain_verified_at")
    op.drop_column("organizations", "custom_domain_verified")
    op.drop_constraint("uq_organizations_custom_domain", "organizations", type_="unique")
    op.drop_column("organizations", "custom_domain")
