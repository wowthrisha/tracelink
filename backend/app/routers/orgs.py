import hashlib
import hmac
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.org import ORG_ROLES, OrgMembership, Organization, role_gte
from app.services.org_service import (
    _slugify,
    ensure_unique_slug,
    get_membership,
    require_role,
)

try:
    import dns.resolver as _dns_resolver
    _DNS_AVAILABLE = True
except ImportError:
    _dns_resolver = None  # type: ignore[assignment]
    _DNS_AVAILABLE = False

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


def _domain_verify_token(org_id: str) -> str:
    h = hmac.new(
        settings.domain_verify_salt.encode(),
        org_id.encode(),
        hashlib.sha256,
    ).hexdigest()[:32]
    return f"securedoc-verify={h}"

router = APIRouter(prefix="/api/orgs", tags=["organizations"])


def _org_response(org: Organization, member_count: int = 0, my_role: Optional[str] = None) -> dict:
    d = {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "saml_domain": org.saml_domain,
        "custom_domain": org.custom_domain,
        "custom_domain_verified": org.custom_domain_verified,
        "custom_domain_verified_at": (
            org.custom_domain_verified_at.isoformat() if org.custom_domain_verified_at else None
        ),
        "is_active": org.is_active,
        "member_count": member_count,
        "created_at": org.created_at.isoformat() if org.created_at else None,
    }
    if my_role is not None:
        d["my_role"] = my_role
    return d


def _member_response(m: OrgMembership) -> dict:
    return {
        "id": str(m.id),
        "user_id": str(m.user_id),
        "role": m.role,
        "invited_by_user_id": str(m.invited_by_user_id) if m.invited_by_user_id else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.post("", status_code=201)
async def create_org(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    name = body.get("name", "").strip()
    if not name or len(name) > 200:
        raise HTTPException(status_code=422, detail="name must be 1–200 characters")

    slug = body.get("slug") or _slugify(name)
    slug = await ensure_unique_slug(db, slug)

    saml_domain = body.get("saml_domain")

    org = Organization(name=name, slug=slug, saml_domain=saml_domain)
    db.add(org)
    await db.flush()

    # Creator becomes owner
    membership = OrgMembership(
        org_id=org.id,
        user_id=uuid.UUID(user["user_id"]),
        role="owner",
    )
    db.add(membership)

    from app.services.audit_service import log_audit_event
    await log_audit_event(
        db, actor_user_id=user["user_id"], event_type="org.created",
        org_id=str(org.id), target_type="org", target_id=str(org.id),
        details={"name": name, "slug": slug},
    )
    await db.commit()
    await db.refresh(org)

    return _org_response(org, member_count=1, my_role="owner")


@router.get("")
async def list_orgs(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_uuid = uuid.UUID(user["user_id"])
    result = await db.execute(
        select(OrgMembership, Organization)
        .join(Organization, OrgMembership.org_id == Organization.id)
        .where(OrgMembership.user_id == user_uuid)
        .order_by(Organization.name)
    )
    rows = result.all()
    orgs = []
    for membership, org in rows:
        count_result = await db.execute(
            select(func.count()).select_from(OrgMembership).where(
                OrgMembership.org_id == org.id
            )
        )
        count = count_result.scalar() or 0
        orgs.append(_org_response(org, member_count=count, my_role=membership.role))
    return {"organizations": orgs}


@router.get("/{org_id}")
async def get_org(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    org, member = await _get_org_and_member(org_id, user, db, minimum_role="viewer")
    count_result = await db.execute(
        select(func.count()).select_from(OrgMembership).where(
            OrgMembership.org_id == org.id
        )
    )
    count = count_result.scalar() or 0
    return _org_response(org, member_count=count, my_role=member.role)


@router.patch("/{org_id}")
async def update_org(
    org_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    org, _ = await _get_org_and_member(org_id, user, db, minimum_role="owner")

    if "name" in body:
        name = body["name"].strip()
        if not name or len(name) > 200:
            raise HTTPException(status_code=422, detail="name must be 1–200 characters")
        org.name = name

    if "slug" in body:
        new_slug = body["slug"].strip()
        if not new_slug or len(new_slug) > 100:
            raise HTTPException(status_code=422, detail="slug must be 1–100 characters")
        if not new_slug.replace("-", "").replace("_", "").isalnum():
            raise HTTPException(status_code=422, detail="slug must be URL-safe")
        new_slug = await ensure_unique_slug(db, new_slug, exclude_id=org.id)
        org.slug = new_slug

    if "saml_domain" in body:
        org.saml_domain = body["saml_domain"]

    if "custom_domain" in body:
        raw_domain = (body["custom_domain"] or "").strip().lower() or None
        if raw_domain is not None and not _DOMAIN_RE.match(raw_domain):
            raise HTTPException(status_code=422, detail="custom_domain must be a valid hostname (e.g. docs.acme.com)")
        if raw_domain != org.custom_domain:
            org.custom_domain = raw_domain
            org.custom_domain_verified = False
            org.custom_domain_verified_at = None

    org.updated_at = datetime.now(timezone.utc)
    from app.services.audit_service import log_audit_event
    await log_audit_event(
        db, actor_user_id=user["user_id"], event_type="org.updated",
        org_id=str(org.id), target_type="org", target_id=str(org.id),
        details=body,
    )
    await db.commit()
    await db.refresh(org)
    return _org_response(org)


@router.delete("/{org_id}", status_code=204)
async def delete_org(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    org, _ = await _get_org_and_member(org_id, user, db, minimum_role="owner")
    from app.services.audit_service import log_audit_event
    await log_audit_event(
        db, actor_user_id=user["user_id"], event_type="org.deleted",
        org_id=org_id, target_type="org", target_id=org_id,
        details={"name": org.name},
    )
    await db.delete(org)
    await db.commit()


@router.get("/{org_id}/members")
async def list_members(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _, _ = await _get_org_and_member(org_id, user, db, minimum_role="viewer")
    org_uuid = uuid.UUID(org_id)

    result = await db.execute(
        select(OrgMembership)
        .where(OrgMembership.org_id == org_uuid)
        .order_by(OrgMembership.created_at)
    )
    return {"members": [_member_response(m) for m in result.scalars().all()]}


@router.post("/{org_id}/members", status_code=201)
async def add_member(
    org_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    org, actor = await _get_org_and_member(org_id, user, db, minimum_role="admin")
    org_uuid = uuid.UUID(org_id)

    target_user_id_raw = body.get("user_id", "").strip()
    try:
        target_uuid = uuid.UUID(target_user_id_raw)
    except ValueError:
        raise HTTPException(status_code=422, detail="user_id must be a valid UUID")

    role = body.get("role", "viewer")
    if role not in ORG_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role. Allowed: {ORG_ROLES}",
        )
    # Cannot grant a role higher than the actor's own role
    if not role_gte(actor.role, role):
        raise HTTPException(status_code=403, detail="Cannot grant a role higher than your own")

    # Check if already a member
    existing = await get_membership(db, org_uuid, target_uuid)
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")

    membership = OrgMembership(
        org_id=org_uuid,
        user_id=target_uuid,
        role=role,
        invited_by_user_id=uuid.UUID(user["user_id"]),
    )
    db.add(membership)
    from app.services.audit_service import log_audit_event
    await log_audit_event(
        db, actor_user_id=user["user_id"], event_type="member.added",
        org_id=org_id, target_type="member", target_id=str(target_uuid),
        details={"role": role},
    )
    await db.commit()
    await db.refresh(membership)
    return _member_response(membership)


@router.patch("/{org_id}/members/{target_user_id}")
async def update_member_role(
    org_id: str,
    target_user_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    org, actor = await _get_org_and_member(org_id, user, db, minimum_role="admin")
    org_uuid = uuid.UUID(org_id)

    try:
        target_uuid = uuid.UUID(target_user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Member not found")

    target = await get_membership(db, org_uuid, target_uuid)
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    # Cannot modify a member with equal or higher role (except owner modifying anyone)
    if actor.role != "owner" and not role_gte(actor.role, target.role):
        raise HTTPException(status_code=403, detail="Cannot modify a member with a higher role")

    new_role = body.get("role")
    if new_role is None:
        raise HTTPException(status_code=422, detail="role is required")
    if new_role not in ORG_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Allowed: {ORG_ROLES}")
    if not role_gte(actor.role, new_role):
        raise HTTPException(status_code=403, detail="Cannot grant a role higher than your own")

    # Prevent downgrading the only owner
    if target.role == "owner" and new_role != "owner":
        owner_count_result = await db.execute(
            select(func.count()).select_from(OrgMembership).where(
                OrgMembership.org_id == org_uuid, OrgMembership.role == "owner"
            )
        )
        if (owner_count_result.scalar() or 0) <= 1:
            raise HTTPException(
                status_code=409, detail="Cannot remove the last owner from the organization"
            )

    old_role = target.role
    target.role = new_role
    await db.commit()
    await db.refresh(target)

    # Audit log: member.role_changed
    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="member.role_changed",
            actor_user_id=user["user_id"],
            org_id=str(org_uuid),
            target_type="member",
            target_id=str(target_uuid),
            details={"old_role": old_role, "new_role": new_role},
        )
    except Exception:
        pass

    return _member_response(target)


@router.delete("/{org_id}/members/{target_user_id}", status_code=204)
async def remove_member(
    org_id: str,
    target_user_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    org, actor = await _get_org_and_member(org_id, user, db, minimum_role="admin")
    org_uuid = uuid.UUID(org_id)

    try:
        target_uuid = uuid.UUID(target_user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Member not found")

    # Allow self-removal (leave org) at any role
    is_self = target_uuid == uuid.UUID(user["user_id"])

    target = await get_membership(db, org_uuid, target_uuid)
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    if not is_self:
        if actor.role != "owner" and not role_gte(actor.role, target.role):
            raise HTTPException(
                status_code=403, detail="Cannot remove a member with a higher role"
            )

    # Prevent removing the last owner
    if target.role == "owner":
        owner_count_result = await db.execute(
            select(func.count()).select_from(OrgMembership).where(
                OrgMembership.org_id == org_uuid, OrgMembership.role == "owner"
            )
        )
        if (owner_count_result.scalar() or 0) <= 1:
            raise HTTPException(
                status_code=409, detail="Cannot remove the last owner from the organization"
            )

    removed_role = target.role
    await db.delete(target)
    await db.commit()

    # Audit log: member.removed
    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="member.removed",
            actor_user_id=user["user_id"],
            org_id=str(org_uuid),
            target_type="member",
            target_id=str(target_uuid),
            details={"removed_role": removed_role, "self_removal": is_self},
        )
    except Exception:
        pass


@router.get("/{org_id}/domain/token")
async def get_domain_verify_token(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return the TXT record value the admin must add to verify custom domain ownership."""
    org, _ = await _get_org_and_member(org_id, user, db, minimum_role="admin")
    if not org.custom_domain:
        raise HTTPException(status_code=422, detail="No custom_domain set on this organization")
    token = _domain_verify_token(str(org.id))
    return {"domain": org.custom_domain, "txt_record": token, "verified": org.custom_domain_verified}


@router.post("/{org_id}/domain/verify")
async def verify_custom_domain(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Check that the org's custom_domain has the required DNS TXT record and mark it verified.

    The caller must have added a TXT record like:
        @ IN TXT "securedoc-verify=<token>"
    where <token> comes from GET /{id}/domain/token.
    """
    org, _ = await _get_org_and_member(org_id, user, db, minimum_role="admin")
    if not org.custom_domain:
        raise HTTPException(status_code=422, detail="No custom_domain set on this organization")

    import asyncio
    expected = _domain_verify_token(str(org.id))
    found = False
    error_detail = ""

    if not _DNS_AVAILABLE:
        error_detail = "DNS library not available; cannot verify automatically"
    else:
        try:
            loop = asyncio.get_event_loop()
            resolver = _dns_resolver.Resolver()
            resolver.lifetime = 5.0
            _domain = org.custom_domain

            def _lookup():
                answers = resolver.resolve(_domain, "TXT")
                for rdata in answers:
                    for txt_string in rdata.strings:
                        val = txt_string.decode("utf-8") if isinstance(txt_string, bytes) else txt_string
                        if val == expected:
                            return True
                return False

            found = await loop.run_in_executor(None, _lookup)
        except Exception as exc:
            error_detail = f"DNS lookup failed: {exc}"

    if not found:
        return {
            "verified": False,
            "domain": org.custom_domain,
            "expected_txt": expected,
            "error": error_detail or f"TXT record '{expected}' not found on {org.custom_domain}",
        }

    org.custom_domain_verified = True
    org.custom_domain_verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(org)
    return {"verified": True, "domain": org.custom_domain}


async def _get_org_and_member(
    org_id: str, user: dict, db: AsyncSession, minimum_role: str
) -> tuple[Organization, OrgMembership]:
    try:
        org_uuid = uuid.UUID(org_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_result = await db.execute(
        select(Organization).where(Organization.id == org_uuid)
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    member = await require_role(db, org_uuid, uuid.UUID(user["user_id"]), minimum_role)
    return org, member
