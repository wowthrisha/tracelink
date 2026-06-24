# Sprint 3.3 — Viewer Component Wave 1 Report

**Date**: 2026-06-17  
**Build**: `196.6 kb` — PASS ✅  
**Constraint**: Zero feature changes, zero UX changes, zero API changes

---

## Summary

Sprint 3.3 extracted 9 viewer-only components and created the design token file.  
app.jsx reduced from 5,085 → 4,289 lines (−796 lines, −15.7%).

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/constants/tokens.js` | 42 | C (47-key color/spacing object) + mono |
| `src/components/LaserPointer.jsx` | 31 | GPU-accelerated laser cursor |
| `src/components/RectMagnifier.jsx` | 63 | 2.5× rectangular magnifier |
| `src/components/SearchPanel.jsx` | 128 | Full-document text search overlay |
| `src/components/InsightsModal.jsx` | 72 | Page engagement heatmap panel |
| `src/components/LinksPanel.jsx` | 118 | Per-page hyperlink side panel |
| `src/components/TocSidebar.jsx` | 113 | Table of contents sidebar |
| `src/components/PageThumb.jsx` | 100 | Page thumbnail with semaphore |
| `src/components/ViewerErrorBoundary.jsx` | 22 | React error boundary for viewer |

---

## Files Modified

| File | Change |
|------|--------|
| `src/app.jsx` | +9 imports; −C/mono definitions; −ViewerErrorBoundary; −9 components; −2 dead components |
| `src/contexts/toast.jsx` | Replaced `_TC` inline color subset with `import { C } from '../constants/tokens.js'` |

---

## Dead Code Deleted

| Component | Lines | Evidence |
|-----------|-------|---------|
| `MockPage` | 40 | `grep '<MockPage'` → 0 results |
| `WatermarkOverlay` | 18 | `grep '<WatermarkOverlay'` → 0 results |

Both components were defined but never called. Page rendering and watermark display are done inline in ViewerScreen. These are vestigial from a prior design iteration.

---

## Cumulative Sprint Progress

| Sprint | Lines removed from app.jsx | Running total |
|--------|--------------------------|---------------|
| Sprint 2 (7 hooks) | −962 | −962 |
| Sprint 3.2 (toast + toolbar) | −440 | −1,402 |
| Sprint 3.3 (tokens + 9 components + dead code) | −796 | **−2,198** |

**app.jsx**: 6,047 → 4,289 (−36.4%)

---

## Architecture Notes

### tokens.js as prerequisite enabler

`constants/tokens.js` is the critical unlocker for the remaining extraction work. Before this sprint:
- Components using C/mono via closure could NOT be extracted (C was a module-level var in app.jsx)
- toast.jsx carried a `_TC` inline subset (partial token duplication risk)

After this sprint:
- TocSidebar, PageThumb, ViewerErrorBoundary import from tokens.js ✅
- toast.jsx imports from tokens.js ✅
- All future component extractions that need C/mono use: `import { C, mono } from '../constants/tokens.js'`

### Semaphore relocation

The `_THUMB_CONCURRENCY`/`_thumbQueue` semaphore (module-level state, ~25 lines) moved to `PageThumb.jsx`. This is correct ownership — the semaphore is PageThumb's fetch strategy, not app.jsx state. esbuild bundles all modules into a single output file, so there is still only one instance of the semaphore at runtime (behavior unchanged).

### C/mono as props vs. import

Components that previously received C and mono as props (InsightsModal, LinksPanel) continue to receive them as props — no breaking change to the call sites. This was a deliberate earlier decision (Phase 3.2) that remains valid.

---

## Components Deferred to Next Sprint

### Blocked by shared atoms (AccessGate, ViewerInfoPanel)

`GateMessage` and `AccessGate` use `Btn` atom; `ViewerInfoPanel` uses `SectionLabel`, `RiskBadge`, `StatusDot`, `Divider`, `Btn`. All five are defined in app.jsx's shared atom layer (lines 30-430). Extracting these components requires extracting the atoms first.

### Medium-risk deferred (AnnotationLayer, CommentPopup)

AnnotationLayer has a complex state machine (`preview`, `drawPoints`, `dragRef`). Risk: MEDIUM. Deferred to allow a dedicated focused sprint with thorough prop audit.

---

## Build Verification

```
npm run build → 196.6 kb, 22 ms, 0 errors, 0 warnings ✅
```

Bundle size decreased by 0.2 kb vs Sprint 3.2 (dead code deletion more than offset module overhead).

---

## Manual Verification Checklist

| # | Behavior | Path | Status |
|---|----------|------|--------|
| V1 | Toast appears on session error | useViewerSession → toast?.() | Verify |
| V2 | Toast appears on DRM block | useViewerSession → toast?.() | Verify |
| V3 | Laser pointer follows mouse | LaserPointer (extracted) | Verify |
| V4 | Magnifier zooms page area | RectMagnifier (extracted) | Verify |
| V5 | Search finds text, navigates pages | SearchPanel (extracted) | Verify |
| V6 | Insights modal shows heatmap | InsightsModal (extracted) | Verify |
| V7 | Links panel lists page links | LinksPanel (extracted) | Verify |
| V8 | TOC sidebar navigates | TocSidebar (extracted) | Verify |
| V9 | Page thumbnails load progressively | PageThumb (extracted) | Verify |
| V10 | Thumbnail semaphore limits requests | PageThumb._thumbQueue | Verify |
| V11 | Error boundary shows retry button | ViewerErrorBoundary (extracted) | Verify |
| V12 | Toast colors match design | toast.jsx using C.success/error/warning/teal2 | Verify |
| V13 | Viewer toolbar works fully | ViewerToolbar (unchanged) | Verify |

---

## Next Sprint Recommendation

See Phase 10 output in SPRINT3_3_NEXT_SPRINT.md.
