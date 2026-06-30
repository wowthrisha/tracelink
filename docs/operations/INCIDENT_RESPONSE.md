# SecureDoc Incident Response Playbook

## Severity Levels

| Level | Description | Response Time |
|-------|-------------|--------------|
| P0 — Critical | Total service outage, data breach, auth bypass | 15 min |
| P1 — High | Major feature broken, >10% error rate | 1 hour |
| P2 — Medium | Degraded performance, <1% error rate | 4 hours |
| P3 — Low | Minor UX issues, non-critical errors | Next business day |

## Incident Commander Responsibilities

1. Declare incident severity
2. Establish incident channel (Slack #incident-YYYYMMDD-N)
3. Assign roles: commander, tech lead, comms
4. Drive to resolution, not diagnosis
5. Write post-mortem within 48 hours

## Common Incident Playbooks

### P0: Service Down (API not responding)

```bash
# 1. Check health
curl https://api.securedoc.io/live
curl https://api.securedoc.io/ready

# 2. Check logs
docker logs securedoc-api --tail=100 | jq 'select(.level == "ERROR")'

# 3. Check DB
psql $DATABASE_URL -c "SELECT 1"

# 4. Check Redis
redis-cli -u $REDIS_URL ping

# 5. Restart if needed (last resort)
docker restart securedoc-api

# 6. If DB migration failed, rollback
alembic downgrade -1
```

### P0: Suspected Data Breach / Token Compromise

```bash
# 1. Immediately revoke all active sessions for affected user/link
# Via DB (emergency):
psql $DATABASE_URL -c "
  UPDATE viewer_sessions SET revoked_at = NOW()
  WHERE link_id = '<affected_link_id>';
"

# 2. Revoke affected share links
curl -X DELETE https://api.securedoc.io/api/links/<link_id> \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 3. Rotate IP_HASH_SALT (requires app restart — rehashes future IPs)
# Set new IP_HASH_SALT in secrets manager and redeploy

# 4. Audit access log
psql $DATABASE_URL -c "
  SELECT event_type, viewer_email, created_at
  FROM access_events
  WHERE link_id = '<id>'
  ORDER BY created_at DESC
  LIMIT 100;
"

# 5. Notify affected document owner via support ticket
```

### P1: Document Processing Queue Stuck

```bash
# 1. Check stuck documents
psql $DATABASE_URL -c "
  SELECT id, filename, status, updated_at
  FROM documents
  WHERE status = 'processing'
  AND updated_at < NOW() - INTERVAL '20 minutes';
"

# 2. Check worker status
celery -A app.workers.celery_app inspect ping

# 3. Reprocess stuck documents
# Via Celery beat's auto-rescue (runs every 10 min) or manually:
celery -A app.workers.celery_app call securedoc.process_document \
  --args='["<doc_id>"]'

# 4. If workers are dead, restart
docker restart securedoc-worker

# 5. Check for OOM kills
dmesg | grep -i "oom" | tail -20
```

### P1: High Error Rate

```bash
# 1. Identify error pattern
docker logs securedoc-api --tail=500 | jq 'select(.level == "ERROR")' \
  | jq -r '.msg' | sort | uniq -c | sort -rn

# 2. Check DB connection pool
docker logs securedoc-api | grep "pool" | tail -20

# 3. Check rate limiting (429s)
# Query Prometheus: securedoc_http_requests_total{status_code="429"}

# 4. Check for dependency failures (upstream S3/Supabase)
curl https://status.supabase.com
```

### P2: Webhook Delivery Failures

```bash
# 1. Check failure count
psql $DATABASE_URL -c "
  SELECT w.name, COUNT(*) as failed
  FROM webhook_deliveries wd
  JOIN webhook_configs w ON w.id = wd.webhook_id
  WHERE wd.status = 'failed'
  AND wd.created_at > NOW() - INTERVAL '1 hour'
  GROUP BY w.name;
"

# 2. Check specific endpoint
curl -X POST <webhook_url> -H "Content-Type: application/json" -d '{}'

# 3. Dead-letter queue (DLQ): deliveries with status='failed' after max_retries
# Operator decision: retry, notify customer, or discard
```

## Post-Mortem Template

```markdown
# Incident Post-Mortem: YYYYMMDD-N

**Severity:** P0 / P1 / P2
**Duration:** HH:MM
**Impact:** N users affected, N documents inaccessible

## Timeline
- HH:MM UTC: First alert / user report
- HH:MM UTC: Incident declared
- HH:MM UTC: Root cause identified
- HH:MM UTC: Fix deployed
- HH:MM UTC: Incident resolved

## Root Cause
[1-2 sentence description]

## Contributing Factors
- [Factor 1]

## What Went Well
- [Item]

## What Went Wrong
- [Item]

## Action Items
| Action | Owner | Due Date |
|--------|-------|---------|
| [Fix X] | @engineer | YYYY-MM-DD |
```
