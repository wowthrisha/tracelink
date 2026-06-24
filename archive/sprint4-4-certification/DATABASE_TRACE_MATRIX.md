# Database Trace Matrix
Sprint 4.4 — Production Certification Sprint
Date: 2026-06-22
Auditor role: Principal Architect + Lean Six Sigma Black Belt
Method: Trace each database table through the full stack: model → router → api.js → frontend screen.
Source files read: backend/app/models/, backend/app/routers/, frontend/src/screens/, frontend/src/api.js

Trace status:
- FULL TRACE ✅ — Table → Router → api.js → Screen: all links confirmed
- PARTIAL TRACE ⚠️ — Some path segments missing or unverified
- BACKEND ONLY 🔒 — Table and router exist, no frontend consumer
- ORPHANED ❌ — Table or model exists but no clear write path confirmed

---

## Table: documents

**Model file:** `backend/app/models/document.py`
**Key fields:** id, user_id, filename, status (pending/processing/processed/failed), org_id (nullable), parent_document_id (nullable), created_at

| Layer | Reference | Verified |
|---|---|---|
| Database table | `documents` | ✅ |
| Write path | `POST /api/documents/upload` → `documents.py:upload_document` | ✅ |
| Read path | `GET /api/documents` → `documents.py:list_documents` | ✅ |
| Status path | `GET /api/documents/{id}/status` | ✅ |
| api.js | `window.SecureDocAPI.getDocuments()`, `uploadDocument()`, `pollDocumentStatus()` | ✅ |
| Frontend screen | `UploadScreen.jsx` — document table, upload flow, status polling | ✅ |
| Org-scoped upload | `org_id` param accepted in upload, stored on document | ✅ backend; ❌ no org_id selector in frontend |
| Version history | `parent_document_id` FK for version tracking | ✅ backend; ❌ no upload-new-version UI |

**Trace: PARTIAL ⚠️** — org_id and version history fields exist in model and are accepted by the API but have no frontend write path. Documents can be uploaded without org scoping (current behavior). Version history browsable via `GET /api/documents/{id}` → versions array but no UI surfaces it.

---

## Table: share_links

**Model file:** `backend/app/models/link.py`
**Key fields:** id, document_id, token (unique), password_hash, allowed_emails, allowed_domains, expiry_at, max_views, max_concurrent_sessions, ip_allowlist, can_download, can_print, can_copy, can_right_click, watermark_enabled, can_annotate, enable_info, is_revoked

| Layer | Reference | Verified |
|---|---|---|
| Database table | `share_links` | ✅ |
| Write path (create) | `POST /api/links` → `links.py:create_link` | ✅ backend; ❌ **frontend "New Link" button is stub** |
| Write path (update) | `PATCH /api/links/{id}` → `links.py:update_link` | ✅ |
| Write path (revoke) | `DELETE /api/links/{id}` → `links.py:revoke_link` | ✅ |
| Read path | `GET /api/links` | ✅ |
| api.js | `window.SecureDocAPI.getLinks()`, `updateLink()`, `revokeLink()` | ✅ |
| **api.js createLink** | `window.SecureDocAPI.createLink()` | ❓ UNVERIFIED — AccessScreen "New Link" button never calls any API |
| Frontend screen | `AccessScreen.jsx` — Policy tab saves via updateLink; Share Link tab lists/revokes | ✅ partial |

**Trace: PARTIAL ⚠️** — Create path broken by UI-002 defect. `POST /api/links` exists and works. The frontend "⟳ New Link" button does not call it. This means the ONLY way to get a working share link is if one already exists in the database (created prior to this defect or via direct API call).

**CRITICAL IMPLICATION:** If no share links exist for a document, the user cannot create one through the UI. The Share Link tab will be empty and the "New Link" button silently does nothing. The entire viewer-access workflow breaks at this point.

---

## Table: access_events

**Model file:** `backend/app/models/analytics.py` (or access_events)
**Purpose:** Per-viewer, per-page event log (page_view, dwell_time, etc.)

| Layer | Reference | Verified |
|---|---|---|
| Database table | `access_events` | ✅ |
| Write path | `POST /api/analytics/events` → called by viewer session (auto) | ✅ |
| Read path | `GET /api/analytics/events` | ✅ |
| api.js | `window.SecureDocAPI.getAccessEvents()` | ✅ |
| Frontend screen | `AccessScreen.jsx` — Access Log tab, `AnalyticsScreen.jsx` — Overview/By Document tabs | ✅ |

**Trace: FULL TRACE ✅**

---

## Table: document_groups

**Model file:** `backend/app/models/group.py`
**Key fields:** id, user_id, name, created_at

| Layer | Reference | Verified |
|---|---|---|
| Write path | `POST/PATCH/DELETE /api/groups` | ✅ |
| Read path | `GET /api/groups` | ✅ |
| api.js | `createGroup`, `updateGroup`, `deleteGroup`, `assignDocumentsToGroup`, `removeDocumentFromGroup` | ✅ |
| Frontend screen | `UploadScreen.jsx` — Groups strip | ✅ |

**Trace: FULL TRACE ✅**

---

## Table: annotations

**Model file:** `backend/app/models/annotation.py`
**Key fields:** id, document_id, link_id, session_id, page_number, type, content, position_json, created_at

| Layer | Reference | Verified |
|---|---|---|
| Write path | `POST /api/annotations` (viewer) | ✅ |
| Read path | `GET /api/annotations` (owner), `GET /api/annotations/{id}/thread` (viewer) | ✅ |
| Delete path | `DELETE /api/annotations/{id}` | ✅ |
| api.js | `createAnnotation`, `getAnnotationThread`, `deleteAnnotation` | ✅ |
| Frontend screen | `ViewerScreen.jsx` — annotation draw/highlight, thread view; `AccessScreen.jsx` — Annotations tab (owner view) | ✅ |

**Trace: FULL TRACE ✅**

---

## Table: feedback

**Model file:** `backend/app/models/feedback.py`

| Layer | Reference | Verified |
|---|---|---|
| Write path | Viewer submits feedback (unverified — `POST /api/feedback` not confirmed from viewer) | UNVERIFIED |
| Read path | `GET /api/feedback` | ✅ |
| Update path | `PATCH /api/feedback/{id}` | ✅ |
| api.js | `getFeedback`, `updateFeedback` | ✅ |
| Frontend screen | `AccessScreen.jsx` — Feedback tab | ✅ |
| Viewer write path | ViewerScreen.jsx viewer feedback submission | UNVERIFIED |

**Trace: PARTIAL ⚠️** — Owner-side read/update confirmed. Viewer-side write path not confirmed from source reading.

---

## Table: user_billing

**Model file:** `backend/app/models/billing.py`
**Key fields:** user_id, plan (free/pro), subscription_status, stripe_customer_id, stripe_subscription_id, current_period_end

| Layer | Reference | Verified |
|---|---|---|
| Write path (Stripe webhook) | `POST /api/billing/webhook` → `_handle_subscription_upsert`, `_handle_payment_failed`, `_handle_subscription_deleted` | ✅ |
| Write path (create billing row) | `_get_or_create_billing` called on `GET /status` | ✅ |
| Read path | `GET /api/billing/status` | ✅ |
| Frontend screen | `BillingScreen.jsx` | ✅ |

**Trace: FULL TRACE ✅** — Stripe webhook handles all lifecycle events including immediate downgrade on payment failure.

---

## Table: document_storage (logical)

**Note:** Storage data may be derived/aggregated, not a standalone table. `StorageScreen.jsx` uses `getStorageDashboard()` and `getStorageForecast()`. Backend storage model not fully traced — presence of storage aggregation endpoints confirmed.

**Trace: PARTIAL ⚠️** — Frontend → API confirmed. Underlying storage model not fully read.

---

## Table: webhook_endpoints

**Model file:** `backend/app/models/webhook.py`
**Key fields:** user_id, url, secret (hex), events_json, is_active

| Layer | Reference | Verified |
|---|---|---|
| Write path | `POST/PATCH/DELETE /api/webhooks` | ✅ |
| Read path | `GET /api/webhooks` | ✅ |
| api.js | None | ❌ Zero api.js methods |
| Frontend screen | None | ❌ No screen |
| Event dispatch | `dispatch_webhook_event` from `tasks.py` (document.processed ✅), `analytics.py` (analytics.completed ✅), viewer.py (link.viewed ❌ MISSING) | ✅ partial |

**Trace: BACKEND ONLY 🔒**

---

## Table: webhook_deliveries

**Model file:** `backend/app/models/webhook.py`
**Key fields:** webhook_id, event_type, status, attempts, response_status, response_body, last_attempt_at

| Layer | Reference | Verified |
|---|---|---|
| Write path | `deliver_webhook` Celery task in `webhook_tasks.py` | ✅ |
| Read path | `GET /api/webhooks/{id}/deliveries` | ✅ |
| api.js | None | ❌ |
| Frontend screen | None | ❌ |

**Trace: BACKEND ONLY 🔒**

---

## Table: api_keys

**Model file:** `backend/app/models/api_key.py`
**Key fields:** user_id, name, key_prefix, key_hash (SHA-256), scopes_json, is_active, last_used_at, expires_at

| Layer | Reference | Verified |
|---|---|---|
| Write path | `POST /api/api-keys` | ✅ |
| Read path | `GET /api/api-keys` | ✅ |
| api.js | None | ❌ |
| Frontend screen | None | ❌ |

**Trace: BACKEND ONLY 🔒**

---

## Table: organizations

**Model file:** `backend/app/models/org.py`

| Layer | Reference | Verified |
|---|---|---|
| Write path | `POST/PATCH/DELETE /api/orgs` | ✅ |
| Read path | `GET /api/orgs` | ✅ |
| api.js | None | ❌ |
| Frontend screen | None | ❌ |

**Trace: BACKEND ONLY 🔒**

---

## Table: org_memberships

**Model file:** `backend/app/models/org.py`

| Layer | Reference | Verified |
|---|---|---|
| Write path | `POST/PATCH/DELETE /api/orgs/{id}/members` | ✅ |
| Read path | `GET /api/orgs/{id}/members` | ✅ |
| api.js | None | ❌ |
| Frontend screen | None | ❌ |

**Trace: BACKEND ONLY 🔒**

---

## Table: admin_audit_log

**Model file:** `backend/app/models/audit.py`
**Key fields:** org_id, actor_user_id, event_type, target_type, target_id, details_json, ip_hash, created_at

| Layer | Reference | Verified |
|---|---|---|
| Write path | `log_audit_event` service: called from orgs.py, api_keys.py, documents.py:607 (document.deleted), links.py:182 (link.revoked) | ✅ |
| Read path | `GET /api/admin/audit-log` | ✅ |
| api.js | None | ❌ |
| Frontend screen | None | ❌ |

**Event coverage confirmed:**
| Event | Write site | Confirmed |
|---|---|---|
| `org.created` | `orgs.py` | ✅ |
| `org.updated` | `orgs.py` | ✅ |
| `org.deleted` | `orgs.py` | ✅ |
| `member.added` | `orgs.py` | ✅ |
| `member.role_changed` | `orgs.py` | ✅ |
| `member.removed` | `orgs.py` | ✅ |
| `api_key.created` | `api_keys.py` | ✅ |
| `api_key.revoked` | `api_keys.py` | ✅ |
| `api_key.deleted` | `api_keys.py` | ✅ |
| `document.deleted` | `documents.py:607` | ✅ |
| `link.revoked` | `links.py:182` | ✅ |

**Trace: BACKEND ONLY 🔒** — All write paths confirmed. No frontend.

---

## Summary Matrix

| Table | Frontend Accessible | Full Trace | Notes |
|---|---|---|---|
| documents | Yes | PARTIAL ⚠️ | org_id + version history fields unused by frontend |
| share_links | Yes | PARTIAL ⚠️ | Create path broken by UI-002 defect |
| access_events | Yes | FULL ✅ | — |
| document_groups | Yes | FULL ✅ | — |
| annotations | Yes | FULL ✅ | — |
| feedback | Yes | PARTIAL ⚠️ | Viewer write path unverified |
| user_billing | Yes | FULL ✅ | — |
| document_storage | Yes | PARTIAL ⚠️ | Storage model not fully read |
| webhook_endpoints | No | BACKEND ONLY 🔒 | link.viewed write path missing |
| webhook_deliveries | No | BACKEND ONLY 🔒 | — |
| api_keys | No | BACKEND ONLY 🔒 | — |
| organizations | No | BACKEND ONLY 🔒 | — |
| org_memberships | No | BACKEND ONLY 🔒 | — |
| admin_audit_log | No | BACKEND ONLY 🔒 | All write paths confirmed |

**Critical finding:** The `share_links` table has a broken create path. `POST /api/links` exists and is correct on the backend. The frontend "New Link" button never calls it. If a user has no pre-existing share links, they cannot create one.
