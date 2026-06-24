# Security Certification Report
Sprint 4.4 — Production Certification Sprint
Date: 2026-06-22
Auditor role: Security Engineer + Principal Architect
Method: Direct source reading. OWASP Top 10 framework. No assumptions. Every finding verified from file.

Severity levels:
- P0 CRITICAL — Immediate action required. Do not ship without fix.
- P1 HIGH — Fix before next public release.
- P2 MEDIUM — Fix within current sprint or next sprint.
- P3 LOW — Fix when convenient. No immediate risk.

---

## SEC-001 — Exposed Credentials in Git History

**Severity: P0 CRITICAL**
**OWASP:** A02:2021 — Cryptographic Failures / Sensitive Data Exposure

**Finding:**
File `TRACEVIEW_AUDIT_B.md` contains a live Supabase publishable key `sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc` pointing to `https://zznenaqcvzxtqxzilpyh.supabase.co`. This file appears in at least three commits in git history: `ffac077`, `704ca80`, `cc50838`.

**Verified from:** `docs/governance/TECHNICAL_DEBT_RANKING.md` (TD-002), `docs/governance/NEXT_10_ACTIONS.md` (Action 2)

**Impact:**
- The Supabase project URL and publishable key allow an attacker to query the Supabase Auth API directly: enumerate users, attempt auth bypass, access any data exposed via Supabase Row Level Security.
- Even if the key has been rotated, the old key remains in git history and is accessible to anyone with read access to the repository.
- If the repository is public or shared with contractors, this is an active compromise.

**Required actions (in order):**
1. Verify that the key shown in history has been rotated (per SECRET_ROTATION_RUNBOOK.md — verify this file exists and was executed)
2. Remove `TRACEVIEW_AUDIT_B.md` from the repository
3. Purge the key from git history: `git filter-branch` or BFG Repo Cleaner across commits `ffac077`, `704ca80`, `cc50838`
4. Force-push cleaned history to origin (coordinate with all team members to re-clone)
5. If the repository was ever public or shared externally: treat the old key as permanently compromised regardless of rotation

**Note: This is a user-action item. The assistant cannot execute git history rewrite.**

---

## SEC-002 — XSS via javascript: href in LinksPanel

**Severity: P1 HIGH**
**OWASP:** A03:2021 — Injection (XSS)

**Finding:**
`LinksPanel.jsx:79` renders `<a href={link.url} target="_blank" rel="noopener noreferrer">` where `link.url` is extracted from PDF annotations by the backend pipeline. A PDF can contain annotation objects with arbitrary `URI` action values. If a malicious PDF is uploaded containing an annotation with `javascript:alert(document.cookie)` as its URI, the link appears in the Links panel and is clickable.

React 18 issues a console warning for `javascript:` hrefs but does NOT block the navigation. Browser behavior varies: some browsers will execute the script in the current origin's context.

**File:** `frontend/src/components/LinksPanel.jsx:79`
**Function:** Link `<a>` element href attribute

**Attack vector:**
1. Attacker uploads a PDF containing a hyperlink annotation with `javascript:` payload as the URI
2. Attacker shares the document with a victim using a share link
3. Victim opens the document, navigates to the page with the link, sees the link in the Links panel
4. Victim clicks the link → JavaScript executes in the browser
5. Attacker can steal the viewer's session, cookies, or exfiltrate data

**Fix (10-minute change):**
```javascript
// LinksPanel.jsx:62 — add protocol guard to domain calculation
const domain = (() => {
  try {
    const url = new URL(link.url);
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    return url.hostname;
  } catch { return null; }
})();

// LinksPanel.jsx:79 — use safeUrl
const safeUrl = (() => {
  try {
    const url = new URL(link.url);
    return ['http:', 'https:'].includes(url.protocol) ? link.url : null;
  } catch { return null; }
})();
// Render: <a href={safeUrl || '#'} ...> and skip/grey links where safeUrl is null
```

**Note:** `rel="noopener noreferrer"` is already present. That prevents window.opener access but does NOT prevent `javascript:` execution.

---

## SEC-003 — JWT Token in localStorage

**Severity: P2 MEDIUM**
**OWASP:** A07:2021 — Identification and Authentication Failures

**Finding:**
`LoginScreen.jsx:51` stores the Supabase JWT in `localStorage.setItem('securedoc_token', token)`. localStorage is accessible to any JavaScript running on the page, including third-party scripts, browser extensions, and XSS payloads.

**File:** `frontend/src/screens/LoginScreen.jsx:51`

**Impact:**
- If an XSS vulnerability is exploited (see SEC-002), the attacker can immediately exfiltrate the owner's JWT from localStorage, gaining full authenticated access to the account.
- LocalStorage persists across browser sessions and is not scoped to the current tab.

**Mitigating factors:**
- No third-party scripts visible in the current frontend (React loaded via CDN with SRI — acceptable)
- The Supabase JWT is short-lived (typically 1 hour); session refresh is managed by Supabase client

**Recommendation:**
- Long-term: use httpOnly cookies (via Supabase SSR auth cookie mode) — requires backend change
- Short-term: acceptable risk IF SEC-002 is fixed (the primary XSS vector is removed)
- Do NOT mix with a fix for SEC-002 — address them independently

---

## SEC-004 — Rate Limiting Ineffective Under Horizontal Scaling

**Severity: P2 MEDIUM**
**OWASP:** A04:2021 — Insecure Design

**Finding:**
`slowapi` rate limiting is used in `webhooks.py` (10/min create, 5/min test-fire) and `notifications.py` (10/min SSE connect). `slowapi` uses an in-process counter. Under horizontal scaling (2+ backend instances), each instance maintains its own counter independently. A user can bypass rate limits by distributing requests across instances.

**Files:** `backend/app/routers/webhooks.py`, `backend/app/routers/notifications.py`
**Affected endpoints:** `POST /api/webhooks` (10/min), `POST /api/webhooks/{id}/test` (5/min), `GET /api/notifications/stream` (10/min)

**Impact:**
- Webhook test-fire (5/min) can be abused to SSRF-probe internal network from the SecureDoc server if SSRF validation has gaps
- SSE connection limit (5/user, in-process) can be bypassed across instances to create resource exhaustion

**Recommendation:** Replace `slowapi` in-process counters with Redis-backed rate limiting (e.g., `limits` library with Redis storage). Uses same Redis already present for SSE.

---

## SEC-005 — BillingScreen Bypasses Centralized Auth Middleware

**Severity: P2 MEDIUM**
**OWASP:** A07:2021 — Identification and Authentication Failures

**Finding:**
`BillingScreen.jsx` defines its own `authHeaders()` function that reads `localStorage.securedoc_token` directly, bypassing `window.SecureDocAPI` which provides centralized 401 handling. A 401 response from a billing endpoint will not trigger automatic re-authentication.

**File:** `frontend/src/screens/BillingScreen.jsx:20-28` (`authHeaders()` helper)
**Affected:** All three billing operations: status, checkout, portal

**Impact:**
- Expired or revoked JWTs for billing calls will show raw JSON error responses instead of redirecting to login
- Security-relevant behavior (token expiry, revocation) is silently ignored for the billing flow
- If the auth token format ever changes, billing requires a separate code change

**Recommendation:** Add billing methods to `window.SecureDocAPI` in `api.js` and remove the `authHeaders()` helper from BillingScreen.

---

## SEC-006 — link.viewed Event Never Dispatched

**Severity: P1 HIGH (business security posture)**
**OWASP:** A09:2021 — Security Logging and Monitoring Failures

**Finding:**
`POST /api/viewer/validate` creates a viewer session and grants access to a document. Neither `dispatch_webhook_event` nor `publish_notification` are called for the `link.viewed` event type. Document owners who have configured webhooks or who rely on real-time access notifications receive no signal when their document is viewed.

**File:** `backend/app/routers/viewer.py:172` → `backend/app/services/viewer_session_service.py:build_validate_response`
**Confirmed by:** `HIDDEN_FEATURE_BACKEND_AUDIT.md` Phase 1, tasks.py:175-200 (document.processed IS wired, link.viewed is NOT)

**Impact:**
- Document owners cannot receive real-time notification when their secure document is opened, even if they set up webhooks
- This is the most commercially sensitive event: knowing when a prospect or counterparty opens a shared document
- Access events ARE written to the `access_events` table (analytics), so audit trail exists — but real-time push notification is missing

**Recommendation:** Add two `try/except`-wrapped calls to `build_validate_response` after session creation:
```python
try:
    await dispatch_webhook_event(db, str(doc.user_id), 'link.viewed', {'document_id': str(doc.id), 'token': token, 'viewer_email': validated_email})
except Exception:
    pass
try:
    await publish_notification(str(doc.user_id), 'link.viewed', {'document_id': str(doc.id), 'viewer_email': validated_email})
except Exception:
    pass
```

---

## SEC-007 — SSE Auth Method Incompatible with EventSource API

**Severity: P2 MEDIUM**
**OWASP:** A07:2021 — Identification and Authentication Failures

**Finding:**
`GET /api/notifications/stream` uses `get_current_user` which requires an `Authorization: Bearer <jwt>` HTTP header. The browser's native `EventSource` API does not support custom headers. The frontend cannot authenticate with this endpoint using standard EventSource.

**File:** `backend/app/routers/notifications.py:29`

**Impact:**
- SSE cannot be consumed from the browser without a workaround
- Attempting to connect to the SSE stream without the Authorization header will receive a 401 or 403
- If a developer naively implements the frontend hook without understanding this, it will silently fail

**Options (in order of preference):**
1. Add query parameter token support to `get_current_user`: accept JWT from `?token=` query string in addition to Authorization header (scope this to the SSE endpoint only, not globally, to avoid JWT leakage in server logs)
2. Use a short-lived SSE token: add `GET /api/notifications/token` endpoint that returns a single-use token redeemable once for an SSE connection
3. Use `@microsoft/fetch-event-source` polyfill: adds a JS dependency but supports headers

---

## SEC-008 — SSRF Protection Timing in Webhook Delivery

**Severity: P3 LOW** (already partially mitigated)

**Finding:**
`webhook_tasks.py` validates the webhook URL for SSRF twice: at endpoint creation and at delivery time. This is correct architecture (DNS rebinding protection). However, the in-process rate limiter on webhook creation (`10/min`) is ineffective under horizontal scaling (SEC-004). An attacker could rapidly create many webhook endpoints pointing to internal IPs if running against a horizontally scaled instance.

**File:** `backend/app/services/webhook_service.py`, `backend/app/workers/webhook_tasks.py`

**Mitigating factors:** SSRF validation at delivery time catches DNS rebinding even if creation slips through. The 20-endpoint-per-user cap limits blast radius.

**Recommendation:** Redis-backed rate limiting (same fix as SEC-004) eliminates this residual risk.

---

## SEC-009 — Viewer Session via Cookie vs. Header (UNVERIFIED)

**Severity: UNVERIFIED ❓**

**Finding:**
`viewer.py` references `_get_session_id(request)` for session validation on all page/thumb/toc/download endpoints. The exact mechanism (cookie vs. header vs. query param) for `session_id` propagation was not confirmed from source reading.

**File:** `backend/app/routers/viewer.py` — references to `_get_session_id`

**Recommendation:** Verify that session_id is not leaked in browser history (avoid query param for session_id), and that it is properly scoped to the tab (sessionStorage in frontend).

---

## Security Certification Summary

| ID | Severity | Title | Status |
|---|---|---|---|
| SEC-001 | P0 CRITICAL | Credentials in git history | OPEN — user action required |
| SEC-002 | P1 HIGH | javascript: XSS in LinksPanel | OPEN — 10min fix |
| SEC-003 | P2 MEDIUM | JWT in localStorage | OPEN — acceptable with SEC-002 fix |
| SEC-004 | P2 MEDIUM | In-process rate limiting (not Redis) | OPEN |
| SEC-005 | P2 MEDIUM | BillingScreen bypasses auth middleware | OPEN |
| SEC-006 | P1 HIGH | link.viewed event never dispatched | OPEN — two try/except lines |
| SEC-007 | P2 MEDIUM | SSE auth incompatible with EventSource | OPEN — design decision required |
| SEC-008 | P3 LOW | SSRF + rate limit interaction | PARTIALLY MITIGATED |
| SEC-009 | UNVERIFIED | Viewer session_id propagation method | Needs verification |

**Security certification gate: BLOCKED**
- SEC-001 (P0) must be resolved before production certification
- SEC-002 (P1) must be resolved before production certification
- All other items are P2/P3 or require design decisions — acceptable to ship with documented risk

**What is working well:**
- Supabase JWT verification for owner auth (RS256)
- API key SHA-256 hash storage (key never stored in plaintext)
- HMAC-SHA256 webhook signing with SSRF re-validation
- Stripe webhook HMAC verification
- SRI hashes on CDN-loaded React
- `rel="noopener noreferrer"` on external links
- Viewer session isolation via session_id
- Access policy enforcement (max_views, max_concurrent_sessions, ip_allowlist, allowed_emails, allowed_domains)
- Last-owner protection in organizations
- Role hierarchy enforcement (`role_gte`) in organizations
- Audit logging for sensitive operations (document.deleted, link.revoked, api_key.*, org.*, member.*)
