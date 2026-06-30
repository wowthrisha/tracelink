# Viewer Open Notification Plan
Sprint: 4.6 — Workstream 2
Date: 2026-06-22
Status: DESIGN ONLY — Do not implement without sprint approval

---

## Problem Statement

When a viewer opens a shared document, the document owner receives no notification. A consultant who shares a proposal before a meeting cannot know in real-time whether the prospect opened it. DocSend's #1 value proposition — "know the moment your document is opened" — is not met.

This plan covers the full event delivery chain from viewer validation to owner notification.

---

## Current State Assessment

### Backend — link.viewed dispatch

**Status: ALREADY IMPLEMENTED.**

`viewer_session_service.py:build_validate_response` (lines 116–133) already dispatches both channels when a viewer validates a link:

```python
_link_viewed_data = {
    "document_id": str(doc.id),
    "filename": doc.filename,
    "link_id": str(link.id),
    "link_label": link.label,
    "session_id_prefix": session_id[:8] if session_id else None,
}
try:
    from app.services.webhook_service import dispatch_webhook_event as _dispatch_wh
    await _dispatch_wh(db, user_id=str(doc.user_id), event_type="link.viewed", data=_link_viewed_data)
except Exception as _wh_exc:
    logger.warning("link.viewed webhook trigger failed: %s", _wh_exc)

try:
    from app.services.notification_service import publish_notification as _pub_notif
    await _pub_notif(str(doc.user_id), "link.viewed", _link_viewed_data)
except Exception as _notif_exc:
    logger.debug("link.viewed SSE notification failed: %s", _notif_exc)
```

Backend dispatch requires zero additional work. Both webhook delivery and SSE publish are already fire-and-forget with independent try/except guards.

### Backend — SSE stream endpoint

**Status: AUTH BLOCKER.**

`GET /api/notifications/stream` uses `get_current_user` which requires an `Authorization: Bearer <token>` header. The browser's native `EventSource` API cannot send custom headers — it sends only the request URL with cookies.

This is the only gap between "event dispatched" and "owner sees toast."

### Frontend — SSE consumer

**Status: NOT IMPLEMENTED.**

No `EventSource`, no `useNotificationStream` hook, no toast wiring exists in AppShell or any other component.

---

## Architecture

```
Viewer clicks link
       │
       ▼
POST /api/viewer/validate
       │
       ▼
build_validate_response()
  ├─ log_event("opened") ──────────────────► PostgreSQL / analytics
  ├─ dispatch_webhook_event("link.viewed") ► Celery → external webhooks
  └─ publish_notification("link.viewed") ──► Redis pub/sub
                                               channel: securedoc:notifications:user:{owner_id}
                                                       │
                                                       ▼
                                               GET /api/notifications/stream
                                               (SSE — owner's browser)
                                                       │
                                                       ▼
                                               AppShell useNotificationStream hook
                                                       │
                                                       ▼
                                               toast("📄 Your document was just opened")
```

---

## The Auth Blocker — Three Options

The only unresolved design question is how to authenticate the SSE connection. Three approaches are viable:

### Option 1 — Query Parameter Token (Recommended)

**How it works:** Add support for `?token=<jwt>` on the SSE endpoint. The JWT is the same access token already in localStorage. The endpoint validates it via `get_current_user_from_query_token()`, a new function that mirrors `get_current_user` but reads from query params.

**Backend change:**
```python
# notifications.py
@router.get("/stream")
async def stream_notifications(
    request: Request,
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_optional),
):
    user = current_user or await get_current_user_from_token_string(db, token)
    if not user:
        raise HTTPException(401)
    ...
```

**Frontend:**
```javascript
const token = localStorage.getItem('securedoc_token')
const es = new EventSource(`/api/notifications/stream?token=${encodeURIComponent(token)}`)
```

**Security consideration:** Tokens in query params appear in server access logs. Mitigations: (a) short-lived tokens only, (b) log scrubbing, (c) use HTTPS (already required). This is the pattern used by YouTube Live, GitHub SSE APIs, and most browser-native SSE implementations.

**Effort:** 1.5 hours backend (new query param handler + token extraction). 2 hours frontend (hook + toast). Total: ~3.5 hours.

---

### Option 2 — Short-Lived Token Exchange

**How it works:** Add `POST /api/notifications/token` — the authenticated client exchanges its JWT for a short-lived (30-second TTL) SSE-specific token stored in Redis. The SSE endpoint validates that token, deletes it after one use.

**Backend change:** New endpoint + Redis key insert (POST) + Redis key lookup + delete (GET /stream).

**Security consideration:** Significantly more secure than option 1 — the SSE token is single-use, short-lived, and not the main JWT. However, requires more moving parts: a new endpoint, Redis read/write on connection, and a token-rotation mechanism if the SSE connection drops and reconnects.

**Effort:** 3–4 hours backend. 2.5 hours frontend (includes token exchange on connect + reconnect logic). Total: ~6 hours.

---

### Option 3 — fetch-event-source Polyfill

**How it works:** Replace native `EventSource` with `@microsoft/fetch-event-source`, which uses `fetch()` under the hood and therefore supports custom headers. No backend changes required.

**Frontend change:** Add npm package (or load from CDN via `<script>` tag since this is a UMD app). Replace `new EventSource(url)` with `fetchEventSource(url, { headers: { Authorization: 'Bearer ...' } })`.

**Concern for this project:** The frontend is a single-file UMD app (`SecureDoc.html`) that loads React from a CDN without a build step for the HTML layer. `api.js` and `src/` are bundled by esbuild. Adding `@microsoft/fetch-event-source` is viable if loaded via CDN URL or bundled into the esbuild output. This adds a third-party dependency to the auth-critical notification path.

**Effort:** 1.5 hours frontend. 0 hours backend. Total: ~1.5 hours — but introduces a CDN dependency risk.

---

### Recommendation

**Option 1 (query parameter token)** is the right choice for this product at this stage:
- Lowest total effort (3.5 hours)
- No new dependencies
- Pattern is industry-standard for SSE
- The main JWT already has a TTL — if it expires, the EventSource will fail and reconnect with a fresh token
- HTTPS is already required (all viewer links enforce it)

---

## Event Flow — Detailed

### Connection lifecycle

1. AppShell mounts → `useNotificationStream` hook fires
2. Hook reads `token` from localStorage
3. Hook opens `new EventSource('/api/notifications/stream?token=...')`
4. SSE endpoint validates token → starts streaming
5. On each SSE message: hook dispatches to a callback registered by AppShell
6. AppShell callback: calls `toast(...)` with the notification content

### Reconnection

`EventSource` reconnects automatically on disconnect. The hook should:
- On `onerror`: log to console (not a user-visible error)
- If token expires (401 response): close the connection. Do not reconnect until the user re-authenticates. Show no error to the user — missing a notification is not a blocking failure.

### Message format (from `publish_notification`)

The SSE endpoint emits:
```
data: {"type": "link.viewed", "data": {"document_id": "...", "filename": "Proposal.pdf", "link_id": "...", "link_label": "Quick Share", "session_id_prefix": "a1b2c3d4"}}
```

The frontend hook parses `event.data`, reads `type`, and routes to the appropriate toast.

### Toast content

```
📄 "Proposal.pdf" was just opened
```

- Uses `doc.filename` from the SSE payload
- Toast duration: 6 seconds (longer than default — this is a meaningful event)
- Toast type: `info` (not `success` — opening is neutral, not an owner action)
- Toast is non-blocking — does not steal focus

---

## Frontend Hook Design

**File:** `frontend/src/hooks/useNotificationStream.js`

**Signature:**
```javascript
function useNotificationStream(token, onNotification) {
  useEffect(() => {
    if (!token) return;
    const es = new EventSource(`/api/notifications/stream?token=${encodeURIComponent(token)}`);
    es.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        onNotification(msg);
      } catch { /* malformed message — ignore */ }
    };
    es.onerror = () => {
      // EventSource reconnects automatically — no action needed
    };
    return () => es.close();
  }, [token]);
}
```

**In AppShell:**
```javascript
useNotificationStream(authToken, (msg) => {
  if (msg.type === 'link.viewed') {
    const filename = msg.data?.filename || 'A document';
    toast(`📄 "${filename}" was just opened`, 'info');
  }
});
```

---

## Failure Modes

| Failure | Effect | Recovery |
|---|---|---|
| Redis is unavailable | `publish_notification` raises exception; caught by try/except in service; backend continues normally | Owner misses notification; document view still logged in analytics |
| SSE connection drops | EventSource auto-reconnects with exponential backoff (browser native) | Notifications resume on reconnect |
| Token expired during SSE session | Server closes SSE connection (401) | EventSource retries; retry fails; connection stays closed until re-auth |
| Owner's browser doesn't support EventSource | No hook fires | No notification shown; no error; analytics still captures views |
| Multiple browser tabs open | Each tab has its own EventSource connection. Server per-user connection limit is 5. Two tabs = 2 connections = within limit | No issue for normal use |
| Viewer opens document repeatedly in one session | Validation endpoint fires on each validate call. Existing session upsert (`existing_session_id` logic) may deduplicate — depends on session handling | Acceptable: multiple toasts for multiple opens is not harmful |
| Notification contains no filename | Toast falls back to: `📄 A document was just opened` | Acceptable degradation |

---

## Scalability Assessment

### Current architecture (single backend process)

The SSE implementation uses an in-process connection counter (`max_concurrent_sessions_per_link`). Redis pub/sub is already in use for the notification channel. At the scale this product operates (single-tenant SaaS, expected hundreds of concurrent owners), this approach is sound.

### Limits

| Dimension | Current limit | Notes |
|---|---|---|
| SSE connections per user | 5 (in-process counter) | Prevents a single user from holding 100 connections open |
| Redis pub/sub channels | Per-user channel: `securedoc:notifications:user:{user_id}` | One channel per owner; scales with user count |
| Backend SSE workers | Tied to FastAPI worker process | Each open SSE connection holds one async generator alive |

### If user count grows 10x

The SSE connection-per-worker constraint becomes the bottleneck. Standard mitigation: move SSE delivery to a dedicated worker pool (separate FastAPI app or Starlette app) that only handles SSE streaming. Redis pub/sub fan-out is unchanged. This is a future concern — not a current risk at expected user volume.

### What does NOT scale poorly

- Redis pub/sub delivery: O(1) per message regardless of channel count
- Webhook delivery: Celery workers are already isolated; `link.viewed` webhooks are already structured
- Toast rendering: purely client-side; zero backend load

---

## Out of Scope for This Plan

- Email notification when SSE is not connected (owner's browser is closed): this requires a separate email delivery flow, a notification preference screen, and opt-in settings. Not part of this workstream.
- Push notifications (mobile browser): requires a service worker and VAPID key management. Not part of this workstream.
- Feedback notification (`feedback.submitted`): the SSE channel and hook will work for any event type once wired. Feedback notifications are a natural follow-on extension — same hook, new event type.
- Per-document notification settings (mute a specific document): requires a preferences model. Not part of this workstream.

---

## Implementation Sequence

1. Backend: Add `?token=` query param support to `GET /api/notifications/stream` (Option 1)
2. Frontend: Write `useNotificationStream` hook in `frontend/src/hooks/`
3. Frontend: Wire hook in AppShell with `link.viewed` toast handler
4. Test: Open viewer link in one browser session → confirm toast in owner's browser session

**Total estimated effort: 3.5–4 hours.** Backend 1.5h. Frontend 2h. Testing 0.5h.
