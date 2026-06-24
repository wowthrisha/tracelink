# UI Certification Report
Sprint 4.4 — Production Certification Sprint
Date: 2026-06-22
Auditor role: QA Lead + Product Manager
Method: Direct source reading of all 6 screens + shared components. No assumptions.

Pass/Fail criteria: A UI component is PASS if every user-visible action maps to a real API call or a legitimate client-side operation. A UI component is FAIL if any user-visible action triggers no effect or a misleading effect.

---

## Screen 1 — LoginScreen.jsx (234 lines)

**File:** `frontend/src/screens/LoginScreen.jsx`

| Component | Action | Maps To | Status |
|---|---|---|---|
| Login form | Submit | `supabase.auth.signInWithPassword()` | PASS |
| Signup form | Submit | `supabase.auth.signUp()` | PASS |
| Forgot password | Submit | `supabase.auth.resetPasswordForEmail()` | PASS |
| Reset password | Submit | `supabase.auth.updateUser()` | PASS |
| Mode switcher (login ↔ signup ↔ forgot) | Click | Client state change | PASS |
| Password reset auto-detect | URL hash `type=recovery` + `access_token` | Switches to reset mode | PASS |

**Defects:** None found.
**Certification: PASS**

**Note:** Password minimum-length validation (6 chars) enforced frontend-only at `LoginScreen.jsx:145`. Backend Supabase policy may differ. Minor inconsistency risk.

---

## Screen 2 — UploadScreen.jsx (359 lines)

**File:** `frontend/src/screens/UploadScreen.jsx`

| Component | Action | Maps To | Status |
|---|---|---|---|
| Upload button | Click → file picker | `window.SecureDocAPI.uploadDocument()` | PASS |
| Drag-drop zone | Drop file | `window.SecureDocAPI.uploadDocument()` | PASS |
| Processing status | Auto-poll | `window.SecureDocAPI.pollDocumentStatus()` every 2s | PASS |
| Delete document | Confirm + click | `window.SecureDocAPI.deleteDocument()` | PASS |
| Reprocess document | Click | `window.SecureDocAPI.reprocessDocument()` | PASS |
| Create group | Submit | `window.SecureDocAPI.createGroup()` | PASS |
| Rename group | Submit | `window.SecureDocAPI.updateGroup()` | PASS |
| Delete group | Confirm + click | `window.SecureDocAPI.deleteGroup()` | PASS |
| Assign to group | Drag or select | `window.SecureDocAPI.assignDocumentsToGroup()` | PASS |
| Remove from group | Click × | `window.SecureDocAPI.removeDocumentFromGroup()` | PASS |
| Document search | Type in search field | Client-side filter (local state) | PASS |
| Stats grid (4 cards) | Display | Populated from `getAnalyticsOverview()` | PASS |

**Defects:**
- **UI-001 LOW** — Upload button label reads "⊕ Upload PDF" but file type accept includes PDF, DOCX, DOC, TXT, MD, LOG. Label misleads users into thinking only PDFs are accepted.
  - File: `UploadScreen.jsx` (button label)
  - Severity: LOW
  - Recommendation: Change label to "⊕ Upload Document" or "⊕ Upload File"

**Certification: PASS (with UI-001 note)**

---

## Screen 3 — AccessScreen.jsx (714 lines)

**File:** `frontend/src/screens/AccessScreen.jsx`

### Tab 1 — Policy

| Component | Action | Maps To | Status |
|---|---|---|---|
| Password field | Edit + save | `PATCH /api/links/{id}` via `savePolicy` | PASS |
| Allowed emails textarea | Edit + save | `PATCH /api/links/{id}` | PASS |
| Allowed domains field | Edit + save | `PATCH /api/links/{id}` | PASS |
| Expiry date picker | Edit + save | `PATCH /api/links/{id}` | PASS |
| Max views input | Edit + save | `PATCH /api/links/{id}` | PASS |
| Max concurrent sessions | Edit + save | `PATCH /api/links/{id}` | PASS |
| IP allowlist | Edit + save | `PATCH /api/links/{id}` | PASS |
| 7 permission toggles | Toggle + save | `PATCH /api/links/{id}` | PASS |

### Tab 2 — Share Link

| Component | Action | Maps To | Status |
|---|---|---|---|
| Copy link button | Click | Clipboard write (client-side) | PASS |
| Open in new tab | Click | Window.open (client-side) | PASS |
| Revoke link | Confirm + click | `DELETE /api/links/{id}` | PASS |
| Embed code display | View | Client-side `<iframe>` template | PASS |
| **"⟳ New Link" button** | **Click** | **ONLY: `toast('New link generated', 'success')`** | **FAIL** |

### Tab 3 — Access Log

| Component | Action | Maps To | Status |
|---|---|---|---|
| Access log table | Display | `GET /api/analytics/events` | PASS |
| Filter controls | Change | API re-fetch with filters | PASS |

### Tab 4 — Feedback

| Component | Action | Maps To | Status |
|---|---|---|---|
| Feedback list | Display | `GET /api/feedback` | PASS |
| Status filter | Change | API re-fetch | PASS |
| Reviewer filter | Change | API re-fetch | PASS |
| Page filter | Change | API re-fetch | PASS |
| Date range filter | Change | API re-fetch | PASS |
| Text search | Type | API re-fetch | PASS |
| Inline reply | Submit | `PATCH /api/feedback/{id}` | PASS |
| Export dropdown | Click | UNVERIFIED — export method not confirmed in source | UNVERIFIED |

### Tab 5 — Annotations

| Component | Action | Maps To | Status |
|---|---|---|---|
| Annotations list | Display | `GET /api/annotations` | PASS |
| Type filter | Change | Client-side or re-fetch | PASS |
| Refresh | Click | Re-fetch | PASS |
| Export CSV | Click | UNVERIFIED — export call not confirmed in source | UNVERIFIED |

**Defects:**
- **UI-002 HIGH — CRITICAL DEFECT** — "⟳ New Link" button is non-functional
  - File: `AccessScreen.jsx:307`
  - Function: `onClick` handler for "⟳ New Link" button
  - Endpoint: NONE called
  - Severity: HIGH
  - Root cause: Button handler calls `toast('New link generated', 'success')` with no API call
  - Impact: User believes a new share link has been generated. No link is created. This is a silent failure with false-positive feedback — the worst possible failure mode for a security feature.
  - Recommendation: Wire to `window.SecureDocAPI.createLink(selectedDocId)` and reload the links list. Requires determining what the "create link" API call parameters are from the backend links router.

**Certification: FAIL — UI-002 is a critical defect**

---

## Screen 4 — ViewerScreen.jsx (872 lines)

**File:** `frontend/src/screens/ViewerScreen.jsx`

| Component | Action | Maps To | Status |
|---|---|---|---|
| Page render | Load page | `GET /api/viewer/page/{token}/{page}` | PASS |
| Page navigation | Previous/Next/Jump | Client state → page re-fetch | PASS |
| Zoom in/out | Click or pinch | Client-side zoom math (ZOOM_MIN/ZOOM_MAX) | PASS |
| Fit width / fit page | Toggle | Client-side layout recalculation | PASS |
| Rotate page | Click | Client-side rotation state | PASS |
| Annotation (highlight/draw) | Draw on page | `POST /api/annotations` | PASS |
| Annotation thread | Click annotation | `GET /api/annotations/{id}/thread` | PASS |
| Delete annotation | Click delete | `DELETE /api/annotations/{id}` | PASS |
| Bookmark page | Click bookmark | `POST/DELETE /api/viewer/bookmark` | PASS |
| TOC panel | Toggle | `GET /api/viewer/toc/{token}` | PASS |
| Search panel | Toggle + search | Client-side text sidecar search | PASS |
| Links panel | Toggle | Client-side (link data from session) | PASS (but see LinksPanel) |
| Download | Click | `GET /api/viewer/download/{token}` | PASS |
| Insights panel | Toggle | `GET /api/analytics/events` | PASS |
| Info overlay | Toggle | Client-side (session data) | PASS |
| Laser pointer | Toggle | Client-side canvas overlay | PASS |
| Magnifier | Toggle | Client-side canvas zoom | PASS |
| Text document rendering | Display | `useTextLoader` (text sidecar) | PASS |
| Page thumbnails | Display | `GET /api/viewer/thumb/{token}/{page}` | PASS |

**Defects (via LinksPanel.jsx):**
- **UI-003 HIGH — SECURITY DEFECT** — LinksPanel renders links without javascript: protocol guard
  - File: `LinksPanel.jsx:79`
  - Function: link `<a>` element href
  - Endpoint: None (client-side render from link data in session)
  - Severity: HIGH
  - Root cause: `<a href={link.url} target="_blank" rel="noopener noreferrer">` — `link.url` is extracted from PDF annotations by the backend pipeline. A PDF containing an annotation with `javascript:alert(1)` as its URL would produce a clickable link in the panel. React 18 issues a console warning for `javascript:` hrefs but does NOT block them.
  - Impact: If a malicious document is uploaded (or a trusted document is crafted with javascript: annotation URLs), any viewer who clicks the link in the panel executes arbitrary JavaScript.
  - Recommendation: Add protocol guard before rendering: `const safeUrl = /^https?:\/\//i.test(link.url) ? link.url : '#'; <a href={safeUrl} ...>`

**Certification: PASS with HIGH-severity security defect (UI-003) in LinksPanel component**

---

## Screen 5 — AnalyticsScreen.jsx (401 lines)

**File:** `frontend/src/screens/AnalyticsScreen.jsx`

| Component | Action | Maps To | Status |
|---|---|---|---|
| Overview tab | Display | `GET /api/analytics/overview` | PASS |
| By Document tab | Display | `GET /api/analytics/documents` | PASS |
| By Group tab | Display | `GET /api/analytics/groups` | PASS |
| Document row click → heatmap | Click | `GET /api/analytics/page-heatmap?document_id={id}` | PASS |
| Range selector (24h/7d/30d/90d) | Change | Sets `range` state — NOT forwarded to API | DEFECT |
| **"↓ Export CSV" button** | **Click** | **ONLY: `toast('Export started...')`** | **FAIL** |

**Defects:**
- **UI-004 MEDIUM** — Range selector state never forwarded to API
  - File: `AnalyticsScreen.jsx:65` (`loadAll` function), and `loadDocAnalytics`, `loadGroupAnalytics`
  - Endpoint: `GET /api/analytics/overview`, `GET /api/analytics/documents`, `GET /api/analytics/groups`
  - Severity: MEDIUM
  - Root cause: `range` state is set by the range picker but the `loadAll`/`loadDocAnalytics`/`loadGroupAnalytics` calls do not include `?range=` query parameter
  - Impact: Analytics data always shows full history regardless of range selected. Range UI gives false impression of filtering.
  - Recommendation: Pass `range` as query param to each analytics API call. Backend must accept a `range` query parameter (unverified — check analytics router before implementing).

- **UI-005 HIGH — CRITICAL DEFECT** — Export CSV button is non-functional
  - File: `AnalyticsScreen.jsx:82`
  - Function: Export CSV button `onClick`
  - Endpoint: NONE called
  - Severity: HIGH
  - Root cause: Handler calls `toast('Export started — CSV ready in a moment', 'success')` only. No API call or download triggered.
  - Impact: User believes an export is being prepared. Nothing happens. CSV never arrives. This is a false-positive feedback loop — a shipped promise that has never been kept.
  - Recommendation: Either wire to a real export endpoint (if one exists), or remove the button and toast until an endpoint is built.

**Certification: FAIL — UI-004 (MEDIUM) and UI-005 (HIGH) defects**

---

## Screen 6 — BillingScreen.jsx (196 lines)

**File:** `frontend/src/screens/BillingScreen.jsx`

| Component | Action | Maps To | Status |
|---|---|---|---|
| Billing status display | Load | `GET /api/billing/status` via direct `fetch()` | PASS (works) |
| Upgrade to Pro | Click | `POST /api/billing/checkout` via direct `fetch()` → redirect | PASS (works) |
| Manage subscription | Click | `POST /api/billing/portal` via direct `fetch()` → redirect | PASS (works) |
| Billing success state | Detect | `?billing=success` query param detection | PASS |
| No-config graceful state | Display | 503 response from endpoint | PASS |

**Defects:**
- **UI-006 MEDIUM** — BillingScreen bypasses SecureDocAPI middleware
  - File: `BillingScreen.jsx:55`, `BillingScreen.jsx:90`, `BillingScreen.jsx:120`
  - Function: `loadBillingStatus`, `handleUpgrade`, `handlePortal` — all use `fetch('/api/billing/...')` with manual `authHeaders()` helper
  - Endpoint: `GET /api/billing/status`, `POST /api/billing/checkout`, `POST /api/billing/portal`
  - Severity: MEDIUM
  - Root cause: BillingScreen defines its own `authHeaders()` function that reads `localStorage.securedoc_token` directly, bypassing `window.SecureDocAPI` which has centralized 401 handling, error formatting, and future auth middleware
  - Impact: A 401 from a billing endpoint will not trigger automatic re-login. User may see a raw JSON error instead of being redirected to the login screen. Technical debt: any future change to auth headers requires updating two code paths.
  - Recommendation: Add billing API methods to `window.SecureDocAPI` in `api.js` and refactor BillingScreen to use them.

**Certification: PASS with MEDIUM-severity architectural defect (UI-006)**

---

## Screen 7 — StorageScreen.jsx (162 lines)

**File:** `frontend/src/screens/StorageScreen.jsx`

| Component | Action | Maps To | Status |
|---|---|---|---|
| Storage dashboard | Display | `GET /api/storage/dashboard` via `getStorageDashboard()` | PASS |
| Storage forecast | Display | `GET /api/storage/forecast` via `getStorageForecast()` | PASS |
| Retention dropdown | Change + save | `PATCH /api/storage/retention` via `updateRetention()` | PASS |
| Per-org breakdown | Display | Conditional on `dashboard.by_org.length > 1` | PASS |
| Lifecycle state badges | Display | From document data in storage response | PASS |

**Defects:** None found.
**Certification: PASS**

---

## Shared Components

### AppShell.jsx

| Component | Action | Maps To | Status |
|---|---|---|---|
| Sidebar navigation | Click | Sets `screen` state → renders correct Screen | PASS |
| Auth guard | Load | Reads `securedoc_token` from localStorage | PASS |
| Screen routing | Nav item click | Switch-style render | PASS |
| SSE Notifications | None | EventSource not wired | NOT IMPLEMENTED |

**Defects:**
- **UI-007 HIGH** — No SSE EventSource subscription in AppShell
  - File: `AppShell.jsx`
  - Severity: HIGH (business value, not crash)
  - Root cause: No `useEffect` containing `new EventSource(...)` anywhere in AppShell
  - Impact: `document.processed` events published by the backend (tasks.py:200) are never received. ToastProvider infrastructure is ready. Users never see a "document ready" notification after upload.
  - Recommendation: Add `useNotificationStream(token)` hook to AppShell (see `HIDDEN_FEATURE_EXPOSURE_PLAN.md`). Auth blocker: SSE auth requires query param token since EventSource cannot send Authorization headers.

### LinksPanel.jsx

See UI-003 above (HIGH security defect).

---

## Defect Register

| ID | Screen | Severity | Title | Action Required |
|---|---|---|---|---|
| UI-001 | UploadScreen | LOW | Upload button label says "PDF" but accepts 6 file types | Rename button label |
| UI-002 | AccessScreen | HIGH | "⟳ New Link" is non-functional stub | Wire to createLink API |
| UI-003 | LinksPanel | HIGH | javascript: href XSS vector | Add protocol guard |
| UI-004 | AnalyticsScreen | MEDIUM | Range selector not forwarded to API | Pass range as query param |
| UI-005 | AnalyticsScreen | HIGH | "↓ Export CSV" is non-functional stub | Wire to export API or remove |
| UI-006 | BillingScreen | MEDIUM | Direct fetch() bypasses SecureDocAPI | Move to SecureDocAPI |
| UI-007 | AppShell | HIGH | No SSE consumer | Wire useNotificationStream |

**Must fix before production certification: UI-002, UI-003, UI-005**
**Fix in next sprint: UI-004, UI-006, UI-007**
**Cosmetic / low priority: UI-001**
