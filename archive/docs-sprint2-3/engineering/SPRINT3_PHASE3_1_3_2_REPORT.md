# Sprint 3 — Phase 3.1 + 3.2 Implementation Report

**Date**: 2026-06-17  
**Phases**: 3.1 ViewerToolbar Extraction + 3.2 Toast Context Extraction  
**Build**: `196.8 kb` — PASS ✅  
**Constraint**: Zero feature changes, zero UX changes, zero API changes

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `frontend/src/contexts/toast.jsx` | 56 | ToastCtx, useToast, ToastProvider, Toast |
| `frontend/src/components/ViewerToolbar.jsx` | 397 | AnnotToolbar (private), ViewerToolbar (exported) |

---

## Lines Removed from app.jsx

| Block removed | Lines |
|---------------|-------|
| Toast block (ToastCtx, useToast, ToastProvider, Toast) | 44 |
| ANNOT_COLORS + ANNOT_TOOLS constants | 10 |
| AnnotToolbar component | 71 |
| ViewerToolbar component + comment | 315 |
| `useContext`, `createContext` from React destructure | 0 (inline edit) |
| `toast` param from useViewerSession call | 0 (inline edit) |
| **Total** | **440** |

**app.jsx line count**: 5,525 → 5,085 (−440 lines, −8.0%)

---

## Cumulative Sprint Progress

| Phase | Description | Δ lines |
|-------|-------------|---------|
| Phase 1 | Extract constants/viewer.js, utils/viewer.js | −22 |
| Phase 2.1–2.7 | Extract 7 custom hooks | −500 |
| Phase 3.1+3.2 | Extract toast context + ViewerToolbar | −440 |
| **Total** | | **−962 lines** |

**app.jsx**: 6,047 → 5,085 (−15.9%)

---

## What Changed in Each File

### `frontend/src/contexts/toast.jsx` (NEW)

Exports: `ToastCtx`, `useToast`, `ToastProvider`  
Private: `Toast` (not exported — only ToastProvider renders it)

Design token dependency: Toast uses a subset of the `C` color object. Rather than importing
a tokens file that doesn't exist yet (Phase 3.6), the needed values are inlined as `_TC`
(prefixed to prevent collision). When Phase 3.6 extracts `C`, this file becomes a two-line
import replacement.

### `frontend/src/components/ViewerToolbar.jsx` (NEW)

Exports: `ViewerToolbar`  
Private: `AnnotToolbar`, `ANNOT_TOOLS`, `ANNOT_COLORS`

Pure component — no state ownership, no API calls. All business logic (onAnnotUndo API call,
onDownload, onPrint, onToggleBookmark) remains in ViewerScreen and is passed as props.
The only internal state is `showFlyout` in AnnotToolbar (UI toggle, correctly local).

### `frontend/src/hooks/useViewerSession.js` (MODIFIED)

- Added `import { useToast } from '../contexts/toast.jsx';`
- Moved `const toast = useToast();` to first line of hook body
- Removed `toast` from the `{ onValidated, toast }` options parameter
- Removed `@param {Function} [opts.toast]` from JSDoc

All existing `toast?.()` call sites inside the hook are unchanged — optional chaining is still
correct because `useToast()` returns `null` when called outside a `ToastProvider` tree.

### `frontend/src/app.jsx` (MODIFIED)

- Added 2 new imports (toast.jsx, ViewerToolbar.jsx)
- Removed `useContext`, `createContext` from React destructure (no longer used in app.jsx)
- Removed Toast block (lines 59–102)
- Removed `toast` from useViewerSession call options
- Removed ANNOT_COLORS, ANNOT_TOOLS, AnnotToolbar, ViewerToolbar definitions (2,235–2,631)

---

## Prop Surface Analysis — ViewerToolbar

The toolbar accepts 38 props. This is intentionally wide — it was wide before extraction too.
The props fall into 6 categories:

| Category | Props | Count |
|----------|-------|-------|
| Document identity | doc, docName, isTextDoc | 3 |
| Navigation | page, PAGE_COUNT, pageInputStr, setPageInputStr, setPage, goPrev, goNext | 7 |
| Layout/zoom | layoutMode, customZoom, _zoomBy, _zoomTo, _setLayout, LAYOUT, ZOOM_STEP, ZOOM_PRESETS | 8 |
| Panel toggles | showLaser/Magnifier/Insights/Links/Toc/Search/Info/PageList + setters + flags | 14 |
| Annotations | annotTool, annotColor, annotThickness, annotUndoStack, canAnnotate, setters, callbacks | 8 |
| Actions + permissions | canDownload, canPrint, canInfo, onDownload, onPrint, rotation, onRotate, isTwoPage, onToggleTwoPage, C, mono | ~8 |

All 38 props are pass-through from ViewerScreen. No prop is computed inside the component.
This is the correct design for a pure presentational component.

**Observation**: The wide prop surface is a symptom that ViewerScreen itself still owns too many
panel-toggle states. After Phase 3.3 (panel extraction), the panel-toggle props will collapse
into ownership by each panel component, shrinking the toolbar interface significantly.

---

## Bundle Impact

| | Before | After |
|--|--------|-------|
| Bundle size | 196.4 kb | 196.8 kb |
| Build time | 30 ms | 28 ms |

Bundle size increased by 0.4 kb — within noise. No code was added; the slight increase is
from the additional module boundary overhead (import metadata). esbuild inlines everything
into the single output bundle so there is no runtime module resolution overhead.

---

## Build Verification

```
npm run build → 196.8 kb, 28 ms, 0 errors, 0 warnings ✅
```

---

## Manual Verification Checklist

The following behaviors must be unchanged after these phases:

| # | Behavior | Component path | Status |
|---|----------|----------------|--------|
| V1 | Toast appears on download | ViewerScreen → toast() | Verify |
| V2 | Toast appears on failed action | useViewerSession → toast?() | Verify |
| V3 | Toast appears on DRM block (right-click) | useViewerSession → toast?() | Verify |
| V4 | Page navigation (arrows, input) | ViewerToolbar → goPrev/goNext/setPage | Verify |
| V5 | Zoom in/out/presets | ViewerToolbar → _zoomBy/_zoomTo/_setLayout | Verify |
| V6 | Rotation | ViewerToolbar → onRotate | Verify |
| V7 | Fullscreen toggle | ViewerToolbar → toggleFullscreen | Verify |
| V8 | Search panel opens (Ctrl+F + button) | ViewerToolbar → setShowSearch | Verify |
| V9 | Bookmark toggle (star icon) | ViewerToolbar → onToggleBookmark | Verify |
| V10 | Print button (permission gate) | ViewerToolbar → onPrint | Verify |
| V11 | Download button (permission gate) | ViewerToolbar → onDownload | Verify |
| V12 | Annotation flyout opens | AnnotToolbar (internal) | Verify |
| V13 | Annotation color/thickness selection | AnnotToolbar → setAnnotColor/Thickness | Verify |
| V14 | Annotation undo | AnnotToolbar → onAnnotUndo | Verify |
| V15 | Two-page mode toggle | ViewerToolbar → onToggleTwoPage | Verify |
| V16 | Links badge count | ViewerToolbar ← linksCount prop | Verify |
| V17 | Insights button visible | ViewerToolbar ← hasInsights prop | Verify |

---

## Phase 3.3–3.6 Analysis: SearchPanel, LinksPanel, InsightsModal

### Component profiles

| Component | Lines | Props in | Props out | API calls inside | Notes |
|-----------|-------|----------|-----------|-----------------|-------|
| `InsightsModal` | 72 | docName, loading, data, onClose, C, mono | — | None | Purely presentational; displays pre-fetched data |
| `LinksPanel` | 130 | page, pageLinksRef, visitedLinks, onVisit, onClose, C, mono | — | None | Reads a ref; renders link list with visit tracking |
| `SearchPanel` | 136 | session, onClose, onNavigate, onQueryChange, onActiveChange, onResultsChange | — | Yes (`session.link_token` → API) | Makes its own fetch for word positions/search; owned internal state |

### Recommendation: Separate files

**Extract each panel to its own file** (`components/InsightsModal.jsx`, `components/LinksPanel.jsx`,
`components/SearchPanel.jsx`).

Rationale:
1. **No shared code** — the three panels share zero utilities, no sub-components, and no imports
   with each other. A `viewer-panels` module would be an artificial grouping with no cohesion.
2. **Different dependency profiles** — InsightsModal is zero-dependency; LinksPanel needs a ref
   structure; SearchPanel makes API calls. Bundling them together couples these unlike profiles.
3. **Independent call sites** — each panel is conditionally rendered from a separate `{condition && <Panel />}`
   block in ViewerScreen, not from a shared container. Separate files match the render structure.
4. `SearchPanel` will eventually need `useToast()` directly once session errors need toast feedback.
   With separate files, that's a one-line add. With a shared module, it complicates exports.

**Do not** create a `viewer-panels/index.js` barrel. Barrel files cause bundlers to tree-shake
poorly and make `import` paths non-obvious to readers of the call sites.

---

## Fastest Path to app.jsx < 3,000 Lines

**Current**: 5,085 lines  
**Target**: < 3,000 lines  
**Gap**: −2,085 lines needed

### Recommended extraction sequence

| Step | Target | Est. lines freed | Projected app.jsx |
|------|--------|-----------------|-------------------|
| **A** | `DocManagement` screen + sub-panels | ~1,800 | ~3,285 |
| **B** | `SearchPanel` | ~136 | ~3,149 |
| **C** | `LinksPanel` | ~130 | ~3,019 |
| **D** | `InsightsModal` | ~72 | **~2,947** ← passes 3k threshold |
| **E** | `TocSidebar` + `PageThumb` | ~175 | ~2,772 |
| **F** | `AnnotationLayer` + `CommentPopup` | ~240 | ~2,532 |

**DocManagement must go first.** It is by far the largest block (~1,800 lines) and is
completely independent of the viewer — it shares no state, no context, no hooks with
ViewerScreen. It is the single highest-leverage extraction in the remaining codebase.

After step D (panels), app.jsx crosses the 3,000 line threshold regardless of order.

**Steps B–D can run in parallel** — each panel is self-contained. Steps B, C, D have no
dependency on each other and can be extracted in any order or simultaneously.

### Why not AnnotationLayer first?

AnnotationLayer (step F) is higher-complexity than any panel:
- It has its own drawing state machine (`preview`, `drawPoints`, `dragRef`)
- It receives the full annotation callback surface from ViewerScreen
- It needs careful prop audit before extraction (risk: MEDIUM per the Sprint 2 audit)

Doing the panels first (lower risk) reaches the < 3,000 target faster while deferring
the complex extraction to a moment when app.jsx is smaller and easier to reason about.

---

## Sprint 3 Next Steps

| Phase | Work | Risk |
|-------|------|------|
| 3.3 (next) | Extract DocManagement (~1,800 lines) | Low — fully independent of viewer |
| 3.4 | Extract SearchPanel, LinksPanel, InsightsModal (can parallel) | Very low |
| 3.5 | Extract TocSidebar + PageThumb + misc viewer helpers | Low |
| 3.6 | Extract AnnotationLayer + CommentPopup | Medium — drawing state machine |
| 3.7 | Extract design tokens (C object) + update _TC in toast.jsx | Very low |
