# Security Baseline
Sprint 4.0 — Phase 5
Date: 2026-06-18

Reference point for all future security reviews. Covers auth, session, upload, annotation, and admin surfaces as of post-Sprint 3.5 state (app.jsx 3,273 lines, 33 source files).

---

## Auth Surface

### Login Flow
- `LoginScreen` in app.jsx submits credentials via `window.SecureDocAPI.login(email, password)`.
- No client-side credential storage beyond the session token returned by the server.
- Password field is `type="password"` — never echoed in state.
- Login errors display server-returned message (no credential leakage — message is server-controlled).

### Token Model
- Access tokens stored in `sessionStorage` keyed as `securedoc_sess_${token}` (per-tab isolation).
- `publicToken` for viewer URLs passed via URL query param; handled by `useViewerSession`.
- `linkToken` used for thumbnail / TOC requests in PageThumb and TocSidebar — scoped per session.
- No `localStorage` token storage observed in the component layer.

| Finding | Severity | Status |
|---|---|---|
| SEC-AUTH-01: Password never stored or logged on client | — | PASS |
| SEC-AUTH-02: Session token in sessionStorage (tab-isolated) | LOW | ACCEPTED — sessionStorage is per-tab, expires on close; XSS risk is the relevant threat model |
| SEC-AUTH-03: publicToken passed via URL query param | LOW | ACCEPTED — by design for public viewer links; exposure risk is link sharing, not injection |

---

## Session Surface

### useViewerSession Hook
- Manages full session lifecycle: link resolution, gate probing, validation, re-auth on 401, DRM.
- `reinitRef.current` assigned in render body (not useEffect) — intentional: must close over current session/pendingToken on every render (documented in source).
- `_onValidatedRef` stored in a ref to avoid stale closure in effect deps — correct pattern.
- DRM event listeners: right-click, keyboard shortcuts, print, blur — all enforced client-side only.

### Session Re-Auth (401 Handling)
- On 401 response from any API call, `useViewerSession` calls `reinitRef.current()` to restart session flow.
- Gate error state (`gateError`) shown via `AccessGate` component.

### Blur / DRM
- `blurred` state set on window `blur` event — prevents screenshot when tab is backgrounded.
- All DRM controls (print disable, right-click disable, copy prevention) are client-side UX gates only — server-side enforcement is the security boundary.

| Finding | Severity | Status |
|---|---|---|
| SEC-SESS-01: DRM is client-side UX only — not a security boundary | MEDIUM | ACCEPTED — by design; documented. Server enforces access per API call. |
| SEC-SESS-02: `reinitRef` render-body assignment — not a bug, intentional | INFO | DOCUMENTED in source |
| SEC-SESS-03: sessionStorage cleared on tab close — no persistent token leakage | — | PASS |

---

## Upload Surface

### UploadDropZone
- Accepts: `.pdf,.docx,.doc,.txt,.md,.log` — MIME type enforced server-side.
- `<input type="file" accept="...">` — client-side filter only (UX gate, not security).
- Drag-and-drop `e.dataTransfer.files[0]` — file object passed to `simulate()` for processing.

### UploadScreen
- File size limit enforced via UI (`maxSize` check) — client-side UX only.
- Server must enforce both file type and file size limits independently.
- Upload progress tracked via polling (`MAX_POLL_ATTEMPTS = 150`, 2s interval = 5-minute cap).
- `retentionPolicy` selector — value sent to server; server must validate allowed values.
- `selectedGroupId` — sent with upload; server enforces group membership authorization.

| Finding | Severity | Status |
|---|---|---|
| SEC-UPL-01: File type validation is client-side only | MEDIUM | ACCEPTED — client filter is UX; server must validate (S-NEW-04 from Sprint 3.5) |
| SEC-UPL-02: File size limit is client-side only | MEDIUM | ACCEPTED — same as SEC-UPL-01 |
| SEC-UPL-03: retentionPolicy values not validated client-side | LOW | ACCEPTED — server validates allowed retention values |
| SEC-UPL-04: Upload session token passed correctly — no open upload endpoint | — | PASS — window.SecureDocAPI.upload requires valid session |

---

## Annotation Surface

### AnnotationLayer
- `isOwn` delete gate: `a.created_by === sessionPrefix` — client-side check only.
- Server enforces ownership in the `deleteAnnotation` API (R-016 — accepted).
- `onDraw` callback sends annotation data to server via `useAnnotations` hook.
- `onDelete` callback sends delete request to server via `useAnnotations` hook.
- Thread opening (`onOpenThread`) is unrestricted by ownership — any authenticated viewer can read threads (R-020 — accepted by design).
- Comment text capped at `maxLength={2000}` in `CommentPopup` — client-side limit.

### useAnnotations Hook
- Fetches annotation list via `window.SecureDocAPI.getAnnotations(session, page)`.
- Posts new annotations via `window.SecureDocAPI.createAnnotation(session, data)`.
- Deletes via `window.SecureDocAPI.deleteAnnotation(session, annotationId)`.
- All calls require valid `session` — no unauthenticated annotation access.

| Finding | Severity | Status |
|---|---|---|
| SEC-ANN-01: Delete gate is client-side only | LOW | ACCEPTED — server enforces ownership in deleteAnnotation API (R-016) |
| SEC-ANN-02: Comment maxLength=2000 is client-side only | LOW | OPEN — server must enforce independently (S-005 from Sprint 3.5) |
| SEC-ANN-03: Thread visibility unrestricted (any viewer can read) | INFO | ACCEPTED — by design (R-020) |
| SEC-ANN-04: `drawPoints` stale closure in _onMouseUp | INFO | PRE-EXISTING — functional risk, not security risk (R-015, R-017) |

---

## Admin Surface

### AccessScreen
- Group management, permission assignment, access log review.
- All API calls pass `session` — no admin endpoints callable without auth.
- `TabBtn` and `PermRow` (inline in app.jsx) are pure display components — no auth logic.
- Feedback pagination: client-side filter via `buildFeedbackFilters` — server returns all data for the session; filter is display-only.

### StorageScreen
- Shows storage usage and document list.
- All reads via `window.SecureDocAPI.*` with session — no unauthenticated access.

### AnalyticsScreen
- Reads usage metrics from server via session.
- Date range filters sent to server — server must validate date bounds.

| Finding | Severity | Status |
|---|---|---|
| SEC-ADM-01: All admin API calls require valid session | — | PASS |
| SEC-ADM-02: Client-side pagination/filtering in AccessScreen is display-only | INFO | ACCEPTED — server returns full authorized data set; client filters for display |
| SEC-ADM-03: Analytics date range not client-validated | LOW | ACCEPTED — server must validate; client sends raw user input |

---

## Cross-Cutting Findings

| ID | Finding | Severity | Status | Component |
|---|---|---|---|---|
| SEC-XC-01 | `window.SecureDocAPI.*` — all calls use session token | — | PASS | All screens |
| SEC-XC-02 | DocumentPicker shows only documents accessible to current session | MEDIUM | VERIFY — confirm server filters by session, not just doc ID | DocumentPicker + backend |
| SEC-XC-03 | No XSS vectors identified in JSX rendering — all dynamic content in `{}` (React escapes) | — | PASS | All components |
| SEC-XC-04 | `dangerouslySetInnerHTML` — not used anywhere in frontend source | — | PASS | All components |
| SEC-XC-05 | Inline event handlers use React synthetic events — no `eval()` or `Function()` calls | — | PASS | All components |

---

## Security Finding Summary by Severity

| Severity | Count | Open | Accepted |
|---|---|---|---|
| CRITICAL | 0 | 0 | 0 |
| HIGH | 0 | 0 | 0 |
| MEDIUM | 3 | 1 (SEC-XC-02) | 2 (SEC-SESS-01, SEC-UPL-01/02) |
| LOW | 5 | 1 (SEC-ANN-02) | 4 |
| INFO | 4 | 0 | 4 |

**No CRITICAL or HIGH findings.**

**Two open items requiring backend verification:**
1. SEC-XC-02 — DocumentPicker: confirm server filters documents by session
2. SEC-ANN-02 — Comment text length: confirm server enforces 2000-char limit

These are backend audit items, not frontend code changes.

---

## DRM Client-Side Posture

All DRM features (print disable, right-click disable, blur-on-background, watermark) are **client-side UX gates only**. This is the accepted architecture:

- A determined user with DevTools access can bypass all client-side DRM.
- The security model relies on server-side access controls, session expiry, and API authentication.
- Client-side DRM provides friction and UX signals, not cryptographic enforcement.

This posture is documented, accepted, and standard for browser-based document viewers.
