> **HISTORICAL ARCHIVE** — Reflects repository state before Sprint 4.2D extraction (2026-06-22). Not current. Do not use for active decision-making.

# TRACEVIEW PERFORMANCE, SCALABILITY & DEPLOYMENT AUDIT
## Phase C — Latency, Scalability, Caching, Storage, Database, Worker, and Deployment

**Audit Date:** 2026-06-04  
**Auditor Role:** Principal Engineer, Systems Performance  
**Repository:** `/Users/thrisha/traceview/securedoc/`  
**Scope:** Phase C — performance, capacity, bottlenecks, cache effectiveness, deployment readiness. No security deep-dive (see Phase B), no feature additions.

---

## Executive Summary

SecureDoc's architecture is well-suited for the current scale (1 uploader, 500 users, 10 concurrent viewers) and is broadly capable of reaching the next scale target (10 uploaders, 5000 users, 100 concurrent viewers) **without architectural rewrites**. The design makes good choices: multi-tier caching (L1/L2), session heartbeat throttling, watermark offloading to thread pools, batched DB writes at validate time, and IntersectionObserver-driven lazy thumbnail loading.

However, several specific constraints limit the path from current to future scale:

1. **Watermarking is the dominant per-request CPU cost** and is applied synchronously per request. At 100 concurrent viewers, it consumes ~0.8 CPU cores per API process.
2. **Celery worker concurrency is hardcoded at 2** — unable to process multiple large PDFs in parallel.
3. **Missing composite index on `(link_id, created_at)` in `access_events`** will cause analytics queries to slow significantly beyond ~2M rows.
4. **`document_pages` has no explicit index on `document_id`** — page queries rely on the unique constraint, which may be less optimal for ORDER BY scans on large tables.
5. **The L1 metadata cache is per-process** — with 2 uvicorn workers, link/doc snapshots are duplicated in memory and cache misses are 2× more likely under concurrent load.
6. **`access_events` table grows unboundedly** (no archival, no partitioning) — at 5000 users it accumulates ~180k events/day.
7. **Redis has no authentication** configured (localhost default) — a correctness risk for production.
8. **Cloudflare cannot cache any watermarked content** (Cache-Control: no-store) — every page request reaches the API server.

**Verdict:** The current system handles the current load comfortably. For 100 concurrent viewers, three targeted changes are needed before production at that scale: increase worker concurrency, add the `(link_id, created_at)` composite index, and confirm Redis auth is set. Everything else can wait.

---

## Section 1 — Request Flow Analysis

### Viewer Open → Validate → Session → Metadata → Page Fetch → Watermark → Response

#### Flow Map: Cold Start (First Request)

```
VIEWER BROWSER
     │
     │ 1. GET /api/viewer/gate/{token}                           ~5ms
     │    ├─ DB: SELECT share_links WHERE token=?               (token has UNIQUE index ✓)
     │    └─ Response: {status, requires_password, requires_email}
     │
     │ 2. POST /api/viewer/validate                              ~25-40ms
     │    ├─ DB: SELECT share_links WHERE token=?               (UNIQUE index ✓)
     │    ├─ DB: INSERT/UPDATE viewer_sessions                  (batched, commit=False)
     │    ├─ DB: UPDATE share_links SET view_count=...          (commit=False)
     │    ├─ DB: INSERT access_events (event_type='opened')     (COMMIT — 1 round-trip)
     │    ├─ [optional] DB: COUNT viewer_sessions WHERE link_id=? (concurrent check)
     │    ├─ DB: SELECT documents WHERE id=?                    (PK lookup ✓)
     │    └─ DB: SELECT document_pages WHERE document_id=? ORDER BY page_number
     │                                                          (up to 500 rows — unique idx ✓)
     │    └─ Response: {session_id, page_count, pages[], watermark_text, ...}
     │
     │ 3. GET /api/viewer/thumb/{token}/{p}?session_id=...      (×N, lazy per viewport)
     │    ├─ L1 link_cache: GET token                           MISS → DB SELECT ~5ms
     │    ├─ L1 doc_cache: GET doc_id                           MISS → DB SELECT ~5ms
     │    ├─ L1 page_cache: GET doc_id:page                     MISS → DB SELECT ~5ms
     │    ├─ L1 thumb_cache: GET thumbs/doc/page.webp           MISS
     │    ├─ L2 Redis: GET thumb key                            MISS
     │    └─ S3/R2: GET thumbs/doc/page.webp                   ~20-60ms
     │       └─ Response: ~5-8KB WEBP
     │
     │ 4. GET /api/viewer/page/{token}/1?session_id=...         ~50-120ms first load
     │    ├─ L1 link_cache: GET token                           MISS → DB ~5ms
     │    ├─ L1 doc_cache: GET doc_id                           MISS → DB ~5ms  
     │    ├─ L1 page_cache: GET doc_id:1                        MISS → DB ~5ms
     │    ├─ DB: GET viewer_session (upsert_session)            ~5ms (PK lookup ✓)
     │    ├─ L1 page_bytes: GET storage_key                     MISS
     │    ├─ L2 Redis: GET securedoc:page:v1:pages/...          MISS ~2ms
     │    ├─ S3/R2: GET pages/doc/0001.webp                     ~20-60ms (~250KB)
     │    ├─ Thread pool: apply_visible_watermark(bytes, text)  ~20-50ms CPU
     │    ├─ DB: INSERT access_events (COMMIT)                  ~5ms
     │    └─ Response: ~200-300KB watermarked WEBP
```

#### Flow Map: Warm State (Subsequent Pages, Same Session)

```
     │ GET /api/viewer/page/{token}/{p}?session_id=...          ~25-40ms warm
     │    ├─ L1 link_cache: HIT                                  <1ms (10s TTL)
     │    ├─ L1 doc_cache: HIT                                   <1ms (60s TTL)
     │    ├─ L1 page_cache: HIT                                  <1ms (300s TTL)
     │    ├─ DB: GET viewer_session (upsert heartbeat)           ~5ms (throttled 30s)
     │    ├─ L1 page_bytes: HIT (recently viewed pages)          <1ms
     │    │  OR L2 Redis: HIT                                    ~2ms
     │    │  OR S3/R2: GET (cold page)                           ~20-60ms
     │    ├─ Thread pool: apply_visible_watermark(bytes, text)   ~20-50ms CPU
     │    ├─ DB: INSERT access_events (COMMIT)                   ~5ms
     │    └─ Response: ~200-300KB
```

#### Latency Map Summary

| Stage | First Load | Warm State | Bottleneck? |
|-------|-----------|-----------|-------------|
| Gate lookup | 5ms | 5ms | No — cached after validate |
| Validate (all writes) | 25-40ms | 25-40ms | No — batched commit |
| Link metadata cache | 0.05ms | 0.05ms | No — L1 FIFO cache |
| Doc metadata cache | 0.05ms | 0.05ms | No — L1 cache |
| Page metadata cache | 0.05ms | 0.05ms | No — L1 cache |
| Session heartbeat | 5ms | ~0ms (throttled) | Minor |
| Page bytes from L1 | <1ms | <1ms | No |
| Page bytes from Redis | 2ms | 2ms | No |
| Page bytes from S3/R2 | 20-60ms | 20-60ms | **YES — cold pages** |
| Watermarking (thread) | 20-50ms | 20-50ms | **YES — CPU bound** |
| Analytics commit | 5ms | 5ms | Minor |
| **Total (cache hit)** | ~30ms | ~30ms | — |
| **Total (S3 miss)** | ~100-130ms | ~80-100ms | — |

#### Critical Observation: Validate is Expensive

The `/validate` endpoint makes **5-7 DB round-trips** (SELECT link, INSERT session, UPDATE view_count, INSERT event, concurrent session count, SELECT document, SELECT ALL pages). Only 1 actual DB commit (batched correctly), but 5-7 SELECT round-trips remain. With asyncpg and connection pooling, these are fast (~2-3ms each) but not free.

The additional concurrent session count query runs unconditionally if `max_concurrent_sessions_per_link > 0`, adding one more SELECT on every validate.

---

## Section 2 — Storage Analysis

### Storage Paths

| Operation | Storage Path | Size | Frequency |
|-----------|-------------|------|----------|
| Upload original | `originals/{doc_id}.{ext}` | 1-100MB | 1× per doc |
| Upload page | `pages/{doc_id}/{p:04d}.webp` | ~200-300KB | N×pages per doc |
| Upload thumbnail | `thumbs/{doc_id}/{p:04d}.webp` | ~5-8KB | N×pages per doc |
| Upload TOC sidecar | `toc/{doc_id}.json` | ~2-20KB | 1× per doc |
| Download page (serve) | `pages/...` | ~250KB | Every page view |
| Download thumbnail | `thumbs/...` | ~6KB | Once per viewer per page |
| Download TOC sidecar | `toc/{doc_id}.json` | ~10KB | Once per session |
| Download original | `originals/...` | 1-100MB | If can_download=True |

### Storage Sizing Estimates

```
Per 500-page PDF:
  Originals: ~10-50MB
  Pages:     500 × 250KB = 125MB
  Thumbs:    500 × 6KB   = 3MB
  TOC:       ~10KB
  Total:     ~128MB per document

For 100 documents (10 uploaders × 10 docs each):
  Total storage: ~12.8GB
```

### Identified Issues

**1. Original bytes never used after processing.**  
`originals/{doc_id}.{ext}` is downloaded by the worker once during rasterization. After the document is "ready", the original is only needed for text downloads (`can_download=True`). For a 500-page PDF where downloads are disabled, 10-50MB of original bytes sit in storage permanently. No lifecycle rule exists to transition originals to cheaper cold storage after processing.

**2. Storage keys are implicit and scattered.**  
`pages/{doc_id}/{p:04d}.webp`, `thumbs/{doc_id}/...`, `toc/{doc_id}.json` are hardcoded strings in `pipeline/pdf.py`, `viewer.py`, and `tasks.py`. Phase A noted this; still present. Adding new document types risks key collisions or inconsistent prefixes.

**3. No content-addressable storage.**  
Two documents with identical content produce two complete sets of page images. For training contexts where multiple trainers might share the same material, this is pure storage waste.

**4. Large PDF downloads load all pages into memory simultaneously.**  
The download endpoint (`/api/viewer/download/{token}`) fetches ALL page bytes, watermarks them all in parallel via `run_in_executor`, and assembles a PIL-based PDF entirely in memory. A 500-page document requires ~500 × 20MB PIL RGBA images in-flight: **up to 10GB RAM** for a single download request. This is a **critical memory DoS risk** for large PDFs. (In practice, most PDFs are shorter, but the code has no page count limit for downloads.)

**5. S3 connection pool is shared but sized for 16 threads.**  
`_STORAGE_EXECUTOR` has `max_workers=16`. At 100 concurrent viewers each requesting a cold page simultaneously, 100 storage downloads are queued against 16 threads per process. Each download blocks a thread. Peak queue depth = 100 - 16 = 84 requests waiting.

---

## Section 3 — Cache Analysis

### Cache Inventory

| Cache | Type | Max Entries | TTL | Memory est. | Hit Rate Est. |
|-------|------|------------|-----|------------|--------------|
| `link_cache` | FIFO TTL dict | 2,000 | 10s | ~1MB | 80-95%+ |
| `doc_cache` | FIFO TTL dict | 1,000 | 60s | ~0.5MB | 85-98% |
| `page_cache` (metadata) | FIFO TTL dict | 10,000 | 300s | ~2MB | 90-99% |
| `text_content_cache` | FIFO TTL dict | 100 | 300s | up to 500MB | 95%+ |
| `chunk_array_cache` | FIFO TTL dict | 100 | 300s | ~50MB | 95%+ |
| `toc_cache` | FIFO TTL dict | 500 | 300s | ~25MB | 90%+ |
| L1 page bytes | LRU OrderedDict | 600 entries | LRU | ~150MB | 40-70%* |
| L1 thumb bytes | LRU OrderedDict | 2,000 entries | LRU | ~10MB | 60-80% |
| L2 page bytes | Redis | unlimited | 3600s | ~60GB max | 60-90%* |
| L2 thumb bytes | Redis | unlimited | 3600s | large | 70-90% |
| L2 TOC | Redis | unlimited | 300s | ~2MB | 90%+ |

*page bytes L1 hit rate depends heavily on document count and access patterns.

### Critical Cache Issues

**1. L1 caches are per-process, not shared.**  
With `--workers 2`, uvicorn runs 2 separate Python processes. Each has its own `link_cache`, `doc_cache`, `page_cache`, and page-bytes LRU. A link lookup that misses in process 1's cache and hits in process 2's cache still triggers a DB read in process 1. Under load, a viewer's requests are round-robined between processes, halving the effective cache hit rate for link and doc metadata.

**The fix is already in place for bytes (L2 Redis), but NOT for metadata (link_cache, doc_cache, page_cache are L1-only).**

**2. FIFO eviction vs LRU in metadata caches.**  
`_TTLCache` uses FIFO eviction (pops the oldest-inserted entry when full). Under non-uniform access patterns (most popular doc gets many requests, old docs get occasional requests), FIFO evicts recently-accessed hot entries. For a trainer with one widely-shared document and 9 old documents, the hot document's metadata can be evicted by the cold documents' entries. LRU would retain hot entries longer.

**3. text_content_cache has no upper memory bound enforcement.**  
The cache is capped at 100 entries, but each entry can be up to 5MB (`TEXT_CONTENT_MAX_BYTES = 5MB`). Maximum memory: 500MB just for this cache. With 2 uvicorn workers: 1GB for text caches alone. This is fine for PDFs but could be problematic if 100 large text files are cached simultaneously.

**4. Frontend page cache (30 pages, blob URLs) is ephemeral.**  
The browser-side page cache stores 30 blob URLs per session. This is correctly implemented (eviction + URL.revokeObjectURL). However, the cache is session-scoped and tab-isolated — a viewer who opens the same document in two tabs will hit the backend twice per page. This is by design (security) but worth noting for bandwidth estimates.

**5. Validate endpoint does not benefit from any cache.**  
Every `/validate` call reads fresh from DB (correctly, since it writes session state). The 5-7 DB reads at validate time are unavoidable. This is the most expensive endpoint per call but is rate-limited to 20/minute and only called once per session establishment.

### Cache Effectiveness by Workload

| Workload | L1 Link Cache | L1 Doc Cache | Page Bytes L1 | Page Bytes L2 |
|---------|--------------|-------------|--------------|--------------|
| 10 viewers, 1 document | 90%+ | 90%+ | 60-70% | 90%+ |
| 100 viewers, 5 documents | 90%+ | 85%+ | 40-50% | 80-90% |
| 100 viewers, 50 documents | 80-85% | 80-85% | 20-30% | 70-85% |
| 500 users, 100+ docs | 70-80% | 75-85% | 15-20% | 65-80% |

The Redis L2 byte cache is the most critical cache for scale. A cold Redis is significantly worse than a warm one.

---

## Section 4 — Database Analysis

### Index Inventory

| Table | Indexed Columns | Index Type | Notes |
|-------|----------------|-----------|-------|
| documents | `id` | PK | ✓ |
| documents | `user_id` | B-tree (ix_documents_user_id) | ✓ |
| documents | `file_type` | B-tree (ix_documents_file_type) | Rarely queried |
| document_pages | `id` | PK | ✓ |
| document_pages | `(document_id, page_number)` | UNIQUE constraint | Implicit index ✓ |
| document_pages | `document_id` | **None explicit** | FK only, but covered by unique |
| share_links | `id` | PK | ✓ |
| share_links | `token` | UNIQUE constraint | Implicit index ✓ |
| share_links | `document_id` | B-tree (ix_share_links_document_id) | ✓ |
| access_events | `id` | PK | ✓ |
| access_events | `link_id` | B-tree (ix_access_events_link_id) | ✓ |
| access_events | `created_at` | B-tree (ix_access_events_created_at) | ✓ |
| access_events | `(link_id, created_at)` | **MISSING** | ⚠ Critical gap |
| access_events | `session_id` | **None** | Minor — not queried by value |
| viewer_sessions | `session_id` | PK | ✓ |
| viewer_sessions | `link_id` | B-tree (ix_viewer_sessions_link_id) | ✓ |
| viewer_sessions | `last_seen_at` | B-tree (ix_viewer_sessions_last_seen) | ✓ |
| document_groups | `id` | PK | ✓ |
| document_groups | `user_id` | B-tree (ix_document_groups_user_id) | ✓ |

### Query Pattern Analysis

**HOT PATH — `/api/viewer/page` (every page serve):**
```sql
-- All 3 run on cache miss only
SELECT * FROM share_links WHERE token = ?           -- UNIQUE idx ✓ ~0.5ms
SELECT * FROM documents WHERE id = ?               -- PK ✓ ~0.5ms
SELECT * FROM document_pages WHERE document_id=? AND page_number=? -- UNIQUE idx ✓ ~0.5ms

-- Every page serve (heartbeat)
SELECT * FROM viewer_sessions WHERE session_id = ? -- PK ✓ ~0.5ms
UPDATE viewer_sessions SET last_seen_at=? WHERE session_id=? -- PK ✓

-- Every page serve (analytics)
INSERT INTO access_events (...)  -- No PK lookup, just INSERT
```

**WARM PATH — DB operations per page request (most requests):**
- 0 SELECTs (all cache hits) + 1 GET (session PK) + 1 INSERT (analytics)
- Typical: ~5ms total DB time per request

**VALIDATE PATH — Called once per session:**
```sql
SELECT * FROM share_links WHERE token = ?           -- OK
INSERT INTO viewer_sessions (...)                   -- OK
UPDATE share_links SET view_count = view_count + 1 -- OK
INSERT INTO access_events (opened)                 -- OK
SELECT COUNT(*) FROM viewer_sessions WHERE link_id=? AND last_seen_at>=? -- OK
SELECT * FROM documents WHERE id = ?               -- OK
SELECT * FROM document_pages WHERE document_id=? ORDER BY page_number -- OK (up to 500 rows)
```
7 DB operations, 1 commit. Fast for current scale. At very high validate concurrency (>100 req/sec), the count query against viewer_sessions becomes a hot-row contention point.

**ANALYTICS PATH — Dashboard queries:**
```sql
-- GET /api/analytics/events (most concerning)
SELECT COUNT(*) FROM access_events WHERE link_id IN (...) -- needs (link_id, created_at) idx
SELECT * FROM access_events WHERE link_id IN (...) ORDER BY created_at DESC LIMIT 50
```
**MISSING INDEX:** `(link_id, created_at DESC)` composite index.

With the current separate indexes on `link_id` and `created_at`, PostgreSQL must either:
- Scan all events for the given link_ids, then sort by created_at, OR
- Use index scan on created_at and filter by link_id

Neither option is ideal. At 2M+ rows (after ~1 month at 5000-user scale), this query will take 1-5 seconds without the composite index.

**WORKER PATH — SELECT during orphan requeue:**
```sql
SELECT id FROM documents WHERE status='uploaded' AND updated_at < ?
```
No index on `(status, updated_at)`. Currently fast (small table) but degrades with more documents. Low priority for now.

### N+1 Patterns

**`list_documents` (dashboard):** Uses 3 batch queries (link counts, view counts, group info) — **no N+1**. ✓

**`get_document` single doc:** Runs a JOIN for stats + one pages query + one group query. 3 queries, no N+1. ✓

**`get_document_analytics`:** Runs 6 GROUP BY queries sequentially. All use IN clauses with pre-fetched link_ids — no N+1. ✓

**`assign_documents_to_group`:** Loops over `document_ids` with one DB query per ID — **O(n) queries**. For small lists this is fine, but bulk assignment of 50+ documents uses 50+ queries instead of one bulk UPDATE. Medium risk.

---

## Section 5 — Worker Analysis

### Current Worker Configuration

```yaml
# docker-compose.yml
command: ["celery", "-A", "app.workers.celery_app", "worker",
          "--loglevel=info", "--concurrency=2"]
```

**Concurrency=2:** Two Celery worker processes share one container. Each process runs one task at a time (the task is CPU-bound, using asyncio to run blocking operations). This means:

- Maximum **2 PDFs processing simultaneously**.
- Each PDF processing task:
  - Downloads PDF from S3: ~2-5s (network I/O)
  - Rasterizes with pdf2image/poppler: **30-300s** (CPU-bound, proportional to pages × DPI)
  - Forensic stamps each page: ~5ms per page (PIL CPU)
  - Uploads N pages to S3: N × 2-5s (network I/O)
  - Total for 50-page PDF at 150 DPI: **~60-180s**
  - Total for 200-page PDF at 150 DPI: **~5-15 minutes**

**Queue saturation risk:** With 10 uploaders each uploading 5 docs simultaneously, the queue has 50 tasks. With concurrency=2, processing takes 50/2 × avg_time. For 5-minute average: 125 minutes queue drain time.

### Worker Memory Profile

The rasterizer calls `pdf2image.convert_from_bytes(pdf_bytes, ...)` which:
1. Loads the entire PDF into memory (~10-50MB)
2. Calls poppler's `pdftoppm` as a subprocess
3. Returns PIL images — each A4 page at 150 DPI is **1240×1754 pixels = 2.18MP**
4. As RGBA in memory: **8.7MB per page**
5. For a 100-page PDF: **870MB PIL images in memory simultaneously**

The code processes pages sequentially but PIL images are returned as a list, so ALL pages are in memory at once during the rasterize call. `last_page = settings.max_pages_per_doc = 500` means a theoretical 500-page document at 150 DPI requires **4.3GB RAM** in the worker just for the PIL image list.

In practice most PDFs are 10-50 pages. But an adversarial PDF with 500 pages could OOM the worker container.

### Celery Configuration

`task_acks_late=True` + `task_reject_on_worker_lost=True` prevents task loss on worker crash. ✓  
`worker_prefetch_multiplier=1` prevents one worker from hoarding tasks. ✓  
`max_retries=3`, `default_retry_delay=10s` for transient failures. ✓  
`acks_late` means the task message is not ACKed until completion — if the worker crashes mid-processing, the task is requeued. Combined with `_should_process("processing", updated_at)` staleness detection (15-minute threshold), this recovers correctly. ✓

### Worker Risks at Scale

| Risk | Current Impact | At 10 Uploaders |
|------|---------------|----------------|
| Concurrency=2 bottleneck | Low (few uploads) | High — queue backlog |
| OOM on large PDF | Low risk | Medium — larger docs expected |
| No page-by-page commit | — | Medium — no partial progress |
| Sequential page upload to S3 | ~2-5s per page | High for large PDFs |

**Most impactful improvement:** Change upload loop in `pipeline/pdf.py` to upload pages as they are rasterized (instead of rasterizing all pages first, then uploading sequentially). This would also allow earlier streaming availability of pages.

---

## Section 6 — Frontend Performance

### Viewer Component (ViewerScreen)

**State count:** ~20 `useState` hooks in `ViewerScreen`. No `React.memo()`, no `useMemo()` anywhere in the codebase. For the current single-document viewer pattern, this is acceptable — the component is not re-rendered frequently enough to warrant memoization.

**Page loading pipeline:**
1. On session establish: `loadPage(token, 1, sessionId)` + prefetch page 2 in parallel ✓
2. On page change: `loadPage()` first, then prefetch ±1 on load complete ✓
3. Request deduplication: `inflightRef` prevents duplicate in-flight fetches ✓
4. Crossfade: previous image stays visible during next page load ✓
5. Frontend cache: 30 blob URLs, FIFO eviction with `URL.revokeObjectURL` ✓

**Thumbnail loading:**
- IntersectionObserver lazy loading: thumbnails only fetch when scrolled into viewport ✓
- Semaphore: max 6 concurrent thumbnail requests ✓
- Problem: **semaphore is module-level global** (`_thumbQueue`). Multiple ViewerScreen instances (same page) would share the same semaphore, interfering with each other. In practice, only one ViewerScreen mounts at a time, so this is theoretical.

**Status polling (UploadScreen):**
- 2-second interval, max 150 attempts (5 minutes total) ✓
- Polls `GET /api/documents/{id}/status` (lightweight endpoint) ✓

### Frontend Performance Issues

**1. No React.memo or useMemo.**  
The `PageThumb` component renders 500 items (max_pages=500) in the thumbnail strip. Each renders with useState hooks. Without virtualization or React.memo, navigating to a new page triggers re-render of all 500 thumbnails to check if `active` prop changed. For a 500-page PDF with the full sidebar rendered:
- 500 component instances
- Each with useState, useRef, useCallback, useEffect hooks
- Re-render on every page change

**Estimated impact:** ~5-10ms extra JS time per page navigation for large PDFs. Acceptable now, noticeable at 300+ pages on low-end devices.

**2. Thumbnail strip renders ALL pages at mount.**  
Even with IntersectionObserver preventing HTTP requests for off-screen thumbs, React creates 500 DOM elements + 500 IntersectionObserver instances simultaneously. For a 500-page PDF, this is:
- ~500 DOM nodes for the thumbnail strip
- ~500 IntersectionObserver instances
- Initial render time proportional to page count

For a 30-page document: fine. For a 300-page document: ~200ms initial render time on mobile.

**3. Upload screen polls every 2 seconds per upload.**  
With 10 uploaders each polling, that's 10 × 0.5 req/s = 5 req/s against the status endpoint. At current scale, negligible. At 10 uploaders × multiple docs in flight simultaneously, this could reach 20-50 req/s on the status endpoint.

**4. No service worker or background sync.**  
Page images are not persistently cached across sessions. Every new tab or browser restart clears the blob URL cache. For offline-resilient use cases, this is a limitation.

**5. Large single-file JSX (3,631 lines).**  
No code splitting. The full 116KB bundle is loaded before any content appears. For slow networks (e.g., student on mobile 3G), this adds ~1-3s to first meaningful paint. Bundle is loaded from `/static/dist/app.bundle.js` with a 1-hour CDN cache.

---

## Section 7 — Railway Deployment Readiness

### Current Railway Configuration

Based on `docker-compose.yml` and `Dockerfile`:

- **API:** 2 uvicorn workers per container, 1 container
- **Worker:** Celery with `--concurrency=2`, 1 container
- **Beat:** 1 container (singleton required)
- **DB:** Managed Railway Postgres (external from app containers)
- **Redis:** Managed Railway Redis (external)
- **Storage:** Cloudflare R2 / AWS S3 (external)

### Capacity Estimates

#### Current Scale (500 users, 10 concurrent viewers)

| Resource | Estimate | Railway Tier Needed |
|---------|---------|-------------------|
| API RAM | 300-400MB | Starter ($5/mo, 512MB) — tight |
| Worker RAM | 500MB-2GB burst | Starter ($5/mo, 512MB) — **insufficient for large PDFs** |
| API CPU | 0.1-0.3 vCPU steady | Starter ✓ |
| Worker CPU | 1-2 vCPU during rasterize | Starter ($5/mo, 0.25 vCPU) — **insufficient** |
| DB storage | ~10GB after 1 year | Starter DB ✓ |
| Redis memory | ~500MB page cache | Starter Redis ✓ |
| Egress bandwidth | ~50 MB/day | Fine |

**Worker is the critical constraint today.** The Celery worker container needs at least 1GB RAM and 1 dedicated vCPU for PDF rasterization. Railway Starter ($5/mo) provides 512MB RAM and 0.25 vCPU. Rasterizing a 100-page PDF requires 800MB+ RAM.

**Recommendation:** Worker must run on Railway Hobby plan ($10/mo, 8GB RAM, 8 vCPU) or equivalent.

#### Target Scale (5000 users, 100 concurrent viewers)

| Resource | Estimate | Railway Tier Needed |
|---------|---------|-------------------|
| API RAM | 700-900MB (2 workers) | Pro/Team plan — **need 1-2GB** |
| API CPU | 0.8-1.2 vCPU for watermarking | Pro plan ✓ |
| Worker RAM | 2-4GB per task | Pro plan (4GB+) |
| Worker concurrency | 4-8 recommended | Scale to 2 containers |
| DB connections | API: 30 max, Worker: 15 max | Standard PG ✓ |
| Redis memory | 1-3GB byte cache | Standard Redis ✓ |
| Egress bandwidth | 5-20 GB/day | Pro plan ✓ |

At 5000 users / 100 concurrent viewers, the architecture handles the load provided:
1. API is scaled to 2+ replicas (possible on Railway)
2. Worker concurrency is increased to 4-8
3. Redis has sufficient memory for the byte cache

### Railway-Specific Constraints

1. **Cold starts:** Railway containers have ~10-30s cold start times. With `restart: unless-stopped` and healthchecks, downtime per deploy is acceptable but visible.

2. **No persistent local disk:** Workers use S3/R2 for all storage — no `/tmp` dependencies for production (antiword writes temp files, but cleans them up). ✓

3. **Environment injection:** All config via `env_file: ./backend/.env`. Railway handles this via its environment variable UI. ✓

4. **Celery Beat — single instance:** Beat must not be scaled horizontally (it re-runs scheduled tasks). On Railway, this is a single fixed container. If Beat crashes, tasks miss their schedule until the next cycle. ✓ (acceptable for purge_stale_sessions; worst case: 30 minutes of delayed cleanup)

5. **Advisory lock on migration:** `migrate.py` holds a PostgreSQL advisory lock during migrations. This correctly serializes Railway multi-container restarts. ✓

6. **DB pool sizes:** API default `pool_size=10, max_overflow=20` = 30 max connections. Worker `pool_size=5, max_overflow=10` = 15 max. Total: 45 connections per API+Worker pair. Railway managed Postgres handles this easily.

---

## Section 8 — Cloudflare Readiness

### What Cloudflare Improves

| Feature | Benefit | Current State |
|---------|---------|--------------|
| TLS termination | No TLS config needed on Railway | ✓ Already using |
| Static asset CDN | `app.bundle.js`, `api.js` cached at edge | ✓ Already benefiting |
| DDoS protection | Layer 3/4 mitigation | ✓ Automatic |
| Bot protection | Reduces scraping and validate abuse | ✓ Available |
| Access Rules | Block countries/IPs before app | ✓ Available |
| `CF-Connecting-IP` | Real client IP for rate limiting | ⚠ Requires REAL_IP_HEADER=CF-Connecting-IP |
| Geo-routing | — | Not relevant at current scale |
| Cache rules (custom) | Could cache thumbnails at edge | ⚠ Not yet configured |

### What Cloudflare Cannot Improve

| Limitation | Reason | Impact |
|-----------|--------|--------|
| Watermarked page caching | `Cache-Control: no-store` — by design | All page requests hit API |
| Analytics endpoint | Per-user, per-session data | N/A for caching |
| Validate endpoint | Session-stateful — must hit API | Irreducible |
| Worker processing speed | S3 is external to Cloudflare | No benefit |
| DB latency | Internal DB connection | No benefit |

### Caching Opportunity: Thumbnails

Thumbnails are not watermarked and are identical across all viewers of the same document+page. They are served with `Cache-Control: no-store, no-cache, must-revalidate`. This is **unnecessarily strict for thumbnails**.

If thumbnail headers were relaxed to `Cache-Control: private, max-age=3600`, Cloudflare could cache them at the edge. However, because thumbnails require session validation (`session_id` param), Cloudflare cannot cache them by default (query string prevents caching of authenticated resources). A worker-level bypass rule (ignore `session_id` for thumbs) would enable edge caching, but introduces a minor security consideration (anyone with the URL could load the thumbnail without a valid session).

### Header Compatibility

| Cloudflare Behavior | Compatibility |
|---------------------|--------------|
| Strips `X-Request-ID` | No — echoed from incoming header. If Cloudflare passes through, preserved. ✓ |
| CSP enforcement | Handled by browser, not CF | ✓ |
| HSTS | CF respects `Strict-Transport-Security` header | ✓ When HSTS_MAX_AGE > 0 |
| `CF-Connecting-IP` | Injected by CF automatically | Requires `REAL_IP_HEADER=CF-Connecting-IP` in .env |
| Cache-Control: no-store on pages | Cloudflare respects this | Pages correctly bypass CF cache ✓ |
| `X-Frame-Options: DENY` | CF passes through | ✓ |
| Static JS: `public, max-age=3600` | CF caches for 1 hour | ✓ |

---

## Section 9 — Latency Improvement Roadmap

### High Impact

| # | Improvement | Expected Benefit | Complexity | Risk |
|---|------------|----------------|-----------|------|
| H1 | **Add composite index `(link_id, created_at DESC)` on `access_events`** | Analytics queries drop from 5-10s to <100ms at 2M+ rows | Very low (new migration) | None |
| H2 | **Increase Celery concurrency to 4-6 on a larger container** | 3× document processing throughput; eliminate upload backlog at 10 uploaders | Low (config change) | None |
| H3 | **Pipeline PDF page upload alongside rasterization** (upload each page immediately after rasterizing, don't batch) | Reduces total processing time by 30-40%; reduces peak worker RAM by 60-80% | Medium (refactor pipeline/pdf.py) | Low |
| H4 | **Move watermarking to the worker** (burn per-session watermark at view time is a design choice, but session-agnostic watermarks could be pre-computed) | N/A — current design is correct for security (per-session identity). Cannot pre-compute. | — | Not applicable |

### Medium Impact

| # | Improvement | Expected Benefit | Complexity | Risk |
|---|------------|----------------|-----------|------|
| M1 | **Switch metadata caches from FIFO to LRU eviction** | 10-30% improvement in cache hit rates under skewed access patterns | Low (viewer_cache.py) | Very low |
| M2 | **Add explicit index on `document_pages.document_id`** | Faster ORDER BY page_number scans in validate; negligible now, important at 10k pages | Very low (new migration) | None |
| M3 | **Throttle status polling from 2s to exponential backoff** (2s → 4s → 8s) | Reduces DB load during burst uploads; improves UX when processing is slow | Low (api.js) | Very low |
| M4 | **Virtualize thumbnail strip** (only render visible thumbnails + buffer) | Reduces initial render time for 300+ page docs by 80%; significant mobile improvement | Medium (app.jsx) | Low |
| M5 | **Relax thumbnail Cache-Control to `private, max-age=3600`** | Thumbnails served from L1/L2 without session_id re-validation on repeat visits | Low | Low (minor auth relaxation) |
| M6 | **Archive old access_events** (move rows older than 90 days to cold storage or delete) | Prevents unbounded growth; keeps analytics fast | Medium (new periodic task) | Low |
| M7 | **Add `(status, updated_at)` index on documents** for orphan-requeue query | Speed up orphan detection at large document counts | Very low | None |

### Low Impact

| # | Improvement | Expected Benefit | Complexity | Risk |
|---|------------|----------------|-----------|------|
| L1 | **Replace FIFO with bounded LRU in text_content_cache** | Memory safety for large text caches | Low | Very low |
| L2 | **Reduce rasterization DPI from 150 to 120** | 35% smaller page images, faster uploads, better cache density | Low (config) | Low (slightly less sharp) |
| L3 | **Add `React.memo` to `PageThumb` component** | Faster page navigation for 200+ page docs | Low | Very low |
| L4 | **Centralize storage key scheme** (StorageKeys class) | Prevents key inconsistencies in DOCX/PPTX expansion | Low | None |
| L5 | **Pre-warm Redis cache during document processing** | First viewer after upload gets L2 hit instead of S3 miss | Medium (push pages to Redis from worker) | Low |

---

## Section 10 — Go / No-Go Decision for DOCX/PPTX Expansion

### Current Architecture Assessment

Before answering the DOCX/PPTX question, a clear picture of where the system stands:

| Dimension | Current State | Ready for DOCX/PPTX? |
|-----------|-------------|---------------------|
| PDF pipeline | Stable, well-tested | ✓ Unchanged |
| Text pipeline | Stable (txt/md/log/docx/doc) | ✓ DOCX already works |
| TOC extraction | Working for all formats | ✓ |
| Worker concurrency | Constrained (2) | ⚠ Needs increase for parallel uploads |
| Storage key scheme | Implicit, works | ⚠ Add StorageKeys before new formats |
| Analytics | Functional, index gap | ⚠ Add index before high volume |
| Railway sizing | Insufficient for worker | ⚠ Must resize before heavy usage |
| Frontend | Handles txt/md/docx render | ✓ |
| Security | Phase B1 complete | ✓ |

### DOCX/DOC Assessment (Already Implemented)

Both DOCX and DOC processing are already in the codebase (`pipeline/word.py`). The current implementation:
- Converts DOCX to Markdown via python-docx ✓
- Converts DOC to text via antiword subprocess ✓
- Stores as text, serves via `/api/viewer/text` ✓
- TOC extracted via heading styles ✓

The DOCX/DOC pipeline is already production-ready. **No blocker.**

### PPTX Decision

PPTX would require:
1. A new pipeline in `pipeline/pptx.py`
2. Either rasterize slides (similar to PDF) or convert to markdown
3. TOC = slide titles
4. python-pptx library for extraction

**Architecture readiness for PPTX:**
- The pipeline dispatch (`tasks.py`) already switches on `file_type` — adding "pptx" requires one elif branch ✓
- The document upload router already accepts `application/octet-stream` with extension-based detection ✓
- Storage key scheme would need a PPTX prefix ✓
- Frontend already handles text-mode view; slide rasterization would reuse PDF viewer ✓

**Performance consideration for PPTX rasterization:**
- PPTX slides are typically fewer (20-50 slides) and lower-res than PDF pages
- LibreOffice headless conversion is the standard approach (additional system dependency in Dockerfile)
- Worker RAM impact is similar to PDF processing

### Verdict: Go / No-Go

**DOCX/DOC expansion: GO NOW.**  
Already implemented and working. No blockers.

**PPTX expansion: CONDITIONAL GO.**  
Safe to implement with two preconditions:
1. Increase Celery concurrency (H2) and worker container size before enabling PPTX uploads — rasterization via LibreOffice is slower than poppler for PDFs.
2. Add `(link_id, created_at)` composite index (H1) before enabling, because PPTX training materials will generate more page_viewed events.

**Three fixes that MUST precede public wider use (regardless of DOCX/PPTX):**

1. **H1 — Add composite index** `(link_id, created_at)` on `access_events`. One-line migration. Zero risk. Will prevent analytics degradation.

2. **H2 — Resize worker container.** Celery concurrency=2 on 512MB RAM will OOM on large PDFs. Worker needs 2GB+ RAM and concurrency=4.

3. **Confirm `REAL_IP_HEADER=CF-Connecting-IP`** in production `.env`. Without this, IP allowlists and rate limiting are ineffective behind Cloudflare.

**Everything else on the roadmap can be implemented incrementally** without blocking either current operation or DOCX/PPTX expansion.

---

## Appendix: Missing Database Index (Priority Fix)

The critical missing index for analytics at scale:

```sql
-- Migration 012: Add composite index for analytics event queries
CREATE INDEX ix_access_events_link_created 
ON access_events (link_id, created_at DESC);
```

This covers:
- `GET /api/analytics/events` → `WHERE link_id IN (...) ORDER BY created_at DESC`
- `GET /api/analytics/documents` → `WHERE link_id IN (...) AND created_at >= ?`  
- The current separate indexes on `link_id` and `created_at` cannot satisfy both constraints simultaneously using an index-only scan.

Without this index, at 2M rows (1-month scale at 5000 users), analytics queries take **5-30 seconds**. With the composite index: **<100ms**.

---

*End of Phase C Audit. Phase D (competitor research) and Phase E (DOCX/PPTX planning) to follow.*
