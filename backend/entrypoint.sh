#!/bin/sh
# Container entrypoint — runs DB migrations then starts the requested process.
# Used by both the API and worker containers so migrations are always applied
# before any service handles traffic or processes tasks.
set -e

echo "[entrypoint] Running database migrations ..."
alembic upgrade head
echo "[entrypoint] Migrations complete."

exec "$@"
