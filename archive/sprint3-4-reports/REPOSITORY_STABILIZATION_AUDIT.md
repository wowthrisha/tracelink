> **HISTORICAL ARCHIVE** — Sprint milestone record. Reflects state at time of writing. Not current state.

# Repository Stabilization Audit
Sprint 4.2E — Phase 0
Date: 2026-06-22

---

## 1. Source File Inventory

### Totals

| Directory | Files | LOC total |
|---|---|---|
| `src/app.jsx` | 1 | 5 |
| `src/screens/` | 8 | 2,710 |
| `src/components/` (top-level) | 17 | 1,531 |
| `src/components/access/` | 2 | 74 |
| `src/components/analytics/` | 5 | 152 |
| `src/components/upload/` | 5 | 156 |
| `src/hooks/` | 7 | 891 |
| `src/constants/` | 2 | 67 |
| `src/contexts/` | 1 | 47 |
| `src/utils/` | 2 | 23 |
| **Total** | **50** | **5,656** |

### Screens (8 files)

| File | LOC | Exports | Dependencies |
|---|---|---|---|
| `AppShell.jsx` | 112 | `AppShell` | tokens, toast, atoms, ViewerErrorBoundary, 7 screens |
| `LoginScreen.jsx` | 234 | `LoginScreen` | tokens |
| `BillingScreen.jsx` | 196 | `BillingScreen` | tokens |
| `StorageScreen.jsx` | 162 | `StorageScreen` | tokens, viewer.js, toast, atoms |
| `AnalyticsScreen.jsx` | 401 | `AnalyticsScreen` | tokens, viewer.js, toast, atoms, 5 analytics |
| `UploadScreen.jsx` | 359 | `UploadScreen` | tokens, viewer.js, toast, atoms, 5 upload |
| `AccessScreen.jsx` | 714 | `AccessScreen` | tokens, viewer.js, toast, feedback.js, atoms, AccessLog, TabBtn, DocumentPicker |
| `ViewerScreen.jsx` | 872 | `ViewerScreen` | viewer.js, _errMsg, 8 hooks, toast, ViewerToolbar, tokens, 11 components, atoms |

### Hooks (7 files)

| File | LOC | Exports | Dependencies |
|---|---|---|---|
| `useAnnotations.js` | 67 | `useAnnotations` | — (window.SecureDocAPI) |
| `useLinksSidecar.js` | 68 | `useLinksSidecar` | — (window.SecureDocAPI) |
| `usePageLoader.js` | 242 | `usePageLoader` | — (window.SecureDocAPI) |
| `useSearchHighlights.js` | 61 | `useSearchHighlights` | — (window.SecureDocAPI) |
| `useTextLoader.js` | 48 | `useTextLoader` | utils/viewer.js |
| `useViewerLayout.js` | 139 | `useViewerLayout` | constants/viewer.js |
| `useViewerSession.js` | 168 | `useViewerSession` | utils/viewer.js, contexts/toast.jsx |

### Components — Top-Level (17 files)

| File | LOC | Exports | C/mono source |
|---|---|---|---|
| `AccessGate.jsx` | 72 | `AccessGate` | imports |
| `AnnotationLayer.jsx` | 155 | `AnnotationLayer` | props |
| `CommentPopup.jsx` | 20 | `CommentPopup` | props |
| `DocumentPicker.jsx` | 78 | `DocumentPicker` | imports |
| `GateMessage.jsx` | 17 | `GateMessage` | imports |
| `InsightsModal.jsx` | 70 | `InsightsModal` | props |
| `LaserPointer.jsx` | 28 | `LaserPointer` | — (none) |
| `LinksPanel.jsx` | 128 | `LinksPanel` | props |
| `PageThumb.jsx` | 108 | `PageThumb` | imports |
| `RectMagnifier.jsx` | 67 | `RectMagnifier` | — (none) |
| `SearchPanel.jsx` | 136 | `SearchPanel` | — (none) |
| `TocSidebar.jsx` | 125 | `TocSidebar` | imports |
| `ViewerErrorBoundary.jsx` | 23 | `ViewerErrorBoundary` | imports |
| `ViewerInfoPanel.jsx` | 120 | `ViewerInfoPanel` | imports |
| `ViewerToolbar.jsx` | 397 | `ViewerToolbar` | props |
| `atoms.jsx` | 411 | 14 exports | imports |

### Components — Sub-directories

| Directory | Files | Exports |
|---|---|---|
| `access/` | AccessLog.jsx (56 LOC), TabBtn.jsx (18 LOC) | `AccessLog`, `TabBtn` |
| `analytics/` | DocAnalyticsRow (29), DonutChart (40), KpiCard (23), RangeBtn (18), SparkChart (42) | 5 named exports |
| `upload/` | DocRow (80), StatCard (25), UploadDropZone (26), UploadMetadataPanel (32), UploadProgressPanel (33) | 5 named exports |

### Infrastructure

| File | LOC | Exports |
|---|---|---|
| `constants/tokens.js` | 40 | `C` (47 keys), `mono` |
| `constants/viewer.js` | 27 | `LAYOUT`, `ZOOM_MIN/MAX/STEP/PRESETS`, `_saveLayoutPref`, `_loadLayoutPref` |
| `contexts/toast.jsx` | 47 | `ToastCtx`, `useToast`, `ToastProvider` |
| `utils/viewer.js` | 12 | `_errMsg` |
| `utils/feedback.js` | 11 | `buildFeedbackFilters` |

---

## 2. Import Hygiene Findings

| ID | File | Finding | Severity | Action |
|---|---|---|---|---|
| IH-001 | `components/access/AccessLog.jsx` | Atoms import path `../../components/atoms.jsx` is redundant — should be `../atoms.jsx` (all other sub-components use 1-level-up path). Both resolve to `src/components/atoms.jsx`. | LOW | FIX in Phase 1 |
| IH-002 | `contexts/toast.jsx` | `ToastCtx` exported but never imported externally — used internally by `useToast()` and `ToastProvider` within the same file. | INFO | NONE — internal use is valid |
| IH-003 | `components/atoms.jsx` | `NavItem` exported but never imported externally — used internally by `Sidebar` within atoms.jsx. | INFO | NONE — intentional (Sidebar renders NavItems internally; export available for future direct use) |
| IH-004 | `screens/ViewerScreen.jsx` | C/mono import is at position 12 (after hooks) — other screens put C/mono at position 1. Inconsistency is cosmetic and inherited from app.jsx functional ordering. | INFO | NONE — reordering very-high-risk file for cosmetics violates sprint constraint |
| IH-005 | All source files | Zero circular dependencies confirmed. | PASS | — |
| IH-006 | All source files | Zero duplicate imports confirmed. | PASS | — |

---

## 3. File & Folder Consistency Findings

| ID | Finding | Status |
|---|---|---|
| FC-001 | All 8 screens export a single named function. | PASS |
| FC-002 | All 7 hooks export a single named `useXxx` function. | PASS |
| FC-003 | All components export a single named function (exception: `atoms.jsx` — 14 exports by design). | PASS |
| FC-004 | File extension convention: `.jsx` for files with JSX, `.js` for pure logic. Applied consistently. | PASS |
| FC-005 | `AnnotationLayer`, `CommentPopup`, `InsightsModal`, `LinksPanel`, `ViewerToolbar` receive C/mono as props. Documented pattern (D-002). | BY DESIGN |
| FC-006 | `DocumentPicker.jsx` lives in `components/` not `components/upload/` — shared by ViewerScreen + AccessScreen. Documented (D-012). | BY DESIGN |
| FC-007 | Root `securedoc/` directory has ~60 untracked `.md` files from prior audit sessions. Outside frontend scope. | OUT OF SCOPE |
| FC-008 | `securedoc/].md` — 0-byte or content file from shell redirect accident (D-015). `TRACEVIEW_PILOT_DEPLOYMENT_GUIDE.md` also exists at root. User should resolve. | OUT OF SCOPE (user action) |

---

## 4. Git State

| File | Status | Notes |
|---|---|---|
| `frontend/src/app.jsx` | Modified | 882 → 5 lines (Sprint 4.2D) |
| `frontend/src/hooks/useViewerSession.js` | Modified | Toast refactor Sprint 4.0 (D-016) |
| `frontend/dist/app.bundle.js` | Modified | Rebuilt after Sprint 4.2D |
| `200`, `404` | Deleted | Sprint 4.0 (D-015) |
| `frontend/src/components/`, `frontend/src/screens/`, etc. | Untracked | All extracted files from Sprint 3.3–4.2D |
| `frontend/docs/` | Untracked | All engineering docs from Sprint 4.0+ |

**Pending commit:** All Sprint 3.3–4.2E changes. None of the extraction work has been committed. See Sprint 4.2E Phase 3 for commit plan.

---

## 5. Dependency Findings

| ID | Finding | Severity | Action |
|---|---|---|---|
| DEP-001 | Only dependency: `esbuild ^0.25.0`. No unused or obsolete deps. | PASS | — |
| DEP-002 | esbuild browser target: `chrome80,firefox78,safari14` (year 2020). Current browsers: Chrome 130+, Firefox 127+, Safari 18+. Stale target means more transpilation and larger potential polyfill surface. | INFO | Document — upgrade candidate (do not change yet) |
| DEP-003 | No source maps in build. Debugging production requires bundle traversal. | INFO | Document — add `--sourcemap` flag as future enhancement |
| DEP-004 | React is CDN/UMD global (not in package.json). Intentional CDN deployment model (D-014). | BY DESIGN | — |

---

## 6. Build Hygiene

| Check | Result |
|---|---|
| Clean build | PASS — 198.0 kb, 0 warnings, 37ms |
| Circular dependencies | PASS — zero |
| Unused imports in build | PASS — esbuild tree-shakes; bundle size confirms no bloat |
| Dead exports | INFO — `ToastCtx` and `NavItem` exported but not externally consumed (see IH-002, IH-003). esbuild will include them since everything is bundled. Negligible size impact. |

---

## 7. Documentation Inventory (26 files in docs/engineering/)

### Living operational docs (append-only)
- `ACTION_LOG.md` — A-001 through A-127
- `DECISION_LOG.md` — D-001 through D-030
- `RISK_REGISTER.md` — R-001 through R-060
- `ARCHITECTURE_SCORECARD.md` — Baseline through Sprint 4.2D

### Architecture / baseline docs
- `ARCHITECTURE_BASELINE.md`
- `REPOSITORY_INVENTORY.md`
- `DEPENDENCY_AUDIT.md`

### Security docs
- `SECURITY_BASELINE.md`

### Sprint reports (completed, historical)
- `SPRINT3_4_REPORT.md`
- `SPRINT3_5_REPORT.md`
- `SPRINT4_0_REPORT.md`
- `SPRINT4_2D_REPORT.md`

### Readiness reviews / audits (completed, historical)
- `ANNOTATION_LAYER_READINESS_REVIEW.md`
- `SCREEN_EXTRACTION_READINESS_REVIEW.md`
- `POST_SCREEN_EXTRACTION_AUDIT.md`
- `BUILD_HYGIENE_AUDIT.md`
- `DEAD_CODE_AUDIT.md`
- `VIEWERSCREEN_FINAL_AUDIT.md`

### Sprint plans (completed execution plans, historical)
- `SPRINT3_5_NEXT_SPRINT.md`
- `SPRINT4_EXECUTION_PLAN.md`
- `SPRINT4_2_EXECUTION_PLAN.md`
- `SPRINT4_2B_EXECUTION_PLAN.md`
- `SPRINT4_2C_EXECUTION_PLAN.md`
- `SPRINT4_2D_VIEWER_FINAL_PLAN.md`
- `SPRINT4_2D_IMPLEMENTATION_PROMPT.md`
- `SPRINT4_2E_REPOSITORY_STABILIZATION_PLAN.md`

### New (this sprint)
- `REPOSITORY_STABILIZATION_AUDIT.md` (this file)
