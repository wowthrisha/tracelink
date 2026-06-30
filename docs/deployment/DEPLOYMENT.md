# Deployment Guide

**Last Updated:** 2026-06-30
**Applies To:** SecureDoc v8.1.0 (RC-1)

---

## Quick Start (Docker)

```bash
cp backend/.env.example backend/.env   # fill in credentials
docker compose up --build
```

The app is available at `http://localhost:8000` when the `api` health check passes.

---

## Stack

| Service | Image | Purpose |
|---------|-------|---------|
| `db` | postgres:16-alpine | Primary database |
| `redis` | redis:7-alpine | Cache + Celery broker |
| `migrate` | (built) | Runs `alembic upgrade head` once, then exits |
| `api` | (built) | FastAPI + static frontend |
| `worker` | (built) | Celery PDF processing |
| `beat` | (built) | Celery periodic task scheduler |
| `backup` | postgres:16-alpine | Daily pg_dump (profile: backup) |

`api` and `worker` both wait for `migrate` to complete via `depends_on: service_completed_successfully`. The migration runner holds a PostgreSQL advisory lock (`pg_advisory_lock(7325613)`) for the full duration of `alembic upgrade head`, preventing race conditions when multiple containers start simultaneously.

---

## Environment Variables

Copy `backend/.env.example` and fill in every required value.

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Yes | `redis://host:6379/0` |
| `JWT_SECRET` | Yes | 32-byte hex — `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `SUPABASE_URL` | Yes | `https://your-project.supabase.co` |
| `SUPABASE_ANON_KEY` | Yes | Supabase publishable anon key |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key — never expose to browser |
| `STORAGE_BACKEND` | Yes | `s3`, `gcs`, or `demo` |
| `STORAGE_ENDPOINT_URL` | Yes (s3) | Supabase Storage S3 endpoint |
| `STORAGE_ACCESS_KEY_ID` | Yes (s3) | Storage access key |
| `STORAGE_SECRET_ACCESS_KEY` | Yes (s3) | Storage secret key |
| `STORAGE_BUCKET_NAME` | Yes (s3) | S3 bucket name (default: `securedoc-docs`) |
| `APP_PUBLIC_BASE_URL` | Yes | Root URL for share links (e.g. `https://your-domain.com`) |
| `ALLOWED_ORIGINS` | Yes | Comma-separated CORS origins |
| `APP_ENV` | No | `development` (default) or `production` |
| `WORKER_CONCURRENCY` | No | Celery worker processes (default: 2) |
| `STRIPE_SECRET_KEY` | No | Enables billing features |

---

## Production Deployment (Railway / Fly / VPS)

1. Push code to your hosting provider
2. Set start command to the Dockerfile default CMD, or use `./entrypoint.sh uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`
3. Set all required env vars in the platform dashboard
4. Set `APP_ENV=production`
5. Deploy the `worker` service separately using the same image with the Celery command

### Railway

Deploy directly from the `Dockerfile`. The advisory lock in `migrate.py` handles the Railway cold-start race where `api` and `worker` start simultaneously with no dedicated migrate service.

---

## Database Migrations

Migrations are managed by Alembic. Current head: `025_performance_indexes` (26 total).

```bash
# Check current state
cd backend && alembic current

# Apply pending migrations
cd backend && alembic upgrade head

# Roll back one migration
cd backend && alembic downgrade -1
```

The `migrate` Docker service and `entrypoint.sh` both call `migrate.py`, which holds a PostgreSQL advisory lock for the full duration. Multiple containers can start simultaneously without conflict.

---

## Health Check

`GET /health` returns `{"status": "ok", ...}` with subsystem checks:

```json
{
  "status": "ok",
  "checks": {
    "db": "ok",
    "redis": "ok",
    "storage": "...",
    "worker": "ok",
    "auth_configured": true,
    "storage_credentials": "configured"
  },
  "version": "8.1.0"
}
```

---

## Demo Mode (No Cloud Storage)

Set `USE_DEMO_STORAGE=1` to use local disk at `/tmp/securedoc_storage/` instead of S3. Useful for evaluation and development. Not for production.

```bash
cd backend && USE_DEMO_STORAGE=1 python run_demo.py
```

---

## Cloudflare Quick Tunnel (Public HTTPS Without a Domain)

```bash
brew install cloudflared
./start.sh quicktunnel   # auto-detects URL and writes to .env
./start.sh backend       # restart to apply
```

---

## Backup

Enable the backup service (runs `pg_dump` daily at 02:00 UTC, retains 7 days):

```bash
docker compose --profile backup up -d backup
```

---

## Scaling Notes

- **API**: Horizontal scaling is safe. Each instance connects to shared PostgreSQL + Redis.
- **Worker**: Scale by increasing `WORKER_CONCURRENCY` or running multiple worker containers. Set `WORKER_MAX_TASKS_PER_CHILD=50` to recycle worker processes and limit memory accumulation from PDF libraries.
- **Beat**: Run exactly one Beat instance. Multiple Beat instances cause duplicate task submissions.
