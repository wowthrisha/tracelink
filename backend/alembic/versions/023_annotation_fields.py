"""Add sticky_note/draw support, resolved_at, parent_id, thickness to viewer_annotations

Revision ID: 023
Revises: 022
Create Date: 2026-06-15

Changes:
  viewer_annotations:
    - thickness    INTEGER  nullable  (stroke width for draw/rectangle/arrow)
    - resolved_at  TIMESTAMPTZ nullable  (set when comment resolved by owner)
    - parent_id    UUID FK->viewer_annotations.id nullable  (reply threading)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None

_uuid = PGUUID(as_uuid=False)


def upgrade():
    op.add_column("viewer_annotations", sa.Column("thickness", sa.Integer, nullable=True, server_default="2"))
    op.add_column("viewer_annotations", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "viewer_annotations",
        sa.Column(
            "parent_id",
            _uuid,
            sa.ForeignKey("viewer_annotations.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_viewer_annotations_parent", "viewer_annotations", ["parent_id"])


def downgrade():
    op.drop_index("ix_viewer_annotations_parent", table_name="viewer_annotations")
    op.drop_column("viewer_annotations", "parent_id")
    op.drop_column("viewer_annotations", "resolved_at")
    op.drop_column("viewer_annotations", "thickness")
