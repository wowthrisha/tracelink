# Action 2 Design: Fix max_views Race Condition

**Status:** APPROVED  
**Date:** 2026-06-07  
**Risk Level:** Medium (modifies core validation flow)

---

## Current Architecture

`link_service.py:validate_link()` (step 4):
```python
if link.max_views is not None and link.view_count >= link.max_views:
    raise HTTPException(status_code=410, detail="Max views reached")
```

Then in `viewer.py:validate_link`:
```python
await link_svc.increment_view_count(db, str(link.id), commit=False)
```

Two separate operations on different queries.

---

## Problem

**Race condition:** Two concurrent `/validate` requests can both read `view_count = N-1`, both pass `N-1 < max_views`, both increment to `N` and `N+1` respectively. If `max_views = N`, the second request exceeds the limit.

**Impact:** With high concurrent share link access (e.g., DocSend-style "investor opens pitch deck"), the max_views limit can be exceeded by the concurrency factor. If `max_views=1` (one-time link), two concurrent requests can both succeed.

---

## Threat Model

1. **Unintentional:** Two browser tabs opening the same one-time link simultaneously
2. **Intentional:** Attacker sends 10 concurrent requests to exceed max_views=1 limit
3. **Incidental:** Heavy traffic to a link moments before max_views is hit

---

## Alternative Designs

**Option A: SELECT FOR UPDATE (pessimistic locking)**
```sql
SELECT * FROM share_links WHERE id=:id FOR UPDATE;
-- check in Python
UPDATE share_links SET view_count=view_count+1 WHERE id=:id;
```
- Pro: Explicit; familiar pattern  
- Con: Row-level lock held across Python check; reduces throughput under high concurrency

**Option B: Optimistic locking (version column)**
```python
UPDATE share_links SET view_count=view_count+1, version=version+1
WHERE id=:id AND version=:expected_version
```
- Pro: No locks  
- Con: Requires retry loop; adds roundtrips

**Option C: Atomic UPDATE ... RETURNING** (chosen)
```sql
UPDATE share_links
SET view_count = view_count + 1
WHERE id = :link_id
  AND (max_views IS NULL OR view_count < max_views)
RETURNING view_count, max_views, id
```
- Pro: Single atomic operation; no locks needed; PostgreSQL handles atomicity at row level
- Pro: Eliminates separate SELECT and UPDATE
- Pro: SQLite 3.35.0+ supports RETURNING (Python 3.9+ ships SQLite 3.35+)

---

## Chosen Design

Option C: Atomic UPDATE ... RETURNING.

The `validate_link()` method flow changes:
1. Remove step 4 (explicit max_views check before increment)
2. After all other checks (revoked, expired, password, email, IP) pass:
   - Execute atomic check-and-increment
   - If 0 rows returned → max_views exceeded → 410
   - If rows returned → use the returned `view_count` for any logging
3. Remove `increment_view_count()` from `link_service.py` (caller no longer needs it)
4. Remove explicit `increment_view_count()` call from `viewer.py:validate_link`

---

## Migration Plan

1. Modify `link_service.py:validate_link()` — steps 4 and increment
2. Remove `increment_view_count()` method (no callers after change)
3. Modify `viewer.py:validate_link` — remove explicit increment call
4. Write concurrent tests

No database migration required.

---

## Rollback Plan

Revert `link_service.py` and `viewer.py`. The two-query pattern can be reinstated.

---

## Performance Impact

**Positive:** One fewer DB round-trip per validate call. Before: SELECT + check + UPDATE = 2 queries. After: 1 atomic UPDATE.

---

## Security Impact

**Eliminates:** max_views bypass via concurrent requests  
**Preserves:** All other validation logic unchanged

---

## Test Plan

1. Single validate succeeds when view_count < max_views
2. validate returns 410 when view_count == max_views (already at limit)
3. Concurrent validate — run 10 threads simultaneously; verify total successes ≤ max_views
4. max_views=None → unlimited (no 410 ever from max_views)
5. Existing analytics events still logged on 410
6. view_count incremented exactly once per successful validate
7. Failed validates (wrong password, IP denied) do NOT increment view_count
8. Session reuse validate does NOT double-increment view_count
