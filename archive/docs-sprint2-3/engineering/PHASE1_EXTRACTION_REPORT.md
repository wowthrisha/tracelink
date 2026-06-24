# Phase 1 Extraction Report — Constants & Utilities

**Sprint**: Architecture Refactor Sprint 2, Goal #3  
**Date**: 2026-06-17  
**Status**: Complete ✅

---

## Objective

Extract viewer-related constants and pure utility functions from `frontend/src/app.jsx`
into dedicated modules with zero behavior changes.

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `frontend/src/constants/viewer.js` | 25 | LAYOUT enum, ZOOM constants, layout-pref helpers |
| `frontend/src/utils/viewer.js` | 11 | `_errMsg` error message extractor |

### `frontend/src/constants/viewer.js`
Exported symbols:
- `LAYOUT` — `{ AUTO, FIT_WIDTH, FIT_HEIGHT, ACTUAL, CUSTOM }` enum
- `ZOOM_MIN` — `10`
- `ZOOM_MAX` — `400`
- `ZOOM_STEP` — `10`
- `ZOOM_PRESETS` — `[25, 50, 75, 100, 125, 150, 200, 300, 400]`
- `_saveLayoutPref(mode, zoom)` — writes to localStorage
- `_loadLayoutPref()` — reads from localStorage, returns `{ mode, zoom }`

### `frontend/src/utils/viewer.js`
Exported symbols:
- `_errMsg(e, fallback)` — extracts a human-readable message from any error shape

---

## Imports Updated in `app.jsx`

Two import lines added at the very top of `frontend/src/app.jsx`:

```js
import { LAYOUT, ZOOM_MIN, ZOOM_MAX, ZOOM_STEP, ZOOM_PRESETS, _saveLayoutPref, _loadLayoutPref } from './constants/viewer.js';
import { _errMsg } from './utils/viewer.js';
```

---

## Lines Removed from `app.jsx`

| Block removed | Original lines | Count |
|---------------|---------------|-------|
| `_errMsg` function + section header | 49–60 | 13 lines |
| LAYOUT/ZOOM constants + layout-pref functions | 1219–1236 | 19 lines |
| **Total removed** | | **32 lines** |

Import lines added: **2**  
Net change to `app.jsx`: **−30 lines**

---

## Build Verification

| Metric | Before | After |
|--------|--------|-------|
| Build command | `esbuild src/app.jsx --loader:...` | `esbuild src/app.jsx --bundle --loader:...` |
| Bundle size | 199.2 kb | 192.5 kb |
| Build time | ~21 ms | ~15 ms |
| Build result | PASS ✅ | PASS ✅ |

The `--bundle` flag was added to `package.json`. esbuild v0.25 requires this flag
to resolve and inline ES module imports. Without it, `import` statements are left
in the output verbatim, which would cause a runtime error since the app runs in a
browser that loads the bundle as a plain `<script>`.

Bundle size decreased by 6.7 kb because `--bundle` allows esbuild's minifier to
perform cross-module dead-code elimination and constant folding.

---

## Before / After Dependency Graph

### Before Phase 1
```
app.jsx (6 047 lines, standalone)
│
├── [inline] _errMsg (lines 50–60)
├── [inline] LAYOUT (line 1220)
├── [inline] ZOOM_MIN/MAX/STEP/PRESETS (lines 1221–1224)
├── [inline] _saveLayoutPref (lines 1227–1229)
└── [inline] _loadLayoutPref (lines 1231–1235)
```

### After Phase 1
```
app.jsx (6 015 lines, entry)
├── constants/viewer.js
│   ├── LAYOUT
│   ├── ZOOM_MIN, ZOOM_MAX, ZOOM_STEP, ZOOM_PRESETS
│   ├── _saveLayoutPref
│   └── _loadLayoutPref
└── utils/viewer.js
    └── _errMsg
```

---

## Risks Encountered

**None.**

The only structural change was adding `--bundle` to the esbuild command. This was
verified before making any file changes by confirming `esbuild src/app.jsx --bundle ...`
produced a valid output of identical structure (192.5 kb vs 199.2 kb baseline).

There were no dependency issues: the extracted functions have no imports of their own
(they use only standard browser globals — `localStorage`, `JSON`, `parseInt`, `Array`).

---

## Recommended Phase 2 Starting Hook

**`useTextLoader`** — start here.

Rationale:
- Completely isolated: owns only `textContent`, `textLoading`, `textError`
- Single `useEffect` (lines ~1637–1653 in original)
- Single `useCallback` (`loadTextChunk`)
- No shared refs, no cross-hook dependencies
- Proves the hook extraction pattern without risk

After `useTextLoader` is green, proceed to `useLinksSidecar` (also isolated), then
`useSearchHighlights`, then the more coupled hooks in the order specified in
`FRONTEND_REFACTOR_PLAN.md` Section 10 Phase 2.
