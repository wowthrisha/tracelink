# Security Revalidation Report — Sprint 5.3 Phase 5

**Date:** 2026-06-23  
**Sprint:** 5.3  
**Phase:** 5 — Security Review  
**Status:** COMPLETE

---

## Summary

Phase 5 performed a security audit across frontend and backend for XSS, open redirects, unsafe URLs, CSRF, and auth bypass patterns. One XSS vulnerability was found and fixed in ViewerScreen. All other checks passed.

---

## Checks Performed

### XSS — PASS with one fix

**Check:** `dangerouslySetInnerHTML`, `innerHTML`, `document.write`, `eval()` in all JSX/JS files.  
**Result:** None found. ✓

**Check:** User-controlled data rendered as href without protocol validation.  
**Finding (FIXED):** `ViewerScreen.jsx` — annotation hyperlink overlays used `href={link.url}` directly. PDF annotations can contain any URL scheme. A PDF with `javascript:` link annotations would render as invisible clickable overlays covering document content.

**Fix applied:**
```javascript
// Before (VULNERABLE):
<a key={i} href={link.url} target="_blank" rel="noopener noreferrer" ...>

// After (FIXED):
let safeHref = null;
try { const u = new URL(link.url); if (/^https?:$/i.test(u.protocol)) safeHref = link.url; } catch {}
<a key={i} href={safeHref || '#'} target={safeHref ? '_blank' : undefined}
   onClick={safeHref ? undefined : e => e.preventDefault()} ...>
```

**Pre-existing protection:** `LinksPanel.jsx` already had the same `safeUrl` pattern. ViewerScreen was inconsistent.

---

### Open Redirects — PASS

**Check:** `window.location.href` assignments.  
**Finding:** `BillingScreen.jsx` line 50 — `window.location.href = url` where `url` comes from `POST /api/billing/checkout` response.  
**Assessment:** PASS — URL comes from the authenticated backend response (Stripe checkout URL). Not user-controllable from the client. No open redirect risk.

---

### CSRF — PASS

**Assessment:** All state-mutating API calls use JWT Bearer tokens in `Authorization` header (not cookies), making CSRF irrelevant. The `POST /analytics/events` endpoint (unauthenticated viewer) validates the share-link token in the request body and checks for an active session.

---

### Auth Bypass — PASS

**Check:** Endpoints that require `require_scope()` or `get_current_user()`.  
**Assessment:** All document/link/analytics management endpoints use `Depends(require_scope(...))`. Viewer endpoints validate the link token. No bypass patterns found.

---

### Injection — PASS

**Check:** Raw SQL strings, f-string queries, unparameterized values.  
**Assessment:** All queries use SQLAlchemy ORM with parameterized expressions. No raw SQL found in routers or services.

---

### Sensitive Data Exposure — PASS

**Check:** Password hashes in API responses, tokens in logs.  
**Assessment:** Gate endpoint explicitly excludes `password_hash`. Link summaries include only `has_password: bool`. Test `test_gate_never_exposes_password_hash` verifies this.

---

## Commit

`fix(security): sanitize PDF annotation hrefs to prevent javascript: URL injection — e6b3929`

---

## Verdict

**PASS** — One XSS vulnerability found and fixed. No open redirects, CSRF, auth bypass, or injection vulnerabilities found. Security posture confirmed production-ready.
