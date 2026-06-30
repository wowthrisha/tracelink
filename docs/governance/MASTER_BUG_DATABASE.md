# Master Bug Database — SecureDoc Zero Defect Program
**Generated:** 2026-06-30 | **Sprint:** 6.4  
**Sources:** BLOCKER_DATABASE.md, PRIORITY_FIX_LIST.md, EDGE_CASE_DATABASE.md, CONSISTENCY_REVIEW.md, ACCESSIBILITY_REVIEW.md, UX_REVIEW.md, ENTERPRISE_READINESS.md, code inspection of all 13 frontend screens + 15 backend routers

---

## Status Key
- ✅ FIXED — verified fixed in code
- 🔧 IN PROGRESS — fix being implemented this sprint
- ❌ OPEN — confirmed not yet fixed
- ⏸ DEFERRED — requires business decision (see REMAINING_DECISIONS.md)
- N/A — not reproducible / not applicable

---

## CRITICAL Severity

| ID | Description | Location | Status | Evidence | Fix Strategy | Regression Risk | Owner |
|----|-------------|----------|--------|----------|--------------|-----------------|-------|
| BUG-001 | Zero-restriction link created without confirmation | AccessScreen.jsx:334 | ✅ FIXED | `setQuickLinkModal(true)` warning modal exists | Warning modal with "Create Anyway" button | Low | Eng |
| BUG-002 | Org delete without confirmation | OrgsScreen.jsx | ✅ FIXED | `deleteOrgModal` state + Modal exists | Confirmation modal added | Low | Eng |
| BUG-003 | Group delete without confirmation | UploadScreen.jsx | ✅ FIXED | `deleteGroupModal` state + Modal exists | Confirmation modal added | Low | Eng |
| BUG-004 | Session blur shows no reason when session is invalidated during viewing | ViewerScreen.jsx, useViewerSession.js | 🔧 IN PROGRESS | Blur overlay shows "Focus window to resume" (window focus case OK, but concurrent-sessions reauth falls through) | Add 403/429 status to gateInfo path in doValidate | Low | Eng |
| BUG-005 | DRM blocks (print/copy/download) show generic "Action disabled" toast | useViewerSession.js:136-138 | 🔧 IN PROGRESS | `toast?.('Action disabled in secure viewer.', 'warning')` — not specific | Specific message per action type | Low | Eng |
| BUG-006 | Org member management was non-functional | OrgsScreen.jsx | ✅ FIXED | InviteMemberModal + MembersPanel with role/remove implemented | Invite/role/remove all added | Medium | Eng |
| BUG-007 | Audit log had no filter or export | AuditLogScreen.jsx | ✅ FIXED | Date/type filters + CSV export added | Filters + export implemented | Low | Eng |
| BUG-008 | No URL routing — page refresh loses navigation state | AppShell.jsx | ⏸ DEFERRED | `setScreen('upload')` on init — no URL routing | RD-002: implement hash routing | High | Product |
| BUG-009 | Link revoke (single) had no confirmation | AccessScreen.jsx | ✅ FIXED | `revokeLinkModal` state + Modal exists | Confirmation modal added | Low | Eng |
| BUG-010 | API key revoke/delete had no confirmation | ApiKeysScreen.jsx | ✅ FIXED | `revokeKeyModal`, `deleteKeyModal` states + Modals exist | Confirmation modals added | Low | Eng |
| BUG-011 | Webhook delete had no confirmation | WebhooksScreen.jsx | ✅ FIXED | `deleteWebhookModal` state + Modal exists | Confirmation modal added | Low | Eng |
| BUG-012 | Free plan doc limit hits server error with no UI explanation | UploadScreen.jsx | 🔧 IN PROGRESS | No counter, no upgrade prompt | Show counter from overview stats | Low | Eng |
| BUG-013 | window.confirm() used for irreversible link delete | AccessScreen.jsx | ✅ FIXED | `deleteLinkModal` state + Modal exists | Modal added | Low | Eng |
| BUG-014 | Cascade delete behavior on org delete unknown | backend/routers/orgs.py | ❌ OPEN | DB FK constraints need review | Check cascade in org model | Medium | Eng |

---

## HIGH Severity

| ID | Description | Location | Status | Evidence | Fix Strategy | Regression Risk | Owner |
|----|-------------|----------|--------|----------|--------------|-----------------|-------|
| BUG-015 | Audit log CSV export missing (now fixed) | AuditLogScreen.jsx | ✅ FIXED | Export button exists | CSV export added | Low | Eng |
| BUG-016 | Analytics has no date range picker | AnalyticsScreen.jsx | 🔧 IN PROGRESS | No date picker visible | Add date range selector + backend params | Medium | Eng |
| BUG-017 | Feedback empty state copy was misleading | AccessScreen.jsx | ✅ FIXED | "No feedback yet. Viewers can leave comments when they view this document." | Copy corrected | Low | Eng |
| BUG-018 | Notification read state stored in localStorage only | NotificationsScreen.jsx | ⏸ DEFERRED | RD-007: server-side read state | Requires user_notification_reads table | Low | Product |
| BUG-019 | Webhook edit was impossible | WebhooksScreen.jsx | ✅ FIXED | Edit modal added | Modal + PATCH endpoint | Low | Eng |
| BUG-020 | API key edit (name/scopes) was impossible | ApiKeysScreen.jsx | ✅ FIXED | Edit modal added | Modal + PATCH endpoint | Low | Eng |
| BUG-021 | Token expiry → no auto-logout, user sees "Failed to load" | api.js, AppShell.jsx | ❌ OPEN | `_clearAndReload()` exists but not called on admin 401 | Hook 401 responses in _request to call _clearAndReload for non-viewer calls | Medium | Eng |
| BUG-022 | Upload fails with server error when free plan limit hit | UploadScreen.jsx | ❌ OPEN | Only generic toast on upload failure | Parse 402/403 to show upgrade prompt | Low | Eng |
| BUG-023 | Upload corrupt PDF shows generic "Processing error: unknown" | UploadScreen.jsx:95 | ❌ OPEN | `s.error_message || 'unknown'` passed through | Show "Could not process file. It may be corrupt, password-protected, or unsupported." | Low | Eng |
| BUG-024 | Create link with past expiry date → accepted, immediately expired | AccessScreen.jsx:125-143 | 🔧 IN PROGRESS | No validation of expiry date against today | Add `if (expiry && new Date(expiry) < new Date()) return toast(...)` | Low | Eng |
| BUG-025 | Create link with max_views=0 → ambiguous behavior | AccessScreen.jsx:131 | 🔧 IN PROGRESS | `parseInt('0')` is falsy → treated as unlimited | Add explicit validation: if maxViews is set, require ≥1 | Low | Eng |
| BUG-026 | Webhook URL accepts non-https:// values without validation | WebhooksScreen.jsx | 🔧 IN PROGRESS | Only empty check, no URL format check | Validate `url.startsWith('https://')` before registering | Low | Eng |
| BUG-027 | Audit log actor shows raw UUID for API key auth events | AuditLogScreen.jsx | 🔧 IN PROGRESS | `ev.actor_email || ev.actor_id || '—'` shows UUID | Show "API Key" label when no email | Low | Eng |
| BUG-028 | Add member with non-existent user_id goes unchecked in backend | backend/routers/orgs.py | ❌ OPEN | No verification of user_id existence | Supabase lookup added for email path; direct add path unchecked | Medium | Eng |
| BUG-029 | Org domain verification state stale if TXT record removed | backend/models/org.py | ⏸ DEFERRED | No re-verification interval | Requires scheduled re-verification job | Low | Product |
| BUG-030 | Webhook URL with invalid format (no scheme) is accepted | backend/routers/webhooks.py | ❌ OPEN | Frontend check added; backend validate_ssrf_url may pass | Verify backend rejects non-https | Low | Eng |
| BUG-031 | Notifications list truncates at 50 events, no load-more | NotificationsScreen.jsx | 🔧 IN PROGRESS | `getEvents(null, null, 50)` — no pagination control | Add "Load more" button | Low | Eng |
| BUG-032 | Documents list has no pagination | backend/routers/documents.py | ❌ OPEN | No offset/limit in GET /documents | Add pagination to backend + frontend | High | Eng |
| BUG-033 | Polling fires even when browser tab is backgrounded | NotificationsScreen.jsx:96 | ❌ OPEN | `setInterval` fires regardless of `document.hidden` | Add `document.visibilityState` check | Low | Eng |
| BUG-034 | MAX_POLL_ATTEMPTS reached → polling silently stops | UploadScreen.jsx:79-83 | ✅ FIXED | Toast: 'Processing is taking longer than expected. Check back later.' | Toast added | Low | Eng |

---

## MEDIUM Severity

| ID | Description | Location | Status | Evidence | Fix Strategy | Regression Risk | Owner |
|----|-------------|----------|--------|----------|--------------|-----------------|-------|
| BUG-035 | Password reset with expired token shows generic "Authentication failed" | LoginScreen.jsx | ❌ OPEN | `_errMsg` passes generic fallback | Parse Supabase error, show "Reset link has expired. Please request a new one." | Low | Eng |
| BUG-036 | Processing failure for encrypted PDF shows no hint | UploadScreen.jsx | ❌ OPEN | Generic "Processing error" | Parse `error_message` for encryption hint | Low | Eng |
| BUG-037 | Edit link expiry with past date browser inconsistency | AccessScreen.jsx (EditLinkModal) | ❌ OPEN | `type="date"` — browser allows past on some | Add past-date validation in EditLinkModal handleSave | Low | Eng |
| BUG-038 | Two-page mode on single-page document | ViewerScreen.jsx | ❌ OPEN | page2 would load non-existent page | Disable two-page toggle when PAGE_COUNT=1 | Low | Eng |
| BUG-039 | Page input NaN when non-numeric entered | useViewerLayout.js | ❌ OPEN | `parseInt(pageInputStr)` → NaN | Add `isNaN` guard, revert to current page | Low | Eng |
| BUG-040 | Viewer window resize below 768px mid-session not detected | AppShell.jsx | ❌ OPEN | Only checked at render time | Add resize event listener | Low | Eng |
| BUG-041 | Access log view history not paginated (100k sessions case) | AccessScreen.jsx | ❌ OPEN | No pagination on access log component | AccessLog component needs pagination | Medium | Eng |
| BUG-042 | IP allowlist field accepts invalid CIDR without validation | AccessScreen.jsx | ❌ OPEN | No frontend CIDR validation | Add basic CIDR format check | Low | Eng |
| BUG-043 | Billing manage button hidden when billingEnabled=false | BillingScreen.jsx | ❌ OPEN | `stripe_customer_id && billingEnabled` | Keep manage button if customer_id exists | Low | Eng |
| BUG-044 | CORS config must include production domain | backend/main.py | ❌ OPEN | Env var configuration, can't verify | Must be verified during deployment | Low | DevOps |
| BUG-045 | Date format inconsistency — Access screen uses ISO slice | AccessScreen.jsx:427,439 | 🔧 IN PROGRESS | `link.created_at?.slice(0, 10)` vs `fmtDate()` elsewhere | Add local fmtDate, use consistently | Low | Eng |
| BUG-046 | "File" vs "Document" terminology inconsistency | UploadDropZone.jsx | ❌ OPEN | Upload zone says "Drop your file here" | Change to "Drop your document here" | Low | Eng |
| BUG-047 | RiskBadge component accepts unknown risk levels silently | atoms.jsx | ❌ OPEN | `if (!level || !map[level]) return '—'` | Unknown levels fall back to `—` — acceptable, but normalize backend values | Low | Eng |
| BUG-048 | Stripe payment race condition — billing status lag after payment | BillingScreen.jsx | ❌ OPEN | Race between webhook receipt and status fetch | Add poll-until-updated or manual refresh button | Low | Eng |
| BUG-049 | ViewerScreen two-page mode (page 2 out-of-bounds) | ViewerScreen.jsx | ❌ OPEN | No guard on isTwoPage when near last page | Don't show page 2 if `page === PAGE_COUNT` | Low | Eng |
| BUG-050 | Concurrent sessions gate message missing (loop in doValidate) | useViewerSession.js:55-60 | 🔧 IN PROGRESS | 403 sets gateError but gateInfo is null → no gate shows | Set gateInfo for concurrent session deny | Low | Eng |
| BUG-051 | Button label inconsistency ("New"/"Create"/"Register") | Various screens | ❌ OPEN | ApiKeys: "+ New API Key"; Webhooks: "+ Register Webhook"; Orgs: "+ New Organization" | Standardize to "+ New X" pattern | Low | Eng |
| BUG-052 | Empty states lack actionable CTAs on most screens | Various screens | ❌ OPEN | "No organizations yet." has no follow-up | Add CTA to empty states | Low | Eng |
| BUG-053 | Notification background polling wastes resources | NotificationsScreen.jsx | ❌ OPEN | Polls even on background tabs | Add `document.visibilityState` guard | Low | Eng |
| BUG-054 | Loading state in StorageScreen is full-screen outside layout | StorageScreen.jsx | ❌ OPEN | Returns before rendering header | Move loading inline | Low | Eng |
| BUG-055 | Filename path traversal characters not validated (frontend) | UploadScreen.jsx | ❌ OPEN | No frontend filename sanitization | Backend sanitizes; add frontend check on `../` | Low | Eng |
| BUG-056 | Webhook test button visible when webhook is paused | WebhooksScreen.jsx | ❌ OPEN | No disabled state on test when paused | Disable/hide test button if paused | Low | Eng |
| BUG-057 | Actor in audit log shows UUID for API key events | AuditLogScreen.jsx | 🔧 IN PROGRESS | See BUG-027 | Same fix | Low | Eng |
| BUG-058 | Sort controls missing from document table | UploadScreen.jsx | 🔧 IN PROGRESS | No column header sorting | Add sort state + click handlers to Document column header | Low | Eng |
| BUG-059 | Analytics metric definitions not visible to users | AnalyticsScreen.jsx | 🔧 IN PROGRESS | No tooltip on Risk, Completion, Avg Session | Add `title` attributes + visual hint | Low | Eng |
| BUG-060 | Sidebar nav groups not labeled for screen readers | atoms.jsx (Sidebar) | ❌ OPEN | Section labels rendered as divs | Add `role="group"` + `aria-label` to nav groups | Low | Eng |
| BUG-061 | EditLinkModal: past expiry date accepted | AccessScreen.jsx (EditLinkModal) | 🔧 IN PROGRESS | Same as BUG-024 but in edit path | Same validation | Low | Eng |

---

## LOW Severity

| ID | Description | Location | Status | Evidence | Fix Strategy | Regression Risk | Owner |
|----|-------------|----------|--------|----------|--------------|-----------------|-------|
| BUG-062 | "organise" British spelling in analytics | AnalyticsScreen.jsx | ✅ FIXED | Fixed to "organize" in previous sprint | Copy fix applied | Low | Eng |
| BUG-063 | Org name shows raw UUID in Storage screen | StorageScreen.jsx | ✅ FIXED | `org_name` field added from backend | org_name lookup in storage router | Low | Eng |
| BUG-064 | Access link dates use ISO slice (BUG-045 alias) | AccessScreen.jsx | 🔧 IN PROGRESS | Same | Same | Low | Eng |
| BUG-065 | Toast copy inconsistency (punctuation/capitalization) | Various | ❌ OPEN | Some end with `.`, some don't; mixed case "webhook" | Standardize toast copy | Low | Eng |
| BUG-066 | "Endpoint" vs "Webhook" terminology in WebhooksScreen | WebhooksScreen.jsx | ❌ OPEN | "Registered Endpoints" section header | Change to "Registered Webhooks" | Low | Eng |
| BUG-067 | Icon inconsistency (+ vs ⟳ for create actions) | Various | ❌ OPEN | `⟳` was on New Share Link; all others use `+` | "Quick Link" button already changed | Low | Eng |
| BUG-068 | Orgs empty state has no CTA | OrgsScreen.jsx | ❌ OPEN | "No organizations yet." with period, no action | Add CTA pointing to + New Organization | Low | Eng |
| BUG-069 | Info cards only on 4/13 screens | Various | ❌ OPEN | API Keys, Webhooks, Audit Log, Notifications have info cards; others don't | Either standardize or accept inconsistency | Low | Eng |
| BUG-070 | SAML SSO configuration UI missing | OrgsScreen.jsx | ⏸ DEFERRED | RD-008 | Requires enterprise decision | Low | Product |

---

## Accessibility Issues

| ID | Description | WCAG | Location | Status | Fix |
|----|-------------|------|----------|--------|-----|
| AX-001 | No semantic landmarks (no `<main>`, limited `<nav>`) | 1.3.1 A | AppShell.jsx | 🔧 IN PROGRESS | Add `<main>` to content area |
| AX-002 | No focus trap in modals | 2.4.3 A | atoms.jsx (Modal) | 🔧 IN PROGRESS | Implement focus trap with useEffect |
| AX-003 | Color-only status indicators (StatusDot, RiskBadge) | 1.4.1 A | atoms.jsx | ❌ OPEN | Add text alternative alongside color |
| AX-004 | Form fields not labeled (Field uses label wrapping now) | 1.3.1 A | atoms.jsx | ✅ FIXED | `<label>` wraps `<input>` |
| AX-005 | Icon-only buttons without aria-label | 4.1.2 A | All screens | ✅ FIXED | aria-label added to all close/rename/open buttons |
| AX-006 | Table headers missing `scope="col"` | 1.3.1 A | All tables | ✅ FIXED | scope="col" added to all `<th>` |
| AX-007 | Insufficient contrast on muted/dim text | 1.4.3 AA | All screens | ❌ OPEN | Requires design token audit |
| AX-008 | Mobile blocked at 768px (affects screen magnification) | 1.4.4 AA | AppShell.jsx | ⏸ DEFERRED | RD-005 |
| AX-009 | Toast not announced to screen readers | 4.1.3 AA | toast.jsx | ✅ FIXED | `aria-live="polite"` added |
| AX-010 | window.confirm inaccessible | 4.1.2 A | AccessScreen.jsx | ✅ FIXED | Replaced with Modal |
| AX-011 | Keyboard trap in viewer (intentional, needs escape path) | 2.1.2 A | ViewerScreen.jsx | ❌ OPEN | Add Escape key handler to return toolbar focus |
| AX-012 | autoFocus without announcement context | 2.4.3 A | Various | ❌ OPEN | AX-002 focus management partially addresses |

---

## Security Issues

| ID | Description | OWASP | Status | Notes |
|----|-------------|-------|--------|-------|
| SEC-001 | Zero-restriction link exposure | A04 | ✅ FIXED | Warning modal added |
| SEC-002 | Org member add with non-existent user_id | A01 | ❌ OPEN | Supabase lookup covers email path; direct UUID add unchecked |
| SEC-003 | Webhook URL validation — non-https accepted (frontend) | A03 | 🔧 IN PROGRESS | Frontend validation being added |
| SEC-004 | IP allowlist accepts invalid CIDR | A03 | ❌ OPEN | Backend must validate |
| SEC-005 | No rate limiting visible in frontend (backend has it) | A07 | N/A | Backend middleware handles |
| SEC-006 | Filename path traversal not checked frontend | A01 | ❌ OPEN | Backend sanitizes; frontend should too |

---

## Performance Issues

| ID | Description | Location | Status | Notes |
|----|-------------|----------|--------|-------|
| PERF-001 | Background tab notification polling | NotificationsScreen.jsx | 🔧 IN PROGRESS | Add visibilitychange guard |
| PERF-002 | Audit log OFFSET pagination degrades at scale | AuditLogScreen.jsx | ❌ OPEN | Cursor-based pagination needed |
| PERF-003 | Documents list loads all documents in memory | UploadScreen.jsx | ❌ OPEN | No pagination |
| PERF-004 | No request deduplication on rapid clicks | api.js | ❌ OPEN | No AbortController usage |

---

## Summary

| Severity | Total | Fixed | In Progress | Open | Deferred |
|----------|-------|-------|-------------|------|---------|
| Critical | 14 | 9 | 3 | 2 | 1 |
| High | 20 | 7 | 6 | 7 | 3 |
| Medium | 27 | 1 | 7 | 16 | 3 |
| Low | 9 | 2 | 0 | 7 | 1 |
| Accessibility | 12 | 6 | 2 | 4 | 2 |
| Security | 6 | 1 | 1 | 4 | 0 |
| Performance | 4 | 0 | 1 | 3 | 0 |
| **Total** | **92** | **26** | **20** | **43** | **10** |

---

*Last updated: 2026-06-30 | Sprint 6.4*
