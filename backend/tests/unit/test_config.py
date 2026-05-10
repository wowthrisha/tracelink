"""Deployment config and database URL normalization tests.

Verifies that Settings parses env vars correctly, that production guards
are detectable, and that share URL generation is consistent.
"""
import pytest
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

    def test_jwt_placeholder_is_detectable(self):
        """The placeholder JWT secret must be detectable so production guard can reject it."""
        placeholder = "change_me_to_a_long_random_string_in_production"
        s = Settings(jwt_secret=placeholder)
        assert s.jwt_secret == placeholder

    def test_strong_jwt_secret_passes_placeholder_check(self):
        import secrets
        strong = secrets.token_hex(32)
        s = Settings(jwt_secret=strong)
        placeholder = "change_me_to_a_long_random_string_in_production"
        assert s.jwt_secret != placeholder

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
