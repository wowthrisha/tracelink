# Phase 2.6 — usePageLoader Extraction Report

**Sprint**: Architecture Refactor Sprint 2, Goal #3  
**Date**: 2026-06-17  
**Status**: Complete ✅

---

## Objective

Extract all page image loading, blob URL caching, inflight deduplication, crossfade
transitions, two-page spread loading, and background prefetching from ViewerScreen
into `usePageLoader`. `reinitRef` stays in ViewerScreen; the 401 retry path flows
through an `onAuth401` callback seam.

---

## File Created

**`frontend/src/hooks/usePageLoader.js`** — 200 lines

```js
export function usePageLoader({ session, page, twoPageMode, isTextDoc, onAuth401 })
  → {
      imgSrc, imgLoading, pageError,
      prevImgSrc, imgReady, setImgReady,
      imgSrc2, imgLoading2, page2Error,
      pageAspectRatio, setPageAspectRatio,
      pageImgRef, pageContainerRef,
    }
```

---

## State Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `imgSrc` | `''` | Current page blob URL (or fallback fetch URL) |
| `imgLoading` | `false` | True while a page fetch is in flight |
| `pageError` | `null` | Error string shown inline when fetch fails |
| `prevImgSrc` | `''` | Previous page blob URL — held visible during crossfade |
| `imgReady` | `false` | Flips to `true` in img `onLoad`; drives crossfade opacity |
| `imgSrc2` | `''` | Second-page blob URL for two-page spread |
| `imgLoading2` | `false` | Loading state for second-page fetch |
| `page2Error` | `null` | Error string for second-page fetch failure |
| `pageAspectRatio` | `null` | `"nw/nh"` string set from img `onLoad` natural dimensions |

`setImgReady` and `setPageAspectRatio` are returned because JSX `img.onLoad` handlers
in ViewerScreen set them directly.

---

## Refs Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `pageImgRef` | `null` | DOM ref on the current-page `<img>` |
| `pageContainerRef` | `null` | DOM ref on the viewer page container (needed by `RectMagnifier`) |
| `inflightRef` | `new Map()` | `token:page → Promise` — deduplicates concurrent fetches of the same page |
| `imgSrcRef` | `''` | Stable snapshot of `imgSrc` for empty-dep `loadPage` callback |
| `pageCache` | `new Map()` | LRU blob URL cache: `token:page → blobUrl`, capped at 30 entries |

`pageImgRef` and `pageContainerRef` are returned (used in ViewerScreen JSX).
The other three refs are internal to the hook.

---

## Callbacks Extracted (all internal — not returned)

| Symbol | Deps | Purpose |
|--------|------|---------|
| `_cacheSet(key, blobUrl)` | `[]` | LRU insert with eviction + `URL.revokeObjectURL` on evicted entry |
| `_clearPageCache()` | `[]` | Revokes all blob URLs in the cache; called on unmount |
| `loadPage(token, pageNum, sessionId)` | `[]` | Cache-hit fast path → inflight dedup → fetch with crossfade |
| `prefetchPage(token, pageNum, sessionId, total)` | `[]` | Silent background prefetch; no state updates |
| `loadPage2(token, pageNum, sessionId, total)` | `[]` | Two-page second image fetch with separate loading/error state |

All five callbacks have empty deps (`[]`) because they close only over stable refs and
their own `set*` state setters, not over any React state values. This is correct and
intentional — stale closures are prevented by `imgSrcRef` for the crossfade path.

---

## Effects Extracted

### imgSrcRef sync
```
deps: [imgSrc]
```
Keeps `imgSrcRef.current` up-to-date so `loadPage`'s empty-dep closure can read
the current displayed URL when setting up the crossfade background.

### Unmount blob URL cleanup
```
deps: []  (cleanup-only effect)
```
Returns `_clearPageCache` as the cleanup function. Revokes all cached blob URLs on
component unmount to prevent memory leaks.

### Page load
```
deps: [session?.link_token, session?.session_id, page, session?.doc_status, session?.doc_type, loadPage]
```
Guards on session readiness and `doc_status`. On `ready`, calls `loadPage`. Also fires
`logEvent('completed')` client-side when the viewer reaches the last page.

### Prefetch next + prev pages
```
deps: [session?.link_token, session?.session_id, page, imgLoading, PAGE_COUNT, prefetchPage, isTextDoc]
```
Fires after current page has loaded (`!imgLoading`). Prefetches the next and previous
pages so navigation feels instant.

### Two-page spread load
```
deps: [session?.link_token, session?.session_id, page, isTwoPage, isTextDoc, PAGE_COUNT, session?.doc_status, loadPage2]
```
Loads `page + 1` into `imgSrc2` when in two-page mode. Clears `imgSrc2` when the
mode is disabled.

### Eager page-2 prefetch on session start
```
deps: [session?.link_token, session?.session_id, session?.doc_type]
```
Prefetches page 2 immediately when a session is established (before the user
navigates). `prefetchPage` intentionally omitted from deps — it is stable (`[]`)
and omitting it avoids a spurious double-fire on session object re-allocation.

---

## Dependency Graph

```
usePageLoader
  params:
    ← session         (ViewerScreen inline state)
    ← page            (useViewerLayout return)
    ← twoPageMode     (useViewerLayout return)
    ← isTextDoc       (derived in ViewerScreen from session)
    ← onAuth401       (callback: () => reinitRef.current?.())

  internal derived:
    PAGE_COUNT = session?.page_count || 1
    isTwoPage  = twoPageMode

  returns:
    → imgSrc, imgLoading, pageError         (rendered in JSX)
    → prevImgSrc, imgReady, setImgReady     (crossfade JSX)
    → imgSrc2, imgLoading2, page2Error      (two-page JSX)
    → pageAspectRatio, setPageAspectRatio   (layout + img.onLoad JSX)
    → pageImgRef, pageContainerRef          (DOM refs in JSX)
```

---

## Ref Ownership Graph

```
┌───────────────────────────────────────────────────────────────┐
│ ViewerScreen                                                  │
│   reinitRef  ──────────────────────────────────┐             │
│   (useRef(null), written every render via       │             │
│    reinitRef.current = async () => {...})        │             │
└───────────────────────────────────────────────────────────────┘
         │  passed as: onAuth401: () => reinitRef.current?.()
         ▼
┌───────────────────────────────────────────────────────────────┐
│ usePageLoader                                                 │
│   _onAuth401Ref  ←── stabilises onAuth401 callback           │
│   pageCache      (LRU blob URL store)                        │
│   inflightRef    (in-flight dedup map)                        │
│   imgSrcRef      (crossfade snapshot)                         │
│   pageImgRef     ───────────────────────────────────────────► JSX ref │
│   pageContainerRef ─────────────────────────────────────────► JSX ref │
└───────────────────────────────────────────────────────────────┘
```

`reinitRef` ownership stays in ViewerScreen. When `loadPage` receives a 401, it calls
`_onAuth401Ref.current?.()`, which calls `reinitRef.current?.()`, which calls the
reinit logic in ViewerScreen. The chain is: hook → ViewerScreen → hook (async).

---

## 401 Retry Flow Diagram

```
User navigates to page N
        │
        ▼
loadPage(token, pageNum, sessionId)    [inside usePageLoader, empty-dep useCallback]
        │
        ▼
fetch(pageUrl, sessionHeaders)
        │
        ├─ 200 OK ──────────────────► create blob URL → _cacheSet → setImgSrc
        │
        └─ 401 ──────────────────────► _onAuth401Ref.current?.()
                                                │
                                                ▼
                                   reinitRef.current()          [in ViewerScreen]
                                                │
                                                ▼
                                   getGateRequirements(token)
                                                │
                              ┌─────────────────┴──────────────────┐
                              │ gate requires pw/email             │ gate open
                              ▼                                    ▼
                    setSession(null)                  doValidate(token, null, null)
                    setGateInfo(gate)                         │
                    setPendingToken(token)                    ▼
                    setInit(false)             setSession(newSession)
                    [AccessGate overlay]       setPage(1)
                                               [viewer reloads from page 1]
```

The 401 path is identical to the original. The only change is the call site:
- **Before**: `if (r.status === 401 && reinitRef.current) { reinitRef.current(); }`
- **After**: `if (r.status === 401) { _onAuth401Ref.current?.(); }`

Both are null-safe; behavior is identical.

---

## Lines Removed from ViewerScreen

| Block removed | Count |
|---------------|-------|
| `imgSrc`, `imgLoading`, `pageError` useState | 3 |
| `prevImgSrc`, `imgReady` useState + comment | 3 |
| `pageAspectRatio` useState | 1 |
| `pageImgRef` useRef | 1 |
| `pageContainerRef` useRef + comment | 2 |
| `imgSrc2`, `imgLoading2`, `page2Error` useState + comment | 4 |
| inflightRef + comment block | 5 |
| imgSrcRef + comment | 2 |
| pageCache + comment block (7-line block comment) | 9 |
| `_cacheSet` useCallback | 10 |
| `_clearPageCache` useCallback + comment | 8 |
| `loadPage` useCallback | 73 |
| `prefetchPage` useCallback | 9 |
| `loadPage2` useCallback | 15 |
| Unmount cleanup useEffect | 1 |
| Page load useEffect + comment block | 21 |
| Prefetch next/prev useEffect + comment | 6 |
| Two-page load useEffect + comment | 6 |
| Eager page-2 prefetch useEffect + comment | 5 |
| imgSrcRef sync useEffect + comment | 3 |
| Dead `pageStep` derived const | 1 |
| **Total removed** | **188** |

Lines added (import + hook call block): **14**  
Phase 2.6 net change to `app.jsx`: **−174 lines**

(Actual file delta: 5 832 → 5 636 = **−196 lines**; difference reflects blank-line
cleanup and comment consolidation during edit.)

---

## Build Result

| Metric | Before (Phase 2.5) | After (Phase 2.6) |
|--------|-------------------|------------------|
| `app.jsx` lines | 5 832 | 5 636 |
| Bundle size | 195.1 kb | 195.8 kb |
| Build time | 27 ms | 29 ms |
| Build result | PASS ✅ | PASS ✅ |

Bundle grows 0.7 kb — expected from the new hook file boilerplate.

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
| Phase 2.6 (usePageLoader) | −196 |
| **Running total** | **−387 lines** |

`app.jsx`: 6 047 → 5 636 lines (**−6.4%** of file, **−28.8%** of ViewerScreen span)

---

## Manual Verification Checklist

- [ ] PDF loads on first open
- [ ] DOCX/text document loads (text viewer path, no image fetch)
- [ ] Page navigation with toolbar buttons, arrow keys, swipe
- [ ] Image crossfade plays on navigation (no flash)
- [ ] Cache reuse: navigate to page 3, back to page 1 — no network request on page 1
- [ ] Two-page spread shows page N and N+1 side by side
- [ ] Two-page toggle switches between single and spread view
- [ ] Prefetch: navigate to page 2 after page 1 loads — should be instant (prefetched)
- [ ] Page rotation applies correctly over the loaded image
- [ ] Zoom changes do not trigger a page reload
- [ ] Annotation overlays remain aligned with image (pageContainerRef intact)
- [ ] Search highlight overlays remain aligned with image
- [ ] Links overlay remains aligned with image
- [ ] 401 retry: expire a session manually, navigate to a page — AccessGate appears
- [ ] Expired session recovery: after re-authentication, viewer reloads from page 1
- [ ] `RectMagnifier` opens and correctly magnifies the page image
- [ ] No console errors on load, navigation, or tool interaction

---

## Remaining ViewerScreen Inline State Inventory

After Phase 2.6, ViewerScreen still owns these inline symbols:

### State (15 useState)

| Symbol | Purpose | Phase 2.7 candidate |
|--------|---------|---------------------|
| `session` | Core validated session object | useViewerSession ✓ |
| `initializing` (`setInit`) | Loading gate spinner | useViewerSession ✓ |
| `gateInfo` | Gate requirements for AccessGate overlay | useViewerSession ✓ |
| `gateError` | Password/email validation error | useViewerSession ✓ |
| `pendingToken` | Token before gate is satisfied | useViewerSession ✓ |
| `blurred` | Document blur for DRM enforcement | useViewerSession ✓ |
| `showInfo` | Info panel open/closed | stays (UI toggle) |
| `showSearch` | Search panel open/closed | stays (UI toggle) |
| `showToc` | TOC panel open/closed | stays (UI toggle) |
| `showLaser` | Laser pointer active | stays (UI toggle) |
| `showMagnifier` | Magnifier active | stays (UI toggle) |
| `showInsights` | Insights panel open/closed | stays (UI toggle) |
| `insightsData` | Heatmap data for insights panel | stays (UI data) |
| `insightsLoading` | Insights fetch in flight | stays (UI data) |
| `showLinks` | Links panel open/closed | stays (UI toggle) |
| `showPageList` | Pages panel open/closed | stays (UI toggle) |

### Refs (1 useRef)

| Symbol | Purpose | Phase 2.7 candidate |
|--------|---------|---------------------|
| `reinitRef` | 401 re-entry point; set every render | useViewerSession ✓ |

### Functions (1 async function)

| Symbol | Purpose | Phase 2.7 candidate |
|--------|---------|---------------------|
| `doValidate(token, email, pw)` | Link token validation + session setup | useViewerSession ✓ |

### Effects (2 useEffect)

| Effect | Deps | Phase 2.7 candidate |
|--------|------|---------------------|
| Auto-create link + gate probe | `[docId]` | useViewerSession ✓ |
| Security listeners | `[session]` | useViewerSession ✓ |
| Tab visibility | `[session]` | useViewerSession ✓ |
| Shimmer style inject | `[]` | stays in ViewerScreen |

---

## Phase 2.7 — useViewerSession Analysis

### What it would own

**State**: `session`, `initializing`, `gateInfo`, `gateError`, `pendingToken`, `blurred`

**Ref**: `reinitRef`

**Function**: `doValidate(token, email, password)` — the core async session setup logic

**Effects**:
1. Auto-create link + gate probe (`deps: [docId]`) — gets/creates the link token, probes
   gate requirements, calls `doValidate` if no restrictions
2. Security listeners (`deps: [session]`) — 6 listener pairs:
   `contextmenu` (right-click block), `keydown` (Ctrl+P/C/X/U/S), `beforeprint`/`afterprint`
   (page hide/show), `blur`/`focus` (DRM blurred overlay)
3. Tab visibility (`deps: [session]`) — `visibilitychange` listener for mobile tab-switch

### Dependency Map

```
useViewerSession
  params:
    ← doc          (ViewerScreen prop — for docId and publicToken)
    ← publicToken  (ViewerScreen prop)
    ← toast        (from useToast — context hook called in ViewerScreen)
    ← onValidated  (callback: () => setPage(1), from useViewerLayout return)

  internal:
    doValidate calls setPage(1) via onValidated callback
    reinitRef.current = async () => { getGateRequirements → doValidate }
    blurred set by blur/focus and visibilitychange listeners

  returns:
    → session, setSession (consumed by all other hooks as params)
    → initializing        (gate/loading spinner)
    → gateInfo, setGateInfo
    → gateError, setGateError
    → pendingToken, setPendingToken
    → blurred             (DRM blur overlay in JSX)
    → reinitRef           (passed as onAuth401 source to usePageLoader)
    → doValidate          (called by AccessGate onSubmit in JSX)
```

### Listener Inventory

| Event | Target | Trigger condition | Action |
|-------|--------|-------------------|--------|
| `contextmenu` | `document` | `!perms.can_right_click` | `preventDefault` + log event + toast |
| `keydown` | `document` | Ctrl+P + `!can_print` | `preventDefault` + `stopPropagation` + log + toast |
| `keydown` | `document` | Ctrl+C/X/A/U + `!can_copy` | `preventDefault` + `stopPropagation` + log + toast |
| `keydown` | `document` | Ctrl+S + `!can_download` | `preventDefault` + `stopPropagation` + log + toast |
| `beforeprint` | `window` | `!can_print` | Hide `.viewer-page` elements + log event |
| `afterprint` | `window` | always | Restore `.viewer-page` element visibility |
| `blur` | `window` | always | `setBlurred(true)` |
| `focus` | `window` | always | `setBlurred(false)` |
| `visibilitychange` | `document` | always | `setBlurred(document.hidden)` |

All 9 listener registrations are in 2 effects. Both effects are gated on `session`.

### Security-Event Inventory

Events logged via `window.SecureDocAPI.logEvent(link_token, session_id, event_type)`:

| Event type | Trigger |
|------------|---------|
| `right_click_attempt` | Blocked `contextmenu` |
| `print_attempt` | Blocked Ctrl+P or `beforeprint` |
| `copy_attempt` | Blocked Ctrl+C/X/A/U |
| `download_attempt` | Blocked Ctrl+S |

These logs must be preserved exactly — they are the DRM audit trail.

### Critical Coupling Points

**1. `doValidate` calls `setPage(1)`**  
`setPage` comes from `useViewerLayout`. If `useViewerSession` is extracted, `setPage`
must be passed in as a callback param (`onValidated: () => setPage(1)`). ViewerScreen
calls `useViewerLayout` first, then calls `useViewerSession(... { onValidated: () => setPage(1) })`.

**2. `reinitRef` feeds `usePageLoader`'s `onAuth401`**  
After `useViewerSession` is extracted, `reinitRef` is returned from the hook. ViewerScreen
passes it through:
```js
const { reinitRef, ... } = useViewerSession(...);
const { imgSrc, ... } = usePageLoader({ ..., onAuth401: () => reinitRef.current?.() });
```

**3. `toast` from `useToast`**  
`doValidate` and `reinitRef.current` both call `toast(...)`. Since `toast` comes from
`useToast()` which is called at the top of ViewerScreen, it must be passed as a param
to `useViewerSession`. Alternatively, `useViewerSession` can call `useToast()` itself
(it would just need to be called unconditionally, which it is).

**Recommendation**: Have `useViewerSession` call `useToast()` internally — this avoids
a `toast` param and is the cleaner API. `useToast` is a context hook that reads from
the existing `ToastContext`, so it's safe to call in any hook.

### Expected Line Reduction

| Block | Estimated lines |
|-------|----------------|
| `session` etc. state declarations | 8 |
| `reinitRef` useRef | 1 |
| `doValidate` function | 33 |
| `reinitRef.current = async () => {...}` | 16 |
| Auto-create link effect + comment | 34 |
| Security listeners effect + comment | 23 |
| Tab visibility effect + comment | 8 |
| **Total estimated removal** | **~123 lines** |

Lines added (import + hook call block): **~20 lines**  
**Estimated Phase 2.7 net**: **−103 lines**  
`app.jsx` after Phase 2.7: **~5 533 lines** (estimated)

### Recommended Implementation Sequence for Phase 2.7

```
Step 1: Create useViewerSession.js
  - Move 6 state vars + reinitRef
  - Move doValidate (with onValidated callback seam for setPage)
  - Move reinitRef.current = assignment (as useEffect or inline each render)
  - Move auto-create-link effect
  - Move security-listeners effect
  - Move tab-visibility effect
  - Call useToast() internally

Step 2: Update ViewerScreen
  - Call useViewerLayout first (produces setPage for onValidated callback)
  - Call useViewerSession second (produces session, reinitRef, blurred)
  - Call usePageLoader third (uses reinitRef for onAuth401)
  - useTextLoader, useSearchHighlights, useLinksSidecar, useAnnotations unchanged

Step 3: Verify security paths manually
  - Right-click blocked
  - Ctrl+P/C/S blocked
  - Print events hide/restore pages
  - Blur overlay appears on window blur
  - 401 → reinit → re-authentication flow
```

**Risk assessment**: HIGH — security listeners must not break; `doValidate`'s 5 error
paths must be reproduced exactly; the `onValidated`/`setPage` callback seam adds a new
dependency direction (session → layout). Verify each security event type after
implementation.
