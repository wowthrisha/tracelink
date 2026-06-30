# SecureDoc V8.1.0 — Final Release Notes

**Release Date:** 2026-07-01  
**Release Type:** Enterprise Readiness  
**Sprint:** 6.5

---

## Release Summary

V8.1.0 transforms SecureDoc from a feature-complete product into a production-grade enterprise SaaS platform. This release adds no new customer-facing features — all work targets reliability, observability, security hardening, and operational excellence.

---

## What's New in V8.1.0

### Observability

- **Structured JSON logging** with 15+ fields per log record, compatible with Grafana Loki, Datadog, CloudWatch, GCP Cloud Logging, and Splunk
- **20+ Prometheus metrics** covering HTTP, viewer sessions, document operations, share links, annotations, webhooks, database latency, and cache behavior
- **X-Correlation-ID** header: clients can set their own correlation ID for cross-service tracing
- **`/live` and `/ready` health endpoints** for Kubernetes probes (in addition to existing `/health`)
- **IP field in access logs** for security monitoring and rate limit analysis

### Security Hardening

- **Production startup blocked** on default placeholder secrets (`IP_HASH_SALT`, `DOMAIN_VERIFY_SALT`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`)
- **`SUPABASE_ANON_KEY` added** to mandatory production config checks
- **IP allowlist validation** uses Python `ipaddress` module — invalid CIDRs rejected at API layer with 422

### API

- **`X-API-Version: 2024-01`** response header on all responses for client compatibility detection

### Metrics Wiring

New Prometheus metrics are now instrumented at callsites:
- `securedoc_share_links_created_total` / `_revoked_total` — wired in `links.py`
- `securedoc_viewer_sessions_total{outcome}` — wired in `viewer_session_service.py`
- `securedoc_annotations_total{type,action}` — wired in `annotations.py`
- `securedoc_webhook_deliveries_total{outcome}` + `_retries_total` — wired in `webhook_tasks.py`
- `securedoc_upload_duration_seconds` + `document_uploads_total` — wired in `documents.py`
- `securedoc_processing_duration_seconds{stage}` — wired in `tasks.py`

### Documentation

9 new documentation files added:
- `docs/architecture/ARCHITECTURE.md`
- `docs/deployment/DEPLOYMENT.md` (enhanced)
- `docs/api/API.md`
- `docs/security/SECURITY.md`
- `docs/operations/RUNBOOK.md`
- `docs/operations/INCIDENT_RESPONSE.md`
- `docs/operations/BACKUP_RESTORE.md`
- `docs/operations/SCALING.md`
- `docs/development/DEVELOPER_GUIDE.md`

### CI/CD

New GitHub Actions pipeline (`.github/workflows/ci.yml`):
- Ruff lint
- Full pytest suite (1624 tests) against real PostgreSQL + Redis
- Alembic migration smoke test
- Frontend build
- pip-audit + npm audit
- Bandit SAST scan
- Docker build

---

## Files Changed

### Backend

| File | Change |
|------|--------|
| `app/main.py` | Added `/live`, `/ready`, `X-API-Version` middleware, `SUPABASE_ANON_KEY` startup check |
| `app/config.py` | HSTS model validator (restored), production startup checks in main.py |
| `app/metrics.py` | 11 new Prometheus metrics |
| `app/middleware/json_logging.py` | Added `correlation_id`, `org_id`, `error_category` log fields |
| `app/middleware/request_id.py` | X-Correlation-ID support, `ip=` in access log |
| `app/routers/links.py` | `share_links_created/revoked_total` metrics |
| `app/routers/documents.py` | `upload_duration_seconds` + `document_uploads_total` metrics |
| `app/routers/annotations.py` | `annotations_total` metrics |
| `app/services/viewer_session_service.py` | `viewer_sessions_total` metrics |
| `app/workers/webhook_tasks.py` | `webhook_deliveries_total` + `webhook_retries_total` metrics |
| `app/workers/tasks.py` | `processing_duration_seconds` metrics |

### Infrastructure

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | New 7-job CI/CD pipeline |

### Documentation (new files)

9 documentation files added across `docs/api/`, `docs/security/`, `docs/operations/`, `docs/development/`.

### Release Documents (new files)

| File | Description |
|------|-------------|
| `docs/release/ENTERPRISE_READINESS_CERTIFICATION.md` | Enterprise certification |
| `docs/release/OPERATIONAL_EXCELLENCE_REPORT.md` | 10-domain scorecard |
| `docs/release/OBSERVABILITY_REPORT.md` | Full observability reference |
| `docs/release/PERFORMANCE_BENCHMARK.md` | Benchmark data and recommendations |
| `docs/release/DEPENDENCY_AUDIT.md` | pip-audit + npm audit findings |
| `docs/release/FINAL_RELEASE_NOTES.md` | This document |

---

## Test Results

```
Backend: 1624 passed, 1 skipped, 0 failed
Frontend: 13 passed, 0 failed
Frontend build: Clean (no errors or warnings)
pip-audit: 6 packages with vulnerabilities (see DEPENDENCY_AUDIT.md)
npm audit: 0 vulnerabilities
```

---

## Known Issues / Remediation Items

| Issue | Severity | Sprint |
|-------|---------|--------|
| starlette path traversal CVE-2025-54121 | HIGH | 6.6 |
| python-multipart DoS vulnerabilities | HIGH | 6.6 |
| pyjwt algorithm confusion CVE | HIGH | 6.6 |
| cryptography RSA validation CVE | MEDIUM | 6.6 |
| pillow image parsing CVE | MEDIUM | 6.7 |
| pypdf parsing CVEs (20+) | MEDIUM | 6.7 |

---

## Upgrading

V8.1.0 is a drop-in upgrade from V3.x. No schema changes (migrations 001–025 unchanged). No breaking API changes.

```bash
# 1. Pull new image
docker pull securedoc/backend:8.1.0

# 2. Run migrations (no changes from V3.x, safe to run)
alembic upgrade head

# 3. Verify new endpoints
curl https://api.yourapp.com/live   # → {"status": "alive"}
curl https://api.yourapp.com/ready  # → {"status": "ready"}

# 4. Verify API version header
curl -I https://api.yourapp.com/health | grep X-API-Version
# → X-API-Version: 2024-01
```

---

## Next Release: V8.2.0 (Sprint 6.6)

- Dependency upgrades (security remediation)
- Dead-letter queue (DLQ) explicit Celery routing
- API version deprecation framework
- Pagination for audit log endpoints
