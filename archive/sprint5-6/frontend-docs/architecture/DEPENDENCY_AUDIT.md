# Dependency Audit
Sprint 4.0 — Phase 2
Date: 2026-06-18

---

## Scope

All 33 source files in `frontend/src/`. Audit covers: circular dependencies, duplicated utilities, duplicated constants, duplicated helpers, cross-file coupling risks.

---

## Dependency Graph

```
constants/tokens.js          (no deps)
constants/viewer.js          (no deps)
utils/viewer.js              (no deps)
contexts/toast.jsx           ← tokens.js
components/atoms.jsx         ← tokens.js
components/GateMessage.jsx   ← tokens.js
components/AccessGate.jsx    ← tokens.js, atoms.jsx, GateMessage.jsx
components/ViewerInfoPanel.jsx ← tokens.js, atoms.jsx
components/DocumentPicker.jsx ← tokens.js, atoms.jsx, contexts/toast.jsx
components/upload/StatCard.jsx ← tokens.js, atoms.jsx
components/upload/DocRow.jsx ← tokens.js, atoms.jsx
components/upload/UploadDropZone.jsx    ← tokens.js
components/upload/UploadMetadataPanel.jsx ← tokens.js, atoms.jsx
components/upload/UploadProgressPanel.jsx ← tokens.js, atoms.jsx
components/TocSidebar.jsx    ← tokens.js
components/PageThumb.jsx     ← tokens.js
components/ViewerErrorBoundary.jsx ← tokens.js
components/ViewerInfoPanel.jsx ← tokens.js, atoms.jsx
hooks/useViewerLayout.js     ← constants/viewer.js
hooks/useTextLoader.js       ← utils/viewer.js
hooks/useViewerSession.js    ← utils/viewer.js, contexts/toast.jsx
hooks/useAnnotations.js      (no deps — React UMD global only)
hooks/useLinksSidecar.js     (no deps — React UMD global only)
hooks/usePageLoader.js       (no deps — React UMD global only)
hooks/useSearchHighlights.js (no deps — React UMD global only)
components/InsightsModal.jsx (no deps — C/mono as props)
components/LinksPanel.jsx    (no deps — C/mono as props)
components/AnnotationLayer.jsx (no deps — C/mono as props)
components/CommentPopup.jsx  (no deps — C as prop)
components/LaserPointer.jsx  (no deps)
components/RectMagnifier.jsx (no deps)
components/SearchPanel.jsx   (no deps)
components/ViewerToolbar.jsx (no deps — C/mono as props)
app.jsx                      ← all above
```

---

## Circular Dependency Analysis

**Result: NONE found.**

The dependency graph is a strict DAG (directed acyclic graph):
- Layer 0 (leaves): `tokens.js`, `viewer.js` (constants), `utils/viewer.js`
- Layer 1: `toast.jsx`, `atoms.jsx`, `GateMessage.jsx`
- Layer 2: `AccessGate.jsx`, `ViewerInfoPanel.jsx`, `DocumentPicker.jsx`, upload components, hooks
- Layer 3: `app.jsx` (root)

No file imports from a file that imports it. No cycles exist at any depth.

---

## Duplicated Utility Analysis

| Utility | Files | Status |
|---|---|---|
| `_errMsg(e, fallback)` | `utils/viewer.js` (defined), `app.jsx` (25×), `useTextLoader.js`, `useViewerSession.js` (imported) | CLEAN — single definition, multiple importers |
| `_saveLayoutPref / _loadLayoutPref` | `constants/viewer.js` (defined), `useViewerLayout.js` (imported), `app.jsx` imports `_saveLayoutPref` only | CLEAN — `_loadLayoutPref` correctly encapsulated in hook |

**No duplicated utility functions found.**

---

## Duplicated Constant Analysis

| Constant | Files | Status |
|---|---|---|
| Design tokens (`C`, `mono`) | `constants/tokens.js` (defined), imported by 12 files | CLEAN — single source of truth since Sprint 3.3 |
| `LAYOUT`, `ZOOM_*` | `constants/viewer.js` (defined), imported by app.jsx and useViewerLayout.js | CLEAN |

**No duplicated constants found.**

---

## Duplicated SVG Helper Analysis

AnnotationLayer.jsx contains internal SVG helpers (`_toNorm`, `_pathD`). These are component-private and not duplicated elsewhere.

`ViewerToolbar.jsx` uses inline SVG icon elements — no shared SVG helper utilities, so no duplication risk.

**No duplicated SVG helpers found.**

---

## C/mono Dependency Patterns

Two patterns coexist by design (D-002):

**Pattern A — Import:** Component imports C directly from tokens.js.
Used by: atoms.jsx, GateMessage.jsx, AccessGate.jsx, ViewerInfoPanel.jsx, DocumentPicker.jsx, TocSidebar.jsx, PageThumb.jsx, ViewerErrorBoundary.jsx, toast.jsx, all upload/ components.

**Pattern B — Props:** Component receives C/mono as props from caller.
Used by: AnnotationLayer, CommentPopup, InsightsModal, LinksPanel, ViewerToolbar.

Both patterns are intentional. Pattern B components predate centralization or have callers that already pass C/mono. No inconsistency — the rule is "don't change caller interface" (D-002).

**One minor finding:** `UploadDropZone.jsx` imports `mono` from tokens.js and uses it 2× in JSX (font-family references). This is correct — `mono` is used.

---

## Cross-File Coupling Risks

| Risk | Files | Severity | Notes |
|---|---|---|---|
| `fileRef` ref object shared across components | `UploadDropZone.jsx` receives `fileRef` prop; `UploadScreen` (in app.jsx) holds the ref and also uses `fileRef.current.click()` in the Header button | LOW | React ref semantics guarantee same DOM node — by design (D-011, R-018) |
| `drawPoints` stale closure | `AnnotationLayer.jsx` `_onMouseUp` reads state directly | LOW | Pre-existing risk (R-015, R-017); not introduced by extraction |
| Arrow `id="ah-${a.id}"` | `AnnotationLayer.jsx` SVG marker IDs | LOW | Unique per annotation; collision only if multiple AnnotationLayer instances on same page (R-014) |

---

## npm Dependency Analysis

**`package.json` devDependencies:**

| Package | Version | Used | Notes |
|---|---|---|---|
| `esbuild` | `^0.25.0` | YES — sole build tool | No unused devDependencies |

**Runtime dependencies: NONE.** React is loaded via UMD CDN in SecureDoc.html, not bundled via npm. esbuild bundles only `import` statements; CDN scripts are loaded externally.

---

## Summary

| Category | Findings | Action |
|---|---|---|
| Circular dependencies | 0 | None |
| Duplicated utilities | 0 | None |
| Duplicated constants | 0 | None |
| Unused npm dependencies | 0 | None |
| Cross-file coupling risks | 3 (all pre-existing, documented) | No action — documented in Risk Register |
| C/mono pattern consistency | 2 patterns by design | No action — D-002 decision |

**Dependency health: CLEAN.** No remediation required in Phase 4.
