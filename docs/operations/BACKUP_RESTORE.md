# SecureDoc Backup and Restore

## Backup Strategy

### PostgreSQL (Primary data)

**Frequency:** Daily full backup, WAL archiving for point-in-time recovery (PITR)

```bash
# Full backup (pg_dump)
pg_dump -Fc -v $DATABASE_URL > securedoc_$(date +%Y%m%d_%H%M%S).dump

# Upload to S3
aws s3 cp securedoc_$(date +%Y%m%d).dump s3://securedoc-backups/postgres/

# Verify backup
pg_restore --list securedoc_backup.dump | head -20
```

**Retention:** 30 daily, 12 weekly, 3 monthly

**PITR setup (PostgreSQL WAL):**
```bash
# In postgresql.conf:
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://securedoc-backups/wal/%f'
```

### Object Storage (Documents, Pages, Thumbnails)

S3/R2 bucket is the source of truth for all document content.

**Strategy:**
- Enable S3 Versioning on the bucket (protects against accidental deletion)
- Enable S3 Cross-Region Replication for DR
- Lifecycle policy: move originals to Glacier after 90 days

```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket securedoc-docs \
  --versioning-configuration Status=Enabled

# Enable replication (requires IAM role)
aws s3api put-bucket-replication \
  --bucket securedoc-docs \
  --replication-configuration file://replication.json
```

**Manual backup of all documents:**
```bash
aws s3 sync s3://securedoc-docs s3://securedoc-backup-bucket/ --delete
```

### Redis

Redis is a cache + Celery broker. **No backup required** — all critical state is in PostgreSQL.

On Redis failure:
- In-process caches (TTL-based) handle short outages
- Celery tasks requeue automatically when broker reconnects
- Page cache miss results in S3 fetch (higher latency, no data loss)

## Restore Procedures

### PostgreSQL — Full Restore

```bash
# 1. Stop application (prevent writes during restore)
docker stop securedoc-api securedoc-worker securedoc-beat

# 2. Drop and recreate database
psql postgres:// -c "DROP DATABASE securedoc;"
psql postgres:// -c "CREATE DATABASE securedoc;"

# 3. Restore from dump
pg_restore -v -d $DATABASE_URL securedoc_backup.dump

# 4. Verify
psql $DATABASE_URL -c "SELECT COUNT(*) FROM documents;"

# 5. Run any pending migrations (if restoring to older backup)
alembic upgrade head

# 6. Restart application
docker start securedoc-api securedoc-worker securedoc-beat
```

### PostgreSQL — PITR (Point-in-Time Recovery)

```bash
# 1. Stop primary
systemctl stop postgresql

# 2. Restore base backup
pg_basebackup -D /var/lib/postgresql/data_restore --source-server=$PRIMARY_URL

# 3. Create recovery.conf (PostgreSQL 12+: recovery.signal + postgresql.conf)
echo "recovery_target_time = '2025-12-01 14:00:00'" >> /var/lib/postgresql/data_restore/postgresql.conf
echo "restore_command = 'aws s3 cp s3://securedoc-backups/wal/%f %p'" >> /var/lib/postgresql/data_restore/postgresql.conf
touch /var/lib/postgresql/data_restore/recovery.signal

# 4. Start PostgreSQL
systemctl start postgresql

# 5. Verify and promote
psql -c "SELECT pg_promote();"
```

### Object Storage — Restore Deleted Document

```bash
# List versions of deleted key
aws s3api list-object-versions \
  --bucket securedoc-docs \
  --prefix "originals/<doc_id>"

# Restore specific version
aws s3api copy-object \
  --bucket securedoc-docs \
  --copy-source "securedoc-docs/originals/<doc_id>.pdf?versionId=<version_id>" \
  --key "originals/<doc_id>.pdf"

# Trigger reprocess via API
curl -X POST https://api.securedoc.io/api/documents/<doc_id>/reprocess \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Migration Rollback

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Show history
alembic history
```

All migrations are designed to be rollback-safe: no destructive schema changes in a single migration (add column, then populate, then add constraint as separate steps).

## Recovery Time Objectives (RTO) / Recovery Point Objectives (RPO)

| Component | RPO | RTO |
|-----------|-----|-----|
| PostgreSQL (PITR) | 5 minutes | 30 minutes |
| PostgreSQL (daily backup) | 24 hours | 2 hours |
| Object Storage (versioned) | Near-zero | 15 minutes |
| Redis | N/A (cache) | 5 minutes |

## Backup Verification (Monthly)

```bash
# 1. Restore backup to staging
pg_restore -v -d $STAGING_URL securedoc_backup_latest.dump

# 2. Verify row counts match production
psql $STAGING_URL -c "
  SELECT 'documents' as t, COUNT(*) FROM documents
  UNION ALL SELECT 'share_links', COUNT(*) FROM share_links
  UNION ALL SELECT 'access_events', COUNT(*) FROM access_events;
"

# 3. Run smoke tests against restored staging
pytest tests/integration/ -k "smoke"

# 4. Document results in ops log
```
