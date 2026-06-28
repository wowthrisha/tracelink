import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.audit import AdminAuditLog

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/audit-log")
async def get_audit_log(
    org_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
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

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(AdminAuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    entries = result.scalars().all()

    return {
        "events": [
            {
                "id": str(e.id),
                "org_id": str(e.org_id) if e.org_id else None,
                "actor_user_id": str(e.actor_user_id),
                "event_type": e.event_type,
                "target_type": e.target_type,
                "target_id": e.target_id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }
