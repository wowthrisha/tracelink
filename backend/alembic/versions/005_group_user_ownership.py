"""Add user_id ownership to document_groups for multi-user isolation

Revision ID: 005
Revises: 004
Create Date: 2026-05-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column (nullable — existing groups become orphaned/invisible)
    op.add_column(
        "document_groups",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_index("ix_document_groups_user_id", "document_groups", ["user_id"])

    # Drop old global unique constraint on name
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        op.drop_constraint("document_groups_name_key", "document_groups", type_="unique")
    # SQLite: can't drop constraints; new DB starts fresh so no issue.

    # Add new per-user unique constraint (name unique per user)
    op.create_unique_constraint(
        "uq_group_user_name", "document_groups", ["user_id", "name"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_group_user_name", "document_groups", type_="unique")
    op.drop_index("ix_document_groups_user_id", table_name="document_groups")
    op.drop_column("document_groups", "user_id")
    # Re-add global name uniqueness (best effort; may fail if duplicates exist)
    op.create_unique_constraint(
        "document_groups_name_key", "document_groups", ["name"]
    )
