# Production Readiness Report
Production Readiness Audit — Phase 5
Date: 2026-06-22
Source: Direct code reading. Verified from source files, not historical reports.

---

## Executive Summary

SecureDoc is production-ready for its core use case: secure document sharing with viewer analytics. The document viewer, access control, annotation system, and analytics pipeline are all working end-to-end. The platform has a strong security foundation (session-scoped tokens, DRM controls, rate limiting, forensic watermarking).

The primary production gap is feature completeness, not stability or security: five complete backend features (Webhooks, API Keys, Organizations, SSE, Admin Audit Log) have no frontend UI, and there is no email notification when a viewer opens a document.

One P0 item requires immediate user action: credentials committed to git history (see TD-002).

---

## Score by Dimension

### 1. Security — 81/100

**Strengths:**
- Share link tokens in `sessionStorage` (tab-scoped; cleared on tab close)
- SRI integrity hashes on React/ReactDOM CDN loads (`sha384-...`)
- Rate limiting on all sensitive endpoints: viewer validate (20/min), page (120/min), analytics events (60/min), auth
- IP allowlist per share link (server-enforced)
- Forensic watermark (`apply_viewer_forensic_stamp()`) embeds viewer identity in metadata
- Visual watermark overlay for viewer identification
- Session expiry + 401 recovery flow (re-authenticates without full reload)
- `rel="noopener noreferrer"` + `target="_blank"` on all external links
- No `dangerouslySetInnerHTML` anywhere in source
- No `innerHTML` assignment anywhere in source
- Supabase credentials are placeholders in HTML (injected at deploy time)

**Vulnerabilities:**
- `link.url` rendered as `href` without `javascript:` protocol check (FE-R-064 / TD-001) — MEDIUM, fixable in 10 minutes
- Auth JWT (`securedoc_token`) in `localStorage` — MEDIUM, accepted tradeoff for SPA architecture
- Credentials in git history (TRACEVIEW_AUDIT_B.md) — P0, requires user action

**Score breakdown:**
- Auth model: 18/20 (−2 localStorage token)
- Input sanitization: 17/20 (−3 link.url href gap)
- Transport security: 20/20 (HSTS, SRI, HTTPS)
- Rate limiting: 18/20 (−2 in-process, not Redis-backed)
- Session model: 20/20 (sessionStorage, tab-scoped, 401 recovery)
- Credentials hygiene: −12 (committed credential, P0 issue)

**Score: 81/100** — would be 93/100 after fixing TD-001 and TD-002

---

### 2. Reliability — 76/100

**Strengths:**
- Celery async document processing (202 + poll — uploads never block on processing)
- Celery worker task recovery: `requeue_orphaned_uploads` task handles stuck uploads
- `purge_stale_sessions` maintenance task
- Streaming document viewer (images loaded per-page, not full PDF)
- 401 recovery in viewer (session re-established without losing page position)
- `upload_error` state handled in UploadScreen (processing failure surfaced to user)

**Weaknesses:**
- LibreOffice subprocess for DOCX/PPTX/XLSX — single point of failure for 4 of 5 supported formats (TD-012)
- Rate limiting is per-process (effective on single instance only) (TD-010)
- No health check endpoint visible in routers (standard `/health` or `/ready`)
- No error tracking integration (no Sentry or similar) — failures are logged but not alerted
- SSE connection registry is in-process (failures invisible across instances) (TD-011)

**Score: 76/100**

---

### 3. Maintainability — 84/100

**Strengths:**
- 50 source files in purpose-named directories after Sprint 4.2D extraction
- 5-line app.jsx entry point (no logic in entry point)
- Zero dead code, zero broken imports, zero feature flags
- All 43 relative import paths resolve correctly
- Consistent styling pattern (C/mono from tokens.js)
- Single bundle (198 kb, 0 warnings)
- Hooks are single-responsibility (useViewerSession, useAnnotations, useSearch, useToc, etc.)

**Weaknesses:**
- `api.js` at 769 lines with ~30 duplicated 401 handlers, 5 copy-pasted blob-download sequences (TD-005)
- `buildFeedbackFilters` duplicated in api.js and utils/feedback.js (TD-005)
- BillingScreen bypasses SecureDocAPI pattern (TD-008)
- ViewerScreen.jsx at 872 lines — largest component, multiple responsibilities
- esbuild targets Chrome 80 (2020) — generates unnecessarily verbose output (TD-009)
- SAML domain field in model with no implementation or documentation (TD-014)

**Score: 84/100**

---

### 4. Observability — 73/100

**Strengths:**
- Analytics event logging: every viewer action creates an `access_events` row
- Page heatmap data available (`GET /api/analytics/page-heatmap`)
- Backend has structured logging (FastAPI request logs)
- Backend has OTel + Prometheus metrics (confirmed in SECURITY_AUDIT_REPORT.md)
- Per-viewer access log with email, IP, timestamp
- DRM blocked actions logged to analytics events (audit trail for print/copy blocks)

**Weaknesses:**
- No error tracking integration (Sentry or equivalent) — errors logged to console only
- No frontend error boundary logging to backend
- No alerting on failed Celery tasks (failed processing is visible in DB status but generates no alert)
- No real-time uploader notification (must poll AnalyticsScreen)
- No operational dashboard (is the system healthy? are workers running?)
- SSE exists but is not wired to events — real-time updates never reach the frontend

**Score: 73/100**

---

### 5. Scalability — 69/100

**Strengths:**
- Celery + Redis for async processing (workers scale independently of API)
- Server-rasterized pages (viewer is stateless — any API instance can serve any page)
- Session validation in `policy_enforcer` with 5-second TTL cache
- R2/S3-compatible storage (not local disk)
- Streaming chunked text for large text documents

**Weaknesses:**
- Rate limiting is in-process — ineffective under horizontal scaling (TD-010)
- SSE connection registry is in-process — notifications break across instances (TD-011)
- Viewer session creation creates per-session DB rows — could contend under high concurrent views
- No read replicas or connection pooling evidence in models (SQLAlchemy async, but no pool configuration visible)
- LibreOffice conversion is not containerized as a separate service — CPU-intensive conversion blocks the worker

**Score: 69/100**

---

### 6. Product Completeness — 64/100

**Core value proposition: fully implemented (adds full points)**
- Secure link creation: ✅
- Document viewer (PDF + Office + Text): ✅
- Per-viewer analytics + heatmaps: ✅
- DRM controls: ✅
- Annotations + feedback + export: ✅
- Watermarking (visual + forensic): ✅
- Billing (Stripe): ✅

**Major gaps (each deducts points):**
- No email notification when viewer opens document: −10 (critical daily use case)
- No frontend for Webhooks: −5 (integration story blocked)
- No frontend for API Keys: −5 (developer use case blocked)
- No frontend for Organizations / team management: −7 (multi-user blocked)
- No version history creation flow: −3 (model exists, not accessible)
- SSE not wired to frontend: −3 (real-time updates never delivered)
- No NDA gate: −3 (DocSend parity gap)

**Score: 64/100**

---

## Overall Production Readiness Score

| Dimension | Weight | Score | Weighted |
|---|---|---|---|
| Security | 25% | 81 | 20.25 |
| Reliability | 20% | 76 | 15.20 |
| Maintainability | 15% | 84 | 12.60 |
| Observability | 15% | 73 | 10.95 |
| Scalability | 10% | 69 | 6.90 |
| Product Completeness | 15% | 64 | 9.60 |
| **TOTAL** | **100%** | | **75.5 / 100** |

**Overall: 76/100 — Production Ready with Caveats**

---

## Verdict by Use Case

| Deployment Context | Ready? | Blocker |
|---|---|---|
| Single-user document sharing | ✅ Yes | None |
| Small team (2–5 users, same account) | ✅ Yes | None |
| Multi-user organization (separate accounts) | ⚠️ Not yet | No org management UI |
| API-driven integration (CRM, zapier) | ⚠️ Not yet | No API key UI |
| Enterprise with SSO | ❌ No | SAML not implemented |
| Public/OSS repository | ❌ No | Credentials in git history — P0 |

---

## P0 Items (Must Fix Before Any Public Launch)

1. **TD-002: Rotate Supabase credentials and scrub git history.** `TRACEVIEW_AUDIT_B.md` contains `sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc` and the Supabase URL. Execute `SECRET_ROTATION_RUNBOOK.md`. This is a user action (requires Supabase dashboard access). BFG repo-cleaner or `git-filter-repo` to scrub commits ffac077, 704ca80, cc50838.

2. **TD-001: Add `javascript:` protocol guard to LinksPanel.jsx.** 10-minute fix. Sprint 4.3 Phase 4.

---

## P1 Items (Fix Before Growth Phase)

3. **TD-003: Email notification when viewer opens document.** #1 daily-use-case gap.

4. **TD-004: Add frontend for Webhooks + API Keys.** Two simple settings screens to unlock the integration market.

5. **TD-004 (cont): Add Organization management screen.** Multi-user workflows require this.
