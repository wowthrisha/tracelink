from datetime import timedelta
import pytest
from app.utils.token import encode_token, decode_token, TokenExpiredError, TokenInvalidError


class TestTokenUtils:

    def test_encode_decode_roundtrip(self):
        payload = {"sub": "doc_123", "link_id": "link_456"}
        token = encode_token(payload)
        decoded = decode_token(token)
        assert decoded["sub"] == "doc_123"

    def test_expired_token_raises(self):
        token = encode_token({"sub": "x"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(TokenExpiredError):
            decode_token(token)

    def test_tampered_token_raises(self):
        token = encode_token({"sub": "x"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(TokenInvalidError):
            decode_token(tampered)
