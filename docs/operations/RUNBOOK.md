# SecureDoc Operations Runbook

## Service Overview

| Service | Port | Health Check |
|---------|------|-------------|
| API (FastAPI/uvicorn) | 8000 | `GET /live` |
| Celery worker | — | `celery inspect ping` |
| Celery beat | — | Process health |
| PostgreSQL | 5432 | `pg_isready` |
| Redis | 6379 | `redis-cli ping` |

## Common Operations

### Restart API

```bash
# Docker
docker restart securedoc-api

# systemd
systemctl restart securedoc-api

# Kubernetes
kubectl rollout restart deployment/securedoc-api
```

### Restart Workers

```bash
docker restart securedoc-worker
# Workers gracefully finish current task (acks_late=True) before exiting
```

### Run Database Migrations

```bash
# Always backup before migrating
pg_dump -Fc securedoc > backup_$(date +%Y%m%d).dump

# Apply migrations
alembic upgrade head

# Verify
alembic current
```

### Clear Redis Cache (emergency)

```bash
redis-cli FLUSHDB  # clears only db 0 (page cache + Celery)
# WARNING: forces all page re-fetches; high S3 bandwidth spike
```

### Reprocess a Stuck Document

```bash
# Via API
curl -X POST https://api.securedoc.io/api/documents/{doc_id}/reprocess \
  -H "Authorization: Bearer $TOKEN"

# Via Celery
celery -A app.workers.celery_app call securedoc.process_document \
  --args='["<doc_id>"]'
```

### Revoke a Compromised Share Link

```bash
curl -X DELETE https://api.securedoc.io/api/links/{link_id} \
  -H "Authorization: Bearer $TOKEN"
# Revocation propagates to in-process cache within 30 seconds
```

### Check Celery Queue Depth

```bash
celery -A app.workers.celery_app inspect reserved
celery -A app.workers.celery_app inspect active
# Queue depth in Redis:
redis-cli LLEN celery
```

### Scale Workers

```bash
# Docker Compose
docker compose scale worker=4

# Kubernetes
kubectl scale deployment securedoc-worker --replicas=4
```

## Monitoring Checklist

### Daily
- [ ] Check error rate on `/metrics`: `securedoc_http_requests_total{status_code=~"5.."}`
- [ ] Check Celery queue depth < 100
- [ ] Check DB connection pool utilization

### Weekly
- [ ] Review webhook delivery failures: `securedoc_webhook_deliveries_total{outcome="failure"}`
- [ ] Review document processing errors in logs
- [ ] Check disk usage on object storage

## Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|---------|
| HTTP 5xx rate | >1% | >5% |
| API p99 latency | >2s | >5s |
| Celery queue depth | >50 | >200 |
| DB query p99 | >500ms | >2s |
| Cache hit rate | <70% | <50% |
| Failed webhook deliveries | >10/hr | >50/hr |

## Log Locations

```bash
# Application logs (JSON)
docker logs securedoc-api

# Filter by error level
docker logs securedoc-api 2>&1 | jq 'select(.level == "ERROR")'

# Filter by document ID
docker logs securedoc-api 2>&1 | jq 'select(.doc_id == "<id>")'
```

## Emergency Contacts

- On-call: page via PagerDuty `securedoc-prod`
- Database: DBA team Slack #database-oncall
- Storage: Cloud infrastructure Slack #infra-oncall
