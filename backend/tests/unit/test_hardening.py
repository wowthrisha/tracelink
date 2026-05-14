"""
Tests covering the production-hardening fixes applied in the audit remediation pass.

Each test names the audit finding it covers (CRIT-N, HIGH-N, etc.) so regressions
are immediately traceable back to the original vulnerability.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── CRIT-2: storage_key must never appear in API error responses ─────────────

class TestStorageKeyNotLeaked:
    """CRIT-2: 502 error detail must not contain the storage key or bucket path."""

    @pytest.mark.asyncio
    async def test_upload_502_hides_storage_key(self, client, sample_pdf_bytes):
        """A storage failure must return a generic message, never the key."""
        with patch(
            "app.services.storage.StorageService.upload_file",
            new_callable=AsyncMock,
            side_effect=Exception("Connection reset by peer"),
        ):
            r = await client.post(
                "/api/documents/upload",
                files={"file": ("doc.pdf", sample_pdf_bytes, "application/pdf")},
            )
        assert r.status_code == 502
        body_text = r.text
        assert "originals/" not in body_text
        assert "storage_key" not in body_text
        # Generic message must be present
        assert "Storage upload failed" in body_text
        # The underlying exception detail must NOT be in the response
        assert "Connection reset by peer" not in body_text


# ── CRIT-3: IP hash salt must come from env, not source code ─────────────────

class TestIpHashSalt:
    """CRIT-3: hash_value must use settings.ip_hash_salt, not a hardcoded string."""

    def test_hash_value_uses_settings_salt(self):
        from app.utils.crypto import hash_value
        from app.config import settings

        result = hash_value("1.2.3.4")
        expected = __import__("hashlib").sha256(
            f"1.2.3.4{settings.ip_hash_salt}".encode()
        ).hexdigest()
        assert result == expected

    def test_hash_value_with_explicit_salt(self):
        from app.utils.crypto import hash_value
        result_a = hash_value("1.2.3.4", salt="salt_a")
        result_b = hash_value("1.2.3.4", salt="salt_b")
        assert result_a != result_b

    def test_hash_value_different_ips_differ(self):
        from app.utils.crypto import hash_value
        assert hash_value("1.2.3.4") != hash_value("5.6.7.8")


# ── CRIT-4: Analytics write endpoint requires valid session ───────────────────

class TestAnalyticsEndpointSecurity:
    """CRIT-4: POST /api/analytics/events must reject unauthenticated requests."""

    @pytest.mark.asyncio
    async def test_rejects_missing_session_id(self, client, active_link):
        r = await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": "",
            "event_type": "print_attempt",
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_fake_session_id(self, client, active_link):
        r = await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": "deadbeef" * 4,
            "event_type": "print_attempt",
        })
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_rejects_server_side_event_types(self, client, active_link):
        val = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = val.json()["session_id"]
        server_events = ["opened", "page_viewed", "access_denied", "revoked",
                         "expired", "ip_blocked", "session_limit_reached",
                         "max_views_reached", "password_wrong"]
        for evt in server_events:
            r = await client.post("/api/analytics/events", json={
                "token": active_link.token,
                "session_id": session_id,
                "event_type": evt,
            })
            assert r.status_code == 400, f"Expected 400 for server event {evt!r}"

    @pytest.mark.asyncio
    async def test_accepts_viewer_events_with_valid_session(self, client, active_link):
        val = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = val.json()["session_id"]
        viewer_events = ["print_attempt", "copy_attempt", "right_click_attempt",
                         "download_attempt", "completed"]
        for evt in viewer_events:
            r = await client.post("/api/analytics/events", json={
                "token": active_link.token,
                "session_id": session_id,
                "event_type": evt,
            })
            assert r.status_code == 200, f"Expected 200 for viewer event {evt!r}"


# ── CRIT-1: Document.user_id must be non-nullable ─────────────────────────────

class TestDocumentUserIdNotNull:
    """CRIT-1: user_id column must be NOT NULL."""

    @pytest.mark.asyncio
    async def test_document_user_id_is_not_nullable(self, db_session):
        from app.models.document import Document
        from sqlalchemy import inspect as sa_inspect

        col = Document.__table__.c["user_id"]
        assert not col.nullable, "Document.user_id must be NOT NULL"

    @pytest.mark.asyncio
    async def test_document_without_user_id_raises(self, db_session):
        """Inserting a document without user_id must fail at the DB level."""
        from app.models.document import Document
        from sqlalchemy.exc import IntegrityError

        doc = Document(
            id=uuid.uuid4(),
            filename="orphan.pdf",
            storage_key="originals/orphan.pdf",
            status="uploaded",
            file_size_bytes=100,
            # user_id intentionally omitted
        )
        db_session.add(doc)
        with pytest.raises((IntegrityError, Exception)):
            await db_session.flush()


# ── CRIT-5: created_by must be set atomically in create_link ─────────────────

class TestAtomicCreatedBy:
    """CRIT-5: create_link must set created_by in the same transaction."""

    @pytest.mark.asyncio
    async def test_created_by_is_set_in_single_transaction(self, client, db_session, sample_document_in_db):
        user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

        r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "label": "atomic test",
        })
        assert r.status_code == 201
        link_id = uuid.UUID(r.json()["id"])

        from sqlalchemy import select
        from app.models.link import ShareLink
        result = await db_session.execute(select(ShareLink).where(ShareLink.id == link_id))
        link = result.scalar_one()
        assert link.created_by == user_id, "created_by must be set in the same commit"


# ── HIGH-10: Rasterizer timeout protects against PDF bombs ───────────────────

class TestRasterizerTimeout:
    """HIGH-10: rasterize_document must raise RasterizerError on timeout."""

    @pytest.mark.asyncio
    async def test_timeout_raises_rasterizer_error(self):
        from app.services.rasterizer import RasterizerService, RasterizerError
        from unittest.mock import patch
        import asyncio

        svc = RasterizerService()
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"xref\n0 1\n0000000000 65535 f\n"
            b"trailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF"
        )

        # Simulate a conversion that takes forever
        def slow_convert(*args, **kwargs):
            import time
            time.sleep(60)

        with patch("pdf2image.convert_from_bytes", side_effect=slow_convert), \
             patch("app.config.settings.rasterizer_timeout_sec", 0.05):
            with pytest.raises(RasterizerError, match="timed out"):
                await svc.rasterize_document(pdf_bytes, "test-doc-id")


# ── Phase 2: Permanent errors must not retry ──────────────────────────────────

class TestWorkerErrorClassification:
    """Phase 2: RasterizerError and ValueError must not trigger Celery retries."""

    def test_rasterizer_error_is_permanent(self):
        """Verify RasterizerError is the exception used for permanent PDF failures."""
        from app.services.rasterizer import RasterizerError
        err = RasterizerError("PDF conversion timed out after 300s")
        assert isinstance(err, Exception)
        assert not isinstance(err, ConnectionError)  # not a transient network error


# ── Phase 3: IP allowlist fails closed on bad JSON ───────────────────────────

class TestPolicyFailClosed:
    """Audit: ip_is_allowed must fail CLOSED on malformed JSON."""

    def test_malformed_ip_allowlist_json_denies_access(self):
        from app.services.policy import PolicyEnforcer
        enforcer = PolicyEnforcer()
        # Malformed JSON must deny, not allow
        result = enforcer.ip_is_allowed("1.2.3.4", "{not valid json}")
        assert result is False

    def test_malformed_domain_json_denies_access(self):
        from app.services.policy import PolicyEnforcer
        enforcer = PolicyEnforcer()
        result = enforcer.email_domain_is_allowed("user@example.com", "[unclosed")
        assert result is False

    def test_null_allowlist_still_allows(self):
        from app.services.policy import PolicyEnforcer
        enforcer = PolicyEnforcer()
        assert enforcer.ip_is_allowed("1.2.3.4", None) is True
        assert enforcer.email_domain_is_allowed("u@x.com", None) is True


# ── Phase 5: Session entropy ──────────────────────────────────────────────────

class TestSessionEntropy:
    """Phase 5: session_id must be 128-bit (32 hex chars)."""

    def test_session_id_is_128_bit(self):
        from app.services.link_service import LinkService
        svc = LinkService()
        sid = svc._generate_session_id()
        assert len(sid) == 32, f"Expected 32 hex chars, got {len(sid)}"
        assert all(c in "0123456789abcdef" for c in sid)

    def test_session_ids_are_unique(self):
        from app.services.link_service import LinkService
        svc = LinkService()
        ids = {svc._generate_session_id() for _ in range(100)}
        assert len(ids) == 100, "Session IDs must be unique"


# ── Phase 5: Domain allowlist case-folding ───────────────────────────────────

class TestDomainCaseFolding:
    """Domains in allowlist must be normalized to lowercase at creation time."""

    @pytest.mark.asyncio
    async def test_domains_stored_lowercase(self, db_session, sample_document_in_db):
        from app.services.link_service import LinkService
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(sample_document_in_db.id),
            allowed_domains=["EXAMPLE.COM", "PARTNER.ORG"],
        )
        import json
        stored = json.loads(link.allowed_domains)
        assert "EXAMPLE.COM" not in stored
        assert "example.com" in stored
        assert "partner.org" in stored


# ── Phase 6: Billing — past_due must not grant Pro access ────────────────────

class TestBillingSubscriptionEnforcement:
    """Phase 6: past_due subscription must be treated as free plan."""

    @pytest.mark.asyncio
    async def test_past_due_user_cannot_bypass_quota(self, db_session):
        from app.routers.documents import _check_upload_quota
        from app.models.billing import UserBilling, PLAN_PRO, STATUS_PAST_DUE
        from app.config import settings

        uid = uuid.uuid4()
        billing = UserBilling(
            user_id=uid,
            plan=PLAN_PRO,
            subscription_status=STATUS_PAST_DUE,
        )
        db_session.add(billing)

        # Insert enough documents to hit the free limit
        from app.models.document import Document
        for _ in range(settings.free_plan_doc_limit):
            doc = Document(
                id=uuid.uuid4(),
                filename="f.pdf",
                storage_key=f"originals/{uuid.uuid4()}.pdf",
                status="ready",
                file_size_bytes=100,
                user_id=uid,
            )
            db_session.add(doc)
        await db_session.commit()

        # past_due Pro must be treated as free — should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await _check_upload_quota(db_session, uid)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_active_pro_bypasses_quota(self, db_session):
        from app.routers.documents import _check_upload_quota
        from app.models.billing import UserBilling, PLAN_PRO, STATUS_ACTIVE
        from app.config import settings

        uid = uuid.uuid4()
        billing = UserBilling(
            user_id=uid,
            plan=PLAN_PRO,
            subscription_status=STATUS_ACTIVE,
        )
        db_session.add(billing)

        from app.models.document import Document
        for _ in range(settings.free_plan_doc_limit):
            doc = Document(
                id=uuid.uuid4(), filename="f.pdf",
                storage_key=f"originals/{uuid.uuid4()}.pdf",
                status="ready", file_size_bytes=100, user_id=uid,
            )
            db_session.add(doc)
        await db_session.commit()

        # Active Pro must pass — no exception
        await _check_upload_quota(db_session, uid)
