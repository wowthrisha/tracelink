# Action 19 Design: Real-Time SSE Notifications

**Status:** IN PROGRESS  
**Risk:** P2 — DocSend's "your prospect just opened the doc" push is a key differentiator  
**Effort:** 3 hours

## Problem

Users have no real-time feedback when a share link is viewed. They must manually refresh analytics. DocSend sends a push notification within seconds of a prospect opening a document.

## Solution

Server-Sent Events (SSE) endpoint that streams events to authenticated users. Events are published to Redis when key actions occur (link.viewed, document.processed). The SSE endpoint subscribes to a per-user Redis channel and forwards events to connected clients.

## SSE Channel Pattern

```
securedoc:notifications:user:{user_id}
```

Publishers (viewer.py, tasks.py) push JSON events to this channel. SSE endpoint uses Redis pub/sub to forward to the browser.

## Event Format (SSE)

```
id: <uuid>
event: link.viewed
data: {"document_id":"...","document_filename":"...","link_id":"...","link_label":"...","session_id_prefix":"..."}

id: <uuid>
event: document.processed
data: {"document_id":"...","filename":"...","status":"ready","page_count":5}
```

## SSE Endpoint

`GET /api/notifications/stream`

- Requires authentication (Bearer token or X-API-Key)
- Sends `ping` comment every 15 seconds to keep connection alive
- On client disconnect: unsubscribes from Redis cleanly
- When Redis is unavailable: returns 503 or falls back to ping-only mode

## Publishing

Events are published from two sites:
1. `viewer.py:validate_link` — publishes `link.viewed` after successful session creation
2. `tasks.py:_process_document_async` — publishes `document.processed` after pipeline

## Files Changed

| File | Change |
|------|--------|
| `app/services/notification_service.py` | `publish_notification()` async helper |
| `app/routers/notifications.py` | SSE endpoint |
| `app/main.py` | Include notifications router |
| `app/routers/viewer.py` | Publish `link.viewed` on validate |
| `app/workers/tasks.py` | Publish `document.processed` after pipeline |
