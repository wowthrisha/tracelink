"""
migrate.py — run Alembic migrations under a PostgreSQL advisory lock.

Why this exists
---------------
Both the API container and the Celery worker container execute this script on
startup (via entrypoint.sh).  Without a lock, two containers starting
simultaneously can both read the current alembic_version as, say, '006', then
both attempt to apply migration '007'.  The second container will fail on
idempotency-unsafe DDL (CREATE TABLE, ALTER COLUMN, etc.) that the first
container already committed.

The fix is a PostgreSQL *session-level advisory lock* (pg_advisory_lock).
The lock is exclusive and session-scoped, meaning:
  • Only one connection holds it at a time.
  • It is automatically released when the holding connection closes.

Because the lock is held for the entire duration of the subprocess call to
``alembic upgrade head``, any concurrent caller blocks in pg_advisory_lock()
until the winner finishes, then acquires the lock, runs ``alembic upgrade
head``, and finds nothing to do (already at head) — completing in milliseconds.

SQLite (used by local dev and the test suite)
---------------------------------------------
SQLite does not have advisory locks and does not need them (only one process
uses the test DB at a time).  When DATABASE_URL contains 'sqlite', this script
skips the lock and calls alembic directly.

Fallback safety
---------------
If the advisory lock itself cannot be acquired (e.g., network blip before the
DB is ready), the error is printed and alembic is called directly.  In the
worst case two containers race on the first migration — the second fails and
restarts (Docker/Railway restart policy re-runs entrypoint.sh, which then
succeeds because migrations are already applied).  This is no worse than the
pre-fix behaviour but is now a rare fallback rather than the common case.
"""
import asyncio
import os
import subprocess
import sys

# Arbitrary fixed integer key that identifies SecureDoc's migration lock.
# Any 64-bit integer works; this one spells "SDMIG" in decimal.
_LOCK_KEY = 7_325_613


def _to_asyncpg_url(url: str) -> str:
    """Strip SQLAlchemy dialect tags so asyncpg.connect() accepts the URL."""
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


async def _run_with_advisory_lock(db_url: str) -> int:
    """Acquire pg_advisory_lock, run alembic, release lock, return exit code."""
    import asyncpg  # imported here so SQLite path never touches asyncpg

    conn = await asyncpg.connect(_to_asyncpg_url(db_url))
    try:
        print(f"[migrate] Acquiring advisory lock (key={_LOCK_KEY}) …", flush=True)
        await conn.execute(f"SELECT pg_advisory_lock({_LOCK_KEY})")
        print("[migrate] Lock acquired — running: alembic upgrade head", flush=True)

        result = subprocess.run(["alembic", "upgrade", "head"])
        return result.returncode
    finally:
        try:
            await conn.execute(f"SELECT pg_advisory_unlock({_LOCK_KEY})")
        except Exception:
            pass  # connection may already be closing; lock releases on disconnect
        await conn.close()
        print("[migrate] Advisory lock released.", flush=True)


def main() -> None:
    db_url = os.environ.get("DATABASE_URL", "")

    # SQLite: no advisory lock needed — run alembic directly.
    if not db_url or "sqlite" in db_url.lower():
        print("[migrate] SQLite detected — running alembic upgrade head directly.", flush=True)
        result = subprocess.run(["alembic", "upgrade", "head"])
        sys.exit(result.returncode)

    # PostgreSQL: acquire advisory lock, then run alembic.
    try:
        rc = asyncio.run(_run_with_advisory_lock(db_url))
    except Exception as exc:
        # Lock acquisition failed (e.g., DB not yet ready).  Fall back to
        # running alembic directly — Docker/Railway restart policy will recover
        # if the race actually causes a failure.
        print(
            f"[migrate] Advisory lock unavailable ({exc}) — running alembic directly.",
            file=sys.stderr,
            flush=True,
        )
        result = subprocess.run(["alembic", "upgrade", "head"])
        rc = result.returncode

    sys.exit(rc)


if __name__ == "__main__":
    main()
