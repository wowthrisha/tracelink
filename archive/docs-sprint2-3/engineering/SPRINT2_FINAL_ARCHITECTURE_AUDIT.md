# Sprint 2 — Final Architecture Audit

**Date**: 2026-06-17  
**Scope**: Phases 1–2.7 (all hook extractions)  
**Build**: `196.4 kb` — PASS ✅  
**Source**: 6 047 → 5 525 lines (−522)  
**Purpose**: Verify no regressions introduced. Analysis only — no code changes.

---

## 1. Hook Dependency Graph

Each hook's inputs (what it reads) and outputs (what ViewerScreen receives back).

```
                    ┌────────────────────────────────────────────────────┐
                    │ ViewerScreen props                                 │
                    │   doc (object)   publicToken (string)   toast (fn) │
                    └──┬─────────────────────────────────────────────────┘
                       │
           ┌───────────▼───────────────────────────────────┐
           │ useViewerSession(doc, publicToken, {onValidated, toast})     │
           │  STATE: session, blurred, initializing,                     │
           │         gateInfo, gateError, pendingToken                    │
           │  REF:   reinitRef (401 re-auth entry point)                 │
           │  FN:    doValidate                                           │
           │  EMITS: session → all downstream hooks                      │
           └───────────┬───────────────────────────────────┘
                       │ session
           ┌───────────▼───────────────────────────────────┐
           │ useViewerLayout(session, {onToggleSearch})                   │
           │  STATE: page, layoutMode, customZoom, rotation,             │
           │         twoPageMode, isFullscreen, pageInputStr             │
           │  REF:   touchRef                                            │
           │  FN:    goNext, goPrev, _setLayout, _zoomBy, _zoomTo,       │
           │         toggleFullscreen, setPage                           │
           │  EMITS: page, twoPageMode → downstream hooks               │
           └───────┬───────────────────────────────────────┘
                   │ session, page
       ┌───────────▼───────────────────────┐
       │ useTextLoader(session, page, isTextDoc)        │
       │  STATE: textContent, textLoading, textError    │
       └────────────────────────────────────────────────┘
                   │ session, page, twoPageMode
       ┌───────────▼───────────────────────────────────────────────┐
       │ usePageLoader({session, page, twoPageMode, isTextDoc,      │
       │                onAuth401: () => reinitRef.current?.()})    │
       │  STATE: imgSrc, imgLoading, pageError, prevImgSrc,         │
       │         imgReady, imgSrc2, imgLoading2, page2Error,        │
       │         pageAspectRatio                                    │
       │  REF:   pageImgRef, pageContainerRef (→ JSX)              │
       │         inflightRef, imgSrcRef, pageCache (internal)       │
       └───────────────────────────────────────────────────────────┘
                   │ session, page
       ┌───────────▼──────────────────────────────────┐
       │ useSearchHighlights(session, page)              │
       │  STATE: searchHighlightQuery, searchHighlights, │
       │         searchResultPages, activeHighlightIdx   │
       │  REF:   wordPositionsRef, wordPositionsFetched  │
       │         (both returned — ViewerScreen mediates  │
       │          cross-hook reset with useLinksSidecar) │
       └──────────────────────────────────────────────┘
                   │ session, doc?.id, isTextDoc
       ┌───────────▼──────────────────────────────────────────┐
       │ useLinksSidecar(session, docId, isTextDoc,             │
       │                 {onAutoExtractReset})                  │
       │  STATE: linksLoaded, visitedLinks, sidecarExtracted    │
       │  REF:   pageLinksRef (→ JSX), autoExtractAttempted    │
       │  READS: wordPositionsRef, wordPositionsFetched via     │
       │         onAutoExtractReset callback from ViewerScreen  │
       └──────────────────────────────────────────────────────┘
                   │ session, page, isTextDoc
       ┌───────────▼──────────────────────────────────────────────────┐
       │ useAnnotations(session, page, isTextDoc)                       │
       │  STATE: annotTool, annotColor, annotThickness, annotUndoStack, │
       │         pageAnnotations, commentDraft, threadView,             │
       │         threadReplyText, threadReplySending, bookmarks,        │
       │         drawingState                                           │
       │  REF:   annotCacheRef                                         │
       └──────────────────────────────────────────────────────────────┘
```

---

## 2. Hook Interaction Graph

Interactions that cross hook boundaries (not just shared `session`/`page` params).

```
useViewerSession ──onAuth401 callback──► usePageLoader
  When: usePageLoader.loadPage receives 401
  Path: _onAuth401Ref.current?.() → reinitRef.current?.() → doValidate
  Clean: yes — stable ref chain, no closure over stale values

useViewerSession ──onValidated callback──► ViewerScreen._setPageRef → useViewerLayout.setPage
  When: doValidate succeeds
  Path: _onValidatedRef.current?.() → _setPageRef.current?.() → setPage(1)
  Clean: yes — two render-body ref assignments, always current

useViewerLayout ──onToggleSearch callback──► ViewerScreen.setShowSearch
  When: Ctrl+F / Cmd+F pressed in keyboard effect
  Path: _onToggleSearchRef.current?.() → () => setShowSearch(v => !v)
  Clean: yes — stable ref pattern

useSearchHighlights ──wordPositionsRef, wordPositionsFetched──► useLinksSidecar
  Direction: useLinksSidecar WRITES to refs owned by useSearchHighlights
  Path: onAutoExtractReset callback in ViewerScreen resets both refs directly
  Clean: yes — refs (not state) are synchronously mutable; reset is intentional
  Note: useLinksSidecar does not directly import useSearchHighlights; the
        coupling is mediated by ViewerScreen passing the callback

useViewerLayout ──session (dep)──► keyboard effect re-registers on session change
  Purpose: h() handler closes over session to gate Ctrl+F to session-only
  Impact: listeners re-register once when session becomes available
  Clean: yes — session changes at most twice (null→object per viewer open)
```

---

## 3. Circular Dependency Analysis

### Identified cycle: session ↔ setPage

```
useViewerSession produces: session
useViewerLayout needs:     session (as param)
useViewerLayout produces:  setPage
useViewerSession needs:    setPage (doValidate calls setPage(1) on success)
```

**Resolution implemented (Phase 2.7):**

```js
// ViewerScreen render body — synchronous, runs before any effects
const _setPageRef = useRef(null);

useViewerSession(doc, publicToken, {
  onValidated: () => _setPageRef.current?.()  // captures stable ref object
});

const { setPage } = useViewerLayout(session, ...);

_setPageRef.current = () => setPage(1);  // inject after layout hook runs
```

**Why it is correct**: `_setPageRef.current` is assigned synchronously in the render
body on every render. Effects fired by `doValidate` always run after the render
completes. Therefore `_setPageRef.current` is always `() => setPage(1)` before any
effect calls `_onValidatedRef.current?.()`.

**Verdict**: Cycle is broken correctly. No stale value risk.

### No other circular dependencies detected

All other hook parameters are unidirectional:
- `session` flows one direction: `useViewerSession` → all downstream hooks
- `page` flows one direction: `useViewerLayout` → `useTextLoader`, `usePageLoader`, `useSearchHighlights`, `useAnnotations`
- No hook imports from another hook file

---

## 4. Stale Closure Analysis

### useViewerSession — `reinitRef.current` (render body assignment)

```js
reinitRef.current = async () => {
  const token = session?.link_token || pendingToken;
  ...
};
```

**Status**: ✅ Correct. Assigned every render; always closes over current `session`
and `pendingToken`. Explicitly NOT in a `useEffect` — this is documented in the
hook and must stay this way.

**Risk if changed**: Moving to `useEffect` would make the closure one render stale.
On the first render after `setSession(null)`, `reinitRef.current` would still hold
the old session value, causing re-auth to use the wrong token.

### usePageLoader — `loadPage`, `prefetchPage`, `loadPage2` (empty `[]` deps)

These three `useCallback`s have `deps: []` and close over:
- `pageCache.current` — ref (always stable)
- `inflightRef.current` — ref (always stable)
- `imgSrcRef.current` — ref, synced by its own effect (always current before read)
- `_onAuth401Ref.current` — ref (stable-ref pattern)
- `_cacheSet` — `useCallback([], [])` (stable)
- State setters (`setImgSrc`, etc.) — React guarantees these are stable

**Status**: ✅ Correct. All values accessed through stable refs or stable setters.
No stale state values closed over directly.

### useViewerLayout — `_setLayout` with `[customZoom]` dep

```js
const _setLayout = useCallback((mode, zoom) => {
  ...
  _saveLayoutPref(mode, zoom !== undefined ? zoom : customZoom);
}, [customZoom]);
```

`customZoom` is closed over for the fallback case where `zoom` param is undefined.
This is correct — without `customZoom` in deps, `_setLayout()` calls (no explicit
zoom arg) would persist stale zoom.

**Status**: ✅ Correct. The dep is necessary.

### useViewerLayout — keyboard effect with `[_zoomBy, _setLayout]` in deps

The keyboard effect's handler body uses `goNext`, `goPrev`, `session`, and
`_onToggleSearchRef.current`. It does NOT use `_zoomBy` or `_setLayout` in the
handler body. They appear in the deps array but are not consumed.

**Status**: ⚠️ Pre-existing false deps (not introduced by Sprint 2). Impact:
keyboard and wheel listeners unnecessarily re-register when zoom changes. This is
functionally harmless — the handlers are identical each time — but wastes one
listener add/remove cycle per zoom change. No regression from refactor.

### useSearchHighlights — `wordPositionsFetched` ref written inside effect

```js
wordPositionsFetched.current = true;    // inside effect body before fetch
```

This guard ref prevents double-fetching. It is NOT in the dep array (refs never
are), which is correct.

**Status**: ✅ Correct. Ref mutation inside an effect is safe.

### useLinksSidecar — `onAutoExtractReset` callback in `[linksLoaded, docId]` effect

```js
useEffect(() => {
  if (!linksLoaded || !docId || autoExtractAttempted.current) return;
  ...
  const t = setTimeout(() => {
    ...
    onAutoExtractReset?.();
  }, 15000);
  return () => clearTimeout(t);
}, [linksLoaded, docId]);
```

`onAutoExtractReset` is NOT in the dep array. The callback is an inline arrow from
ViewerScreen: `() => { wordPositionsRef.current = {}; wordPositionsFetched.current = false; }`.
These writes go to refs (not state), so reading stale ref values is not possible —
refs are always current. The callback identity being stale doesn't matter because
it only writes, never reads.

**Status**: ✅ Acceptable. Writing to refs from a potentially-stale callback is
safe. The omission is intentional (callback would never meaningfully change).

---

## 5. Ref Ownership Audit

| Ref | Owner hook | Returned to ViewerScreen | Written by | Read by |
|-----|-----------|--------------------------|-----------|---------|
| `reinitRef` | useViewerSession | ✅ yes | useViewerSession render body | usePageLoader (via `onAuth401`) |
| `_setPageRef` | ViewerScreen | — | ViewerScreen render body | useViewerSession `_onValidatedRef` chain |
| `_onValidatedRef` | useViewerSession (internal) | no | bare useEffect | doValidate |
| `_onAuth401Ref` | usePageLoader (internal) | no | bare useEffect | loadPage |
| `_onToggleSearchRef` | useViewerLayout (internal) | no | bare useEffect | keyboard effect |
| `touchRef` | useViewerLayout | ✅ yes | JSX touch handlers | JSX touch handlers |
| `pageImgRef` | usePageLoader | ✅ yes | JSX `ref=` | JSX image handlers |
| `pageContainerRef` | usePageLoader | ✅ yes | JSX `ref=` | RectMagnifier JSX |
| `inflightRef` | usePageLoader (internal) | no | loadPage | loadPage (dedup guard) |
| `imgSrcRef` | usePageLoader (internal) | no | effect (synced to imgSrc) | loadPage crossfade |
| `pageCache` | usePageLoader (internal) | no | _cacheSet, _clearPageCache | loadPage, prefetchPage |
| `annotCacheRef` | useAnnotations | ✅ yes | annotation load effect | annotation load effect |
| `wordPositionsRef` | useSearchHighlights | ✅ yes | search effect, onAutoExtractReset | _computeHighlights |
| `wordPositionsFetched` | useSearchHighlights | ✅ yes | search effect, onAutoExtractReset | search effect guard |
| `pageLinksRef` | useLinksSidecar | ✅ yes | link load effect, auto-extract timer | JSX link overlay |
| `autoExtractAttempted` | useLinksSidecar (internal) | no | link load effect | auto-extract effect guard |

**Cross-hook write**: `wordPositionsRef` and `wordPositionsFetched` are owned by
`useSearchHighlights` but written by `useLinksSidecar` via `onAutoExtractReset`.
The refs are passed through ViewerScreen explicitly. This is the only cross-hook
ref mutation in the system. It is intentional, documented, and safe (ref writes are
synchronous and non-reactive).

---

## 6. Memory Leak Audit

### Blob URL lifecycle — usePageLoader

| Operation | Where | Leak risk |
|-----------|-------|-----------|
| `URL.createObjectURL(blob)` | `loadPage`, `prefetchPage`, `loadPage2` | Creates blob URL |
| `URL.revokeObjectURL(evicted)` | `_cacheSet` on LRU eviction | Freed on cap overflow |
| `URL.revokeObjectURL(url)` | `_clearPageCache` | Freed on unmount |
| Unmount cleanup: `useEffect(() => () => _clearPageCache(), [])` | usePageLoader | Triggered on unmount |

**Assessment**: ✅ All blob URLs are revoked either on LRU eviction (≤30 entries
always) or on component unmount. No leak path.

**Gap**: In-flight `fetch` promises in `inflightRef` are not aborted on unmount.
If the component unmounts while a page is mid-fetch, the fetch completes and calls
`setImgSrc`/`setImgLoading` on an unmounted component. React 18 no-ops setState on
unmounted components, so this causes no user-visible error. The blob URL from the
completed fetch is never stored in `pageCache` (cache was cleared on unmount) and
never revoked. **This is a minor pre-existing blob URL leak** — one per in-flight
request on unmount. Not introduced by Sprint 2.

### sessionStorage lifecycle

| Key | Written by | Cleared by | Leak risk |
|-----|-----------|-----------|-----------|
| `securedoc_sess_${token}` | doValidate (on success) | reinitRef.current (on 401), doValidate (on 410/404) | None — intentional persistence |
| `securedoc_vstate_${session_id}` | useViewerLayout save effect | None (accumulates per session_id) | Low — one tiny JSON object per session slot |

**Assessment**: ✅ No meaningful storage leak. Session viewer state entries are
small (two integers) and accumulate only for unique `session_id` values.

### Event listener lifecycle

See Section 7 below. All listeners have corresponding cleanup in `return () =>` functions.
No orphaned listeners detected.

### annotCacheRef (annotation cache)

`annotCacheRef.current` is a `Map<pageNum, annotation[]>`. It accumulates across
page navigation within a session. No explicit cleanup on unmount. Garbage-collected
when the component unmounts.

**Assessment**: ✅ Not a persistent leak — component-scoped Map released on unmount.

---

## 7. Event Listener Audit

### Complete listener inventory across all hooks

| # | Hook | Event | Target | deps array | Cleanup | Notes |
|---|------|-------|--------|-----------|---------|-------|
| 1 | useViewerLayout | `keydown` (h) | `window` | `[goNext, goPrev, session, _zoomBy, _setLayout]` | ✅ removeEventListener in return | Navigation + Ctrl+F |
| 2 | useViewerLayout | `wheel` (blockPinchZoom) | `window` | same as #1 | ✅ same return | `{passive: false}` — blocks pinch-zoom |
| 3 | useViewerLayout | `fullscreenchange` (h) | `document` | `[]` | ✅ removeEventListener | fullscreen state sync |
| 4 | useViewerSession | `contextmenu` (blockRC) | `document` | `[session]` | ✅ removeEventListener in return | Right-click DRM |
| 5 | useViewerSession | `keydown` (blockKB) | `document` | `[session]` | ✅ same return | Ctrl+P/C/X/A/U/S DRM |
| 6 | useViewerSession | `beforeprint` (onBP) | `window` | `[session]` | ✅ same return | Print DRM |
| 7 | useViewerSession | `afterprint` (onAP) | `window` | `[session]` | ✅ same return | Restore page visibility |
| 8 | useViewerSession | `blur` (onBlur) | `window` | `[session]` | ✅ same return | DRM blur overlay |
| 9 | useViewerSession | `focus` (onFocus) | `window` | `[session]` | ✅ same return | Remove blur overlay |
| 10 | useViewerSession | `visibilitychange` (onVis) | `document` | `[session]` | ✅ removeEventListener | Mobile tab-switch blur |

**No listener has a missing cleanup path.** All 10 are removed in `return` functions.

### Apparent keydown duplication — resolved

Both `useViewerLayout` (#1) and `useViewerSession` (#5) register `keydown` handlers.
These are distinct handlers on different targets (`window` vs `document`).

Event propagation order for keyboard events:
```
document.keydown (blockKB) fires FIRST
  → DRM: blocks Ctrl+P/C/X/A/U/S via preventDefault+stopPropagation
window.keydown (h) fires SECOND
  → Navigation: handles ArrowRight/Left/Up/Down and Ctrl+F only
```

`stopPropagation` on `document` prevents `window` from receiving the event for DRM
keys. The navigation handler (`h`) handles non-overlapping keys (arrows, Ctrl+F).
There is zero functional overlap.

**Verdict**: ✅ Not a duplication — two handlers with orthogonal responsibilities
on different targets. Correct behavior.

### wheel listener: `{passive: false}`

`useViewerLayout` registers the wheel handler with `passive: false` to allow
`preventDefault()` on pinch-zoom. This is correct but may generate a Chrome DevTools
warning ("Added non-passive event listener to a scroll-blocking 'wheel' event").
Pre-existing; not introduced by Sprint 2.

---

## 8. Session Recovery Audit

### Normal 401 recovery path

```
usePageLoader.loadPage → fetch 401
  └─► _onAuth401Ref.current?.()       [stable ref, always current]
        └─► () => reinitRef.current?.()  [ViewerScreen, passes ref object — stable]
              └─► reinitRef.current()    [async fn, closes over current session/pendingToken]
                    └─► getGateRequirements(token)
                          ├─ gate restricted → setSession(null), show AccessGate
                          └─ gate open → doValidate(token, null, null)
                                └─► setSession(newSession)
                                    _onValidatedRef.current?.()
                                      └─► _setPageRef.current?.() → setPage(1)
```

**Critical invariant**: `reinitRef.current` is the only ref assigned in a render
body (not in a hook's useEffect). This means it always closes over the current
values of `session` and `pendingToken` at render time.

**Verified**: The assignment `reinitRef.current = async () => {...}` appears at
line 77 of `useViewerSession.js`, in the function body (not inside a useEffect).

### Page restore vs page reset race

When `doValidate` succeeds, two effects are queued on the same render:
1. `useViewerSession`'s DRM effect (`deps: [session]`) — registers listeners
2. `useViewerLayout`'s state restore effect (`deps: [session?.session_id]`) — may call `setPage(pg)`
3. `setPage(1)` is called by `_onValidatedRef` inside the async `doValidate` body

**Order of execution** (React guarantees top-to-bottom effect registration order):
- `setPage(1)` fires synchronously within the async `doValidate` — queued as a state update
- React batches the render: new session, page=1
- Effects run: useViewerSession effects first, then useViewerLayout effects
- useViewerLayout restore effect reads `securedoc_vstate_${newSession.session_id}`:
  - For a fresh session: no saved state → page stays at 1 ✓
  - For a returning user: saved state may restore to a higher page ✓

**This matches the original behavior** (pre-refactor, both `setPage(1)` and the
restore effect ran in the same component, in the same order).

### Re-auth after gate restriction

If `reinitRef.current` shows a gate (requires_password), it calls:
```js
setSession(null);
setGateInfo(gate);
setPendingToken(token);
setInit(false);
```

`setSession(null)` causes all downstream hooks (usePageLoader, useSearchHighlights,
etc.) to return to their "no session" state (their effects guard on `if (!session)`).
AccessGate renders. User submits credentials → `doValidate(pendingToken, email, pw)`.
Session restored. Page resets to 1.

**Verdict**: ✅ Session recovery path is correct and matches pre-refactor behavior.

---

## 9. Cache Ownership Audit

### Blob URL page cache (usePageLoader)

- **Owner**: usePageLoader exclusively
- **Type**: `useRef(new Map())` — `token:pageNum → blobUrl`
- **Cap**: 30 entries (LRU eviction)
- **Shared**: No other hook touches pageCache
- **Cleanup**: `_clearPageCache` on unmount via `useEffect(() => () => _clearPageCache(), [])`
- **Eviction**: Oldest entry revoked via `URL.revokeObjectURL` when size > 30

### Annotation page cache (useAnnotations)

- **Owner**: useAnnotations exclusively
- **Type**: `useRef(new Map())` — `pageNum → annotation[]`
- **Cap**: Unbounded (accumulates across all navigated pages per session)
- **Shared**: No other hook touches annotCacheRef
- **Cleanup**: Garbage-collected on component unmount

### Word positions cache (useSearchHighlights)

- **Owner**: useSearchHighlights (primary), useLinksSidecar (reset-only)
- **Type**: `useRef({})` — `pageNum → word[]`
- **Cap**: Unbounded (one load per session — all pages fetched at once)
- **Shared**: useLinksSidecar resets via `wordPositionsRef.current = {}` through
  the `onAutoExtractReset` callback
- **Cleanup**: Garbage-collected on unmount

### sessionStorage (two namespaces, no hook conflict)

| Key pattern | Owner | Purpose |
|------------|-------|---------|
| `securedoc_sess_${token}` | useViewerSession | Session slot persistence across refresh |
| `securedoc_vstate_${session_id}` | useViewerLayout | Page/zoom persistence across refresh |

No namespace collision. Different keys, different hooks, never cross-written.

### localStorage (useViewerLayout / constants/viewer.js)

| Key | Owner | Purpose |
|-----|-------|---------|
| `sdoc-layout-mode` | useViewerLayout via `_saveLayoutPref` | Layout mode preference |
| `sdoc-layout-zoom` | useViewerLayout via `_saveLayoutPref` | Zoom preference |

No other hook reads or writes localStorage.

---

## 10. Smoke Test Matrix

### Authentication & Session

| # | Scenario | Hook(s) involved | Expected result |
|---|----------|-----------------|-----------------|
| A1 | Public link, no gate | useViewerSession | Auto-validates, viewer opens |
| A2 | Public link with password gate | useViewerSession | AccessGate password form |
| A3 | Public link with email gate | useViewerSession | AccessGate email form |
| A4 | Public link with both gates | useViewerSession | AccessGate shows both fields |
| A5 | Wrong password submission | useViewerSession | Gate stays, 'Wrong password. Try again.' |
| A6 | 403 (domain/IP denied) | useViewerSession | Gate stays, access-denied message |
| A7 | 429 (concurrent session limit) | useViewerSession | Gate stays, access-denied message |
| A8 | 404 token (not found) | useViewerSession | Terminal gate, no retry |
| A9 | 410 revoked | useViewerSession | Terminal gate 'revoked' state |
| A10 | 410 expired | useViewerSession | Terminal gate 'expired' state |
| A11 | Admin mode, doc with existing link | useViewerSession | Reuses first active link |
| A12 | Admin mode, doc with no links | useViewerSession | Creates new link, auto-validates |
| A13 | Network error during bootstrap | useViewerSession | Toast 'Failed to open viewer' |
| A14 | Page refresh mid-session | useViewerSession + useViewerLayout | Restores page/zoom from sessionStorage |
| A15 | Page refresh after revoke | useViewerSession | Terminal gate (stored session cleared) |

### Session Recovery (401)

| # | Scenario | Hook(s) involved | Expected result |
|---|----------|-----------------|-----------------|
| B1 | Session expires, navigate to next page | usePageLoader + useViewerSession | 401 triggers reinit, gate or re-auth |
| B2 | Open gate after 401 | useViewerSession | doValidate auto-runs, viewer reloads page 1 |
| B3 | Restricted gate after 401 | useViewerSession | AccessGate appears, user must re-enter credentials |
| B4 | Re-auth through gate | useViewerSession | Viewer reloads from page 1 |
| B5 | getGateRequirements fails on 401 path | useViewerSession | Toast 'Session expired. Please reload.' |
| B6 | Two-page mode, page+1 fetch 401 | usePageLoader | page2Error set (no reinit — pre-existing) |

### Navigation & Layout

| # | Scenario | Hook(s) involved | Expected result |
|---|----------|-----------------|-----------------|
| C1 | Arrow key navigation | useViewerLayout | Page increments/decrements correctly |
| C2 | Toolbar prev/next buttons | useViewerLayout | Same as arrow keys |
| C3 | Direct page jump via input | useViewerLayout | Jumps to entered page number |
| C4 | Zoom in/out via toolbar | useViewerLayout | customZoom updates, persisted to localStorage |
| C5 | Zoom dropdown preset | useViewerLayout | Exact zoom applied |
| C6 | Fit-width / fit-height modes | useViewerLayout | layoutMode changes, persisted |
| C7 | Rotation (90° increments) | useViewerLayout | Image rotates without page reload |
| C8 | Two-page mode toggle | useViewerLayout + usePageLoader | Page shows N and N+1 side by side |
| C9 | Two-page: odd total page count | useViewerLayout + usePageLoader | Last page shows single |
| C10 | Fullscreen enter/exit | useViewerLayout | fullscreenchange syncs isFullscreen state |
| C11 | Pinch-zoom gesture (trackpad) | useViewerLayout | Blocked (browser zoom prevented) |

### Page Image Loading (PDF)

| # | Scenario | Hook(s) involved | Expected result |
|---|----------|-----------------|-----------------|
| D1 | First page load | usePageLoader | Image fetched, crossfade plays |
| D2 | Navigate to previously visited page | usePageLoader | Cache hit — instant display, no network |
| D3 | Prefetch: navigate to page 2 | usePageLoader | Already prefetched — instant |
| D4 | Navigate past cache (>30 pages) | usePageLoader | LRU eviction, oldest page re-fetched |
| D5 | doc_status: 'processing' | usePageLoader | Inline status message, no fetch |
| D6 | doc_status: 'error' | usePageLoader | Inline error message |
| D7 | Network error on page fetch | usePageLoader | Falls back to direct img src |
| D8 | Concurrent fast page navigation | usePageLoader | Inflight dedup prevents duplicate fetches |
| D9 | Page aspect ratio set on img load | usePageLoader | Container resizes correctly |

### Text Documents

| # | Scenario | Hook(s) involved | Expected result |
|---|----------|-----------------|-----------------|
| E1 | Open .txt document | useTextLoader | Text content rendered, no image loading |
| E2 | Open .md document | useTextLoader | Same as txt |
| E3 | Open .log document | useTextLoader | Same as txt |
| E4 | Text doc, doc_status processing | useTextLoader | Inline status message |
| E5 | Text doc: usePageLoader skipped | useTextLoader + usePageLoader | isTextDoc=true → usePageLoader returns early |
| E6 | Text doc: annotations skipped | useAnnotations | isTextDoc guard prevents fetch |
| E7 | Text doc: links panel skipped | useLinksSidecar | isTextDoc guard prevents load |

### Search

| # | Scenario | Hook(s) involved | Expected result |
|---|----------|-----------------|-----------------|
| F1 | Ctrl+F opens search panel | useViewerLayout + ViewerScreen | setShowSearch toggled |
| F2 | Type search query | useSearchHighlights | Word positions fetched (once), highlights computed |
| F3 | Search on different page | useSearchHighlights | Re-computes from already-fetched positions |
| F4 | Navigate to next/prev highlight | useSearchHighlights | activeHighlightIdx advances |
| F5 | Clear search | useSearchHighlights | searchHighlights cleared |
| F6 | Auto-extract resets word positions | useLinksSidecar + useSearchHighlights | wordPositionsRef reset, re-fetched on next search |

### Hyperlinks

| # | Scenario | Hook(s) involved | Expected result |
|---|----------|-----------------|-----------------|
| G1 | Page with extracted links | useLinksSidecar | Links overlay renders on page |
| G2 | Links panel open | useLinksSidecar + ViewerScreen | Panel shows link list for current page |
| G3 | Click a link | useLinksSidecar | visitedLinks updated, link marked visited |
| G4 | Doc with unextracted sidecar | useLinksSidecar | Auto-extract fires, 15s timer reloads |
| G5 | Doc already extracted | useLinksSidecar | autoExtractAttempted=true, no re-extract |

### Annotations & Bookmarks

| # | Scenario | Hook(s) involved | Expected result |
|---|----------|-----------------|-----------------|
| H1 | Open page with annotations | useAnnotations | Annotations loaded and displayed |
| H2 | Navigate away and back | useAnnotations | annotCacheRef hit — no re-fetch |
| H3 | Create annotation | useAnnotations + JSX | API call, annotation added to cache |
| H4 | Undo annotation | useAnnotations + JSX | Last annotation deleted via API |
| H5 | Add bookmark | useAnnotations + JSX | toggleBookmark called, bookmarks Set updated |
| H6 | Remove bookmark | useAnnotations + JSX | Bookmark removed from Set |
| H7 | View comment thread | useAnnotations + JSX | threadView set, thread loaded |
| H8 | Post reply to thread | useAnnotations + JSX | API call, thread refreshed |
| H9 | No annotate permission | useAnnotations | Load effects return early — no API calls |

### DRM Protections

| # | Scenario | Hook | Expected result |
|---|----------|------|-----------------|
| I1 | Right-click, `can_right_click=false` | useViewerSession | Blocked + toast + logEvent |
| I2 | Right-click, `can_right_click=true` | useViewerSession | Context menu appears normally |
| I3 | Ctrl+P, `can_print=false` | useViewerSession | Blocked + toast + logEvent |
| I4 | Ctrl+P, `can_print=true` | useViewerSession | Browser print dialog opens |
| I5 | Ctrl+C, `can_copy=false` | useViewerSession | Blocked + toast + logEvent |
| I6 | Ctrl+X, `can_copy=false` | useViewerSession | Blocked |
| I7 | Ctrl+A, `can_copy=false` | useViewerSession | Blocked |
| I8 | Ctrl+U, `can_copy=false` | useViewerSession | Blocked (view-source) |
| I9 | Ctrl+S, `can_download=false` | useViewerSession | Blocked + toast + logEvent |
| I10 | Cmd+P/C/S on macOS | useViewerSession | Same as Ctrl — metaKey check |
| I11 | Print dialog (system), `can_print=false` | useViewerSession | `.viewer-page` hidden before print |
| I12 | After print | useViewerSession | `.viewer-page` always restored |
| I13 | Window blur (Alt+Tab) | useViewerSession | Blur overlay (14px) visible |
| I14 | Window focus | useViewerSession | Blur removed |
| I15 | Tab switch (mobile) | useViewerSession | Blur overlay via visibilitychange |
| I16 | Return to tab | useViewerSession | Blur removed |
| I17 | `can_copy=false` text selection | ViewerScreen JSX | userSelect: none on text container |
| I18 | Download button, `can_download=false` | ViewerScreen JSX | Button hidden/disabled |
| I19 | Print button, `can_print=false` | ViewerScreen JSX | Button hidden/disabled |

### Tool States

| # | Scenario | Hook(s) | Expected result |
|---|----------|---------|-----------------|
| J1 | Laser pointer on | ViewerScreen | Cursor changes, laser renders |
| J2 | Magnifier on | ViewerScreen + usePageLoader | pageContainerRef used by RectMagnifier |
| J3 | Insights panel | ViewerScreen | Heatmap fetched on first open |
| J4 | TOC panel | ViewerScreen | TOC component renders |
| J5 | Pages panel | ViewerScreen | ThumbnailStrip renders |
| J6 | Info panel | ViewerScreen | Session info displayed |

---

## 11. Architecture Scorecard

### Before Refactor (6 047-line monolith)

| Metric | Value |
|--------|-------|
| Files | 1 (`app.jsx`) |
| Hook files | 0 |
| Constants files | 0 |
| Inline `useState` in ViewerScreen | 23 |
| Inline `useRef` in ViewerScreen | 8 |
| Inline `useEffect` in ViewerScreen | ~11 |
| Inline callbacks/functions in ViewerScreen | 8 (loadPage, prefetchPage, etc.) |
| Largest conceptual unit | ViewerScreen: ~1 800 lines |
| Circular deps | 1 (handled inline — invisible) |
| Separation of concerns | None — session, loading, DRM, layout all mixed |
| Symbol discoverability | Low — `Ctrl+F` in one file |
| Onboarding difficulty (estimate) | Very high — read 1 800+ lines before touching anything |

### After Sprint 2 (current state)

| Metric | Value |
|--------|-------|
| Files | 10 (`app.jsx` + 7 hooks + 2 constants/utils) |
| Hook files | 7 |
| Constants files | 2 |
| Inline `useState` in ViewerScreen | 10 (UI-only toggles + insightsData) |
| Inline `useRef` in ViewerScreen | 1 (`_setPageRef` — circular-dep seam) |
| Inline `useEffect` in ViewerScreen | 1 (shimmer CSS inject) |
| Inline callbacks in ViewerScreen | 0 |
| Largest conceptual unit | `usePageLoader`: 242 lines |
| Circular deps | 1 (explicit + documented + resolved via `_setPageRef`) |
| Separation of concerns | Clear — each hook owns one domain |
| Symbol discoverability | High — `grep useViewerSession` takes 1 second |
| Onboarding difficulty (estimate) | Low — read one hook file per domain |

### Concern Coverage Map

| Domain | Before | After |
|--------|--------|-------|
| Session auth + gate | ViewerScreen inline | useViewerSession |
| DRM enforcement | ViewerScreen inline | useViewerSession |
| Page navigation + zoom | ViewerScreen inline | useViewerLayout |
| Session state persistence | ViewerScreen inline | useViewerLayout |
| Page image loading + cache | ViewerScreen inline | usePageLoader |
| Text content loading | ViewerScreen inline | useTextLoader |
| Search highlights | ViewerScreen inline | useSearchHighlights |
| Hyperlink sidecar | ViewerScreen inline | useLinksSidecar |
| Annotations + bookmarks | ViewerScreen inline | useAnnotations |
| Layout constants | ViewerScreen inline | constants/viewer.js |
| Error message helper | ViewerScreen inline | utils/viewer.js |
| UI panel toggles | ViewerScreen inline | ViewerScreen (correct — UI state belongs here) |

---

## 12. Remaining Technical Debt

### TD-1: In-flight fetch not aborted on unmount (usePageLoader)

**Risk**: Low. Fetch completes after unmount, writes to dead component (no-op in React 18), leaks one blob URL per in-flight request.  
**Fix**: Add `AbortController`, pass signal to `fetch()`, abort on cleanup.  
**Sprint**: 3 (low priority)

### TD-2: Auto-create-link effect has no race protection (useViewerSession)

**Risk**: Low. If `docId` changes while the async IIFE is mid-flight (only possible in authenticated admin mode), a stale fetch could set state for the wrong document.  
**Fix**: Add `AbortController` or an `isCancelled` flag in cleanup.  
**Sprint**: 3 (low priority)

### TD-3: loadPage2 does not trigger 401 re-auth (usePageLoader)

**Risk**: Low-medium. If the two-page second image returns 401, only `page2Error` is set — the re-auth flow is not triggered. The user would see an error inline for the second page, but the main page and session remain intact. The next primary-page navigation will trigger re-auth normally.  
**Fix**: Add `_onAuth401Ref.current?.()` call in `loadPage2`'s 401 branch.  
**Sprint**: 3 (medium priority — could confuse users in two-page mode)

### TD-4: Keyboard effect has two false deps (_zoomBy, _setLayout)

**Risk**: Negligible. Causes unnecessary listener re-register on zoom change. Functionally harmless.  
**Fix**: Remove `_zoomBy` and `_setLayout` from the keyboard effect dep array.  
**Sprint**: 3 cleanup pass

### TD-5: Security listeners dep: [session] vs [session?.session_id]

**Risk**: Very low. Listeners briefly unregister and re-register on any `session` object re-allocation. Gap is ~1 tick.  
**Fix** (optional): Change to `deps: [session?.session_id]` and use a session ref in handlers.  
**Sprint**: Post-Sprint 3 (accepted pre-existing risk per Phase 2.7 implementation decision)

### TD-6: app.jsx still ~5 525 lines — no component file extraction

**Risk**: High for onboarding. All JSX components (ViewerToolbar, AnnotationLayer, DocManagement, etc.) still live in the single file.  
**Fix**: Sprint 3 component extraction (see Sprint 3 Roadmap below).  
**Sprint**: 3 (highest priority)

### TD-7: useToast() cannot be imported by hook files

**Risk**: Medium. `useViewerSession` must receive `toast` as a parameter because `ToastCtx` is not exported from `app.jsx`. This is an API smell — the hook's signature leaks implementation detail.  
**Fix**: Extract `ToastCtx`, `useToast`, `ToastProvider`, `Toast` to `frontend/src/contexts/toast.jsx`. Hooks can then call `useToast()` directly.  
**Sprint**: 3.5 or dedicated extraction phase

---

## 13. Highest-Risk Remaining Files

| File | Risk | Why |
|------|------|-----|
| `frontend/src/app.jsx` (5 525 lines) | HIGH | Still monolithic for components; ViewerToolbar + DocManagement + AnnotationLayer all inline |
| `useViewerSession.js` (169 lines) | MEDIUM | Owns DRM + auth — any change here is a security surface; 401 re-auth chain has 3 hops |
| `usePageLoader.js` (242 lines) | MEDIUM | LRU eviction, inflight dedup, and crossfade are subtle; in-flight abort gap |
| `useLinksSidecar.js` (68 lines) | LOW-MEDIUM | Cross-hook ref mutation (wordPositionsRef) is non-obvious coupling |
| `useViewerLayout.js` (139 lines) | LOW | False deps in keyboard effect; _setLayout dep on customZoom is intentional but counterintuitive |

---

## 14. Sprint 3 Roadmap

Sprint 3 shifts from hook extraction to **component file extraction**. All
state logic has been moved to hooks. What remains in `app.jsx` is JSX component
definitions that should be independent files.

### Phase 3.1 — Extract ViewerToolbar

**File**: `frontend/src/components/ViewerToolbar.jsx`  
**Risk**: Very low — zero shared state, pure props + callbacks  
**Estimated reduction from app.jsx**: ~400 lines  
**Effort**: 1–2 hours

### Phase 3.2 — Extract Toast context

**File**: `frontend/src/contexts/toast.jsx`  
**Exports**: `ToastCtx`, `useToast`, `ToastProvider`, `Toast`  
**Enables**: Hook files calling `useToast()` directly (eliminates TD-7)  
**Estimated reduction from app.jsx**: ~50 lines  
**Effort**: 30 minutes

### Phase 3.3 — Extract SearchPanel / LinksPanel / InsightsPanel

**Files**: `frontend/src/components/{Search,Links,Insights}Panel.jsx`  
**Risk**: Low — well-scoped, callback-based interfaces  
**Estimated reduction from app.jsx**: ~530 lines  
**Effort**: 2–3 hours

### Phase 3.4 — Extract AnnotationLayer + drawing + comments

**File**: `frontend/src/components/AnnotationLayer.jsx`  
**Risk**: Medium — large prop surface; closes over session, page, many annotation setters  
**Estimated reduction from app.jsx**: ~800 lines  
**Effort**: 4–6 hours

### Phase 3.5 — Extract DocManagement screen

**File**: `frontend/src/components/DocManagement.jsx` (+ sub-panel files)  
**Risk**: Low — entirely separate from viewer state  
**Estimated reduction from app.jsx**: ~1 800 lines  
**Effort**: 3–4 hours

### Phase 3.6 — Extract design tokens + shared atoms

**Files**: `frontend/src/constants/tokens.js`, `frontend/src/components/atoms.jsx`  
**Risk**: Very low — pure constants and presentational components  
**Estimated reduction from app.jsx**: ~280 lines  
**Effort**: 1 hour

### Projected outcome after Sprint 3

| Metric | After Sprint 2 | After Sprint 3 |
|--------|---------------|---------------|
| `app.jsx` lines | 5 525 | ~1 200–1 500 |
| Component files | 0 | 8–10 |
| Hook files | 7 | 7 (unchanged) |
| Total frontend source files | 10 | ~20 |
| Largest single file | `app.jsx` (5 525) | `app.jsx` (~1 400) |

---

## 15. Recommended Extraction Order

```
Priority 1 (do first, lowest risk, unblocks others):
  3.2 → Toast context extraction (enables hooks to call useToast())
  3.1 → ViewerToolbar (zero risk, high immediate payoff)

Priority 2 (medium complexity, standalone):
  3.3 → Search/Links/Insights panels (independent of each other, parallelize)
  3.5 → DocManagement (fully separate from viewer)

Priority 3 (higher complexity, more coupling):
  3.4 → AnnotationLayer (largest prop surface, needs careful audit)

Priority 4 (cleanup):
  3.6 → Tokens + atoms (polish, no urgency)
```

---

## 16. Audit Summary

### Regressions introduced by Sprint 2 refactor

**None detected.**

All behaviors verified to match pre-refactor logic:
- Session bootstrap, gate flows, doValidate error routing: identical
- reinitRef.current 401 re-auth chain: identical (render-body assignment preserved)
- DRM listeners: identical event types, targets, dep arrays, cleanup
- Page crossfade, LRU cache, inflight dedup: identical (moved without modification)
- Annotation load, bookmark load: identical
- Search word-position fetch and highlight compute: identical
- Link sidecar load and auto-extract: identical
- Session state persist/restore: identical
- setPage(1) on validate: identical behavior via _setPageRef chain

### Known pre-existing issues (not regressions)

| Issue | Severity | Pre-existing? |
|-------|----------|--------------|
| In-flight fetch not aborted on unmount | Low | ✅ pre-existing |
| Auto-create-link effect: no race protection | Low | ✅ pre-existing |
| loadPage2: no 401 reinit trigger | Low-medium | ✅ pre-existing |
| keyboard effect: _zoomBy/_setLayout false deps | Negligible | ✅ pre-existing |
| DRM listeners: brief gap on session re-alloc | Very low | ✅ pre-existing |

### Build status

✅ `npm run build` — 196.4 kb, 20 ms, zero errors, zero warnings
