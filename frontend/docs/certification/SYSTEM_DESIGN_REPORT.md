# SYSTEM DESIGN REPORT — Sprint 6.0 Engineering Excellence
**Date:** 2026-06-29  
**Sprint:** 6.0 (supersedes Sprint 5.5)  
**Method:** Full source code review of all routers, services, workers, middleware, models, and utilities

---

## Architecture Overview

```
Browser ──HTTPS──▶ FastAPI (port 8000)
                      │
                      ├── /static/    (React IIFE bundle, 248 KB)
                      ├── /api/       (REST endpoints)
                      └── /app        (redirect to /static/SecureDoc.html)

FastAPI Middleware Stack (outer → inner):
  PrometheusMiddleware
  TrustedProxyMiddleware
  SecurityHeadersMiddleware
  RequestIDMiddleware
  RateLimitMiddleware (slowapi)
  CORSMiddleware

FastAPI Routers:
  auth → /api/auth
  documents → /api/documents
  links → /api/links
  viewer → /api/viewer
  analytics → /api/analytics
  storage → /api/storage
  groups → /api/groups
  webhooks → /api/webhooks
  api_keys → /api/api-keys
  orgs → /api/orgs
  admin → /api/admin
  billing → /api/billing
  notifications → /api/notifications
  annotations → (viewer/documents sub-paths)

Services:
  analytics_service.py  — analytics aggregation
  audit_service.py      — immutable audit log writes
  webhook_service.py    — webhook dispatch (Celery)
  link_service.py       — link operations + cache invalidation
  viewer_service.py     — session, access control helpers
  policy.py             — IP allowlist, session enforcement
  storage.py            — S3/R2/local file storage abstraction
  rasterizer.py         — PDF → WebP page rendering
  watermark.py          — visible + forensic watermarking

Workers:
  Celery (Redis broker) → webhook_tasks.py, worker/tasks.py
```

---

## Layer Separation Assessment

| Layer | Assessment |
|-------|-----------|
| Routers | Route handling only — business logic delegated to services. CLEAN. |
| Services | Business logic only — no HTTP concerns. CLEAN. |
| Models | SQLAlchemy ORM models only — no business logic. CLEAN. |
| Middleware | Cross-cutting concerns only (auth, CORS, headers, metrics). CLEAN. |

---

## API Contract Assessment

All API contracts reviewed. Key findings:

### REST conventions: CORRECT
- POST for create (201)
- GET for read
- PATCH for partial update (returns updated resource)
- DELETE for remove (204 for hard deletes)
- All error responses use `{"detail": "..."}` FastAPI standard format

### Pagination: CONSISTENT
- All list endpoints: `limit`, `offset`, `total` in response
- Default limits are bounded (50–100)
- Max limits enforced (200–500)

### Null handling in PATCH: CORRECT
- `links.py` and `groups.py` use `model_fields_set` to distinguish "field not sent" vs "field sent as null"
- Allows explicitly clearing optional fields (e.g., expiry, allowed_emails)

---

## Cache Invalidation Assessment

### Viewer cache layers
- L1: in-process LRU cache (TTL 10s for links, 60s for docs, 5min for pages)
- L2: Redis page byte cache (bypassed if Redis unavailable)
- Cache evicted on link mutations via `invalidate_link()` in `link_service.py`

### Missing cache invalidation
- **VERIFIED**: All link mutation paths (create, update, revoke, hard delete) call `invalidate_link()`. No cache staleness.

---

## Error Handling Assessment

| Pattern | Assessment |
|---------|-----------|
| Audit failure is non-fatal | `audit_service.log_audit_event()` wraps in try/except, never raises. ✅ |
| Webhook failure is non-fatal | `dispatch_webhook_event()` catches exceptions; analytics.py try/except around call. ✅ |
| Celery task failure is non-fatal | Upload, reprocess, extract-sidecars all catch Celery failures and log. ✅ |
| Storage failure → 502/503 | Storage exceptions mapped to HTTP errors at router layer. ✅ |
| DB failure → 500 | Unhandled DB exceptions propagate as 500. Acceptable — DB failure is unrecoverable. |

---

## Database Design Assessment

### Migrations
25 migrations total (001–025). Each is independently reversible with `downgrade()`. Migration 025 added critical performance indexes identified in Sprint 5.3.

### Schema highlights
| Model | Key design |
|-------|-----------|
| ShareLink | `revoked_at` timestamp pattern (not a boolean) — enables time-of-revocation auditing |
| AccessEvent | `link_id` FK (not document_id) — enforces event ownership through link |
| AdminAuditLog | Append-only by convention; no UPDATE or DELETE paths in codebase |
| APIKey | Key stored as SHA-256 hash only; prefix stored for display |
| WebhookEndpoint | `is_active` flag; events as JSON array on the endpoint record |

---

## Scalability Concerns

| Concern | Severity | Note |
|---------|----------|------|
| `link_ids = [...]` in `get_events` | MEDIUM | For users with many links, large IN() clause. Acceptable until thousands of links. |
| No request-level DB connection pooling tuning | LOW | Using default SQLAlchemy pool. Sufficient for beta. |
| Analytics overview runs 4 separate COUNT queries | LOW | Each is indexed. Acceptable. Could be cached per-user with 60s TTL in future. |
