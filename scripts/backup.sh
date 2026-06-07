#!/usr/bin/env bash
# SecureDoc — Database Backup Script
#
# Usage:
#   ./scripts/backup.sh                        # backup to ./backups/
#   ./scripts/backup.sh /path/to/backup/dir    # backup to specified directory
#   BACKUP_DB_URL=postgresql://... ./scripts/backup.sh
#
# Environment variables:
#   BACKUP_DB_URL   Override database URL (default: read from backend/.env)
#   BACKUP_DIR      Override backup directory (default: ./backups)
#   KEEP_DAYS       Days to retain backups (default: 7)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BACKUP_DIR="${1:-${BACKUP_DIR:-$PROJECT_DIR/backups}}"
KEEP_DAYS="${KEEP_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/securedoc_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Resolve DB URL
if [ -z "${BACKUP_DB_URL:-}" ]; then
    if [ -f "$PROJECT_DIR/backend/.env" ]; then
        BACKUP_DB_URL=$(grep -E '^DATABASE_URL=' "$PROJECT_DIR/backend/.env" | cut -d= -f2- | tr -d '"' | tr -d "'")
        # Convert asyncpg URL to psycopg2-compatible URL for pg_dump
        BACKUP_DB_URL="${BACKUP_DB_URL/postgresql+asyncpg:\/\//postgresql://}"
    fi
fi

if [ -z "${BACKUP_DB_URL:-}" ]; then
    echo "ERROR: DATABASE_URL not found. Set BACKUP_DB_URL or ensure backend/.env exists." >&2
    exit 1
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting backup → $BACKUP_FILE"

pg_dump "$BACKUP_DB_URL" \
    --format=plain \
    --no-owner \
    --no-acl \
    | gzip -9 > "$BACKUP_FILE"

BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup complete: $BACKUP_FILE ($BACKUP_SIZE)"

# Verify the backup is non-empty
if [ ! -s "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file is empty!" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Verify the backup is a valid gzip file
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    echo "ERROR: Backup file is not a valid gzip archive!" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup verified (valid gzip, non-empty)"

# Rotate old backups
if [ "$KEEP_DAYS" -gt 0 ]; then
    DELETED=$(find "$BACKUP_DIR" -name "securedoc_*.sql.gz" -mtime "+${KEEP_DAYS}" -print -delete | wc -l)
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Rotated $DELETED backup(s) older than ${KEEP_DAYS} days"
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Done."
