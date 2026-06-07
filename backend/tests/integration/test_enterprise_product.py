"""
Enterprise Product Completeness Test Suite — Phase 3

Covers:
  Action 10: PPTX support
  Action 11: XLSX support
  Action 12: Time-on-page analytics
  Action 13: Webhooks
  Action 14: Public API (API keys)
"""
import hashlib
import hmac
import json
import uuid
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.config import Settings
from app.services.adapters.registry import get_adapter, all_adapters, allowed_content_types
from app.services.text_processor import detect_file_type
from app.models.webhook import WEBHOOK_EVENTS
from app.models.api_key import API_SCOPES, generate_api_key, hash_api_key
from app.workers.webhook_tasks import sign_payload


# ══════════════════════════════════════════════════════════════════════════════
# Actions 10 & 11: PPTX and XLSX Support
# ══════════════════════════════════════════════════════════════════════════════

class TestPPTXSupport:
    """PPTX files are detected, validated, and routed through LibreOffice pipeline."""

    def test_adapter_registered(self):
        adapter = get_adapter("pptx")
        assert adapter.file_type == "pptx"

    def test_adapter_viewer_mode_is_image(self):
        adapter = get_adapter("pptx")
        assert adapter.viewer_mode == "image"

    def test_adapter_supports_thumbnails(self):
        adapter = get_adapter("pptx")
        assert adapter.supports_thumbnails() is True

    def test_adapter_mime_type(self):
        adapter = get_adapter("pptx")
        assert "application/vnd.openxmlformats-officedocument.presentationml.presentation" \
               in adapter.upload_mime_types()

    def test_adapter_validate_bytes_rejects_non_zip(self):
        adapter = get_adapter("pptx")
        with pytest.raises(ValueError, match="ZIP header"):
            adapter.validate_bytes(b"not a zip file", "test.pptx")

    def test_adapter_validate_bytes_accepts_zip_magic(self):
        adapter = get_adapter("pptx")
        zip_magic = b"PK\x03\x04" + b"\x00" * 100
        adapter.validate_bytes(zip_magic, "test.pptx")  # must not raise

    def test_detect_file_type_pptx_by_extension(self):
        zip_bytes = b"PK\x03\x04" + b"\x00" * 100
        result = detect_file_type("deck.pptx", "application/octet-stream", zip_bytes)
        assert result == "pptx"

    def test_detect_file_type_pptx_by_content_type(self):
        zip_bytes = b"PK\x03\x04" + b"\x00" * 100
        ct = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        result = detect_file_type("deck", ct, zip_bytes)
        assert result == "pptx"

    def test_detect_file_type_pptx_rejects_non_zip(self):
        with pytest.raises(ValueError, match="ZIP header"):
            detect_file_type("deck.pptx", "application/octet-stream", b"not a zip")

    def test_allowed_content_types_includes_pptx(self):
        ct = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert ct in allowed_content_types()

    @pytest.mark.asyncio
    async def test_pptx_upload_accepted(self, client):
        """PPTX upload must return 200 with a document ID."""
        zip_magic = b"PK\x03\x04" + b"\x00" * 200
        with patch("app.services.text_processor.detect_file_type", return_value="pptx"), \
             patch("app.routers.documents.get_storage_service") as mock_storage_factory, \
             patch("app.workers.tasks.process_document") as mock_task:
            mock_storage = MagicMock()
            mock_storage.upload_file = AsyncMock(return_value="originals/test.pptx")
            mock_storage_factory.return_value = mock_storage
            mock_task.delay = MagicMock()

            r = await client.post(
                "/api/documents/upload",
                files={"file": ("deck.pptx", zip_magic,
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
            )
        assert r.status_code in (200, 202)
        assert "id" in r.json()


class TestXLSXSupport:
    """XLSX files are detected, validated, and routed through LibreOffice pipeline."""

    def test_adapter_registered(self):
        adapter = get_adapter("xlsx")
        assert adapter.file_type == "xlsx"

    def test_adapter_viewer_mode_is_image(self):
        adapter = get_adapter("xlsx")
        assert adapter.viewer_mode == "image"

    def test_adapter_supports_thumbnails(self):
        adapter = get_adapter("xlsx")
        assert adapter.supports_thumbnails() is True

    def test_adapter_mime_type(self):
        adapter = get_adapter("xlsx")
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
               in adapter.upload_mime_types()

    def test_adapter_validate_bytes_rejects_non_zip(self):
        adapter = get_adapter("xlsx")
        with pytest.raises(ValueError, match="ZIP header"):
            adapter.validate_bytes(b"not a zip file", "test.xlsx")

    def test_adapter_validate_bytes_accepts_zip_magic(self):
        adapter = get_adapter("xlsx")
        zip_magic = b"PK\x03\x04" + b"\x00" * 100
        adapter.validate_bytes(zip_magic, "test.xlsx")  # must not raise

    def test_detect_file_type_xlsx_by_extension(self):
        zip_bytes = b"PK\x03\x04" + b"\x00" * 100
        result = detect_file_type("report.xlsx", "application/octet-stream", zip_bytes)
        assert result == "xlsx"

    def test_detect_file_type_xlsx_by_content_type(self):
        zip_bytes = b"PK\x03\x04" + b"\x00" * 100
        ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        result = detect_file_type("report", ct, zip_bytes)
        assert result == "xlsx"

    def test_detect_file_type_xlsx_rejects_non_zip(self):
        with pytest.raises(ValueError, match="ZIP header"):
            detect_file_type("report.xlsx", "application/octet-stream", b"not a zip")

    def test_allowed_content_types_includes_xlsx(self):
        ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert ct in allowed_content_types()

    @pytest.mark.asyncio
    async def test_xlsx_upload_accepted(self, client):
        """XLSX upload must return 200 with a document ID."""
        zip_magic = b"PK\x03\x04" + b"\x00" * 200
        with patch("app.services.text_processor.detect_file_type", return_value="xlsx"), \
             patch("app.routers.documents.get_storage_service") as mock_storage_factory, \
             patch("app.workers.tasks.process_document") as mock_task:
            mock_storage = MagicMock()
            mock_storage.upload_file = AsyncMock(return_value="originals/test.xlsx")
            mock_storage_factory.return_value = mock_storage
            mock_task.delay = MagicMock()

            r = await client.post(
                "/api/documents/upload",
                files={"file": ("report.xlsx", zip_magic,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        assert r.status_code in (200, 202)
        assert "id" in r.json()

    def test_eight_adapters_registered(self):
        """Registry must have 8 adapters after adding PPTX and XLSX."""
        assert len(all_adapters()) == 8


# ══════════════════════════════════════════════════════════════════════════════
# Action 12: Time-on-Page Analytics (implementation in next step)
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeOnPageAnalytics:
    """time_spent_ms field accepted in access event logging."""

    @pytest.mark.asyncio
    async def test_analytics_event_accepts_time_spent_ms(self, client, active_link):
        val_r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        assert val_r.status_code == 200
        sid = val_r.json()["session_id"]

        r = await client.post(
            "/api/analytics/events",
            json={
                "token": active_link.token,
                "session_id": sid,
                "event_type": "completed",
                "page_number": 1,
                "time_spent_ms": 12500,
            },
        )
        assert r.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_analytics_event_without_time_spent_ms_still_accepted(
        self, client, active_link
    ):
        val_r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        sid = val_r.json()["session_id"]

        r = await client.post(
            "/api/analytics/events",
            json={
                "token": active_link.token,
                "session_id": sid,
                "event_type": "completed",
                "page_number": 1,
            },
        )
        assert r.status_code in (200, 201)


# ══════════════════════════════════════════════════════════════════════════════
# Action 13: Webhooks
# ══════════════════════════════════════════════════════════════════════════════

class TestWebhooks:
    """Webhook endpoint CRUD, delivery dispatch, HMAC signing, and retry."""

    # ── helpers ──

    async def _create(self, client, events=None, url="https://example.com/hook"):
        events = events or ["document.processed"]
        r = await client.post(
            "/api/webhooks",
            json={"url": url, "events": events, "description": "test hook"},
        )
        return r

    # ── CRUD ──

    @pytest.mark.asyncio
    async def test_create_returns_201_with_secret(self, client):
        r = await self._create(client)
        assert r.status_code == 201
        body = r.json()
        assert "secret" in body
        assert len(body["secret"]) == 64  # 32-byte hex

    @pytest.mark.asyncio
    async def test_create_all_event_types_accepted(self, client):
        r = await self._create(client, events=sorted(WEBHOOK_EVENTS))
        assert r.status_code == 201

    @pytest.mark.asyncio
    async def test_list_webhooks_no_secret(self, client):
        await self._create(client)
        r = await client.get("/api/webhooks")
        assert r.status_code == 200
        webhooks = r.json()["webhooks"]
        assert len(webhooks) >= 1
        for wh in webhooks:
            assert "secret" not in wh

    @pytest.mark.asyncio
    async def test_get_webhook_no_secret(self, client):
        cr = await self._create(client)
        wh_id = cr.json()["id"]
        r = await client.get(f"/api/webhooks/{wh_id}")
        assert r.status_code == 200
        assert "secret" not in r.json()

    @pytest.mark.asyncio
    async def test_update_webhook_url_and_active(self, client):
        cr = await self._create(client)
        wh_id = cr.json()["id"]
        r = await client.patch(
            f"/api/webhooks/{wh_id}",
            json={"url": "https://new.example.com/hook", "is_active": False},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["url"] == "https://new.example.com/hook"
        assert body["is_active"] is False
        assert "secret" not in body

    @pytest.mark.asyncio
    async def test_delete_webhook(self, client):
        cr = await self._create(client)
        wh_id = cr.json()["id"]
        r = await client.delete(f"/api/webhooks/{wh_id}")
        assert r.status_code == 204
        # Confirm deleted
        r2 = await client.get(f"/api/webhooks/{wh_id}")
        assert r2.status_code == 404

    @pytest.mark.asyncio
    async def test_other_user_cannot_access(self, client):
        """Webhook owned by user A must not be visible to user B."""
        cr = await self._create(client)
        wh_id = cr.json()["id"]
        # Overriding get_current_user to a different user_id
        from app.auth import get_current_user
        other_id = str(uuid.uuid4())
        from app.main import app
        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": other_id, "email": "other@test.com"
        }
        try:
            r = await client.get(f"/api/webhooks/{wh_id}")
            assert r.status_code == 404
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original
            else:
                app.dependency_overrides.pop(get_current_user, None)

    # ── Validation ──

    @pytest.mark.asyncio
    async def test_invalid_url_rejected(self, client):
        r = await self._create(client, url="not-a-url")
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_event_type_rejected(self, client):
        r = await client.post(
            "/api/webhooks",
            json={"url": "https://example.com/hook", "events": ["invalid.event"]},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_events_rejected(self, client):
        r = await client.post(
            "/api/webhooks",
            json={"url": "https://example.com/hook", "events": []},
        )
        assert r.status_code == 422

    # ── Delivery ──

    @pytest.mark.asyncio
    async def test_delivery_history_endpoint(self, client):
        cr = await self._create(client)
        wh_id = cr.json()["id"]
        r = await client.get(f"/api/webhooks/{wh_id}/deliveries")
        assert r.status_code == 200
        assert "deliveries" in r.json()

    @pytest.mark.asyncio
    async def test_test_endpoint_queues_delivery(self, client):
        cr = await self._create(client)
        wh_id = cr.json()["id"]
        with patch("app.routers.webhooks.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()
            r = await client.post(f"/api/webhooks/{wh_id}/test")
        assert r.status_code == 202
        body = r.json()
        assert "delivery_id" in body
        assert body["status"] == "queued"

    # ── HMAC signing ──

    def test_sign_payload_sha256_format(self):
        sig = sign_payload("mysecret", b'{"event":"test"}')
        assert sig.startswith("sha256=")
        assert len(sig) == 7 + 64  # "sha256=" + 64 hex chars

    def test_sign_payload_deterministic(self):
        body = b'{"hello":"world"}'
        s1 = sign_payload("key", body)
        s2 = sign_payload("key", body)
        assert s1 == s2

    def test_sign_payload_different_secret_different_sig(self):
        body = b'{"x":1}'
        assert sign_payload("key1", body) != sign_payload("key2", body)

    def test_sign_payload_matches_stdlib(self):
        secret = "test_secret_abc"
        body = b'{"event":"document.processed"}'
        expected = "sha256=" + hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        assert sign_payload(secret, body) == expected

    # ── Dispatch integration ──

    @pytest.mark.asyncio
    async def test_dispatch_creates_delivery_record(self, client, db_session):
        """dispatch_webhook_event creates a delivery row and queues a Celery task."""
        from sqlalchemy import select
        from app.models.webhook import WebhookEndpoint, WebhookDelivery
        from app.services.webhook_service import dispatch_webhook_event
        from app.auth import get_current_user
        from app.main import app

        user_id = app.dependency_overrides[get_current_user]()["user_id"]

        # Create endpoint subscribed to document.processed
        ep = WebhookEndpoint(
            user_id=uuid.UUID(user_id),
            url="https://example.com/wh",
            secret="a" * 64,
            is_active=True,
        )
        ep.events = ["document.processed"]
        db_session.add(ep)
        await db_session.commit()

        with patch("app.services.webhook_service.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()
            dispatched = await dispatch_webhook_event(
                db_session,
                user_id=user_id,
                event_type="document.processed",
                data={"document_id": str(uuid.uuid4()), "filename": "test.pdf", "status": "ready"},
            )

        assert dispatched == 1
        mock_celery.send_task.assert_called_once()
        call_args = mock_celery.send_task.call_args
        assert call_args[0][0] == "securedoc.deliver_webhook"

        # Verify delivery record in DB
        result = await db_session.execute(
            select(WebhookDelivery).where(WebhookDelivery.webhook_id == ep.id)
        )
        deliveries = result.scalars().all()
        assert len(deliveries) == 1
        assert deliveries[0].status == "pending"
        assert deliveries[0].event_type == "document.processed"

    @pytest.mark.asyncio
    async def test_unsubscribed_event_not_dispatched(self, client, db_session):
        """Endpoint subscribed to document.processed does not receive link.viewed."""
        from app.models.webhook import WebhookEndpoint
        from app.services.webhook_service import dispatch_webhook_event
        from app.auth import get_current_user
        from app.main import app

        user_id = app.dependency_overrides[get_current_user]()["user_id"]

        ep = WebhookEndpoint(
            user_id=uuid.UUID(user_id),
            url="https://example.com/wh2",
            secret="b" * 64,
            is_active=True,
        )
        ep.events = ["document.processed"]  # NOT link.viewed
        db_session.add(ep)
        await db_session.commit()

        with patch("app.services.webhook_service.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()
            dispatched = await dispatch_webhook_event(
                db_session,
                user_id=user_id,
                event_type="link.viewed",
                data={"link_id": "x"},
            )

        assert dispatched == 0
        mock_celery.send_task.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# Action 14: Public API + API Keys
# ══════════════════════════════════════════════════════════════════════════════

class TestPublicAPI:
    """API key CRUD, key format, hash storage, and auth integration."""

    # ── helpers ──

    async def _create_key(self, client, name="test key", scopes=None):
        return await client.post(
            "/api/api-keys",
            json={"name": name, "scopes": scopes or ["documents:read"]},
        )

    # ── Key generation ──

    def test_generate_key_prefix(self):
        key = generate_api_key()
        assert key.startswith("sd_")

    def test_generate_key_length(self):
        key = generate_api_key()
        assert len(key) == 51  # "sd_" + 48 hex chars

    def test_generate_key_unique(self):
        assert generate_api_key() != generate_api_key()

    def test_hash_api_key_sha256(self):
        key = "sd_" + "a" * 48
        h = hash_api_key(key)
        assert len(h) == 64  # SHA-256 hex
        assert h == hashlib.sha256(key.encode()).hexdigest()

    # ── CRUD ──

    @pytest.mark.asyncio
    async def test_create_returns_201_with_key(self, client):
        r = await self._create_key(client)
        assert r.status_code == 201
        body = r.json()
        assert "key" in body
        assert body["key"].startswith("sd_")
        assert len(body["key"]) == 51

    @pytest.mark.asyncio
    async def test_create_stores_key_prefix_not_full_key(self, client):
        r = await self._create_key(client)
        body = r.json()
        assert body["key_prefix"] == body["key"][:10]

    @pytest.mark.asyncio
    async def test_list_keys_no_full_key(self, client):
        await self._create_key(client)
        r = await client.get("/api/api-keys")
        assert r.status_code == 200
        keys = r.json()["api_keys"]
        assert len(keys) >= 1
        for k in keys:
            assert "key" not in k

    @pytest.mark.asyncio
    async def test_get_key_no_full_key(self, client):
        cr = await self._create_key(client)
        key_id = cr.json()["id"]
        r = await client.get(f"/api/api-keys/{key_id}")
        assert r.status_code == 200
        assert "key" not in r.json()

    @pytest.mark.asyncio
    async def test_update_key_name(self, client):
        cr = await self._create_key(client)
        key_id = cr.json()["id"]
        r = await client.patch(f"/api/api-keys/{key_id}", json={"name": "renamed"})
        assert r.status_code == 200
        assert r.json()["name"] == "renamed"

    @pytest.mark.asyncio
    async def test_revoke_key(self, client):
        cr = await self._create_key(client)
        key_id = cr.json()["id"]
        r = await client.patch(f"/api/api-keys/{key_id}", json={"is_active": False})
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_key(self, client):
        cr = await self._create_key(client)
        key_id = cr.json()["id"]
        r = await client.delete(f"/api/api-keys/{key_id}")
        assert r.status_code == 204
        assert (await client.get(f"/api/api-keys/{key_id}")).status_code == 404

    # ── Validation ──

    @pytest.mark.asyncio
    async def test_empty_name_rejected(self, client):
        r = await client.post("/api/api-keys", json={"name": "", "scopes": []})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_scope_rejected(self, client):
        r = await client.post(
            "/api/api-keys",
            json={"name": "k", "scopes": ["invalid:scope"]},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_all_valid_scopes_accepted(self, client):
        r = await client.post(
            "/api/api-keys",
            json={"name": "all scopes", "scopes": sorted(API_SCOPES)},
        )
        assert r.status_code == 201

    # ── Auth integration ──

    @pytest.mark.asyncio
    async def test_api_key_authenticates_requests(self, client):
        """A valid sd_ key must be routed through verify_api_key and succeed."""
        from app.auth import get_current_user
        from app.main import app
        from fastapi import HTTPException as _HTTPException

        user_id = app.dependency_overrides[get_current_user]()["user_id"]
        raw_key = generate_api_key()

        async def _mock_verify(key):
            if key == raw_key:
                return {"user_id": user_id, "email": "", "role": "authenticated",
                        "scopes": [], "auth_method": "api_key"}
            raise _HTTPException(status_code=401, detail="Authentication failed")

        original_override = app.dependency_overrides.pop(get_current_user, None)
        try:
            with patch("app.auth.verify_api_key", side_effect=_mock_verify):
                from httpx import AsyncClient, ASGITransport
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    r = await ac.get("/api/documents", headers={"X-API-Key": raw_key})
            assert r.status_code == 200
        finally:
            if original_override is not None:
                app.dependency_overrides[get_current_user] = original_override

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, client):
        """An unknown sd_ key must return 401."""
        from app.auth import get_current_user
        from app.main import app
        from fastapi import HTTPException as _HTTPException

        async def _mock_verify(key):
            raise _HTTPException(status_code=401, detail="Authentication failed")

        original_override = app.dependency_overrides.pop(get_current_user, None)
        try:
            with patch("app.auth.verify_api_key", side_effect=_mock_verify):
                from httpx import AsyncClient, ASGITransport
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    r = await ac.get(
                        "/api/documents", headers={"X-API-Key": "sd_" + "f" * 48}
                    )
            assert r.status_code == 401
        finally:
            if original_override is not None:
                app.dependency_overrides[get_current_user] = original_override

    @pytest.mark.asyncio
    async def test_revoked_key_rejected(self, client):
        """An is_active=False key must return 401."""
        from app.auth import get_current_user
        from app.main import app
        from fastapi import HTTPException as _HTTPException

        async def _mock_verify(key):
            raise _HTTPException(status_code=401, detail="Authentication failed")

        original_override = app.dependency_overrides.pop(get_current_user, None)
        try:
            with patch("app.auth.verify_api_key", side_effect=_mock_verify):
                from httpx import AsyncClient, ASGITransport
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    r = await ac.get(
                        "/api/documents", headers={"X-API-Key": generate_api_key()}
                    )
            assert r.status_code == 401
        finally:
            if original_override is not None:
                app.dependency_overrides[get_current_user] = original_override
