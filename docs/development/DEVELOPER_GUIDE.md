# SecureDoc Developer Guide

## Repository Structure

```
securedoc/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware stack, startup
│   │   ├── config.py            # Pydantic-settings config
│   │   ├── auth.py              # JWT + API key auth
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── metrics.py           # Prometheus metric definitions
│   │   ├── telemetry.py         # OpenTelemetry setup
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── routers/             # FastAPI route handlers
│   │   ├── services/            # Business logic
│   │   ├── workers/             # Celery tasks and pipelines
│   │   │   ├── celery_app.py    # Celery app configuration
│   │   │   ├── tasks.py         # process_document task
│   │   │   ├── webhook_tasks.py # deliver_webhook task
│   │   │   └── pipeline/        # Per-file-type processing adapters
│   │   ├── middleware/          # ASGI middleware
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   └── utils/               # Crypto, validation helpers
│   ├── alembic/                 # Database migrations
│   ├── tests/
│   │   ├── unit/                # Unit tests
│   │   └── integration/         # Integration tests (real DB)
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root component
│   │   ├── AppShell.jsx         # Screen router, auth state
│   │   ├── components/          # Shared atoms.jsx + feature components
│   │   ├── screens/             # Full-page screen components
│   │   ├── hooks/               # Custom React hooks
│   │   └── api/                 # API client functions
│   └── package.json
├── docs/                        # Documentation
└── .github/workflows/           # CI/CD
```

## Local Development Setup

### Backend

```bash
cd backend

# Create virtualenv
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env (copy from .env.example)
cp .env.example .env
# Edit .env: set DATABASE_URL, REDIS_URL, SUPABASE_*, etc.

# Start PostgreSQL and Redis (Docker)
docker compose up -d db redis

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --port 8000

# Start worker (separate terminal)
celery -A app.workers.celery_app worker -l info
```

### Frontend

```bash
cd frontend
npm install

# Build once
npm run build

# Watch mode
npm run build -- --watch

# Run tests
npm test
```

### Demo Mode (no S3/Celery needed)

```bash
export USE_DEMO_STORAGE=1
uvicorn app.main:app --reload
# Documents process in-process synchronously using local temp storage
```

## Running Tests

```bash
cd backend

# All tests
pytest tests/ -x -q

# Unit only
pytest tests/unit/ -x -q

# Integration only (requires DB + Redis)
pytest tests/integration/ -x -q

# With coverage
pytest tests/ --cov=app --cov-report=html

# Specific test file
pytest tests/integration/test_viewer.py -x -v
```

Frontend tests:
```bash
cd frontend
npm test
```

## Adding a New Feature

### Backend Endpoint

1. Add route in `app/routers/<feature>.py`
2. Add Pydantic schemas in `app/schemas/<feature>.py`
3. Add business logic in `app/services/<feature>_service.py`
4. Add/update ORM model in `app/models/<feature>.py`
5. Create migration: `alembic revision --autogenerate -m "add_<feature>"`
6. Review and edit migration file (autogenerate is a starting point)
7. Run migration: `alembic upgrade head`
8. Wire metrics in `metrics.py` for new operations
9. Add tests in `tests/integration/test_<feature>.py`
10. Register router in `main.py`

### Frontend Screen

1. Create `frontend/src/screens/<Feature>Screen.jsx`
2. Add navigation entry in `AppShell.jsx` sidebar
3. Add API client functions in `frontend/src/api/<feature>.js`
4. Reuse atoms from `frontend/src/components/atoms.jsx` (Btn, Card, Modal, Field, etc.)
5. Add toast notifications via `useToast()` hook
6. Add tests in `frontend/src/tests/`

## Code Standards

### Backend

- Async functions for all I/O (DB, storage, Redis)
- Route handlers are thin — business logic in `services/`
- Never log raw session IDs, tokens, emails, or raw IPs
- Use `extra={"key": value}` in logger calls for structured fields
- Increment Prometheus metrics at call sites, not in services
- Return HTTP exceptions with specific status codes and messages

### Frontend

- Component library: use `atoms.jsx` (Btn, Card, Modal, Field, Toggle, etc.)
- Screen-level state management only (no global state library)
- Error handling: always show toast on API failure
- Accessibility: WCAG 2.1 AA — semantic HTML, ARIA labels, keyboard navigation
- No inline styles where CSS classes suffice

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description_of_change"

# Edit the generated file — autogenerate misses:
# - Custom defaults
# - Partial indexes
# - Check constraints
# - FTS indexes

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

**Migration rules:**
- Never drop columns or tables in the same migration that removes references
- Always make columns nullable before making them NOT NULL (separate migration)
- Test rollback before merging: `alembic downgrade -1 && alembic upgrade head`

## Adding Prometheus Metrics

1. Define metric in `app/metrics.py` (Counter, Histogram, or Gauge)
2. Follow naming convention: `securedoc_<subsystem>_<metric>_<unit>`
3. Labels must be low-cardinality (status codes, outcomes — never user IDs or paths)
4. Import and `.inc()` / `.observe()` at the callsite (router or worker)

## Environment Variables Reference

See [DEPLOYMENT.md](../deployment/DEPLOYMENT.md) for full list.

For local development, `.env.example`:
```
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://securedoc:password@localhost:5432/securedoc
REDIS_URL=redis://localhost:6379/0
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
USE_DEMO_STORAGE=1
ENABLE_JSON_LOGGING=false
```
