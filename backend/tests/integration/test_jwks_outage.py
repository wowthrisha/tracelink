"""Regression tests for the Supabase JWKS-outage incident.

Production symptom: GET /api/documents (and every other JWT-gated route)
returned HTTP 500 with `httpcore.ConnectError: Name or service not known`
whenever the Supabase JWKS endpoint (`{SUPABASE_URL}/auth/v1/.well-known/
jwks.json`) was unreachable — the fetch in app.auth had no error handling,
so the raw httpx exception propagated to FastAPI's generic 500 handler.

These tests assert the fix: an unreachable JWKS endpoint degrades to a
clean 503 (or transparently serves from a stale cache) and never surfaces
as an unhandled 500.
"""
import base64
import json
import time

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

import app.auth as auth_module
from app.database import get_db
from app.main import app

TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


def _b64url(data: dict) -> str:
    raw = json.dumps(data).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _fake_jwt(alg: str = "ES256", kid: str = "test-kid") -> str:
    """A compact JWT with a well-formed header/payload but no real signature.

    Sufficient for these tests: the connect-error path is triggered while
    fetching the *public key*, before signature verification ever runs.
    """
    header = _b64url({"alg": alg, "kid": kid, "typ": "JWT"})
    payload = _b64url({"sub": TEST_USER_ID, "email": "user@example.com", "role": "authenticated"})
    signature = base64.urlsafe_b64encode(b"fakesignature").rstrip(b"=").decode()
    return f"{header}.{payload}.{signature}"


@pytest.fixture(autouse=True)
def _isolate_jwks_cache():
    """Module-level JWKS cache must not leak state between tests."""
    saved_cache = dict(auth_module._jwks_cache)
    saved_fetched_at = auth_module._jwks_fetched_at
    auth_module._jwks_cache.clear()
    auth_module._jwks_fetched_at = 0.0
    yield
    auth_module._jwks_cache.clear()
    auth_module._jwks_cache.update(saved_cache)
    auth_module._jwks_fetched_at = saved_fetched_at


@pytest_asyncio.fixture
async def unauthenticated_client(db_session):
    """Unlike the shared `client` fixture, this does NOT override
    get_current_user — requests go through the real JWKS/JWT verification
    path, which is what these regression tests need to exercise."""
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


_CONNECT_ERROR = httpx.ConnectError(
    "[Errno 8] nodename nor servname provided, or not known"
)


class TestJWKSFetchErrorHandling:

    @pytest.mark.asyncio
    async def test_fetch_jwks_raises_typed_error_on_dns_failure(self):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_CONNECT_ERROR):
            with pytest.raises(auth_module.JWKSUnavailableError):
                await auth_module._fetch_jwks()

    @pytest.mark.asyncio
    async def test_get_public_key_returns_503_with_no_cache(self):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_CONNECT_ERROR):
            with pytest.raises(HTTPException) as exc_info:
                await auth_module._get_public_key("test-kid")
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_get_public_key_falls_back_to_stale_cache(self):
        sentinel_key = object()
        auth_module._jwks_cache["test-kid"] = sentinel_key
        auth_module._jwks_fetched_at = time.time() - auth_module._JWKS_TTL - 1  # force a refresh attempt

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_CONNECT_ERROR):
            key = await auth_module._get_public_key("test-kid")
        assert key is sentinel_key

    @pytest.mark.asyncio
    async def test_get_current_user_returns_503_not_500_when_supabase_unreachable(self):
        token = _fake_jwt()
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_CONNECT_ERROR):
            with pytest.raises(HTTPException) as exc_info:
                await auth_module.get_current_user(f"Bearer {token}")
        assert exc_info.value.status_code == 503
        assert exc_info.value.status_code != 500


class TestDocumentsEndpointDuringOutage:
    """End-to-end reproduction of the reported production incident."""

    @pytest.mark.asyncio
    async def test_list_documents_returns_503_not_500(self, unauthenticated_client):
        # Patched at the app.auth._fetch_jwks boundary (not httpx.AsyncClient.get)
        # because the test client itself is an httpx.AsyncClient over ASGITransport —
        # patching the raw transport method would intercept the test's own request too.
        token = _fake_jwt()
        with patch(
            "app.auth._fetch_jwks",
            new_callable=AsyncMock,
            side_effect=auth_module.JWKSUnavailableError("Could not reach Supabase: DNS failure"),
        ):
            resp = await unauthenticated_client.get(
                "/api/documents", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 503
        assert resp.status_code != 500
        body = resp.json()
        assert "detail" in body
        assert "Internal Server Error" not in body["detail"]

    @pytest.mark.asyncio
    async def test_list_documents_succeeds_on_warm_cache_despite_outage(self, unauthenticated_client):
        """A fresh (non-expired) JWKS cache — e.g. loaded at startup before
        the outage began — must keep serving requests without ever touching
        the network, so a transient Supabase blip doesn't disrupt live traffic."""
        auth_module._jwks_cache["test-kid"] = object()
        auth_module._jwks_fetched_at = time.time()  # fresh — no refetch needed

        token = _fake_jwt()
        fake_payload = {"sub": TEST_USER_ID, "email": "user@example.com", "role": "authenticated"}
        with patch("app.auth.jwt.decode", return_value=fake_payload), \
             patch(
                 "app.auth._fetch_jwks",
                 new_callable=AsyncMock,
                 side_effect=AssertionError("must not hit the network when the JWKS cache is warm"),
             ):
            resp = await unauthenticated_client.get(
                "/api/documents", headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200
        assert resp.json() == {"documents": []}
