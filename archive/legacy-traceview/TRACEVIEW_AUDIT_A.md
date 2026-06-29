> **HISTORICAL ARCHIVE** — Reflects repository state before Sprint 4.2D extraction (2026-06-22). Not current. Do not use for active decision-making.

# TRACEVIEW ARCHITECTURE, REPOSITORY, API & SYSTEM DESIGN AUDIT
## Phase A — Structural, Design, and Maintainability Audit

**Audit Date:** 2026-06-01  
**Auditor Role:** Principal Software Architect / Staff Backend+Frontend / Security-Aware Systems Engineer  
**Repository:** `/Users/thrisha/traceview/securedoc/`  
**Scope:** Phase A only — structure, design, APIs, components, hygiene, debt. No security deep-dives, no scalability analysis.

---

## SECTION 1 — FULL REPOSITORY INVENTORY

### Top-Level Structure

```
securedoc/
├── backend/                    # FastAPI application + workers + tests
├── frontend/                   # React SPA (HTML shell + JSX bundle)
├── tests_e2e/                  # End-to-end test suite (separate from backend/tests/)
├── docker-compose.yml          # Multi-service local deployment
├── Makefile                    # Convenience targets (up/down/test/migrate)
├── start.sh                    # One-command dev launcher
├── README.md                   # Project documentation
├── HARDENING_REPORT.md         # Hardening audit report (previous pass)
├── test_*.db (×4)              # ⚠ LEAKED test SQLite databases at root level
```

### backend/ Directory

| Path | Purpose | Responsibilities | Coupling | Concern |
|------|---------|-----------------|---------|---------|
| `app/main.py` | App factory, ASGI entry | Router wiring, middleware stack, lifespan hooks, health endpoint | Medium | Version string `8.0.0` hardcoded; no constants |
| `app/config.py` | Settings (pydantic-settings) | All env config via `Settings`, `lru_cache` singleton | Low | Phase comments in config keys (e.g. `# Phase 7`, `# Phase 8`) — cosmetic but noisy |
| `app/database.py` | Async SQLAlchemy engine | Engine factory, URL normalization, Railway guard, `get_db` dep | Low | Clean and well-structured |
| `app/auth.py` | Supabase JWT verification | JWKS fetch+cache, token verification, user extraction | Low | Module-level mutable globals (`_jwks_cache`, `_jwks_fetched_at`) — not thread-safe in multi-process mode, but acceptable for asyncio workers |
| `app/models/` | SQLAlchemy ORM models | Schema definitions | Low | `group.py`: `user_id` is `nullable=True` in the ORM but migration 007 sets `Document.user_id NOT NULL`. `DocumentGroup.user_id` was never hardened — groups can still be orphaned |
| `app/schemas/` | Pydantic request/response shapes | Input validation, output serialization | Low | `schemas/event.py,cover` committed — ghost of a file that was deleted |
| `app/routers/` | FastAPI route handlers | HTTP contract, auth enforcement, orchestration | Medium | `viewer.py` is large (~990 lines) and has significant repeated cache-lookup boilerplate across all viewer endpoints |
| `app/services/` | Business logic services | Core algorithms, storage, policy, analytics | Medium | `document_adapter.py` exists but is **never imported by any router or service** — only in tests |
| `app/services/toc/` | Table-of-contents extraction | Multi-format TOC extraction, model, cache | Low | `toc/cache.py` provides L2 Redis TOC caching, but `viewer.py` bypasses it entirely — uses `viewer_cache.toc_cache` (L1 only) instead |
| `app/workers/` | Celery task processing | Document processing pipeline, periodic tasks | Medium | Single `tasks.py` file handles PDF, text, DOCX, DOC, TOC extraction, stale session purge, orphan requeue — conceptually multi-function |
| `app/middleware/` | ASGI middleware | CORS, rate limit, proxy trust, security headers, request ID, HTTPS redirect, JSON logging | Low | Well-structured and modular |
| `app/utils/` | Crypto primitives | Password hashing, IP/value hashing, email masking | Low | `token.py,cover` committed — dead file (token.py was deleted, but coverage artifact remained) |
| `alembic/` | DB migrations | Schema versioning | Low | 10 migrations, clean sequential chain |
| `demo_storage_patch.py` | Dev-only storage mock | Monkey-patches storage to disk | Low | Appropriate isolation with production guard |
| `run_demo.py` | Dev server entry point | Starts uvicorn with optional demo storage | Low | Fine as-is |
| `migrate.py` | Advisory-locked migration runner | Wraps alembic with pg_advisory_lock | Low | Good pattern; clean |
| `htmlcov/` | Coverage HTML report | Build artifact | N/A | ⚠ Should not be in repo (non-functional docs) |
| `backend/.coverage` | Coverage data file | Build artifact | N/A | ⚠ Should not be in repo |
| `backend/*.db` (×4) | Test SQLite databases | Leftover from test runs | N/A | ⚠ Generated at runtime, should not persist in working tree |

### frontend/ Directory

| Path | Purpose | Responsibilities | Concern |
|------|---------|-----------------|---------|
| `SecureDoc.html` | HTML entry point | Loads CDN React + api.js + app.bundle.js, minimal shell (231 lines) | Clean |
| `api.js` | API client module | Auth, all fetch wrappers, URL detection | Clean (382 lines) |
| `src/app.jsx` | Single-file React application | Entire frontend (4,083 lines) | ⚠ See Section 4 |
| `dist/app.bundle.js` | Compiled esbuild output | Pre-compiled for Docker | ⚠ Build artifact committed — by design (see Section 10) |
| `package.json` | Node build tooling | esbuild dev dependency | Clean |
| `node_modules/` | Build toolchain | esbuild binary | ⚠ Committed? See Section 10 |

### tests_e2e/ Directory

| Path | Purpose |
|------|---------|
| `api/` | Contract tests against live stack |
| `services/` | Service-level unit tests (SQLite) |
| `ui/` | Playwright browser tests |
| `e2e/` | Full flow scenarios |
| `fixtures/minimal.pdf` | Shared test fixture |

### Orphaned / Stale / Misplaced Items

| Item | Type | Severity |
|------|------|---------|
| `securedoc/test_*.db` (×4 at root) | Duplicate test artifacts | HIGH |
| `backend/app/utils/token.py,cover` | Ghost coverage file for deleted `token.py` | HIGH |
| `backend/app/schemas/event.py,cover` | Ghost coverage file for never-created `schemas/event.py` | MEDIUM |
| `backend/htmlcov/` | HTML coverage report directory | MEDIUM |
| `backend/.coverage` | Binary coverage data | LOW |
| `backend/app/services/document_adapter.py` | Architecture stub — **not used in production code**, only in tests | MEDIUM |
| `backend/app/services/toc/cache.py` | L2 Redis TOC cache — **not called by viewer.py** (bypassed by direct viewer_cache access) | MEDIUM |
| Phase comments throughout `config.py` | Maintenance noise | LOW |

---

## SECTION 2 — SYSTEM DESIGN REVIEW

### Architecture Flow Diagram

```
Browser (React SPA)
        │
        │  HTTPS / Bearer JWT
        ▼
┌─────────────────────────────────────────┐
│            Middleware Stack              │
│  CORS → TrustedProxy → RequestID        │
│  → SecurityHeaders → Route              │
└────────────────┬────────────────────────┘
                 │
        ┌────────▼──────────────┐
        │    FastAPI Routers     │
        │  /api/documents        │
        │  /api/links            │
        │  /api/viewer           │
        │  /api/analytics        │
        │  /api/groups           │
        │  /api/billing          │
        │  /health               │
        └───────────────────────┘
                 │
     ┌───────────┼───────────────────┐
     │           │                   │
     ▼           ▼                   ▼
Services      Auth/Policy         Storage
(Analytics,   (PolicyEnforcer,    (StorageBackend
 LinkService,  auth.py)            → S3/R2/Demo)
 viewer_cache,
 page_cache)
     │           │
     ▼           ▼
  Database      Redis
(PostgreSQL   (Page cache L2,
 via async     Celery broker,
 SQLAlchemy)   session storage)
                    │
              ┌─────▼──────┐
              │ Celery      │
              │ Workers     │
              │ (PDF/Text/  │
              │  DOCX/DOC   │
              │  pipelines) │
              └─────────────┘
```

### Viewer Architecture — Rating: 7/10

**Strengths:** L1/L2 cache layers (viewer_cache + page_cache) are cleanly separated. Watermark offloaded to thread pool. Session heartbeat throttling. Proxy-aware IP resolution.

**Concerns:**
- `/page`, `/thumb`, `/toc`, `/text` routes each duplicate the same 3-stage cache-lookup prologue (link → doc → page metadata). ~80 lines of identical boilerplate repeated 4+ times.
- `/toc` endpoint bypasses `toc/cache.py` entirely and directly manipulates `toc_cache` from `viewer_cache`. The dedicated `toc/cache.py` module (with L2 Redis support) is dead code from the viewer's perspective.
- Download endpoint (`/download`) does not use the viewer metadata cache at all — re-reads link/doc from DB fresh.

### Upload Architecture — Rating: 8/10

**Strengths:** Type detection (extension + magic bytes + content-type), quota gating, demo/production mode dispatch, async task queuing with graceful failure logging.

**Concerns:**
- File type validation split across two files (`documents.py` validates `ALLOWED_CONTENT_TYPES`, then `text_processor.detect_file_type()` re-validates). Double-check pattern is acceptable but slightly inconsistent.
- `_run_demo_processing()` inside `documents.py` imports from deep internal paths — creates coupling between the router and worker internals.

### Processing (Worker) Architecture — Rating: 7/10

**Strengths:** Clear dispatch pattern (`process_document_with_session` → `_process_pdf/text/docx/doc`), stale processing recovery, retry/no-retry distinction, TOC extraction as best-effort side effect.

**Concerns:**
- `tasks.py` is a monolith: 4 document pipelines + 2 periodic tasks + async engine management all in one file (~580 lines). Should be split.
- `_process_docx_document` and `_process_doc_document` are essentially identical pipelines with one different step.
- Error state (`_mark_document_error`) can race with the retry path; no idempotency guard on the error write.

### Analytics Architecture — Rating: 8/10

**Strengths:** `AnalyticsService` is well-isolated. Batch queries to avoid N+1. Risk scoring, event aggregation, and group rollup are all centralized. `commit=False` pattern for batching.

**Concerns:**
- `BLOCKED_EVENT_TYPES` defined in `analytics_service.py` but `VIEWER_LOGGABLE_EVENTS` defined in `models/event.py` — the split requires importing from both when deciding what to log.
- `get_document_analytics` runs 6 GROUP BY queries sequentially; could be parallelized.

### Storage Architecture — Rating: 9/10

**Strengths:** `StorageBackend` ABC enforces a clean interface. Dedicated thread pool separates S3 I/O from CPU work. R2/MinIO compatibility via config. `file_exists()` method added.

**Concerns:**
- `DemoStorageService` (in `demo_storage_patch.py`) does not extend `StorageBackend` — it re-implements all methods ad-hoc and would not be caught by type checks.
- Storage key structure (`originals/`, `pages/`, `thumbs/`, `toc/`) is implicit and scattered; no central key-scheme module.

### Cache Architecture — Rating: 8/10

**Strengths:** Clean L1/L2 design. TTL values chosen per data volatility. `invalidate_link()` called synchronously on revocation. Metadata cache (`viewer_cache.py`) and byte cache (`page_cache.py`) correctly separated.

**Concerns:**
- `toc/cache.py` introduces a third "L2 Redis TOC" cache that is never called by `viewer.py`. The viewer uses `viewer_cache.toc_cache` (L1) directly, making `toc/cache.py` effectively dead code in the hot path.
- L1 metadata cache uses FIFO eviction (not LRU) — under non-uniform access patterns, hot entries can be evicted before cold ones.
- No cache invalidation when a link's `allowed_emails` or `allowed_domains` changes via PATCH (only token eviction on revoke).

### Worker Architecture — Rating: 7/10

See Processing section. The beat schedule is correct and `acks_late=True` + `reject_on_worker_lost=True` is sound.

---

## SECTION 3 — API AUDIT

### Route Inventory

| Route | Method | Router | Auth | Purpose | Consumer |
|-------|--------|--------|------|---------|---------|
| `/api/documents` | GET | documents | JWT | List user documents with stats | Dashboard |
| `/api/documents/upload` | POST | documents | JWT | Upload document | Dashboard |
| `/api/documents/{id}` | GET | documents | JWT | Get document detail with pages | Dashboard |
| `/api/documents/{id}/status` | GET | documents | JWT | Poll processing status | Dashboard |
| `/api/documents/{id}` | DELETE | documents | JWT | Delete document + storage | Dashboard |
| `/api/links` | GET | links | JWT | List links for document | Dashboard |
| `/api/links` | POST | links | JWT | Create share link | Dashboard |
| `/api/links/{id}` | DELETE | links | JWT | Revoke link | Dashboard |
| `/api/links/{id}` | PATCH | links | JWT | Update link policy | Dashboard |
| `/api/viewer/gate/{token}` | GET | viewer | None | Gate requirements check | Viewer SPA |
| `/api/viewer/validate` | POST | viewer | None | Validate link → create session | Viewer SPA |
| `/api/viewer/page/{token}/{page}` | GET | viewer | Session | Serve watermarked page | Viewer SPA |
| `/api/viewer/thumb/{token}/{page}` | GET | viewer | Session | Serve thumbnail | Viewer SPA |
| `/api/viewer/toc/{token}` | GET | viewer | Session | Table of contents | Viewer SPA |
| `/api/viewer/download/{token}` | GET | viewer | Session | Download watermarked doc | Viewer SPA |
| `/api/viewer/text/{token}/{chunk}` | GET | viewer | Session | Serve text chunk | Viewer SPA |
| `/api/analytics/overview` | GET | analytics | JWT | Dashboard KPIs | Dashboard |
| `/api/analytics/documents` | GET | analytics | JWT | Per-document analytics | Dashboard |
| `/api/analytics/groups` | GET | analytics | JWT | Per-group analytics | Dashboard |
| `/api/analytics/events` | GET | analytics | JWT | Raw event log | Dashboard |
| `/api/analytics/events` | POST | analytics | Session | Log viewer event | Viewer SPA |
| `/api/groups` | GET | groups | JWT | List user groups | Dashboard |
| `/api/groups` | POST | groups | JWT | Create group | Dashboard |
| `/api/groups/{id}` | GET | groups | JWT | Get group | Dashboard |
| `/api/groups/{id}` | PATCH | groups | JWT | Update group | Dashboard |
| `/api/groups/{id}` | DELETE | groups | JWT | Delete group | Dashboard |
| `/api/groups/{id}/documents` | PUT | groups | JWT | Assign documents to group | Dashboard |
| `/api/groups/{id}/documents/{did}` | DELETE | groups | JWT | Remove document from group | Dashboard |
| `/api/billing/status` | GET | billing | JWT | Get billing state | Dashboard |
| `/api/billing/checkout` | POST | billing | JWT | Create Stripe checkout | Dashboard |
| `/api/billing/portal` | POST | billing | JWT | Open billing portal | Dashboard |
| `/api/billing/webhook` | POST | billing | None (HMAC) | Stripe event handler | Stripe |
| `/health` | GET | main | None | Health check | Load balancers |
| `/v/{token}` | GET | main | None | Share link redirect | External browsers |
| `/` | GET | main | None | Root redirect | Direct access |

### Dead / Missing Endpoints

**No dead endpoints found.** All routes are consumed by either the frontend or Stripe.

### Inconsistencies and Cleanup Opportunities

#### HIGH PRIORITY

1. **Two different schema shapes for links creation vs retrieval:**
   - `POST /api/links` returns `LinkResponse` (no `has_password`, no `is_active`, no `permissions`)
   - `GET /api/links` returns `{"links": [LinkSummary]}` (has `has_password`, `is_active`, `permissions`)
   - `PATCH /api/links/{id}` returns `LinkSummary`
   - **Impact:** Frontend must handle two different link object shapes depending on the operation that created the link in memory. The `POST` response is deliberately minimal, but this forces the frontend to re-fetch after creation if it needs the full shape.

2. **Validate endpoint returns non-standard fields alongside security-relevant ones:**
   - `doc_status` returned as part of `/validate` response — the document status of a doc that may not be ready is useful, but it doesn't belong in the session creation response conceptually.
   - `document_filename` is returned in `/validate` but `filename` is used everywhere else in the documents API.

3. **`/api/documents/{id}` returns `dict` (via `model_dump()`) instead of a proper response model:**
   - `@router.get("/{document_id}", response_model=dict)` loses type safety and OpenAPI documentation quality.
   - Same pattern in `GET /api/documents` and all analytics endpoints.

4. **Viewer endpoints repeat the link→doc metadata lookup pattern 4+ times** with no shared helper function. The `/download` endpoint re-reads link freshly from DB while `/page`, `/thumb`, `/text`, `/toc` all use the TTL cache — inconsistent.

#### MEDIUM PRIORITY

5. **`POST /api/analytics/events` accepts `metadata` (free-form dict) but there is no validation** on its shape or size — potential unbounded data storage.

6. **`GET /api/groups/{id}` runs a separate `COUNT` query** while `GET /api/groups` does a batch count. The single-group endpoint creates an avoidable N+1 when listing groups individually.

7. **`PUT /api/groups/{id}/documents` loops over `document_ids` with one DB query per ID** instead of a bulk update.

---

## SECTION 4 — FRONTEND / BACKEND BOUNDARY REVIEW

### Frontend File: `src/app.jsx` (4,083 lines)

The frontend is a single-file React application. This is the correct architecture for the project's current scale (single-page app, one developer, no build pipeline complexity needed beyond esbuild).

### Critical Issue: Embedded Tweaks Panel (Design Tool Prototype Code)

**`app.jsx` lines 1–480 contain a full copy of a "tweaks-panel.jsx" design tool prototype component** that has no relation to SecureDoc:
- `TweaksPanel`, `TweakSection`, `TweakSlider`, `TweakToggle`, `TweakRadio`, `TweakSelect`, `TweakText`, `TweakNumber`, `TweakColor`, `TweakButton`, `useTweaks` — all design-panel utilities
- These are used by the `App` component (lines 3969-4083) to expose runtime UI customization knobs for development/prototyping
- `TWEAK_DEFAULTS` includes `accentColor`, `surfaceColor`, `density` — prototype theming
- This code has no business in a production document security application
- It compiles into the production bundle (`dist/app.bundle.js`), adding ~15KB of dead UI code to every page load

### Frontend Responsibilities That Should Be Backend

1. **`is_active` flag computed in `links.py` (`_link_to_summary`)** — this is a derived state computed server-side ✅ (correct)
2. **Watermark text constructed in `viewer.py`** ✅ (correct — session identity belongs on server)
3. No major frontend-should-be-backend violations found

### Backend Responsibilities That Should Be Frontend

1. **Duplicate `permissions_dict` defaulting** — default permissions (`can_download: false`, etc.) are hard-coded in `viewer.py` (lines 231-237) AND must be mirrored in the frontend for display. A permissions schema would prevent drift.

2. **`watermark_text` construction repeated in two places** — computed in `validate_link` response AND again in `get_page` / `get_text_chunk`. The validate response provides it but the page endpoint recomputes it independently (correctly — masked email vs. raw email).

### Duplicate Validation

1. **Content-type check + file extension detection** — `documents.py` checks `file.content_type not in ALLOWED_CONTENT_TYPES` (line 137) and then calls `detect_file_type()` which also branches on extension and content-type. These are complementary (early rejection vs. canonical detection) but the boundary between them is implicit.

2. **Link revocation/expiry checked in `get_gate_requirements` AND in `validate_link` AND on every page request** — this is correct defense-in-depth, not duplication.

### Architecture Smells

1. **`_link_to_summary` in `links.py`** computes `is_active` using the same logic as `enforcer.is_active_session` — but for link state, not session state. The function name is clear but the duplication of the "active" calculation logic is worth noting.

2. **`viewer.py` imports from 12 different modules** — it is a coordination hub. This is expected for a viewer endpoint but should not grow further.

3. **Frontend has `DocumentPicker` component duplicated conceptually** across Upload screen and both Viewer/Access tabs — it's a shared component in the code but the duplication of intent is visible.

---

## SECTION 5 — WORKER ARCHITECTURE REVIEW

### Celery Configuration

The `celery_app.py` is minimal and correct:
- `acks_late=True` + `task_reject_on_worker_lost=True` prevents task loss on worker crash
- `worker_prefetch_multiplier=1` prevents one worker from hoarding all tasks
- Beat schedule correct for `purge_stale_sessions` (30 min) and `requeue_orphaned_uploads` (5 min)

### Processing Pipeline

Three document format pipelines live in `tasks.py`:

| Pipeline | Steps | Status |
|----------|-------|--------|
| PDF | Download → Rasterize → Watermark → Upload pages + thumbs → Insert DB pages → TOC extract | Complete |
| Text (txt/md/log) | Download → Decode → Count chunks → Mark ready | Complete |
| DOCX | Download → Extract TOC → Convert to markdown → Overwrite storage → Count chunks → Mark ready | Complete |
| DOC (legacy) | Download → antiword subprocess → Overwrite storage → Count chunks → Mark ready | Complete |

### Issues

1. **`tasks.py` is a God File** — 580 lines handling:
   - Module-level async engine lifecycle management
   - 4 document processing pipelines
   - TOC extraction helper
   - Stale session purge periodic task
   - Orphan upload requeue periodic task
   - Stale processing recovery logic
   - Error marking helper
   
   This should be split into at minimum: `pipeline/pdf.py`, `pipeline/text.py`, `pipeline/word.py`, `cleanup.py`

2. **DOCX and DOC pipelines are near-identical** — both: download → convert to text → overwrite storage → count chunks → mark ready. They differ only in the conversion function. A shared `_process_as_text_document(db, doc, document_id, storage, converter_fn)` helper would eliminate duplication.

3. **The `_should_process` function** checks `status == "uploaded" | "processing"` but does not account for `"error"` status with a retry count. Documents in `"error"` can never be re-queued without direct DB manipulation.

4. **`requeue_orphaned_uploads` uses a new DB session** outside of the function argument — a design inconsistency vs. `process_document_with_session` which accepts an injectable session. This makes `_requeue_orphaned_uploads_async` untestable without a running DB.

5. **No dead tasks found** — all 4 tasks in the file are active.

---

## SECTION 6 — STORAGE ABSTRACTION REVIEW

### Abstraction Quality

`StorageBackend` ABC is clean:
- `upload_file`, `download_bytes`, `delete_file`, `list_keys_with_prefix`, `file_exists`, `generate_presigned_url`
- Only `StorageService` (S3/R2) implements it in production
- `DemoStorageService` re-implements all methods **without extending `StorageBackend`** — breaks the type hierarchy

### Leakage Points

1. **Storage key structure is implicit and scattered:**
   - `originals/{doc_id}.{ext}` — hardcoded in `documents.py`
   - `pages/{doc_id}/{page:04d}.webp` — hardcoded in `tasks.py`
   - `thumbs/{doc_id}/{page:04d}.webp` — hardcoded in `tasks.py`
   - `toc/{doc_id}.json` — hardcoded in `tasks.py` and `viewer.py`
   - A `StorageKeys` utility class/module would centralize this and prevent drift when new formats are added

2. **`generate_presigned_url`** exists in `StorageService` but is never called by any router or service. The page serving model (proxy bytes) makes presigned URLs unnecessary for the viewer, but the method adds dead surface area.

3. **`DemoStorageService.list_keys_with_prefix`** has a brittle path reconstruction logic (replaces `_` with `/`) that is specific to its flat-file storage scheme and would silently fail for storage keys with underscores in the base name.

4. **Cloud provider lock-in:** `boto3` is the only client. The abstract interface exists but there is no DynamoDB, GCS, or Azure Blob adapter. For the current use case (Cloudflare R2 + S3 compatibility), this is acceptable.

---

## SECTION 7 — CACHE ARCHITECTURE REVIEW

### Cache Layers

| Layer | Location | Stores | TTL | Size |
|-------|---------|--------|-----|------|
| L1 metadata | `viewer_cache._TTLCache` | Link/Doc/Page snapshots, text, chunks, TOC | 10s/60s/300s | 2000/1000/10000/100/100/500 |
| L1 bytes | `page_cache._PAGE/THUMB_BYTES_CACHE` (OrderedDict) | Page images, thumbnails | LRU eviction | 600/2000 entries |
| L2 bytes | `page_cache.RedisPageCache` | Page images, thumbnails | 3600s (configurable) | Redis |
| L2 TOC | `toc/cache.py` | TOC trees (JSON) | 300s | Redis |

### Ownership Clarity

**Good:** Byte cache (L1/L2) is clearly separated from metadata cache. Each cache has a single owner module.

**Issue:** TOC is cached in two places:
1. `viewer_cache.toc_cache` (L1 only, used by viewer.py)
2. `toc/cache.py` `store_toc_async` (L1 + L2, only called from tests)

The `viewer.py` `/toc` endpoint never calls `toc/cache.py`'s L2 functions — so **TOC entries are never Redis-cached in production**, only in-process. This means on a cold API restart (or under multi-replica deployments), every first TOC request will hit storage and re-extract. The `toc/cache.py` module was written but its integration was never completed.

### Invalidation Design

| Event | Cache Invalidated | How |
|-------|------------------|-----|
| Link revoke | `link_cache` | `invalidate_link(token)` in `link_service.revoke_link()` |
| Document delete | All caches for doc | `invalidate_doc_entries()` + `clear_doc_bytes()` in router |
| Document reprocess | L2 byte cache + L1 metadata | `clear_doc_bytes_redis()` + `invalidate_doc_entries()` in worker |
| Link policy update (PATCH) | **Nothing** | ⚠ Link snapshot stale for up to 10s (IP allowlist, email list change) |

**Potential design weakness:** When a link's `allowed_emails`, `allowed_domains`, or `ip_allowlist` is updated via `PATCH /api/links/{id}`, the cached `LinkSnapshot` is not invalidated. A viewer with a cached link snapshot could bypass a newly-added email restriction for up to `LINK_TTL_SEC` (10 seconds). This is the defined TTL behavior, but it should be explicitly documented and `revoke_link`-style cache invalidation should also be called on security-policy changes.

---

## SECTION 8 — ANALYTICS ARCHITECTURE REVIEW

### Isolation

`AnalyticsService` is well-isolated:
- All event writes go through `analytics_svc.log_event()`
- The `commit=False` pattern allows batching with other writes
- `VIEWER_LOGGABLE_EVENTS` controls what the frontend can log
- `BLOCKED_EVENT_TYPES` in `analytics_service.py` drives risk scoring

### Analytics Logic in Viewer Logic

The `viewer.py` router:
- Calls `analytics_svc.log_event()` directly at 4 points (`validate_link`, `get_page`, `get_text_chunk`, `download_document`)
- The "opened" event at validate time is committed atomically with the session and view count — this is an architecture choice that couples analytics to the session establishment path
- This coupling is intentional (to reduce DB round-trips) but means the viewer router cannot be tested for session creation without also testing analytics writes

### Cleanup Opportunities

1. **`BLOCKED_EVENT_TYPES` in `analytics_service.py` and `VIEWER_LOGGABLE_EVENTS` in `models/event.py`** should be co-located. They are two sides of the same "which events are security-relevant" classification. Currently imports are needed from both files to understand the full classification.

2. **Risk scoring (`"HIGH"/"MED"/"LOW"` based on `blocked_24h` thresholds)** is hardcoded in `analytics_service.py` with magic numbers (2, 5). Should be configurable or at minimum named constants.

3. **`get_document_analytics` and `get_group_analytics` share nearly identical query patterns** (batch link ID lookup, batch event aggregation by link) but are implemented separately — potential DRY violation.

---

## SECTION 9 — TEST STRUCTURE REVIEW

### Structure Overview

```
backend/tests/
├── unit/          (12 files) — pure unit tests, no DB
├── integration/   (20 files) — FastAPI + SQLite, mocked storage
└── regression/    (4 files)  — auth, group, link, security invariants
```

```
tests_e2e/
├── api/       — contract tests against live stack
├── services/  — service-level unit tests
├── ui/        — Playwright browser tests
└── e2e/       — full scenario flows
```

### Structural Assessment

**Good:** 
- Clear three-tier separation (unit/integration/regression) in backend
- `conftest.py` provides reusable fixtures with correct lifecycle management
- Test database isolation per test via `scope="function"` fixtures
- Rate limiter reset fixture prevents test contamination

**Issues:**

1. **Phase-named test files (`test_phase1.py` through `test_phase8.py`) are named after development phases, not what they test.** These filenames tell a story about when tests were added, not what behavior they cover. Future contributors won't know which phase file to look in for a specific feature's tests.
   - `test_phase1.py` → tests watermark offloading, batch commit, thumbnails
   - `test_phase2.py` → tests static bundle, no-Babel HTML
   - `test_phase3.py` → tests viewer metadata caching
   - `test_phase4.py` → tests Redis byte caching
   - `test_phase5.py` → tests text document support
   - `test_phase6.py` → tests security headers, proxy, rate limiter
   - `test_phase7.py` → tests session management, document adapter, analytics
   - `test_phase8.py` → tests Cloudflare readiness, HTTPS redirect, cache headers

2. **Significant overlap between `test_phase5.py` (49KB) and `test_stability.py` (57KB)** — both cover large portions of the text pipeline, analytics, and viewer behavior. May contain redundant test coverage.

3. **`test_audit_remediation.py` (22KB) and `test_cleanup_pass.py` (10KB)** are also named after development activities rather than behaviors. These are regression suites but their names make it unclear what they protect.

4. **`test_toc_engine.py` (40KB)** is one of the largest test files — tests the TOC engine extensively, including `toc/cache.py`'s async L2 functions. However, since `viewer.py` never calls these L2 functions, some of these tests verify behavior that never runs in production.

5. **No dedicated test file for `document_adapter.py`** — adapter tests are embedded in `test_phase7.py` but the adapter module is never tested through the actual API path (it's tested directly in isolation).

6. **E2E test coverage is good:** 160 passed, 16 expected skips. Session-scoped `ready_doc` fixture is clever for rate limit management.

---

## SECTION 10 — REPOSITORY HYGIENE

### Committed Artifacts

| Item | Status | Severity |
|------|--------|---------|
| `backend/app/utils/token.py,cover` | Committed dead coverage artifact (source deleted, cover remains) | HIGH |
| `backend/app/schemas/event.py,cover` | Ghost cover for a schemas/event.py that was never created | HIGH |
| `frontend/dist/app.bundle.js` | Pre-compiled bundle, committed intentionally for Docker multi-stage | ACCEPTABLE |
| `frontend/node_modules/` | Build toolchain committed | MEDIUM |
| `backend/htmlcov/` | HTML coverage report (not tracked by git — untracked only) | MEDIUM |
| `backend/.coverage` | Coverage data (not tracked by git — untracked only) | LOW |
| `test_*.db` (×4 at project root) | Test SQLite databases leaking out of `backend/` (not tracked) | HIGH |
| `test_*.db` (×4 in `backend/`) | Test SQLite databases (not tracked, .gitignore partially covers) | MEDIUM |

### .gitignore Quality

**Partially effective.** Issues:
- `.gitignore` lists `backend/test_securedoc.db` and `backend/test_link_service.db` but **not** `backend/test_phase5.db` or `backend/test_purge_sessions.db` — these leak to untracked state
- `*.cover` files are **not in .gitignore** — two ghost cover files are tracked: `token.py,cover` and `event.py,cover`  
- `*.log*.db` pattern is malformed (should be two separate patterns: `*.log` and `*.db`)
- No `htmlcov/` entry (though currently untracked, this should be explicit)
- `frontend/node_modules/` needs verification — if committed, this is a serious bloat issue

### node_modules Status

```
/Users/thrisha/traceview/securedoc/frontend/node_modules/
  @esbuild/darwin-arm64/  (binary esbuild for macOS ARM)
  esbuild/
```

The `node_modules/` directory **appears to contain only esbuild** (the build tool), not React or other runtime dependencies. React is loaded from CDN. This is a deliberate design choice to keep the Docker build deterministic without a separate npm install step. However, committing platform-specific binaries (`darwin-arm64`) is problematic for CI/CD running on Linux. This should be excluded from the repo and installed during the Docker build stage (which already runs `npm ci`).

### Summary Table

| Category | Finding | Severity |
|----------|---------|---------|
| Committed `.cover` files | 2 ghost coverage artifacts tracked by git | HIGH |
| Mispatched `.gitignore` | 2 test DBs missing from `.gitignore` | MEDIUM |
| Root-level test DBs | 4 `.db` files at project root (leaked from backend/) | HIGH |
| `node_modules/` committed | Platform-specific esbuild binary in repo | MEDIUM |
| `htmlcov/` untracked | HTML coverage not excluded by `.gitignore` | LOW |
| Tweaks panel in production bundle | ~480 lines of prototype UI code in production app | HIGH |

---

## SECTION 11 — DESIGN DRIFT ANALYSIS

### Drift 1: `document_adapter.py` — Architecture Without Adoption

**Intended:** A unified `DocumentAdapter` interface to eliminate scattered `if file_type == "pdf"` chains.  
**Reality:** The adapter is defined in `services/document_adapter.py` but no router, service, or task imports it. The if/elif chains in `viewer.py`, `tasks.py`, and `documents.py` were never refactored to use it. Only `test_phase7.py` imports the adapter — to test the adapter itself, not behavior routed through it.  
**Debt:** Medium — the pattern is good but was never completed. Either adopt it or delete it.

### Drift 2: `toc/cache.py` — L2 Integration Never Wired

**Intended:** A two-level TOC cache (L1 in-process + L2 Redis) matching the page byte cache pattern.  
**Reality:** `toc/cache.py` was written and unit-tested, but `viewer.py`'s `/toc` endpoint uses `viewer_cache.toc_cache` (L1 only) and never calls `get_cached_toc_async` or `store_toc_async`. The L2 Redis TOC cache path is completely unused in production.  
**Debt:** Medium — either complete the wiring or delete `toc/cache.py`.

### Drift 3: `DemoStorageService` Not Typed as `StorageBackend`

**Intended:** All storage backends implement `StorageBackend` ABC.  
**Reality:** `DemoStorageService` in `demo_storage_patch.py` re-implements all methods but does not inherit from `StorageBackend`. It monkey-patches the module globals directly.  
**Debt:** Low — only affects development mode, but causes type-checker warnings.

### Drift 4: `DocumentGroup.user_id` Nullable vs. Intent

**Intended:** Every group belongs to a user (`NOT NULL`).  
**Reality:** `DocumentGroup.user_id` is `nullable=True` in the ORM model (`group.py`) and migration 005 added it as nullable. Migration 007 hardened `Document.user_id` to NOT NULL but didn't touch `DocumentGroup.user_id`.  
**Debt:** Medium — groups with `user_id=NULL` are "orphaned" (no query filters for them), but the nullable constraint is a semantic inconsistency. A migration to set NOT NULL would require cleaning orphaned rows first.

### Drift 5: Phase Comments in Config

`config.py` has comments like `# Phase 7 — enterprise / performance / observability` and `# Phase 8 — DB connection pool` attached to settings fields. This is development timeline cruft that will rot as the codebase evolves. Config keys should document their purpose, not their origin phase.

### Drift 6: Tweaks Panel as Production Prototype Scaffolding

Lines 1–480 of `app.jsx` are a design-tool prototype panel (`TweaksPanel`, `useTweaks`, etc.) that was originally used during UI iteration. It is still actively used by the `App` component to expose runtime theming controls, but this has no place in a production security application. The `TWEAK_DEFAULTS` at line 3969 drive the app's color scheme — meaning the entire visual theme is controlled through a prototype tooling system rather than proper CSS variables or a theme file.

### Drift 7: `schemas/event.py` Ghost

There is a `backend/app/schemas/event.py,cover` committed to the repo but no `schemas/event.py` source file. This indicates `schemas/event.py` was created (or planned) at some point and then removed, but its coverage artifact was committed and never cleaned up.

### Drift 8: Response Model Inconsistency (`response_model=dict`)

Several endpoints use `response_model=dict` instead of a typed Pydantic schema:
- `GET /api/documents` → `{"documents": [DocumentSummary]}`  
- `GET /api/documents/{id}` → `DocumentDetail.model_dump()`  
- `GET /api/links` → `{"links": [LinkSummary]}`  
- Analytics endpoints generally return dicts

The pattern of returning a dict wrapper (`{"documents": [...]}`) is consistent but the `response_model=dict` annotation defeats OpenAPI type documentation and Pydantic validation of the response.

---

## SECTION 12 — ARCHITECTURE SCORECARD

| Dimension | Score | Justification |
|-----------|-------|---------------|
| **Repository Structure** | 6/10 | Clean layering, but ghost files, duplicate DBs, committed build artifacts, and the tweaks panel drift pull it down |
| **API Design** | 7/10 | REST-aligned, consistent auth, good rate limiting. Weakened by `response_model=dict`, two link shapes (Create vs List), and viewer endpoint boilerplate duplication |
| **Frontend Architecture** | 6/10 | Single JSX file is acceptable at this scale, but 4,083 lines in one file with 480 lines of unrelated prototype code is a liability |
| **Backend Architecture** | 8/10 | Excellent layering: router → service → model. Middleware stack is clean. Auth is secure. Config is well-structured. Minor: `tasks.py` is a monolith |
| **Worker Architecture** | 7/10 | Pipeline design is solid. Beat schedule correct. But `tasks.py` should be split, DOCX/DOC pipelines have obvious duplication, and periodic tasks live alongside document processors |
| **Storage Design** | 8/10 | StorageBackend ABC is clean. Dedicated thread pool is correct. Demo service not typed. Storage key scheme implicit |
| **Analytics Design** | 8/10 | Well-isolated service, batch queries, risk scoring. Minor: event type classification split across two modules, risk thresholds are magic numbers |
| **Cache Design** | 7/10 | Two-level byte cache excellent. TTL metadata cache sound. But TOC L2 never wired, PATCH link policy doesn't invalidate cache, FIFO vs LRU is a minor concern |
| **Test Organization** | 6/10 | Good coverage, clean fixtures, E2E suite. Weakened by phase-named files (not behavior-named), redundant coverage across large test files, and tests for dead code (toc/cache L2) |
| **Maintainability** | 7/10 | The codebase is generally readable and well-documented. The main threats: single 4,083-line frontend file, `tasks.py` monolith, ghost files, and the unwired adapter/TOC-cache modules create confusion about what's production vs. aspirational |

**Overall Architecture Score: 7.0/10**

---

## SECTION 13 — PHASED FIX PLAN

### Phase A1 — Critical Repository Cleanup

**Objective:** Remove committed and leaked artifacts; fix .gitignore.

**Files Involved:**
- `backend/app/utils/token.py,cover` — delete (ghost)
- `backend/app/schemas/event.py,cover` — delete (ghost)
- `test_*.db` × 8 (4 at root + 4 in backend/) — delete all, add to .gitignore
- `frontend/node_modules/` — remove from repo if committed; rely on Dockerfile's `npm ci`
- `.gitignore` — add `*.cover`, `htmlcov/`, `test_phase5.db`, `test_purge_sessions.db`, `!frontend/dist/app.bundle.js` (keep this), `node_modules/`

**Priority:** HIGH  
**Expected Impact:** Cleaner git history, no ghost references, CI won't accidentally run stale test databases  
**Risk:** Low (deletions only)

---

### Phase A2 — Dead Code Removal

**Objective:** Remove production-dead modules and prototype scaffolding.

**Files Involved:**
1. `backend/app/services/toc/cache.py` — **either delete OR wire into viewer.py's /toc endpoint** (not both)
2. `backend/app/services/document_adapter.py` — **either delete OR adopt in tasks.py/viewer.py** (current state: test-only import)
3. `frontend/src/app.jsx` lines 1–480 — Remove `TweaksPanel`, `TweakSection`, `TweakSlider`, `TweakToggle`, `TweakRadio`, `TweakSelect`, `TweakText`, `TweakNumber`, `TweakColor`, `TweakButton`, `useTweaks`, `__TWEAKS_STYLE`
4. `frontend/src/app.jsx` lines 3969–4083 — Remove `TWEAK_DEFAULTS`, `useTweaks` usage, `TweakColor`/`TweakRadio` calls from `App`; move color scheme to CSS variables

**Priority:** HIGH  
**Expected Impact:** ~480 lines removed from frontend; bundle size reduced; removes test-only modules that create architectural confusion  
**Risk:** Medium (must verify tweaks controls aren't used for anything essential in production builds)

---

### Phase A3 — API Cleanup

**Objective:** Improve API consistency and type safety.

**Files Involved:**
1. `backend/app/routers/viewer.py` — Extract shared `_get_link_doc_snap(token, db)` helper to replace the repeated 3-stage cache-lookup prologue (affects `/page`, `/thumb`, `/toc`, `/text` routes)
2. `backend/app/routers/documents.py` — Replace `response_model=dict` with typed `ListDocumentsResponse` wrapper schema
3. `backend/app/routers/links.py` — Align `POST /api/links` response with `LinkSummary` shape (add `has_password`, `is_active`) OR update frontend to re-fetch after creation
4. `backend/app/routers/analytics.py` — Replace `response_model=dict` with typed wrapper schemas
5. `backend/app/routers/viewer.py` — Add cache invalidation on `PATCH /api/links/{id}` for security policy fields

**Priority:** MEDIUM  
**Expected Impact:** Cleaner OpenAPI docs; eliminates 80+ lines of boilerplate duplication; prevents future cache staleness bug on policy updates  
**Risk:** Low-Medium (schema changes need frontend verification)

---

### Phase A4 — Architecture Alignment

**Objective:** Close the gaps between intended and actual architecture.

**Files Involved:**
1. `backend/app/services/document_adapter.py` + `backend/app/workers/tasks.py` + `backend/app/routers/viewer.py` — **Option A (adopt adapter):** Replace `if file_type in (...)` chains with `adapter = DocumentAdapter.for_file_type(doc.file_type)` calls. **Option B (delete):** Remove the adapter, leave if/elif chains as-is (simpler, no new abstraction).

2. `backend/app/services/toc/cache.py` + `backend/app/routers/viewer.py` — **Option A (wire L2):** Update `/toc` endpoint to use `get_cached_toc_async` / `store_toc_async`. **Option B (delete L2 module):** Remove `toc/cache.py`, document that TOC is L1-only.

3. `backend/app/models/group.py` + migration — Add `010_hardening_group_user_id.py` migration to set `DocumentGroup.user_id NOT NULL` after cleaning orphans; update ORM to `nullable=False`.

4. `backend/app/services/storage.py` — Add `StorageKeys` module or class with `original(doc_id, ext)`, `page(doc_id, page)`, `thumb(doc_id, page)`, `toc(doc_id)` classmethods to centralize key scheme.

**Priority:** MEDIUM  
**Expected Impact:** Closes architectural dead-ends; eliminates code that misleads future contributors; prevents future storage key typos  
**Risk:** Medium (migration on DocumentGroup requires data cleanup step)

---

### Phase A5 — Technical Debt Reduction

**Objective:** Reduce maintenance burden and improve navigability.

**Files Involved:**
1. `backend/app/workers/tasks.py` — Split into:
   - `workers/pipeline/pdf.py` — PDF processing
   - `workers/pipeline/text.py` — text/md/log processing  
   - `workers/pipeline/word.py` — DOCX/DOC processing (unify the two near-identical pipelines)
   - `workers/pipeline/toc.py` — TOC extraction helpers
   - `workers/cleanup.py` — periodic tasks (session purge, orphan requeue)
   - `workers/tasks.py` — thin dispatcher calling above modules

2. `backend/app/config.py` — Replace phase comments with purpose-oriented comments or remove if self-explanatory.

3. `backend/tests/integration/` — Rename phase-named test files to behavior-named:
   - `test_phase3.py` → `test_viewer_cache.py`
   - `test_phase4.py` → `test_redis_byte_cache.py`
   - `test_phase5.py` → `test_text_documents.py`
   - `test_phase6.py` → `test_security_middleware.py`
   - `test_phase7.py` → `test_session_management.py` (or split)
   - `test_phase8.py` → `test_cloudflare_deployment.py`
   - `test_phase1.py` / `test_phase2.py` — evaluate for merge into more focused files

4. `backend/app/models/event.py` + `backend/app/services/analytics_service.py` — Co-locate `BLOCKED_EVENT_TYPES` and `VIEWER_LOGGABLE_EVENTS` in one module (suggestion: `models/event.py`)

5. `frontend/src/app.jsx` — Extract `TocSidebar`, `SearchPanel`, `AnalyticsScreen`, `BillingScreen`, `ViewerScreen` into separate JSX component files to reduce the single-file from 4,083 lines.

**Priority:** LOW-MEDIUM  
**Expected Impact:** Dramatically improves navigability; reduces `tasks.py` from 580 to ~80 lines; test files tell a story about behavior not history  
**Risk:** Low (pure refactor, no behavioral change)

---

## SECTION 14 — FINAL VERDICT

### 1. Is the repository structurally healthy?

**Mostly yes, with specific issues to clean up.** The core architecture is sound. Layering is respected. Auth, storage, caching, and analytics are correctly isolated into services. The main structural problems are:
- Ghost committed files (`.cover` artifacts, leaked `.db` files)
- Prototype code in production bundle (tweaks panel)
- Dead modules that create architectural confusion (document_adapter, toc/cache)

### 2. Is architecture clean enough for future expansion?

**Yes, but two things should be addressed first:**
1. The storage key scheme should be centralized before new document types are added
2. The `document_adapter.py` question must be resolved (adopt or delete) — it is the intended abstraction point for new format support but is currently inert

DOCX/PPTX expansion can begin safely with these caveats. The existing `DocxAdapterStub` and `PptxAdapterStub` signal where new adapters would plug in.

### 3. Must anything be refactored before DOCX/PPTX work begins?

**Recommended (not strictly required):**
- Centralize storage key scheme (`StorageKeys` module) — prevents future key inconsistencies
- Decide adapter adoption (Phase A4, Option A or B) — clarifies the extension point
- Complete or remove `toc/cache.py` L2 wiring — DOCX TOC extraction will use TOC caching

**Not required before starting:**
- Test file renames (Phase A5)
- `tasks.py` split (Phase A5)
- Frontend tweaks panel removal (Phase A2)

### 4. Top 10 Architecture Issues

| # | Issue | Severity |
|---|-------|---------|
| 1 | Tweaks panel prototype code compiled into production bundle (480 lines dead UI code) | HIGH |
| 2 | Ghost committed artifacts: `token.py,cover`, `event.py,cover`, duplicate test DBs | HIGH |
| 3 | `document_adapter.py` exists but is never called by production code | MEDIUM |
| 4 | `toc/cache.py` L2 TOC cache written but never wired into viewer.py | MEDIUM |
| 5 | `tasks.py` is a 580-line monolith combining 4 pipelines + 2 periodic tasks + engine management | MEDIUM |
| 6 | Viewer endpoints repeat 3-stage cache-lookup prologue ~4× (80+ lines of duplication) | MEDIUM |
| 7 | `DocumentGroup.user_id` is nullable in ORM despite intent to be NOT NULL (unlike `Document.user_id`) | MEDIUM |
| 8 | PATCH on link policy fields does not invalidate the link metadata cache | MEDIUM |
| 9 | Storage key scheme scattered across 3 files with no central definition | MEDIUM |
| 10 | Phase-named test files (`test_phase1.py` through `test_phase8.py`) document history, not behavior | LOW |

### 5. Top 10 Strengths

| # | Strength |
|---|---------|
| 1 | Two-level byte cache (L1 OrderedDict + L2 Redis) for page images with graceful Redis fallback |
| 2 | Clean layered architecture: router → service → model, no layer skipping |
| 3 | `StorageBackend` ABC with dedicated thread pool separating S3 I/O from CPU work |
| 4 | Fail-closed policy enforcement on all security checks (IP allowlist, domain allowlist, malformed JSON) |
| 5 | `commit=False` pattern in analytics and link service for atomic multi-write batching |
| 6 | Session heartbeat throttling (30-second interval) reducing DB write amplification |
| 7 | Middleware stack correctly ordered with TrustedProxy before rate limiter for real-IP rate limiting |
| 8 | Advisory-locked migration runner preventing parallel migration race on multi-replica startup |
| 9 | Production startup validation in `main.py` refusing to start with unsafe config |
| 10 | Comprehensive E2E test suite (160 passing) with Playwright UI tests, API contract tests, and service unit tests |

### 6. What should be fixed immediately?

1. **Delete ghost committed files** (`token.py,cover`, `event.py,cover`) and fix `.gitignore` — 15 minutes, zero risk
2. **Remove tweaks panel code from `app.jsx`** — reduces bundle, removes prototype scaffolding from production
3. **Delete root-level test `.db` files** and ensure `.gitignore` covers all test databases
4. **Resolve `document_adapter.py` and `toc/cache.py`** — delete both if not adopting them, or wire them in. The current state (present but unused) is architecturally misleading.

### 7. What can wait?

- `tasks.py` split (Phase A5) — works correctly, just hard to navigate
- Test file renaming — cosmetic, no runtime impact
- `DocumentGroup.user_id NOT NULL` migration — functional gap but low exploitation risk
- `response_model=dict` cleanup — OpenAPI quality issue, not a runtime bug
- Storage key centralization — only matters when adding new formats (can be done as part of DOCX/PPTX work)
- Frontend component extraction from `app.jsx` — manageable at current size, prioritize when file approaches 5,000+ lines

---

*End of Phase A Audit. Phases B (security deep-dive), C (scalability), D (competitor research), and E (DOCX/PPTX planning) to follow separately.*
