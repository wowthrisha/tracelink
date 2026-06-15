"""Add viewer_annotations and viewer_bookmarks tables

Revision ID: 021
Revises: 020
Create Date: 2026-06-15

Creates:
  - viewer_annotations: overlay annotations (highlights, comments, rectangles,
    arrows, bookmarks) created by viewers on a per-link basis.  Coordinates
    are stored as normalized JSON floats (0–1 relative to page dimensions) so
    they are resolution-independent and never depend on the rendered image size.
  - viewer_bookmarks: fast-lookup alias for bookmark-type annotations; kept
    separate so we can enforce a unique constraint per (link, session, page)
    without scanning the full annotations table.

Security:
  - Both tables CASCADE-delete on share_links.id so all viewer data is wiped
    when a link is revoked or its document is deleted.
  - session_id ties each row to the ViewerSession that created it; the API
    layer enforces that PUT/DELETE can only touch the owner's rows.

Indexes:
  - (link_id, page_number) — primary hot-path: fetch all annotations for a
    given page in a single range scan.
  - session_id — used when a viewer loads their own annotations for deletion.
"""
from alembic import op
import sqlalchemy as sa


revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "viewer_annotations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "link_id",
            sa.String(36),
            sa.ForeignKey("share_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("viewer_email_masked", sa.String(255), nullable=True),
        sa.Column("page_number", sa.Integer, nullable=False),
        # 'highlight' | 'comment' | 'bookmark' | 'rectangle' | 'arrow'
        sa.Column("annotation_type", sa.String(32), nullable=False),
        # JSON: {x, y, w, h} normalized 0–1, or {x1,y1,x2,y2} for arrows
        sa.Column("coords", sa.Text, nullable=False),
        sa.Column("color", sa.String(16), nullable=True, server_default="#FFFF00"),
        sa.Column("comment_text", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_viewer_annotations_link_page",
        "viewer_annotations",
        ["link_id", "page_number"],
    )
    op.create_index(
        "ix_viewer_annotations_session",
        "viewer_annotations",
        ["session_id"],
    )

    op.create_table(
        "viewer_bookmarks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "link_id",
            sa.String(36),
            sa.ForeignKey("share_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "link_id", "session_id", "page_number",
            name="uq_viewer_bookmark_per_page",
        ),
    )
    op.create_index(
        "ix_viewer_bookmarks_link_session",
        "viewer_bookmarks",
        ["link_id", "session_id"],
    )


def downgrade():
    op.drop_index("ix_viewer_bookmarks_link_session", table_name="viewer_bookmarks")
    op.drop_table("viewer_bookmarks")
    op.drop_index("ix_viewer_annotations_session", table_name="viewer_annotations")
    op.drop_index("ix_viewer_annotations_link_page", table_name="viewer_annotations")
    op.drop_table("viewer_annotations")
