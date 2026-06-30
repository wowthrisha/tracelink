# RC1 DEPLOYMENT REPORT — Sprint 6.2
**Date:** 2026-06-30
**Release:** RC-1 (v8.1.0)

---

## Deployment Stack

| Layer | Technology | Config File |
|-------|-----------|------------|
| Container runtime | Docker (multi-stage) | `backend/Dockerfile` |
| Orchestration | Docker Compose | `docker-compose.yml` |
| Process manager | Uvicorn (2 workers) | `CMD` in Dockerfile |
| Background workers | Celery | `worker` service in docker-compose |
| Scheduler | Celery Beat | `beat` service in docker-compose |
| Database | PostgreSQL 16 | `db` service / `DATABASE_URL` env |
| Cache / broker | Redis 7 | `redis` service / `REDIS_URL` env |
| Migrations | Alembic + advisory lock | `migrate.py` + `entrypoint.sh` |
| Backup | pg_dump cron (daily 02:00 UTC) | `backup` service (profile: backup) |

---

## Dockerfile Analysis

### Stage 1 — Frontend Build
- Base: `node:20-alpine`
- Compiles JSX → `dist/app.bundle.js` via esbuild
- No Node.js runtime in final image (build artifact only)

### Stage 2 — Python Runtime
- Base: `python:3.12-slim`
- System deps: ghostscript, poppler-utils (PDF), antiword (legacy .doc), libreoffice-writer (DOCX→PDF), fonts
- Non-root user: `appuser` (UID 1001)
- `EXPOSE 8000`
- `ENTRYPOINT ["./entrypoint.sh"]` → runs `migrate.py` then `exec "$@"`
- Default `CMD`: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`

**Security posture:** Non-root execution, no secrets baked into image, env vars injected at runtime via `.env` file or platform env.

---

## Migration Safety

`migrate.py` implements a PostgreSQL session-level advisory lock (key `7325613`):

1. Acquires `pg_advisory_lock(7325613)` — blocks concurrent callers
2. Runs `alembic upgrade head` as subprocess
3. Releases lock on connection close

**Concurrent startup safety:** Both `api` and `worker` containers call `migrate.py` on start. The advisory lock serialises them — the winner upgrades, the loser finds nothing to do (already at head) and proceeds in milliseconds.

**docker-compose ordering:** `api` and `worker` both declare `depends_on: migrate: condition: service_completed_successfully`, ensuring the dedicated `migrate` service finishes before either starts. Belt-and-suspenders with the advisory lock.

**Rollback:** Alembic supports `alembic downgrade -1`. All 26 migrations (001–025) use standard DDL patterns compatible with transactional DDL on PostgreSQL.

---

## Migration State

```
Current head: 025_performance_indexes
Total migrations: 26 (001 through 025 + initial)
Status: AT HEAD — no pending migrations
```

---

## Health Checks

| Service | Check | Interval | Retries |
|---------|-------|----------|---------|
| `db` | `pg_isready -U securedoc` | 5s | 10 |
| `redis` | `redis-cli ping` | 5s | 10 |
| `api` | `curl -sf http://localhost:8000/health` | 10s | 12 (start_period: 25s) |
| `worker` | `celery inspect ping --timeout=5` | 30s | 3 (start_period: 30s) |

---

## Scheduled Jobs (Celery Beat)

| Task | Schedule | Purpose |
|------|----------|---------|
| `purge_stale_sessions` | Every 30 min | Removes expired viewer sessions |
| `requeue_orphaned_uploads` | Every 5 min | Recovers stuck processing jobs |

Beat runs as a single instance. Docker `restart: unless-stopped` recovers crashes; next scheduled slot fires on next interval.

---

## Environment Variables Required for Production

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL async URL (`postgresql+asyncpg://…`) |
| `REDIS_URL` | Redis URL (`redis://…`) |
| `SECRET_KEY` | 32-byte hex for session signing |
| `SUPABASE_URL` | Supabase project URL for JWT auth |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_KEY` | Supabase service key |
| `STORAGE_BACKEND` | `s3`, `gcs`, or `demo` |
| `STRIPE_SECRET_KEY` | Optional — billing features |
| `WORKER_CONCURRENCY` | Celery worker concurrency (default: 2) |

---

## Railway Deployment Notes

No `railway.json` / `railway.toml` found in repository. Railway deployment uses the `Dockerfile` directly. The advisory lock in `migrate.py` handles the Railway cold-start race condition (api + worker starting simultaneously with no dedicated migrate service).

---

## Verdict

Deployment stack is **production-ready**. No gaps in migration safety, health checks, worker scheduling, or container security.
