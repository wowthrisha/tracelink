# SecureDoc Architecture

## Overview

SecureDoc is a security-first document sharing platform built on a FastAPI async backend, React frontend, PostgreSQL database, Redis cache, and Celery background workers.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Clients                              │
│           Browser (React SPA)  │  API consumers              │
└──────────────────┬──────────────┴──────────────┬────────────┘
                   │ HTTPS                        │ HTTPS + API Key
┌──────────────────▼──────────────────────────────▼────────────┐
│                      FastAPI (uvicorn)                        │
│  /static/*  │  /api/*  │  /v/*  │  /health  │  /metrics      │
│                                                               │
│  Middleware stack (outer → inner):                            │
│    HTTPSRedirect → TrustedProxy → CORS → RequestID            │
│    → SecurityHeaders → PrometheusMetrics → APIVersion         │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
    ┌───────────▼──────────┐      ┌────────────▼───────────────┐
    │   PostgreSQL (async)  │      │   Redis                    │
    │   SQLAlchemy ORM      │      │   L2 page/thumb byte cache │
    │   25 Alembic migr.    │      │   Celery broker + results  │
    └───────────────────────┘      └────────────────────────────┘
                                              │
                               ┌──────────────▼─────────────────┐
                               │   Celery Workers                │
                               │   process_document              │
                               │   deliver_webhook               │
                               │   cleanup_expired               │
                               │   beat scheduler                │
                               └─────────────────────────────────┘
                                              │
                               ┌──────────────▼─────────────────┐
                               │   Object Storage (S3/R2)        │
                               │   originals/  pages/  thumbs/  │
                               └─────────────────────────────────┘
```

## Authentication

Two authentication mechanisms:
- **Supabase JWT** (ES256, JWKS): user-facing sessions. Token extracted from `Authorization: Bearer` header, verified against cached JWKS.
- **API keys** (`sd_` prefix, SHA-256 hashed in DB): machine-to-machine access with per-key scopes (`documents:read`, `links:write`, etc.).

## Document Processing Pipeline

1. `POST /api/documents/upload` — validates file, stores to S3 `originals/`, creates DB record, queues `process_document` Celery task
2. Celery worker downloads original, dispatches to file-type adapter (PDF/DOCX/TXT)
3. PDF adapter: LibreOffice conversion (DOCX) → pdf2image rasterization → Pillow WEBP encoding → per-page storage at `pages/{doc_id}/{n}.webp` + `thumbs/{doc_id}/{n}.webp`
4. Text adapter: chunked storage for streaming delivery
5. Side effects: TOC extraction (pypdf), text extraction, OCR (optional), annotations extraction

## Viewer DRM Session Lifecycle

```
validate_link → create/resume session → heartbeat per page request
     │
     ▼
ShareLink validation:
  password check (bcrypt) → email allowlist → IP allowlist →
  max_views atomic decrement → expiry check → revocation check
     │
     ▼
DRM session (policy.py):
  session_id (32-char hex) → stored in viewer_sessions table →
  heartbeat upserts last_seen → expires after 2h inactivity
```

## Security Model

- All page images served with a per-session **visible** watermark (viewer email + timestamp, random per-session angle jitter). Separately, two near-invisible **forensic** stamps are burned into each byte: a document-level stamp (lower-right, encodes a document-ID fingerprint) and a viewer-session-level stamp (lower-left, encodes a session-ID fingerprint) — distinct from, and in addition to, the visible watermark.
- Session IDs never logged in full (first 8 chars only)
- IP addresses hashed before storage (HMAC-SHA256 with `IP_HASH_SALT`)
- Share link tokens are cryptographically random (32 bytes, URL-safe base64)
- Download-protected pages reassembled server-side; never exposed as direct S3 URLs
- SSRF guard on webhook URLs (rejects RFC-1918/link-local targets)
- CSP, X-Frame-Options, X-Content-Type-Options on all API responses

## Caching Strategy

- **L1 in-process (TTL cache)**: link snapshots (10s), doc snapshots (60s), page metadata (5min), session validation (5s) — source of truth: `LINK_TTL_SEC`/`DOC_TTL_SEC`/`PAGE_TTL_SEC`/`SESSION_TTL_SEC` in `backend/app/services/viewer_cache.py`
- **L2 Redis**: raw WEBP bytes for page images and thumbnails (TTL: `REDIS_PAGE_CACHE_TTL_SEC`, default 3600s)
- **Cache invalidation**: explicit on document reprocess, link revoke, session expiry

## Database Schema (key tables)

| Table | Purpose |
|-------|---------|
| `documents` | Document metadata, status, file_type, retention |
| `document_pages` | Per-page storage keys and dimensions |
| `share_links` | Tokens, permissions, allowlists, view counts |
| `viewer_sessions` | Active DRM sessions with heartbeat |
| `access_events` | Analytics: opens, views, downloads |
| `api_keys` | Hashed API keys with scopes |
| `org_members` | RBAC: org membership and roles |
| `webhook_configs` / `webhook_deliveries` | Webhook lifecycle |
| `annotations` / `annotation_threads` | Viewer and reviewer annotations |

## Observability

- **Structured logs**: JSON via `JSONLogFormatter`, fields include `request_id`, `correlation_id`, `user_id`, `org_id`, `doc_id`, `link_id`, `error_category`
- **Metrics**: Prometheus at `/metrics` — HTTP latency, document ops, viewer sessions, share links, webhooks, DB query latency, cache hit/miss
- **Tracing**: OpenTelemetry (OTLP export); no-op when `OTEL_EXPORTER_OTLP_ENDPOINT` unset
- **Health**: `/health` (basic), `/live` (liveness), `/ready` (DB+Redis)
