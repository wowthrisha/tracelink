# SecureDoc API Reference

**Version:** 2024-01  
**Base URL:** `https://app.securedoc.io`  
**OpenAPI:** `GET /openapi.json`

## Authentication

### Supabase JWT (user sessions)
```
Authorization: Bearer <supabase_jwt>
```

### API Keys (machine-to-machine)
```
Authorization: Bearer sd_<api_key>
X-API-Key: sd_<api_key>
```

API keys have per-key scopes: `documents:read`, `documents:write`, `links:read`, `links:write`.

## Response Headers

Every response includes:
- `X-Request-ID` — unique request identifier
- `X-Correlation-ID` — caller-supplied correlation ID (or equals X-Request-ID)
- `X-API-Version` — API version (`2024-01`)

## Core Endpoints

### Documents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents/upload` | Upload document (202, async processing) |
| `GET` | `/api/documents/` | List documents |
| `GET` | `/api/documents/{id}` | Get document detail |
| `GET` | `/api/documents/{id}/status` | Get processing status |
| `DELETE` | `/api/documents/{id}` | Delete document |
| `POST` | `/api/documents/{id}/reprocess` | Reprocess document |

**Upload request** (`multipart/form-data`):
```
file: <binary>
filename: optional override
group_id: optional UUID
org_id: optional UUID
parent_document_id: optional UUID (for versioning)
retention_policy: never|30d|90d|1y
```

**Supported file types:** `.pdf`, `.docx`, `.doc`, `.txt`, `.md`, `.log`

### Share Links

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/links/` | Create share link |
| `GET` | `/api/links/` | List links for document |
| `DELETE` | `/api/links/{id}` | Revoke link |
| `PATCH` | `/api/links/{id}` | Update link settings |

**Create link body:**
```json
{
  "document_id": "uuid",
  "label": "Client Review",
  "password": "optional",
  "allowed_emails": ["user@example.com"],
  "allowed_domains": ["example.com"],
  "ip_allowlist": ["192.168.1.0/24", "10.0.0.1"],
  "max_views": 10,
  "max_concurrent_sessions": 2,
  "expires_at": "2025-12-31T23:59:59Z",
  "permissions": {
    "can_download": false,
    "can_print": false,
    "can_copy": false,
    "watermark_enabled": true,
    "can_annotate": true
  }
}
```

### Viewer (DRM)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/viewer/validate` | None | Validate link + create session |
| `GET` | `/api/viewer/page/{token}/{n}` | Session | Get page image |
| `GET` | `/api/viewer/thumb/{token}/{n}` | Session | Get page thumbnail |
| `GET` | `/api/viewer/download/{token}` | Session | Download PDF (if permitted) |
| `GET` | `/api/viewer/annotations/{token}/{n}` | Session | Get page annotations |
| `POST` | `/api/viewer/annotations/{token}` | Session | Create annotation |

**Validate request:**
```json
{
  "token": "link_token",
  "password": "optional",
  "email": "optional",
  "session_id": "optional (to resume)"
}
```

**Validate response:**
```json
{
  "session_id": "32-char-hex",
  "document_id": "uuid",
  "page_count": 42,
  "doc_status": "ready",
  "permissions": { "can_download": false, ... },
  "pages": [{"page_number": 1, "width_px": 1240, "height_px": 1754}],
  "link_id": "uuid",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/analytics/overview` | Aggregate stats |
| `GET` | `/api/analytics/daily` | Daily views time series |
| `GET` | `/api/analytics/geo` | Geo distribution |
| `GET` | `/api/analytics/events` | Paginated event log |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/webhooks/` | Create webhook |
| `GET` | `/api/webhooks/` | List webhooks |
| `DELETE` | `/api/webhooks/{id}` | Delete webhook |
| `GET` | `/api/webhooks/{id}/deliveries` | List deliveries |

**Webhook events:** `link.viewed`, `link.created`, `link.revoked`, `document.ready`, `document.error`

**Webhook payload signature:** HMAC-SHA256, header `X-SecureDoc-Signature: sha256=<hex>`

## Pagination

List endpoints return:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 25,
  "has_next": true
}
```

Query params: `page` (1-based), `per_page` (max 100).

## Error Format

```json
{
  "detail": "Human-readable error message",
  "code": "optional_machine_code"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (validation) |
| 401 | Authentication required |
| 403 | Forbidden (insufficient scope) |
| 404 | Resource not found |
| 409 | Conflict |
| 413 | Payload too large |
| 422 | Unprocessable entity |
| 429 | Rate limited |
| 502 | Upstream dependency failure |
| 503 | Service unavailable (startup/degraded) |

## Rate Limits

- `/api/documents/upload`: 10/minute per user
- `/api/viewer/page/*`: 120/minute per session
- `/api/viewer/validate`: 60/minute per IP
- Most other endpoints: 60/minute per user
