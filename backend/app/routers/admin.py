import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.audit import AdminAuditLog, AUDIT_EVENT_TYPES

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/audit-log")
async def get_audit_log(
    org_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    date_from: Optional[str] = Query(None, description="ISO date filter start (inclusive), e.g. 2026-01-01"),
    date_to: Optional[str] = Query(None, description="ISO date filter end (inclusive), e.g. 2026-06-30"),
    event_type: Optional[str] = Query(None, description="Filter by event type, e.g. document.deleted"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Retrieve admin audit log entries.

    - With org_id: returns entries for that org; requires admin/owner role
    - Without org_id: returns entries where current user is the actor
    """
    user_uuid = uuid.UUID(user["user_id"])

    query = select(AdminAuditLog)

    if org_id:
        try:
            org_uuid = uuid.UUID(org_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="org_id must be a valid UUID")

        # Verify caller is admin/owner of the org
        from app.services.org_service import get_membership, role_gte
        membership = await get_membership(db, org_uuid, user_uuid)
        if not membership or not role_gte(membership.role, "admin"):
            raise HTTPException(
                status_code=403,
                detail="Requires admin role or higher in the organization",
            )
        query = query.where(AdminAuditLog.org_id == org_uuid)
    else:
        # Without org_id: return only entries where caller is the actor
        query = query.where(AdminAuditLog.actor_user_id == user_uuid)

    # Optional filters
    if event_type:
        if event_type not in AUDIT_EVENT_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"event_type must be one of: {sorted(AUDIT_EVENT_TYPES)}",
            )
        query = query.where(AdminAuditLog.event_type == event_type)
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=422, detail="date_from must be ISO format, e.g. 2026-01-01")
        query = query.where(AdminAuditLog.created_at >= dt_from)
    if date_to:
        try:
            # Make date_to inclusive of the full day
            dt_to = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=422, detail="date_to must be ISO format, e.g. 2026-06-30")
        query = query.where(AdminAuditLog.created_at <= dt_to)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(AdminAuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    entries = result.scalars().all()

    def _serialize(e: AdminAuditLog) -> dict:
        details = None
        if e.details_json:
            try:
                details = json.loads(e.details_json)
            except Exception:
                details = e.details_json
        return {
            "id": str(e.id),
            "org_id": str(e.org_id) if e.org_id else None,
            "actor_user_id": str(e.actor_user_id),
            "event_type": e.event_type,
            "target_type": e.target_type,
            "target_id": e.target_id,
            "details": details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }

    return {
        "events": [_serialize(e) for e in entries],
        "total": total,
        "offset": offset,
        "limit": limit,
        "available_event_types": sorted(AUDIT_EVENT_TYPES),
    }
