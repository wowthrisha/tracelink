"""Annotation filter utilities — pure functions with no HTTP or DB dependencies."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

_UPLOADER_SESSION_PREFIX = "uploader:"


def _parse_filter_date(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    """Parse a date_from/date_to query param into a tz-aware UTC datetime.

    Accepts a bare date ("2026-06-01") or a full ISO timestamp. A bare date
    passed as date_to is treated as the end of that day so "date_to=today"
    includes everything created today.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid date: {value!r}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if end_of_day and len(value) <= 10:  # bare "YYYY-MM-DD", no time component
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return dt


def _as_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """sqlite drops tzinfo on round-trip; treat a naive value as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _message_matches_filters(
    a,
    *,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    page_number: Optional[int],
    author_role: Optional[str],
    reviewer_email: Optional[str] = None,
) -> bool:
    """True if a single message (root or reply) satisfies every active filter."""
    if page_number is not None and a.page_number != page_number:
        return False
    if author_role is not None:
        role = "uploader" if (a.session_id or "").startswith(_UPLOADER_SESSION_PREFIX) else "viewer"
        if role != author_role:
            return False
    if reviewer_email is not None and (a.viewer_email or "").lower() != reviewer_email.lower():
        return False
    created_at = _as_aware_utc(a.created_at)
    if date_from is not None and (created_at is None or created_at < date_from):
        return False
    if date_to is not None and (created_at is None or created_at > date_to):
        return False
    return True


def _thread_matches_filters(messages, **filters) -> bool:
    """A thread matches if ANY message in it satisfies all active filters."""
    return any(_message_matches_filters(m, **filters) for m in messages)
