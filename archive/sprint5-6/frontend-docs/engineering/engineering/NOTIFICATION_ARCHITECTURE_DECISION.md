# Notification Architecture Decision
Sprint: 4.6B Pre-Implementation Review
Date: 2026-06-22
Status: DECISION — Polling recommended

---

## Constraints Summary

| Constraint | Source | Impact |
|---|---|---|
| Railway 15-minute hard connection limit | Railway platform | Kills any persistent SSE connection every 15 minutes |
| Railway idle timeout | Railway platform | Connections with no traffic are terminated earlier |
| No email notifications required | Sprint spec | Removes a key reason to prefer SSE (async delivery) |
| Must persist notifications across refresh | Sprint spec | Requires a DB layer regardless of transport |
| Must support unread counts | Sprint spec | Requires queryable state, not just fire-and-forget |
| Must support notification history | Sprint spec | Requires durable storage, not just Redis pub/sub |
| Minimize operational complexity | Sprint spec | Weights toward the simpler transport |

---

## Current State Audit

### What the SSE infrastructure looks like today

`GET /api/notifications/stream` — `notifications.py`:
- Auth: `get_current_user` requires `Authorization: Bearer` header
- Browser `EventSource` API cannot send custom headers — **auth is currently incompatible with any browser SSE consumer**
- Keepalive ping: every 15 seconds (`: ping\n\n`)
- Application-level idle timeout: 300 seconds (5 minutes with no real message)
- Per-user connection limit: 5 — tracked in `_active_connections`, an in-process dict
- Workers: 2 (`Dockerfile:68: CMD ["uvicorn", ... "--workers", "2"]`) — the connection counter is **not shared across workers**; the effective limit is 5 per worker, not 5 per user globally

`publish_notification` — `notification_service.py`:
- Publishes to Redis pub/sub channel `securedoc:notifications:user:{user_id}`
- **Fire-and-forget**. No persistence. No retry.
- Returns `False` silently when Redis is unavailable.

**The critical finding:** `notification_service.py` has no database write. If the SSE connection is not open at the moment `publish_notification` fires, the event is gone permanently. There is no replay, no retry, no history. The requirements for persistence, unread counts, and notification history are **completely unmet** by the current SSE infrastructure.

### What the access_events table already provides

`AccessEvent` model (`models/event.py`) — table: `access_events`:
- Records every `opened` event when a viewer validates a share link
- Fields: `id`, `link_id`, `event_type`, `viewer_email`, `session_id`, `created_at`
- Indexed: `ix_access_events_created_at`, `ix_access_events_link_id`, composite `ix_access_events_link_id_created`
- Already queryable via `GET /api/analytics/events` (with auth, pagination, document/group filter)

This table is the authoritative, durable record of every document open. It already has everything needed for a notification center. It is NOT used by the current SSE infrastructure — `publish_notification` bypasses it entirely and goes straight to Redis.

---

## Option A — Polling

### How it works

The frontend polls `GET /api/analytics/events?event_type=opened&since={timestamp}` every 10–15 seconds. On each response, new events become toasts and are appended to an in-memory notification list. The `since` timestamp advances to the latest event seen. Unread count = events received since the user last clicked "Mark all read" (stored in localStorage).

### Engineering effort

**Backend change (1 hour):**
- Add `since` query parameter (ISO 8601 timestamp) to `GET /api/analytics/events`
- Filter: `AccessEvent.created_at > since`
- The composite index `ix_access_events_link_id_created` already covers this query path
- No migration. No new table. No schema change.

**Frontend (3–4 hours):**
- `useNotificationPoller` hook: `setInterval` at 12 seconds, calls `getEvents({event_type:'opened', since})`, deduplicates by event ID, fires toasts for new items
- `useNotificationStore`: in-memory list (AppShell state) + `unreadSince` in localStorage
- Notification bell icon in sidebar: badge showing unread count
- Notification center panel: list of recent opens, "Mark all read" button, timestamp

**Total: ~1 day. Zero infrastructure changes.**

### Maintenance burden

Extremely low. A `setInterval` with a standard `fetch` call. No persistent connections. No reconnect logic. No event ID tracking. No Redis dependency for delivery. If the backend is down, the poll fails silently and retries in 12 seconds.

### Infrastructure complexity

None. HTTP polling is stateless. Each poll is an independent authenticated request. Works identically whether there are 1 or 4 uvicorn workers. Works identically whether Redis is available or not. Works identically on Railway, on a local machine, or behind any reverse proxy.

### Reliability on Railway

**Excellent.** Polling is inherently immune to Railway's 15-minute connection limit because each request completes in under 200ms. There is no connection to kill. Reconnect is not a concept. Missed events during a network hiccup are caught on the next poll because the query uses a timestamp filter, not a stream cursor.

### User-perceived responsiveness

**12 seconds maximum latency.** In practice, average latency is 6 seconds (half the poll interval). For the primary use case — "the consultant wants to know when a prospect opened their proposal" — 6–12 seconds is indistinguishable from real-time. The decision to call or not to call is not made in the 6-second window. The human reaction loop is measured in minutes.

### Long-term scalability

At 100 concurrent active users, polling at 12-second intervals generates ~8 requests/second to the events endpoint. The `access_events` table query with a `since` filter on the indexed `created_at` column is a fast range scan — sub-millisecond at current data volumes. PostgreSQL with a connection pool handles this trivially.

At 10,000 concurrent users, polling generates ~833 requests/second to a single endpoint. This would require query optimization (a dedicated `GET /api/notifications/poll` endpoint with a narrower query and aggressive caching on the DB side). This is a solvable problem when SecureDoc has 10,000 simultaneous active users — which is not the current planning horizon.

---

## Option B — SSE

### How it works

The frontend opens a persistent `EventSource` connection to `GET /api/notifications/stream`. The backend maintains the connection, receives Redis pub/sub messages, and pushes them downstream. The client receives events without polling.

### Engineering effort

To meet **all five stated requirements** (live notification, persistence, unread counts, history, minimize operational complexity), SSE requires considerably more than the basic stream that currently exists:

**Backend changes required:**

1. **Auth fix** — Add `?token=` query param support to `/api/notifications/stream`. The current `get_current_user` dependency only accepts `Authorization: Bearer` headers. Browser `EventSource` cannot send custom headers. This is currently a hard blocker. (1.5 hours)

2. **Notification persistence** — Add a `notifications` database table:
   ```
   notifications(id, user_id, event_type, data_json, created_at, read_at)
   ```
   Without this table: unread counts, history, and replay after reconnect are impossible. (1 hour + migration)

3. **Update `publish_notification`** — Write to DB before publishing to Redis. This ensures events survive connection gaps. (1 hour)

4. **Add `GET /api/notifications/` endpoint** — Returns paginated notification history for the notification center. Needed for unread count on page load and history display. (1 hour)

5. **Add `POST /api/notifications/mark-read`** — Marks notifications as read. (30 min)

6. **Last-Event-ID replay** — On reconnect, the client sends `Last-Event-ID`. The backend must query the DB for events after that ID and re-emit them before resuming the live stream. Without this, events missed during Railway's forced reconnects (every 15 minutes) are lost. (2 hours)

7. **Multi-worker connection tracking** — The current per-process `_active_connections` dict does not work correctly with 2 workers. A user's connection on Worker 1 is invisible to Worker 2. This means if a load balancer routes the notification POST to Worker 2, it cannot check whether Worker 1 has an open SSE for that user. For correct behavior, connection tracking needs Redis (or removal of the in-process approach). (1 hour)

**Frontend changes required:**

1. `useNotificationStream` hook with token-in-URL auth (2 hours)
2. EventSource reconnect handling, including `Last-Event-ID` header on reconnect (1 hour)
3. Handle Railway's 15-minute forced close without user-visible disruption (30 min)
4. Notification bell, unread count, history panel — same as polling (3–4 hours)

**Total: 3–4 days. Requires a DB migration.**

### Maintenance burden

High relative to polling. Persistent connections have failure modes that stateless requests do not: stale connections, half-open connections, connection tracking drift across workers, Redis unavailability silently dropping all live notifications if the pub/sub layer is bypassed. The Railway reconnect cycle (forced every 15 minutes) must be tested explicitly. The `Last-Event-ID` replay path must be tested explicitly. Each of these is an additional surface for bugs that manifests only under specific timing conditions.

### Infrastructure complexity

**Redis is on the critical path for SSE delivery.** If Redis is unavailable, `publish_notification` returns `False` silently, and the SSE stream delivers only keepalive pings. Notifications are lost. With polling + DB, Redis unavailability has zero impact on notification delivery.

The in-process connection counter (`_active_connections`) is architecturally incompatible with multiple workers without a shared store. The 2-worker deployment is the current configuration.

### Reliability on Railway

**Poor without mitigation; acceptable with full implementation.**

Railway kills connections at 15 minutes. The current SSE stream does not implement `Last-Event-ID` replay. Without it, any document that is opened in the 15-second reconnect window is never delivered to the owner's browser.

The application-level idle timeout (300 seconds) also closes connections when no messages arrive for 5 minutes. In a typical working day, a consultant who shares one proposal in the morning may have no document opens for hours — their SSE connection will be closed by the idle timeout, and the keepalive ping restarts the 5-minute clock but doesn't prevent the close.

With full Last-Event-ID replay implementation, missed events are delivered on reconnect. But the delivery is then functionally equivalent to polling: the client reconnects, sends its last-seen ID, and the server queries the DB for events since then. This is polling, with extra protocol complexity layered on top.

### User-perceived responsiveness

**Sub-second latency** when the SSE connection is healthy. This is the genuine advantage of SSE. However, with Railway's 15-minute forced reconnect, there is a recurring ~5–15 second gap every 15 minutes where live push is unavailable. During that gap, behavior degrades to the equivalent of polling at 15-second intervals.

### Long-term scalability

SSE holds one open async generator per connected user per worker. At 100 simultaneous users, this is 100 open connections across 2 workers. At 1,000 users, this is 1,000 connections — manageable for async uvicorn, but each connection holds memory and an event loop task. The Redis pub/sub fan-out is O(subscribers) per message — at scale, this becomes an argument for a more sophisticated message bus.

At the current user count, SSE scales fine. The architectural debt of the in-process connection counter and the lack of persistence is the near-term risk, not the connection count itself.

---

## Head-to-Head Comparison

| Dimension | Polling | SSE |
|---|---|---|
| Engineering effort to meet ALL requirements | ~1 day | 3–4 days |
| DB migration required | No | Yes (notifications table) |
| Maintenance burden | Low — stateless requests | High — persistent connections, reconnect logic, Railway timeout handling |
| Infrastructure complexity | None — HTTP only | Redis on critical path; connection counter not multi-worker safe |
| Reliability on Railway | Excellent — 15-min limit irrelevant | Poor without Last-Event-ID replay; Good after full implementation |
| User-perceived latency | 6–12 seconds average | Sub-second (with 15-min gap every 15 minutes) |
| Notification persistence | From DB (access_events, zero new schema) | Requires new DB table |
| Unread counts on page load | Trivially from DB query | Requires new DB table + endpoint |
| Notification history | From existing access_events query | Requires new DB table + endpoint |
| Behavior if Redis is down | Unaffected | Notifications silently dropped |
| Auth blocker status | Not applicable | Currently blocked — EventSource can't send headers |
| Works correctly with 2 workers | Yes — stateless | No — connection counter is per-process |
| Rollback risk | Low — remove a `setInterval` | High — DB migration must be reversed |

---

## Decision: Polling

**Recommendation: Option A — Polling at 12-second intervals.**

### Rationale

The requirements as stated (persist notifications, unread counts, notification history) require a database layer regardless of transport. Once that database layer exists, SSE becomes "polling from a DB, with a live push channel layered on top." The push channel provides sub-second latency instead of 6–12 second latency.

For SecureDoc's use case — a consultant learning that a prospect opened their proposal — 6–12 second latency is not a meaningful difference. The user's response to the notification (picking up the phone, sending a follow-up email) takes minutes. The 6-second window does not change behavior.

Against this marginal UX benefit, SSE requires:
- A DB migration
- 3–4 days of implementation
- Ongoing maintenance of persistent connection logic
- A reliability gap on Railway that requires Last-Event-ID replay to close
- A correctness fix for the multi-worker connection counter

Polling achieves all five stated requirements with no DB migration, ~1 day of implementation, and zero new failure modes.

The existing SSE infrastructure (`notifications.py`, `notification_service.py`) remains in place and continues to work for the `link.viewed` webhook dispatch path, which is already implemented and tested. Nothing is removed. If SSE is desired in a future sprint with a different infrastructure (dedicated async service, no Railway connection limits), the foundation is present.

---

## Implementation Plan — Polling-Based Notifications

### Backend change (1 hour, no migration)

**File:** `backend/app/routers/analytics.py`

Add `since` query parameter to `GET /api/analytics/events`:

```python
since: Optional[str] = Query(None)  # ISO 8601 timestamp
```

In the query builder, after the `link_ids` check:

```python
if since:
    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        query = query.where(AccessEvent.created_at > since_dt)
    except ValueError:
        pass  # invalid since param — ignore, return all
```

This uses the existing `ix_access_events_link_id_created` composite index — no new index needed.

No migration. No new table. No schema change. Non-breaking addition (existing callers without `since` continue to work).

### Frontend additions (3–4 hours)

**New file: `src/hooks/useNotificationPoller.js`**

```javascript
function useNotificationPoller(onNewEvents, intervalMs = 12000) {
  const sinceRef = useRef(new Date().toISOString()); // start from now

  useEffect(() => {
    const tick = async () => {
      try {
        const data = await window.SecureDocAPI.getEvents({
          event_type: 'opened',
          since: sinceRef.current,
          limit: 20,
        });
        const events = data?.events ?? [];
        if (events.length > 0) {
          // advance cursor to the newest event seen
          sinceRef.current = events[0].created_at;
          onNewEvents(events);
        }
      } catch { /* silent fail — retry on next tick */ }
    };

    const id = setInterval(tick, intervalMs);
    return () => clearInterval(id);
  }, []);
}
```

Key design decisions:
- `sinceRef` starts at "now" (page load) — users do not receive a backlog of old opens as notifications
- `sinceRef` is a ref, not state — interval callback always reads the latest value without re-registering the interval
- Silent error handling — a failed poll is retried 12 seconds later; no user-visible error for transient failures
- Limit 20 — caps the response size; in 12 seconds, more than 20 new opens would be unusual at current scale

**AppShell additions:**

```javascript
const [notifications, setNotifications] = useState([]);
const [unreadCount, setUnreadCount] = useState(0);

useNotificationPoller((events) => {
  const opens = events.filter(e => e.event_type === 'opened');
  if (opens.length === 0) return;

  // Toast for each new open (max 3 toasts if multiple arrive together)
  opens.slice(0, 3).forEach(e => {
    const docName = e.document_filename || 'A document';
    const viewer = e.viewer_email ? ` by ${e.viewer_email}` : '';
    toast(`"${docName}" was just opened${viewer}`, 'info');
  });
  if (opens.length > 3) {
    toast(`${opens.length} documents were opened`, 'info');
  }

  setNotifications(prev => [...opens, ...prev].slice(0, 100));
  setUnreadCount(prev => prev + opens.length);
});
```

**Notification center (sidebar bell icon + panel):**
- Bell icon in sidebar with unread badge (red dot or number ≤ 99)
- Click opens a panel listing recent opens: timestamp, document name, viewer email
- "Mark all read" button sets `unreadCount` to 0
- Panel shows last 100 notifications in session; refreshes on page load from the events endpoint (fetch last 24h of `opened` events on mount to populate history)

### api.js addition (30 minutes)

`getEvents` already exists at a different path. Add or extend it to accept `event_type` and `since` params:

```javascript
async getEvents({ document_id, event_type, since, limit = 50 } = {}) {
  const params = new URLSearchParams();
  if (document_id) params.set('document_id', document_id);
  if (event_type) params.set('event_type', event_type);
  if (since) params.set('since', since);
  if (limit) params.set('limit', limit);
  const r = await fetch(`${API_BASE}/api/analytics/events?${params}`, {
    headers: { ...authHeaders() },
  });
  if (r.status === 401) { _clearAndReload(); return; }
  if (!r.ok) throw await r.json();
  return r.json();
}
```

### Deliverables

| Phase | Deliverable | Effort |
|---|---|---|
| 1 | `since` param on `GET /api/analytics/events` | 1 hour |
| 2 | `useNotificationPoller` hook | 1 hour |
| 3 | AppShell integration — toast on new opens | 1 hour |
| 4 | Notification bell + unread count in sidebar | 1 hour |
| 5 | Notification history panel | 1–2 hours |
| 6 | Tests — hook, toast firing, unread count | 1 hour |

**Total: ~1 day. No DB migration. No Redis dependency. No new infrastructure.**

---

## What Polling Does Not Provide

| Feature | Available with polling? | Mitigation |
|---|---|---|
| Sub-second latency | No — 6–12s average | Acceptable for the use case |
| Push while tab is in background | No | Service Worker / Web Push is a future feature requiring separate infrastructure |
| Cross-device sync of read state | No — unread count is localStorage | Acceptable for solo professional use; DB-backed read state is a future enhancement |

---

## Future Upgrade Path

If SSE or WebSocket is needed in a future sprint (e.g., after migrating off Railway, or when real-time collaborative features are added), the transition is straightforward:

1. The `access_events` table used by polling is the same source of truth SSE replay would query
2. The `notifications.py` SSE stream is already in place
3. The frontend hook interface (`onNewEvents(events)`) can be swapped from a polling implementation to an SSE implementation without changing the AppShell integration
4. The only required change is adding the `since` param to the SSE endpoint's `Last-Event-ID` replay logic — which is exactly the same DB query as the polling endpoint

Polling is not a dead end. It is the right architecture for now, and it leaves a clean upgrade path.
