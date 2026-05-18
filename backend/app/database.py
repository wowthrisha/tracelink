from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

import logging

_log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _normalize_db_url(url: str) -> str:
    """Rewrite plain postgres:// or postgresql:// to the asyncpg dialect.

    Railway (and most cloud providers) supply a standard postgresql:// URL.
    SQLAlchemy's async engine requires postgresql+asyncpg://.
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


def _resolve_migration_url() -> str:
    """Pick the right database URL for Alembic migrations.

    Precedence:
      1. MIGRATION_DATABASE_URL — explicit override, always wins.
      2. DATABASE_PUBLIC_URL    — used when running outside Railway (local Mac/CI).
      3. DATABASE_URL           — runtime URL; used inside Railway or as last resort.

    Safety guard: if the resolved host is a Railway-internal hostname
    (*.railway.internal) and RAILWAY_ENVIRONMENT is not set, raise an
    informative error rather than hanging on a DNS lookup that will never
    resolve outside Railway's private network.
    """
    import os

    on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))

    # 1. Explicit override
    if settings.migration_database_url:
        return _normalize_db_url(settings.migration_database_url)

    # 2. Public URL when running locally / outside Railway
    if not on_railway and settings.database_public_url:
        return _normalize_db_url(settings.database_public_url)

    # 3. Runtime URL
    normalized = _normalize_db_url(settings.database_url)

    # Guard: internal Railway hostnames are unreachable from outside Railway
    if not on_railway and ".railway.internal" in normalized:
        raise RuntimeError(
            "\n"
            "Migration target is a Railway-internal hostname "
            "(e.g. postgres.railway.internal).\n"
            "That hostname only resolves inside Railway's private network.\n\n"
            "Fix — add ONE of the following to backend/.env:\n"
            "  DATABASE_PUBLIC_URL=<Railway public Postgres URL>   # preferred\n"
            "  MIGRATION_DATABASE_URL=<any reachable Postgres URL>  # explicit override\n\n"
            "Alternatively, run migrations from inside Railway:\n"
            "  make migrate-railway\n"
        )

    return normalized


def make_engine(url: str | None = None):
    db_url = _normalize_db_url(url or settings.database_url)
    kwargs: dict = {"echo": False}
    if "sqlite" in db_url:
        # SQLite used in tests — single-file, no pool tuning needed.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL / asyncpg production settings.
        #
        # pool_pre_ping: execute "SELECT 1" before returning a connection from
        #   the pool.  Discards connections that are stale (e.g. left dirty by a
        #   cancelled request) so callers never see "another operation is in
        #   progress" from a recycled bad connection.
        #
        # pool_recycle: force-close connections older than 30 min.  Railway's
        #   managed Postgres closes idle connections server-side; without recycle
        #   the pool would hand out a TCP-alive-but-DB-dead connection.
        #
        # pool_size / max_overflow: sized for ~10 concurrent viewers each
        #   fetching 6 thumbnails + page simultaneously (≈70 requests).
        #   30 total connections leaves headroom for the Celery worker pool.
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 1800
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
    return create_async_engine(db_url, **kwargs)


engine = make_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """
    FastAPI dependency: yields a per-request isolated AsyncSession.

    Lifecycle:
      • A fresh session is created for every request (never shared).
      • On success: caller commits explicitly; session is closed by the
        async context manager on exit.
      • On exception: explicit rollback before re-raising ensures the
        connection is returned to the pool in a clean state, preventing
        "another operation is in progress" on the next checkout.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            # Rollback any staged changes so the underlying asyncpg connection
            # is clean when it returns to the pool.  Without this, a connection
            # interrupted mid-transaction can be reused with a pending operation
            # still "in progress", causing InterfaceError on the next request.
            try:
                await session.rollback()
            except Exception as rb_exc:
                # Rollback itself failed (e.g. connection already broken).
                # Log and let session.close() in __aexit__ invalidate it.
                _log.warning("session rollback failed during error cleanup: %s", rb_exc)
            raise
