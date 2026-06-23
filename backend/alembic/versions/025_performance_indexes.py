"""Add missing performance indexes for analytics and active-link queries

Revision ID: 025
Revises: 024
Create Date: 2026-06-23

Three indexes identified as missing during Sprint 5.2 compliance review
and verified in Phase 0 of Sprint 5.3 hardening:

1. access_events (link_id, event_type)
   Every analytics aggregate query filters on both columns.  The existing
   (link_id) index forces a post-scan filter on event_type; the composite
   index eliminates that step.  6 queries per analytics page load benefit.

2. share_links (document_id, revoked_at)
   Active-link queries filter on document_id AND revoked_at IS NULL.  The
   existing (document_id) index requires a post-filter pass over all links
   for a document to find non-revoked ones.

3. documents (group_id)
   get_group_analytics() issues WHERE group_id IN (...) with no supporting
   index.  Migration 002 added the group_id FK but not an index.
"""
from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_access_events_link_event",
        "access_events",
        ["link_id", "event_type"],
    )
    op.create_index(
        "ix_share_links_doc_revoked",
        "share_links",
        ["document_id", "revoked_at"],
    )
    op.create_index(
        "ix_documents_group_id",
        "documents",
        ["group_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_group_id", table_name="documents")
    op.drop_index("ix_share_links_doc_revoked", table_name="share_links")
    op.drop_index("ix_access_events_link_event", table_name="access_events")
