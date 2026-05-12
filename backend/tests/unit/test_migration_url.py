"""Migration URL resolver tests.

Verifies _resolve_migration_url() precedence and safety guard:
  - MIGRATION_DATABASE_URL wins over everything
  - DATABASE_PUBLIC_URL is chosen when running outside Railway
  - On Railway (RAILWAY_ENVIRONMENT set), DATABASE_URL is used regardless
  - .railway.internal host raises RuntimeError outside Railway
  - .railway.internal host is allowed when on Railway
  - All resolved URLs are normalized to postgresql+asyncpg://
"""
import pytest
from unittest.mock import MagicMock, patch

from app.database import _resolve_migration_url, _normalize_db_url


_INTERNAL = "postgresql://user:pass@postgres.railway.internal:5432/railway"
_PUBLIC   = "postgresql://user:pass@roundhouse.proxy.rlwy.net:12345/railway"
_OVERRIDE = "postgresql://user:pass@migration-override.example.com:5432/db"
_LOCAL    = "postgresql+asyncpg://securedoc:password@localhost:5432/securedoc"


def _mock_settings(*, migration_url=None, public_url=None, db_url=_INTERNAL):
    m = MagicMock()
    m.migration_database_url = migration_url
    m.database_public_url = public_url
    m.database_url = db_url
    return m


class TestResolveMigrationUrl:

    def test_explicit_override_wins_over_all(self, monkeypatch):
        """MIGRATION_DATABASE_URL beats public URL and DATABASE_URL."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        mock_s = _mock_settings(migration_url=_OVERRIDE, public_url=_PUBLIC)
        with patch("app.database.settings", mock_s):
            url = _resolve_migration_url()
        assert url == _normalize_db_url(_OVERRIDE)

    def test_explicit_override_beats_railway_url_too(self, monkeypatch):
        """MIGRATION_DATABASE_URL also wins when running inside Railway."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        mock_s = _mock_settings(migration_url=_OVERRIDE, db_url=_INTERNAL)
        with patch("app.database.settings", mock_s):
            url = _resolve_migration_url()
        assert url == _normalize_db_url(_OVERRIDE)

    def test_public_url_used_outside_railway(self, monkeypatch):
        """DATABASE_PUBLIC_URL is chosen when RAILWAY_ENVIRONMENT is absent."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        mock_s = _mock_settings(public_url=_PUBLIC, db_url=_INTERNAL)
        with patch("app.database.settings", mock_s):
            url = _resolve_migration_url()
        assert url == _normalize_db_url(_PUBLIC)

    def test_public_url_ignored_on_railway(self, monkeypatch):
        """On Railway, DATABASE_URL is used even when DATABASE_PUBLIC_URL is set."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        mock_s = _mock_settings(public_url=_PUBLIC, db_url=_INTERNAL)
        with patch("app.database.settings", mock_s):
            url = _resolve_migration_url()
        assert url == _normalize_db_url(_INTERNAL)

    def test_falls_back_to_database_url_when_no_public_url(self, monkeypatch):
        """Without a public URL or override, DATABASE_URL is used (non-internal host)."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        mock_s = _mock_settings(db_url=_LOCAL)
        with patch("app.database.settings", mock_s):
            url = _resolve_migration_url()
        assert url == _normalize_db_url(_LOCAL)

    def test_internal_host_rejected_outside_railway(self, monkeypatch):
        """Raises RuntimeError when DATABASE_URL is Railway-internal and we're outside Railway."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        mock_s = _mock_settings(db_url=_INTERNAL)
        with patch("app.database.settings", mock_s):
            with pytest.raises(RuntimeError, match="railway.internal"):
                _resolve_migration_url()

    def test_internal_host_allowed_on_railway(self, monkeypatch):
        """No error when RAILWAY_ENVIRONMENT is set, even with internal hostname."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        mock_s = _mock_settings(db_url=_INTERNAL)
        with patch("app.database.settings", mock_s):
            url = _resolve_migration_url()
        assert ".railway.internal" in url

    def test_error_message_contains_fix_instructions(self, monkeypatch):
        """RuntimeError message tells user exactly what to do."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        mock_s = _mock_settings(db_url=_INTERNAL)
        with patch("app.database.settings", mock_s):
            with pytest.raises(RuntimeError) as exc_info:
                _resolve_migration_url()
        msg = str(exc_info.value)
        assert "DATABASE_PUBLIC_URL" in msg
        assert "migrate-railway" in msg

    def test_public_url_normalized_to_asyncpg(self, monkeypatch):
        """DATABASE_PUBLIC_URL is rewritten from postgres:// to postgresql+asyncpg://."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        mock_s = _mock_settings(public_url="postgres://user:pass@host:5432/db")
        with patch("app.database.settings", mock_s):
            url = _resolve_migration_url()
        assert url.startswith("postgresql+asyncpg://")

    def test_override_url_normalized_to_asyncpg(self, monkeypatch):
        """MIGRATION_DATABASE_URL is also rewritten to asyncpg dialect."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        mock_s = _mock_settings(migration_url="postgres://user:pass@host:5432/db")
        with patch("app.database.settings", mock_s):
            url = _resolve_migration_url()
        assert url.startswith("postgresql+asyncpg://")

    def test_database_url_normalized_on_railway(self, monkeypatch):
        """DATABASE_URL with postgres:// scheme is normalized even when on Railway."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        raw = "postgres://user:pass@postgres.railway.internal:5432/railway"
        mock_s = _mock_settings(db_url=raw)
        with patch("app.database.settings", mock_s):
            url = _resolve_migration_url()
        assert url.startswith("postgresql+asyncpg://")
        assert "psycopg2" not in url
