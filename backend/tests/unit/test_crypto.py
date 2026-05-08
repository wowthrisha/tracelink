import pytest
from app.utils.crypto import hash_password, verify_password, hash_value


class TestCrypto:

    def test_hash_password_produces_bcrypt_hash(self):
        hashed = hash_password("mysecret")
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("mysecret")
        assert verify_password("wrongpassword", hashed) is False

    def test_hash_value_is_hex_64_chars(self):
        result = hash_value("192.168.1.1")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_value_different_inputs_different_outputs(self):
        h1 = hash_value("192.168.1.1")
        h2 = hash_value("10.0.0.1")
        assert h1 != h2

    def test_hash_value_no_dots_or_colons(self):
        result = hash_value("192.168.1.1")
        assert "." not in result
        assert ":" not in result
