import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.event import AccessEvent
from app.models.link import ShareLink
from app.models.document import Document
from app.services.analytics_service import AnalyticsService
from app.middleware.rate_limit import limiter
from app.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
analytics_svc = AnalyticsService()


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return await analytics_svc.get_overview(db, user_id=uuid.UUID(user["user_id"]))


@router.get("/documents")
async def get_document_analytics(
    group_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    group_uuid: Optional[uuid.UUID] = None
    if group_id:
        try:
            group_uuid = uuid.UUID(group_id)
        except ValueError:
            group_uuid = None
    docs = await analytics_svc.get_document_analytics(
        db, group_id=group_uuid, user_id=uuid.UUID(user["user_id"])
    )
    for d in docs:
        d["id"] = str(d["id"])
        if d.get("group_id"):
            d["group_id"] = str(d["group_id"])
    return {"documents": docs}


@router.get("/groups")
async def get_group_analytics(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    groups = await analytics_svc.get_group_analytics(db, user_id=uuid.UUID(user["user_id"]))
    for g in groups:
        g["group_id"] = str(g["group_id"])
    return {"groups": groups}


@router.get("/events")
async def get_events(
    document_id: Optional[str] = Query(None),
    group_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
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
    user_docs_q = select(Document.id).where(Document.user_id == user_uuid)
    if doc_uuid:
        user_docs_q = user_docs_q.where(Document.id == doc_uuid)
    if group_uuid:
        user_docs_q = user_docs_q.where(Document.group_id == group_uuid)

    doc_ids_result = await db.execute(user_docs_q)
    doc_ids = [r[0] for r in doc_ids_result.all()]
    if not doc_ids:
        return {"events": [], "total": 0}

    links_result = await db.execute(
        select(ShareLink.id).where(ShareLink.document_id.in_(doc_ids))
    )
    link_ids = [row[0] for row in links_result.all()]
    if not link_ids:
        return {"events": [], "total": 0}

    # Count total — direct COUNT on the filtered set, not a subquery wrapper.
    # The ix_access_events_link_id_created composite index satisfies both the
    # count and the paginated SELECT below without a full table scan.
    from sqlalchemy import func as _func
    count_query = (
        select(_func.count())
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
                "viewer_email": e.viewer_email,
                "ip_hash": e.ip_hash,
                "session_id": e.session_id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "link_id": str(e.link_id),
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
    from app.models.event import VIEWER_LOGGABLE_EVENTS
    from app.services.policy import enforcer

    token = body.get("token", "").strip()
    session_id = body.get("session_id", "").strip()
    event_type = body.get("event_type", "").strip()
    page_number = body.get("page_number")
    metadata = body.get("metadata")

    if not token:
        raise HTTPException(status_code=400, detail="token is required")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

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

    # Verify the session is active for this specific link — prevents anyone with
    # a valid token from logging events without an established viewer session.
    if not await enforcer.is_active_session(db, link.id, session_id):
        raise HTTPException(status_code=403, detail="Invalid or expired session")

    await analytics_svc.log_event(
        db,
        link_id=link.id,
        event_type=event_type,
        page_number=page_number,
        session_id=session_id,
        ip=getattr(request.state, "client_ip", None) or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        metadata=metadata,
    )

    return {"logged": True}
