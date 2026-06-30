# Network Report — Sprint 5.5 Production Audit

**Date:** 2026-06-28  
**Sprint:** 5.5  
**Source:** Playwright route intercept log (`audit_artifacts/network/network_log.json`)

---

## Summary

All intercepted API requests returned HTTP 200 in the mocked test environment. No failed requests, no unexpected duplicate calls, no unauthorized requests were observed.

---

## Endpoint Inventory (Discovered)

| Endpoint | Method | Screen | Notes |
|----------|--------|--------|-------|
| `GET /api/auth/me` | GET | All screens | Auth check on load |
| `GET /api/documents` | GET | Upload, Access Control | Document list |
| `GET /api/documents/{id}` | GET | Access Control | Single doc metadata |
| `GET /api/documents/{id}/retention` | GET | Storage | Retention policy |
| `GET /api/documents/{id}/feedback` | GET | Access Control — Feedback | Feedback items |
| `GET /api/documents/{id}/annotations` | GET | Access Control — Annotations | Annotations |
| `POST /api/documents/upload` | POST | Upload | File upload |
| `DELETE /api/documents/{id}` | DELETE | Upload | Document deletion |
| `GET /api/links?document_id=` | GET | Access Control — Links | Link list |
| `POST /api/links` | POST | Access Control — Create | Create link |
| `PATCH /api/links/{id}` | PATCH | Access Control — Edit Modal | Update link |
| `DELETE /api/links/{id}` | DELETE | Access Control | Revoke link |
| `DELETE /api/links/{id}/hard` | DELETE | Access Control | Hard delete link |
| `GET /api/analytics` | GET | Analytics | Analytics summary + chart data |
| `GET /api/storage/dashboard` | GET | Storage | Storage usage |
| `GET /api/storage/forecast` | GET | Storage | Storage forecast |
| `GET /api/api-keys` | GET | API Keys | List keys |
| `POST /api/api-keys` | POST | API Keys | Create key |
| `DELETE /api/api-keys/{id}` | DELETE | API Keys | Revoke key |
| `GET /api/webhooks` | GET | Webhooks | Webhook list |
| `POST /api/webhooks` | POST | Webhooks | Register webhook |
| `POST /api/webhooks/{id}/test` | POST | Webhooks | Test delivery |
| `PATCH /api/webhooks/{id}` | PATCH | Webhooks | Update webhook |
| `GET /api/admin/audit-log` | GET | Audit Log | Event log |
| `GET /api/orgs` | GET | Organizations | Org list |
| `POST /api/orgs` | POST | Organizations | Create org |
| `DELETE /api/orgs/{id}` | DELETE | Organizations | Delete org |
| `GET /api/billing` | GET | Billing | Plan info |
| `GET /api/notifications` or `/api/activity` | GET | Notifications | Activity feed |

---

## Network Issues

### NET-001 — Notifications Endpoint URL Unclear
The NotificationsScreen calls an activity endpoint but the exact URL was not captured in the intercept log. The screen showed "Loading..." suggesting the endpoint didn't return within the capture window or uses a URL pattern not covered by `**/api/**` intercept.

**Action:** Verify `NotificationsScreen.jsx` and trace the exact API call with `console.log` or `curl`.

### NET-002 — Analytics Summary vs Chart Data Mismatch
The `/api/analytics` endpoint appears to return data in a format that populates the chart correctly but leaves the summary metric cards empty (all showing 0). This suggests either:
- The summary fields have different names than the component expects
- The analytics endpoint returns a different schema in the test environment vs production

**Action:** Inspect `AnalyticsScreen.jsx` to verify the field names consumed from the analytics API response.

---

## Performance Observations

| Metric | Observation |
|--------|-------------|
| API calls per screen transition | 1–3 calls per screen (appropriate) |
| Duplicate calls observed | None |
| Redundant polling | Notifications screen refreshes every 30s (by design) |
| Request batching | Not observed — each resource loaded individually |
| Auth header on every call | ✅ Confirmed (`Authorization: Bearer ...`) |
| Token refresh mechanism | Not observed in audit (JWT is long-lived in test) |

---

## API Contract Notes

The following API contracts are well-defined and verified against live source code:

| Contract | Verified |
|----------|---------|
| `POST /api/links` → returns token + share_url | ✅ |
| `PATCH /api/links/{id}` → returns updated LinkSummary | ✅ |
| `DELETE /api/links/{id}/hard` → requires revoked_at ≠ null | ✅ |
| `GET /api/links?document_id=` → returns `{links: [...]}` | ✅ |
| All PATCH fields use `model_fields_set` (null-clears work) | ✅ |
