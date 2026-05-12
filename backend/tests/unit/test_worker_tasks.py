"""
Unit tests for the Celery worker task helpers.

_should_process() is a pure function with no I/O, so it can be tested without
any mocking or database fixtures.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.workers.tasks import _should_process, _STALE_PROCESSING_THRESHOLD


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ago(minutes: int) -> datetime:
    return _now() - timedelta(minutes=minutes)


class TestShouldProcess:
    """_should_process(status, updated_at) → "proceed" | "skip" | "recover" """

    # ── uploaded ───────────────────────────────────────────────────────────────

    def test_uploaded_always_proceeds(self):
        assert _should_process("uploaded", _now()) == "proceed"

    def test_uploaded_with_old_timestamp_still_proceeds(self):
        assert _should_process("uploaded", _ago(60)) == "proceed"

    # ── ready / error — finished states must be skipped ──────────────────────

    def test_ready_is_skipped(self):
        assert _should_process("ready", _now()) == "skip"

    def test_error_is_skipped(self):
        assert _should_process("error", _now()) == "skip"

    # ── processing — active jobs must be skipped ──────────────────────────────

    def test_recent_processing_is_skipped(self):
        """A job that started 1 minute ago is still active — skip it."""
        assert _should_process("processing", _ago(1)) == "skip"

    def test_processing_just_under_threshold_is_skipped(self):
        margin = _STALE_PROCESSING_THRESHOLD - timedelta(seconds=30)
        assert _should_process("processing", _now() - margin) == "skip"

    # ── processing — stale jobs must trigger recovery ─────────────────────────

    def test_processing_exactly_at_threshold_triggers_recovery(self):
        assert _should_process("processing", _now() - _STALE_PROCESSING_THRESHOLD) == "recover"

    def test_processing_well_past_threshold_triggers_recovery(self):
        assert _should_process("processing", _ago(60)) == "recover"

    def test_processing_one_day_old_triggers_recovery(self):
        assert _should_process("processing", _ago(60 * 24)) == "recover"

    # ── timezone-naive updated_at ─────────────────────────────────────────────

    def test_naive_datetime_treated_as_utc_for_recent_processing(self):
        """Postgres sometimes returns tz-naive datetimes; worker must handle them."""
        naive_recent = datetime.utcnow() - timedelta(minutes=1)
        assert naive_recent.tzinfo is None
        assert _should_process("processing", naive_recent) == "skip"

    def test_naive_datetime_treated_as_utc_for_stale_processing(self):
        naive_stale = datetime.utcnow() - timedelta(hours=1)
        assert naive_stale.tzinfo is None
        assert _should_process("processing", naive_stale) == "recover"

    # ── threshold is configurable ─────────────────────────────────────────────

    def test_threshold_is_15_minutes(self):
        assert _STALE_PROCESSING_THRESHOLD == timedelta(minutes=15)
