"""add organizations, org_memberships, and documents.org_id

Revision ID: 016
Revises: 015
Create Date: 2026-06-07

Adds multi-tenant organization model. Documents gain optional org_id.
Existing documents are unaffected (org_id defaults to NULL).
"""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("saml_domain", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "org_memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="viewer"),
        sa.Column("invited_by_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_memberships_org_user"),
    )
    op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])

    op.add_column(
        "documents",
        sa.Column("org_id", sa.UUID(), nullable=True),
    )
    op.create_index("ix_documents_org_id", "documents", ["org_id"])


def downgrade():
    op.drop_index("ix_documents_org_id", "documents")
    op.drop_column("documents", "org_id")
    op.drop_index("ix_org_memberships_user_id", "org_memberships")
    op.drop_table("org_memberships")
    op.drop_index("ix_organizations_slug", "organizations")
    op.drop_table("organizations")
