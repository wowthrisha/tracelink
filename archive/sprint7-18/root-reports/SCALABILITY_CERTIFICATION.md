# Scalability Certification — TraceLink

**Method**: source-code inspection of the actual deployed codebase, cross-referenced against live behavior observed during three prior live-QA sprints against the deployed Railway instance (V10.0–V12.0). **No synthetic load was generated against the production instance** — per explicit instruction, this is an architectural assessment, not a load test. Every finding below is labeled by evidence type:

- **[CODE]** — read directly in this review, cited with file:line.
- **[BROWSER]** — observed live in a real browser during a prior sprint's QA pass, cited to the sprint that found it.
- **[INFERENCE]** — an engineering judgment extrapolated from the above, not directly measured. Never presented as a benchmark or throughput number, since none were measured.

No benchmark numbers, RPS figures, or latency percentiles appear anywhere in this document — none were measured, and fabricating them would violate the mission's explicit instruction.

---

## 1. Database queries — pagination, N+1, indexes

**[CODE]** `list_documents` (`app/routers/documents.py:384-470`) fetches **every** document a user can see (owned + org-visible) in one unbounded query, with no `LIMIT`/`OFFSET` and no query parameter to request a page. It does, however, correctly avoid N+1: link counts, view counts, and group lookups are each done as a single batched query keyed by `IN (doc_ids)` (lines 422-449), not a per-document loop.

**[CODE]** Confirmed via grep across all 6 `GET ""` (list) endpoints (`documents.py`, `groups.py`, `links.py`, `api_keys.py`, `orgs.py`, `webhooks.py`): only `admin.py`'s audit-log endpoint (`limit: int = Query(50, ge=1, le=500)`, line 20) and `analytics.py` implement pagination. The other 5 do not — this matches a finding already on record from an earlier sprint (`ISSUE_DATABASE.md` M-7), re-confirmed here at the source.

- **Current scalability limit (estimated)**: comfortable into the low hundreds of documents/links/keys per account — this account (used across all live-QA sprints) has ~30 documents and shows no visible slowdown. **[INFERENCE]** Becomes a real problem in the thousands: every dashboard load, every Access Control screen open, and every API Keys/Webhooks screen open re-fetches and re-renders the *entire* unbounded set.
- **Primary bottleneck**: unbounded result sets, not N+1 — the query patterns themselves are already well-batched.
- **Why it becomes a bottleneck**: response payload size and JSON-serialization cost grow linearly with account age/usage with no ceiling; the frontend has no virtualization for these lists either (confirmed for the Upload/Access Control tables during live QA — full table always renders).
- **Recommended fix**: add `limit`/`offset` (or cursor-based pagination for the documents list specifically, since it's ordered by `created_at desc`) to the 5 unpaginated list endpoints, matching the pattern already proven out in `admin.py`.
- **Estimated engineering effort**: Small–Medium (1-2 days) — the query and response-shape changes are mechanical per endpoint; the larger cost is the corresponding frontend pagination UI across 5 screens.
- **Priority**: **Before 10,000 users.** Not urgent at current usage patterns (a single account's document count grows slowly), but this is exactly the kind of unbounded-query pattern that turns into an incident once a handful of power-user accounts accumulate large libraries.

## 2. Connection pooling

**[CODE]** `app/database.py:71-96` — `pool_pre_ping=True`, `pool_recycle` (env-tunable), `pool_size`/`max_overflow` (env-tunable, defaulting to 10+20=30 per process, per the inline comment at line 90). Sound defaults: pre-ping avoids handing out dead connections from Railway's managed Postgres (which closes idle connections server-side), and recycle avoids the same failure mode proactively.

**[CODE]** `Dockerfile` (tail) — the API container runs `uvicorn ... --workers 2` by default. **[INFERENCE]** That means 2 × 30 = 60 possible DB connections from a *single* API container replica. If this is horizontally scaled to N replicas (Railway supports this), total possible connections become 60×N, which will hit most managed Postgres tiers' `max_connections` ceiling (commonly 100-200 on hobby/starter tiers) well before N gets large.

- **Current scalability limit (estimated)**: fine for 1 replica at current traffic. **[INFERENCE]** A second replica alone could already threaten a small managed-Postgres connection ceiling if both replicas' pools fill concurrently (unlikely at today's traffic, plausible under any real growth).
- **Primary bottleneck**: no connection-count coordination across replicas — each replica's pool is sized independently of how many replicas exist.
- **Why**: `pool_size`/`max_overflow` are static, per-process env vars; nothing scales them down as replica count goes up, and nothing enforces a cluster-wide connection budget.
- **Recommended fix**: either front Postgres with a connection pooler (PgBouncer, or Railway's managed equivalent if available) so replica count doesn't multiply real DB connections, or document a hard replica-count ceiling relative to the DB tier's `max_connections` and enforce it in deploy config.
- **Estimated engineering effort**: Small (PgBouncer sidecar/managed add-on) to Medium (if migrating to a pooler requires prepared-statement-mode changes for asyncpg).
- **Priority**: **Before 1,000 users**, specifically before ever running more than 1 API replica — this is latent (not yet triggered, since the deployment is very likely still single-replica) but becomes an outage risk the moment horizontal scaling is turned on without addressing it first.

## 3. Async / background jobs, worker concurrency, PDF rendering

**[CODE]** `app/workers/celery_app.py` — sound configuration: `task_acks_late=True` + `task_reject_on_worker_lost=True` (a killed worker mid-task re-queues rather than losing the job — good failure-recovery posture), `worker_prefetch_multiplier=1` (avoids one worker hoarding queued jobs it can't get to), explicit soft/hard time limits (600s/660s) sized for "a 200-page PDF under normal R2 upload conditions" per the inline comment.

**[CODE]** `backend/.env.example` (WORKER_CONCURRENCY section) — explicitly documents the real constraint: **"PDF rasterization uses 800MB–4GB RAM per worker depending on page count"**, with a sizing guide (`WORKER_CONCURRENCY=2` for "1 uploader/10 viewers", `=4` for "10 uploaders/100 viewers", requiring 4GB+ RAM). `app/config.py:125` defaults `worker_concurrency: int = 2`.

**[CODE]** Document upload (`documents.py:277-278`) correctly queues via `process_document.delay(...)` rather than rasterizing inline — the upload request returns immediately; processing happens out-of-band. Confirmed **[BROWSER]** during V10.0 live QA: uploading a real PDF showed an immediate "processing" state, not a blocked request.

- **Current scalability limit (estimated)**: **[INFERENCE]** document *processing throughput* (not viewing) is capped at `WORKER_CONCURRENCY` PDFs rasterizing simultaneously — 2 by default. This is a deliberate, memory-driven ceiling, not an oversight: the team's own sizing guide states the exact RAM cost per worker and provides a concrete scaling knob.
- **Primary bottleneck**: memory, not CPU or queue depth — rasterization is stated to cost up to 4GB per concurrent worker.
- **Why**: PDF rasterization (image conversion for viewing) is inherently memory-hungry per page; running many workers concurrently on typical container RAM (Railway Hobby: 8GB per the .env.example comment) OOM-kills workers.
- **Recommended fix**: none needed as an urgent fix — this is already correctly tunable via `WORKER_CONCURRENCY` and documented. The actionable next step is purely operational: monitor actual memory usage in production and raise `WORKER_CONCURRENCY` (with proportionally more container RAM) as upload volume grows, per the existing sizing guide.
- **Estimated engineering effort**: None (config-only) unless memory-per-page needs genuine optimization (e.g., streaming rasterization instead of full-page-in-memory), which would be Large.
- **Priority**: **Before 10,000 users** (revisit the concurrency/RAM tuning as real upload volume data comes in) — **Future optimization** for any deeper rasterization-memory-efficiency work.

## 4. File upload/download pipeline

**[CODE]** Download (`app/routers/viewer.py`, `download_document`) was already fixed in an earlier sprint (V4.0, per `FIX_LOG.md`) to offload the blocking multi-page PDF write via `run_in_executor` rather than blocking the event loop — confirmed still in place this review.

**[CODE]** Page viewing (`viewer.py get_page`, reviewed in V11.0/V12.0 work) always proxies bytes through the API server — fetch (cache → storage), apply per-viewer watermark (Pillow, CPU-bound, offloaded to executor), then stream the response. **[INFERENCE]** This is architecturally required (watermarking must happen per-viewer, so a static presigned-URL/CDN-redirect pattern — which would otherwise be the standard high-scale approach for static file serving — isn't available for the *page-viewing* path specifically, only for the original-file storage layer). This means every single page view does real server-side image-composition work, not a cheap redirect.

**[CODE]** `StorageService.generate_presigned_url` exists (`app/services/storage.py:135`) and is used for *some* operations, but the primary viewer read-path does not use it (by design, per the watermarking requirement above).

- **Current scalability limit (estimated)**: **[INFERENCE]** fine at today's traffic; becomes the single most CPU-relevant per-request cost path at high view-volume, since it's real image processing (not I/O-bound proxying) on every page view of every watermark-enabled link.
- **Primary bottleneck**: server-side watermark compositing is unavoidably synchronous-per-request work (already offloaded off the event loop, but still consumes worker CPU time).
- **Why**: the product's core security feature (per-viewer watermarking) is fundamentally incompatible with the cheapest possible serving pattern (static CDN redirect).
- **Recommended fix**: the L1(local)/L2(Redis)/storage cache tier already in place (`fetch_page_bytes`/`store_page_bytes`, confirmed in earlier sprints' code reads) caches the *pre-watermark* bytes, correctly avoiding repeated storage fetches — but the watermark compositing itself still runs on every request since it's viewer-specific. No further fix is obviously safe without either (a) accepting the CPU cost as the price of the security feature, or (b) a genuinely large redesign (e.g., client-side watermark overlay, which would weaken the security guarantee and is explicitly the kind of "partially implement a security redesign" the earlier V10.0 mission was told never to do).
- **Estimated engineering effort**: N/A — no safe fix identified; this is an inherent tradeoff, not a bug.
- **Priority**: **Future optimization** — monitor CPU usage on the API/viewer path specifically as view-volume grows; no action needed now.

## 5. Reading Intelligence & Analytics aggregation

**[CODE]** Reviewed extensively in V11.0/V12.0: `ReadingAnalyticsService` (1257 lines) computes engagement/absorption/focus/consistency/attention/understanding scores from `ReadingSession`/`PageReadingEvent` rows. The per-page-average query added in V11.0 (`select(func.avg(PageReadingEvent.active_time_ms)).where(document_id=..., page_number=...)`) uses the existing composite index `ix_pre_document_page` (`document_id`, `page_number`) — confirmed indexed, not a table scan.

**[CODE]** `get_document_summary` (`reading_analytics_service.py:969-1019`) loads **all** `ReadingSession` rows for a document into Python to compute `statistics.median`/`statistics.mean` — this is the same unbounded-result-set pattern as §1, scoped to reading sessions instead of documents.

- **Current scalability limit (estimated)**: **[INFERENCE]** fine into the hundreds of sessions per document (typical for most shared documents); becomes a real cost for a viral/high-reach document with thousands of reader sessions, since the median/mean computation pulls every row into application memory rather than computing aggregates in SQL.
- **Primary bottleneck**: Python-side statistics on an unbounded row set instead of DB-side aggregation (`PERCENTILE_CONT`, `AVG` in SQL).
- **Why**: `statistics.median()` has no direct SQL equivalent as simply as `AVG`, so the current implementation understandably chose to pull rows and compute in Python — reasonable at today's scale, not at very high per-document view counts.
- **Recommended fix**: push median/percentile computation into SQL (Postgres supports `PERCENTILE_CONT` natively) for documents with a session count above some threshold, falling back to the current in-Python approach for typical documents.
- **Estimated engineering effort**: Small–Medium.
- **Priority**: **Before 100,000 users** / **Future optimization** — this only matters for individual documents with unusually high reach, not overall platform scale.

## 6. Share-link validation & authentication

**[CODE]** `viewer_cache.py` — the hottest read path (link/document/page lookups on every page view) is cached in a **process-local, in-memory TTL cache** (`_TTLCache`, FIFO eviction, no cross-process sharing). This is not an oversight — the module's own docstring explicitly documents the tradeoff: *"FastAPI runs uvicorn with workers=N using forked processes, not threads"* (line 33), and separately documents the security contract this implies: link revocation propagates "within < TTL seconds for new requests" (`LINK_TTL_SEC = 10.0`, line 46), with the *revoked_at* field re-checked against wall-clock time on every cache hit as a second, TTL-independent safety net.

**[BROWSER]** V12.0 live-verified that an Edit-Link permission change propagated to an already-open anonymous viewer session promptly (observed as effectively immediate in that test). **[INFERENCE]** That specific test's timing does not prove sub-10-second propagation is *guaranteed* under multi-process/multi-replica deployment — with the current 2-worker-per-container setup, an edit made via one worker process only invalidates *that process's* cache copy; a viewer request routed to the *other* worker process would still see the pre-edit permissions for up to `LINK_TTL_SEC` (10s) until natural TTL expiry. The V12.0 test's request likely landed on the same process that handled the edit (plausible with only 2 workers and a fast sequential test), which is why it appeared instantaneous — this is not a contradiction of the finding, just a reminder that a single successful live test doesn't rule out the documented, bounded staleness window on unlucky routing.

- **Current scalability limit (estimated)**: correctness-bounded, not throughput-bounded — the *maximum* staleness window is a known, fixed 10 seconds regardless of scale, by design.
- **Primary bottleneck**: cache coherence across processes/replicas, not raw capacity.
- **Why**: avoiding a Redis round-trip on the single hottest read path (every page view) is a deliberate, reasonable latency optimization; the cost is bounded (not unbounded) staleness.
- **Recommended fix**: **only if instantaneous (not "within 10s") propagation becomes a hard product requirement** — move link/document snapshot invalidation to a Redis pub/sub broadcast so all processes/replicas invalidate simultaneously on write, at the cost of a small latency/complexity increase on the hot read path. Until then, this is a reasonable, already-mitigated tradeoff, not a defect requiring a fix.
- **Estimated engineering effort**: Medium (Redis pub/sub invalidation broadcast + subscriber in each process).
- **Priority**: **Before 10,000 users** *if* horizontal scaling (multiple replicas) is turned on and instant-revocation is a hard requirement (e.g., for a compliance-sensitive customer who needs link revocation to be provably immediate, not "within 10 seconds"). **Future optimization** otherwise — the current bounded-staleness design is defensible for a document-sharing product.

## 7. Permission checks & authorization pattern

**[CODE]** Consistent pattern across every router reviewed this session (`documents.py`, `links.py`, `orgs.py`, `reading.py`, and others from prior sprints): resource ownership is checked via `WHERE {Resource}.user_id == current_user_id` (or org-membership joins for org-scoped resources) directly in the query, not filtered after the fact — the correct, IDOR-resistant pattern (a request for someone else's resource ID returns 404, not a 403 that would confirm the resource exists). `require_scope(...)` (`app/auth.py`) gates every write endpoint reviewed. This pattern was not newly discovered this sprint — it's been consistently observed across V10.0 through V12.0's code reads — but is re-confirmed here as architecturally sound for scale (it's a per-request query-level check, not a cached/stateful authorization decision that would need cross-process coordination).

- **Current scalability limit**: no scalability concern identified — this pattern scales linearly with request volume with no shared-state bottleneck.
- **Priority**: N/A — no action needed.

## 8. Audit logging

**[CODE]** Covered in depth in V12.0: `log_audit_event()` (`audit_service.py`) does `add()` + `flush()` only, requiring the *caller* to commit — a deliberate design allowing callers to batch the audit write into their own transaction. This session's V12.0 sprint found and fixed 3 call sites in `links.py` that never actually issued that commit, meaning those audit events were silently discarded in production (fixed, see `FIX_LOG.md` V12-1). Beyond that specific bug, the write pattern itself (one row insert per event, indexed on `actor_user_id`/`org_id`/`created_at`) has no scalability concern — a single-row insert per action is cheap regardless of volume.

- **Current scalability limit**: fine indefinitely for write volume. **[INFERENCE]** The *read* path (`GET /api/admin/audit-log`) is already paginated (`limit`/`offset`, max 500) — the one list endpoint in the codebase that got this right from the start.
- **Priority**: N/A for scale — the only real issue found (silent write loss) was a correctness bug, already fixed, not a scale limit.

## 9. Storage operations

**[CODE]** `StorageService` (S3/R2-compatible) — standard `boto3`-style client usage, `upload_fileobj`/`download_bytes`/`generate_presigned_url`. No obvious anti-pattern (e.g., no evidence of synchronous boto3 calls blocking the async event loop directly — need a full audit of every call site to be certain, which this review did not exhaustively do; flagging as **[INFERENCE]** rather than a confirmed finding).
- **Recommended verification** (not performed this sprint): audit every `StorageService` call site to confirm none run boto3's synchronous client directly on the event loop without `run_in_executor` — the same class of bug already found and fixed once in `viewer.py`'s download path (V4.0) could plausibly exist elsewhere in storage-touching code that wasn't specifically re-audited this sprint.
- **Priority**: **Before 1,000 users** — cheap to verify, and blocking-I/O-on-the-event-loop bugs compound badly under concurrent load (this exact bug class already caused one confirmed real issue in this codebase).

## 10. API response sizes, memory, CPU hotspots

**[INFERENCE]**, informed by §1 and §4: the two largest response-size/CPU-cost risks are the unbounded document/link list endpoints (§1) and per-request watermark compositing (§4). No other endpoint reviewed this sprint showed an obviously unbounded response shape. A genuine memory/CPU profiling pass (flame graphs, actual heap snapshots under real traffic) was not performed — that requires either production APM tooling or a controlled load test, both out of scope for this architecture-only review per the explicit instruction against generating live load.

- **Priority**: **Before 10,000 users** for the two already-identified unbounded-cost paths (§1, §4); genuine profiling is a **Future optimization** that should happen once real production traffic data exists to profile against — profiling synthetic load would produce numbers that don't reflect real usage patterns anyway.

## 11. Statelessness & horizontal-scaling readiness

**[CODE]** The one significant piece of process-local state identified is `viewer_cache.py` (§6) — everything else reviewed (sessions via JWT, rate limiting via Redis in production per `middleware/rate_limit.py:17-19`, Celery task state via Redis broker/backend) is already correctly externalized and safe for horizontal scaling.

- **Current scalability limit**: the app is **largely stateless and horizontally-scaling-ready**, with one known, bounded, already-documented exception (§6).
- **Priority**: **Before 1,000 users** if multiple API replicas are turned on (re-stating §2's connection-pool concern and §6's cache-coherence concern together — both are "safe today, latent risk the moment replica count > 1").

## 12. Failure recovery

**[CODE]** Celery: `task_acks_late=True` + `task_reject_on_worker_lost=True` (§3) — a worker killed mid-task re-queues the job rather than losing it. A scheduled task (`requeue-orphaned-uploads-every-5-min`, `celery_app.py` beat schedule) exists specifically to catch documents stuck in "processing" from a lost task. This is a genuinely good, deliberate failure-recovery pattern — positive finding, not a gap.
- **Priority**: N/A — already well-handled.

## 13. Observability

**[CODE]** `app/metrics.py` — real Prometheus instrumentation already in place: `http_requests_total`, `http_request_duration_seconds`, `viewer_validations_total`, `page_requests_total`, `document_uploads_total`, `upload_duration_seconds`, `processing_duration_seconds`, `downloads_total`, `share_links_created_total`/`revoked_total`, `webhook_deliveries_total`/`retries_total`, and more. Structured JSON logging exists and is applied consistently to both API and Celery worker processes (`_configure_worker_logging`, `celery_app.py`).

- **Current scalability limit**: genuinely strong — this is the kind of instrumentation that makes diagnosing a real scaling incident tractable, rather than something that needs to be retrofitted during one.
- **Priority**: N/A — this is a positive finding; no action needed, though it's worth explicitly confirming (not verified this sprint) that these metrics are actually scraped/dashboarded somewhere, since instrumentation that exists but isn't monitored provides false confidence.

## 14. Rate limiting

**[CODE]** `middleware/rate_limit.py:17-19` — Redis-backed in production (`storage_uri = settings.redis_url if app_env == "production" else None`), correctly shared across processes/replicas (unlike §6's viewer cache). Per-endpoint limits observed throughout this and prior sprints' code reads (e.g., `/api/reading/batch` at 30/min, `/api/notifications/stream` at 10/min, various `/api/reading/document/*` endpoints at 20-30/min).

- **Current scalability limit**: correctly architected for horizontal scaling.
- **Priority**: N/A — no action needed.

---

## Summary table

| Subsystem | Bottleneck | Priority | Effort |
|---|---|---|---|
| Unbounded document/link/key/webhook lists | No pagination on 5 of 6 list endpoints | Before 10,000 users | Small–Medium |
| Connection pooling across replicas | No cluster-wide connection budget | Before 1,000 users (if scaling replicas) | Small–Medium |
| PDF rasterization concurrency | Memory-bound, already tunable | Before 10,000 users (tune only) | None (config) |
| Per-viewer watermark compositing | Inherent CPU cost of the security feature | Future optimization | N/A (tradeoff) |
| Reading-session median/percentile computation | Python-side stats on unbounded rows | Before 100,000 users | Small–Medium |
| Process-local link/doc cache (≤10s staleness) | No cross-process invalidation broadcast | Before 10,000 users (if instant revocation required) | Medium |
| Storage call sites — blocking I/O audit | Unverified this sprint | Before 1,000 users | Small (verification) |
| Real profiling under production traffic | Not yet performed (needs real data) | Future optimization | Medium |

**Positive findings, no action needed**: authorization pattern (IDOR-resistant by construction), audit-log write/read scalability, Celery failure recovery, observability instrumentation, rate limiting architecture, upload/download async offloading.

## What this certification does NOT cover

- **Measured throughput or latency at any concurrency level** — none was generated, per instruction. Every "current scalability limit" above is either directly cited from code (e.g., explicit RAM-per-worker documentation) or an engineering inference, never a benchmark.
- **Actual production resource utilization** (CPU/memory/connection-pool saturation under real traffic) — this data doesn't exist yet for this application at any meaningful scale; it should inform future revisions of this document once available.
- **Frontend bundle size / render performance at scale** — out of scope for this backend-focused pass; a separate frontend performance review would be needed.
- **A full audit of every `StorageService` call site for blocking I/O** (§9) — flagged as a specific, cheap follow-up, not completed here.
