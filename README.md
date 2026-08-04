# SecureDoc

**Secure document sharing with per-link access controls, viewer analytics, and forensic watermarking.**

Share documents as controlled links — not attachments. Set expiry dates, view limits, IP restrictions, and passwords per link. See exactly who viewed what, when, and for how long. Every page is watermarked with the viewer's identity.

---

## Features

- **Controlled sharing** — per-link expiry, view limits, IP allowlist, password, domain restriction
- **Viewer analytics** — time per page, completion rate, geography, device
- **Forensic watermarking** — visible watermark (email + timestamp) + invisible forensic stamp per viewer per page
- **DRM controls** — print, copy, right-click, and screenshot prevention (client-side UX gates)
- **Multi-format support** — PDF, DOCX, DOC, TXT, MD, LOG
- **API access** — full REST API with `sd_` API keys
- **Webhooks** — outbound events for view, completion, access denial
- **Organizations** — multi-org support, role-based membership (viewer/editor/admin/owner)
- **Retention policies** — per-document automatic expiry
- **Audit log** — admin audit trail for all sensitive operations

## Architecture

```
Browser (Viewer)
    └─▶ Share link  /v/{token}
            └─▶ FastAPI API  :8000
                    ├─▶ Supabase Auth (JWT / SAML)
                    ├─▶ PostgreSQL    (state, 27 migrations)
                    ├─▶ Redis         (page cache + Celery broker)
                    ├─▶ Object Storage (S3-compatible)
                    └─▶ Celery Worker (PDF processing pipeline)
```

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLAlchemy async |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Storage | Supabase Storage (S3-compatible) |
| Auth | Supabase JWT (ES256 / JWKS) + API keys |
| Task queue | Celery + Celery Beat |
| Frontend | React 18, esbuild IIFE bundle (~309 KB) |

For system diagrams and design decisions see [`docs/architecture/`](docs/architecture/).

---

## Quick Start

### Docker (recommended)

```bash
cp backend/.env.example backend/.env   # fill in credentials
docker compose up --build
# App available at http://localhost:8000
```

### Native

```bash
# Prerequisites: Python 3.12+, PostgreSQL, Redis

cd backend
pip install -r requirements.txt
cp .env.example .env                   # fill in credentials
alembic upgrade head

# Terminal 1 — API
USE_DEMO_STORAGE=1 python run_demo.py

# Terminal 2 — Worker
celery -A app.workers.celery_app worker --loglevel=info
```

Frontend is served automatically at `http://localhost:8000` by the backend.

---

## Environment Variables

Copy `backend/.env.example` and set these:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Redis connection (`redis://...`) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon (publishable) key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key — never expose to browser |
| `USE_DEMO_STORAGE` | Set to `1` for local dev (in-memory/demo storage, no S3 needed); omit for real object storage — see `backend/.env.example` for the S3/R2 variables |
| `APP_PUBLIC_BASE_URL` | Root URL for share links (e.g. `https://your-domain.com`) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |

See [`docs/deployment/DEPLOYMENT.md`](docs/deployment/DEPLOYMENT.md) for the full variable reference, Railway/Fly deployment, and scaling notes.

---

## Development

### Run tests

```bash
cd backend
python -m pytest tests/ -q
# Expected: ~1700 passed, 1 skipped, 0 failed
```

### Build the frontend bundle

```bash
cd frontend && npm ci && npm run build
# Output: frontend/dist/app.bundle.js
```

### API documentation

Interactive API docs at `http://localhost:8000/docs` (Swagger UI) when the backend is running.

### Migrations

```bash
cd backend
alembic current           # show current migration state
alembic upgrade head      # apply pending migrations
alembic downgrade -1      # roll back one migration
```

---

## Deployment

See [`docs/deployment/DEPLOYMENT.md`](docs/deployment/DEPLOYMENT.md) for:

- Full Docker Compose service reference
- Railway / Fly / VPS deployment
- Environment variable reference
- Migration safety (advisory lock)
- Scaling notes (API, worker, Beat)
- Backup configuration

### Public HTTPS without a domain (Cloudflare Quick Tunnel)

```bash
brew install cloudflared
./start.sh quicktunnel   # detects URL and writes APP_PUBLIC_BASE_URL to .env
./start.sh backend       # restart to apply
```

---

## Security

All page bytes are proxied through the API — object storage URLs are never exposed to viewers. HSTS is enabled by default. See [`SECURITY.md`](SECURITY.md) for the full security model, vulnerability reporting, and known limitations.

---

## Documentation Index

| Area | Location |
|------|----------|
| Architecture & design decisions | [`docs/architecture/`](docs/architecture/) |
| API reference | [`docs/api/`](docs/api/) |
| Deployment (Railway/Fly/VPS, scaling, backups) | [`docs/deployment/DEPLOYMENT.md`](docs/deployment/DEPLOYMENT.md) |
| Local development setup | [`docs/development/DEVELOPER_GUIDE.md`](docs/development/DEVELOPER_GUIDE.md) |
| Security model, hardening plans | [`docs/security/`](docs/security/), [`SECURITY.md`](SECURITY.md) |
| Operations runbooks | [`docs/operations/`](docs/operations/) |
| Reading Intelligence engine internals | [`docs/reading_analytics/`](docs/reading_analytics/) |
| Current release certification | [`docs/release/FINAL_RELEASE_CERTIFICATION.md`](docs/release/FINAL_RELEASE_CERTIFICATION.md) |
| Engineering process (canonical backlog, fix log, action log) | [`ENGINEERING_BACKLOG.md`](ENGINEERING_BACKLOG.md), [`docs/engineering/`](docs/engineering/) |
| Historical sprint/audit reports | [`archive/`](archive/) — see [`docs/governance/ARCHIVED_FILES.md`](docs/governance/ARCHIVED_FILES.md) for the index |

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the development workflow, code standards, and PR checklist.

---

## License

MIT — see [`LICENSE`](LICENSE).
