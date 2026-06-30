# Technical Debt Ranking
Production Readiness Audit — Phase 4
Date: 2026-06-22
Source: Direct code reading. All findings verified from source files.

Priority: P0 = security/reliability risk now | P1 = blocks growth | P2 = friction | P3 = cleanup

---

## P0 — Security / Reliability Risk (Fix Immediately)

### TD-001 — `link.url` href without `javascript:` protocol guard
- **File:** `frontend/src/components/LinksPanel.jsx:79`
- **Code:** `<a href={link.url} target="_blank" rel="noopener noreferrer">`
- **Risk:** PDF-extracted URLs are rendered as `href` without validation. React passes `javascript:` URLs to the DOM with a console warning but does not block them. If a PDF contains a `javascript:` hyperlink, clicking it in the viewer would execute code in the viewer's origin.
- **Impact:** XSS via crafted PDF. Could expose viewer session token.
- **Effort:** 10 minutes. Add `if (!link.url || link.url.startsWith('javascript:')) return null;` before the `<a>` render.
- **Action:** Sprint 4.3 Phase 4. Tracked as FE-R-064 / GOV-R-006.

### TD-002 — TRACEVIEW_AUDIT_B.md contains live Supabase credentials in git history
- **File:** `securedoc/TRACEVIEW_AUDIT_B.md`
- **Credential:** `sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc` + Supabase URL
- **Risk:** The anon key is PUBLIC in git history (commits ffac077, 704ca80, cc50838). If the repository is or becomes public, all Supabase data is accessible to anyone with that key. Even for a private repo, any team member or CI system that clones has the credential.
- **Impact:** Full Supabase data exposure. **P0 security incident.**
- **Effort:** User action required. Execute SECRET_ROTATION_RUNBOOK.md → rotate anon key in Supabase dashboard → BFG/git-filter-repo to scrub commits → force-push to remove from history → delete TRACEVIEW_AUDIT_B.md.
- **Action:** User must execute immediately. Claude cannot do this — requires Supabase dashboard access and git history rewrite.

---

## P1 — Blocks Growth (Fix Before Next Product Phase)

### TD-003 — No email notification when viewer opens a document
- **Component:** None (no SMTP/sendgrid integration)
- **Impact:** Every uploader must manually check AnalyticsScreen to know if their document was opened. This is the #1 user experience gap vs. DocSend. Sales teams, investors, and clients share documents specifically to track opens — no notification makes the platform unusable for time-sensitive workflows.
- **Effort:** MEDIUM. Backend: 1 day (add sendgrid/ses call in viewer.py validate endpoint). Frontend: zero changes.
- **Action:** Requires new backend integration. Not a Sprint 4.3 item (Sprint 4.3 is frontend-only hardening). Schedule as Sprint 4.4 P1.

### TD-004 — Webhooks, API Keys, Orgs, Admin Log, SSE have zero frontend UI
- **Scope:** 5 complete backend feature areas with no frontend path
- **Files affected:** `backend/app/routers/webhooks.py` (fully implemented), `api_keys.py` (fully implemented), `orgs.py` (fully implemented), `admin.py` (fully implemented), `notifications.py` (SSE stream)
- **Impact:** Users cannot configure webhooks for integrations, cannot create API keys, cannot manage team memberships, cannot access audit logs, and receive no real-time notifications. These features are invisible despite being fully built.
- **Effort:** Each requires a new screen + SecureDocAPI methods:
  - API Keys: 1-day screen (simple CRUD list)
  - Webhooks: 1–2 days (CRUD + delivery log view)
  - Organizations: 3–4 days (multi-tab: members, domains, roles)
  - Admin Audit Log: 1 day (read-only table with filters)
  - SSE: 0.5 days (EventSource in AppShell, toast on events)
- **Note:** These are new screens — requires plan approval. Hard constraint: DO NOT ADD FEATURES without explicit sprint authorization.

### TD-005 — `api.js` 769-line monolith with ~30 duplicated patterns
- **File:** `frontend/api.js:1-769`
- **Duplications found:**
  - `_clearAndReload()` error handler called ~30 times (every 401 path)
  - 5 copy-pasted `_downloadBlob()` sequences (feedback export, annotation export, reviewer activity export, visual annotation export, download endpoint)
  - `buildFeedbackFilters` duplicated inline in `api.js` AND in `src/utils/feedback.js` (the extracted version is not used by api.js)
- **Impact:** Every new API method copies these patterns, growing the duplication. Test coverage is impractical on a 769-line single-file UMD global. The 401 handler `_clearAndReload` is not visible to the React component tree (no error state propagated), so auth failures are opaque to the UI.
- **Effort:** HIGH. Full decomposition of `api.js` is a 3–5 day sprint with high risk (every frontend feature depends on it).
- **Action:** No action until `api.js` exceeds 1,000 lines OR test coverage is added. Track in TECHNICAL_DEBT_REGISTER. Trigger: next new API method addition.

### TD-006 — Auth JWT (`securedoc_token`) in localStorage
- **Files:** `frontend/src/screens/AppShell.jsx:23`, `frontend/src/screens/LoginScreen.jsx:51`
- **Risk:** localStorage is accessible to any JavaScript on the same origin. If an XSS vulnerability is ever introduced, the auth token is exfiltrable. An httpOnly cookie would not be accessible to JavaScript.
- **Current mitigations:** No XSS vectors found in current codebase. Supabase JWTs have standard expiry. HSTS is enabled.
- **Impact:** MEDIUM. Not exploitable today due to clean XSS surface. Becomes HIGH if any innerHTML or dangerouslySetInnerHTML is added to any component.
- **Effort:** HIGH. Requires migrating from client-set localStorage to backend-issued httpOnly cookies, which changes the auth contract across api.js and all screens. This is an API contract change.
- **Action:** Monitor. If XSS surface grows (any innerHTML addition), prioritize immediately. Current risk level: MEDIUM-ACCEPTED.

---

## P2 — Friction (Fix Within 2–3 Sprints)

### TD-007 — Document version history: model exists, no creation flow
- **Files:** `backend/app/models/document.py` (version, parent_document_id columns), `backend/app/routers/documents.py` (GET /versions)
- **Gap:** Recursive CTE query for version chains is implemented. There is no `POST /api/documents/{id}/versions` endpoint and no frontend flow to upload a document as a new version of an existing one. Users must upload separate files with no version linking.
- **Impact:** Enterprise customers expect version control. Documents are siloed — there's no way to say "this is v2 of the proposal I sent last week."
- **Effort:** MEDIUM. Backend: add POST endpoint with version chain logic (~100 lines). Frontend: version picker in UploadScreen.

### TD-008 — BillingScreen bypasses SecureDocAPI abstraction
- **File:** `frontend/src/screens/BillingScreen.jsx`
- **Problem:** BillingScreen uses `fetch()` directly for all 3 billing endpoints instead of going through `window.SecureDocAPI`. This breaks the architecture pattern where all API communication routes through the centralized api.js layer (auth headers, error handling, _clearAndReload on 401).
- **Impact:** Billing 401 errors silently fail instead of triggering re-auth. Auth header injection is done manually. When api.js adds request middleware, BillingScreen is excluded.
- **Effort:** LOW. Add 3 billing methods to api.js, update BillingScreen to call them. ~1 hour.

### TD-009 — esbuild browser targets are 2020-era (chrome80, firefox78, safari14)
- **File:** `frontend/package.json` (esbuild config)
- **Problem:** Chrome 80 is from February 2020. The current browser market is Chrome 124+. Targeting Chrome 80 prevents using modern JS features (optional chaining, nullish coalescing, logical assignment, top-level await) in transpiled output. The build emits more verbose compatibility code than necessary.
- **Impact:** Larger bundle, slower parse time on modern browsers. No functional impact.
- **Effort:** LOW. Update target to `chrome110,firefox115,safari16` (~1 line in package.json). Verify bundle size decreases and no regressions.

### TD-010 — Rate limiting is in-process (slowapi), not Redis-backed
- **Files:** `backend/app/main.py`, all routers with `@limiter.limit()`
- **Problem:** slowapi stores rate limit counters in-process memory. Under horizontal scaling (multiple Railway instances), each instance has independent counters. A client that rotates between instances can exceed rate limits by a factor equal to the instance count.
- **Impact:** Rate limiting is ineffective under horizontal scaling. Not a current problem (single instance), but becomes a risk under load.
- **Effort:** MEDIUM. Requires Redis-backed slowapi configuration and a Redis instance in production.

### TD-011 — SSE notifications use in-process connection registry
- **File:** `backend/app/routers/notifications.py`
- **Problem:** The SSE connection registry is a Python `dict` in-process memory. Connections from different instances are invisible to each other. A "notify user X" call will only reach the connection on the instance that handles the SSE request.
- **Impact:** Real-time notifications don't work under horizontal scaling. Requires Redis pub/sub to broadcast across instances.
- **Effort:** MEDIUM. Add Redis pub/sub to the SSE path. Prerequisite to TD-010.

### TD-012 — LibreOffice is a single point of failure for DOCX/PPTX/XLSX conversion
- **File:** `backend/app/workers/pipeline/docx_pdf.py`, `pptx_pdf.py`, `xlsx_pdf.py`
- **Problem:** All Office document conversion uses LibreOffice via subprocess. If LibreOffice is not installed, all non-PDF uploads silently fail at the conversion step. There is no fallback.
- **Impact:** HIGH if the deployment environment doesn't have LibreOffice. Production Railway deployments must have LibreOffice installed in the container image.
- **Effort:** LOW for documentation (add to deployment checklist). MEDIUM for a proper alternative (python-docx2pdf or a cloud conversion API).

---

## P3 — Cleanup (Fix Opportunistically)

### TD-013 — ViewerScreen.jsx C/mono import ordering inconsistency (IH-004)
- **File:** `frontend/src/screens/ViewerScreen.jsx:12`
- **Problem:** `import { C, mono }` is at position 12 (after hook imports). All other screens put it at position 1. Cosmetic inconsistency.
- **Effort:** 30 seconds. Fix when ViewerScreen.jsx is opened for any substantive change.

### TD-014 — SAML domain field stored but not implemented
- **File:** `backend/app/models/org.py:saml_domain`
- **Problem:** `saml_domain` is stored in the Organization model. No SAML authentication flow exists. The field is orphaned.
- **Impact:** None functionally. Could confuse future engineers who see the field.
- **Effort:** LOW to document (add note to ORG model); HIGH if SAML is actually implemented.
- **Action:** Document in DECISION_LOG: "saml_domain field reserved for future SAML SSO; not implemented."

### TD-015 — Annotation export produces 3 separate CSV files instead of 1
- **Files:** `backend/app/routers/annotations.py`, `backend/app/routers/documents.py` (feedback routes)
- **Problem:** Users downloading annotation data must click 3 separate export buttons (feedback CSV, reviewer activity CSV, visual annotations CSV) and reconcile them manually.
- **Effort:** MEDIUM. Merge into a single combined export endpoint with format options. Low priority.

---

## Ranking Summary

| ID | Description | Priority | Effort | Fix Now |
|---|---|---|---|---|
| TD-001 | `link.url` javascript: guard | P0 | 10 min | YES — Sprint 4.3 |
| TD-002 | Credentials in git history | P0 | User action | YES — user-initiated |
| TD-003 | No notification on doc open | P1 | MEDIUM | Sprint 4.4 |
| TD-004 | 5 backend features invisible to users | P1 | HIGH | Sprint 4.4+ |
| TD-005 | api.js 769-line monolith | P1 | HIGH | Future sprint |
| TD-006 | Auth JWT in localStorage | P1 | HIGH | Monitor only |
| TD-007 | Version history no creation flow | P2 | MEDIUM | Sprint 4.4+ |
| TD-008 | BillingScreen bypasses SecureDocAPI | P2 | LOW | Next opportunity |
| TD-009 | Stale esbuild browser targets | P2 | LOW | Next opportunity |
| TD-010 | Rate limiting not Redis-backed | P2 | MEDIUM | Before scaling |
| TD-011 | SSE in-process connection registry | P2 | MEDIUM | Before scaling |
| TD-012 | LibreOffice single point of failure | P2 | LOW/doc | Add to deploy checklist |
| TD-013 | Import ordering inconsistency | P3 | Trivial | Next ViewerScreen touch |
| TD-014 | saml_domain field undocumented | P3 | LOW | Document in DECISION_LOG |
| TD-015 | 3 separate annotation exports | P3 | MEDIUM | Low priority |
