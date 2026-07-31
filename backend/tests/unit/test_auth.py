"""Unit tests for app/auth.py — Supabase JWKS JWT authentication."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
from fastapi import HTTPException

from app.auth import get_current_user

TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_EMAIL = "user@example.com"

_VALID_HEADER = {"alg": "ES256", "kid": "test-kid"}
_VALID_PAYLOAD = {"sub": TEST_USER_ID, "email": TEST_EMAIL, "role": "authenticated"}


class TestGetCurrentUser:

    @pytest.mark.asyncio
    async def test_valid_token_returns_dict(self):
        with patch("app.auth.jwt.get_unverified_header", return_value=_VALID_HEADER), \
             patch("app.auth._get_public_key", new_callable=AsyncMock, return_value=MagicMock()), \
             patch("app.auth.jwt.decode", return_value=_VALID_PAYLOAD):
            user = await get_current_user("Bearer valid.token")
        assert user["user_id"] == TEST_USER_ID
        assert user["email"] == TEST_EMAIL

    @pytest.mark.asyncio
    async def test_missing_header_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_scheme_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("Basic validtoken")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        with patch("app.auth.jwt.get_unverified_header", side_effect=pyjwt.DecodeError("bad")):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("Bearer not.a.valid.token")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self):
        with patch("app.auth.jwt.get_unverified_header", return_value=_VALID_HEADER), \
             patch("app.auth._get_public_key", new_callable=AsyncMock, return_value=MagicMock()), \
             patch("app.auth.jwt.decode", side_effect=pyjwt.ExpiredSignatureError("Expired")):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("Bearer expired.token")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_unsupported_algorithm_raises_401(self):
        with patch("app.auth.jwt.get_unverified_header", return_value={"alg": "HS256", "kid": "x"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("Bearer some.token.here")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_after_jwks_refresh_raises_401(self):
        with patch("app.auth.jwt.get_unverified_header", return_value=_VALID_HEADER), \
             patch("app.auth._get_public_key", new_callable=AsyncMock, return_value=MagicMock()), \
             patch("app.auth._fetch_jwks", new_callable=AsyncMock), \
             patch("app.auth.jwt.decode", side_effect=pyjwt.InvalidTokenError("bad")):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("Bearer rotated.token")
        assert exc_info.value.status_code == 401
