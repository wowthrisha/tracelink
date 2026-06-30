# ADR-004: Viewer Session Cache (5-Second TTL)

**Status:** Accepted
**Date:** 2026-06-07

## Context

`is_active_session()` did a DB SELECT on every `/api/viewer/page` call. At 100 concurrent viewers × 1 page/2s = 50 DB reads/second on `viewer_sessions`, exhausting the connection pool before any other bottleneck.

## Decision

Add `session_cache: TTLCache(maxsize=50000, ttl_seconds=5.0)` to `viewer_cache.py`.

- Cache key: `session_id`
- Cache value: `(link_id, last_seen_at, viewer_email_masked)`
- On `upsert_session()`: update cache entry
- On `invalidate_link()`: scan and evict all sessions for that link_id immediately

5-second TTL chosen because revocation must propagate in < 10 seconds (link cache TTL), and 5s eliminates 95%+ of session DB reads.

## Consequences

- ~95% reduction in `viewer_sessions` DB reads under load
- ~50 MB memory overhead for 50,000 concurrent sessions (acceptable)
- A revoked session may serve at most 1 additional page within the 5-second window
- Direct `invalidate_link()` call purges sessions from cache immediately — revocation propagates in < 1 second when triggered explicitly
