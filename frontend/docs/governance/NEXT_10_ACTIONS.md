# Next 10 Actions
Production Readiness Audit — Phase 6
Date: 2026-06-22

Ranked by: user/business value first, effort second. "High ROI" = large user impact, low engineering effort.
Source: FEATURE_INVENTORY, E2E_VALIDATION_MATRIX, COMPETITOR_GAP_ANALYSIS, TECHNICAL_DEBT_RANKING, PRODUCTION_READINESS_REPORT.

---

## Action 1 — Fix `link.url` javascript: protocol vulnerability
**Sprint:** 4.3 (Phase 4, already planned)
**File:** `frontend/src/components/LinksPanel.jsx:79`
**Effort:** 10 minutes
**Impact:** Closes P0 XSS vector. Prevents javascript: URL execution from crafted PDFs.
**Change:** Add `if (!link.url || link.url.startsWith('javascript:')) return null;` before the `<a>` element render.
**Risk:** None. Bad URLs simply don't render. Zero UX impact for any real URL.
**Tracking:** TD-001, FE-R-064, GOV-R-006

---

## Action 2 — Rotate Supabase credentials and scrub git history
**Sprint:** Immediate (user action — cannot be automated)
**Files:** `securedoc/TRACEVIEW_AUDIT_B.md`, git commits ffac077, 704ca80, cc50838
**Effort:** 1–2 hours (user action in Supabase dashboard + BFG/git-filter-repo)
**Impact:** Closes P0 security incident. Credential `sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc` is committed to git history. Must be rotated before any public repository access or team onboarding.
**Steps:** Execute `SECRET_ROTATION_RUNBOOK.md` → rotate anon key in Supabase dashboard → scrub git history → delete `TRACEVIEW_AUDIT_B.md` → force-push.
**Risk:** Requires coordinated deployment update (new anon key must be set in Railway env vars before old one is deactivated).
**Tracking:** TD-002, GOV-R-003

---

## Action 3 — Add email notification when a viewer opens a document
**Sprint:** 4.4 (first backend sprint after 4.3 security hardening)
**Component:** Backend only — `backend/app/routers/viewer.py:validate`
**Effort:** 1 day (backend: add SendGrid/SES call on session creation; frontend: zero changes)
**Impact:** Closes the #1 competitive gap vs. DocSend. Every user who shares a document with a prospect/investor/client wants to know when it's opened. Without this, SecureDoc requires manual analytics polling for every document.
**Change:** In `POST /api/viewer/validate`, after session creation, queue an email to the document owner: "Your document [name] was opened by [email] at [time]."
**Risk:** Requires new external service dependency (SendGrid or AWS SES). Add to env vars. No frontend changes, no API contract changes.
**Constraints:** DO NOT add frontend UI for notification preferences until a separate sprint approves it.

---

## Action 4 — Wire BillingScreen to SecureDocAPI
**Sprint:** 4.3 or next available sprint
**File:** `frontend/src/screens/BillingScreen.jsx`
**Effort:** 1–2 hours
**Impact:** Fixes auth token handling for billing calls. Currently, BillingScreen uses raw `fetch()` without routing through `window.SecureDocAPI`. 401 errors from billing endpoints don't trigger re-auth. Auth headers are set manually and could drift from the api.js pattern.
**Change:** Add `getBillingStatus()`, `createBillingCheckout()`, `createBillingPortal()` to api.js (3 methods, ~30 lines). Update BillingScreen to call them. Zero visible change to users.
**Risk:** None. Pure refactor with no behavior change if api.js methods are identical to the current fetch calls.
**Tracking:** TD-008

---

## Action 5 — Add frontend settings screen for API Keys
**Sprint:** 4.4 (requires sprint authorization — new screen)
**Component:** New screen: `src/screens/ApiKeysScreen.jsx` + AppShell nav entry
**Effort:** 1 day
**Impact:** Unlocks developer integrations. The backend (`/api/api-keys`) is fully implemented with SHA-256 key storage, scope enforcement, and expiry. Zero users can create an API key today. API keys enable CRM integrations, automation, and partner workflows.
**Change:** Create a minimal CRUD list screen: show existing keys (masked), create new key (show once on creation), delete key. Add to AppShell nav. Add 4 SecureDocAPI methods for the 4 endpoints.
**Risk:** Low. Backend is fully tested. New screen doesn't touch existing screens.
**Constraints:** This is a NEW SCREEN. Requires explicit sprint authorization before implementation.

---

## Action 6 — Add frontend settings screen for Webhooks
**Sprint:** 4.4 (requires sprint authorization — new screen)
**Component:** New screen: `src/screens/WebhooksScreen.jsx`
**Effort:** 1.5 days
**Impact:** Unlocks integration workflows (Zapier, n8n, custom builds). Backend is fully implemented with SSRF protection, delivery logs, test-fire capability. Zero users can configure a webhook today.
**Change:** CRUD screen: list endpoints, create with URL + event types + secret, view delivery logs, test-fire button. Add to AppShell nav. Add SecureDocAPI methods for the 5 webhook endpoints.
**Risk:** Low. Backend is complete. Delivery log view is read-only.
**Constraints:** New screen. Requires sprint authorization.

---

## Action 7 — Wire SSE EventSource to AppShell
**Sprint:** 4.4 (alongside Action 3 email notification sprint)
**Component:** `frontend/src/screens/AppShell.jsx`
**Effort:** 0.5 days
**Impact:** Enables real-time toast notifications for document processing completion and link access events. The backend SSE endpoint (`GET /api/notifications/stream`) exists and streams events. AppShell never subscribes to it.
**Change:** Add `EventSource('/api/notifications/stream')` in AppShell useEffect. On `message` event, push to toast context. On `upload_complete` event, refresh document list.
**Risk:** Low for single-instance deployment. Under horizontal scaling, see TD-011 (in-process registry). Add after Action 3 so the same sprint can wire link-access events into SSE.
**Note:** Also requires TD-011 fix (Redis pub/sub) before horizontal scaling.

---

## Action 8 — Update esbuild browser targets
**Sprint:** Next available (trivial)
**File:** `frontend/package.json` (esbuild target config)
**Effort:** 30 minutes (change + build + smoke test)
**Impact:** Smaller bundle output. Eliminates compatibility transforms for IE11-era patterns. Modern JS syntax in production.
**Change:** Update `target: ['chrome80', 'firefox78', 'safari14']` to `target: ['chrome110', 'firefox115', 'safari16']`. Run build, verify bundle size decreases, run smoke test in browser.
**Risk:** Low. These are minimum supported browser versions. Any user on Chrome 110+ (2023) is covered. If older browser support is a business requirement, keep as-is.
**Tracking:** TD-009

---

## Action 9 — Document saml_domain field in DECISION_LOG
**Sprint:** 4.3 (no code change — documentation only)
**File:** `docs/decisions/DECISION_LOG.md`
**Effort:** 15 minutes
**Impact:** Prevents future engineers from thinking SAML is partially implemented when it is only a placeholder field. Clarifies that SAML authentication requires a dedicated sprint.
**Change:** Add DECISION_LOG entry: "D-033 — `saml_domain` field in Organization model is reserved for future SAML SSO. No authentication flow is implemented. The field stores the SAML identity provider domain for future use."
**Tracking:** TD-014

---

## Action 10 — Add `POST /api/documents/{id}/versions` endpoint + upload UI
**Sprint:** 4.4+ (backend endpoint + frontend change — requires sprint authorization)
**Files:** `backend/app/routers/documents.py`, `frontend/src/screens/UploadScreen.jsx`
**Effort:** 2 days
**Impact:** Makes version history a usable feature. The `documents` model has `version` and `parent_document_id` columns. The `GET /versions` recursive CTE query is implemented. But there is no way to create a version chain — every upload is an orphaned document.
**Change:** Backend: add `POST /api/documents/{id}/versions` that accepts a new file, creates a document record with `parent_document_id = {id}`, increments version. Frontend: add "Upload new version" button on existing documents in UploadScreen (opens upload picker, calls new endpoint).
**Risk:** Medium. Changes UploadScreen (high-traffic component) and adds a new backend endpoint. Requires careful testing of version chain queries.
**Constraints:** New feature. Requires explicit sprint authorization.

---

## Priority Summary

| Action | Sprint | Effort | Type | Authorizer |
|---|---|---|---|---|
| 1. Fix link.url javascript: guard | 4.3 (now) | 10 min | Security fix | Already in plan |
| 2. Rotate credentials + scrub git history | Now | 1–2 hrs | User action | User must execute |
| 3. Email notification on doc open | 4.4 | 1 day | New backend feature | Requires sprint approval |
| 4. Wire BillingScreen to SecureDocAPI | 4.3 or 4.4 | 1–2 hrs | Refactor | Safe, no behavior change |
| 5. API Keys frontend screen | 4.4 | 1 day | New screen | Requires sprint approval |
| 6. Webhooks frontend screen | 4.4 | 1.5 days | New screen | Requires sprint approval |
| 7. SSE EventSource in AppShell | 4.4 | 0.5 days | Wiring | Requires sprint approval |
| 8. Update esbuild targets | Next opportunity | 30 min | Build config | Safe |
| 9. Document saml_domain decision | 4.3 | 15 min | Docs only | Safe |
| 10. Version creation endpoint + UI | 4.4+ | 2 days | New feature | Requires sprint approval |

**Actions 1, 2, 4, 8, 9 can be done without new feature authorization.**
**Actions 3, 5, 6, 7, 10 require explicit new sprint authorization before any code is written.**
