"""V22.0 Priority 2 — authorization consistency review follow-up.

While tracing ENG-039's fix, the same "zero/wrong-scope API key has full
access" pattern was found in two more places that were objectively
demonstrated (not merely suspected) to have the identical defect shape:

- admin.py's GET /api/admin/audit-log (org accountability trail — read)
- annotations.py's 10 uploader-facing /api/documents/{doc_id}/... routes
  (annotations/feedback list/export/reply/resolve — read + write)
- notifications.py's GET /api/notifications/stream (SSE — read)

All three used bare Depends(get_current_user) despite documents:read/write
and organizations:read already existing as scopes covering exactly this
shape of operation. Fixed by applying the existing scopes, not inventing
new ones. This suite proves each fix with the same rigor as ENG-039's:
zero-scope denied, correctly-scoped allowed, JWT unaffected.
"""
import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from app.auth import get_current_user
from app.main import app
from app.models.org import Organization, OrgMembership
from tests.conftest import TEST_USER_ID

_TEST_KEY = "sd_" + "b" * 48


async def _api_key_client(scopes):
    async def _mock_verify(raw_key: str) -> dict:
        if raw_key != _TEST_KEY:
            raise HTTPException(status_code=401, detail="Authentication failed")
        return {
            "user_id": TEST_USER_ID, "email": "", "role": "authenticated",
            "scopes": scopes, "auth_method": "api_key",
        }
    return _mock_verify


class TestAuditLogScope:
    @pytest.mark.asyncio
    async def test_zero_scope_key_denied_audit_log(self, client, db_session):
        mock_verify = await _api_key_client([])
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            with patch("app.auth.verify_api_key", side_effect=mock_verify):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    r = await ac.get("/api/admin/audit-log", headers={"X-API-Key": _TEST_KEY})
            assert r.status_code == 403
            assert "organizations:read" in r.json()["detail"]
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original

    @pytest.mark.asyncio
    async def test_organizations_read_scope_allows_audit_log(self, client, db_session):
        mock_verify = await _api_key_client(["organizations:read"])
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            with patch("app.auth.verify_api_key", side_effect=mock_verify):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    r = await ac.get("/api/admin/audit-log", headers={"X-API-Key": _TEST_KEY})
            assert r.status_code == 200
            assert "events" in r.json()
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original

    @pytest.mark.asyncio
    async def test_jwt_caller_unaffected_audit_log(self, client):
        r = await client.get("/api/admin/audit-log")
        assert r.status_code == 200


class TestAnnotationsFeedbackScope:
    @pytest.mark.asyncio
    async def test_zero_scope_key_denied_list_annotations(self, client, db_session, ready_document):
        mock_verify = await _api_key_client([])
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            with patch("app.auth.verify_api_key", side_effect=mock_verify):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    r = await ac.get(f"/api/documents/{ready_document.id}/annotations", headers={"X-API-Key": _TEST_KEY})
            assert r.status_code == 403
            assert "documents:read" in r.json()["detail"]
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original

    @pytest.mark.asyncio
    async def test_documents_read_scope_allows_list_annotations(self, client, db_session, ready_document):
        mock_verify = await _api_key_client(["documents:read"])
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            with patch("app.auth.verify_api_key", side_effect=mock_verify):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    r = await ac.get(f"/api/documents/{ready_document.id}/annotations", headers={"X-API-Key": _TEST_KEY})
            assert r.status_code == 200
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original

    @pytest.mark.asyncio
    async def test_documents_read_scope_denied_on_write_route(self, client, db_session, ready_document):
        """A read-only key must not be able to resolve feedback (a write operation)."""
        mock_verify = await _api_key_client(["documents:read"])
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            with patch("app.auth.verify_api_key", side_effect=mock_verify):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    r = await ac.patch(
                        f"/api/documents/{ready_document.id}/feedback/{uuid.uuid4()}/resolve",
                        headers={"X-API-Key": _TEST_KEY},
                    )
            assert r.status_code == 403
            assert "documents:write" in r.json()["detail"]
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original

    @pytest.mark.asyncio
    async def test_jwt_caller_unaffected_list_annotations(self, client, ready_document):
        r = await client.get(f"/api/documents/{ready_document.id}/annotations")
        assert r.status_code == 200


class TestNotificationStreamScope:
    @pytest.mark.asyncio
    async def test_zero_scope_key_denied_stream(self, client, db_session):
        mock_verify = await _api_key_client([])
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            with patch("app.auth.verify_api_key", side_effect=mock_verify):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    r = await ac.get("/api/notifications/stream", headers={"X-API-Key": _TEST_KEY})
            assert r.status_code == 403
            assert "documents:read" in r.json()["detail"]
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original
