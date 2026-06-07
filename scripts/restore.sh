#!/usr/bin/env bash
# SecureDoc — Database Restore Script
#
# Usage:
#   ./scripts/restore.sh backups/securedoc_20260101_020000.sql.gz
#
# WARNING: This drops and recreates the target database. Use with caution.
# Always take a pre-restore backup first.
#
# Environment variables:
#   RESTORE_DB_URL   Override target database URL
#   SKIP_CONFIRM     Set to "yes" to skip the confirmation prompt (CI/automation)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>" >&2
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE" >&2
    exit 1
fi

# Verify backup integrity before proceeding
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo "ERROR: Backup file is corrupted (failed gzip integrity check)" >&2
    exit 1
fi

# Resolve DB URL
if [ -z "${RESTORE_DB_URL:-}" ]; then
    if [ -f "$PROJECT_DIR/backend/.env" ]; then
        RESTORE_DB_URL=$(grep -E '^DATABASE_URL=' "$PROJECT_DIR/backend/.env" | cut -d= -f2- | tr -d '"' | tr -d "'")
        RESTORE_DB_URL="${RESTORE_DB_URL/postgresql+asyncpg:\/\//postgresql://}"
    fi
fi

if [ -z "${RESTORE_DB_URL:-}" ]; then
    echo "ERROR: DATABASE_URL not found. Set RESTORE_DB_URL or ensure backend/.env exists." >&2
    exit 1
fi

# Extract DB name for confirmation message
DB_NAME=$(echo "$RESTORE_DB_URL" | sed 's|.*\/||' | cut -d? -f1)

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                  ⚠  DESTRUCTIVE OPERATION  ⚠         ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Backup file : $BACKUP_FILE"
echo "  Target DB   : $DB_NAME"
echo "  URL         : ${RESTORE_DB_URL//:*@/:***@}"
echo ""
echo "  This will ERASE ALL DATA in '$DB_NAME' and restore from the backup."
echo ""

if [ "${SKIP_CONFIRM:-no}" != "yes" ]; then
    read -r -p "  Type 'restore' to confirm: " CONFIRM
    if [ "$CONFIRM" != "restore" ]; then
        echo "Aborted." >&2
        exit 1
    fi
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Taking pre-restore backup..."
"$SCRIPT_DIR/backup.sh" "$(dirname "$BACKUP_FILE")"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting restore from $BACKUP_FILE..."

gunzip -c "$BACKUP_FILE" | psql "$RESTORE_DB_URL"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Restore complete."
echo ""
echo "Post-restore steps:"
echo "  1. Restart API:    docker compose restart api"
echo "  2. Restart worker: docker compose restart worker"
echo "  3. Verify health:  curl http://localhost:8000/health"
