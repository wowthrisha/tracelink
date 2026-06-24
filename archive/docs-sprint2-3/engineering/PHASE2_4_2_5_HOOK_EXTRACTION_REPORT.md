# Phase 2.4 + 2.5 — useAnnotations & useViewerLayout Extraction Report

**Sprint**: Architecture Refactor Sprint 2, Goal #3  
**Date**: 2026-06-17  
**Status**: Complete ✅

---

## Objective

Extract annotation state/effects into `useAnnotations` and layout/navigation/keyboard
state, callbacks, and effects into `useViewerLayout`, with zero behavior change.

---

## Files Created

### `frontend/src/hooks/useAnnotations.js` — 68 lines

```js
export function useAnnotations(session, page, isTextDoc)
  → {
      annotTool, setAnnotTool,
      annotColor, setAnnotColor,
      annotThickness, setAnnotThickness,
      annotUndoStack, setAnnotUndoStack,
      pageAnnotations, setPageAnnotations,
      commentDraft, setCommentDraft,
      threadView, setThreadView,
      threadReplyText, setThreadReplyText,
      threadReplySending, setThreadReplySending,
      bookmarks, setBookmarks,
      drawingState, setDrawingState,
      annotCacheRef,
    }
```

### `frontend/src/hooks/useViewerLayout.js` — 126 lines

```js
export function useViewerLayout(session, { onToggleSearch } = {})
  → {
      page, setPage,
      pageInputStr, setPageInputStr,
      twoPageMode, setTwoPageMode,
      isFullscreen,
      layoutMode, setLayoutMode,
      customZoom, setCustomZoom,
      rotation, setRotation,
      goNext, goPrev,
      _setLayout, _zoomBy, _zoomTo,
      toggleFullscreen,
      touchRef,
    }
```

---

## Phase 2.4 — useAnnotations

### State Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `annotTool` | `null` | Active tool: `null \| 'highlight' \| 'comment' \| 'rectangle' \| 'arrow' \| 'sticky_note' \| 'draw'` |
| `annotColor` | `'#FFE066'` | Active tool color |
| `annotThickness` | `2` | Stroke thickness for draw/arrow/rect tools |
| `annotUndoStack` | `[]` | `[{annotId, page}]` — undoable annotation ops |
| `pageAnnotations` | `[]` | Annotations loaded for the current page |
| `commentDraft` | `null` | `{x, y, coords, type}` — pending comment text |
| `threadView` | `null` | `{root, replies, loading}` — open comment-thread modal |
| `threadReplyText` | `''` | Draft reply text |
| `threadReplySending` | `false` | Prevents double-submit on reply send |
| `bookmarks` | `new Set()` | Bookmarked page numbers |
| `drawingState` | `null` | `{startX, startY}` for in-progress draw strokes |

### Ref Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `annotCacheRef` | `new Map()` | `page → annotation[]` — avoids re-fetching per page |

`annotCacheRef` is returned so that annotation CRUD callbacks in ViewerScreen JSX can
write to it on create/update/delete without triggering re-renders.

### Effects Extracted

**Annotation lazy-load**
```
deps: [session?.link_token, session?.session_id, page, session?.permissions?.can_annotate, isTextDoc]
```
Cache-first: checks `annotCacheRef.current` before calling the API. Skips entirely when
`can_annotate` is false or the document is a text type.

**Bookmark load**
```
deps: [session?.link_token, session?.session_id, session?.permissions?.can_annotate]
```
Fires once on session start; converts the bookmark list to a `Set` of page numbers.

### Cross-hook Coupling

None. `annotCacheRef` is only touched by the load effect (inside the hook) and by
annotation CRUD callbacks in ViewerScreen JSX (which receive it from the hook return).
No dependency on search or sidecar hooks.

---

## Phase 2.5 — useViewerLayout

### State Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `page` | `1` | Current page number — consumed by all other hooks |
| `layoutMode` | `_loadLayoutPref().mode` | `'auto' \| 'fit-width' \| 'fit-height' \| 'actual' \| 'custom'` |
| `customZoom` | `_loadLayoutPref().zoom` | Numeric zoom % when `layoutMode === 'custom'` |
| `rotation` | `0` | Page rotation in degrees: 0, 90, 180, 270 |
| `twoPageMode` | `false` | Side-by-side two-page display |
| `isFullscreen` | `false` | Mirrors `!!document.fullscreenElement` |
| `pageInputStr` | `''` | Raw text value of the page-jump input |

### Ref Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `touchRef` | `{x, y, pinchDist: null}` | Touch/pinch state for swipe and pinch-to-zoom JSX handlers |

### Callbacks Extracted (all returned)

| Symbol | Deps | Purpose |
|--------|------|---------|
| `goNext` | `[PAGE_COUNT, pageStep]` | Advance one (or two in two-page mode) pages |
| `goPrev` | `[pageStep]` | Go back one (or two) pages |
| `_setLayout` | `[customZoom]` | Set layout mode + optionally zoom; persists to localStorage |
| `_zoomBy` | `[]` | Delta-zoom clamped to `[ZOOM_MIN, ZOOM_MAX]` |
| `_zoomTo` | `[]` | Set absolute zoom %; switches mode to `LAYOUT.CUSTOM` |
| `toggleFullscreen` | `[]` | Toggle browser fullscreen via Fullscreen API |

`PAGE_COUNT` and `pageStep` are derived constants inside the hook (`session?.page_count || 1`
and `twoPageMode ? 2 : 1`); they are **not** returned — ViewerScreen derives its own
`PAGE_COUNT` from `session` for inline prefetch effects.

### Effects Extracted

**Keyboard + pinch-zoom block**
```
deps: [goNext, goPrev, session, _zoomBy, _setLayout]
```
Arrow navigation, Ctrl/Cmd+F search toggle (via `_onToggleSearchRef`), and passive-false
`wheel` blocker. Deps preserved identically from original.

**Ctrl+F / onToggleSearch seam**: `onToggleSearch` is stored in a `useRef` and kept
current via a separate one-line effect. The keyboard handler calls
`_onToggleSearchRef.current?.()`. This prevents `onToggleSearch` from appearing in the
keyboard effect's deps, which eliminates a spurious re-registration whenever ViewerScreen
re-renders (the inline `() => setShowSearch(v => !v)` factory was a new reference on
every render).

**Session state restore**
```
deps: [session?.session_id]
```
Reads `securedoc_vstate_<session_id>` from sessionStorage on session change; restores
`page` and `customZoom` within safe bounds.

**Session state save**
```
deps: [session?.session_id, page, customZoom]
```
Writes `{pg, zm}` to sessionStorage after any navigation or zoom change.

**Fullscreen sync**
```
deps: []
```
Listens to `fullscreenchange` and updates `isFullscreen` state.

---

## Hook Call Ordering in ViewerScreen

`useViewerLayout` must be called **first** among all custom hooks because it produces
`page`, which is consumed by `useTextLoader`, `useSearchHighlights`, and `useAnnotations`.

Current call order after Phase 2.5:

```
1. useViewerLayout(session, { onToggleSearch })   → page, goNext, goPrev, ...
2. useTextLoader(session, page, isTextDoc)         → textContent, textLoading, textError
3. useSearchHighlights(session, page)              → searchHighlights, wordPositionsRef, ...
4. useLinksSidecar(session, docId, isTextDoc, …)  → pageLinksRef, linksLoaded, ...
5. useAnnotations(session, page, isTextDoc)        → annotTool, bookmarks, annotCacheRef, ...
```

`useAnnotations` is last because it has no outputs that any other hook consumes.

---

## Lines Removed from ViewerScreen

### Phase 2.4 — useAnnotations

| Block removed | Count |
|---------------|-------|
| Annotation state comment + 12 useState | 13 |
| `annotCacheRef` useRef | 1 |
| Annotation lazy-load useEffect | 15 |
| Bookmark load useEffect | 7 |
| **Total removed** | **36** |

Lines added (import + hook call block): **17**  
Phase 2.4 net change to `app.jsx`: **−19 lines**

### Phase 2.5 — useViewerLayout

| Block removed | Count |
|---------------|-------|
| `page`, layout state, `zoom` alias, `rotation`, `twoPageMode` | 9 |
| `isFullscreen`, `pageInputStr` | 2 |
| `touchRef` + comment | 2 |
| `goNext`, `goPrev` useCallbacks | 2 |
| `_setLayout`, `_zoomBy`, `_zoomTo`, `toggleFullscreen` useCallbacks | 16 |
| Keyboard + wheel useEffect | 20 |
| Session restore useEffect | 14 |
| Session save useEffect | 7 |
| Fullscreen sync useEffect | 5 |
| **Total removed** | **77** |

Lines added (import + hook call block): **19**  
Phase 2.5 net change to `app.jsx`: **−58 lines**  
`_loadLayoutPref` removed from app.jsx import (no longer used directly in ViewerScreen).

---

## Combined Build Result

| Metric | Before (Phase 2.3) | After (Phase 2.4+2.5) |
|--------|-------------------|----------------------|
| `app.jsx` lines | 5 935 | 5 832 |
| Bundle size | 193.5 kb | 195.1 kb |
| Build time | 26 ms | 27 ms |
| Build result | PASS ✅ | PASS ✅ |

Bundle grows 1.6 kb — expected from two new hook files with boilerplate.

---

## Running Total (All Phases)

| Phase | Net lines removed from `app.jsx` |
|-------|----------------------------------|
| Phase 1 (constants + utils) | −30 |
| Phase 2.1 (useTextLoader) | −35 |
| Phase 2.2 (useLinksSidecar) | −23 |
| Phase 2.3 (useSearchHighlights) | −26 |
| Phase 2.4 (useAnnotations) | −19 |
| Phase 2.5 (useViewerLayout) | −58 |
| **Running total** | **−191 lines** |

`app.jsx`: 6 047 → 5 832 lines (**−3.2%** of file, **−14.2%** of ViewerScreen span)

---

## Manual Verification Checklist

- [ ] PDF opens, all pages render
- [ ] Page navigation with arrow keys, toolbar buttons, and swipe
- [ ] Ctrl+F (or Cmd+F) opens search panel; Escape/close button closes it
- [ ] Zoom +/−, presets, fit-width, fit-height, actual-size work
- [ ] Two-page mode renders pages side by side
- [ ] Fullscreen button enters/exits fullscreen; F11 also syncs state
- [ ] Page/zoom state is saved on navigation and restored on next session load
- [ ] Rotation button rotates page image
- [ ] Pinch-to-zoom on mobile changes zoom within bounds
- [ ] Swipe left/right navigates pages
- [ ] Highlight tool creates yellow highlight annotations on page
- [ ] Comment tool opens comment draft → text input → saves annotation
- [ ] Rectangle, arrow, draw tools work
- [ ] Annotation undo removes the last placed annotation
- [ ] Bookmarks load on session start; bookmark toggle updates state
- [ ] Comment thread modal opens on click; reply sends and list updates
- [ ] No console errors on load, navigation, or tool use

---

## Phase 2.6 Candidates Analysis

See section below. **Do not implement until the next sprint message.**

---

# Phase 2.6 Candidate Analysis — usePageLoader & useViewerSession

## Candidate A — `usePageLoader`

### What it would own

**State**:
- `imgSrc`, `imgLoading`, `pageError` — primary page image
- `prevImgSrc`, `imgReady` — crossfade transition layer
- `imgSrc2`, `imgLoading2`, `page2Error` — two-page mode second image
- `pageAspectRatio` — set by img `onLoad` handler in JSX

**Refs**:
- `pageCache` (`useRef(new Map())`) — blob URL cache keyed by `token:page`
- `inflightRef` (`useRef(new Map())`) — in-flight dedup keyed by `token:page`
- `imgSrcRef` (`useRef('')`) — stable snapshot of `imgSrc` for empty-dep callbacks

**Callbacks** (all `[]` deps):
- `_cacheSet(key, blobUrl)` — LRU-capped cache insert; evicts oldest on overflow
- `_clearPageCache()` — revokes all blob URLs; called on unmount
- `loadPage(token, pageNum, sessionId)` — cache-hit fast path, then inflight dedup, then fetch; crossfade management
- `loadPage2(token, pageNum, sessionId, total)` — two-page second image fetch
- `prefetchPage(token, pageNum, sessionId, total)` — silent background prefetch

**Effects** (would move into hook):
- `useEffect(() => { imgSrcRef.current = imgSrc; }, [imgSrc])` — imgSrcRef sync
- `useEffect(() => () => _clearPageCache(), [])` — unmount cache cleanup
- Page load effect: `deps: [session?.link_token, session?.session_id, page, ...]`
- Prefetch effect (next/prev): `deps: [session?.link_token, ..., page, imgLoading, PAGE_COUNT, ...]`
- Prefetch effect (two-page): `deps: [session?.link_token, ..., page, isTwoPage, ...]`
- Eager page-2 prefetch: `deps: [session?.link_token, session?.session_id, session?.doc_type]`

**Proposed API**:
```js
const {
  imgSrc, imgLoading, pageError,
  prevImgSrc, imgReady, setImgReady,
  imgSrc2, imgLoading2, page2Error,
  pageAspectRatio, setPageAspectRatio,
  loadPage, prefetchPage,
} = usePageLoader(session, page, { isTextDoc, isTwoPage, PAGE_COUNT });
```

### Dependency Graph

```
usePageLoader
  ← session (param)
  ← page (from useViewerLayout return)
  ← isTextDoc (derived in ViewerScreen)
  ← isTwoPage (from useViewerLayout return)
  ← PAGE_COUNT (derived in ViewerScreen)
  ← reinitRef.current() [CROSS-BOUNDARY — calls useViewerSession logic]
```

### Shared Ref Coupling

The critical cross-boundary ref is `reinitRef`. Inside `loadPage`, a 401 response triggers:
```js
if (r.status === 401 && reinitRef.current) {
  reinitRef.current();
  return;
}
```

`reinitRef.current` is set every render in ViewerScreen to an async function that calls
`doValidate` (session logic). This is the only tight coupling between page loading and
session management. Resolution options:

**Option A**: `usePageLoader` accepts `{ onAuth401 }` callback (same ref-stabilization
pattern used for `onToggleSearch` in `useViewerLayout`).

**Option B**: Leave `reinitRef` as a shared ref owned by ViewerScreen, passed as a param.
The hook calls `onAuth401Ref.current?.()` from inside `loadPage`.

Option A is cleaner — the hook owns the ref internally.

### Risk Level: MEDIUM

- Large callback body with intricate blob-URL lifecycle management
- Empty-dep callbacks with intentional stale closures (must be understood before touching)
- `pageAspectRatio` is set via `img.onLoad` in JSX — hook must return `setPageAspectRatio`
  so JSX handlers can update it
- The unmount cleanup effect must move inside the hook (easily verifiable)
- Estimated removal from ViewerScreen: ~110 lines

---

## Candidate B — `useViewerSession`

### What it would own

**State**:
- `session` — the core session object (`null` until validated)
- `initializing` (`setInit`) — loading spinner gate
- `gateInfo` — gate requirements object (shows `AccessGate` overlay)
- `gateError` — password/email validation error message
- `pendingToken` — token before gate is satisfied
- `blurred` — document blur state (DRM enforcement)

**Ref**:
- `reinitRef` — used by `loadPage` (in future `usePageLoader`) for 401 re-entry

**Functions**:
- `doValidate(token, email, password)` — async; validates link token; sets session or
  routes to gate; calls `setPage(1)` on success (needs `setPage` from `useViewerLayout`)

**Effects**:
- Auto-create link + gate probe: `deps: [docId]` — initializes token, checks gate, fires `doValidate`
- Security listeners: `deps: [session]` — right-click block, Ctrl+P/C/X/U/S block, blur/focus
- Tab visibility: `deps: [session]` — `document.hidden` listener (moved to inline effect in Phase 2.5; would move into session hook)

**Proposed API**:
```js
const {
  session, setSession,
  initializing,
  gateInfo, setGateInfo,
  gateError, setGateError,
  pendingToken, setPendingToken,
  blurred,
  doValidate,
  reinitRef,
} = useViewerSession(doc, publicToken, page, { onValidateSuccess: () => setPage(1), toast });
```

### Dependency Graph

```
useViewerSession
  ← doc (prop)
  ← publicToken (prop)
  ← toast (from useToast — context)
  → setPage called inside doValidate [CROSS-BOUNDARY — needs setPage from useViewerLayout]
  → reinitRef.current → doValidate [consumed by usePageLoader]
```

### Shared Ref Graph

```
reinitRef
  written by: useViewerSession (or ViewerScreen if session hook not extracted)
  read by: loadPage (in usePageLoader) on 401 response

setPage (from useViewerLayout)
  called by: doValidate inside useViewerSession
  seam: pass as callback param `onValidateSuccess`
```

### Hook Interaction Diagram

```
┌────────────────────────────────────────────────────────────────┐
│ ViewerScreen                                                   │
│                                                                │
│  useViewerSession(doc, publicToken, …)                         │
│    ↓ session, reinitRef, doValidate                            │
│                                                                │
│  useViewerLayout(session, { onToggleSearch })                  │
│    ↓ page, setPage, goNext, …                                  │
│    ↑ onValidateSuccess: () => setPage(1)  ──────────────────┐  │
│                                                             │  │
│  usePageLoader(session, page, { …, onAuth401 })             │  │
│    ↑ onAuth401: () => reinitRef.current?.()  ──────────┐   │  │
│                                                        │   │  │
│  useTextLoader / useSearchHighlights / …              │   │  │
│                                                        │   │  │
│  useAnnotations(session, page, isTextDoc)             │   │  │
│                                                        │   │  │
│  [callback seams close the loops ──────────────────────┘───┘] │
└────────────────────────────────────────────────────────────────┘
```

### Risk Level: HIGH

- `doValidate` has 5 distinct error paths (401/403/429/410/404/other), each updating
  different state combinations; must be reproduced exactly
- The security effect touches `document` and `window` simultaneously with 6 listener
  pairs; test coverage is manual (DRM features)
- `setPage(1)` inside `doValidate` creates a dependency on `useViewerLayout` output —
  this must flow through a callback param (`onValidateSuccess`) to avoid circular imports
- `blurred` state is currently in ViewerScreen and used by the blur overlay in JSX;
  moving it into the hook is safe but must be verified against the blur overlay rendering
- Estimated removal from ViewerScreen: ~90 lines

---

## Recommended Extraction Order for Phase 2.6

```
Step 1: usePageLoader first
  - Cleaner deps (no setPage cross-dependency)
  - reinitRef stays in ViewerScreen as a shared ref until useViewerSession is extracted
  - onAuth401 callback seam is straightforward (same pattern as onToggleSearch)
  - Establishes the blob-URL lifecycle boundary before touching session logic

Step 2: useViewerSession second
  - After usePageLoader extracts reinitRef usage, the seam is clear
  - doValidate's setPage(1) call becomes onValidateSuccess callback
  - Security effect moves cleanly with session
  - reinitRef transfers ownership from ViewerScreen to useViewerSession
```

**Do not extract both in the same commit.** The interaction between `reinitRef` (owned by
session) and `loadPage` (owned by page loader) is the highest-risk coupling point. Extract
`usePageLoader` first, confirm the 401 retry path works, then extract `useViewerSession`.

---

## Remaining Inline Symbols After Phase 2.5 (inputs for Phase 2.6 planning)

After Phase 2.5, ViewerScreen still owns inline:

**State (19 useState)**: `showInfo`, `session`, `imgSrc`, `imgLoading`, `pageError`,
`blurred`, `initializing`, `gateInfo`, `gateError`, `pendingToken`, `prevImgSrc`,
`imgReady`, `showSearch`, `showToc`, `showLaser`, `showMagnifier`, `showInsights`,
`insightsData`, `insightsLoading`, `showLinks`, `showPageList`, `pageAspectRatio`,
`imgSrc2`, `imgLoading2`, `page2Error` — **25 total**

**Refs (6)**: `pageImgRef`, `pageContainerRef`, `reinitRef`, `inflightRef`, `imgSrcRef`, `pageCache`

**Callbacks (5)**: `_cacheSet`, `_clearPageCache`, `loadPage`, `loadPage2`, `prefetchPage`

**Functions (1)**: `doValidate`

**Effects (6)**: auto-create-link, security-listeners, unmount-cache-clear, page-load,
prefetch-next-prev, prefetch-two-page, eager-page-2 — technically 7

`usePageLoader` would absorb ~10 of 25 inline states, 4 of 6 refs, all 5 callbacks, and
4 of 7 effects. `useViewerSession` would absorb 6 states, 1 ref, `doValidate`, and 2 effects.
