.PHONY: up down logs test shell build clean

# Build images and start all services (runs DB migrations automatically)
up:
	docker compose up --build -d
	@echo "Waiting for backend health..."
	@for i in $$(seq 1 30); do \
		curl -sf http://localhost:8000/health >/dev/null 2>&1 && break; \
		sleep 3; \
		if [ $$i -eq 30 ]; then echo "ERROR: backend not healthy after 90s"; exit 1; fi; \
	done
	@echo "Stack is up: http://localhost:8000"

# Stop all services and remove containers (data volumes are preserved)
down:
	docker compose down

# Tail logs from all services (Ctrl+C to stop)
logs:
	docker compose logs -f

# Run backend unit test suite (SQLite mocks — no live services needed)
test:
	cd backend && PYTHONPATH=. python -m pytest tests/ -q --tb=short

# Run tests inside the running API container
test-docker:
	docker compose exec api python -m pytest tests/ -q --tb=short

# Open a shell in the running API container
shell:
	docker compose exec api /bin/bash

# Build images without starting
build:
	docker compose build

# Remove containers + volumes (WARNING: deletes local DB data)
clean:
	docker compose down -v

# ── Migrations ─────────────────────────────────────────────────────────────────
# Run Alembic migrations from your local Mac against Railway's public Postgres.
# Requires DATABASE_PUBLIC_URL in backend/.env (Railway dashboard → Postgres → Connect).
# The migration resolver automatically picks DATABASE_PUBLIC_URL over DATABASE_URL
# when RAILWAY_ENVIRONMENT is not set.
migrate-local:
	cd backend && PYTHONPATH=. alembic upgrade head

# Run migrations from inside Railway (uses Railway's internal network).
# Requires the Railway CLI: https://docs.railway.app/guides/cli
# Replace "securedoc-api" with your actual Railway service name.
migrate-railway:
	railway run --service securedoc-api sh -c "cd /app && alembic upgrade head"

# Show current migration state against the configured database
migrate-status:
	cd backend && PYTHONPATH=. alembic current
