"""Storage management API.

Endpoints:
  GET  /api/storage/dashboard        — storage totals per user + per document
  GET  /api/storage/forecast         — current + 30d + 90d byte projections
  GET  /api/storage/documents        — per-document storage breakdown
  PATCH /api/documents/{id}/retention — update retention policy on existing doc
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_scope
from app.database import get_db
from app.models.document import Document, RETENTION_POLICIES
from app.models.storage_snapshot import StorageSnapshot
from app.services.retention import compute_expires_at

logger = logging.getLogger(__name__)
router = APIRouter(tags=["storage"])

_BYTES_PER_MB = 1_048_576


def _effective_bytes(doc: Document) -> int:
    """Return the best available storage estimate for a document."""
    if doc.storage_bytes_computed:
        return doc.storage_bytes_computed
    return doc.file_size_bytes or 0


# ── GET /api/storage/dashboard ────────────────────────────────────────────────

@router.get("/api/storage/dashboard")
async def storage_dashboard(
    org_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:read")),
):
    """Return storage totals for the authenticated user (or a specific org they belong to)."""
    user_uuid = uuid.UUID(user["user_id"])

    base_q = select(Document).where(
        Document.user_id == user_uuid,
        Document.lifecycle_state != "deleted",
    )
    if org_id:
        try:
            oid = uuid.UUID(org_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid org_id")
        base_q = base_q.where(Document.org_id == oid)

    docs = (await db.execute(base_q)).scalars().all()

    # Bulk-load groups for all documents that have a group_id
    group_ids = {d.group_id for d in docs if d.group_id}
    groups_by_id: dict = {}
    if group_ids:
        from app.models.group import DocumentGroup
        group_rows = (
            await db.execute(select(DocumentGroup).where(DocumentGroup.id.in_(group_ids)))
        ).scalars().all()
        groups_by_id = {g.id: g for g in group_rows}

    total_bytes = sum(_effective_bytes(d) for d in docs)
    active_count = sum(1 for d in docs if d.lifecycle_state == "active")
    archived_count = sum(1 for d in docs if d.lifecycle_state == "archived")
    expired_count = sum(1 for d in docs if d.lifecycle_state == "expired")

    by_doc = [
        {
            "id": str(d.id),
            "filename": d.filename,
            "file_type": d.file_type,
            "lifecycle_state": d.lifecycle_state,
            "retention_policy": d.retention_policy,
            "expires_at": d.expires_at.isoformat() if d.expires_at else None,
            "last_viewed_at": d.last_viewed_at.isoformat() if d.last_viewed_at else None,
            "last_accessed_at": d.last_accessed_at.isoformat() if d.last_accessed_at else None,
            "storage_bytes": _effective_bytes(d),
            "file_size_bytes": d.file_size_bytes,
            "storage_bytes_computed": d.storage_bytes_computed,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "group_id": str(d.group_id) if d.group_id else None,
            "group_name": groups_by_id[d.group_id].name if d.group_id and d.group_id in groups_by_id else None,
            "group_color": groups_by_id[d.group_id].color if d.group_id and d.group_id in groups_by_id else None,
        }
        for d in sorted(docs, key=lambda d: _effective_bytes(d), reverse=True)
    ]

    # Per-org breakdown (only if user has multiple orgs)
    org_totals = {}
    for d in docs:
        key = str(d.org_id) if d.org_id else "_personal"
        org_totals[key] = org_totals.get(key, 0) + _effective_bytes(d)

    # Load org names for the breakdown
    org_ids_to_lookup = [k for k in org_totals if k != "_personal"]
    org_names: dict = {}
    if org_ids_to_lookup:
        from app.models.org import Organization
        org_rows = (
            await db.execute(
                select(Organization).where(Organization.id.in_([uuid.UUID(oid) for oid in org_ids_to_lookup]))
            )
        ).scalars().all()
        org_names = {str(o.id): o.name for o in org_rows}

    return {
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / _BYTES_PER_MB, 2),
        "document_count": len(docs),
        "active_count": active_count,
        "archived_count": archived_count,
        "expired_count": expired_count,
        "by_document": by_doc,
        "by_org": [
            {
                "org_id": k,
                "org_name": "Personal" if k == "_personal" else org_names.get(k, k[:8] + "…"),
                "total_bytes": v,
                "total_mb": round(v / _BYTES_PER_MB, 2),
            }
            for k, v in org_totals.items()
        ],
    }


# ── GET /api/storage/forecast ─────────────────────────────────────────────────

@router.get("/api/storage/forecast")
async def storage_forecast(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:read")),
):
    """Return current storage usage and 30-day / 90-day projections.

    Growth rate is derived from the most recent 30-day average of bytes
    uploaded.  Planned deletions (docs with expires_at within the window)
    are subtracted from the forward projection.
    """
    user_uuid = uuid.UUID(user["user_id"])
    now = datetime.now(timezone.utc)
    window_30d = now - timedelta(days=30)

    # Current total (active + archived docs only)
    all_docs = (
        await db.execute(
            select(Document).where(
                Document.user_id == user_uuid,
                Document.lifecycle_state.in_(("active", "archived")),
            )
        )
    ).scalars().all()

    current_bytes = sum(_effective_bytes(d) for d in all_docs)

    # Daily growth rate from docs uploaded in the last 30 days
    recent_docs = [d for d in all_docs if d.created_at and d.created_at >= window_30d]
    recent_bytes = sum(_effective_bytes(d) for d in recent_docs)
    daily_growth_bytes = recent_bytes / 30 if recent_docs else 0

    # Planned deletions within 30d and 90d windows
    deletions_30d = sum(
        _effective_bytes(d)
        for d in all_docs
        if d.expires_at and d.expires_at <= now + timedelta(days=30)
    )
    deletions_90d = sum(
        _effective_bytes(d)
        for d in all_docs
        if d.expires_at and d.expires_at <= now + timedelta(days=90)
    )

    projected_30d = max(0, current_bytes + daily_growth_bytes * 30 - deletions_30d)
    projected_90d = max(0, current_bytes + daily_growth_bytes * 90 - deletions_90d)

    # Historical snapshots for the chart (last 90 days)
    snapshots = (
        await db.execute(
            select(StorageSnapshot)
            .where(
                StorageSnapshot.user_id == user_uuid,
                StorageSnapshot.org_id.is_(None),
                StorageSnapshot.snapshot_at >= now - timedelta(days=90),
            )
            .order_by(StorageSnapshot.snapshot_at)
        )
    ).scalars().all()

    return {
        "current_bytes": current_bytes,
        "current_mb": round(current_bytes / _BYTES_PER_MB, 2),
        "projected_30d_bytes": int(projected_30d),
        "projected_30d_mb": round(projected_30d / _BYTES_PER_MB, 2),
        "projected_90d_bytes": int(projected_90d),
        "projected_90d_mb": round(projected_90d / _BYTES_PER_MB, 2),
        "daily_growth_bytes": int(daily_growth_bytes),
        "daily_growth_mb": round(daily_growth_bytes / _BYTES_PER_MB, 4),
        "planned_deletions_30d_bytes": deletions_30d,
        "planned_deletions_90d_bytes": deletions_90d,
        "history": [
            {
                "snapshot_at": s.snapshot_at.isoformat(),
                "total_bytes": s.total_bytes,
                "total_mb": round(s.total_bytes / _BYTES_PER_MB, 2),
                "document_count": s.document_count,
            }
            for s in snapshots
        ],
    }


# ── PATCH /api/documents/{id}/retention ──────────────────────────────────────

class RetentionUpdate(BaseModel):
    retention_policy: str
    lifecycle_state: Optional[str] = None


@router.patch("/api/documents/{document_id}/retention")
async def update_retention(
    document_id: uuid.UUID,
    body: RetentionUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:write")),
):
    """Update a document's retention policy and optionally its lifecycle state."""
    if body.retention_policy not in RETENTION_POLICIES:
        raise HTTPException(
            status_code=422,
            detail=f"retention_policy must be one of {list(RETENTION_POLICIES)}",
        )
    from app.models.document import LIFECYCLE_STATES
    if body.lifecycle_state and body.lifecycle_state not in LIFECYCLE_STATES:
        raise HTTPException(
            status_code=422,
            detail=f"lifecycle_state must be one of {list(LIFECYCLE_STATES)}",
        )

    doc = (
        await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == uuid.UUID(user["user_id"]),
            )
        )
    ).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.retention_policy = body.retention_policy
    doc.expires_at = compute_expires_at(doc.created_at, body.retention_policy)

    if body.lifecycle_state:
        doc.lifecycle_state = body.lifecycle_state

    await db.commit()
    return {
        "id": str(doc.id),
        "retention_policy": doc.retention_policy,
        "lifecycle_state": doc.lifecycle_state,
        "expires_at": doc.expires_at.isoformat() if doc.expires_at else None,
    }
