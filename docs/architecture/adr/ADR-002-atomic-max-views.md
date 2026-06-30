# ADR-002: Atomic max_views Check-and-Increment

**Status:** Accepted
**Date:** 2026-06-07

## Context

The original validate flow checked `view_count < max_views` in one SELECT and incremented in a separate UPDATE. Under concurrent requests, both SELECTs could pass and both increment, exceeding `max_views`.

## Decision

Replace the two-query pattern with a single atomic PostgreSQL UPDATE:

```sql
UPDATE share_links
SET view_count = view_count + 1
WHERE id = :link_id
  AND (max_views IS NULL OR view_count < max_views)
RETURNING view_count, max_views
```

Zero rows returned means `max_views` was hit. The separate `increment_view_count()` method was removed from `link_service.py`.

## Consequences

- Race condition eliminated without advisory locks; PostgreSQL row-level locking handles atomicity
- One fewer DB round-trip on each validate call
- Requires SQLite 3.35.0+ for `UPDATE … RETURNING` (Python 3.9+ ships 3.35.0+)
