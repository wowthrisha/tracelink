# Scalability Risk Register — SecureDoc

**Sprint:** 5.2 — Production Architecture & System Design Compliance Review  
**Date:** 2026-06-23  
**Scope:** Identify components that will degrade or fail under load at three user tiers.  
**Scale targets:**
- Tier 1: 100 beta users, ~1,000 documents, ~10,000 viewer events, ~300 share links
- Tier 2: 1,000 users, ~10,000 documents, ~500,000 viewer events, ~30,000 share links
- Tier 3: 10,000 users, ~100,000 documents, ~5,000,000 viewer events, ~300,000 share links

**Risk levels:**
- **GREEN:** No degradation expected. Scales without intervention.
- **YELLOW:** Degradation begins. Intervention recommended before crossing threshold.
- **RED:** Failure or unacceptable latency. Must be fixed before crossing threshold.

---

## Risk Summary Table

| ID | Component | Risk Description | Tier 1 (100 users) | Tier 2 (1K users) | Tier 3 (10K users) |
|---|---|---|---|---|---|
| SR-01 | `get_overview()` timestamp aggregation | Python-side date bucketing of all events | GREEN | YELLOW | RED |
| SR-02 | `get_overview()` scoped_link_ids list | All user link IDs materialized into Python | GREEN | YELLOW | RED |
| SR-03 | Analytics queries with large IN clauses | 6–9 queries × unbounded IN clause | GREEN | YELLOW | YELLOW |
| SR-04 | `get_document_analytics()` no pagination | Full document list returned per request | GREEN | YELLOW | RED |
| SR-05 | Missing `(link_id, event_type)` index | Analytics aggregate queries scan by link only | GREEN | YELLOW | RED |
| SR-06 | Missing `(document_id, revoked_at)` index | Active link queries post-filter in Python | GREEN | GREEN | YELLOW |
| SR-07 | Default DB connection pool (pool_size=5) | Pool exhaustion under concurrent analytics | GREEN | YELLOW | RED |
| SR-08 | Viewer profile creation on hot path | SELECT + potential INSERT per new session | GREEN | YELLOW | YELLOW |
| SR-09 | JSON Text policy columns | Python-side `json.loads()` per validation | GREEN | GREEN | YELLOW |
| SR-10 | Analytics endpoints not rate-limited | Polling clients can generate burst DB load | YELLOW | RED | RED |
| SR-11 | Process-local caches (no Redis) | Cache invalidation limited to single process | GREEN | YELLOW | RED |
| SR-12 | `get_group_analytics()` IN clause pattern | Same as SR-03 for group-level queries | GREEN | YELLOW | YELLOW |

---

## Detailed Risk Analysis

### SR-01 — Python-Side Timestamp Aggregation
**Severity at Tier 2:** HIGH  
**Severity at Tier 3:** CRITICAL  
**Component:** `services/analytics_service.py:148–161`  
**Evidence:**
```python
week_q = select(AccessEvent.created_at).where(
    AccessEvent.event_type == "opened",
    AccessEvent.created_at >= week_start,
)
if scoped_link_ids:
    week_q = week_q.where(AccessEvent.link_id.in_(scoped_link_ids))
week_ts_rows = (await db.execute(week_q)).scalars().all()  # ENTIRE RESULT SET INTO PYTHON

date_counts: dict = {}
for ts in week_ts_rows:
    date_counts[ts.strftime("%Y-%m-%d")] = date_counts.get(ts.strftime("%Y-%m-%d"), 0) + 1
```

**What happens at scale:**

| Tier | User Events in 7 Days | Objects Loaded Into Python | Memory/Request |
|---|---|---|---|
| Tier 1 (100 users) | ~5,000 total | ~500 per user avg | ~28 KB |
| Tier 2 (1K users) | ~200,000 total | ~5,000 per active user | ~280 KB |
| Tier 3 (10K users) | ~2,000,000 total | ~50,000 per active user | ~2.8 MB |

At Tier 3, loading 50,000 `datetime` objects into Python per request, with 100 concurrent users checking analytics = **5 million objects in Python memory simultaneously**, plus CPU time for 5 million `strftime()` calls.

**Fix:** Replace with a single SQL-side GROUP BY:
```sql
SELECT DATE(created_at) AS day, COUNT(*) as cnt
FROM access_events
WHERE event_type = 'opened'
  AND created_at >= :week_start
  AND link_id = ANY(:link_ids)
GROUP BY DATE(created_at)
```
Returns 7 rows maximum regardless of event volume.

**Effort to fix:** 1 day. No schema change needed.

---

### SR-02 — scoped_link_ids Materialized Into Python
**Severity at Tier 2:** MEDIUM  
**Severity at Tier 3:** HIGH  
**Component:** `services/analytics_service.py:73–83`  
**Evidence:**
```python
doc_ids_r = await db.execute(select(Document.id).where(Document.user_id == user_id))
doc_ids = [r[0] for r in doc_ids_r.all()]  # Python list, grows with document count
if doc_ids:
    link_ids_r = await db.execute(
        select(ShareLink.id).where(ShareLink.document_id.in_(doc_ids))
    )
    scoped_link_ids = [r[0] for r in link_ids_r.all()]  # Python list, grows with link count
```

**What happens at scale:**

| Tier | Docs per User | Links per User | Python List Size |
|---|---|---|---|
| Tier 1 (100 users) | ~10 | ~30 | 30 UUIDs × 16 bytes = ~500 B |
| Tier 2 (1K users) | ~100 | ~300 | 300 UUIDs = ~5 KB |
| Tier 3 (10K users) | ~1,000 | ~3,000 | 3,000 UUIDs = ~50 KB |

The list is then passed to every subsequent IN clause. Beyond ~1,000 items, PostgreSQL's IN clause planner may switch to a sequential scan (depending on table statistics and fill factor). Not a memory issue — a query plan issue.

**Additional issue:** Step 1 (load all doc IDs) and the `SELECT COUNT(*) FROM documents WHERE user_id = :id` at line 87 are redundant. The count is `len(doc_ids)`.

**Fix:** Replace the two-step ID materialization with a correlated subquery or CTE:
```sql
WITH user_links AS (
    SELECT sl.id FROM share_links sl
    JOIN documents d ON d.id = sl.document_id
    WHERE d.user_id = :user_id
)
SELECT COUNT(*) FROM access_events ae
JOIN user_links ul ON ul.id = ae.link_id
WHERE ae.event_type = 'opened' AND ae.created_at >= :today_start
```
**Effort to fix:** 2 days. Requires rewriting `get_overview()` query strategy.

---

### SR-03 — Analytics IN Clauses (6 Queries × Unbounded List)
**Severity at Tier 2:** MEDIUM  
**Severity at Tier 3:** MEDIUM  
**Component:** `services/analytics_service.py:228–267`  
**Evidence:** `get_document_analytics()` issues 6 aggregate queries, each with `AccessEvent.link_id.in_(all_link_ids)`. The list size equals the total number of share links for all documents being analyzed.

**What happens at scale:**

| Tier | Links in Query | IN Clause | PostgreSQL Response |
|---|---|---|---|
| Tier 1 | ~30 per user | Small | B-tree index scan, fast |
| Tier 2 | ~300 per user | Medium | B-tree bitmap scan, acceptable |
| Tier 3 | ~3,000 per user | Large | B-tree bitmap scan degrades; planner may switch to seq scan |

PostgreSQL's query planner switches from index scan to sequential scan when it estimates that scanning a large fraction of the table is faster than following index pointers. With 300K links and 3,000 items in the IN clause (1% of table), the planner may choose a seq scan over `access_events`, negating the `link_id` index.

**Fix:** Replace IN clause with a JOIN against a temporary table or CTE when list size exceeds ~500 items. Not urgent at Tier 1.

---

### SR-04 — No Pagination on Document Analytics
**Severity at Tier 2:** HIGH  
**Severity at Tier 3:** CRITICAL  
**Component:** `routers/analytics.py:28–46`, `services/analytics_service.py:190–197`  
**Evidence:** `GET /api/analytics/documents` returns all documents for the user in a single response. No `limit` or `offset` parameter.

**What happens at scale:**

| Tier | Docs per User | Response Size | DB Load |
|---|---|---|---|
| Tier 1 | ~10 | ~5 KB | 9 queries |
| Tier 2 | ~100 | ~50 KB | 9 queries + larger IN clauses |
| Tier 3 | ~1,000 | ~500 KB | 9 queries + very large IN clauses + 500 KB JSON |

**Fix:** Add `limit` (default 50, max 500) and `offset` query parameters. This is a 1-day fix and prevents all downstream scale problems with this endpoint.

---

### SR-05 — Missing (link_id, event_type) Composite Index
**Severity at Tier 2:** HIGH  
**Severity at Tier 3:** CRITICAL  
**Component:** `models/event.py:40–46`  
**Evidence:** All 6 analytics aggregate queries filter on `link_id IN (...)` AND `event_type = 'X'`. Current index covers only `(link_id)` and `(link_id, created_at)`.

**Query execution path without composite index:**
1. PostgreSQL uses `ix_access_events_link_id` to find all events matching `link_id IN (...)`
2. Of those events, filters `event_type = 'X'` sequentially
3. Step 2 scales with events-per-link, not with total events

**Query execution path with `(link_id, event_type)` index:**
1. PostgreSQL uses the composite index to directly access events matching both `link_id` and `event_type`
2. Only matching rows are accessed
3. Step 2 is eliminated

**Performance projection:**

| Events/link | Without index | With index | Ratio |
|---|---|---|---|
| 100 | ~2ms | ~0.5ms | 4× |
| 1,000 | ~15ms | ~1ms | 15× |
| 10,000 | ~150ms | ~5ms | 30× |

At Tier 3 with 10K events/link average and 6 concurrent analytics queries per request: **6 queries × 150ms = 900ms minimum analytics latency** without the index. With the index: **6 × 5ms = 30ms**.

**Fix:** Add Alembic migration:
```python
op.create_index("ix_access_events_link_event", "access_events", ["link_id", "event_type"])
```
**Effort:** Half-day. Highest ROI fix in this register.

---

### SR-06 — Missing (document_id, revoked_at) Index on share_links
**Severity at Tier 2:** LOW  
**Severity at Tier 3:** MEDIUM  
**Component:** `models/link.py:11–13`  
**Evidence:** Active-links queries use `WHERE document_id IN (...) AND revoked_at IS NULL`. The current `ix_share_links_document_id` index is used, but `revoked_at IS NULL` must be post-filtered.

At 3 avg links per document and 100K documents = 300K link rows: a `(document_id, revoked_at)` partial index would allow PostgreSQL to directly access only non-revoked links. Not urgent at Tier 1 or 2.

---

### SR-07 — Default DB Connection Pool Size
**Severity at Tier 2:** HIGH  
**Component:** `database.py` (pool_size not explicitly configured)  
**Evidence:** SQLAlchemy async engine created with default pool parameters:
- `pool_size=5` (default) — 5 persistent connections
- `max_overflow=10` (default) — 10 additional connections when pool is full

Total: 15 connections maximum.

**What happens at scale:**

| Concurrent Requests | Connections Needed | Pool Status |
|---|---|---|
| 15 | 15 | At limit |
| 20 | 20 | 5 requests queued |
| 50 | 50 | 35 requests queued, latency spikes |

Analytics endpoints hold DB connections for the duration of 9 sequential queries. At 100ms per analytics request × 15 simultaneous analytics users = 15 connections held for 100ms each = 150 connection-seconds per second required. With pool_size=5, this exhausts the pool at ~5 concurrent analytics users.

**Fix:** Set `pool_size=20, max_overflow=40` in `database.py` or via environment variable. This is a 1-hour change.

---

### SR-08 — viewer_profile Creation on Hot Validation Path
**Severity at Tier 2:** MEDIUM  
**Component:** `services/link_service.py:226–228`  
**Evidence:**
```python
if viewer_email:
    from app.services.viewer_profile import get_or_create_viewer_profile
    profile = await get_or_create_viewer_profile(db, viewer_email)
```
Every new viewer session that provides an email triggers a `SELECT ... WHERE viewer_email = :email`, and if not found, an `INSERT`. This is on the `POST /api/viewer/validate` path, which is rate-limited to 20/minute.

**What happens at scale:** At 1,000 active share links each receiving 20 validation attempts/minute = 20,000 `get_or_create` calls/minute. The `SELECT` has implicit index usage (assuming `viewer_email` is indexed on the profiles table — unverified). The `INSERT` rate is bounded by new unique viewers.

**Why not a Tier 1 risk:** At 100 users with 300 links, the validation rate is low.  
**Why a Tier 2 risk:** At 1,000 users sharing with 5–10 viewers each, validation rate grows significantly.  
**Fix:** Cache viewer profile IDs in Redis (or the viewer session record itself) to avoid the DB lookup on subsequent validations for the same email.

---

### SR-09 — JSON Text Policy Columns
**Severity at Tier 1-3:** LOW  
**Component:** `models/link.py:24–28`  
**Evidence:** `allowed_emails`, `allowed_domains`, `ip_allowlist`, `permissions` are stored as JSON Text and parsed with `json.loads()` on every validation call. At 100K validations/day, `json.loads()` on 200–500 byte strings adds ~0.01ms per call = 1 second of cumulative Python time per day. Not a scalability concern — a maintainability concern.

---

### SR-10 — Analytics Endpoints Not Rate-Limited
**Severity at Tier 1:** LOW  
**Severity at Tier 2:** HIGH  
**Component:** `routers/analytics.py:19–82`  
**Evidence:** No `@limiter.limit()` decorators on analytics GET endpoints.

**Attack vector:** A client (or a bug) polling `/api/analytics/overview` every 100ms would issue 10 requests/second, each requiring 9 DB queries = 90 DB queries/second from a single client. With 100 such clients = 9,000 DB queries/second.

**Fix:** Add `@limiter.limit("10/minute")` or `@limiter.limit("30/minute")` to all analytics GET endpoints. Dashboard polling should be at most once per minute.

---

### SR-11 — Process-Local Caches
**Severity at Tier 1:** GREEN  
**Severity at Tier 2:** YELLOW  
**Severity at Tier 3:** RED  
**Component:** `services/viewer_cache.py`, `services/page_cache.py`  
**Evidence:** Link, document, and page caches are process-local LRU/TTL caches. Invalidation on revocation (`invalidate_link()`) only clears the cache in the calling process.

**What happens at scale:**  
- Single process (Tier 1): Revocation is immediately effective. PASS.
- Multi-process/container (Tier 2+): Process A revokes a link. Process B still has the link cached (up to 10-second TTL). A viewer served by Process B can still access the revoked link for up to 10 seconds.

**Fix:** Redis-backed cache with pub/sub invalidation. Not needed at 100-user scale. Required before deploying multiple worker processes.

---

## Risk Matrix by Tier

### Tier 1 (100 Beta Users) — READY

| Risk | Status |
|---|---|
| SR-01 Timestamp aggregation | GREEN — ~500 events/user/week |
| SR-02 scoped_link_ids list | GREEN — ~30 links/user |
| SR-03 IN clause size | GREEN — ~30 links |
| SR-04 No pagination | GREEN — ~10 docs/user |
| SR-05 Missing index | GREEN — ~100 events/link |
| SR-06 revoked_at index | GREEN — ~3 links/doc |
| SR-07 Connection pool | GREEN — low concurrency |
| SR-08 Profile creation | GREEN — low validation rate |
| SR-09 JSON policy parsing | GREEN |
| SR-10 No analytics rate limit | YELLOW — must fix before launch |
| SR-11 Process-local cache | GREEN — single process |
| SR-12 Group analytics IN | GREEN |

**Action before beta launch:** Fix SR-10 (add rate limits to analytics endpoints). 30-minute change.

---

### Tier 2 (1,000 Users) — CONDITIONAL

Pre-requisites before reaching 1,000 users:

| Priority | Risk | Fix Required |
|---|---|---|
| CRITICAL | SR-01 | Replace timestamp loop with SQL GROUP BY DATE() |
| HIGH | SR-04 | Add pagination to document analytics |
| HIGH | SR-05 | Add (link_id, event_type) composite index |
| HIGH | SR-07 | Increase pool_size to 20+ |
| MEDIUM | SR-02 | Replace scoped_link_ids materialization with CTE |
| MEDIUM | SR-10 | Rate limit analytics endpoints |

---

### Tier 3 (10,000 Users) — NOT READY

In addition to all Tier 2 fixes:

| Priority | Risk | Fix Required |
|---|---|---|
| CRITICAL | SR-11 | Redis-backed caches + pub/sub invalidation |
| HIGH | SR-03 | Replace IN clauses with CTEs for large sets |
| HIGH | SR-02 | Full rewrite of scoped_link_ids pattern |
| MEDIUM | SR-08 | Profile ID caching |

---

*Sprint 5.2 — Production Architecture & System Design Compliance Review. No implementation. Audit only.*
