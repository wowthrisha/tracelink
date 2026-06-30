> **MIGRATED** — This file has been migrated to `docs/governance/RISK_REGISTER.md` (2026-06-22, A-145). Append new entries to the governance location under the FE-R- namespace. This copy preserved for path compatibility.

# Risk Register
SecureDoc Frontend — Autonomous Engineering Framework
Append-only log. Do not remove or modify existing entries.

---

## Sprint 3.3 — Phase 0 (Initial Assessment)

Date: 2026-06-15

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-001 | C/mono token object | 47 C keys used across all components; inline definition = single point of breakage | MEDIUM | RESOLVED | Extracted to `constants/tokens.js`; all references updated |
| R-002 | toast.jsx | Had private `_TC` color subset that could diverge from C | LOW | RESOLVED | Replaced with `import { C } from '../constants/tokens.js'` |
| R-003 | PageThumb semaphore | `_THUMB_CONCURRENCY`/`_thumbQueue` module-level state must colocate with PageThumb | MEDIUM | RESOLVED | Both moved to `components/PageThumb.jsx` |
| R-004 | MockPage | Dead component — defined but never called | LOW | RESOLVED | Deleted |
| R-005 | WatermarkOverlay | Dead component — defined but never called | LOW | RESOLVED | Deleted |
| R-006 | AnnotationLayer | Complex draw state machine; SVG mouse event system; 7 renderers | MEDIUM | DEFERRED | Phase 4 readiness review completed; scheduled for Sprint 3.5 |
| R-007 | app.jsx LOC | 5,085 lines in single file — tooling limits, merge conflicts, bundle cost | HIGH | IN PROGRESS | Sprint 3.3 reduced to 4,289; Sprint 3.4 reduced to 3,687 |

---

## Sprint 3.4 — Phase 0 (Assessment before extraction)

Date: 2026-06-17

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-008 | atoms.jsx | 14 atoms + label() + NAV_SECTIONS in single file; label() used at 8+ call sites in app.jsx | MEDIUM | RESOLVED | Exported label() from atoms.jsx; imported in app.jsx import block |
| R-009 | NAV_SECTIONS constant | Module-level const used only by Sidebar; incorrect export would expose internal state | LOW | RESOLVED | Kept as module-private (not exported) in atoms.jsx |
| R-010 | AccessGate emoji | Original used surrogate pair escapes `🔐` | LOW | RESOLVED | Replaced with direct emoji literals — same visual output |
| R-011 | ViewerInfoPanel React.useState | Used `React.useState` directly instead of destructured `useState` | LOW | RESOLVED | Added `const { useState } = React;` to extracted file |
| R-012 | commentDraft prop | AnnotationLayer declares but does not use `commentDraft` — used by sibling CommentPopup | INFO | DOCUMENTED | Documented in ANNOTATION_LAYER_READINESS_REVIEW.md; no change needed |
| R-013 | mono prop | AnnotationLayer declares but does not use `mono` in body | INFO | DOCUMENTED | Keep in signature for caller compatibility |
| R-014 | Arrow marker ID collision | `id="ah-${a.id}"` — unique per annotation but document-scoped; multiple AnnotationLayer instances could collide | LOW | DOCUMENTED | Current app uses one instance per page; not a problem now |
| R-015 | drawPoints stale closure | `_onMouseUp` reads `drawPoints` state directly (not functional update) — pre-existing stale-closure risk | LOW | DOCUMENTED | Pre-existing; document in extracted file; not introduced by extraction |

---

## Sprint 3.5 — Phase 0 (Assessment before extraction)

Date: 2026-06-18

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-016 | AnnotationLayer | `isOwn` delete gate is client-side only | LOW | ACCEPTED | Server enforces ownership in deleteAnnotation API; client gate is UX-only |
| R-017 | AnnotationLayer | `drawPoints` stale closure in `_onMouseUp` | LOW | DOCUMENTED | Pre-existing from Sprint 3.4 review; not introduced by extraction |
| R-018 | UploadDropZone | `fileRef` passed as prop — `fileRef.current.click()` in UploadScreen Header button must still work | LOW | RESOLVED | React ref semantics: ref assigned to `<input>` in child, DOM node available in parent via same ref object |
| R-019 | DocumentPicker docblock comment | Unclosed `/*` comment block left by Python walk-back heuristic | HIGH | RESOLVED | Orphaned lines detected and deleted (A-048); build error fixed same sprint |
| R-020 | Comment/sticky_note thread | Thread open unrestricted (`!activeTool` only, no ownership check) | INFO | ACCEPTED | By design — all viewers can read threads; reply/write auth server-enforced |

---

## Sprint 4.0 — Phase 0 (Baseline audit)

Date: 2026-06-18

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-021 | `].md` (securedoc root) | Malformed filename — 31KB content (Pilot Deployment Guide) is untracked and could be lost | LOW | OPEN | User must rename to `PILOT_DEPLOYMENT_GUIDE.md` and commit; content not duplicated elsewhere |
| R-022 | `securedoc/200`, `securedoc/404` | Empty shell-accident files at repo root | INFO | RESOLVED | Deleted (A-055, A-056) |
| R-023 | `useViewerSession.js` uncommitted change | `toast` param removed from hook signature — possible API contract change | LOW | RESOLVED | Verified caller (app.jsx) never passed `toast`; change is safe (D-016) |
| R-024 | No `frontend/.gitignore` | Build artifact policy relies on root-level `.gitignore` with `!frontend/dist/` exception | INFO | ACCEPTED | Root .gitignore is correct and complete; no change needed (D-014) |
| R-025 | Two `docs/engineering/` directories | `frontend/docs/engineering/` (current) and `securedoc/docs/engineering/` (prior sessions) could cause confusion about canonical docs location | LOW | OPEN | Document clearly which is current; future: consider consolidating to one location |
| R-026 | `].md` documentation gap | TraceView Pilot Deployment Guide content may be the only copy of that operational document | MEDIUM | OPEN | User must decide: rename+commit or verify it's duplicated elsewhere before any cleanup |

---

## Sprint 4.1 — Phase 0 (Assessment before extraction)

Date: 2026-06-18

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-027 | `PermRow` | Defined at line 1973 but never called anywhere — dead code. AccessScreen uses its own inline permission toggle grid (lines 1521–1541). | INFO | RESOLVED | Delete PermRow from app.jsx; do NOT create PermRow.jsx (D-017) |
| R-028 | `SparkChart` | SVG gradient `id="aGrad"` is document-scoped. If multiple SparkChart instances render simultaneously, the gradient would collide. | LOW | DOCUMENTED | Current usage: only 1 SparkChart per page (overview tab only). Acceptable for now. Future: parameterise ID if needed. |
| R-029 | `AccessLog` | Has own API call (`window.SecureDocAPI.getEvents`) and context dep (`useToast`). Not a pure prop-receiver component. | MEDIUM | DEFERRED | Do not extract AccessLog in Sprint 4.1. Requires full state/API boundary analysis. Deferred to Sprint 4.2 screen extraction phase. |
| R-030 | `buildFeedbackFilters` | Called at 2 sites in AccessScreen (lines 1319, 1648). Moving to `utils/feedback.js` requires import to replace both closure references. | LOW | RESOLVED | Both call sites in same screen function — adding import at module top covers both |

---

## Sprint 4.2A — Phase 0 (Assessment before extraction)

Date: 2026-06-18

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-031 | `AppShell` circular dep risk | App() references inline screens (UploadScreen, ViewerScreen, AccessScreen, AnalyticsScreen) still in app.jsx — extracting AppShell naively creates circular import | MEDIUM | RESOLVED | AppShell receives the 4 still-inline screens as props (`{ UploadScreen, ViewerScreen, AccessScreen, AnalyticsScreen }`). Props replaced by imports in Sprint 4.2B+ as each screen is extracted (D-020) |
| R-032 | `parseJwtEmail` ownership | Currently module-level between StorageScreen and LoginScreen (line 2562). App uses it at line 3008. | LOW | RESOLVED | Move to AppShell.jsx alongside App state logic (D-021) |
| R-033 | `LoginScreen` localStorage write | LoginScreen writes `securedoc_token` to localStorage on successful auth. No toast — uses local error/info state. | INFO | DOCUMENTED | Same behavior preserved in extracted file; no change to localStorage key |
| R-034 | `BillingScreen` raw fetch + authHeaders | BillingScreen uses raw `fetch()` with inner `authHeaders()` function (reads localStorage). Not window.SecureDocAPI. | LOW | RESOLVED | authHeaders() moves into BillingScreen.jsx as a module-level function (D-022) |
| R-035 | `StorageScreen` inner helpers | fmtBytes() and lifecycleBadge() are inner functions of StorageScreen. Both must migrate with the screen. | LOW | RESOLVED | Both move to StorageScreen.jsx as module-level functions (D-023) |

---

## Sprint 4.2B — Phase 0 (Assessment before extraction)

Date: 2026-06-22

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-036 | `AccessLog` — no pagination, no filtering | Sprint plan mentioned "pagination" and "filtering" — actual code has neither. AccessLog fetches last 50 events via `getEvents(docId, 50)` and shows a Refresh button only. | INFO | DOCUMENTED | Extracted exactly as-is. No pagination or filter UI to preserve. Sprint plan was overcautious. |
| R-037 | `AccessLog` `label` import | AccessLog uses `label(9)` at line 1982 for TH styles. Must import `label` from atoms.jsx. | LOW | RESOLVED | Import `{ label, SectionLabel, Chip, Btn, Card, RiskBadge }` from atoms.jsx in AccessLog.jsx |
| R-038 | `AnalyticsScreen` `label` parameter shadows import | AnalyticsScreen has `[id, label]` destructuring in a .map() callback (tab list), shadowing the imported `label()` function. No conflict: `label(9)` calls are always outside the shadowed scope. | LOW | DOCUMENTED | Safe as-is. No rename needed. |
| R-039 | `AnalyticsScreen` missing `useCallback` | AnalyticsScreen uses only `useState` + `useEffect`. `useCallback` is NOT used (only AccessLog uses it). | INFO | DOCUMENTED | Do not include `useCallback` in AnalyticsScreen.jsx React destructure. |
| R-040 | `AppShell` prop → import migration | After AnalyticsScreen extraction, AppShell must be updated: remove `AnalyticsScreen` from props signature, add direct import. app.jsx render call must also remove the prop. Doing these two changes atomically is critical. | MEDIUM | RESOLVED | Update AppShell.jsx and app.jsx render call in same edit pass before build (Phase 3). |

---

## Sprint 4.2C — Phase 0 (Assessment before extraction)

Date: 2026-06-22

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-041 | `UploadScreen` pollRef interval leak | `useEffect(() => () => clearInterval(pollRef.current), [])` — cleanup effect MUST migrate with the screen. Without it, polling continues after unmount. | HIGH | RESOLVED | Copied verbatim into UploadScreen.jsx (verified in file) |
| R-042 | `UploadScreen` fileRef dual ownership | `fileRef` is passed as prop to `<UploadDropZone fileRef={fileRef} />` AND used directly in Header `onClick={() => fileRef.current.click()}`. Both wired to same ref object. | MEDIUM | RESOLVED | Same ref object — React semantics unchanged in extracted file |
| R-043 | `UploadScreen` inner helpers | `_detectFileType()` and `_isDocType()` are inner helpers + `MAX_POLL_ATTEMPTS` is an inner const — all promoted to module-level in extracted file since none close over state | LOW | RESOLVED | Promoted to module-level in UploadScreen.jsx |
| R-044 | `UploadScreen` 12 API endpoints | getDocuments, getAnalyticsOverview, getGroups, uploadDocument, pollDocumentStatus, createGroup, updateGroup, deleteGroup, assignDocumentsToGroup, removeDocumentFromGroup, deleteDocument, reprocessDocument — all preserved | LOW | RESOLVED | All API calls copied verbatim |
| R-045 | `AccessScreen` no useRef | AccessScreen uses `setTimeout` for linkCopied and saved timeouts — NOT useRef. Do not include `useRef` in React destructure for AccessScreen.jsx | INFO | DOCUMENTED | Only `useState, useEffect, useCallback` needed |
| R-046 | `AccessScreen` label_txt naming | `label_txt` is deliberately named to avoid shadowing the `label()` atom import. MUST NOT be renamed to `label` in extracted file | HIGH | RESOLVED | Preserved exactly as `label_txt` in AccessScreen.jsx |
| R-047 | `AccessScreen` permissions default | permissions useState initializer has 7 keys: can_download, can_print, can_copy, can_right_click, watermark_enabled, can_annotate, enable_info. Missing any key causes a silent permission toggle bug | HIGH | RESOLVED | Copied verbatim with all 7 keys |
| R-048 | `AccessScreen` no AnnotationLayer/CommentPopup | These are ViewerScreen components only — AccessScreen uses only AccessLog, TabBtn, DocumentPicker, plus atoms | INFO | DOCUMENTED | Sprint plan correctly excludes them from AccessScreen imports |
| R-049 | `AccessScreen` React.Fragment usage | Feedback tab uses `<React.Fragment key={a.id}>` at the feedback item rows. React is a global UMD object — `React.Fragment` available without import | INFO | DOCUMENTED | No special handling needed — global React is always available |

---

## Standing Constraints (all sprints)

- ZERO security regressions — auth and permissions must remain identical
- ZERO API changes — all existing endpoints remain identical
- ZERO database changes — no migrations
- ZERO UX changes — no visible behavior changes
- STOP on: security risk, circular dependency, build failure, test failure

---

## Sprint 4.2D — Phase 0 (Assessment)

Date: 2026-06-22

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-055 | ViewerScreen atoms audit | 14 atoms in app.jsx import line, but only Modal + Header used in ViewerScreen JSX body. Phase 0 grep confirmed no other atom JSX components in ViewerScreen. | MEDIUM | RESOLVED | ViewerScreen.jsx imports only `{ Modal, Header }` (D-029) |
| R-056 | `_setPageRef.current` render-body position | Confirmed at line 85 in app.jsx (between useViewerLayout at 82 and useTextLoader at 87). Must remain in render body in extracted file. | CRITICAL | RESOLVED | Python extraction preserved exact position; confirmed at line 78 in ViewerScreen.jsx |
| R-057 | Hook call order in extracted file | All 8 hook calls must be in same order as in app.jsx. Any reorder → silent behavior break. | HIGH | RESOLVED | Python extraction copied lines 36–879 verbatim (with 4-space indent strip); hook order identical |

---

## Sprint 4.2D — Execution

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-058 | 4-space outer indentation in app.jsx | app.jsx was uniformly indented by 4 spaces. Python strip of 4 leading chars applied to all lines. Risk: any line with fewer than 4 leading spaces would be mis-stripped. | LOW | RESOLVED | All lines in ViewerScreen body begin with 6+ spaces (4 outer + 2+ inner); no line begins with fewer than 4. Strip was clean. |
| R-059 | Bundle size regression | Extraction replaces inline definition with module import. esbuild should produce identical output. | MEDIUM | RESOLVED | Build confirmed 198.0 kb before and after extraction. No regression. |
| R-060 | Circular import: ViewerScreen ↔ AppShell | AppShell imports ViewerScreen.jsx; ViewerScreen.jsx must not import AppShell. Verified. | MEDIUM | RESOLVED | grep confirmed ViewerScreen.jsx has no AppShell import |

---

## Sprint 4.2E

| ID | Component | Risk | Severity | Status | Mitigation |
|---|---|---|---|---|---|
| R-061 | `docs/` path references | Sprint prompts and ACTION_LOG entries reference `docs/engineering/ARCHITECTURE_SCORECARD.md`, `docs/engineering/DECISION_LOG.md`, `docs/engineering/RISK_REGISTER.md` — these files have moved in Sprint 4.2E | LOW | DOCUMENTED | Historical references are intentionally stale (they record where files were at time of action). Future sprints should use new paths: `docs/architecture/ARCHITECTURE_SCORECARD.md`, `docs/decisions/DECISION_LOG.md`, `docs/risks/RISK_REGISTER.md` |
| R-062 | esbuild browser target | Target `chrome80,firefox78,safari14` is 5+ years stale. No functional impact today, but stale targets risk unexpected behavior if future syntax uses newer JS features that require newer targets. | LOW | DOCUMENTED | Upgrade candidate recorded (DEP-002). Do not change until a regression or new syntax requirement is observed. |
| R-063 | React CDN pin | React is loaded as a CDN/UMD global. If the CDN URL is not pinned to a specific version, a React minor/patch release could silently change behavior. | MEDIUM | DOCUMENTED | Verify CDN URL in index.html is pinned to a specific version (e.g., `react@18.2.0`) — not just `latest`. Out of scope for frontend sprint; requires index.html review. |
