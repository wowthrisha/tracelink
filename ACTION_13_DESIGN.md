# Action 13 Design: Webhooks

**Status:** IN PROGRESS  
**Risk:** P2 — No integration surface for CRM / Salesforce / Zapier pipelines  
**Effort:** 4 hours

## Problem

SecureDoc has no programmatic event notification. Enterprise customers need to react to document events (prospect opened doc, viewer finished reading) in real-time from their CRM, sales tools, or custom automation.

## Solution

Outbound webhooks: user-registered HTTPS endpoints that receive HMAC-signed POST payloads when key events occur. Delivery is async via Celery with 4-level exponential backoff retry.

## Supported Events

| Event | Trigger point |
|-------|--------------|
| `document.processed` | After pipeline completes (success or error) |
| `link.viewed` | After viewer successfully validates a share link |
| `analytics.completed` | After viewer logs the `completed` event |

## Schema

```sql
-- Migration 014

CREATE TABLE webhook_endpoints (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  url VARCHAR(2048) NOT NULL,
  secret VARCHAR(64) NOT NULL,       -- returned only at creation, never again
  description VARCHAR(255),
  events TEXT NOT NULL,              -- JSON array of event names
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE webhook_deliveries (
  id UUID PRIMARY KEY,
  webhook_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  event_type VARCHAR(64) NOT NULL,
  payload_json TEXT NOT NULL,        -- full JSON payload delivered to endpoint
  status VARCHAR(16) NOT NULL DEFAULT 'pending',  -- pending | success | failed | skipped
  attempts INT NOT NULL DEFAULT 0,
  response_status INT,               -- last HTTP response code
  response_body VARCHAR(500),        -- first 500 chars of last response body
  last_attempt_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/webhooks | Create endpoint; secret returned once only |
| GET | /api/webhooks | List endpoints (no secret) |
| GET | /api/webhooks/{id} | Get endpoint (no secret) |
| PATCH | /api/webhooks/{id} | Update url/description/events/is_active |
| DELETE | /api/webhooks/{id} | Delete + cascade deliveries |
| GET | /api/webhooks/{id}/deliveries | Delivery history (last 50) |
| POST | /api/webhooks/{id}/test | Send a test ping |

## Payload Format

```json
{
  "id": "<delivery_uuid>",
  "event": "document.processed",
  "created_at": "2026-06-07T12:00:00Z",
  "data": {
    "document_id": "...",
    "filename": "report.pdf",
    "status": "ready",
    "page_count": 12
  }
}
```

## HMAC Signing

```
X-SecureDoc-Signature: sha256=<hex(HMAC-SHA256(secret, body_bytes))>
X-SecureDoc-Event: document.processed
X-SecureDoc-Delivery: <delivery_uuid>
Content-Type: application/json
```

Receivers verify: `hmac.compare_digest(expected_sig, header_sig)`

## Delivery & Retry

- Timeout: 10s per attempt
- Retry on: 5xx, 429, connection error
- No retry on: 4xx (except 429) — indicates bad endpoint config
- Retry schedule: 1m → 5m → 30m → 3h (4 retries total)
- After 4 retries: `status = "failed"`, no further attempts
- Delivery record persisted regardless of outcome

## Security

- Secret: `secrets.token_hex(32)` (64-char hex) — never returned after creation
- Minimum secret length enforced at generation (not user-provided)
- Webhook data never includes `storage_key`, `originals/`, `password_hash`
- IP included in payloads only as SHA-256 hash (consistent with event model)

## Files Changed

| File | Change |
|------|--------|
| `app/models/webhook.py` | `WebhookEndpoint`, `WebhookDelivery` models + `WEBHOOK_EVENTS` |
| `alembic/versions/014_add_webhooks.py` | DB migration |
| `app/services/webhook_service.py` | `dispatch_webhook_event()` fan-out function |
| `app/routers/webhooks.py` | Full CRUD + delivery history + test endpoint |
| `app/workers/webhook_tasks.py` | `deliver_webhook` Celery task with HMAC + retry |
| `app/main.py` | Include webhooks router |
| `app/workers/tasks.py` | Trigger `document.processed` after pipeline |
| `app/routers/analytics.py` | Trigger `analytics.completed` after log |
| `app/routers/viewer.py` | Trigger `link.viewed` after validate |
| `tests/integration/test_enterprise_product.py` | `TestWebhooks` class |
