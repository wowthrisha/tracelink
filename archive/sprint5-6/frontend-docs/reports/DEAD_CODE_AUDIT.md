> **HISTORICAL ARCHIVE** — Sprint milestone record. Reflects state at time of writing. Not current state.

# Dead Code Audit
Sprint 4.0 — Phase 1
Date: 2026-06-18

---

## Scope

All 33 source files in `frontend/src/`. Audit covers: unused functions, unused constants, unreachable code, stale comments, orphaned section headers, TODO/FIXME/HACK inventory, console.log inventory.

---

## TODO / FIXME / HACK Inventory

**Result: NONE actionable.**

`grep -rn "TODO|FIXME|HACK|XXX|TEMP|KLUDGE" src/` returned 2 lines, both non-actionable:

| File | Line | Text | Assessment |
|---|---|---|---|
| `app.jsx` | 84 | `const MAX_POLL_ATTEMPTS = 150; // 150 × 2s = 5 minutes before giving up` | Inline documentation comment — not a TODO, not dead |

---

## Console Log Inventory

| File | Line | Call | Assessment |
|---|---|---|---|
| `components/ViewerErrorBoundary.jsx` | 6 | `console.error('ViewerErrorBoundary caught:', error, info)` | Intentional — error boundary diagnostic, keep |
| `hooks/usePageLoader.js` | 70 | `console.error('[SecureDoc] loadPage: token or sessionId missing', ...)` | Intentional — security diagnostic, keep |
| `hooks/usePageLoader.js` | 114 | `console.error('[SecureDoc] page fetch HTTP error', ...)` | Intentional — network diagnostic, keep |
| `hooks/usePageLoader.js` | 129 | `console.warn('[SecureDoc] page fetch network error, falling back to img src', ...)` | Intentional — graceful degradation diagnostic, keep |

**Result: No dead console.log calls. All 4 are intentional diagnostics.**

---

## Blank Line Clusters

| File | Location | Severity | Description |
|---|---|---|---|
| `app.jsx` | Lines 387–389 | LOW | 3 consecutive blank lines before `/* ══ SCREEN 2 — DOCUMENT VIEWER ══ */` comment. Should be 1 blank line. Left by Sprint 3.5 deletion of AnnotationLayer/CommentPopup block. |

**Action:** Collapse to 1 blank line (Phase 4 execution).

---

## Unused Function Inventory

**None found.** All module-level functions and component functions verified as called or exported and imported.

- `buildFeedbackFilters` — still inline in app.jsx, called in AccessScreen. Not dead, pending Sprint 4.1 extraction.
- `_pathD`, `_toNorm`, `_onMouseDown`, `_onMouseMove`, `_onMouseUp` — internal to AnnotationLayer.jsx, called within component.
- `_saveLayoutPref`, `_loadLayoutPref` — called by useViewerLayout.js.
- `_errMsg` — called at 25 sites in app.jsx, and in useTextLoader.js and useViewerSession.js.

---

## Unused Constant Inventory

**None found.** All constants in tokens.js and viewer.js are actively imported and used.

---

## Stale Comment Inventory

| File | Location | Description | Action |
|---|---|---|---|
| `app.jsx` | Line 390 | `/* ══════ SCREEN 2 — DOCUMENT VIEWER ══════ */` section header | Legitimate section separator — keep |
| Various | — | `/* ─── COMPONENT NAME ─── */` style block headers | All were removed during Sprint 3.5 extractions; none remain orphaned |

**Result: No stale or orphaned comments confirmed.**

---

## Dead Code from useViewerSession Refactor

The uncommitted change to `useViewerSession.js` removed the `toast` parameter from the hook's option object:

```diff
- export function useViewerSession(doc, publicToken, { onValidated, toast } = {}) {
+ export function useViewerSession(doc, publicToken, { onValidated } = {}) {
+   const toast = useToast();
```

**Impact:** Zero. App.jsx only passes `{ onValidated: ... }` — never passed `toast`. The removed parameter was dead in the caller. The JSDoc lines describing the removed parameter are also removed in the diff. This is a clean dead-parameter removal + encapsulation improvement.

**Status:** Accept uncommitted change — no API contract breakage, caller was already compatible.

---

## Summary

| Category | Count | Action |
|---|---|---|
| TODO/FIXME/HACK markers | 0 | None |
| Dead console.log | 0 | None |
| Dead functions | 0 | None |
| Dead constants | 0 | None |
| Unused imports | 0 | None |
| Unused exports | 0 | None |
| Stale/orphaned comments | 0 | None |
| Blank line clusters (3+) | 1 | Fix in Phase 4 |
| Dead parameters (accepted) | 1 | useViewerSession `toast` param — removed in uncommitted change |

**Cleanup scope is minimal: 1 blank-line fix only.**
