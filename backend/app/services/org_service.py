import re
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org import OrgMembership, Organization, role_gte


def _slugify(name: str) -> str:
    """Convert name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:100] or "org"


async def get_membership(
    db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[OrgMembership]:
    result = await db.execute(
        select(OrgMembership).where(
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def require_role(
    db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, minimum_role: str
) -> OrgMembership:
    """Raise 403 if user doesn't have at least minimum_role in the org."""
    member = await get_membership(db, org_id, user_id)
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    if not role_gte(member.role, minimum_role):
        raise HTTPException(
            status_code=403,
            detail=f"Requires {minimum_role} role or higher",
        )
    return member


async def ensure_not_last_owner(db: AsyncSession, org_id: uuid.UUID) -> None:
    """Raise 409 if the org currently has only one owner.

    Shared by both the role-downgrade and member-removal paths — an org
    losing its last owner would become permanently unmanageable.
    """
    owner_count_result = await db.execute(
        select(func.count()).select_from(OrgMembership).where(
            OrgMembership.org_id == org_id, OrgMembership.role == "owner"
        )
    )
    if (owner_count_result.scalar() or 0) <= 1:
        raise HTTPException(
            status_code=409, detail="Cannot remove the last owner from the organization"
        )


async def ensure_unique_slug(db: AsyncSession, slug: str, exclude_id: Optional[uuid.UUID] = None) -> str:
    """Ensure slug is unique, appending a counter if needed."""
    base = slug
    attempt = 0
    while True:
        candidate = f"{base}-{attempt}" if attempt else base
        q = select(Organization).where(Organization.slug == candidate)
        if exclude_id:
            q = q.where(Organization.id != exclude_id)
        existing = (await db.execute(q)).scalar_one_or_none()
        if not existing:
            return candidate
        attempt += 1
        if attempt > 99:
            return f"{base}-{uuid.uuid4().hex[:6]}"
