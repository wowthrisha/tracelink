# System Design Compliance Report — SecureDoc

**Sprint:** 5.2 — Production Architecture & System Design Compliance Review  
**Date:** 2026-06-23  
**Scope:** Backend audit against scale targets: 100 beta users, 10,000 documents, 100,000 viewer events, 1,000 share links.  
**Method:** Direct source-code inspection of 16 backend files. No implementation. No code changes.  
**Verdict:** See Section 9.

---

## Classification Key

| Classification | Meaning |
|---|---|
| **PASS** | Correct implementation. No action required. |
| **WARNING** | Works now; degrades meaningfully under load. Should be addressed before 1,000-user scale. |
| **VIOLATION** | Active defect at stated scale targets. Will produce failures or unacceptable degradation. |

---

## 1. Frontend Architecture

### Finding 1.1 — Viewer Cache Layer (Three-Stage Read Path)
**Classification:** PASS  
**Component:** `routers/viewer.py:86–142` (`_get_cached_link_and_doc`), `services/viewer_cache.py`, `services/page_cache.py`  
**Evidence:** Link metadata is TTL-cached (10s), document metadata is TTL-cached (60s), page snapshots are TTL-cached (5 min). Page image bytes follow an L1 (in-process) → L2 (Redis, when configured) → S3 fallback chain. The cache fetch is `fetch_page_bytes(page_snap.storage_key)` at `viewer.py:238`.  
**Why it matters:** Without caching, each page request would issue 2–3 DB queries plus an S3 download. At 120 viewer requests/minute per the rate limiter, that would be 240–360 DB round-trips per minute per endpoint. The cache collapses this to near-zero for hot documents.  
**Recommended action:** None required at 100-user scale. At 1,000+ users, confirm Redis is deployed and cache hit ratios are monitored.  
**Estimated effort:** 0 (current state is adequate).

---

### Finding 1.2 — Cache Invalidation on Revocation
**Classification:** PASS  
**Component:** `services/link_service.py:277` (`invalidate_link`), `services/viewer_cache.py`  
**Evidence:**
```python
# link_service.py:274–278
link.revoked_at = datetime.now(timezone.utc)
await db.commit()
await db.refresh(link)
from app.services.viewer_cache import invalidate_link
invalidate_link(link.token, link_id=link.id)
```
Revocation immediately evicts both the link snapshot and all active sessions from the process-local cache.  
**Why it matters:** Without this, a revoked link could remain accessible for the full 10-second TTL window.  
**Recommended action:** None. If the deployment moves to multi-process or multi-node, this cache invalidation must be propagated via Redis pub/sub. Not a concern at 100-user scale.

---

### Finding 1.3 — React State Management Not Audited
**Classification:** N/A  
**Component:** Frontend (`src/`)  
**Evidence:** This audit covers backend architecture only. Frontend bundle size (246.4 KB from build output) and test coverage (13/13 passing) were verified in Sprint 4.8C. No frontend regressions identified in this review.

---

## 2. Backend Architecture

### Finding 2.1 — Async SQLAlchemy Throughout
**Classification:** PASS  
**Component:** All routers and services  
**Evidence:** All DB calls use `AsyncSession`, `await db.execute(select(...))`, `await db.commit()`. No synchronous ORM calls found. The engine is `create_async_engine` with `asyncpg` dialect (`database.py:1`).  
**Why it matters:** Synchronous ORM calls in an async ASGI application would serialize all requests through a single thread. The async implementation allows FastAPI to handle concurrent requests efficiently.

---

### Finding 2.2 — Service Layer Separation
**Classification:** PASS  
**Component:** `services/analytics_service.py`, `services/link_service.py`, `services/viewer_service.py`  
**Evidence:** Business logic is separated from router handlers. Routers call service layer; services own DB access patterns. Example: `routers/analytics.py:23` delegates immediately to `analytics_svc.get_overview(db, user_id=...)`.  
**Why it matters:** Testable business logic. Observed in test suite: `services/` is patchable separately from `routers/`.

---

### Finding 2.3 — Atomic View Count Increment
**Classification:** PASS  
**Component:** `services/link_service.py:242–257`  
**Evidence:**
```python
result = await db.execute(
    update(ShareLink)
    .where(
        ShareLink.id == link.id,
        or_(ShareLink.max_views.is_(None), ShareLink.view_count < ShareLink.max_views),
    )
    .values(view_count=ShareLink.view_count + 1)
    .returning(ShareLink.id)
)
row = result.fetchone()
if row is None:
    # max_views was hit
    raise HTTPException(status_code=410, detail="Max views reached")
```
Single `UPDATE ... WHERE ... RETURNING` — the conditional WHERE is evaluated atomically at PostgreSQL row lock level. No separate SELECT + UPDATE race condition.  
**Why it matters:** Without atomicity, two simultaneous viewers on a `max_views=1` link could both pass the check and both increment, allowing double-access.

---

### Finding 2.4 — get_overview() Loads All Timestamps Into Python
**Classification:** VIOLATION  
**Component:** `services/analytics_service.py:148–161`  
**Evidence:**
```python
week_q = select(AccessEvent.created_at).where(
    AccessEvent.event_type == "opened",
    AccessEvent.created_at >= week_start,
)
if scoped_link_ids:
    week_q = week_q.where(AccessEvent.link_id.in_(scoped_link_ids))
week_ts_rows = (await db.execute(week_q)).scalars().all()  # ALL timestamps into Python

date_counts: dict = {}
for ts in week_ts_rows:  # iterated in Python
    date_counts[ts.strftime("%Y-%m-%d")] = date_counts.get(..., 0) + 1
```
At 100,000 events (the stated scale target), if a single active user's documents generate 50K "opened" events in a week, this query loads 50,000 `datetime` objects into the Python process per analytics page load.  
**Why it matters:** Memory pressure and CPU time. Each `datetime` object is ~56 bytes. 50K = 2.8 MB per request per user. At 100 concurrent users checking analytics, this is 280 MB of unnecessary in-process data.  
**Recommended action:** Replace with SQL-level aggregation:
```sql
SELECT DATE(created_at) AS day, COUNT(*) FROM access_events
WHERE event_type = 'opened' AND created_at >= :week_start AND link_id = ANY(:link_ids)
GROUP BY DATE(created_at)
```
**Estimated effort:** 1 day. Replace the Python-side aggregation in `get_overview()` with a single SQL GROUP BY query.

---

### Finding 2.5 — get_overview() Loads All User Link IDs Into Python
**Classification:** WARNING  
**Component:** `services/analytics_service.py:73–83`  
**Evidence:**
```python
doc_ids_r = await db.execute(select(Document.id).where(Document.user_id == user_id))
doc_ids = [r[0] for r in doc_ids_r.all()]  # all doc IDs into Python list
if doc_ids:
    link_ids_r = await db.execute(select(ShareLink.id).where(ShareLink.document_id.in_(doc_ids)))
    scoped_link_ids = [r[0] for r in link_ids_r.all()]  # all link IDs into Python list
```
This then passes `scoped_link_ids` as an IN clause to 4 subsequent queries. At 100 beta users with 100 documents each = 10K doc IDs, each user's overview call generates an IN clause with potentially thousands of UUIDs.  
**Why it matters:** PostgreSQL IN clause with thousands of UUIDs works but is not optimal. More critically, the Python-side list grows without bound as a user accumulates documents.  
**Recommended action:** Replace with a correlated subquery or a JOIN-based approach that avoids materializing the full list.  
**Estimated effort:** 2–3 days.

---

### Finding 2.6 — Analytics Batch Queries Use Large IN Clauses
**Classification:** WARNING  
**Component:** `services/analytics_service.py:228–267` (`get_document_analytics`), `services/analytics_service.py:440–467` (`get_group_analytics`)  
**Evidence:** Both methods issue 6 and 4 aggregate `GROUP BY` queries respectively, each with `AccessEvent.link_id.in_(all_link_ids)`. The comment at line 224 reads "Batch event aggregates — one GROUP BY query per metric (6 queries total)". This is correctly batched (not N+1). The concern is the unbounded size of `all_link_ids` passed to the IN clause.  
**Why it matters:** At 1,000 share links per user, the IN clause contains 1,000 UUIDs per analytics query (6 queries × 1,000 UUIDs each). PostgreSQL handles this but the query plan may not use indexes efficiently beyond ~1,000 items.  
**Recommended action:** At 1,000+ users, consider replacing IN clauses with a JOIN against a CTE or a temporary table.  
**Estimated effort:** 2 days.

---

### Finding 2.7 — get_document_analytics() Returns All Documents With No Pagination
**Classification:** WARNING  
**Component:** `services/analytics_service.py:190–197`, `routers/analytics.py:28–46`  
**Evidence:** `GET /api/analytics/documents` has no limit/offset parameter. The service loads all documents for the user and returns all of them in a single response. A user with 10,000 documents gets a 10,000-item JSON response.  
**Why it matters:** HTTP response size grows linearly with document count. At 10,000 documents, the JSON response could be 1–5 MB per analytics page load. No pagination means no graceful degradation.  
**Recommended action:** Add `limit` and `offset` (or cursor) query parameters to `GET /api/analytics/documents`. Default limit of 50 or 100.  
**Estimated effort:** 1 day.

---

## 3. API Design

### Finding 3.1 — Consistent Scope-Based Authorization
**Classification:** PASS  
**Component:** All authenticated routers  
**Evidence:** Every authenticated endpoint uses `Depends(require_scope("X:read"))` or `Depends(require_scope("X:write"))`. Examples:
- `routers/analytics.py:22`: `require_scope("analytics:read")`
- `routers/documents.py:118`: `require_scope("documents:write")`
- `routers/viewer.py:184` (validate): no scope (intentionally public — viewer endpoints use token auth, not user auth)  
**Why it matters:** Consistent authorization boundary. No endpoint is accidentally unprotected.

---

### Finding 3.2 — Rate Limiting Consistently Applied
**Classification:** PASS  
**Component:** Multiple routers  
**Evidence:** Rate limits are tiered appropriately:
- Upload: `@limiter.limit("10/minute")` — `routers/documents.py:108`
- Validate: `@limiter.limit("20/minute")` — `routers/viewer.py:173`
- Page fetch: `@limiter.limit("120/minute")` — `routers/viewer.py:185`
- Write endpoints (general): `@limiter.limit("30/minute")`  
**Why it matters:** Prevents abuse of costly endpoints. Upload at 10/min prevents storage flooding.

---

### Finding 3.3 — Inconsistent Error Response Format
**Classification:** WARNING  
**Component:** Multiple routers  
**Evidence:** Most errors use `HTTPException(status_code=X, detail="...")` which produces `{"detail": "..."}`. However, some validation failures return `{"status": "...", "requires_password": false, ...}` (e.g., `routers/viewer.py:153`), mixing `{"detail": ...}` and structured status objects. The `GET /api/viewer/gate/{token}` endpoint returns `{"status": "not_found"}` with HTTP 200 for a missing link — a client cannot distinguish "link exists" from "link not found" by HTTP status code alone.  
**Why it matters:** API clients and frontend code must handle two different error formats. The HTTP 200 for "not_found" is semantically incorrect and may confuse monitoring tools that alert on 4xx/5xx.  
**Recommended action:** Standardize gate endpoint to return HTTP 404 for missing links, HTTP 410 for revoked/expired. Reserve the structured `{status: ...}` response only for active links.  
**Estimated effort:** Half-day.

---

### Finding 3.4 — Viewer Event Logging Whitelist
**Classification:** PASS  
**Component:** `models/event.py:28–35`  
**Evidence:**
```python
VIEWER_LOGGABLE_EVENTS = frozenset({
    "print_attempt", "copy_attempt", "right_click_attempt",
    "download_attempt", "completed", "printed",
})
```
Only these six event types can be submitted by the viewer client. All security-sensitive events (`access_denied`, `ip_blocked`, `session_limit_reached`, etc.) are logged exclusively server-side.  
**Why it matters:** Prevents a viewer from injecting fake security events (e.g., fake `opened` events to appear engaged, or fake `access_denied` to mask their access pattern).

---

### Finding 3.5 — Pagination Only on Events Endpoint
**Classification:** WARNING  
**Component:** `routers/analytics.py:88–100` (events has pagination), `routers/analytics.py:28–46` (documents has none)  
**Evidence:** `GET /api/analytics/events` accepts `limit` (max 500) and `offset`. `GET /api/analytics/documents` returns all documents with no limit. `GET /api/analytics/groups` returns all groups with no limit.  
**Why it matters:** As noted in Finding 2.7, unbounded document and group endpoints will produce large responses at scale. The pattern is inconsistent — if one endpoint has pagination, all list endpoints should.  
**Recommended action:** Add pagination to `/api/analytics/documents` and `/api/analytics/groups`.  
**Estimated effort:** 1 day.

---

## 4. Database Design

*See detailed findings in DATABASE_HEALTH_REVIEW.md. Summary below.*

### Finding 4.1 — Document Model Indexing: Adequate
**Classification:** PASS  
**Component:** `models/document.py:15–25`  
**Evidence:** `ix_documents_user_id`, `ix_documents_lifecycle_state`, `ix_documents_expires_at`, `ix_documents_file_type`, `ix_documents_org_id`, `ix_documents_parent_id`, and `ix_documents_status_updated` (composite) are all declared. Covers every common query pattern.

---

### Finding 4.2 — AccessEvent Missing (link_id, event_type) Composite Index
**Classification:** WARNING  
**Component:** `models/event.py:40–46`  
**Evidence:** Existing indexes: `(created_at)`, `(link_id)`, `(link_id, created_at)`. All 6 analytics aggregate queries filter by `link_id IN (...)` AND `event_type = 'X'`. The `(link_id, created_at)` index does not help for event_type filtering. PostgreSQL will use the link_id index and then apply the event_type filter as a table-level scan over the matching rows.  
**Why it matters:** At 100,000 events spread across 1,000 links (~100 events/link), this is imperceptible. At 1,000,000 events (1K users, active sharing), each analytics query scans all events for a set of links (~1,000 events/link) and filters by type in memory.  
**Recommended action:** Add `Index("ix_access_events_link_event", "link_id", "event_type")` in an Alembic migration.  
**Estimated effort:** Half-day (migration only, no code changes).

---

### Finding 4.3 — ShareLink Missing Active-Links Composite Index
**Classification:** WARNING  
**Component:** `models/link.py:11–13`  
**Evidence:** Only one explicit index: `ix_share_links_document_id`. Queries that look up active links for a document (e.g., in `get_group_analytics()` at `analytics_service.py:419–435`) filter on `document_id IN (...)` AND `revoked_at IS NULL`. Without a `(document_id, revoked_at)` composite index, every active-links check scans all links for a document.  
**Why it matters:** At 10 links per document × 10,000 documents = 100,000 link rows, every analytics call touches the full share_links table for active-link filtering.  
**Recommended action:** Add `Index("ix_share_links_doc_revoked", "document_id", "revoked_at")`.  
**Estimated effort:** Half-day.

---

## 5. Security Controls

### Finding 5.1 — PII Hashed Before Storage
**Classification:** PASS  
**Component:** `services/analytics_service.py:52–53`  
**Evidence:**
```python
viewer_email=mask_email(viewer_email) if viewer_email else None,
ip_hash=hash_value(ip) if ip else None,
user_agent_hash=hash_value(user_agent) if user_agent else None,
```
Viewer IP, email, and user-agent are all hashed or masked before persistence. Raw PII is never stored in `access_events`.  
**Why it matters:** GDPR/privacy compliance. A breach of the events table does not expose viewer PII.

---

### Finding 5.2 — Session ID Entropy
**Classification:** PASS  
**Component:** `services/link_service.py:281`  
**Evidence:** `secrets.token_hex(16)` generates a 32-character hex string from 128-bit cryptographic entropy. `secrets.token_hex` uses `os.urandom()`, which is cryptographically secure.  
**Why it matters:** 128-bit entropy makes session IDs unguessable. An attacker would need 2^127 guesses to predict a valid session ID.

---

### Finding 5.3 — VIEWER_LOGGABLE_EVENTS Whitelist
**Classification:** PASS — covered in Finding 3.4.

---

### Finding 5.4 — Production Startup Guard
**Classification:** PASS  
**Component:** `main.py:29–82`  
**Evidence:** In production mode, startup is blocked if any of the following are unset or misconfigured: `SUPABASE_URL`, `APP_PUBLIC_BASE_URL` (must be HTTPS, not localhost), `IP_HASH_SALT` (must not be the default placeholder), `DOMAIN_VERIFY_SALT` (same). `HSTS_MAX_AGE=0` triggers an error. Localhost CORS origins trigger a warning.  
**Why it matters:** Prevents accidental production deployment with development credentials or unsafe defaults.

---

### Finding 5.5 — Policy Fields Stored as JSON Text (Not JSONB)
**Classification:** WARNING  
**Component:** `models/link.py:24–28`  
**Evidence:**
```python
allowed_emails: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
allowed_domains: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
permissions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # JSON
ip_allowlist: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # JSON list
```
All policy fields are raw JSON strings. Parsing happens in Python on every validation call (`link_service.py:137` calls `json.loads(link.allowed_emails)`).  
**Why it matters:** Cannot index policy fields. Cannot query by specific policy attribute (e.g., "find all links with IP allowlist containing 192.168.1.x"). At current scale this is fine; at scale it prevents efficient policy-level queries.  
**Recommended action:** Migrate to JSONB columns. Not urgent at 100-user scale.  
**Estimated effort:** 3 days (migration + code change to remove `json.loads()` calls).

---

### Finding 5.6 — get_or_create_viewer_profile on Hot Validation Path
**Classification:** WARNING  
**Component:** `services/link_service.py:226–228`  
**Evidence:**
```python
if viewer_email:
    from app.services.viewer_profile import get_or_create_viewer_profile
    profile = await get_or_create_viewer_profile(db, viewer_email)
    profile_id = str(profile.id) if profile else None
```
This executes a SELECT + potential INSERT on every new viewer session that provides an email. The validate endpoint is already rate-limited to 20/minute, but the `get_or_create` is an additional DB round-trip on the hot path.  
**Why it matters:** At 1,000 concurrent viewers, this adds a DB round-trip per session creation.  
**Recommended action:** Move profile creation to a background task or deduplicate with a cache.  
**Estimated effort:** 1 day.

---

## 6. Scalability

*See full findings in SCALABILITY_RISK_REGISTER.md.*

### Summary Table

| Finding | Component | Breaks At | Classification |
|---|---|---|---|
| Python-side timestamp aggregation | `analytics_service.py:148–161` | 50K+ events | VIOLATION |
| Unbounded link_id list into Python | `analytics_service.py:73–83` | 10K+ links | WARNING |
| Missing (link_id, event_type) index | `models/event.py` | 1M+ events | WARNING |
| No pagination on document analytics | `routers/analytics.py:28` | 10K+ documents | WARNING |
| policy fields as JSON Text | `models/link.py` | scale | WARNING |

---

## 7. Observability

### Finding 7.1 — Prometheus Metrics Middleware
**Classification:** PASS  
**Component:** `middleware/metrics.py`, `main.py:178`  
**Evidence:** `PrometheusMiddleware` is registered as application middleware. HTTP request counts, latencies, and status codes are tracked per endpoint.  
**Why it matters:** Without metrics, production incidents are invisible until users complain.

---

### Finding 7.2 — OpenTelemetry Tracing Configured
**Classification:** PASS  
**Component:** `app/telemetry.py`, `main.py:97–98`  
**Evidence:**
```python
from app.telemetry import setup_tracing, instrument_app
setup_tracing(settings.otel_exporter_otlp_endpoint, settings.otel_service_name)
instrument_app(app)
```
OTel tracing is configured via `OTEL_EXPORTER_OTLP_ENDPOINT`. When not set, it is a no-op (does not crash).  
**Why it matters:** Distributed tracing allows cross-service debugging. At 100 users the value is limited; at 1,000+ users it becomes essential for latency debugging.

---

### Finding 7.3 — Request ID on Every Response
**Classification:** PASS  
**Component:** `middleware/request_id.py`, `main.py:185`  
**Evidence:** `RequestIDMiddleware` assigns a unique `X-Request-ID` header to every response, enabling log correlation between client errors and server logs.

---

### Finding 7.4 — JSON Structured Logging
**Classification:** PASS  
**Component:** `middleware/json_logging.py`  
**Evidence:** Configurable via `ENABLE_JSON_LOGGING=true`. When enabled, log output is machine-parseable JSON. Compatible with Datadog, Splunk, CloudWatch Logs Insights.

---

### Finding 7.5 — No Alerting Rules Defined
**Classification:** WARNING  
**Component:** None  
**Evidence:** Prometheus metrics are collected but no alerting thresholds are defined in the codebase. No PagerDuty/OpsGenie integration found.  
**Why it matters:** Metrics without alerts are passive. An analytics endpoint timing out at 5K events will not notify anyone until a user reports it.  
**Recommended action:** Define at minimum: P95 latency > 2s on `/api/analytics/*` endpoints, error rate > 1% on `/api/viewer/validate`, DB connection pool exhaustion.  
**Estimated effort:** Half-day to 1 day (infrastructure, not code).

---

## 8. Operational Readiness

### Finding 8.1 — Connection Pool Configuration
**Classification:** WARNING  
**Component:** `database.py`  
**Evidence:** The engine is created with `create_async_engine(settings.database_url, echo=False)`. No `pool_size`, `max_overflow`, or `pool_timeout` parameters are set explicitly — these default to SQLAlchemy defaults (`pool_size=5`, `max_overflow=10`). At 100 concurrent requests, 15 connections may not be sufficient.  
**Why it matters:** At default settings, 16 concurrent DB-bound requests will queue. FastAPI is async so actual concurrency per request is low, but analytics endpoints with 6+ DB queries can hold connections for >100ms.  
**Recommended action:** Set `pool_size=20, max_overflow=30` for a 100-user deployment.  
**Estimated effort:** <1 hour (environment variable addition).

---

### Finding 8.2 — Alembic Migration History Complete
**Classification:** PASS  
**Component:** `alembic/versions/` (24 migrations, 001–024)  
**Evidence:** 24 sequential migration files tracked. Most recent: `024_viewer_profiles.py`. Down-revision present in all migrations reviewed. Alembic history provides a complete audit trail of schema evolution.

---

### Finding 8.3 — No Dead Celery Task Paths
**Classification:** PASS  
**Component:** `workers/tasks.py`, `workers/pipeline/`  
**Evidence:** Demo mode (`USE_DEMO_STORAGE=1`) is gated separately: `_run_demo_processing()` in `routers/documents.py:40–68`. In production mode, Celery is used. The demo path is never reached in production due to the `if settings.use_demo_storage` guard.

---

### Finding 8.4 — Graceful Shutdown
**Classification:** PASS  
**Component:** `main.py:157–161`  
**Evidence:**
```python
from app.database import engine as _db_engine
if _db_engine is not None:
    await _db_engine.dispose()
    _shutdown_log.info("DB engine disposed on shutdown")
```
DB engine is cleanly disposed on SIGTERM, releasing all connection pool connections.

---

## 9. Final Verdict

| Area | Score | Top Finding |
|---|---|---|
| Frontend Architecture | PASS | Cache layer correctly implemented |
| Backend Architecture | WARNING | Python-side timestamp aggregation (V-01) |
| API Design | WARNING | No pagination on document analytics |
| Database Design | WARNING | Missing (link_id, event_type) composite index |
| Security Controls | PASS | Atomic increment, PII masking, production guards |
| Scalability | VIOLATION | Timestamp aggregation breaks at 50K+ events |
| Observability | WARNING | No alerting rules defined |
| Operational Readiness | WARNING | Default DB connection pool size |

**Overall:** READY FOR 100 USERS  
**Conditional:** READY FOR 1,000 USERS (requires V-01 fix + pagination + index)  
**Not Ready:** 10,000 USERS (requires V-01, pagination, index, connection pool, IN clause redesign)

See `PRODUCTION_ARCHITECTURE_SCORECARD.md` for the scored verdict and `SCALABILITY_RISK_REGISTER.md` for the full risk breakdown by user tier.

---

*Sprint 5.2 — Production Architecture & System Design Compliance Review. No implementation. Audit only.*
