"""Billing system tests.

Covers:
  - Status endpoint returns current plan
  - Checkout session creation (mocked Stripe)
  - Webhook updates subscription status
  - Webhook rejects invalid signatures
  - Feature gating: free plan document limit
  - Unauthorized access denied
"""
import json
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models.billing import UserBilling, PLAN_FREE, PLAN_PRO
from app.models.document import Document
from tests.conftest import TEST_USER_ID


# ── helpers ────────────────────────────────────────────────────────────────

USER_UUID = uuid.UUID(TEST_USER_ID)


async def _make_billing(db_session, user_id=TEST_USER_ID, plan=PLAN_FREE, status="inactive") -> UserBilling:
    billing = UserBilling(
        user_id=uuid.UUID(user_id),
        plan=plan,
        subscription_status=status,
        stripe_customer_id="cus_test_123" if plan == PLAN_PRO else None,
    )
    db_session.add(billing)
    await db_session.commit()
    await db_session.refresh(billing)
    return billing


async def _make_doc(db_session, user_id=TEST_USER_ID) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=1,
        file_size_bytes=512,
        user_id=uuid.UUID(user_id),
    )
    db_session.add(doc)
    await db_session.commit()
    return doc


# ══════════════════════════════════════════════════════════════════════════
# 1. STATUS ENDPOINT
# ══════════════════════════════════════════════════════════════════════════

class TestBillingStatus:

    @pytest.mark.asyncio
    async def test_status_returns_free_plan_by_default(self, client, db_session):
        r = await client.get("/api/billing/status")
        assert r.status_code == 200
        data = r.json()
        assert data["plan"] == PLAN_FREE

    @pytest.mark.asyncio
    async def test_status_returns_pro_plan_when_subscribed(self, client, db_session):
        await _make_billing(db_session, plan=PLAN_PRO, status="active")

        r = await client.get("/api/billing/status")
        assert r.status_code == 200
        assert r.json()["plan"] == PLAN_PRO

    @pytest.mark.asyncio
    async def test_status_creates_billing_row_if_missing(self, client, db_session):
        r = await client.get("/api/billing/status")
        assert r.status_code == 200

        from sqlalchemy import select
        result = await db_session.execute(
            select(UserBilling).where(UserBilling.user_id == USER_UUID)
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_status_requires_auth(self, unauth_client):
        r = await unauth_client.get("/api/billing/status")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# 2. CHECKOUT SESSION
# ══════════════════════════════════════════════════════════════════════════

class TestCheckoutSession:

    @pytest.mark.asyncio
    async def test_checkout_returns_503_when_billing_not_configured(self, client, db_session):
        # settings.billing_enabled = bool(stripe_secret_key) — patch the key
        from unittest.mock import MagicMock
        mock_settings = MagicMock()
        mock_settings.billing_enabled = False
        mock_settings.stripe_secret_key = ""
        mock_settings.stripe_price_id_pro = ""
        with patch("app.routers.billing.settings", mock_settings):
            r = await client.post("/api/billing/checkout")
        assert r.status_code == 503

    @pytest.mark.asyncio
    async def test_checkout_returns_url_when_stripe_configured(self, client, db_session):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test/session"

        mock_customer = MagicMock()
        mock_customer.id = "cus_test_abc"

        mock_settings = MagicMock()
        mock_settings.billing_enabled = True
        mock_settings.stripe_secret_key = "sk_test_xxx"
        mock_settings.stripe_price_id_pro = "price_abc"
        mock_settings.app_public_base_url = "http://localhost:8000"

        with patch("app.routers.billing.settings", mock_settings), \
             patch("stripe.Customer.create", return_value=mock_customer), \
             patch("stripe.checkout.Session.create", return_value=mock_session):
            r = await client.post("/api/billing/checkout")

        assert r.status_code == 200
        assert r.json()["url"] == "https://checkout.stripe.com/test/session"

    @pytest.mark.asyncio
    async def test_checkout_requires_auth(self, unauth_client):
        r = await unauth_client.post("/api/billing/checkout")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# 3. WEBHOOK
# ══════════════════════════════════════════════════════════════════════════

class TestBillingWebhook:

    def _make_subscription_event(self, event_type: str, customer_id: str, status: str, sub_id="sub_test"):
        period_end = int(time.time()) + 2592000  # 30 days
        return {
            "type": event_type,
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": customer_id,
                    "status": status,
                    "current_period_end": period_end,
                }
            }
        }

    def _mock_billing_settings(self):
        m = MagicMock()
        m.billing_enabled = True
        m.stripe_secret_key = "sk_test_xxx"
        m.stripe_webhook_secret = "whsec_test"
        m.stripe_price_id_pro = "price_abc"
        m.app_public_base_url = "http://localhost:8000"
        return m

    @pytest.mark.asyncio
    async def test_webhook_rejects_invalid_signature(self, client, db_session):
        import stripe
        mock_settings = self._mock_billing_settings()
        with patch("app.routers.billing.settings", mock_settings), \
             patch("stripe.Webhook.construct_event",
                   side_effect=stripe.SignatureVerificationError("bad sig", None)):
            r = await client.post(
                "/api/billing/webhook",
                content=b'{"type":"test"}',
                headers={"stripe-signature": "invalid"},
            )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_upgrades_plan_on_subscription_active(self, client, db_session):
        billing = await _make_billing(db_session, plan=PLAN_FREE)
        billing.stripe_customer_id = "cus_upgrade_test"
        await db_session.commit()

        event = self._make_subscription_event(
            "customer.subscription.updated", "cus_upgrade_test", "active"
        )
        mock_settings = self._mock_billing_settings()
        with patch("app.routers.billing.settings", mock_settings), \
             patch("stripe.Webhook.construct_event", return_value=event):
            r = await client.post(
                "/api/billing/webhook",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "mocked"},
            )

        assert r.status_code == 200
        await db_session.refresh(billing)
        assert billing.plan == PLAN_PRO
        assert billing.subscription_status == "active"

    @pytest.mark.asyncio
    async def test_webhook_downgrades_plan_on_subscription_deleted(self, client, db_session):
        billing = await _make_billing(db_session, plan=PLAN_PRO, status="active")
        billing.stripe_customer_id = "cus_cancel_test"
        await db_session.commit()

        event = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_cancel_test", "id": "sub_del", "status": "canceled"}}
        }
        mock_settings = self._mock_billing_settings()
        with patch("app.routers.billing.settings", mock_settings), \
             patch("stripe.Webhook.construct_event", return_value=event):
            r = await client.post(
                "/api/billing/webhook",
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "mocked"},
            )

        assert r.status_code == 200
        await db_session.refresh(billing)
        assert billing.plan == PLAN_FREE
        assert billing.subscription_status == "canceled"


# ══════════════════════════════════════════════════════════════════════════
# 4. FEATURE GATING
# ══════════════════════════════════════════════════════════════════════════

class TestUploadQuotaGating:
    """Free plan users are blocked at the document limit.
    Tests call _check_upload_quota directly to avoid rate-limiter in upload endpoint.
    """

    @pytest.mark.asyncio
    async def test_free_user_raises_403_after_limit(self, db_session):
        from fastapi import HTTPException
        from app.routers.documents import _check_upload_quota
        from app.config import settings

        # Create docs up to the limit
        for _ in range(settings.free_plan_doc_limit):
            await _make_doc(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await _check_upload_quota(db_session, USER_UUID)
        assert exc_info.value.status_code == 403
        assert "Free plan" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_pro_user_not_blocked_after_limit(self, db_session):
        from app.routers.documents import _check_upload_quota
        from app.config import settings

        await _make_billing(db_session, plan=PLAN_PRO, status="active")
        for _ in range(settings.free_plan_doc_limit):
            await _make_doc(db_session)

        # Should not raise
        await _check_upload_quota(db_session, USER_UUID)

    @pytest.mark.asyncio
    async def test_free_user_allowed_within_limit(self, db_session):
        from app.routers.documents import _check_upload_quota

        # 0 docs — should not raise
        await _check_upload_quota(db_session, USER_UUID)

    @pytest.mark.asyncio
    async def test_zero_limit_means_unlimited(self, db_session):
        """free_plan_doc_limit=0 disables the limit entirely."""
        from app.routers.documents import _check_upload_quota

        for _ in range(100):
            await _make_doc(db_session)

        with patch("app.routers.documents.settings") as mock_settings:
            mock_settings.free_plan_doc_limit = 0
            # Should not raise
            await _check_upload_quota(db_session, USER_UUID)


# Need the unauth_client fixture from test_auth_enforcement
@pytest_asyncio.fixture
async def unauth_client(db_session):
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    from unittest.mock import AsyncMock, MagicMock
    with patch("app.services.storage.StorageService.upload_file", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.generate_presigned_url", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.download_bytes", new_callable=AsyncMock) as mock_dl, \
         patch("app.services.storage.StorageService.delete_file", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.list_keys_with_prefix", new_callable=AsyncMock), \
         patch("app.workers.tasks.process_document.delay") as mock_celery:
        from PIL import Image
        import io
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        mock_dl.return_value = buf.getvalue()
        mock_celery.return_value = MagicMock(id="fake-task-id")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()
