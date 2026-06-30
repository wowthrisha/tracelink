# System Design Review

Scope: `docker-compose.yml`, `app/workers/celery_app.py`, `app/config.py`, storage adapters. This describes the deployable topology, not just code structure.

## Current Architecture

Six services defined in `docker-compose.yml`:

- **db** — PostgreSQL 16, single instance, local-only by design (comment: "in production use a managed DB via DATABASE_URL").
- **redis** — Redis 7, single instance, dual-purpose: Celery broker/backend AND (per SECURITY_AUDIT_REPORT.md Finding 6) *not currently used* for rate limiting, which is still in-process (slowapi default store) — a clear scaling gap given Redis is already present.
- **migrate** — one-shot Alembic runner under a Postgres advisory lock; `api`/`worker`/`beat` all `depends_on: migrate: service_completed_successfully`. Well-designed: prevents the classic "two app replicas race to run migrations" failure mode, and the comment block explains the Railway-deployment edge case (no dedicated migrate service there) explicitly.
- **api** — FastAPI + static frontend (`StaticFiles`), single container in this compose file, port 8000, `/health` healthcheck.
- **worker** — Celery, concurrency configurable via `WORKER_CONCURRENCY` (default 2), `WORKER_MAX_TASKS_PER_CHILD` configurable for production (recycles processes to bound PDF-library memory growth — a real, specific operational concern someone already hit).
- **beat** — Celery Beat, single instance required (comment explicitly warns: "running multiple Beat workers causes duplicate task submissions"). Runs `purge_stale_sessions` every 30 min, `requeue_orphaned_uploads` every 5 min.
- **backup** (profile-gated, off by default) — `pg_dump` via cron inside a postgres-alpine container, daily 02:00 UTC, 7-day local retention.

## Bottlenecks / Failure Points (as deployed today)

1. **Single Beat instance is a hard architectural constraint, not just a tuning choice.** If `beat` dies and Docker's `restart: unless-stopped` doesn't bring it back fast enough, `purge_stale_sessions` and `requeue_orphaned_uploads` simply stop firing — no error surfaces anywhere except an absence of expected behavior. No alerting on Beat liveness was found in the reviewed config.
2. **Rate limiting is in-process** (SECURITY_AUDIT_REPORT.md Finding 6) — the moment `api` is scaled to >1 replica, the effective rate limit becomes `N × intended_limit`. Redis is already a dependency; this is a config change away from being fixed, not a redesign.
3. **LibreOffice conversion runs in the same worker process pool as everything else** — no isolation between a malformed/slow document conversion and other queued Celery tasks. `WORKER_MAX_TASKS_PER_CHILD` mitigates memory creep but a single hung LibreOffice subprocess (bounded by its own timeout per SECURITY_AUDIT_REPORT.md) still occupies one of only `WORKER_CONCURRENCY` (default 2, recommended 4) worker slots for its duration.
4. **Single Postgres instance, no read replica.** All read-heavy paths (analytics aggregation, feedback listing, audit-log pagination) hit the same primary as all writes. Not a problem at current scale; becomes the first thing to address past ~1,000 concurrent users.
5. **No CDN/edge caching layer in front of `api`'s StaticFiles frontend serving** — every dashboard load round-trips to the single `api` container for the 199KB bundle.
6. **`viewer_cache.py`'s 5s/10s TTL caching is in-process (per-`api`-replica)**, not Redis-backed — once `api` scales to >1 replica, each replica independently re-queries the DB for session/link state every 5-10s rather than sharing a cache. Same class of issue as the rate limiter.

## Scaling Estimates

| Users (concurrent) | Behavior |
|---|---|
| **100** | Current single-replica `api`/`worker`/`db`/`redis` topology handles this comfortably. In-process rate limiting and caching are non-issues at this scale (single replica = no double-counting). Bottleneck risk: none observed. |
| **1,000** | Still likely fine on a single `api` replica if vertically sized adequately, but this is the point where the worker pool (`WORKER_CONCURRENCY=4` recommended) starts to matter for upload-processing latency — a burst of simultaneous uploads queues behind the LibreOffice conversion timeout. Recommend monitoring Celery queue depth. Database: single Postgres instance still fine for this read/write volume given the indexed hot paths confirmed in DATABASE_REVIEW.md. |
| **10,000** | This is where horizontal `api` scaling becomes necessary, which immediately exposes the two in-process-state bugs: rate limiting (Finding 6) and `viewer_cache` (#6 above) both need to move to Redis-backed implementations *before* adding a second `api` replica, not after — otherwise multi-replica deployment silently weakens both the security control (rate limiting) and the cache-consistency guarantee (stale session data could be read from one replica's cache after a revoke invalidates another's). Single Postgres primary likely still adequate with the existing indexes, but `pg_isready`-style health monitoring and connection pooling (PgBouncer or equivalent) become necessary as replica count grows. |
| **100,000** | Requires: Redis-backed rate limiting and caching (mandatory at this point, not optional), a read replica or equivalent for analytics/audit-log read paths, horizontal worker scaling beyond a single `worker` container (Celery already supports this — it's a compose/orchestration change, not a code change), and a CDN in front of the static frontend bundle. The `beat` single-instance constraint remains architecturally necessary (Celery Beat doesn't support multi-instance) but its liveness needs dedicated alerting at this scale since a silent Beat outage means `requeue_orphaned_uploads` silently stops recovering stuck uploads under much higher upload volume. LibreOffice conversion would benefit from a dedicated worker pool/queue separate from lightweight tasks (webhook delivery, analytics event ingestion) so a burst of large-file conversions doesn't starve fast tasks. |

## What's Architecturally Sound (don't redesign)

- The `migrate` advisory-lock pattern correctly solves multi-replica migration races and is explicitly documented for the Railway no-migrate-service edge case — this is exactly the kind of forethought that should be left alone.
- SSRF TOCTOU re-validation at webhook delivery time (separate from creation-time validation) is correct defense-in-depth and doesn't need rearchitecting.
- The Celery task structure (sync wrapper around testable async core) is the right shape for testability even though current test coverage of the wrapper layer itself is thin (see TECHNICAL_DEBT_REGISTER.md).
- `WORKER_MAX_TASKS_PER_CHILD` being externally configurable (not hardcoded) shows this was already tuned in response to a real memory-growth issue — good operational hygiene, keep it.

## Top Recommendation

Before any horizontal scaling of `api`, move rate limiting and `viewer_cache` from in-process to Redis-backed. This is the one change that gates safely scaling past a single `api` replica — everything else in the current design degrades gracefully or simply needs more resources, not a different architecture.
