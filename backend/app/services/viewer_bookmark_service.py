"""Bookmark CRUD operations for viewer sessions."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import ViewerBookmark


async def fetch_bookmarks(db: AsyncSession, link_id: str, session_id: str) -> dict:
    rows = (
        await db.execute(
            select(ViewerBookmark)
            .where(
                ViewerBookmark.link_id == link_id,
                ViewerBookmark.session_id == session_id,
            )
            .order_by(ViewerBookmark.page_number)
        )
    ).scalars().all()

    return {
        "bookmarks": [
            {
                "id": b.id,
                "page_number": b.page_number,
                "label": b.label,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in rows
        ]
    }


async def toggle_bookmark(
    db: AsyncSession,
    link_id: str,
    session_id: str,
    page_number: int,
    label: Optional[str] = None,
) -> dict:
    """Create bookmark if absent, delete if already bookmarked (toggle)."""
    existing = (
        await db.execute(
            select(ViewerBookmark).where(
                ViewerBookmark.link_id == link_id,
                ViewerBookmark.session_id == session_id,
                ViewerBookmark.page_number == page_number,
            )
        )
    ).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        return {"action": "removed", "page_number": page_number}

    bm = ViewerBookmark(
        link_id=link_id,
        session_id=session_id,
        page_number=page_number,
        label=label,
        created_at=datetime.now(timezone.utc),
    )
    db.add(bm)
    await db.commit()
    await db.refresh(bm)
    return {
        "action": "added",
        "id": bm.id,
        "page_number": bm.page_number,
        "label": bm.label,
    }
