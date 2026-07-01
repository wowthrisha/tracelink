"""Reading Intelligence Engine — REST API router.

Endpoints:
  POST /api/reading/batch                           viewer batch ingest
  GET  /api/reading/session/{session_id}            viewer's own summary
  GET  /api/reading/document/{document_id}/summary  uploader summary
  GET  /api/reading/document/{document_id}/heatmap  rich page heatmap
  GET  /api/reading/document/{document_id}/insights NL insights
  GET  /api/reading/document/{document_id}/viewers  per-viewer breakdown
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_scope
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.link import ShareLink
from app.services.policy import enforcer
from app.services.reading_analytics_service import ReadingAnalyticsService
from app.utils.crypto import mask_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reading", tags=["reading"])
svc = ReadingAnalyticsService()


@router.post("/batch")
@limiter.limit("30/minute")
async def ingest_batch(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Batch ingest reading analytics events from the viewer frontend.

    Requires a valid share-link token + active session_id (same as /api/analytics/events).
    All timing values are in milliseconds.

    Request body:
      token         str      share link token
      session_id    str      viewer session id
      page_data     list     per-page analytics (see schema below)
      session_meta  dict     session-level timing metadata

    page_data item fields:
      page_number, active_time_ms, pause_duration_ms, revisit_count,
      scroll_percentage, zoom_level, fullscreen_used, annotations_created,
      copy_attempts, print_attempts, tab_switch_count, visibility_changes,
      idle_events, completion_status, enter_timestamp, exit_timestamp

    session_meta fields:
      total_elapsed_ms, total_active_ms, started_at, page_count,
      current_page, initial_estimate_ms
    """
    # -- Input validation --
    raw_token = body.get("token")
    if not isinstance(raw_token, str) or not raw_token.strip():
        raise HTTPException(status_code=400, detail="token is required")
    token = raw_token.strip()

    raw_session = body.get("session_id")
    if not isinstance(raw_session, str) or not raw_session.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    session_id = raw_session.strip()

    page_data = body.get("page_data", [])
    if not isinstance(page_data, list):
        raise HTTPException(status_code=400, detail="page_data must be a list")
    if len(page_data) > 500:
        raise HTTPException(status_code=400, detail="page_data exceeds 500 items")

    session_meta = body.get("session_meta", {})
    if not isinstance(session_meta, dict):
        session_meta = {}

    # Validate timing values
    for key in ("total_elapsed_ms", "total_active_ms"):
        val = session_meta.get(key)
        if val is not None:
            if not isinstance(val, (int, float)) or val < 0:
                raise HTTPException(status_code=400, detail=f"{key} must be a non-negative number")
            # Cap at 24 hours
            session_meta[key] = min(val, 86_400_000)

    # Verify link + session
    link_result = await db.execute(select(ShareLink).where(ShareLink.token == token))
    link = link_result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if not await enforcer.is_active_session(db, link.id, session_id):
        raise HTTPException(status_code=403, detail="Invalid or expired session")

    # Sanitize page_data items
    clean_page_data = []
    for item in page_data:
        if not isinstance(item, dict):
            continue
        pn = item.get("page_number")
        if not isinstance(pn, int) or pn < 1:
            continue
        active_ms = item.get("active_time_ms", 0)
        if not isinstance(active_ms, (int, float)) or active_ms < 0:
            active_ms = 0
        # Cap per-page active time at 4 hours
        item["active_time_ms"] = int(min(active_ms, 14_400_000))
        item["pause_duration_ms"] = int(min(max(item.get("pause_duration_ms", 0) or 0, 0), 14_400_000))
        item["revisit_count"] = int(max(item.get("revisit_count", 0) or 0, 0))
        item["scroll_percentage"] = float(max(min(item.get("scroll_percentage", 0.0) or 0.0, 100.0), 0.0))
        item["zoom_level"] = int(max(min(item.get("zoom_level", 100) or 100, 500), 10))
        item["tab_switch_count"] = int(max(item.get("tab_switch_count", 0) or 0, 0))
        item["visibility_changes"] = int(max(item.get("visibility_changes", 0) or 0, 0))
        item["idle_events"] = int(max(item.get("idle_events", 0) or 0, 0))
        item["annotations_created"] = int(max(item.get("annotations_created", 0) or 0, 0))
        item["copy_attempts"] = int(max(item.get("copy_attempts", 0) or 0, 0))
        item["print_attempts"] = int(max(item.get("print_attempts", 0) or 0, 0))
        valid_statuses = {"unread", "started", "reading", "completed", "revisited", "skipped"}
        if item.get("completion_status") not in valid_statuses:
            item["completion_status"] = "unread"
        clean_page_data.append(item)

    result = await svc.ingest_batch(
        db=db,
        token=token,
        session_id=session_id,
        page_data=clean_page_data,
        session_meta=session_meta,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/session/{session_id}")
@limiter.limit("60/minute")
async def get_viewer_session(
    request: Request,
    session_id: str,
    token: str = Query(..., description="Share link token for authentication"),
    db: AsyncSession = Depends(get_db),
):
    """Viewer's own reading analytics for their current session.

    Authentication: share link token + session_id (same auth as viewer endpoints).
    Returns only the viewer's own data — never reveals uploader-level stats.
    """
    link_result = await db.execute(select(ShareLink).where(ShareLink.token == token))
    link = link_result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if not await enforcer.is_active_session(db, link.id, session_id):
        raise HTTPException(status_code=403, detail="Invalid or expired session")

    summary = await svc.get_viewer_session_summary(db, session_id)
    if not summary:
        # No reading data yet — return zeros
        return {
            "total_active_ms": 0,
            "total_elapsed_ms": 0,
            "estimated_remaining_ms": None,
            "completion_pct": 0.0,
            "pages_visited": 0,
            "pages_completed": 0,
            "page_count": 0,
            "reading_speed_wpm": None,
            "avg_ms_per_page": None,
            "engagement_score": None,
            "focus_score": None,
        }
    return summary


@router.get("/document/{document_id}/summary")
@limiter.limit("30/minute")
async def get_document_summary(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("analytics:read")),
):
    """Uploader-facing document reading analytics summary."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id")

    result = await svc.get_document_summary(db, doc_uuid, uuid.UUID(user["user_id"]))
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.get("/document/{document_id}/heatmap")
@limiter.limit("30/minute")
async def get_document_heatmap(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("analytics:read")),
):
    """Rich per-page heatmap for the uploader dashboard."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id")

    result = await svc.get_page_heatmap_rich(db, doc_uuid, uuid.UUID(user["user_id"]))
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.get("/document/{document_id}/insights")
@limiter.limit("20/minute")
async def get_document_insights(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("analytics:read")),
):
    """Generate natural-language insights from collected reading data."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id")

    result = await svc.get_insights(db, doc_uuid, uuid.UUID(user["user_id"]))
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.get("/document/{document_id}/viewers")
@limiter.limit("20/minute")
async def get_document_viewers(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("analytics:read")),
):
    """Per-viewer breakdown table for the uploader dashboard."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id")

    result = await svc.get_viewer_breakdown(db, doc_uuid, uuid.UUID(user["user_id"]))
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result
