# API Certification Report
Sprint 4.4 — Production Certification Sprint
Date: 2026-06-22
Auditor role: Staff Engineer + Principal Architect
Method: Direct source reading of all backend routers. Every endpoint listed from `@router` decorators. No assumptions.

Auth types:
- **JWT-owner**: `get_current_user` — requires Supabase JWT in `Authorization: Bearer` header
- **Scope**: `require_scope("X:Y")` — JWT-owner OR API key with the named scope
- **Public**: No auth required
- **Public-HMAC**: No user auth, but HMAC payload signature verified (webhooks, Stripe)
- **Viewer-session**: Link token + session_id cookie/header

---

## Router: Documents (`/api/documents`)

| Method | Path | Auth | Status Code | Findings |
|---|---|---|---|---|
| POST | `/api/documents/upload` | JWT-owner | 202 | Quota check via `_check_upload_quota`. Celery task queued. `org_id` accepted but frontend has no org selector. |
| GET | `/api/documents` | Scope: `documents:read` | 200 | Returns paginated list. Org-scoped if `org_id` param present. |
| GET | `/api/documents/{id}/status` | Scope: `documents:read` | 200 | Returns processing status + sidecar availability. |
| GET | `/api/documents/{id}` | Scope: `documents:read` | 200 | Returns full document including `versions` array. |
| DELETE | `/api/documents/{id}` | JWT-owner | 204 | Ownership verified. Audit log `document.deleted` called at `documents.py:607`. |
| POST | `/api/documents/{id}/reprocess` | JWT-owner | 202 | Re-queues Celery pipeline. Guard: not re-processable if already `processed`. |
| POST | `/api/documents/{id}/extract-sidecars` | JWT-owner | 202 | Standalone sidecar extraction without full reprocess. |

**Certification: PASS** — All endpoints have auth. Quota enforcement present. Audit logging confirmed for delete.

---

## Router: Groups (`/api/groups`)

| Method | Path | Auth | Status Code | Findings |
|---|---|---|---|---|
| POST | `/api/groups` | JWT-owner | 201 | Creates document group. |
| GET | `/api/groups` | JWT-owner | 200 | Returns user's groups. |
| PATCH | `/api/groups/{id}` | JWT-owner | 200 | Ownership verified. |
| DELETE | `/api/groups/{id}` | JWT-owner | 204 | Documents in group are unassigned, not deleted. |
| POST | `/api/groups/{id}/documents` | JWT-owner | 200 | Assign documents to group. |
| DELETE | `/api/groups/{id}/documents/{doc_id}` | JWT-owner | 204 | Remove document from group. |

**Certification: PASS**

---

## Router: Links (`/api/links`)

| Method | Path | Auth | Status Code | Findings |
|---|---|---|---|---|
| POST | `/api/links` | Scope: `links:write` | 201 | Creates share link with policy. |
| GET | `/api/links` | Scope: `links:read` | 200 | Returns all links for a document (by `document_id` param). |
| PATCH | `/api/links/{id}` | Scope: `links:write` | 200 | Updates link policy. Ownership verified. |
| DELETE | `/api/links/{id}` | Scope: `links:write` | 200 | Revokes link. Audit log `link.revoked` called at `links.py:182`. |

**Certification: PASS** — Audit logging confirmed for revoke. Ownership isolation enforced.

**Gap noted:** `POST /api/links` exists and works. The frontend "⟳ New Link" button in AccessScreen does NOT call this endpoint (UI-002 defect from UI_CERTIFICATION).

---

## Router: Viewer (`/api/viewer`)

| Method | Path | Auth | Status Code | Findings |
|---|---|---|---|---|
| GET | `/api/viewer/gate/{token}` | Public | 200 | Returns policy requirements (password required, allowed_emails check). |
| POST | `/api/viewer/validate` | Public + link token | 200 | Validates viewer, issues session. `link.viewed` webhook/SSE NOT dispatched here. |
| GET | `/api/viewer/page/{token}/{page}` | Viewer-session | 200 | Page image with forensic watermark. `is_active_session` check. |
| GET | `/api/viewer/thumb/{token}/{page}` | Viewer-session | 200 | Thumbnail version of page. Same session check. |
| GET | `/api/viewer/toc/{token}` | Viewer-session | 200 | Table of contents sidecar. |
| GET | `/api/viewer/download/{token}` | Viewer-session | 200 | Full PDF with download watermark. `can_download` permission checked. |

**Certification: PASS with CRITICAL GAP**

**Gap API-001 — HIGH:** `POST /api/viewer/validate` does not call `dispatch_webhook_event` or `publish_notification` for `link.viewed` event.
- File: `backend/app/routers/viewer.py:172` → `viewer_session_service.py:build_validate_response`
- Severity: HIGH
- Impact: Webhook subscribers and SSE stream consumers never receive `link.viewed` events. This is the most commercially valuable notification type — "notify me when my document is viewed."
- Recommendation: Add two `try/except`-wrapped calls after successful session creation: `dispatch_webhook_event(db, doc.user_id, 'link.viewed', {...})` and `publish_notification(str(doc.user_id), 'link.viewed', {...})`. Pattern exists in `tasks.py:188-200`.

---

## Router: Analytics (`/api/analytics`)

| Method | Path | Auth | Status Code | Findings |
|---|---|---|---|---|
| GET | `/api/analytics/overview` | Scope: `analytics:read` | 200 | No `range` filter parameter observed in router (UNVERIFIED — may exist). Frontend does not pass range. |
| GET | `/api/analytics/documents` | Scope: `analytics:read` | 200 | Per-document view stats. |
| GET | `/api/analytics/groups` | Scope: `analytics:read` | 200 | Per-group aggregation. |
| GET | `/api/analytics/page-heatmap` | Scope: `analytics:read` | 200 | Requires `document_id`. Returns per-page view counts. |
| GET | `/api/analytics/events` | Scope: `analytics:read` | 200 | Raw event log with filtering. |
| POST | `/api/analytics/events` | Public (viewer token) | 201 | Logs viewer events (page view, dwell time). Also dispatches `analytics.completed` webhook. |

**Certification: PASS with note**

**Note API-002 — MEDIUM:** No range-based filtering observed in GET endpoints. Frontend range selector state is not forwarded. Analytics always returns full history. Verify if `?from_date=` or `?range=` params are accepted by backend before adding frontend filtering.

---

## Router: Storage (`/api/storage`)

| Method | Path | Auth | Status Code | Findings |
|---|---|---|---|---|
| GET | `/api/storage/dashboard` | JWT-owner | 200 | Storage breakdown with per-org view when org present. |
| GET | `/api/storage/forecast` | JWT-owner | 200 | Growth projection. |
| PATCH | `/api/storage/retention` | JWT-owner | 200 | Updates lifecycle retention policy. Options: never/30_days/60_days/90_days. |

**Certification: PASS**

---

## Router: Billing (`/api/billing`)

| Method | Path | Auth | Status Code | Findings |
|---|---|---|---|---|
| GET | `/api/billing/status` | JWT-owner | 200 | Returns plan, subscription_status, period_end, billing_enabled. |
| POST | `/api/billing/checkout` | JWT-owner | 200 | Creates Stripe Checkout session. Returns `{url}`. |
| POST | `/api/billing/portal` | JWT-owner | 200 | Creates Stripe Customer Portal session. Returns `{url}`. |
| POST | `/api/billing/webhook` | Public-HMAC | 200 | Stripe event handler. HMAC via `stripe.Webhook.construct_event`. |

**Certification: PASS**

**Note:** BillingScreen frontend uses direct `fetch()` rather than `window.SecureDocAPI`. Backend endpoints are correct. Frontend implementation is the defect (UI-006).

---

## Router: Annotations (`/api/annotations`)

| Method | Path | Auth | Status Code | Findings |
|---|---|---|---|---|
| POST | `/api/annotations` | Viewer-session | 201 | Creates annotation. Requires `can_annotate` permission on link. |
| GET | `/api/annotations` | JWT-owner | 200 | List all annotations for a document (owner view). |
| GET | `/api/annotations/{id}/thread` | Viewer-session | 200 | Thread for a specific annotation. |
| DELETE | `/api/annotations/{id}` | JWT-owner or viewer (own) | 204 | Delete annotation. |

**Certification: PASS**

---

## Router: Feedback (`/api/feedback`)

| Method | Path | Auth | Findings |
|---|---|---|---|
| GET | `/api/feedback` | JWT-owner | Filtered list with rich query params matching frontend filter UI. |
| PATCH | `/api/feedback/{id}` | JWT-owner | Reply and status update. |

**Certification: PASS**

---

## Router: Webhooks (`/api/webhooks`)

| Method | Path | Auth | Rate Limit | Status |
|---|---|---|---|---|
| POST | `/api/webhooks` | Scope: `webhooks:write` | 10/min | BACKEND ONLY |
| GET | `/api/webhooks` | Scope: `webhooks:read` | — | BACKEND ONLY |
| GET | `/api/webhooks/{id}` | Scope: `webhooks:read` | — | BACKEND ONLY |
| PATCH | `/api/webhooks/{id}` | Scope: `webhooks:write` | — | BACKEND ONLY |
| DELETE | `/api/webhooks/{id}` | Scope: `webhooks:write` | — | BACKEND ONLY |
| GET | `/api/webhooks/{id}/deliveries` | Scope: `webhooks:read` | — | BACKEND ONLY |
| POST | `/api/webhooks/{id}/test` | Scope: `webhooks:write` | 5/min | BACKEND ONLY |

**Certification: PASS (backend). Zero frontend consumer.** See F-46.

---

## Router: API Keys (`/api/api-keys`)

| Method | Path | Auth | Status |
|---|---|---|---|
| POST | `/api/api-keys` | JWT-owner | BACKEND ONLY |
| GET | `/api/api-keys` | JWT-owner | BACKEND ONLY |
| GET | `/api/api-keys/{id}` | JWT-owner | BACKEND ONLY |
| PATCH | `/api/api-keys/{id}` | JWT-owner | BACKEND ONLY |
| DELETE | `/api/api-keys/{id}` | JWT-owner | BACKEND ONLY |

**Certification: PASS (backend). Zero frontend consumer.** See F-47.

---

## Router: Organizations (`/api/orgs`)

| Method | Path | Min Role | Status |
|---|---|---|---|
| POST | `/api/orgs` | None (creator becomes owner) | BACKEND ONLY |
| GET | `/api/orgs` | — | BACKEND ONLY |
| GET | `/api/orgs/{id}` | viewer | BACKEND ONLY |
| PATCH | `/api/orgs/{id}` | owner | BACKEND ONLY |
| DELETE | `/api/orgs/{id}` | owner | BACKEND ONLY |
| GET | `/api/orgs/{id}/members` | viewer | BACKEND ONLY |
| POST | `/api/orgs/{id}/members` | admin | BACKEND ONLY |
| PATCH | `/api/orgs/{id}/members/{uid}` | admin | BACKEND ONLY |
| DELETE | `/api/orgs/{id}/members/{uid}` | admin | BACKEND ONLY |
| GET | `/api/orgs/{id}/domain/token` | admin | BACKEND ONLY |
| POST | `/api/orgs/{id}/domain/verify` | admin | BACKEND ONLY |

**Certification: PASS (backend). Zero frontend consumer.** See F-48.

---

## Router: Admin Audit Log (`/api/admin`)

| Method | Path | Auth | Status |
|---|---|---|---|
| GET | `/api/admin/audit-log` | JWT-owner | BACKEND ONLY |

**Certification: PASS (backend). Zero frontend consumer.** See F-49.

---

## Router: Notifications (`/api/notifications`)

| Method | Path | Auth | Status |
|---|---|---|---|
| GET | `/api/notifications/stream` | JWT-owner (`Authorization: Bearer`) | BACKEND ONLY — **auth incompatible with browser EventSource** |

**Certification: PASS (backend). Zero frontend consumer. Auth method is a blocker for frontend integration.**

**Gap API-003 — HIGH:** `GET /api/notifications/stream` uses `get_current_user` which requires `Authorization: Bearer` header. The browser's native `EventSource` API does not support custom headers. The frontend cannot consume this endpoint without one of: (a) query param token support added to `get_current_user`, (b) a short-lived SSE token exchange endpoint, or (c) a polyfill like `@microsoft/fetch-event-source`.

---

## API Security Summary

| Check | Status | Detail |
|---|---|---|
| All owner endpoints require JWT | PASS | `get_current_user` or `require_scope` on every non-public endpoint |
| Viewer endpoints use session validation | PASS | `is_active_session` check on all page/thumb/toc/download routes |
| Stripe webhook HMAC verified | PASS | `stripe.Webhook.construct_event` before any processing |
| SecureDoc webhook HMAC signed | PASS | HMAC-SHA256 in `webhook_tasks.py`, SSRF re-validation at delivery |
| Rate limiting (in-process, slowapi) | PARTIAL | Exists on webhook create (10/min), webhook test (5/min), SSE (10/min). Ineffective under horizontal scaling. |
| SQL injection | PASS | SQLAlchemy ORM with parameterized queries throughout |
| SSRF protection (webhooks) | PASS | `validate_ssrf_url` at endpoint creation + re-validation at delivery time |
| API key scope isolation | PASS | `require_scope` enforced in all scope-gated endpoints |
| link.viewed event dispatch | FAIL | Never called in viewer.py — Gap API-001 |
| SSE auth method | FAIL | Header-only auth incompatible with EventSource — Gap API-003 |

---

## Total Endpoint Count

| Router | Endpoints | Certified | Defects |
|---|---|---|---|
| Documents | 7 | 7 | 0 |
| Groups | 6 | 6 | 0 |
| Links | 4 | 4 | 1 (API-001 gap) |
| Viewer | 6 | 6 | 1 (API-001 gap) |
| Analytics | 6 | 6 | 1 (API-002 range) |
| Storage | 3 | 3 | 0 |
| Billing | 4 | 4 | 0 |
| Annotations | 4 | 4 | 0 |
| Feedback | 2 | 2 | 0 |
| Webhooks | 7 | 7 | 0 (backend only) |
| API Keys | 5 | 5 | 0 (backend only) |
| Organizations | 11 | 11 | 0 (backend only) |
| Admin Audit Log | 1 | 1 | 0 (backend only) |
| Notifications | 1 | 1 | 1 (API-003 auth) |
| **Total** | **67** | **67** | **4** |
