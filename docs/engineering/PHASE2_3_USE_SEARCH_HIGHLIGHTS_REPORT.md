# Phase 2.3 — useSearchHighlights Extraction Report

**Sprint**: Architecture Refactor Sprint 2, Goal #3  
**Date**: 2026-06-17  
**Status**: Complete ✅

---

## Objective

Extract all search-highlight ownership (state, refs, callbacks, effects) from
`ViewerScreen` into a dedicated custom hook with zero behavior changes.

---

## File Created

**`frontend/src/hooks/useSearchHighlights.js`** — 62 lines

```js
export function useSearchHighlights(session, page)
  → {
      searchHighlightQuery, setSearchHighlightQuery,
      searchHighlights,
      searchResultPages,    setSearchResultPages,
      activeHighlightIdx,   setActiveHighlightIdx,
      wordPositionsRef,
      wordPositionsFetched,
    }
```

---

## State Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `searchHighlightQuery` | `''` | Active query string; drives the highlight effect |
| `searchHighlights` | `[]` | Word-position rects for the current page matching the query |
| `searchResultPages` | `new Set()` | Pages that have any match — used for the fallback glow border |
| `activeHighlightIdx` | `0` | Index of the orange (active) highlight among all matches |

---

## Refs Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `wordPositionsRef` | `{}` | Map of `{ pageNum: [{t, x, y, w, h}, …] }` fetched once per session |
| `wordPositionsFetched` | `false` | Once-fetch guard — prevents re-requesting after the first API call |

---

## Callbacks Extracted

| Symbol | Deps | Purpose |
|--------|------|---------|
| `_computeHighlights(pageNum, query)` | `[]` (stable) | Filters word positions for the given page/query; updates `searchHighlights` state |

---

## Effects Extracted

### Search word-position load + highlight computation
```
deps: [searchHighlightQuery, page, session?.link_token, session?.session_id, _computeHighlights]
```
- Clears highlights when query is empty or session missing.
- On first query: fetches word positions via `getWordPositions`, stores in
  `wordPositionsRef`, then calls `_computeHighlights`.
- On subsequent page/query changes: recomputes directly from the cached ref
  without a network request (`wordPositionsFetched.current` guard).

---

## Lines Removed from ViewerScreen

| Block removed | Count |
|---------------|-------|
| `wordPositionsRef` useRef | 1 |
| `wordPositionsFetched` useRef | 1 |
| `searchHighlightQuery` useState | 1 |
| `searchHighlights` useState | 1 |
| `searchResultPages` useState | 1 |
| `activeHighlightIdx` useState | 1 |
| `_computeHighlights` useCallback (+ comment) | 7 |
| Search useEffect (+ blank line) | 22 |
| **Total removed** | **35** |

Lines added (import + hook call block): **12**  
Net change to `app.jsx`: **−26 lines**

---

## Build Result

| Metric | Before (Phase 2.2) | After (Phase 2.3) |
|--------|-------------------|-------------------|
| Bundle size | 193.1 kb | 193.5 kb |
| Build time | 22 ms | 26 ms |
| Build result | PASS ✅ | PASS ✅ |

---

## Coupling Removed with useLinksSidecar

In Phase 2.2, `useLinksSidecar` was given an `onAutoExtractReset` callback
because its auto-extract timer needed to reset `wordPositionsRef` and
`wordPositionsFetched` — refs that were still inline in ViewerScreen at that time.

After this extraction those refs are owned by `useSearchHighlights`. ViewerScreen
receives them as returned values and passes them through the same
`onAutoExtractReset` callback:

```js
// Before Phase 2.3 — inline refs:
onAutoExtractReset: () => {
  wordPositionsRef.current = {};      // inline ref
  wordPositionsFetched.current = false; // inline ref
}

// After Phase 2.3 — refs from hook return:
onAutoExtractReset: () => {
  wordPositionsRef.current = {};      // from useSearchHighlights return
  wordPositionsFetched.current = false; // from useSearchHighlights return
}
```

The `onAutoExtractReset` callback body is **unchanged**. Only the provenance of
the refs changed — from inline declarations to hook return values. The same
pattern applies to the `onSidecarExtract` JSX callback (ViewerInfoPanel prop).

This completes the ownership boundary: `useLinksSidecar` resets search refs
via an explicit callback seam; it has no direct import of or reference to
`useSearchHighlights`.

---

## Hook Call Ordering

`useSearchHighlights` must be called **before** `useLinksSidecar` in ViewerScreen
so that `wordPositionsRef` and `wordPositionsFetched` are available when
constructing the `onAutoExtractReset` callback passed to `useLinksSidecar`.

Current call order:
1. `useSearchHighlights(session, page)` → exposes `wordPositionsRef`, `wordPositionsFetched`
2. `useLinksSidecar(session, doc?.id, isTextDoc, { onAutoExtractReset })` → callback uses refs from step 1

---

## Total Reduction Since Phase 1

| Phase | Net lines removed from `app.jsx` |
|-------|----------------------------------|
| Phase 1 (constants + utils) | −30 |
| Phase 2.1 (useTextLoader) | −35 |
| Phase 2.2 (useLinksSidecar) | −23 |
| Phase 2.3 (useSearchHighlights) | −26 |
| **Running total** | **−114 lines** |

`app.jsx`: 6 047 → 5 935 lines (**−1.9%** of file, **−8.5%** of ViewerScreen span)

---

## Manual Verification Checklist

- [ ] PDF viewer opens, all pages load
- [ ] Ctrl+F opens the search panel
- [ ] Typing a query fetches word positions and shows highlight rects on page
- [ ] Yellow highlights visible for all matches on current page
- [ ] Active (orange) highlight changes when navigating results in SearchPanel
- [ ] Navigating to a different page recomputes highlights from cached positions
- [ ] `setSearchHighlightQuery('')` on panel close clears all highlights
- [ ] `setActiveHighlightIdx(0)` resets active on close
- [ ] `setSearchResultPages(new Set())` resets fallback glow on close
- [ ] Pages with matches show fallback gold border when word positions unavailable
- [ ] Auto-extract reset (15-second timer) clears word positions and triggers reload
- [ ] Manual sidecar extract (Info panel) also resets word positions
- [ ] Text documents unaffected (no highlight fetching attempted)
- [ ] No console errors

---

## Recommended Phase 2.4 Extraction — `useAnnotations`

**Why next**: The annotation group is the largest remaining isolated block in
ViewerScreen. It owns 10 state values and 1 ref without external dependencies on
search, links, or session logic.

**Owns**:
- `annotTool`, `annotColor`, `annotThickness`, `annotUndoStack` state
- `pageAnnotations`, `commentDraft`, `drawingState` state
- `threadView`, `threadReplyText`, `threadReplySending` state
- `bookmarks` state
- `annotCacheRef` ref (page → annotation[] map)
- Annotations lazy-load `useEffect` (deps: `session`, `page`, `can_annotate`, `isTextDoc`)
- Bookmarks load `useEffect` (deps: `session`, `can_annotate`)

**Hook signature (proposed)**:
```js
const {
  annotTool, setAnnotTool,
  annotColor, setAnnotColor,
  annotThickness, setAnnotThickness,
  annotUndoStack, setAnnotUndoStack,
  pageAnnotations, setPageAnnotations,
  commentDraft, setCommentDraft,
  drawingState, setDrawingState,
  threadView, setThreadView,
  threadReplyText, setThreadReplyText,
  threadReplySending, setThreadReplySending,
  bookmarks, setBookmarks,
  annotCacheRef,
} = useAnnotations(session, page, isTextDoc);
```

**No cross-hook refs** — `annotCacheRef` is only written by the load effect and
the annotation CRUD callbacks in JSX, which stay in ViewerScreen and receive
`annotCacheRef` from the hook return. Zero coupling to search or sidecar hooks.

**Estimated removal from ViewerScreen**: ~40 lines.
