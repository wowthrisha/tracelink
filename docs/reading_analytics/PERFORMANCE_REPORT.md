# Performance Report — Reading Intelligence Engine

## Frontend Impact

### Bundle size
- Before: ~285kb
- After: 299.1kb
- Delta: **+14.1kb** (hook + 2 components + updated InsightsModal)

All new code is included in the main bundle (no code splitting needed — reading analytics is always active for authenticated viewers).

### Runtime overhead

| Component | Interval | CPU Impact |
|---|---|---|
| Active timer (perf.now arithmetic) | 1s | Negligible (<0.01ms) |
| Display state update (setInterval) | 1s | ~1 React reconciliation cycle |
| Batch flush (fire-and-forget fetch) | 5s | <1ms JS, async network |
| Idle detection (setTimeout reset) | Per interaction | Debounced, passive listeners |

All event listeners are passive (`{ passive: true }`) — they never block scroll or touch performance.

### Memory
- `state.current` ref: O(page_count) objects — ~50 bytes × 500 pages = ~25kb max
- No growing arrays in the hot path
- Cleanup on unmount: timers cleared, listeners removed

---

## Backend Performance

### Batch Ingest (`POST /api/reading/batch`)

Typical request size: 1–10 pages, ~2kb JSON.

| Operation | Estimated Time |
|---|---|
| Auth check (in-memory cache) | <1ms |
| Session upsert | 3–8ms |
| Page events upsert (per page) | 2–5ms each |
| Score computation (Python, in-memory) | <1ms |
| Total (10 pages) | 35–60ms |

The session upsert uses `SELECT + UPDATE` (not `INSERT ... ON CONFLICT`) because SQLAlchemy async session state must be managed explicitly. This is slightly slower than a single SQL upsert but avoids partial-update bugs.

### Heatmap Query (`GET /api/reading/document/{id}/heatmap`)

```sql
SELECT pre.page_number,
       COUNT(DISTINCT rs.id) AS session_count,
       AVG(pre.active_time_ms) AS avg_active_ms,
       ...
FROM page_reading_events pre
JOIN reading_sessions rs ON rs.id = pre.reading_session_id
WHERE rs.document_id = $1
GROUP BY pre.page_number
ORDER BY pre.page_number
```

With index `ix_rs_document_started` on `(document_id, started_at)`:
- 10,000 sessions × 30 pages = 300k rows → ~50ms
- 100 sessions × 30 pages = 3k rows → <5ms

### Insights Query

Fetches all sessions + page events for a document, runs in-memory. Bounded by session_count; at 1,000 sessions this is ~1,000 Python objects → <10ms computation.

---

## Scalability Notes

### Horizontal scaling
All state is in PostgreSQL. The backend is stateless — multiple FastAPI workers handle requests independently.

### Write amplification
Each 5-second batch from a viewer causes:
- 1 session row read + write
- N page event rows read + write (N = pages in batch)

At 1,000 concurrent viewers: ~200 writes/second to PostgreSQL. Within standard PostgreSQL limits (typically 5,000–10,000 writes/second on modern hardware).

### Read scaling
Heatmap and insights queries are read-heavy aggregations. At high traffic, these can be cached at the application layer (e.g., 60-second Redis cache). The current implementation queries live — acceptable for the expected scale.
