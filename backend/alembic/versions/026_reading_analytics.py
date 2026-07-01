"""Reading Intelligence Engine — reading_sessions, page_reading_events, document_complexity

Revision ID: 026
Revises: 025
Create Date: 2026-07-01

Adds three tables for the Reading Intelligence Engine:
  reading_sessions      — per-viewer-session aggregate analytics
  page_reading_events   — per-page per-session detail
  document_complexity   — cached per-document complexity metrics for speed model

All three tables are append/upsert-only from the /api/reading/batch endpoint.
Queries hit indexed columns (session_id, document_id) so no full-table scans.
"""
import sqlalchemy as sa
from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reading_sessions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(32), nullable=False),
        sa.Column("link_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.UUID(as_uuid=True), nullable=False),
        # Timing
        sa.Column("total_active_ms", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_elapsed_ms", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_idle_ms", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_pause_ms", sa.BigInteger, nullable=False, server_default="0"),
        # Page coverage
        sa.Column("pages_visited", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pages_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pages_skipped", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pages_revisited", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_pct", sa.Float, nullable=False, server_default="0"),
        # Speed model
        sa.Column("avg_ms_per_page", sa.Float, nullable=True),
        sa.Column("reading_speed_wpm", sa.Float, nullable=True),
        sa.Column("fastest_page", sa.Integer, nullable=True),
        sa.Column("slowest_page", sa.Integer, nullable=True),
        sa.Column("drop_off_page", sa.Integer, nullable=True),
        sa.Column("confusion_page", sa.Integer, nullable=True),
        # Engagement scores
        sa.Column("engagement_score", sa.Float, nullable=True),
        sa.Column("absorption_score", sa.Float, nullable=True),
        sa.Column("focus_score", sa.Float, nullable=True),
        sa.Column("reading_consistency", sa.Float, nullable=True),
        sa.Column("attention_stability", sa.Float, nullable=True),
        sa.Column("understanding_confidence", sa.Float, nullable=True),
        # Interaction
        sa.Column("total_annotations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_copy_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_print_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_idle_events", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reading_interruptions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_pause_ms", sa.Float, nullable=True),
        sa.Column("tab_switch_count", sa.Integer, nullable=False, server_default="0"),
        # Prediction
        sa.Column("initial_estimate_ms", sa.BigInteger, nullable=True),
        sa.Column("prediction_accuracy_pct", sa.Float, nullable=True),
        sa.Column("viewer_email_masked", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["link_id"], ["share_links.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", name="uq_reading_sessions_session_id"),
    )
    op.create_index("ix_rs_link_id", "reading_sessions", ["link_id"])
    op.create_index("ix_rs_document_id", "reading_sessions", ["document_id"])
    op.create_index("ix_rs_session_id", "reading_sessions", ["session_id"])
    op.create_index("ix_rs_document_started", "reading_sessions", ["document_id", "started_at"])

    op.create_table(
        "page_reading_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("reading_session_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(32), nullable=False),
        sa.Column("document_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("enter_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_time_ms", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("pause_duration_ms", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("revisit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("scroll_percentage", sa.Float, nullable=False, server_default="0"),
        sa.Column("zoom_level", sa.Integer, nullable=False, server_default="100"),
        sa.Column("fullscreen_used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("annotations_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("copy_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("print_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tab_switch_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("visibility_changes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("idle_events", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_status",
                  sa.Enum("unread", "started", "reading", "completed", "revisited", "skipped",
                          name="page_completion_status_enum"),
                  nullable=False, server_default="unread"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["reading_session_id"], ["reading_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pre_session_id", "page_reading_events", ["session_id"])
    op.create_index("ix_pre_document_page", "page_reading_events", ["document_id", "page_number"])
    op.create_index("ix_pre_reading_session", "page_reading_events", ["reading_session_id"])

    op.create_table(
        "document_complexity",
        sa.Column("document_id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("word_count", sa.BigInteger, nullable=True),
        sa.Column("page_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("estimated_words_per_page", sa.Float, nullable=False, server_default="250"),
        sa.Column("image_density", sa.Float, nullable=False, server_default="0"),
        sa.Column("table_density", sa.Float, nullable=False, server_default="0"),
        sa.Column("avg_page_length_ratio", sa.Float, nullable=False, server_default="1"),
        sa.Column("complexity_factor", sa.Float, nullable=False, server_default="1"),
        sa.Column("baseline_wpm", sa.Float, nullable=False, server_default="200"),
        sa.Column("median_completion_ms", sa.BigInteger, nullable=True),
        sa.Column("p25_completion_ms", sa.BigInteger, nullable=True),
        sa.Column("p75_completion_ms", sa.BigInteger, nullable=True),
        sa.Column("session_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("document_complexity")
    op.drop_index("ix_pre_reading_session", table_name="page_reading_events")
    op.drop_index("ix_pre_document_page", table_name="page_reading_events")
    op.drop_index("ix_pre_session_id", table_name="page_reading_events")
    op.drop_table("page_reading_events")
    op.drop_index("ix_rs_document_started", table_name="reading_sessions")
    op.drop_index("ix_rs_session_id", table_name="reading_sessions")
    op.drop_index("ix_rs_document_id", table_name="reading_sessions")
    op.drop_index("ix_rs_link_id", table_name="reading_sessions")
    op.drop_table("reading_sessions")
    op.execute("DROP TYPE IF EXISTS page_completion_status_enum")
