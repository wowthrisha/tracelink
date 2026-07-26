import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.event import AccessEvent
from app.models.link import ShareLink
from app.models.document import Document
from app.services.analytics_service import AnalyticsService
from app.middleware.rate_limit import limiter
from app.auth import require_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
analytics_svc = AnalyticsService()


@router.get("/overview")
@limiter.limit("30/minute")
async def get_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("analytics:read")),
):
    return await analytics_svc.get_overview(db, user_id=uuid.UUID(user["user_id"]))


@router.get("/documents")
@limiter.limit("30/minute")
async def get_document_analytics(
    request: Request,
    group_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("analytics:read")),
):
    group_uuid: Optional[uuid.UUID] = None
    if group_id:
        try:
            group_uuid = uuid.UUID(group_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid group_id format")
    docs, total = await analytics_svc.get_document_analytics(
        db, group_id=group_uuid, user_id=uuid.UUID(user["user_id"]),
        limit=limit, offset=offset,
    )
    for d in docs:
        d["id"] = str(d["id"])
        if d.get("group_id"):
            d["group_id"] = str(d["group_id"])
    return {"documents": docs, "total": total, "limit": limit, "offset": offset}


@router.get("/groups")
@limiter.limit("30/minute")
async def get_group_analytics(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("analytics:read")),
):
    groups, total = await analytics_svc.get_group_analytics(
        db, user_id=uuid.UUID(user["user_id"]), limit=limit, offset=offset,
    )
    for g in groups:
        g["group_id"] = str(g["group_id"])
    return {"groups": groups, "total": total, "limit": limit, "offset": offset}


@router.get("/page-heatmap")
@limiter.limit("30/minute")
async def get_page_heatmap(
    request: Request,
    document_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("analytics:read")),
):
    """
    Return page-level view counts and average time-on-page for a document.

    Uses existing page_viewed analytics events — no new tracking required.
    Response: {document_id, filename, page_count, total_views, pages: [{page, views, pct, avg_time_sec}]}
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id")

    result = await analytics_svc.get_page_heatmap(
        db, document_id=doc_uuid, user_id=uuid.UUID(user["user_id"])
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.get("/events")
@limiter.limit("30/minute")
async def get_events(
    request: Request,
    document_id: Optional[str] = Query(None),
    group_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("analytics:read")),
):
    user_uuid = uuid.UUID(user["user_id"])

    # Validate and coerce UUID string params; ignore silently if invalid
    doc_uuid: Optional[uuid.UUID] = None
    if document_id:
        try:
            doc_uuid = uuid.UUID(document_id)
        except ValueError:
            doc_uuid = None

    group_uuid: Optional[uuid.UUID] = None
    if group_id:
        try:
            group_uuid = uuid.UUID(group_id)
        except ValueError:
            group_uuid = None

    # Build user-scoped document ID filter, optionally narrowed by document_id / group_id
    user_docs_q = select(Document.id, Document.filename).where(Document.user_id == user_uuid)
    if doc_uuid:
        user_docs_q = user_docs_q.where(Document.id == doc_uuid)
    if group_uuid:
        user_docs_q = user_docs_q.where(Document.group_id == group_uuid)

    doc_ids_result = await db.execute(user_docs_q)
    doc_rows = doc_ids_result.all()
    doc_ids = [r[0] for r in doc_rows]
    doc_titles = {r[0]: r[1] for r in doc_rows}
    if not doc_ids:
        return {"events": [], "total": 0}

    links_result = await db.execute(
        select(ShareLink.id, ShareLink.document_id).where(ShareLink.document_id.in_(doc_ids))
    )
    link_rows = links_result.all()
    link_ids = [row[0] for row in link_rows]
    link_document_titles = {row[0]: doc_titles.get(row[1]) for row in link_rows}
    if not link_ids:
        return {"events": [], "total": 0}

    # Count total — direct COUNT on the filtered set, not a subquery wrapper.
    # The ix_access_events_link_id_created composite index satisfies both the
    # count and the paginated SELECT below without a full table scan.
    count_query = (
        select(func.count())
        .select_from(AccessEvent)
        .where(AccessEvent.link_id.in_(link_ids))
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        select(AccessEvent)
        .where(AccessEvent.link_id.in_(link_ids))
        .order_by(AccessEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    events_result = await db.execute(query)
    events = events_result.scalars().all()

    return {
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "page_number": e.page_number,
                "time_spent_ms": e.time_spent_ms,
                "viewer_email": e.viewer_email,
                "ip_hash": e.ip_hash,
                "session_id": e.session_id[:8] if e.session_id else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "link_id": str(e.link_id),
                "document_title": link_document_titles.get(e.link_id),
            }
            for e in events
        ],
        "total": total,
    }


@router.post("/events")
@limiter.limit("60/minute")
async def log_viewer_event(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Client-side event logging for the viewer frontend.

    Requires a valid share-link token AND an active session_id — prevents
    unauthenticated callers from polluting analytics or inflating event counts.
    Only viewer-initiated events are accepted; server-side security events
    (revoked, expired, ip_blocked, etc.) cannot be logged through this endpoint.
    """
    from datetime import datetime, timezone
    from app.models.event import VIEWER_LOGGABLE_EVENTS
    from app.services.policy import enforcer

    # SEC: validate body field types explicitly — body: dict accepts any JSON type.
    # A non-string token/session_id would cause AttributeError on .strip() → 500.
    _raw_token = body.get("token")
    if not isinstance(_raw_token, str) or not _raw_token.strip():
        raise HTTPException(status_code=400, detail="token is required")
    token = _raw_token.strip()

    _raw_session = body.get("session_id")
    if not isinstance(_raw_session, str) or not _raw_session.strip():
        raise HTTPException(status_code=400, detail="session_id is required")
    session_id = _raw_session.strip()

    _raw_event_type = body.get("event_type")
    if not isinstance(_raw_event_type, str):
        raise HTTPException(status_code=400, detail="event_type must be a string")
    event_type = _raw_event_type.strip()

    page_number = body.get("page_number")
    metadata = body.get("metadata")
    time_spent_ms = body.get("time_spent_ms")

    # SEC: page_number must be a positive integer when supplied — prevents analytics
    # poisoning via out-of-range or negative page numbers from client-side code.
    if page_number is not None:
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
            raise HTTPException(status_code=400, detail="page_number must be a positive integer")

    # time_spent_ms must be a non-negative integer when supplied.
    if time_spent_ms is not None:
        if not isinstance(time_spent_ms, int) or isinstance(time_spent_ms, bool) or time_spent_ms < 0:
            raise HTTPException(
                status_code=400,
                detail="time_spent_ms must be a non-negative integer (milliseconds)",
            )
        # Cap at 4 hours to prevent absurd values that would skew averages.
        if time_spent_ms > 14_400_000:
            time_spent_ms = 14_400_000

    # Restrict metadata size to prevent storage-inflation attacks.
    # A viewer with a valid session could otherwise spam large payloads at the
    # rate limit (60/min), inflating the database at ~86 MB/day per IP.
    _METADATA_MAX_BYTES = 1024
    if metadata is not None:
        import json as _json
        try:
            _meta_str = _json.dumps(metadata)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="metadata must be a JSON object")
        if len(_meta_str) > _METADATA_MAX_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"metadata exceeds {_METADATA_MAX_BYTES} bytes",
            )

    # Restrict to viewer-side events only
    if event_type not in VIEWER_LOGGABLE_EVENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Allowed: {sorted(VIEWER_LOGGABLE_EVENTS)}",
        )

    link_result = await db.execute(select(ShareLink).where(ShareLink.token == token))
    link = link_result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # SEC: reject event logging for revoked or expired links even when the viewer
    # session is still technically active (sessions outlive link revocation by up to
    # 2 h).  This prevents a revoked-link viewer from polluting analytics records
    # after the link owner has cut access.
    now = datetime.now(timezone.utc)
    if link.revoked_at is not None:
        raise HTTPException(status_code=410, detail="Link revoked")
    if link.expires_at is not None:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < now:
            raise HTTPException(status_code=410, detail="Link expired")

    # Verify the session is active for this specific link — prevents anyone with
    # a valid token from logging events without an established viewer session.
    if not await enforcer.is_active_session(db, link.id, session_id):
        raise HTTPException(status_code=403, detail="Invalid or expired session")

    # SEC: validate page_number against document page_count — prevents poisoning
    # analytics with out-of-range page numbers (e.g., page 9999 on a 5-page doc).
    if page_number is not None:
        from app.models.document import Document as _Document
        _doc_row = await db.execute(select(_Document).where(_Document.id == link.document_id))
        _doc = _doc_row.scalar_one_or_none()
        if _doc and _doc.page_count and page_number > _doc.page_count:
            raise HTTPException(
                status_code=400,
                detail=f"page_number {page_number} exceeds document page count",
            )

    await analytics_svc.log_event(
        db,
        link_id=link.id,
        event_type=event_type,
        page_number=page_number,
        session_id=session_id,
        ip=getattr(request.state, "client_ip", None) or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        metadata=metadata,
        time_spent_ms=time_spent_ms,
    )

    # Trigger analytics.completed webhook (fire-and-forget, never fails the response)
    if event_type == "completed":
        try:
            from app.models.document import Document as _Document
            _doc_row = await db.execute(
                select(_Document).where(_Document.id == link.document_id)
            )
            _doc = _doc_row.scalar_one_or_none()
            if _doc:
                from app.services.webhook_service import dispatch_webhook_event
                await dispatch_webhook_event(
                    db,
                    user_id=str(_doc.user_id),
                    event_type="analytics.completed",
                    data={
                        "document_id": str(link.document_id),
                        "filename": _doc.filename,
                        "link_id": str(link.id),
                        "session_id_prefix": session_id[:8] if session_id else None,
                        "page_count": _doc.page_count,
                        "time_spent_ms": time_spent_ms,
                    },
                )
        except Exception as _exc:
            logger.warning("analytics.completed webhook trigger failed: %s", _exc)

    return {"logged": True}
