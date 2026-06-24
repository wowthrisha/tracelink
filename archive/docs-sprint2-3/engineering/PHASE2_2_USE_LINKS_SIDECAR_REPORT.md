# Phase 2.2 — useLinksSidecar Extraction Report

**Sprint**: Architecture Refactor Sprint 2, Goal #3  
**Date**: 2026-06-17  
**Status**: Complete ✅

---

## Objective

Extract hyperlink sidecar state, refs, and effects from `ViewerScreen` into a
dedicated custom hook with zero behavior changes.

---

## File Created

**`frontend/src/hooks/useLinksSidecar.js`** — 68 lines

```js
export function useLinksSidecar(session, docId, isTextDoc, { onAutoExtractReset } = {})
  → { pageLinksRef, linksLoaded, setLinksLoaded,
      visitedLinks, setVisitedLinks,
      sidecarExtracted, setSidecarExtracted }
```

---

## State Extracted

| Symbol | Type | Initial | Purpose |
|--------|------|---------|---------|
| `linksLoaded` | state | `false` | Signals that the sidecar fetch has completed (success or failure) |
| `visitedLinks` | state | `new Set()` | URLs the viewer has already clicked/opened |
| `sidecarExtracted` | state | `false` | Toast-once flag for manual sidecar extraction |

---

## Refs Extracted

| Symbol | Type | Initial | Purpose |
|--------|------|---------|---------|
| `pageLinksRef` | `useRef({})` | `{}` | Map of `{pageNum: [{x, y, w, h, url, …}]}` built from API response |
| `autoExtractAttempted` | `useRef(false)` | `false` | Fire-once guard — prevents re-extraction when backend already extracted |

---

## Effects Extracted

### Effect 1 — Sidecar load on session activation
```
deps: [session?.link_token, session?.session_id, isTextDoc]
```
Calls `getDocumentLinks`, builds the per-page link map into `pageLinksRef.current`,
sets `autoExtractAttempted.current = true` if the backend reports extraction was
already done, then sets `linksLoaded = true`. Skips entirely for text documents.

### Effect 2 — Auto-extract for pre-feature documents
```
deps: [linksLoaded, docId]
```
If the sidecar was not previously extracted (i.e. `autoExtractAttempted.current`
is still false after load), calls `extractSidecars`. Schedules a 15-second
`setTimeout` to clear `pageLinksRef.current`, set `linksLoaded = false`, and
call `onAutoExtractReset()` — which allows ViewerScreen to simultaneously reset
its still-inline search word-position refs. Returns a cleanup to cancel the timer.

---

## Lines Removed from ViewerScreen

| Block removed | Count |
|---------------|-------|
| `visitedLinks` useState | 1 |
| `sidecarExtracted` useState | 1 |
| `pageLinksRef` useRef | 1 |
| `linksLoaded` useState | 1 |
| `autoExtractAttempted` useRef | 1 |
| Sidecar-load useEffect (+ comment) | 14 |
| Auto-extract useEffect (+ comment) | 17 |
| **Total removed** | **36** |

Lines added (import + hook call with callback): **15**  
Net change to `app.jsx`: **−23 lines**

---

## Build Result

| Metric | Before (Phase 2.1) | After (Phase 2.2) |
|--------|-------------------|-------------------|
| Bundle size | 192.7 kb | 193.1 kb |
| Build time | 21 ms | 22 ms |
| Build result | PASS ✅ | PASS ✅ |

Bundle grows 0.4 kb — expected from hook file module boilerplate.

---

## Cross-Hook Dependency — Design Decision

The auto-extract effect's 15-second reset timer originally contained:
```js
wordPositionsRef.current = {};
wordPositionsFetched.current = false;
```

These two refs belong to the search system (not yet extracted — will be Phase 2.3).
Rather than importing them into the sidecar hook (which would create tight coupling),
or leaving the effect split across two locations, the hook accepts an optional
`onAutoExtractReset` callback:

```js
useLinksSidecar(session, doc?.id, isTextDoc, {
  onAutoExtractReset: () => {
    wordPositionsRef.current = {};
    wordPositionsFetched.current = false;
  },
})
```

ViewerScreen constructs this callback inline with access to its own still-inline
refs. The callback receives no arguments and has no return value. If omitted, the
hook is a safe no-op (`onAutoExtractReset?.()` optional call).

When Phase 2.3 extracts `useSearchHighlights`, that hook will return
`wordPositionsRef` and `wordPositionsFetched`. The `onAutoExtractReset` callback
in ViewerScreen will then reference those returned values instead of inline refs —
zero changes to the hook itself.

---

## React UMD Compatibility

Follows the standing constraint established in Phase 2.1:

```js
// React hooks via UMD CDN global (no npm react package).
const { useState, useRef, useEffect } = React;
```

No `import from 'react'` — the React 18 UMD bundle sets `window.React` via
`<script>` tag; there is no `react` npm package in this project.

---

## Manual Verification Checklist

- [ ] PDF viewer opens, pages load
- [ ] Links panel button shows correct link count for current page
- [ ] Links panel opens, all page links listed
- [ ] Clicking a link marks it visited (checkbox checked, strikethrough)
- [ ] Visited state persists across page navigation within session
- [ ] Navigating away and back to same page preserves visited state
- [ ] Auto-extract fires for docs without sidecars (15-second timer → links reload)
- [ ] Manual extract via Info panel still triggers `setSidecarExtracted(true)`
- [ ] `onSidecarExtract` callback resets link and search caches correctly
- [ ] Text documents (.txt/.md/.log) not affected — no sidecar fetch attempted
- [ ] No console errors on mount, navigation, or link panel open/close

---

## Recommended Phase 2.3 Extraction — `useSearchHighlights`

**Why next**: Clean isolation — owns search-specific state and refs, no mutation
from outside except the reset in `onAutoExtractReset` (which will become a clean
ref return after this extraction).

**Owns**:
- `searchHighlightQuery` state
- `searchHighlights` state (word-position rects for current page)
- `searchResultPages` state (Set of pages with any match)
- `activeHighlightIdx` state
- `wordPositionsRef` ref (Map of pageNum → word positions)
- `wordPositionsFetched` ref (once-fetch guard)
- `_computeHighlights` useCallback
- Search word-positions useEffect

**Hook signature (proposed)**:
```js
const {
  wordPositionsRef,
  wordPositionsFetched,
  searchHighlights,
  searchResultPages,
  activeHighlightIdx,
  setActiveHighlightIdx,
  setSearchHighlightQuery,
  setSearchResultPages,
} = useSearchHighlights(session, page, searchHighlightQuery);
```

After this extraction, the `onAutoExtractReset` callback in ViewerScreen can
reference `wordPositionsRef` and `wordPositionsFetched` from the hook's return
value instead of inline refs — completing the ref ownership boundary cleanly.

**Estimated removal from ViewerScreen**: ~35 lines.
