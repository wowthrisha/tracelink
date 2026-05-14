"""
Tests for migrate.py — the advisory-lock migration runner.

These tests mock asyncpg and subprocess so they run without a live database.
They verify:
  1. SQLite DATABASE_URL bypasses the advisory lock and calls alembic directly.
  2. PostgreSQL DATABASE_URL acquires pg_advisory_lock before running alembic.
  3. pg_advisory_unlock is called in the finally block (even on alembic failure).
  4. When the advisory lock is unavailable, alembic is still called (fallback).
  5. The URL conversion strips the +asyncpg dialect tag for asyncpg.connect().
  6. Exit code from alembic subprocess is propagated.
"""
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# migrate.py lives at the repo root (backend/), importable as `migrate`
# when PYTHONPATH=. (the standard test invocation).
import migrate as m


class TestToAsyncpgUrl:
    """_to_asyncpg_url strips SQLAlchemy dialect tags."""

    def test_strips_asyncpg_dialect(self):
        assert m._to_asyncpg_url(
            "postgresql+asyncpg://user:pass@host:5432/db"
        ) == "postgresql://user:pass@host:5432/db"

    def test_strips_postgres_scheme(self):
        assert m._to_asyncpg_url(
            "postgres://user:pass@host:5432/db"
        ) == "postgresql://user:pass@host:5432/db"

    def test_passthrough_plain_postgresql(self):
        url = "postgresql://user:pass@host:5432/db"
        assert m._to_asyncpg_url(url) == url

    def test_passthrough_unknown_scheme(self):
        url = "mysql://user:pass@host/db"
        assert m._to_asyncpg_url(url) == url


class TestSqlitePath:
    """SQLite DATABASE_URL must bypass advisory lock."""

    def test_sqlite_calls_alembic_directly(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        with patch("migrate.subprocess.run", mock_run):
            with pytest.raises(SystemExit) as exc_info:
                m.main()
        assert exc_info.value.code == 0
        mock_run.assert_called_once_with(["alembic", "upgrade", "head"])

    def test_empty_database_url_treated_as_sqlite(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "")
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        with patch("migrate.subprocess.run", mock_run):
            with pytest.raises(SystemExit) as exc_info:
                m.main()
        assert exc_info.value.code == 0
        mock_run.assert_called_once_with(["alembic", "upgrade", "head"])

    def test_sqlite_propagates_nonzero_exit_code(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
        mock_run = MagicMock(return_value=MagicMock(returncode=1))
        with patch("migrate.subprocess.run", mock_run):
            with pytest.raises(SystemExit) as exc_info:
                m.main()
        assert exc_info.value.code == 1


class TestAdvisoryLockPath:
    """PostgreSQL DATABASE_URL must use advisory lock."""

    def _make_mock_conn(self):
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        conn.close = AsyncMock(return_value=None)
        return conn

    @pytest.mark.asyncio
    async def test_lock_acquired_before_alembic(self):
        conn = self._make_mock_conn()
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        with patch("asyncpg.connect", AsyncMock(return_value=conn)), \
             patch("migrate.subprocess.run", mock_run):
            rc = await m._run_with_advisory_lock(
                "postgresql://user:pass@localhost/db"
            )
        assert rc == 0
        # Lock acquired
        conn.execute.assert_any_call(f"SELECT pg_advisory_lock({m._LOCK_KEY})")
        # Alembic ran
        mock_run.assert_called_once_with(["alembic", "upgrade", "head"])
        # Lock released
        conn.execute.assert_any_call(f"SELECT pg_advisory_unlock({m._LOCK_KEY})")

    @pytest.mark.asyncio
    async def test_lock_released_even_when_alembic_fails(self):
        """pg_advisory_unlock must be called in the finally block."""
        conn = self._make_mock_conn()
        mock_run = MagicMock(return_value=MagicMock(returncode=1))
        with patch("asyncpg.connect", AsyncMock(return_value=conn)), \
             patch("migrate.subprocess.run", mock_run):
            rc = await m._run_with_advisory_lock(
                "postgresql://user:pass@localhost/db"
            )
        assert rc == 1
        conn.execute.assert_any_call(f"SELECT pg_advisory_unlock({m._LOCK_KEY})")

    @pytest.mark.asyncio
    async def test_connection_closed_in_finally(self):
        conn = self._make_mock_conn()
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        with patch("asyncpg.connect", AsyncMock(return_value=conn)), \
             patch("migrate.subprocess.run", mock_run):
            await m._run_with_advisory_lock("postgresql://user:pass@localhost/db")
        conn.close.assert_awaited_once()

    def test_main_postgres_uses_advisory_lock(self, monkeypatch):
        """main() routes PostgreSQL URLs through _run_with_advisory_lock."""
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db"
        )
        mock_run_with_lock = AsyncMock(return_value=0)
        with patch("migrate._run_with_advisory_lock", mock_run_with_lock):
            with pytest.raises(SystemExit) as exc_info:
                m.main()
        assert exc_info.value.code == 0
        mock_run_with_lock.assert_awaited_once()


class TestFallbackBehavior:
    """When the advisory lock itself fails, alembic still runs."""

    def test_lock_failure_falls_back_to_direct_alembic(self, monkeypatch):
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db"
        )

        async def _raise(*args, **kwargs):
            raise ConnectionRefusedError("DB not ready")

        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        with patch("migrate._run_with_advisory_lock", _raise), \
             patch("migrate.subprocess.run", mock_run):
            with pytest.raises(SystemExit) as exc_info:
                m.main()

        # Alembic must still be called despite lock failure
        mock_run.assert_called_once_with(["alembic", "upgrade", "head"])
        assert exc_info.value.code == 0


class TestLockKeyIsStable:
    """The advisory lock key must be a fixed constant."""

    def test_lock_key_unchanged(self):
        assert m._LOCK_KEY == 7_325_613
