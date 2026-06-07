# Action 4 Design: Session Validation Cache

**Status:** APPROVED  
**Date:** 2026-06-07  
**Risk Level:** Low (additive cache layer)

---

## Current Architecture

`policy.py:is_active_session()` issues a `db.get(ViewerSession, session_id)` on EVERY call. This is called for every `/api/viewer/page`, `/api/viewer/thumb`, `/api/viewer/text`, `/api/viewer/toc`, and `/api/viewer/download` request.

At 100 concurrent viewers × 1 page/2s = 50 DB reads/sec on `viewer_sessions` table.  
With pool_size=10, max_overflow=20 → pool exhaustion risk above ~200 concurrent page requests/sec.

---

## Problem

- Each page request = 1 DB read for session validation (unavoidable correctness requirement)
- This is the most common DB operation in the system (every page load)
- `viewer_sessions` table grows unbounded between purges; reads slow as table grows

---

## Threat Model

1. Revocation: If link is revoked, all sessions for that link must stop being served. Cache must not serve stale "active" sessions beyond an acceptable window.
2. Session expiry: Sessions inactive for >120 minutes should not be served. Cache TTL covers this — a 5s cache miss eventually hits DB which enforces the 120min cutoff.
3. Cross-link replay: Already handled in `upsert_session()`. Cache stores (link_id, ...) so the link check is cache-hit-safe.

---

## Alternative Designs

**Option A: Redis session cache**  
- Pro: Shared across processes; scales horizontally  
- Con: Redis failure path must be handled; adds latency for Redis GET  
- Con: Session data is sensitive; Redis must be encrypted in transit

**Option B: Process-local cache with short TTL (chosen)**  
- Pro: Zero latency on hit (in-process dict lookup)  
- Pro: Redis unavailability doesn't affect session validation  
- Pro: Simple — uses existing `_TTLCache` infrastructure  
- Con: Not shared across API replicas (each replica has its own cache)  
- Acceptable: At typical scale (2-4 replicas), cache hit rate per replica is still ~90%

---

## Chosen Design

Add `session_cache: _TTLCache` to `viewer_cache.py` with TTL=5s, maxsize=50000.

Cache key: `session_id` (32 hex chars, globally unique)  
Cache value: `tuple(link_id: uuid.UUID, last_seen_at: datetime, viewer_email_masked: str | None)`

**Cache invalidation:**
- `invalidate_link(token)` already called on revocation → also purge sessions for that link_id
- We need `invalidate_sessions_for_link(link_id)` helper to scan session_cache
- 5s TTL provides natural fallback

**Modified flow in `policy.py:is_active_session()`:**
1. Check `session_cache.get(session_id)`
2. If hit: verify `cached.link_id == link_id` and `last_seen_at >= cutoff` → return True/False
3. If miss: DB lookup; if active, store in cache → return True/False

**Modified flow in `policy.py:upsert_session()`:**
1. Existing session update: update cache entry `last_seen_at`
2. New session insert: store in cache with current timestamp

---

## Migration Plan

1. Add `session_cache` to `viewer_cache.py`
2. Add `invalidate_sessions_for_link(link_id)` to `viewer_cache.py`
3. Update `invalidate_link()` to also call `invalidate_sessions_for_link(link_id)`
   - But `invalidate_link()` takes a token, not a link_id — need to look up link_id from link_cache first
   - Alternative: store session_id → link_id mapping, separate cache
4. Update `policy.py:is_active_session()` and `upsert_session()`

For `invalidate_link()` to purge sessions: the `LinkSnapshot` in `link_cache` contains `link.id`. We can pass the `link_id` to a separate `invalidate_sessions_for_link(link_id)` function. Call it from `revoke_link()` in link_service.py after the existing `invalidate_link(token)` call.

No database migration.

---

## Rollback Plan

Remove `session_cache` lookups from `policy.py`. Performance degrades to baseline but system remains correct.

---

## Performance Impact

**Before:** 1 DB read per page request = O(N) DB reads/sec with N concurrent viewers  
**After:** ~1 DB read per 5s per unique session = O(N/5) DB reads/sec  
**Memory:** 50,000 entries × (32 + 16 + 32 + 32) bytes ≈ 6 MB overhead

---

## Security Impact

**Preserved:** Cross-link replay protection (link_id checked on cache hit)  
**Preserved:** Session expiry (last_seen_at checked against cutoff on cache hit)  
**Preserved:** Revocation (<5s window on cache hit; immediate if link invalidated)  
**Risk:** ~5s window between session revocation and cache expiry for API-served pages (acceptable per ADR-004)

---

## Test Plan

1. Cache hit: second page request within 5s skips DB for session validation
2. Cache miss: first page request (no cache entry) hits DB
3. Expiry: cache entry expired after 5s; next request hits DB
4. Cross-link: cache hit with wrong link_id returns False (no DB access needed)
5. Revocation: `invalidate_sessions_for_link(link_id)` purges sessions immediately
6. New session: upsert_session stores entry in cache
7. Session refresh: upsert_session updates last_seen_at in cache
8. Cache size: 50001 entries evicts oldest (FIFO)
9. Thread safety: parallel page requests with same session_id don't corrupt cache
