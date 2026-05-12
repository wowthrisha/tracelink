from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


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
    connect_args = {}
    if "sqlite" in db_url:
        connect_args = {"check_same_thread": False}
    return create_async_engine(db_url, echo=False, connect_args=connect_args)


engine = make_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
