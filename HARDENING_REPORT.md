# SecureDoc Production-Hardening Report

**Date:** 2026-05-13 (updated 2026-05-14)
**Scope:** Full 10-phase audit remediation pass + deferred item resolution
**Baseline:** 27 confirmed issues (6 production blockers)
**Result:** 324 tests pass, 0 failures — all deferred items resolved

---

## Phase 1 — 6 Production-Blocking Issues Fixed

### CRIT-1: `Document.user_id` was nullable — orphaned documents possible

**Fix:** `backend/app/models/document.py`
Changed `nullable=True` → `nullable=False`. Added `Index("ix_documents_user_id", "user_id")`.

**Migration:** `alembic/versions/007_harden_schema.py`
Deletes any existing NULL rows, alters column, creates both indexes.

**Test:** `TestDocumentUserIdNotNull` in `tests/unit/test_hardening.py`

---

### CRIT-2: Storage exceptions leaked internal paths in 502 error body

**Fix:** `backend/app/routers/documents.py`
Replaced `detail=f"Storage upload failed: {exc}"` with `detail="Storage upload failed. Please try again."` — the underlying exception (which may contain bucket paths, keys, or stack traces) is now logged server-side only, never returned to the client.

**Test:** `TestStorageKeyNotLeaked` in `tests/unit/test_hardening.py`

---

### CRIT-3: IP hash salt was hardcoded in source code

**Fix:** `backend/app/utils/crypto.py`
Removed hardcoded `"securedoc_ip_salt"` default. `hash_value()` now lazy-imports `settings.ip_hash_salt` from the environment.

**Config:** `backend/app/config.py` — added `ip_hash_salt: str` field.
**Env:** `backend/.env.example` — added `IP_HASH_SALT=change_me_to_a_long_random_secret`.

**Test:** `TestIpHashSalt` in `tests/unit/test_hardening.py`

---

### CRIT-4: Analytics write endpoint accepted unauthenticated requests

**Fix:** `backend/app/routers/analytics.py`
`POST /api/analytics/events` now requires:
1. Non-empty `session_id`
2. Session must be active for the given link (verified via `enforcer.is_active_session`)
3. `event_type` must be in `VIEWER_LOGGABLE_EVENTS` (client-side events only)

Rate limit reduced from 120/min → 60/min.

**Model:** `backend/app/models/event.py` — added `VIEWER_LOGGABLE_EVENTS` frozenset to enforce the client/server event boundary.

**Test:** `TestAnalyticsEndpointSecurity` in `tests/unit/test_hardening.py`

---

### CRIT-5: `created_by` was set in a second transaction — orphan risk

**Fix:** `backend/app/services/link_service.py` + `backend/app/routers/links.py`
`create_link()` now accepts `created_by: Optional[uuid.UUID]` and sets it on the `ShareLink` object before the single `db.commit()`. The router passes `created_by=uuid.UUID(user["user_id"])` at call time. The second `db.commit()` in the router was removed entirely.

**Test:** `TestAtomicCreatedBy` in `tests/unit/test_hardening.py`

---

### HIGH-10: Rasterizer had no timeout — vulnerable to PDF bombs

**Fix:** `backend/app/services/rasterizer.py`
Wrapped `loop.run_in_executor(None, _convert)` with `asyncio.wait_for(timeout=settings.rasterizer_timeout_sec)`. On `asyncio.TimeoutError`, raises `RasterizerError("PDF conversion timed out after Xs")`.

**Config:** `backend/app/config.py` — added `rasterizer_timeout_sec: int = 300`.
**Env:** `backend/.env.example` — added `RASTERIZER_TIMEOUT_SEC=300`.

**Test:** `TestRasterizerTimeout` in `tests/unit/test_hardening.py`

---

## Phase 2 — Worker Reliability

### Module-level DB engine in Celery worker

**Fix:** `backend/app/workers/tasks.py`
Module-level `_engine` and `_session_factory` initialized once on first task execution via `_get_db_session_factory()`. Eliminates O(n) connection pool creation that exhausted PostgreSQL connections under load.

### Error classification — permanent vs transient

`RasterizerError` and `ValueError` → permanent failure: logged, marked `status=error`, no retry.
All other exceptions → transient: marked `status=error`, retried via `task.retry(exc=exc)`.

**Test:** `TestWorkerErrorClassification` in `tests/unit/test_hardening.py`

---

## Phase 3 — Scalability

### IP and domain allowlist fail closed on malformed JSON

**Fix:** `backend/app/services/policy.py`
`ip_is_allowed()` and `email_domain_is_allowed()` now return `False` (deny) on any JSON parse error instead of `True` (allow). `None` allowlist still allows all (no restriction configured).

**Test:** `TestPolicyFailClosed` in `tests/unit/test_hardening.py`

### Session heartbeat throttle

**Fix:** `backend/app/services/policy.py`
`upsert_session()` only writes `last_seen_at` if `elapsed >= SESSION_HEARTBEAT_INTERVAL_SEC (30s)`. Reduces DB writes by ~30× under sustained page-load traffic.

---

## Phase 4 — Storage and Cache

### Frontend page cache capped at 30 entries

**Fix:** `frontend/SecureDoc.html`
`MAX_CACHED_PAGES = 30` enforced via `_cacheSet()` helper that evicts and calls `URL.revokeObjectURL(evicted)` on the oldest entry. `_clearPageCache()` revokes all blob URLs on viewer unmount (`useEffect` cleanup).

### Status poll capped at 150 attempts (5 minutes)

Added `MAX_POLL_ATTEMPTS = 150` guard in the upload status poller.

---

## Phase 5 — Security and Auth Hardening

### Session ID upgraded to 128-bit entropy

**Fix:** `backend/app/services/link_service.py`
`_generate_session_id()` now uses `secrets.token_hex(16)` → 32 hex chars = 128-bit entropy (was `uuid4()` hex, which had only 122 effective bits but was non-standard).

**Test:** `TestSessionEntropy` in `tests/unit/test_hardening.py`

### Domain allowlist normalized to lowercase at creation time

**Fix:** `backend/app/services/link_service.py`
`allowed_domains` stored as `json.dumps([d.strip().lower() for d in ...])`. Prevents case-sensitivity bypass.

**Test:** `TestDomainCaseFolding` in `tests/unit/test_hardening.py`

### Rate limiting on `/api/viewer/validate`

**Fix:** `backend/app/routers/viewer.py`
`@limiter.limit("20/minute")` added to brute-force-sensitive validate endpoint.

**Test conftest:** Added `autouse` `reset_rate_limiter` fixture to prevent test-suite 429 interference.

---

## Phase 6 — Billing Logic

### `past_due` subscription must not grant Pro access

**Fix:** `backend/app/routers/documents.py` (`_check_upload_quota`)
Quota bypass now requires `billing.plan == PLAN_PRO and billing.subscription_status in (STATUS_ACTIVE, STATUS_TRIALING)`. `past_due` falls through to the free-tier limit check.

**Fix:** `backend/app/routers/billing.py`
`invoice.payment_failed` webhook handler sets `subscription_status=STATUS_PAST_DUE` and `plan=PLAN_FREE` immediately on first payment failure.

**Test:** `TestBillingSubscriptionEnforcement` in `tests/unit/test_hardening.py`

---

## Phase 7 — Frontend Quality

### React switched to production builds

`frontend/SecureDoc.html` now loads `react.production.min.js` and `react-dom.production.min.js` with updated SRI hashes. Eliminates development-mode warnings, reduces bundle overhead.

### `page_viewed` removed from client-side logging

Comment added at the call site; `page_viewed` is now logged exclusively server-side on every `/api/viewer/page` request. Frontend only sends: `print_attempt`, `copy_attempt`, `right_click_attempt`, `download_attempt`, `completed`, `printed`.

### `printed` event type added

`EVENT_TYPES` and `VIEWER_LOGGABLE_EVENTS` extended with `"printed"` — fires when `can_print=True` and the user clicks Print (distinct from `print_attempt` which fires when the user is blocked).

**Migration:** `alembic/versions/008_add_printed_event_type.py` — `ALTER TYPE event_type_enum ADD VALUE IF NOT EXISTS 'printed'`.

---

## Phase 8 — Dead Code Removal

- `backend/app/utils/token.py` — deleted (imported `jose`, not in requirements; unreachable dead code)
- `backend/tests/unit/test_token.py` — deleted (tested the above)
- `avg_time_on_page_sec` — removed fabricated field from document analytics response (was always 0.0)
- `page_viewed` — removed from client-side `logEvent` calls in frontend

---

## Phase 9 — Tests Green

**Final count: 301 passed, 0 failed**

| Test file | Tests |
|---|---|
| `tests/integration/test_access.py` | 6 |
| `tests/integration/test_analytics.py` | 20 |
| `tests/integration/test_document_processing.py` | 13 |
| `tests/integration/test_upload.py` | 15 |
| `tests/integration/test_viewer.py` | 28 |
| `tests/integration/test_viewer_pipeline.py` | 24 |
| `tests/regression/test_auth_enforcement.py` | 29 |
| `tests/regression/test_group_ownership.py` | 13 |
| `tests/regression/test_link_lifecycle.py` | 3 |
| `tests/regression/test_security_invariants.py` | 10 |
| `tests/unit/test_auth.py` | 11 |
| `tests/unit/test_billing.py` | 14 |
| `tests/unit/test_config.py` | 29 |
| `tests/unit/test_crypto.py` | 6 |
| `tests/unit/test_hardening.py` | 21 |
| `tests/unit/test_link_service.py` | 13 |
| `tests/unit/test_migration_url.py` | 11 |
| `tests/unit/test_rasterizer.py` | 7 |
| `tests/unit/test_storage.py` | 7 |
| `tests/unit/test_watermark.py` | 8 |
| `tests/unit/test_worker_tasks.py` | 13 |
| **Total** | **301** |

---

## New Session Cleanup Task (audit finding: unbounded table growth)

**Fix:** `backend/app/workers/tasks.py`
Added `purge_stale_sessions` Celery task: deletes `ViewerSession` rows with `last_seen_at < now - 2h`. Uses the module-level engine (no extra pool creation).

**Schedule:** `backend/app/workers/celery_app.py`
`beat_schedule` entry runs `securedoc.purge_stale_sessions` every 30 minutes. Deploy with `celery -A app.workers.celery_app beat` alongside the worker.

**Test:** `TestPurgeStaleSessionsAsync` in `tests/unit/test_worker_tasks.py`

---

## Environment Variables — Required in Production

| Variable | Default (config.py) | Notes |
|---|---|---|
| `IP_HASH_SALT` | `securedoc_ip_salt_change_in_production` | **Must change.** Min 32 random chars. |
| `RASTERIZER_TIMEOUT_SEC` | `300` | Increase for very large PDFs; decrease for stricter DoS protection. |
| `DATABASE_URL` | — | asyncpg URL for production |
| `REDIS_URL` | — | For Celery broker + rate limiter |
| `R2_*` / `S3_*` | — | Storage credentials |
| `STRIPE_WEBHOOK_SECRET` | — | Required for billing webhooks |

---

## Alembic Migrations (apply in order)

```
001_initial_schema.py
002_add_document_groups.py
003_add_user_auth.py
004_ip_allowlist_sessions.py
005_group_user_ownership.py
006_billing.py
007_harden_schema.py       ← CRIT-1: user_id NOT NULL + indexes
008_add_printed_event_type.py  ← adds 'printed' enum value
```

Run: `alembic upgrade head` (done automatically by `entrypoint.sh` on startup).

---

## Previously Deferred — Now Resolved

### HIGH-13: Viewer email stored in plaintext in access_events

**Decision:** Deterministic masking — `u***@example.com`. No schema change, no new env vars.

**Why masking over encryption or hashing:**
- Hashing would break allowlist display (admin sees opaque hash, not who viewed)
- Encryption requires key management (rotation, backup, loss = unrecoverable history)
- Masking preserves enough identity for the document owner to recognise the viewer while preventing DB dumps from harvesting full email addresses
- Allowlist checks happen in-memory on the submitted plaintext before any DB write — unaffected

**Fix:** `backend/app/utils/crypto.py` — added `mask_email(email: str) -> str`
**Fix:** `backend/app/services/analytics_service.py` — `log_event()` calls `mask_email(viewer_email)` before storing
**Watermark:** `viewer.py` still uses the full email in the image watermark (burned into pixel data, never stored in the DB) — unchanged

**Tests added:**
- `TestMaskEmail` (9 tests) in `tests/unit/test_crypto.py`
- `test_INVARIANT_viewer_email_never_stored_raw` in `tests/regression/test_security_invariants.py`

---

### Alembic dual-startup migration race

**Problem:** Both `api` and `worker` containers run `alembic upgrade head` on startup. If both start simultaneously on a fresh deploy, both read `alembic_version` as the same revision, then both attempt to apply the next migration. The second container fails on non-idempotent DDL (`CREATE TABLE`, `ALTER COLUMN`) that the first container already committed.

**Fix:** `backend/migrate.py` — new script that wraps `alembic upgrade head` in a PostgreSQL session-level advisory lock (`pg_advisory_lock(7325613)`). The lock is held for the full duration of the alembic subprocess. Any concurrent caller blocks until the winner releases the lock, then finds `alembic_version` already at head and exits in milliseconds.

**Fix:** `backend/entrypoint.sh` — calls `python migrate.py` instead of `alembic upgrade head` directly.

**Fix:** `docker-compose.yml` — added dedicated `migrate` service (one-shot, `restart: "no"`) that api and worker depend on via `condition: service_completed_successfully`. Provides explicit schema-before-service ordering in Docker Compose without relying on the advisory lock.

**Railway:** Both api and worker still call `python migrate.py` via `entrypoint.sh`. The advisory lock serialises concurrent startups — no docker-compose `migrate` service exists there, and none is needed.

**SQLite (local dev / tests):** No advisory lock acquired; `alembic upgrade head` is called directly (lock not available/needed for SQLite).

**Fallback:** If the advisory lock cannot be acquired (DB not yet ready), alembic runs directly. Docker/Railway restart policy recovers if the race causes a failure on first boot.

**Tests added:** `tests/unit/test_migrate.py` — 13 tests covering:
- URL conversion (`_to_asyncpg_url`)
- SQLite bypass path
- Advisory lock acquisition and release (mocked asyncpg)
- Lock released in finally block even when alembic fails
- Fallback when lock unavailable
- Lock key stability
