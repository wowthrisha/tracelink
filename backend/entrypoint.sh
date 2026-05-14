#!/bin/sh
# Container entrypoint — runs DB migrations then starts the requested process.
# Used by both the API and worker containers.
#
# Migrations are run via migrate.py which holds a PostgreSQL advisory lock for
# the full duration of `alembic upgrade head`.  This serialises concurrent
# startups (api + worker starting simultaneously on Railway) and prevents the
# race condition where both containers try to apply the same migration.
set -e

echo "[entrypoint] Running database migrations ..."
python migrate.py
echo "[entrypoint] Migrations complete."

exec "$@"
