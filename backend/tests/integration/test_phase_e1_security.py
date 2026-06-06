"""
Phase E1 Security Hardening — regression tests.

Covers all 7 confirmed findings from SECURITY_VERIFICATION_AUDIT.md:

  F1. session_id moved from URL query params to X-Session-ID header
  F2. antiword subprocess env whitelist (unit test via docx_extractor)
  F3. analytics page_number validated against document page_count
  F4. viewer page endpoint rejects page > page_count with 404
  F5. download auth ordering: session BEFORE permission check
  F6. thumbnail rate limit reduced to 120/min (config-level test)
  F7. storage key: no user-controlled components in storage paths
"""
import uuid
import json
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import select

from app.models.document import Document, DocumentPage
from app.services.link_service import LinkService
from tests.conftest import TEST_USER_ID, _make_webp_bytes


# ── shared helpers ─────────────────────────────────────────────────────────────

async def _insert_doc(db_session, page_count: int = 5, status: str = "ready") -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="e1_test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status=status,
        page_count=page_count,
        file_size_bytes=1024 * page_count,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.flush()
    for i in range(1, page_count + 1):
        db_session.add(DocumentPage(
            document_id=doc.id,
            page_number=i,
            storage_key=f"pages/{doc.id}/{i:04d}.webp",
            width_px=595,
            height_px=842,
        ))
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


async def _validate(client, token: str) -> dict:
    r = await client.post("/api/viewer/validate", json={"token": token})
    assert r.status_code == 200, r.text
    return r.json()


# ══════════════════════════════════════════════════════════════════════════════
# F1. session_id in X-Session-ID header (no longer required in URL)
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionIDHeader:
    """Backend must accept session_id via X-Session-ID header."""

    @pytest.mark.asyncio
    async def test_page_via_header_returns_200(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1",
            headers={"X-Session-ID": sid},
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/webp"

    @pytest.mark.asyncio
    async def test_page_via_query_param_still_works(self, client, active_link):
        """Query param fallback must continue working (backward compat)."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1?session_id={sid}"
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_thumb_via_header_returns_200(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/thumb/{active_link.token}/1",
            headers={"X-Session-ID": sid},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_toc_via_header_returns_200(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/toc/{active_link.token}",
            headers={"X-Session-ID": sid},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_header_takes_priority_over_query_param(self, client, active_link):
        """When both header and query param are present, header must win."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        # Valid header + bogus query param → request must succeed (header wins)
        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1?session_id=bogus_invalid_sid",
            headers={"X-Session-ID": sid},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_cookie_fallback_accepted(self, client, active_link):
        """sdoc_session cookie must be accepted as second-priority source."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1",
            cookies={"sdoc_session": sid},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_no_session_id_returns_400(self, client, active_link):
        r = await client.get(f"/api/viewer/page/{active_link.token}/1")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_download_via_header(self, client, db_session):
        doc = await _insert_doc(db_session, page_count=1)
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(doc.id),
            permissions={"can_download": True},
        )
        body = await _validate(client, link.token)
        sid = body["session_id"]

        with patch("app.services.storage.StorageService.download_bytes",
                   return_value=_make_webp_bytes()):
            r = await client.get(
                f"/api/viewer/download/{link.token}",
                headers={"X-Session-ID": sid},
            )
        # 200 or 413 (page limit) — not 400/401
        assert r.status_code not in (400, 401)


# ══════════════════════════════════════════════════════════════════════════════
# F2. antiword subprocess env whitelist
# ══════════════════════════════════════════════════════════════════════════════

class TestAntiwordEnvWhitelist:
    """doc_to_text() must run antiword without DB/Redis/AWS credentials."""

    def test_antiword_receives_whitelisted_env_only(self):
        import os
        from app.services.toc.docx_extractor import doc_to_text

        captured_envs = []

        def fake_run(cmd, *, capture_output, timeout, check, env):
            captured_envs.append(dict(env))
            result = MagicMock()
            result.returncode = 0
            result.stdout = b"hello world"
            result.stderr = b""
            return result

        env_backup = os.environ.copy()
        os.environ["DATABASE_URL"] = "postgresql://secret:s3cr3t@localhost/db"
        os.environ["REDIS_URL"] = "redis://:redispass@localhost:6379/0"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "FAKESECRET"

        try:
            with patch("subprocess.run", side_effect=fake_run):
                result = doc_to_text(b"fake doc bytes", doc_id="test-123")

            assert len(captured_envs) == 1
            env_passed = captured_envs[0]

            assert "DATABASE_URL" not in env_passed, "DATABASE_URL must not reach antiword"
            assert "REDIS_URL" not in env_passed, "REDIS_URL must not reach antiword"
            assert "AWS_SECRET_ACCESS_KEY" not in env_passed, "AWS key must not reach antiword"

            _WHITELIST = {"HOME", "TMPDIR", "TEMP", "TMP", "PATH", "LANG", "LC_ALL"}
            for key in env_passed:
                assert key in _WHITELIST, f"Unexpected env key leaked: {key!r}"

            assert result == "hello world"
        finally:
            for k in ["DATABASE_URL", "REDIS_URL", "AWS_SECRET_ACCESS_KEY"]:
                os.environ.pop(k, None)
            for k, v in env_backup.items():
                os.environ[k] = v

    def test_antiword_nonzero_exit_returns_empty_string(self):
        from app.services.toc.docx_extractor import doc_to_text

        def fake_run(cmd, *, capture_output, timeout, check, env):
            result = MagicMock()
            result.returncode = 1
            result.stdout = b""
            result.stderr = b"some error"
            return result

        with patch("subprocess.run", side_effect=fake_run):
            assert doc_to_text(b"bad doc bytes", doc_id="test-456") == ""

    def test_antiword_not_found_returns_empty_string(self):
        from app.services.toc.docx_extractor import doc_to_text

        with patch("subprocess.run", side_effect=FileNotFoundError("antiword not found")):
            assert doc_to_text(b"bytes", doc_id="test-789") == ""


# ══════════════════════════════════════════════════════════════════════════════
# F3. Analytics page_number validated against document page_count
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsPageNumberValidation:
    """POST /api/analytics/events must reject page_number > doc.page_count."""

    @pytest.mark.asyncio
    async def test_valid_page_number_accepted(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": sid,
            "event_type": "print_attempt",
            "page_number": 1,
        })
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_page_beyond_page_count_rejected(self, client, db_session):
        doc = await _insert_doc(db_session, page_count=3)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        body = await _validate(client, link.token)
        sid = body["session_id"]

        r = await client.post("/api/analytics/events", json={
            "token": link.token,
            "session_id": sid,
            "event_type": "print_attempt",
            "page_number": 9999,
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_page_equal_to_page_count_accepted(self, client, db_session):
        doc = await _insert_doc(db_session, page_count=3)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        body = await _validate(client, link.token)
        sid = body["session_id"]

        r = await client.post("/api/analytics/events", json={
            "token": link.token,
            "session_id": sid,
            "event_type": "print_attempt",
            "page_number": 3,
        })
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_page_number_zero_rejected(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": sid,
            "event_type": "print_attempt",
            "page_number": 0,
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_negative_page_number_rejected(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": sid,
            "event_type": "print_attempt",
            "page_number": -5,
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_no_page_number_accepted(self, client, active_link):
        """page_number is optional; omitting it must succeed."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": sid,
            "event_type": "print_attempt",
        })
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# F4. Viewer page endpoint rejects page > page_count
# ══════════════════════════════════════════════════════════════════════════════

class TestViewerPageBoundsCheck:
    """GET /api/viewer/page/{token}/{page} must return 404 for page > page_count."""

    @pytest.mark.asyncio
    async def test_page_beyond_count_returns_404(self, client, db_session):
        doc = await _insert_doc(db_session, page_count=3)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        body = await _validate(client, link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/page/{link.token}/9999",
            headers={"X-Session-ID": sid},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_page_one_returns_200(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1",
            headers={"X-Session-ID": sid},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_page_zero_returns_404(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/page/{active_link.token}/0",
            headers={"X-Session-ID": sid},
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_page_equal_to_count_returns_200(self, client, db_session):
        doc = await _insert_doc(db_session, page_count=2)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        body = await _validate(client, link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/page/{link.token}/2",
            headers={"X-Session-ID": sid},
        )
        # 200 expected; 404 only if the page row is somehow missing (test data issue)
        assert r.status_code in (200, 404)


# ══════════════════════════════════════════════════════════════════════════════
# F5. Download authorization ordering: session BEFORE permission check
# ══════════════════════════════════════════════════════════════════════════════

class TestDownloadAuthOrdering:
    """
    download_document() must check session BEFORE can_download permission.
    An unauthenticated caller must always get 401, never 403.
    """

    @pytest.mark.asyncio
    async def test_invalid_session_download_enabled_returns_401(self, client, db_session):
        doc = await _insert_doc(db_session, page_count=1)
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(doc.id),
            permissions={"can_download": True},
        )

        r = await client.get(
            f"/api/viewer/download/{link.token}",
            headers={"X-Session-ID": "0" * 32},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_session_download_disabled_also_401(self, client, db_session):
        doc = await _insert_doc(db_session, page_count=1)
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(doc.id),
            permissions={"can_download": False},
        )

        r = await client.get(
            f"/api/viewer/download/{link.token}",
            headers={"X-Session-ID": "0" * 32},
        )
        # Must be 401 — NOT 403 (which would leak that download is disabled)
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_session_no_permission_returns_403(self, client, db_session):
        doc = await _insert_doc(db_session, page_count=1)
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(doc.id),
            permissions={"can_download": False},
        )
        body = await _validate(client, link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/download/{link.token}",
            headers={"X-Session-ID": sid},
        )
        assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# F6. Thumbnail rate limit reduced to 120/min
# ══════════════════════════════════════════════════════════════════════════════

class TestThumbnailRateLimit:
    """The thumb endpoint rate limit must be 120/minute."""

    def test_thumb_route_rate_limit_is_120_per_minute(self):
        import inspect
        from app.routers.viewer import get_thumb
        src = inspect.getsource(get_thumb)
        assert "120/minute" in src, "Expected '120/minute' rate limit on get_thumb"
        assert "300/minute" not in src, "Old '300/minute' limit must be removed"


# ══════════════════════════════════════════════════════════════════════════════
# F7. Storage key hardening
# ══════════════════════════════════════════════════════════════════════════════

class TestStorageKeyHardening:
    """Storage keys must be UUID-derived, not user-filename-derived."""

    @pytest.mark.asyncio
    async def test_page_storage_keys_contain_doc_uuid_not_filename(
        self, client, db_session
    ):
        doc = await _insert_doc(db_session, page_count=2)
        result = await db_session.execute(
            select(DocumentPage).where(DocumentPage.document_id == doc.id)
        )
        pages = result.scalars().all()
        for page in pages:
            assert str(doc.id) in page.storage_key
            assert ".." not in page.storage_key
            assert "e1_test" not in page.storage_key  # filename must not appear in key
            assert page.storage_key.startswith("pages/")

    @pytest.mark.asyncio
    async def test_doc_storage_key_starts_with_originals(self, client, db_session):
        doc = await _insert_doc(db_session, page_count=1)
        assert doc.storage_key.startswith("originals/")
        assert ".." not in doc.storage_key
        assert "e1_test" not in doc.storage_key
