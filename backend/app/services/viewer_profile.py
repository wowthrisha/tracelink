"""Viewer identity resolution.

Derives a human display name from an email address and resolves/creates the
global ViewerProfile row for that email. This is the only place plaintext
viewer email is read for identity purposes — callers must already have
validated the email via the share-link gate before calling here.
"""
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.viewer_profile import ViewerProfile

_SPLIT_RE = re.compile(r"[._\-+]+")


def derive_display_name(email: str) -> str:
    """Best-effort human name from an email's local-part.

    "john.doe@x.com" -> "John Doe"; "jdoe123@x.com" -> "Jdoe123" (no
    separators to split on, so we just capitalize what's there).
    """
    local = email.split("@", 1)[0]
    tokens = [t for t in _SPLIT_RE.split(local) if t and not t.isdigit()]
    if not tokens:
        return local.capitalize() if local else "Anonymous Viewer"
    return " ".join(t.capitalize() for t in tokens)


async def get_or_create_viewer_profile(db: AsyncSession, email: str) -> Optional[ViewerProfile]:
    """Resolve the ViewerProfile for an email, creating it on first sight.

    Returns None if email is falsy — callers should treat that as "no
    identity available" rather than fabricating a profile.
    """
    if not email:
        return None
    normalized = email.strip().lower()
    if not normalized:
        return None

    now = datetime.now(timezone.utc)
    existing = (
        await db.execute(select(ViewerProfile).where(ViewerProfile.email == normalized))
    ).scalar_one_or_none()
    if existing:
        existing.last_seen_at = now
        return existing

    profile = ViewerProfile(
        email=normalized,
        display_name=derive_display_name(normalized),
        first_seen_at=now,
        last_seen_at=now,
    )
    db.add(profile)
    await db.flush()
    return profile
