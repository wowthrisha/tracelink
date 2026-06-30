# Production Architecture Scorecard — SecureDoc

**Sprint:** 5.2 — Production Architecture & System Design Compliance Review  
**Date:** 2026-06-23  
**Purpose:** Single-page summary of architectural readiness across all 8 dimensions with scored verdict and final user-tier determination.

---

## Scoring System

Each dimension is scored 1–10:
- **8–10:** Production-grade. No action required at stated scale.
- **6–7:** Functional. Known gaps; manageable at current scale but should be addressed before growth.
- **4–5:** Degraded. Active weaknesses that will produce failures or unacceptable latency at scale.
- **1–3:** Critical gap. Will fail or create security incidents at stated scale.

---

## Dimension Scores

### 1. Frontend Architecture — 8/10
**Verdict:** PASS

**Strengths:**
- Three-stage cache hierarchy (L1 TTL → L2 Redis → S3) correctly implemented
- Cache invalidation on revocation is immediate (within the serving process)
- Viewer session validation on every page request (SEC-03 compliance)
- Rate limiting on content delivery (120/minute)
- Session-based watermarking with deterministic angle derivation (`viewer.py:49–60`)

**Gaps:**
- Process-local caches are not Redis-backed; multi-process deployments need pub/sub invalidation
- Viewer toolbar features (zoom, search, laser pointer) not exercised in this audit

**Score rationale:** Cache architecture is well-designed. The multi-process gap is a deployment concern, not a code defect. Score reduced from 10 for the unaddressed multi-process cache invalidation.

---

### 2. Backend Architecture — 6/10
**Verdict:** WARNING

**Strengths:**
- Fully async FastAPI + asyncpg — no blocking calls in the hot path
- Service layer separation (analytics, link, viewer services)
- Atomic view count increment (UPDATE with conditional WHERE + RETURNING)
- Atomic session creation (upsert pattern)
- Celery worker pipeline correctly separated from API process
- Graceful shutdown (DB engine disposed on SIGTERM)

**Gaps:**
- `get_overview()` loads all event timestamps into Python for date bucketing (SR-01 — VIOLATION at Tier 2)
- `get_overview()` materializes all user link IDs into Python lists (SR-02)
- `get_document_analytics()` returns all documents with no pagination (SR-04)
- Default DB connection pool (pool_size=5) insufficient for concurrent analytics users

**Score rationale:** The architecture is sound and the hot paths (viewer, validation) are well-optimized. The analytics service has a single, well-defined violation that reduces the score from what would otherwise be 8+.

---

### 3. API Design — 7/10
**Verdict:** PASS with caveats

**Strengths:**
- Consistent scope-based authorization on all authenticated endpoints (`require_scope()`)
- Rate limiting on all write endpoints
- VIEWER_LOGGABLE_EVENTS whitelist prevents client event injection
- Global exception handler prevents stack traces from leaking to clients
- JWT validation via Supabase JWKS preloaded at startup

**Gaps:**
- Analytics read endpoints have no rate limit (SR-10)
- `GET /api/viewer/gate/{token}` returns HTTP 200 for missing links
- `group_id` parameter silently ignored when malformed (returns all docs instead of 400)
- Inconsistent response envelope shapes across endpoints
- No pagination on document and group analytics list endpoints

**Score rationale:** Authentication and authorization are correct and consistent. The gaps are API design quality issues (not security issues), reducible to non-breaking fixes.

---

### 4. Database Design — 7/10
**Verdict:** PASS with caveats

**Strengths:**
- `documents` table: comprehensive index coverage (7 indexes including composite)
- `viewer_annotations` table: 4 composite indexes covering all query patterns
- `document_pages` table: unique constraint doubles as composite index
- All cross-table foreign keys declared with appropriate ON DELETE behavior
- Alembic migration history complete (24 migrations, 001–024)

**Gaps:**
- `access_events` missing `(link_id, event_type)` composite index — affects all 6 analytics aggregate queries
- `share_links` missing `(document_id, revoked_at)` composite index — active-link queries post-filter
- Policy fields stored as JSON Text (not JSONB) — no server-side querying possible
- `session_id` truncated to 8 chars at insert; column declared as `String(32)` — misleading schema

**Score rationale:** Core tables are well-indexed. The two missing composite indexes are the only material gaps. Both require a single-line migration each.

---

### 5. Security Controls — 9/10
**Verdict:** PASS

**Strengths:**
- PII hashed before persistence (IP, email, user-agent never stored in plaintext)
- Session IDs use `secrets.token_hex(16)` — 128-bit cryptographic entropy
- Password-protected links use bcrypt (via `hash_password`/`verify_password`)
- Production startup guard: blocks deployment if salts, URLs, or HSTS are misconfigured
- HSTS, CSP, X-Frame-Options, Referrer-Policy all set via middleware
- IP allowlist enforcement on content delivery (not just validation)
- CORS restricted to declared origins in production
- Event type whitelist prevents viewer event injection
- Concurrent session enforcement with stale session purge

**Gaps:**
- `HSTS_MAX_AGE=0` triggers warning but not an error — HSTS should be mandatory in production
- `get_or_create_viewer_profile` called inline on hot path — side effect on validation path
- Admin router not fully audited for scope isolation

**Score rationale:** Security posture is strong. The HSTS warning-vs-error gap is the only meaningful finding; the others are hardening improvements, not vulnerabilities.

---

### 6. Scalability — 5/10
**Verdict:** WARNING (Tier 1), VIOLATION (Tier 2+)

**Strengths:**
- Viewer content delivery scales well (3-tier cache reduces DB to near-zero for hot documents)
- Analytics batch queries (not N+1) — correct batching for links and events
- Async I/O throughout — no thread-blocking operations on the hot path

**Gaps:**
- `get_overview()` timestamp aggregation in Python breaks at 50K+ events/user/week (SR-01 VIOLATION)
- No pagination on analytics endpoints means response sizes grow unboundedly (SR-04)
- Missing `(link_id, event_type)` index means analytics latency scales with events-per-link (SR-05)
- Default DB connection pool (pool_size=5) insufficient for concurrent analytics users (SR-07)
- Process-local caches incompatible with multi-process deployment (SR-11)

**Score rationale:** The viewer path scales well. The analytics path has a known violation at Tier 2. Scalability score reflects the state of the most-stressed subsystem (analytics), not the overall system.

---

### 7. Observability — 7/10
**Verdict:** PASS

**Strengths:**
- Prometheus metrics middleware on all requests
- OpenTelemetry tracing configurable via environment variable
- JSON structured logging configurable (`ENABLE_JSON_LOGGING=true`)
- Request ID on every response (`X-Request-ID`)
- Startup logging for storage, proxy config, auth state

**Gaps:**
- No alerting thresholds defined (metrics are collected but not monitored)
- No SLO definitions (what constitutes an unacceptable p95 latency?)
- No database query latency metrics in the current middleware

**Score rationale:** The instrumentation foundation is good. The gap is operational process — alerting and SLO definition are not code, but their absence means incidents are invisible until users report them.

---

### 8. Operational Readiness — 7/10
**Verdict:** PASS

**Strengths:**
- 24-migration Alembic history with complete up/down coverage
- Production startup validation guards (5 hard-fail checks)
- Celery worker separated from API process
- Demo mode (`USE_DEMO_STORAGE=1`) isolated from production path
- Startup warnings for misconfigured proxy, CORS, and HTTPS settings

**Gaps:**
- Connection pool size not configured for production scale (pool_size=5 default)
- No documented runbook for DB migration rollback
- Admin router not audited for operational safety

**Score rationale:** The deployment foundations are solid. Pool size configuration is a 1-hour fix. Reduced from 8 for the missing runbook and unaudited admin router.

---

## Score Summary

| Dimension | Score | Verdict |
|---|---|---|
| Frontend Architecture | 8/10 | PASS |
| Backend Architecture | 6/10 | WARNING |
| API Design | 7/10 | PASS |
| Database Design | 7/10 | PASS |
| Security Controls | 9/10 | PASS |
| Scalability | 5/10 | WARNING |
| Observability | 7/10 | PASS |
| Operational Readiness | 7/10 | PASS |
| **Overall Average** | **6.9/10** | **CONDITIONAL** |

---

## Final Verdict

### READY FOR 100 USERS
**Confidence: HIGH**

At 100 beta users with ~1,000 documents, ~10,000 viewer events, and ~300 share links, no finding represents a blocking failure. The Python-side timestamp aggregation handles ~500 events per user per week without memory pressure. The default connection pool handles low concurrency. All security controls are operational.

**One pre-launch action required:**
- Add rate limiting to analytics read endpoints (SR-10) — 30-minute fix. Without this, a single user polling the analytics dashboard rapidly could generate 90+ DB queries/second.

---

### READY FOR 1,000 USERS — WITH CONDITIONS

**Confidence: MEDIUM**

Must complete before reaching 1,000 active users:

| Priority | Fix | Effort | Risk If Skipped |
|---|---|---|---|
| CRITICAL | Replace `get_overview()` timestamp loop with SQL GROUP BY | 1 day | Memory exhaustion, analytics timeouts |
| HIGH | Add pagination to `GET /api/analytics/documents` | 1 day | 500 KB+ response sizes, DB overload |
| HIGH | Add `(link_id, event_type)` composite index (migration) | 4 hours | Analytics latency 15× slower per link |
| HIGH | Increase DB pool_size to 20, max_overflow to 40 | 1 hour | Pool exhaustion under concurrent analytics |
| MEDIUM | Replace scoped_link_ids materialization with CTE | 2 days | IN clause degradation at scale |

**Total effort for Tier 2 readiness: ~5–6 developer-days.**

---

### NOT READY FOR 10,000 USERS

**Confidence: HIGH**

In addition to all Tier 2 fixes, requires:

| Fix | Effort | Risk If Skipped |
|---|---|---|
| Redis-backed caches with pub/sub invalidation | 3–5 days | Multi-process revocation bypass |
| CTE-based analytics queries (replace IN clauses) | 3 days | Query planner sequential scans |
| Viewer profile ID caching | 1 day | DB hotspot on validate endpoint |
| SLO definitions + alerting rules | 1–2 days | Incidents invisible until user reports |

**10,000-user scale requires a meaningful architectural investment in the analytics layer and cache invalidation strategy before it is safe to operate.**

---

## The One Fix That Matters Most Right Now

Before the first beta user, add rate limiting to the analytics endpoints:

```python
# routers/analytics.py
@router.get("/overview")
@limiter.limit("30/minute")
async def get_overview(...):
```

This prevents the most immediate operational risk (a polling client generating 90+ DB queries/second) with 30 minutes of work.

The second most important fix — replacing the timestamp aggregation loop — should be planned for the first week of beta when user volumes are still low and the performance impact will be visible in Prometheus metrics rather than in user-reported timeouts.

---

*Sprint 5.2 — Production Architecture & System Design Compliance Review. No implementation. Audit only.*
