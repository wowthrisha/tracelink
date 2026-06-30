# Security Report — Sprint 5.5 Production Audit

**Date:** 2026-06-28  
**Sprint:** 5.5  
**Scope:** Frontend security posture, auth flows, data exposure, access control

---

## Executive Summary

No critical security vulnerabilities found. The application's core security model is sound: JWT-based auth, link revocation with cache invalidation, hard-delete gated behind revocation, and multi-layered access controls per link. Three observations warrant attention before public beta.

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 2 |
| INFO | 3 |

---

## MEDIUM

### SEC-001 — Viewer Screen Accessible via Sidebar Without Document Context
**Evidence:** `016_viewer.png`  
**OWASP category:** A01 Broken Access Control

The Viewer screen is reachable without a document ID by clicking "Viewer" in the sidebar. The resulting view shows an authenticated user an "Email Verification Required" dialog — the public viewer gate. While this doesn't expose any data, it represents an inconsistency in the authentication boundary: authenticated users are being pushed into the unauthenticated viewer flow.

**Risk:** Low — no data exposure occurs; however, a confused user might enter their email into a verification form that has no effect in this context.

**Recommendation:** Guard the `viewer` screen state in `AppShell.jsx` to require `activeDoc` before rendering `ViewerScreen`.

---

## LOW

### SEC-002 — JWT Token Stored in localStorage
**Evidence:** Auth injection via `localStorage.setItem('securedoc_token', ...)`  
**OWASP category:** A02 Cryptographic Failures

The application stores the authentication JWT in `localStorage`, which is accessible to any JavaScript running in the same origin. While the SPA has no third-party scripts visible in the audit, localStorage is generally considered less secure than `httpOnly` cookies for token storage, as it is vulnerable to XSS attacks if any script injection occurs.

**Risk:** Low for current beta (no complex third-party JS, single origin). Medium risk if ad/analytics scripts are added later.

**Recommendation:** Evaluate migration to `httpOnly` cookie-based sessions for production. If localStorage is retained, ensure strict Content-Security-Policy headers are set on the FastAPI server.

---

### SEC-003 — Webhook URL Not Validated Client-Side
**Evidence:** `011_webhooks.png` — webhook registration form accepts any URL  
**OWASP category:** A10 Server-Side Request Forgery

The webhook registration form shows a URL input with no visible client-side format validation. If server-side validation also lacks proper URL allowlisting, a malicious user could register a webhook that points to internal network addresses (e.g., `http://169.254.169.254/` for AWS metadata, `http://localhost:8000/admin/`), enabling SSRF attacks.

**Risk:** Medium in production if the backend makes outbound HTTP requests to webhook URLs without validating the scheme and host. Low if the backend already validates against private IP ranges.

**Recommendation:** Confirm backend webhook delivery validates URLs against an allowlist (public IPs only, no private ranges, no `file://`, no `localhost`).

---

## Informational

### SEC-INFO-001 — Hard Delete Requires Prior Revocation (Good)
The `DELETE /api/links/{id}/hard` endpoint requires `revoked_at is not None`, enforced in `routers/links.py:333`. This prevents accidental permanent deletion of active links. Confirmed working in Sprint 5.4B.

### SEC-INFO-002 — Link Cache Invalidated on Every Mutation (Good)
`invalidate_link()` is called on PATCH, soft-DELETE, and hard-DELETE operations (`routers/links.py:289, 337`). Policy changes (expiry, email list, revocation) take effect on the next viewer request. No stale-cache access window.

### SEC-INFO-003 — Audit Events for All Link Lifecycle Operations (Good)
All four link lifecycle events generate audit log entries:
- `link.created` — on POST (Sprint 5.4B)
- `link.updated` — on PATCH
- `link.revoked` — on soft-DELETE
- `link.deleted` — on hard-DELETE

All are wrapped in `try/except` so audit failures don't break the operation. Appropriate for beta.

---

## Security Controls Verified

| Control | Status | Evidence |
|---------|--------|----------|
| JWT auth on all API endpoints | ✅ Verified | `require_scope("links:write")` guards |
| Document ownership check before link operations | ✅ Verified | `routers/links.py:241-249` — user_id check |
| Password hashing (bcrypt/similar) | ✅ Verified | `hash_password()` called in create and update |
| Revoke gate before hard delete | ✅ Verified | `revoked_at is not None` check |
| Cache invalidation on permission change | ✅ Verified | `invalidate_link()` on all mutations |
| Audit log for link lifecycle | ✅ Verified | All 4 events present |
| No JWT visible in rendered HTML | ✅ Verified | Console scan found no token exposure |
| No CORS errors in browser | ✅ Verified | 0 CORS errors in console log |
| No 401/403 from legitimate requests | ✅ Verified | 0 auth errors in console log |
