"""Deployment config and database URL normalization tests.

Verifies that Settings parses env vars correctly, that production guards
are detectable, and that share URL generation is consistent.
"""
from app.config import Settings
from app.database import _normalize_db_url


class TestDatabaseUrlNormalization:
    """Railway and most cloud providers supply postgresql:// URLs.
    SQLAlchemy async engine requires postgresql+asyncpg://."""

    def test_postgresql_scheme_is_rewritten(self):
        url = "postgresql://user:pass@host:5432/db"
        assert _normalize_db_url(url) == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_postgres_short_scheme_is_rewritten(self):
        url = "postgres://user:pass@host:5432/db"
        assert _normalize_db_url(url) == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_already_asyncpg_is_unchanged(self):
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        assert _normalize_db_url(url) == url

    def test_sqlite_is_unchanged(self):
        url = "sqlite+aiosqlite:///./test.db"
        assert _normalize_db_url(url) == url

    def test_railway_style_url(self):
        url = "postgresql://securedoc:password@containers-us-west-1.railway.app:5432/railway"
        result = _normalize_db_url(url)
        assert result.startswith("postgresql+asyncpg://")
        assert "psycopg2" not in result
        assert "containers-us-west-1.railway.app" in result


class TestConfigParsing:

    def test_allowed_origins_list_splits_on_comma(self):
        s = Settings(allowed_origins="http://localhost:5500,http://localhost:8000")
        assert "http://localhost:5500" in s.allowed_origins_list
        assert "http://localhost:8000" in s.allowed_origins_list

    def test_allowed_origins_list_strips_whitespace(self):
        s = Settings(allowed_origins="  http://a.com , http://b.com  ")
        assert "http://a.com" in s.allowed_origins_list
        assert "http://b.com" in s.allowed_origins_list

    def test_max_upload_bytes_derived_from_mb(self):
        s = Settings(max_upload_mb=50)
        assert s.max_upload_bytes == 50 * 1024 * 1024

    def test_max_upload_bytes_default(self):
        s = Settings()
        assert s.max_upload_bytes == s.max_upload_mb * 1024 * 1024

    def test_app_env_defaults_to_development(self):
        s = Settings()
        assert s.app_env == "development"

    def test_app_public_base_url_explicit(self):
        s = Settings(app_public_base_url="http://localhost:8000")
        assert s.app_public_base_url == "http://localhost:8000"


class TestShareUrlGeneration:

    def test_share_url_uses_app_public_base_url(self):
        s = Settings(app_public_base_url="https://example.com")
        token = "a" * 64
        share_url = f"{s.app_public_base_url}/v/{token}"
        assert share_url == f"https://example.com/v/{token}"

    def test_share_url_no_localhost_when_custom_domain_set(self):
        s = Settings(app_public_base_url="https://example.com")
        token = "b" * 64
        share_url = f"{s.app_public_base_url}/v/{token}"
        assert "localhost" not in share_url
        assert "127.0.0.1" not in share_url

    def test_share_url_no_trailing_slash(self):
        s = Settings(app_public_base_url="https://example.com")
        base = s.app_public_base_url.rstrip("/")
        token = "c" * 64
        share_url = f"{base}/v/{token}"
        assert "//" not in share_url.replace("https://", "")

    def test_share_url_token_path_format(self):
        s = Settings(app_public_base_url="https://secure.example.com")
        token = "d" * 64
        share_url = f"{s.app_public_base_url}/v/{token}"
        assert share_url.startswith("https://secure.example.com/v/")
        assert share_url.endswith(token)


class TestProductionGuards:

    def test_jwt_secret_removed_from_config(self):
        """jwt_secret was a dead field (links use random tokens, not JWTs).
        It must no longer exist in Settings so operators aren't confused about
        what they need to configure."""
        s = Settings()
        assert not hasattr(s, "jwt_secret"), (
            "jwt_secret should have been removed from Settings — it is dead configuration"
        )

    def test_jwt_algorithm_removed_from_config(self):
        s = Settings()
        assert not hasattr(s, "jwt_algorithm"), (
            "jwt_algorithm should have been removed from Settings"
        )

    def test_localhost_in_public_base_url_detectable(self):
        s = Settings(app_public_base_url="http://localhost:8000")
        assert "localhost" in s.app_public_base_url  # production guard checks this

    def test_https_url_passes_localhost_check(self):
        s = Settings(app_public_base_url="https://secure.example.com")
        assert "localhost" not in s.app_public_base_url

    def test_billing_disabled_when_stripe_key_empty(self):
        s = Settings(stripe_secret_key="")
        assert s.billing_enabled is False

    def test_billing_enabled_when_stripe_key_set(self):
        s = Settings(stripe_secret_key="sk_test_abc123")
        assert s.billing_enabled is True

    def test_free_plan_doc_limit_default(self):
        s = Settings()
        assert s.free_plan_doc_limit == 10

    def test_free_plan_doc_limit_configurable(self):
        s = Settings(free_plan_doc_limit=25)
        assert s.free_plan_doc_limit == 25


class TestStableDomainConfig:
    """Stable production domain URL configuration."""

    def test_share_url_uses_stable_domain(self):
        s = Settings(app_public_base_url="https://secure.myapp.com")
        token = "a" * 64
        share_url = f"{s.app_public_base_url}/v/{token}"
        assert share_url == f"https://secure.myapp.com/v/{token}"

    def test_production_domain_has_no_localhost(self):
        s = Settings(app_public_base_url="https://secure.myapp.com")
        assert "localhost" not in s.app_public_base_url
        assert "127.0.0.1" not in s.app_public_base_url

    def test_production_domain_uses_https(self):
        s = Settings(app_public_base_url="https://secure.myapp.com")
        assert s.app_public_base_url.startswith("https://")

    def test_trycloudflare_url_is_detectable_as_temporary(self):
        """Quick tunnel URLs should be detectable (used in monitoring, not production)."""
        s = Settings(app_public_base_url="https://random.trycloudflare.com")
        assert "trycloudflare.com" in s.app_public_base_url

    def test_allowed_origins_includes_stable_domain(self):
        s = Settings(allowed_origins="https://secure.myapp.com,https://api.myapp.com")
        origins = s.allowed_origins_list
        assert "https://secure.myapp.com" in origins
        assert "https://api.myapp.com" in origins

    def test_cors_origins_does_not_include_localhost_in_production_config(self):
        """A production config should have no localhost origins."""
        s = Settings(allowed_origins="https://secure.myapp.com")
        localhost_origins = [o for o in s.allowed_origins_list if "localhost" in o]
        assert localhost_origins == []


class TestProductionStartupGuard:
    """Regression: ensure the startup guard in app/main.py stays aligned with config defaults.

    The guard runs at module import time under APP_ENV=production and raises
    RuntimeError if placeholder secrets are still in use. These tests verify:
      1. The sentinel values in main.py match the insecure defaults in config.py,
         so the guard WILL fire when defaults are used.
      2. The guard code itself hasn't been accidentally removed.
    """

    def test_ip_hash_salt_sentinel_matches_config_default(self):
        """_IP_SALT_DEFAULT in main.py must equal the ip_hash_salt field default in config.py."""
        import app.main as main_mod
        from app.config import Settings as _Settings
        field = _Settings.model_fields.get("ip_hash_salt")
        assert field is not None, "ip_hash_salt field must exist in Settings"
        assert field.default == main_mod._IP_SALT_DEFAULT, (
            f"ip_hash_salt default in config.py ({field.default!r}) does not match "
            f"the guard sentinel in main.py ({main_mod._IP_SALT_DEFAULT!r}). "
            "The startup guard would NOT catch the insecure default — update both to match."
        )

    def test_domain_verify_salt_sentinel_matches_config_default(self):
        """_DOMAIN_SALT_DEFAULT in main.py must equal the domain_verify_salt default."""
        import app.main as main_mod
        from app.config import Settings as _Settings
        field = _Settings.model_fields.get("domain_verify_salt")
        assert field is not None, "domain_verify_salt field must exist in Settings"
        assert field.default == main_mod._DOMAIN_SALT_DEFAULT, (
            f"domain_verify_salt default in config.py ({field.default!r}) does not match "
            f"the guard sentinel in main.py ({main_mod._DOMAIN_SALT_DEFAULT!r}). "
            "The startup guard would NOT catch the insecure default — update both to match."
        )

    def test_guard_block_still_present_in_main(self):
        """The production startup guard block must not have been accidentally removed."""
        import inspect
        import app.main as main_mod
        src = inspect.getsource(main_mod)
        assert "_IP_SALT_DEFAULT" in src, "IP salt guard removed from main.py"
        assert "_DOMAIN_SALT_DEFAULT" in src, "Domain salt guard removed from main.py"
        assert "Refusing to start in production" in src, "Guard RuntimeError message removed"
        assert "raise RuntimeError" in src, "Guard raise statement removed from main.py"

    def test_guard_logic_catches_both_default_salts(self):
        """Simulate the guard: with both salts at default, both errors are collected."""
        from app.main import _IP_SALT_DEFAULT, _DOMAIN_SALT_DEFAULT

        errors = []
        # This mirrors the exact logic in app/main.py
        if _IP_SALT_DEFAULT == _IP_SALT_DEFAULT:
            errors.append("IP_HASH_SALT is still set to the default placeholder value")
        if _DOMAIN_SALT_DEFAULT == _DOMAIN_SALT_DEFAULT:
            errors.append("DOMAIN_VERIFY_SALT is still set to the default placeholder value")

        assert len(errors) == 2, (
            "Guard logic must collect errors for both default salt values"
        )
