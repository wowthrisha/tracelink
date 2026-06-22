# Hidden Feature Reality Check — Sprint 4.7
Date: 2026-06-22
Purpose: Verify backend completeness before writing any frontend code.
Method: Direct source-code trace for each feature area.

---

## 1. API Keys

### Endpoints (all registered in main.py:232)
| Method | Path | Auth | Status |
|---|---|---|---|
| POST | `/api/api-keys` | JWT ✅ | COMPLETE |
| GET | `/api/api-keys` | JWT ✅ | COMPLETE |
| GET | `/api/api-keys/{id}` | JWT ✅ | COMPLETE |
| PATCH | `/api/api-keys/{id}` | JWT ✅ | COMPLETE |
| DELETE | `/api/api-keys/{id}` | 204 No Content | COMPLETE |

### Model: `api_keys` table
Fields: `id`, `user_id`, `name`, `key_prefix`, `key_hash`, `scopes`, `is_active`, `last_used_at`, `expires_at`, `created_at`

### Response shape
```json
{
  "id": "uuid",
  "name": "My Key",
  "key_prefix": "sd_abc12345",
  "scopes": ["documents:read"],
  "is_active": true,
  "last_used_at": "2026-06-22T10:00:00Z",
  "expires_at": null,
  "created_at": "2026-06-01T00:00:00Z",
  "key": "sd_<full_key>"   // only on POST response
}
```

### Available scopes
`documents:read`, `documents:write`, `links:read`, `links:write`, `analytics:read`, `webhooks:read`, `webhooks:write`

### Auth mechanism
`require_scope()` dependency: JWT users bypass scope check (owner-level access). API key callers must have the matching scope. Frontend users always use JWT → all endpoints accessible.

### Audit logging
`api_key.created`, `api_key.revoked`, `api_key.deleted` written to `admin_audit_log` on every mutation.

### Verdict: **READY** — Implement API Keys UI.

---

## 2. Webhooks

### Endpoints (all registered in main.py:231)
| Method | Path | Auth | Status |
|---|---|---|---|
| POST | `/api/webhooks` | JWT ✅ (scope bypassed) | COMPLETE |
| GET | `/api/webhooks` | JWT ✅ | COMPLETE |
| GET | `/api/webhooks/{id}` | JWT ✅ | COMPLETE |
| PATCH | `/api/webhooks/{id}` | JWT ✅ | COMPLETE |
| DELETE | `/api/webhooks/{id}` | 204 | COMPLETE |
| GET | `/api/webhooks/{id}/deliveries` | JWT ✅ | COMPLETE |
| POST | `/api/webhooks/{id}/test` | JWT ✅ | COMPLETE |

### Model: `webhook_endpoints` + `webhook_deliveries` tables
Fields: `id`, `user_id`, `url`, `secret`, `description`, `events_json`, `is_active`, `created_at`, `updated_at`
Delivery fields: `event_type`, `status`, `attempts`, `response_status`, `last_attempt_at`

### Subscribable events
`document.processed`, `link.viewed`, `analytics.completed`

### Security
- SSRF protection via `validate_ssrf_url()` on all URL saves
- Secret returned only once on POST (HMAC signing key for webhook payloads)
- 20 webhook cap per user
- Celery delivers payloads asynchronously (already operational)

### Verdict: **READY** — Implement Webhooks UI.

---

## 3. Audit Log

### Endpoint (registered in main.py:234)
| Method | Path | Auth | Status |
|---|---|---|---|
| GET | `/api/admin/audit-log` | JWT ✅ | COMPLETE |

Query params: `org_id` (optional), `limit` (1–500), `offset`

### Behavior
- Without `org_id`: returns all audit events where the caller is the actor (API key events, org events, document/link mutations)
- With `org_id`: requires admin/owner role in that org; returns org-scoped events

### Model: `admin_audit_log` table
Event types: `org.created`, `org.updated`, `org.deleted`, `member.added`, `member.role_changed`, `member.removed`, `api_key.created`, `api_key.revoked`, `api_key.deleted`, `document.deleted`, `link.revoked`

### Verdict: **READY** — Implement Audit Log UI (read-only, no backend changes).

---

## 4. Organizations

### Endpoints (registered in main.py:233)
| Method | Path | Auth | Status |
|---|---|---|---|
| POST | `/api/orgs` | JWT ✅ | COMPLETE |
| GET | `/api/orgs` | JWT ✅ | COMPLETE |
| GET | `/api/orgs/{id}` | JWT ✅ | COMPLETE |
| PATCH | `/api/orgs/{id}` | owner role | COMPLETE |
| DELETE | `/api/orgs/{id}` | owner role | COMPLETE |
| GET | `/api/orgs/{id}/members` | viewer role | COMPLETE |
| POST | `/api/orgs/{id}/members` | admin role | **BLOCKED** |
| PATCH | `/api/orgs/{id}/members/{uid}` | admin role | COMPLETE |
| DELETE | `/api/orgs/{id}/members/{uid}` | admin role | COMPLETE |
| GET | `/api/orgs/{id}/domain/token` | admin role | COMPLEX |
| POST | `/api/orgs/{id}/domain/verify` | admin role | COMPLEX |

### BLOCKED: Member Addition
`POST /api/orgs/{id}/members` requires `body.user_id` = target user's Supabase UUID.
No user lookup endpoint exists. The frontend cannot resolve an email address to a UUID.
**Per user instruction: "If member management still requires Supabase UUIDs: DO NOT expose that flow."**

### What is exposed in frontend
- Create org
- List my orgs
- View org details (member count, slug, role)
- Rename org (owner only)
- Delete org (owner only)
- View member list (shows user_ids, not emails — cosmetic limitation)

### What is hidden
- Add member (UUID required, no lookup)
- Custom domain verification (DNS integration, complex flow)
- SAML domain configuration

### Verdict: **PARTIAL** — Implement list/create/view/rename/delete org. Hide member add and domain flows.

---

## 5. Notifications

### Available backend
- `GET /api/notifications/stream` — SSE only. **Per user instruction: "Do NOT use SSE."**
- No polling endpoint exists natively.

### Strategy: Poll existing analytics events table
`GET /api/analytics/events?limit=20` returns the most recent 20 access events across all user documents, ordered by `created_at DESC`.

Fields available: `event_type`, `viewer_email`, `created_at`, `link_id`, `session_id`, `page_number`

This is sufficient for:
- **Unread count**: events newer than `localStorage['securedoc_notif_last_seen']`
- **Recent document opens**: filter `event_type = 'viewer_session'` or `'page_view'`
- **Mark as read**: update localStorage timestamp to `now()`
- **Recent feedback**: not available without per-doc polling — will show link activity only

### Polling interval
30 seconds. Uses `setInterval` in a React hook, cleared on unmount.

### Verdict: **IMPLEMENTABLE via polling** — Uses `GET /api/analytics/events`. SSE not needed. Feedback activity limited to what access events capture.

---

## Summary Decision Table

| Feature | Backend | Frontend | Proceed? |
|---|---|---|---|
| API Keys | Complete ✅ | None | YES — Phase 1 |
| Webhooks | Complete ✅ | None | YES — Phase 2 |
| Audit Log | Complete ✅ | None | YES — Phase 3 |
| Orgs (create/list/view) | Complete ✅ | None | YES — Phase 4 (partial) |
| Orgs (member add) | BLOCKED ❌ | — | NO — hide |
| Orgs (domain verification) | Complete but complex | — | NO — hide |
| Notifications (polling) | Via analytics events ✅ | None | YES — Phase 5 |
| Notifications (SSE) | Complete ✅ | — | NO — user instruction |
