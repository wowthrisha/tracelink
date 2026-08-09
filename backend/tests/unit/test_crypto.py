from app.utils.crypto import hash_password, verify_password, hash_value, mask_email


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


class TestMaskEmail:

    def test_standard_email_masked(self):
        assert mask_email("user@example.com") == "u***@example.com"

    def test_short_local_part_masked(self):
        assert mask_email("a@b.com") == "a***@b.com"

    def test_subdomain_preserved(self):
        assert mask_email("student@psgtech.ac.in") == "s***@psgtech.ac.in"

    def test_uppercase_input_preserved_in_domain(self):
        # masking does not force lowercase — caller normalises before passing
        assert mask_email("User@Example.COM") == "U***@Example.COM"

    def test_no_at_sign_returned_unchanged(self):
        assert mask_email("notanemail") == "notanemail"

    def test_empty_string_returned_unchanged(self):
        assert mask_email("") == ""

    def test_masked_form_contains_at(self):
        result = mask_email("alice@corp.io")
        assert "@" in result

    def test_masked_form_hides_local_beyond_first_char(self):
        result = mask_email("alice@corp.io")
        # Domain must be intact; full local part must not appear
        assert "corp.io" in result
        assert "lice" not in result

    def test_first_char_of_local_preserved(self):
        result = mask_email("alice@corp.io")
        assert result.startswith("a***@")
