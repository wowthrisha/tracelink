# SecureDoc — Architecture Overview

**Last Updated:** 2026-06-30
**Version:** 8.1.0 (RC-1)

---

## System Architecture

SecureDoc is a secure document sharing platform. Documents are uploaded once and shared via per-recipient links with granular access controls, viewer analytics, and revocation.

```
Browser (Viewer)
    └─▶ Share link  /v/{token}
            └─▶ FastAPI backend  :8000
                    ├─▶ Supabase Auth  (JWT / SAML)
                    ├─▶ PostgreSQL     (state)
                    ├─▶ Redis          (cache + Celery broker)
                    ├─▶ Object Storage (S3-compatible via Supabase)
                    └─▶ Celery Worker  (PDF processing pipeline)
```

## Layer Summary

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend API | FastAPI + SQLAlchemy async | Single process, 2 uvicorn workers |
| Database | PostgreSQL 16 | 26 Alembic migrations, advisory-lock safe |
| Cache / Broker | Redis 7 | L2 page cache + Celery broker |
| Storage | Supabase Storage (S3-compatible) | Demo mode: local disk |
| Auth | Supabase JWT (ES256 via JWKS) | API keys also accepted (`sd_` prefix) |
| Task queue | Celery + Celery Beat | PDF pipeline, session cleanup, upload recovery |
| Frontend | React (esbuild IIFE bundle) | 249.3 KB, served by backend via `/static/` |

## Component Graph (Frontend)

```
AppShell
├── UploadScreen        — document library, upload, retention policy
├── ViewerScreen        — paginated PDF viewer, DRM, watermark
│   ├── ViewerToolbar   — zoom, fit, search, laser, magnifier
│   ├── TocSidebar      — table of contents
│   ├── SearchPanel     — full-text search across pages
│   ├── LinksPanel      — hyperlinks extracted from PDF
│   ├── AnnotationLayer — per-page annotations
│   └── InsightsModal   — AI-ready insights surface
├── AccessScreen        — share link management, per-link controls
├── AnalyticsScreen     — view analytics, by document / by group
├── StorageScreen       — storage usage, forecast, cleanup
├── ApiKeysScreen       — API key management
├── WebhooksScreen      — outbound webhook endpoints
├── AuditLogScreen      — admin audit trail
├── OrgsScreen          — multi-org / SSO configuration
├── NotificationsScreen — recent activity feed
└── BillingScreen       — plan and Stripe integration
```

## Key Design Decisions

See [`docs/architecture/adr/`](adr/) for full records. Summary:

| ADR | Decision |
|-----|---------|
| ADR-001 | HSTS enabled by default (1 year + preload) |
| ADR-002 | Atomic `UPDATE … RETURNING` for max_views enforcement |
| ADR-003 | Per-viewer forensic stamp applied at serve time |
| ADR-004 | 5-second session cache TTL to reduce DB load |
| ADR-005 | JSON logging enabled by default |
| ADR-006 | CDN for thumbnails only (full pages stay watermarked) |
| ADR-007 | Streaming download via pypdf PdfWriter |
| ADR-008 | Prometheus native client for metrics |
| ADR-009 | PPTX via LibreOffice (same pipeline as DOCX) |
| ADR-010 | SSO via Supabase SAML (no additional vendor) |

## Data Flow — Document Upload

```
1. Browser → POST /api/documents  (multipart upload)
2. API → Object Storage           (raw file saved)
3. API → Celery task queue        (enqueue processing job)
4. Worker: extract_and_store_pdf_toc       → toc.json sidecar
           extract_and_store_links_sidecar → links.json sidecar
           extract_and_store_word_positions→ words.json sidecar
           extract_and_store_text_sidecar  → text.json sidecar
5. Worker: rasterize pages → page_N.webp in storage
6. DB status: "uploaded" → "processing" → "ready"
```

## Data Flow — Document View

```
1. Browser → GET /v/{token}              → SecureDoc.html
2. Browser → POST /api/viewer/session    → session_id
3. Browser → GET /api/viewer/page/{n}   → watermarked JPEG
             (L1 in-process LRU cache → L2 Redis → Object Storage → rasterize)
4. Events logged: page_viewed, time_spent_ms, IP, device
```

## Security Model

- All page bytes served through the API proxy — object storage URLs never exposed
- Per-session visible watermark (viewer email + timestamp) applied at serve time
- Forensic stamp burned into each byte at document-stamp time (lower-right) and viewer-stamp time (lower-left)
- Rate limiting on viewer endpoints; IP allowlist per link
- Session revocation propagates within 5 seconds (session cache TTL)
- Link revocation propagates within 10 seconds (link cache TTL)
- DRM controls (print, copy, right-click) are client-side UX gates; server enforces per-request
