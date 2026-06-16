"""Add viewer_profiles + plaintext viewer_email on sessions/annotations

Revision ID: 024
Revises: 023
Create Date: 2026-06-17

Identity persistence (Step 1 of feedback UX overhaul):
  - New viewer_profiles table: global, cross-document identity keyed by
    verified email, with a display name derived from the email local-part.
  - viewer_sessions.viewer_email / viewer_profile_id: plaintext email +
    resolved profile, captured only when a link's email gate validates it.
  - viewer_annotations.viewer_email / viewer_profile_id: same, copied from
    the session at annotation-creation time.

No backfill of historical rows: prior to this migration the system only
ever stored a masked email (app/utils/crypto.mask_email — first local-part
char + domain). Plaintext was never persisted anywhere, including the
analytics event log, so there is no source of truth to recover real
identities from for existing rows. Those rows are left with NULL
viewer_email / viewer_profile_id and will read as "Anonymous Viewer" once
the serializer layer is updated (next phase) — fabricating a profile from
the masked remnant would risk merging unrelated viewers under one identity.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None

_uuid = PGUUID(as_uuid=False)


def upgrade():
    op.create_table(
        "viewer_profiles",
        sa.Column("id", _uuid, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_viewer_profiles_email", "viewer_profiles", ["email"], unique=True)

    op.add_column("viewer_sessions", sa.Column("viewer_email", sa.String(255), nullable=True))
    op.add_column(
        "viewer_sessions",
        sa.Column("viewer_profile_id", _uuid, sa.ForeignKey("viewer_profiles.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_viewer_sessions_profile", "viewer_sessions", ["viewer_profile_id"])

    op.add_column("viewer_annotations", sa.Column("viewer_email", sa.String(255), nullable=True))
    op.add_column(
        "viewer_annotations",
        sa.Column("viewer_profile_id", _uuid, sa.ForeignKey("viewer_profiles.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_viewer_annotations_profile", "viewer_annotations", ["viewer_profile_id"])


def downgrade():
    op.drop_index("ix_viewer_annotations_profile", table_name="viewer_annotations")
    op.drop_column("viewer_annotations", "viewer_profile_id")
    op.drop_column("viewer_annotations", "viewer_email")

    op.drop_index("ix_viewer_sessions_profile", table_name="viewer_sessions")
    op.drop_column("viewer_sessions", "viewer_profile_id")
    op.drop_column("viewer_sessions", "viewer_email")

    op.drop_index("ix_viewer_profiles_email", table_name="viewer_profiles")
    op.drop_table("viewer_profiles")
