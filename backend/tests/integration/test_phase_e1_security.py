"""
Phase E1 Security Hardening — regression tests.

Covers every fix made in Phase E1:
  A. SEC-01 — /thumb and /toc reject requests with unrecognized session_id (401)
  B. SEC-02 — upsert_session refuses cross-link session replay
  C. SEC-03 — /page and /text reject phantom session injection (401)
  D. SEC-04 — JWT 401 responses never leak internal library error details
  E. SEC-05 — GET /api/analytics/events returns truncated session_id (≤ 8 chars)
  F. SEC-06 — storage.upload_file does not auto-create missing buckets
  G. SEC-07 — (structural) Dockerfile runs as non-root user (appuser)
  H. SEC-08 — LibreOffice macro security XCU profile written before conversion

Pre-existing behaviour preserved:
  - Valid sessions continue to work on all four content endpoints
  - Revoked/expired/nonexistent links still return 404/410 before session check
  - /download session check unchanged (already correct)
  - Analytics POST still requires active session
"""
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.document import Document, DocumentPage
from app.models.link import ShareLink
from app.models.session import ViewerSession
from app.routers.viewer import clear_page_cache, clear_thumb_cache
from app.services.link_service import LinkService
from tests.conftest import TEST_USER_ID


# ── helpers ────────────────────────────────────────────────────────────────────

async def _insert_ready_doc(db, page_count: int = 3) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="e1test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=page_count,
        file_size_bytes=1024 * page_count,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db.add(doc)
    await db.flush()
    for i in range(1, page_count + 1):
        db.add(DocumentPage(
            document_id=doc.id,
            page_number=i,
            storage_key=f"pages/{doc.id}/{i:04d}.webp",
            width_px=595,
            height_px=842,
        ))
    await db.commit()
    await db.refresh(doc)
    return doc


async def _create_link(db, doc: Document) -> ShareLink:
    svc = LinkService()
    return await svc.create_link(db, document_id=str(doc.id))


async def _get_session(client, token: str) -> str:
    """Call /validate to create a real ViewerSession; return the session_id."""
    r = await client.post("/api/viewer/validate", json={"token": token})
    assert r.status_code == 200, f"validate failed: {r.status_code} {r.text}"
    return r.json()["session_id"]


# ══════════════════════════════════════════════════════════════════════════════
# A. SEC-01 — /thumb and /toc reject unrecognized session_id (401)
# ══════════════════════════════════════════════════════════════════════════════

class TestSec01ThumbSessionRequired:
    """GET /api/viewer/thumb must validate session_id via is_active_session."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        clear_thumb_cache()
        yield
        clear_page_cache()
        clear_thumb_cache()

    @pytest.mark.asyncio
    async def test_thumb_random_session_returns_401(self, client, db_session):
        """A random string that was never validated must yield 401, not 200."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)

        r = await client.get(
            f"/api/viewer/thumb/{link.token}/1?session_id=deadbeefdeadbeef"
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_thumb_valid_session_returns_200(self, client, db_session):
        """A properly validated session must allow access."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)
        session_id = await _get_session(client, link.token)

        with patch(
            "app.services.storage.StorageService.download_bytes",
            new_callable=AsyncMock,
        ) as mock_dl:
            from tests.conftest import _make_webp_bytes
            mock_dl.return_value = _make_webp_bytes()
            r = await client.get(
                f"/api/viewer/thumb/{link.token}/1?session_id={session_id}"
            )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_thumb_missing_session_returns_400(self, client, db_session):
        """Missing session_id must still return 400 (unchanged behaviour)."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)

        r = await client.get(f"/api/viewer/thumb/{link.token}/1")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_thumb_revoked_link_fires_before_session_check(self, client, revoked_link):
        """Revoked link returns 410, not 401 — link check has higher priority."""
        r = await client.get(
            f"/api/viewer/thumb/{revoked_link.token}/1?session_id=anystring"
        )
        assert r.status_code == 410


class TestSec01TocSessionRequired:
    """GET /api/viewer/toc must validate session_id via is_active_session."""

    @pytest.mark.asyncio
    async def test_toc_random_session_returns_401(self, client, db_session):
        """A random session_id must yield 401 on /toc."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)

        r = await client.get(
            f"/api/viewer/toc/{link.token}?session_id=notarealtoken"
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_toc_valid_session_returns_200(self, client, db_session):
        """A real session must yield 200 on /toc."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)
        session_id = await _get_session(client, link.token)

        r = await client.get(
            f"/api/viewer/toc/{link.token}?session_id={session_id}"
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_toc_missing_session_returns_400(self, client, db_session):
        """Missing session_id must still return 400."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)

        r = await client.get(f"/api/viewer/toc/{link.token}")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_toc_expired_link_fires_before_session_check(self, client, expired_link):
        """Expired link returns 410 before session check."""
        r = await client.get(
            f"/api/viewer/toc/{expired_link.token}?session_id=anystring"
        )
        assert r.status_code == 410


# ══════════════════════════════════════════════════════════════════════════════
# B. SEC-02 — upsert_session refuses cross-link session replay
# ══════════════════════════════════════════════════════════════════════════════

class TestSec02UpsertSessionLinkOwnership:
    """upsert_session must reject session IDs that belong to a different link."""

    @pytest.mark.asyncio
    async def test_upsert_session_cross_link_returns_none(self, db_session):
        """upsert_session must return None when existing.link_id != link_id."""
        from app.services.policy import PolicyEnforcer
        from app.models.link import ShareLink
        from app.models.document import Document

        doc = await _insert_ready_doc(db_session)
        link_a = await _create_link(db_session, doc)
        link_b_obj = ShareLink(
            id=uuid.uuid4(),
            document_id=doc.id,
            token="link_b_token_unique_e1",
            label="link-b",
        )
        db_session.add(link_b_obj)
        await db_session.commit()

        enforcer = PolicyEnforcer()
        sid = "aabbccddeeff00112233445566778899"

        # Seed session belonging to link_a
        db_session.add(ViewerSession(
            session_id=sid,
            link_id=link_a.id,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            last_seen_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        ))
        await db_session.commit()

        # Attempt to upsert under link_b — must return None (not link_a's email)
        result = await enforcer.upsert_session(db_session, sid, link_b_obj.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_session_same_link_returns_email(self, db_session):
        """upsert_session must return the viewer email when link_id matches."""
        from app.services.policy import PolicyEnforcer
        import datetime

        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)
        enforcer = PolicyEnforcer()
        sid = "1122334455667788aabbccddeeff0011"

        db_session.add(ViewerSession(
            session_id=sid,
            link_id=link.id,
            viewer_email_masked="v***@test.com",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            last_seen_at=datetime.datetime.now(datetime.timezone.utc),
        ))
        await db_session.commit()

        result = await enforcer.upsert_session(db_session, sid, link.id)
        assert result == "v***@test.com"

    @pytest.mark.asyncio
    async def test_cross_link_session_cannot_access_page(self, client, db_session):
        """
        A session created for link_a cannot be replayed against link_b
        to read link_b's pages.
        """
        doc = await _insert_ready_doc(db_session)

        svc = LinkService()
        link_a = await svc.create_link(db_session, document_id=str(doc.id))
        link_b = await svc.create_link(db_session, document_id=str(doc.id))

        # Validate against link_a — creates a session tied to link_a
        session_id = await _get_session(client, link_a.token)

        # Try to use link_a's session against link_b's /page endpoint
        r = await client.get(
            f"/api/viewer/page/{link_b.token}/1?session_id={session_id}"
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_cross_link_session_cannot_access_thumb(self, client, db_session):
        """A session from link_a must be rejected by link_b's /thumb endpoint."""
        doc = await _insert_ready_doc(db_session)

        svc = LinkService()
        link_a = await svc.create_link(db_session, document_id=str(doc.id))
        link_b = await svc.create_link(db_session, document_id=str(doc.id))

        session_id = await _get_session(client, link_a.token)

        r = await client.get(
            f"/api/viewer/thumb/{link_b.token}/1?session_id={session_id}"
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_cross_link_session_cannot_access_toc(self, client, db_session):
        """A session from link_a must be rejected by link_b's /toc endpoint."""
        doc = await _insert_ready_doc(db_session)

        svc = LinkService()
        link_a = await svc.create_link(db_session, document_id=str(doc.id))
        link_b = await svc.create_link(db_session, document_id=str(doc.id))

        session_id = await _get_session(client, link_a.token)

        r = await client.get(
            f"/api/viewer/toc/{link_b.token}?session_id={session_id}"
        )
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# C. SEC-03 — /page and /text reject phantom session injection (401)
# ══════════════════════════════════════════════════════════════════════════════

class TestSec03PageSessionValidation:
    """/page must call is_active_session before serving content or upserting."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        yield
        clear_page_cache()

    @pytest.mark.asyncio
    async def test_page_random_session_returns_401(self, client, db_session):
        """A random string session_id must yield 401 on /page."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)

        r = await client.get(
            f"/api/viewer/page/{link.token}/1?session_id=randomrandomrandom"
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_page_phantom_session_not_persisted(self, client, db_session):
        """A rejected phantom session_id must NOT create a ViewerSession row."""
        from sqlalchemy import select as _select

        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)
        fake_sid = "phantomphantomphantom0000000001"

        await client.get(
            f"/api/viewer/page/{link.token}/1?session_id={fake_sid}"
        )

        row = await db_session.get(ViewerSession, fake_sid)
        assert row is None, "Phantom session must not be persisted in the DB"

    @pytest.mark.asyncio
    async def test_page_expired_link_fires_before_session_check(self, client, expired_link):
        """Expired link returns 410 before session check."""
        r = await client.get(
            f"/api/viewer/page/{expired_link.token}/1?session_id=anysession"
        )
        assert r.status_code == 410


class TestSec03TextSessionValidation:
    """/text must call is_active_session before serving content."""

    @pytest.mark.asyncio
    async def test_text_random_session_returns_401(self, client, db_session):
        """A random session_id must yield 401 on /text for a text document."""
        doc = Document(
            id=uuid.uuid4(),
            filename="notes.txt",
            storage_key=f"originals/{uuid.uuid4()}.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=100,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        link = await _create_link(db_session, doc)

        r = await client.get(
            f"/api/viewer/text/{link.token}/1?session_id=notvalid00000000"
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_text_phantom_session_not_persisted(self, client, db_session):
        """Rejected phantom text session must not create a ViewerSession row."""
        doc = Document(
            id=uuid.uuid4(),
            filename="report.txt",
            storage_key=f"originals/{uuid.uuid4()}.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=50,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        link = await _create_link(db_session, doc)
        fake_sid = "phantomtextphantomt0000000002"

        await client.get(
            f"/api/viewer/text/{link.token}/1?session_id={fake_sid}"
        )

        row = await db_session.get(ViewerSession, fake_sid)
        assert row is None, "Phantom session must not be persisted"


# ══════════════════════════════════════════════════════════════════════════════
# D. SEC-04 — JWT 401 responses never leak internal error details
# ══════════════════════════════════════════════════════════════════════════════

class TestSec04JwtErrorMessages:
    """JWT 401 errors must return a generic message, never library internals."""

    @pytest.mark.asyncio
    async def test_bad_jwt_header_generic_message(self):
        """A malformed JWT header returns generic 'Authentication failed'."""
        from app.auth import verify_supabase_token
        import pytest
        with pytest.raises(Exception) as exc_info:
            await verify_supabase_token("not.a.valid.jwt.at.all")
        assert "Authentication failed" in str(exc_info.value.detail)
        # Must NOT leak internal library details
        assert "DecodeError" not in str(exc_info.value.detail)
        assert "Traceback" not in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_invalid_algorithm_generic_message(self):
        """A token with a non-ES256/RS256 algorithm returns generic message."""
        import jwt as _jwt
        from app.auth import verify_supabase_token
        import pytest

        # Craft a token with HS256 alg header (rejected algorithm)
        token = _jwt.encode({"sub": "user123"}, "secret", algorithm="HS256")
        with pytest.raises(Exception) as exc_info:
            await verify_supabase_token(token)
        assert "Authentication failed" in str(exc_info.value.detail)
        assert "HS256" not in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_invalid_token_no_kid_in_error(self):
        """Key lookup failure must not reveal JWKS structure or key ID."""
        import time
        from app import auth as _auth
        import pytest

        # Directly exercise _get_public_key with a populated cache (> 1 key) so
        # neither the single-key fallback nor a JWKS refresh hides the check.
        orig_cache = dict(_auth._jwks_cache)
        orig_fetched_at = _auth._jwks_fetched_at
        try:
            _auth._jwks_cache.clear()
            _auth._jwks_cache["real-key-1"] = MagicMock()
            _auth._jwks_cache["real-key-2"] = MagicMock()
            _auth._jwks_fetched_at = time.time()  # prevent auto-refresh

            with pytest.raises(Exception) as exc_info:
                await _auth._get_public_key("nonexistent-kid-xyz")
        finally:
            _auth._jwks_cache.clear()
            _auth._jwks_cache.update(orig_cache)
            _auth._jwks_fetched_at = orig_fetched_at

        detail = str(exc_info.value.detail)
        # Old behaviour was: "Key 'nonexistent-kid-xyz' not in JWKS"
        assert "nonexistent-kid-xyz" not in detail, "Must not leak the kid in the error"
        assert "JWKS" not in detail, "Must not mention JWKS"
        assert "Authentication failed" in detail


# ══════════════════════════════════════════════════════════════════════════════
# E. SEC-05 — GET /api/analytics/events returns truncated session_id
# ══════════════════════════════════════════════════════════════════════════════

class TestSec05AnalyticsSessionIdTruncated:
    """Analytics GET /events must never expose full 32-char session IDs."""

    @pytest.mark.asyncio
    async def test_events_session_id_truncated_to_8_chars(self, client, active_link, ready_document):
        """session_id in analytics events response must be ≤ 8 characters."""
        # Log an event via a valid session
        session_id = await _get_session(client, active_link.token)

        # Generate at least one event
        await client.post("/api/analytics/events", json={
            "session_id": session_id,
            "event_type": "copy_attempt",
            "link_id": str(active_link.id),
        })

        r = await client.get(
            f"/api/analytics/events?document_id={ready_document.id}",
            headers={"Authorization": "Bearer faketoken"},
        )
        assert r.status_code == 200

        for event in r.json().get("events", []):
            sid = event.get("session_id")
            if sid is not None:
                assert len(sid) <= 8, (
                    f"session_id in analytics response is {len(sid)} chars, expected ≤ 8: {sid!r}"
                )

    @pytest.mark.asyncio
    async def test_events_truncated_session_id_not_replayable(self, client, active_link, ready_document):
        """The truncated prefix cannot be used as a complete session token."""
        session_id = await _get_session(client, active_link.token)

        await client.post("/api/analytics/events", json={
            "session_id": session_id,
            "event_type": "right_click_attempt",
            "link_id": str(active_link.id),
        })

        r = await client.get(
            f"/api/analytics/events?document_id={ready_document.id}",
            headers={"Authorization": "Bearer faketoken"},
        )
        events = r.json().get("events", [])
        truncated_ids = {e["session_id"] for e in events if e.get("session_id")}

        # Full session_id must not appear in any response
        assert session_id not in truncated_ids, (
            "Full 32-char session_id must never appear in analytics response"
        )


# ══════════════════════════════════════════════════════════════════════════════
# F. SEC-06 — storage upload does not auto-create missing buckets
# ══════════════════════════════════════════════════════════════════════════════

class TestSec06StorageNoAutoBucketCreation:
    """StorageService.upload_file must raise on NoSuchBucket, not create it."""

    def test_no_such_bucket_raises_client_error(self):
        """NoSuchBucket error must propagate; bucket auto-creation must not occur."""
        import asyncio
        from botocore.exceptions import ClientError
        from app.services.storage import StorageService

        svc = StorageService.__new__(StorageService)
        svc._bucket = "test-bucket"
        svc._endpoint_url = None
        svc._path_style = False
        svc._region = "us-east-1"

        error_response = {"Error": {"Code": "NoSuchBucket", "Message": "The bucket does not exist"}}
        mock_client = MagicMock()
        mock_client.upload_fileobj.side_effect = ClientError(error_response, "PutObject")

        create_bucket_called = []

        def track_create_bucket(**kwargs):
            create_bucket_called.append(True)

        mock_client.create_bucket.side_effect = track_create_bucket

        with patch.object(svc, "_get_client", return_value=mock_client):
            with pytest.raises(ClientError):
                asyncio.get_event_loop().run_until_complete(
                    svc.upload_file(b"data", "key/test.pdf", "application/pdf")
                )

        assert not create_bucket_called, (
            "create_bucket must never be called on NoSuchBucket — "
            "bucket auto-creation was removed in Phase E1"
        )


# ══════════════════════════════════════════════════════════════════════════════
# G. SEC-07 — Dockerfile runs as non-root (structural test)
# ══════════════════════════════════════════════════════════════════════════════

class TestSec07NonRootDockerfile:
    """Dockerfile must define a non-root user and switch to it."""

    def test_dockerfile_has_user_directive(self):
        """Dockerfile must contain a USER directive for a non-root user."""
        import os
        dockerfile = os.path.join(
            os.path.dirname(__file__), "..", "..", "Dockerfile"
        )
        with open(os.path.abspath(dockerfile)) as f:
            content = f.read()
        assert "USER appuser" in content, "Dockerfile must switch to non-root appuser"

    def test_dockerfile_creates_appuser(self):
        """Dockerfile must create the appuser account with UID 1001."""
        import os
        dockerfile = os.path.join(
            os.path.dirname(__file__), "..", "..", "Dockerfile"
        )
        with open(os.path.abspath(dockerfile)) as f:
            content = f.read()
        assert "useradd" in content, "Dockerfile must create a non-root user with useradd"
        assert "appuser" in content, "Dockerfile must name the user appuser"
        assert "1001" in content, "Dockerfile must use UID 1001"

    def test_user_directive_after_app_setup(self):
        """USER appuser must appear AFTER the app is copied and configured."""
        import os
        dockerfile = os.path.join(
            os.path.dirname(__file__), "..", "..", "Dockerfile"
        )
        with open(os.path.abspath(dockerfile)) as f:
            content = f.read()
        copy_pos = content.rfind("COPY backend/")
        user_pos = content.find("USER appuser")
        assert copy_pos < user_pos, "USER appuser must appear after COPY backend/"


# ══════════════════════════════════════════════════════════════════════════════
# H. SEC-08 — LibreOffice macro security XCU profile
# ══════════════════════════════════════════════════════════════════════════════

class TestSec08LibreOfficeMacroSecurity:
    """LibreOfficeConverter must write a macro security profile before running LO."""

    def _make_converter(self):
        from app.services.libreoffice_converter import LibreOfficeConverter
        c = LibreOfficeConverter()
        c.CONVERSION_TIMEOUT_SEC = 5
        return c

    def test_xcu_file_written_before_subprocess(self, tmp_path):
        """registrymodifications.xcu must exist with MacroSecurityLevel=3."""
        import os
        fake_pdf = b"%PDF-1.4 fake"
        converter = self._make_converter()

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")
            (tmp_path / "input.pdf").write_bytes(fake_pdf)
            converter.convert_to_pdf(b"PK\x03\x04 fake", ".docx")

        xcu = tmp_path / "lo_profile" / "user" / "config" / "registrymodifications.xcu"
        assert xcu.exists(), "XCU profile must be written"
        content = xcu.read_text()
        assert "MacroSecurityLevel" in content
        assert "<value>3</value>" in content

    def test_xcu_written_before_subprocess_call(self, tmp_path):
        """The XCU file must be created before subprocess.run is called."""
        import os
        fake_pdf = b"%PDF-1.4 fake"
        converter = self._make_converter()
        xcu_existed_before_subprocess = []

        def check_xcu(cmd, **kwargs):
            xcu_path = os.path.join(str(tmp_path), "lo_profile", "user", "config", "registrymodifications.xcu")
            xcu_existed_before_subprocess.append(os.path.exists(xcu_path))
            return MagicMock(returncode=0, stderr=b"", stdout=b"")

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run", side_effect=check_xcu), \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            (tmp_path / "input.pdf").write_bytes(fake_pdf)
            converter.convert_to_pdf(b"PK\x03\x04 fake", ".docx")

        assert xcu_existed_before_subprocess, "subprocess.run must be called"
        assert xcu_existed_before_subprocess[0], "XCU must exist when subprocess.run is called"

    def test_no_nomacroexecution_flag(self, tmp_path):
        """--nomacroexecution must NOT be in the command (removed in LO 25.2)."""
        fake_pdf = b"%PDF-1.4 fake"
        converter = self._make_converter()

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")
            (tmp_path / "input.pdf").write_bytes(fake_pdf)
            converter.convert_to_pdf(b"PK\x03\x04 fake", ".docx")

        cmd = mock_run.call_args.args[0]
        assert "--nomacroexecution" not in cmd, (
            "--nomacroexecution is not valid in LibreOffice 25.2+; "
            "macro security is now handled via the XCU profile"
        )

    def test_xcu_macro_level_is_very_high(self, tmp_path):
        """The security level in the XCU must be 3 (Very High), not 0/1/2."""
        fake_pdf = b"%PDF-1.4 fake"
        converter = self._make_converter()

        with patch("shutil.which", return_value="/usr/bin/libreoffice"), \
             patch("subprocess.run") as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("shutil.rmtree"):

            mock_run.return_value = MagicMock(returncode=0, stderr=b"")
            (tmp_path / "input.pdf").write_bytes(fake_pdf)
            converter.convert_to_pdf(b"PK\x03\x04 fake", ".docx")

        xcu = tmp_path / "lo_profile" / "user" / "config" / "registrymodifications.xcu"
        content = xcu.read_text()
        # Ensure value is "3" (Very High), not 0 (Low) or 1 (Medium) or 2 (High)
        assert "<value>3</value>" in content
        assert "<value>0</value>" not in content
        assert "<value>1</value>" not in content
        assert "<value>2</value>" not in content


# ══════════════════════════════════════════════════════════════════════════════
# I. Regression — existing correct behaviours not broken by E1 changes
# ══════════════════════════════════════════════════════════════════════════════

class TestE1Regression:
    """Verify that E1 changes do not break previously-correct behaviour."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        clear_thumb_cache()
        yield
        clear_page_cache()
        clear_thumb_cache()

    @pytest.mark.asyncio
    async def test_valid_session_can_access_page(self, client, db_session):
        """A properly validated session must still be able to read pages."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)
        session_id = await _get_session(client, link.token)

        with patch(
            "app.services.storage.StorageService.download_bytes",
            new_callable=AsyncMock,
        ) as mock_dl:
            from tests.conftest import _make_webp_bytes
            mock_dl.return_value = _make_webp_bytes()
            r = await client.get(
                f"/api/viewer/page/{link.token}/1?session_id={session_id}"
            )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_validate_still_creates_session(self, client, db_session):
        """POST /validate must still create a ViewerSession row."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        session_id = r.json()["session_id"]
        assert len(session_id) == 32

        row = await db_session.get(ViewerSession, session_id)
        assert row is not None, "validate must create a ViewerSession row"
        assert row.link_id == link.id

    @pytest.mark.asyncio
    async def test_download_still_validates_session(self, client, active_link):
        """Download endpoint (already correct) must still enforce session."""
        r = await client.get(
            f"/api/viewer/download/{active_link.token}?session_id=badsession"
        )
        assert r.status_code in (401, 403, 404)

    @pytest.mark.asyncio
    async def test_analytics_post_still_requires_active_session(self, client, active_link):
        """POST /analytics/events must reject unrecognized session_ids."""
        r = await client.post("/api/analytics/events", json={
            "session_id": "fakefakefake0000000000000000",
            "event_type": "copy_attempt",
            "link_id": str(active_link.id),
        })
        assert r.status_code in (400, 401, 403)

    @pytest.mark.asyncio
    async def test_session_reuse_across_validate_calls(self, client, db_session):
        """Re-validating with an existing session_id must reuse the same session."""
        doc = await _insert_ready_doc(db_session)
        link = await _create_link(db_session, doc)

        r1 = await client.post("/api/viewer/validate", json={"token": link.token})
        sid1 = r1.json()["session_id"]

        r2 = await client.post("/api/viewer/validate", json={"token": link.token, "session_id": sid1})
        sid2 = r2.json()["session_id"]

        assert sid1 == sid2, "Session reuse must return the same session_id"
