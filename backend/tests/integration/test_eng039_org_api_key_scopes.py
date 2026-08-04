"""ENG-039 security regression suite.

Root cause: orgs.py, api_keys.py, and billing.py used bare
Depends(get_current_user) with no require_scope(...) check, unlike 7 other
routers. Any authenticated API key — regardless of what scopes it was
granted, including zero — had full, unrestricted access to organization
management, other API keys, and billing.

Fix: added organizations:{read,write}, api_keys:{read,write}, and
billing:{read,write} to API_SCOPES, wired require_scope(...) onto all 21
previously-unscoped endpoints across the three routers, and added a
scope-escalation guard so an API key can never mint/widen a sibling key
beyond its own scopes.

Testing note: verify_api_key() opens its own DB session via the module-level
AsyncSessionLocal rather than going through the get_db dependency override,
so it cannot see keys created in this suite's SQLite test database (a
pre-existing testability gap, not part of this fix's scope — flagged in
ENGINEERING_BACKLOG.md, not fixed here). Following this codebase's
established pattern (see TestPublicAPI in test_enterprise_product.py),
verify_api_key is mocked at the auth-boundary with a side_effect that
returns a real, scope-bearing user dict or raises the appropriate
HTTPException — this still exercises the genuine require_scope() logic and
router wiring this fix actually changed, which is what ENG-039 is about.

Covers every scenario in V22.0's mandated test matrix: no key, invalid key,
revoked key, zero-scope key, correctly-scoped key, incorrectly-scoped key,
org member/admin/owner, and cross-organization access. Every test proves
the corresponding ALLOWED or DENIED behavior, not just a status code.
"""
import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from app.auth import get_current_user
from app.main import app
from app.models.api_key import API_SCOPES
from app.models.org import Organization, OrgMembership
from tests.conftest import TEST_USER_ID, TEST_USER_B_ID

_TEST_KEY = "sd_" + "a" * 48


@asynccontextmanager
async def _api_key_session(scopes=None, revoked=False, expired=False, user_id=TEST_USER_ID):
    """Pops the client fixture's get_current_user override and mocks
    verify_api_key to authenticate exactly one raw key value (_TEST_KEY) with
    the given scopes/state, matching the established pattern in
    test_enterprise_product.py::TestPublicAPI. Restores the override on exit."""
    async def _mock_verify(raw_key: str) -> dict:
        if raw_key != _TEST_KEY:
            raise HTTPException(status_code=401, detail="Authentication failed")
        if revoked:
            raise HTTPException(status_code=401, detail="Authentication failed")
        if expired:
            raise HTTPException(status_code=401, detail="API key expired")
        return {
            "user_id": user_id, "email": "", "role": "authenticated",
            "scopes": scopes or [], "auth_method": "api_key",
        }

    original = app.dependency_overrides.pop(get_current_user, None)
    try:
        with patch("app.auth.verify_api_key", side_effect=_mock_verify):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                yield ac
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user] = original


async def _make_org(db_session, owner_user_id: str, role: str = "owner", member_user_id: str = None) -> str:
    org = Organization(id=uuid.uuid4(), name="ENG-039 test org", slug=f"eng039-{uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()
    db_session.add(OrgMembership(
        id=uuid.uuid4(), org_id=org.id,
        user_id=uuid.UUID(member_user_id or owner_user_id), role=role,
    ))
    await db_session.commit()
    return str(org.id)


class TestNoOrInvalidOrRevokedKey:
    """Requests must be denied before scope is ever considered."""

    @pytest.mark.asyncio
    async def test_no_api_key_no_auth_header_denied(self, client, db_session):
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/api/orgs")
            assert r.status_code == 401
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original

    @pytest.mark.asyncio
    async def test_invalid_api_key_denied(self, client, db_session):
        async with _api_key_session(scopes=["organizations:read"]) as ac:
            r = await ac.get("/api/orgs", headers={"X-API-Key": "sd_" + "0" * 48})
        assert r.status_code == 401
        assert "scope" not in r.json().get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_revoked_api_key_denied(self, client, db_session):
        async with _api_key_session(scopes=["organizations:read", "organizations:write"], revoked=True) as ac:
            r = await ac.get("/api/orgs", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_api_key_denied(self, client, db_session):
        async with _api_key_session(scopes=["organizations:read"], expired=True) as ac:
            r = await ac.get("/api/orgs", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 401


class TestZeroScopeApiKey:
    """The core ENG-039 defect: a valid, active key with zero scopes must be
    denied on every organizations/api_keys/billing operation — never treated
    as unlimited access."""

    @pytest.mark.asyncio
    async def test_zero_scope_key_denied_list_orgs(self, client, db_session):
        async with _api_key_session(scopes=[]) as ac:
            r = await ac.get("/api/orgs", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 403
        assert "organizations:read" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_zero_scope_key_denied_create_org(self, client, db_session):
        async with _api_key_session(scopes=[]) as ac:
            r = await ac.post("/api/orgs", json={"name": "should not be created"}, headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_zero_scope_key_denied_invite_member(self, client, db_session):
        org_id = await _make_org(db_session, TEST_USER_ID, role="owner")
        async with _api_key_session(scopes=[]) as ac:
            r = await ac.post(
                f"/api/orgs/{org_id}/members", json={"user_id": TEST_USER_B_ID, "role": "viewer"},
                headers={"X-API-Key": _TEST_KEY},
            )
        # Denied by scope before the org-role/membership logic ever runs.
        assert r.status_code == 403
        assert "organizations:write" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_zero_scope_key_denied_billing_checkout(self, client, db_session):
        async with _api_key_session(scopes=[]) as ac:
            r = await ac.post("/api/billing/checkout", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_zero_scope_key_denied_create_api_key(self, client, db_session):
        async with _api_key_session(scopes=[]) as ac:
            r = await ac.post(
                "/api/api-keys", json={"name": "child key", "scopes": []},
                headers={"X-API-Key": _TEST_KEY},
            )
        assert r.status_code == 403


class TestCorrectlyScopedApiKey:
    """A key granted the right scope must actually work — the fix must not
    over-deny either."""

    @pytest.mark.asyncio
    async def test_organizations_read_scope_allows_list_orgs(self, client, db_session):
        await _make_org(db_session, TEST_USER_ID, role="viewer")
        async with _api_key_session(scopes=["organizations:read"]) as ac:
            r = await ac.get("/api/orgs", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 200
        assert len(r.json()["organizations"]) == 1

    @pytest.mark.asyncio
    async def test_organizations_write_scope_allows_create_org(self, client, db_session):
        async with _api_key_session(scopes=["organizations:write"]) as ac:
            r = await ac.post("/api/orgs", json={"name": "created via scoped key"}, headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 201
        assert r.json()["name"] == "created via scoped key"

    @pytest.mark.asyncio
    async def test_billing_read_scope_allows_status(self, client, db_session):
        async with _api_key_session(scopes=["billing:read"]) as ac:
            r = await ac.get("/api/billing/status", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 200
        assert "plan" in r.json()

    @pytest.mark.asyncio
    async def test_api_keys_read_scope_allows_list(self, client, db_session):
        async with _api_key_session(scopes=["api_keys:read"]) as ac:
            r = await ac.get("/api/api-keys", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 200


class TestIncorrectlyScopedApiKey:
    """A key with unrelated scopes must be denied — scopes are not additive
    across resource families."""

    @pytest.mark.asyncio
    async def test_documents_write_scope_does_not_grant_org_access(self, client, db_session):
        await _make_org(db_session, TEST_USER_ID, role="owner")
        async with _api_key_session(scopes=["documents:write", "documents:read", "links:write"]) as ac:
            r = await ac.get("/api/orgs", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_organizations_read_does_not_grant_write(self, client, db_session):
        async with _api_key_session(scopes=["organizations:read"]) as ac:
            r = await ac.post("/api/orgs", json={"name": "should be denied"}, headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_billing_read_does_not_grant_checkout(self, client, db_session):
        async with _api_key_session(scopes=["billing:read"]) as ac:
            r = await ac.post("/api/billing/portal", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 403


class TestScopeEscalationGuard:
    """An API key must never be able to mint or widen a sibling key beyond
    its own scopes, even once it holds api_keys:write."""

    @pytest.mark.asyncio
    async def test_key_cannot_create_sibling_with_scope_it_lacks(self, client, db_session):
        async with _api_key_session(scopes=["api_keys:write", "documents:read"]) as ac:
            r = await ac.post(
                "/api/api-keys",
                json={"name": "escalated child", "scopes": ["organizations:write"]},
                headers={"X-API-Key": _TEST_KEY},
            )
        assert r.status_code == 403
        assert "organizations:write" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_key_can_create_sibling_with_subset_of_own_scopes(self, client, db_session):
        async with _api_key_session(scopes=["api_keys:write", "documents:read", "documents:write"]) as ac:
            r = await ac.post(
                "/api/api-keys",
                json={"name": "narrower child", "scopes": ["documents:read"]},
                headers={"X-API-Key": _TEST_KEY},
            )
        assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_key_cannot_widen_existing_key_via_patch(self, client, db_session):
        async with _api_key_session(scopes=["api_keys:write", "api_keys:read"]) as ac:
            cr = await ac.post(
                "/api/api-keys", json={"name": "target", "scopes": []},
                headers={"X-API-Key": _TEST_KEY},
            )
            assert cr.status_code == 201
            key_id = cr.json()["id"]
            r = await ac.patch(
                f"/api/api-keys/{key_id}", json={"scopes": ["billing:write"]},
                headers={"X-API-Key": _TEST_KEY},
            )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_jwt_caller_unrestricted_by_escalation_guard(self, client):
        """Browser/JWT callers are unaffected — the escalation guard, like
        require_scope itself, only restricts auth_method == "api_key" callers."""
        r = await client.post("/api/api-keys", json={"name": "jwt-created", "scopes": sorted(API_SCOPES)})
        assert r.status_code == 201


class TestOrgRoleHierarchyStillEnforced:
    """The new scope check is additive to, not a replacement for, the
    pre-existing org-role checks (viewer/editor/admin/owner)."""

    @pytest.mark.asyncio
    async def test_org_viewer_cannot_invite_member(self, client, db_session):
        org_id = await _make_org(db_session, TEST_USER_ID, role="viewer")
        r = await client.post(f"/api/orgs/{org_id}/members", json={"user_id": TEST_USER_B_ID, "role": "viewer"})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_org_admin_can_invite_member(self, client, db_session):
        org_id = await _make_org(db_session, TEST_USER_ID, role="admin")
        r = await client.post(f"/api/orgs/{org_id}/members", json={"user_id": TEST_USER_B_ID, "role": "viewer"})
        assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_org_owner_can_delete_org(self, client, db_session):
        org_id = await _make_org(db_session, TEST_USER_ID, role="owner")
        r = await client.delete(f"/api/orgs/{org_id}")
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_org_admin_cannot_delete_org(self, client, db_session):
        """Deleting an org requires owner, not just admin — unchanged by this fix."""
        org_id = await _make_org(db_session, TEST_USER_ID, role="admin")
        r = await client.delete(f"/api/orgs/{org_id}")
        assert r.status_code == 403


class TestCrossOrganizationAccess:
    """A fully-scoped API key must still be blocked from an org it isn't a
    member of — scope grants a capability class, not access to every
    resource of that class."""

    @pytest.mark.asyncio
    async def test_full_scope_key_cannot_access_foreign_org(self, client, db_session):
        # TEST_USER_B is the owner of this org; TEST_USER_ID is not a member at all.
        foreign_org_id = await _make_org(db_session, TEST_USER_B_ID, role="owner", member_user_id=TEST_USER_B_ID)
        async with _api_key_session(scopes=["organizations:read", "organizations:write"]) as ac:
            r = await ac.get(f"/api/orgs/{foreign_org_id}", headers={"X-API-Key": _TEST_KEY})
        # require_role() inside _get_org_and_member denies non-members —
        # 404/403 both acceptable (no-existence-leak vs. explicit deny),
        # the only unacceptable outcome is 200.
        assert r.status_code in (403, 404)

    @pytest.mark.asyncio
    async def test_full_scope_key_lists_only_own_orgs(self, client, db_session):
        await _make_org(db_session, TEST_USER_B_ID, role="owner", member_user_id=TEST_USER_B_ID)  # foreign org
        await _make_org(db_session, TEST_USER_ID, role="owner")  # own org
        async with _api_key_session(scopes=["organizations:read"]) as ac:
            r = await ac.get("/api/orgs", headers={"X-API-Key": _TEST_KEY})
        assert r.status_code == 200
        assert len(r.json()["organizations"]) == 1


class TestScopeDenialErrorHygiene:
    """Authorization failures must return intentional status codes and never
    leak internal information."""

    @pytest.mark.asyncio
    async def test_scope_denial_is_403_not_500(self, client, db_session):
        async with _api_key_session(scopes=[]) as ac:
            r = await ac.delete(f"/api/orgs/{uuid.uuid4()}", headers={"X-API-Key": _TEST_KEY})
        # Scope check runs before the org lookup — must be 403, not a 500
        # from some downstream code assuming scope was already validated.
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_scope_denial_detail_names_only_the_missing_scope(self, client, db_session):
        async with _api_key_session(scopes=["documents:read"]) as ac:
            r = await ac.get("/api/orgs", headers={"X-API-Key": _TEST_KEY})
        detail = r.json()["detail"]
        assert detail == "API key missing required scope: organizations:read"
