# Phase 2.7 — useViewerSession Extraction Readiness Review

**Sprint**: Architecture Refactor Sprint 2, Goal #3  
**Date**: 2026-06-17  
**Status**: Analysis only — NO code changes  
**Reviewer scope**: Complete audit of all symbols, effects, and risks before implementation

---

## Scope of this Review

This document audits every symbol, closure, listener, and failure mode that would
be affected by extracting `useViewerSession` from `ViewerScreen`. Nothing in the
source is changed here. The goal is to surface every risk before a single line of
implementation code is written.

---

## 1. State Dependency Graph

### Symbols being extracted

```
session        [useState(null)]
initializing   [useState(true)]    alias: setInit
gateInfo       [useState(null)]
gateError      [useState(null)]
pendingToken   [useState(null)]
blurred        [useState(false)]
reinitRef      [useRef(null)]
```

### What consumes each symbol in ViewerScreen (after extraction)

```
session
  → useViewerLayout(session, ...)             param
  → useTextLoader(session, ...)               param
  → usePageLoader({ session, ... })           param
  → useSearchHighlights(session, ...)         param
  → useLinksSidecar(session, ...)             param
  → useAnnotations(session, ...)              param
  → JSX: session?.permissions.*              conditional render guards
  → JSX: session?.link_token, session_id     API call args in JSX handlers
  → JSX: session?.document_id               insights panel
  → JSX: session?.created_at               info panel
  → JSX: docName fallback (session?.document_filename)
  ← PRODUCED by useViewerSession (must be returned)

initializing
  → JSX: conditional return  (!docId && !publicToken && !initializing)
  → JSX: loading spinner     {initializing && <Spinner/>}
  → JSX: content guards      {!initializing && session && ...}
  ← PRODUCED by useViewerSession (must be returned)

gateInfo
  → JSX: conditional return  (gateInfo && !session → AccessGate)
  → JSX: <AccessGate gateInfo={gateInfo} ...>
  ← PRODUCED by useViewerSession (must be returned)

gateError
  → JSX: <AccessGate error={gateError} ...>
  ← PRODUCED by useViewerSession (must be returned)

pendingToken
  → JSX: AccessGate onSubmit  doValidate(pendingToken, email, pw)
  → internal: reinitRef.current  session?.link_token || pendingToken
  ← PRODUCED by useViewerSession (must be returned)

blurred
  → JSX: filter: blurred ? 'blur(14px)' : 'none'   [3 locations in page container]
  → JSX: {blurred && <BlurOverlay/>}                [2 locations]
  ← PRODUCED by useViewerSession (must be returned)

reinitRef
  → usePageLoader({ ..., onAuth401: () => reinitRef.current?.() })
  ← PRODUCED by useViewerSession (must be returned)
```

### Symbols that STAY in ViewerScreen

```
toast          from useToast() — context hook; useViewerSession calls it internally
showInfo       UI toggle
showSearch     UI toggle (also feeds useViewerLayout's onToggleSearch callback)
showToc        UI toggle
showLaser      UI toggle
showMagnifier  UI toggle
showInsights   UI toggle
insightsData   UI data (loaded on demand in JSX handler)
insightsLoading UI data
showLinks      UI toggle
showPageList   UI toggle
```

### Cross-hook data flow (after extraction)

```
ViewerScreen props:
  doc, publicToken, onSelectDoc

               ┌─────────────────────────────────────┐
               │ useViewerSession                    │
               │ params: doc, publicToken, {onValidated}│
               │ produces: session, blurred,          │
               │           initializing, gateInfo,    │
               │           gateError, pendingToken,   │
               │           reinitRef                  │
               └──────────────┬──────────────────────┘
                              │ session
               ┌──────────────▼──────────────────────┐
               │ useViewerLayout                     │
               │ params: session, {onToggleSearch}   │
               │ produces: page, setPage, twoPageMode│
               │           layoutMode, ...           │
               └──────────────┬──────────────────────┘
                              │ session, page, twoPageMode
               ┌──────────────▼──────────────────────┐
               │ usePageLoader                       │
               │ params: session, page, twoPageMode, │
               │         isTextDoc, onAuth401        │
               │ onAuth401: () => reinitRef.current?.()│
               └─────────────────────────────────────┘
```

---

## 2. Ref Dependency Graph

### reinitRef — the critical shared ref

```
┌─ defined in ViewerScreen render body ───────────────────────────────────────┐
│  After extraction: defined inside useViewerSession, returned to ViewerScreen │
└─────────────────────────────────────────────────────────────────────────────┘

reinitRef.current WRITER:
  reinitRef.current = async () => {            ← assigned EVERY render (not in effect)
    const token = session?.link_token || pendingToken;
    ...
    await doValidate(token, null, null);       ← closes over internal doValidate
    ...
    toast('Session expired...', 'error');      ← closes over internal toast
  };

  After extraction this assignment lives inside useViewerSession render body.
  Critical: must remain a render-body assignment, NOT a useEffect. If moved to
  useEffect it becomes one-render stale — see Failure Mode #1.

reinitRef.current CALLER:
  usePageLoader — onAuth401: () => reinitRef.current?.()
  Called inside usePageLoader's loadPage callback when fetch returns 401.

Closure chain on 401:
  usePageLoader._onAuth401Ref.current?.()
    → ViewerScreen: reinitRef.current?.()
      → useViewerSession: doValidate(token, null, null)
        → setSession(newSession)    [inside useViewerSession]
        → _onValidatedRef.current?.()  [calls ViewerScreen's _setPageRef.current]
          → setPage(1)             [inside useViewerLayout via ViewerScreen's _setPageRef]
```

### _setPageRef — new ref required in ViewerScreen

The `doValidate → setPage(1)` call creates a circular dependency between
`useViewerSession` (produces `session`) and `useViewerLayout` (produces `setPage`).
The `_setPageRef` pattern breaks this cycle:

```
ViewerScreen render body:
  const _setPageRef = useRef(null);              ← stays in ViewerScreen

  useViewerSession(doc, publicToken, {
    onValidated: () => _setPageRef.current?.()   ← stable closure (ref never changes)
  })
  → produces session

  useViewerLayout(session, ...)
  → produces setPage

  _setPageRef.current = () => setPage(1);        ← render-body assignment, always current

  usePageLoader({ ..., onAuth401: () => reinitRef.current?.() })
```

This is identical in structure to:
- `reinitRef.current = async () => {...}` (current code)
- `_onAuth401Ref` inside `usePageLoader` (Phase 2.6)
- `_onToggleSearchRef` inside `useViewerLayout` (Phase 2.5)

---

## 3. Full Listener Inventory

### Effect: Security Listeners — `deps: [session]`

| # | Handler var | Event type | Target | Condition | Action | Cleanup | Security impact |
|---|------------|------------|--------|-----------|--------|---------|-----------------|
| 1 | `blockRC` | `contextmenu` | `document` | `!perms.can_right_click` | `preventDefault` + `logEvent('right_click_attempt')` + toast | `removeEventListener` | DRM enforcement — blocks right-click data extraction |
| 2 | `blockKB` | `keydown` | `document` | ctrl+P + `!perms.can_print` | `preventDefault` + `stopPropagation` + `logEvent('print_attempt')` + toast | same handler remove | DRM enforcement — blocks print dialog |
| 3 | `blockKB` | `keydown` | `document` | ctrl+C/X/A/U + `!perms.can_copy` | `preventDefault` + `stopPropagation` + `logEvent('copy_attempt')` + toast | same handler remove | DRM enforcement — blocks clipboard extraction |
| 4 | `blockKB` | `keydown` | `document` | ctrl+S + `!perms.can_download` | `preventDefault` + `stopPropagation` + `logEvent('download_attempt')` + toast | same handler remove | DRM enforcement — blocks save-as |
| 5 | `onBP` | `beforeprint` | `window` | `!perms.can_print` | hide `.viewer-page` elements + `logEvent('print_attempt')` | `removeEventListener` | Print-screen DRM — hides document from OS print dialog |
| 6 | `onAP` | `afterprint` | `window` | always | restore `.viewer-page` element visibility | `removeEventListener` | Restores visibility after any print (including allowed) |
| 7 | `onBlur` | `blur` | `window` | always | `setBlurred(true)` | `removeEventListener` | Blur overlay when app loses focus (DRM visual protection) |
| 8 | `onFocus` | `focus` | `window` | always | `setBlurred(false)` | `removeEventListener` | Remove blur overlay when app regains focus |

**Cleanup path**: Single `return () => {...}` that removes all 8 listeners. All 8 must be removed together. If any removal is omitted, listeners accumulate across session changes, firing multiple times.

**Registration path**: `document.addEventListener(contextmenu, blockRC)` + `document.addEventListener(keydown, blockKB)` + `window.addEventListener(beforeprint, onBP)` + `window.addEventListener(afterprint, onAP)` + `window.addEventListener(blur, onBlur)` + `window.addEventListener(focus, onFocus)`.

Note: handlers `#2, #3, #4` share a single `blockKB` function, added once via `document.addEventListener('keydown', blockKB)`. Three checks are inside `blockKB`. Removing `blockKB` removes all three actions.

### Effect: Tab Visibility — `deps: [session]`

| # | Handler var | Event type | Target | Condition | Action | Cleanup | Security impact |
|---|------------|------------|--------|-----------|--------|---------|-----------------|
| 9 | `onVis` | `visibilitychange` | `document` | always | `setBlurred(document.hidden)` | `removeEventListener` | Mobile tab-switch DRM — applies blur overlay when tab goes to background |

**Cleanup path**: `return () => document.removeEventListener('visibilitychange', onVis)`.

This effect is separate from the security listeners effect. Both have `deps: [session]`. After extraction they must remain separate effects — or can be merged inside the hook since the dep array is identical. Merging is optional but reduces effect count by one.

### Effect: Auto-create-link + gate probe — `deps: [docId]`

No event listeners registered. Async IIFE that fires API calls. No cleanup path.

**Note**: The missing `AbortController` is a pre-existing issue (see Failure Mode #4). Do not introduce one during this refactor.

---

## 4. Validation Flow Diagram

```
ViewerScreen mounts
        │
        ▼
useViewerSession: auto-create-link effect fires (deps: [docId])
        │
        ├─ publicToken provided (public viewer URL)
        │        │
        │        ▼
        │   token = publicToken
        │
        └─ no publicToken (admin/authenticated mode)
                 │
                 ▼
            SecureDocAPI.getLinks(docId)
                 │
                 ├─ active links found → token = active[0].token
                 └─ no active links   → SecureDocAPI.createLink(...)
                                                   └─ token = nl.token
                 
        ▼ (both paths converge)
setPendingToken(token)
        │
        ▼
SecureDocAPI.getGateRequirements(token)
        │
        ├─ gate.status !== 'active'  OR
        │  gate.requires_password    OR
        │  gate.requires_email
        │           │
        │           ▼
        │   setGateInfo(gate); setInit(false)
        │   → AccessGate overlay renders
        │   → user submits email/pw
        │   → onSubmit: doValidate(pendingToken, email, pw)
        │
        └─ no restrictions (open link)
                    │
                    ▼
              await doValidate(token, null, null)

doValidate(token, email, password)
        │
        ├─ storedSessionId = sessionStorage.getItem(...)
        │
        ▼
SecureDocAPI.validateLink(token, password, email, storedSessionId)
        │
        ├─ SUCCESS (200)
        │       │
        │       ├─ sessionStorage.setItem(securedoc_sess_${token}, res.session_id)
        │       ├─ setSession({ ...res, link_token: token })
        │       ├─ setGateInfo(null)
        │       └─ _onValidatedRef.current?.()   [After Phase 2.7: calls _setPageRef.current → setPage(1)]
        │
        ├─ 401 (wrong password / missing)
        │       └─ setGateError('Wrong password. Try again.' | null)
        │          → AccessGate stays visible with error
        │
        ├─ 403 / 429 (domain/IP/email/concurrent denied)
        │       └─ setGateError(_errMsg(e, 'Access denied'))
        │          → AccessGate stays visible with error
        │
        ├─ 410 / 404 (revoked / expired / not found)
        │       └─ sessionStorage.removeItem(...)
        │          setGateInfo({ status: 'revoked'|'expired'|'not_found', ... })
        │          → AccessGate shows terminal state (no retry button)
        │
        └─ other (network error, 500, etc.)
                └─ toast(_errMsg(e, 'Failed to open viewer'), 'error')
                   → viewer stays on loading state

        All paths: finally { setInit(false) }
```

---

## 5. Re-authentication Flow (401 from Page Fetch)

```
User navigates to page N
        │
        ▼
usePageLoader.loadPage → fetch(pageUrl) → 401 response
        │
        ▼
_onAuth401Ref.current?.()        [inside usePageLoader — stable ref to callback]
        │
        ▼
reinitRef.current?.()            [in ViewerScreen — passed as onAuth401 source]
        │
        ▼ (reinitRef.current body, runs every render, always current)
const token = session?.link_token || pendingToken
        │
        ├─ no token → return (silent no-op)
        │
        ▼
sessionStorage.removeItem(securedoc_sess_${token})
        │
        ▼
SecureDocAPI.getGateRequirements(token)
        │
        ├─ gate has restrictions (pw / email / inactive)
        │       │
        │       ▼
        │   setSession(null)
        │   setGateInfo(gate)
        │   setPendingToken(token)
        │   setInit(false)
        │   → AccessGate overlay renders
        │   → user re-authenticates via doValidate(pendingToken, email, pw)
        │
        └─ gate is open (token still active, no restrictions)
                │
                ▼
          await doValidate(token, null, null)
                │
                ▼ (SUCCESS)
          setSession(newSession)
          _onValidatedRef.current?.() → setPage(1)
          → viewer reloads from page 1 with new session
```

**Ref chain on 401** (3 hops):
```
usePageLoader._onAuth401Ref    →    reinitRef (ViewerScreen)    →    doValidate (useViewerSession)
```

All three refs use the same stable-ref pattern. No stale closures possible if the
render-body assignment pattern is maintained correctly.

---

## 6. Hook Boundary Proposal

### Moves INTO `useViewerSession`

| Symbol | Type | Lines |
|--------|------|-------|
| `session` / `setSession` | useState | 1 |
| `blurred` / `setBlurred` | useState | 1 |
| `initializing` / `setInit` | useState | 1 |
| `gateInfo` / `setGateInfo` | useState | 1 |
| `gateError` / `setGateError` | useState | 1 |
| `pendingToken` / `setPendingToken` | useState | 1 |
| `reinitRef` | useRef | 1 |
| `doValidate` | async function | 33 |
| `reinitRef.current = async () => {...}` | render-body assignment | 16 |
| `useEffect auto-create-link` | effect + deps + comment | 32 |
| `useEffect security listeners` | effect + deps + comment | 22 |
| `useEffect tab visibility` | effect + deps + comment | 9 |
| `useToast()` call | context hook | 1 (internal) |
| **Total removed from ViewerScreen** | | **~119 lines** |

### STAYS in ViewerScreen

| Symbol | Reason |
|--------|--------|
| `toast = useToast()` | useViewerSession calls `useToast()` internally |
| `showInfo/showSearch/showToc/showLaser/showMagnifier` | UI-only toggles |
| `showInsights/insightsData/insightsLoading` | UI data loaded on demand in JSX handler |
| `showLinks/showPageList` | UI-only toggles |
| `_setPageRef` | New ref in ViewerScreen to break session→layout circular dep |
| shimmer inject effect | Pure DOM side-effect; unrelated to session logic |
| `docName` / `docId` / `PAGE_COUNT` / `isTextDoc` | Derived values; stay as derived constants |

### Hook signature

```js
export function useViewerSession(doc, publicToken, { onValidated } = {})
```

Returns:
```js
{
  session, setSession,
  blurred,
  initializing,
  gateInfo, setGateInfo,
  gateError, setGateError,
  pendingToken, setPendingToken,
  reinitRef,
  doValidate,
}
```

`setGateError` and `doValidate` are returned because ViewerScreen's AccessGate
`onSubmit` handler calls both:
```js
onSubmit={(email, pw) => { setGateError(null); doValidate(pendingToken, email, pw); }}
```

### Hook call order in ViewerScreen after Phase 2.7

```js
const _setPageRef = useRef(null);  // NEW — breaks setPage circular dep

// 1. Session lifecycle — produces session, reinitRef, blurred, initializing, gate state
const { session, blurred, initializing, gateInfo, setGateInfo,
        gateError, setGateError, pendingToken, setPendingToken,
        reinitRef, doValidate,
} = useViewerSession(doc, publicToken, { onValidated: () => _setPageRef.current?.() });

// 2. Navigation / layout / keyboard — needs session
const { page, setPage, ... } = useViewerLayout(session, { onToggleSearch: ... });

// Inject setPage after useViewerLayout — safe render-body assignment
_setPageRef.current = () => setPage(1);

// 3. Page image loading — needs session, page, reinitRef
const { imgSrc, ... } = usePageLoader({ session, page, twoPageMode, isTextDoc,
                                         onAuth401: () => reinitRef.current?.() });

// 4-7. Content / search / links / annotations — unchanged ordering
const { textContent, ... } = useTextLoader(session, page, isTextDoc);
const { searchHighlightQuery, ..., wordPositionsRef, wordPositionsFetched } = useSearchHighlights(session, page);
const { pageLinksRef, ... } = useLinksSidecar(session, doc?.id, isTextDoc, { onAutoExtractReset: ... });
const { annotTool, ... } = useAnnotations(session, page, isTextDoc);

// [shimmer effect]
// All hooks have run — safe to conditionally return now
```

---

## 7. Failure-Mode Analysis

### FM-1: Stale closure in `reinitRef.current` — CRITICAL

**Risk**: If `reinitRef.current = async () => {...}` is moved into a `useEffect`
(rather than the render body), it becomes one render stale. On the render immediately
after `setSession(null)`, `reinitRef.current` would still close over the old session
value. In the 401 path, this means the wrong token could be used for re-authentication.

**Current guard**: The assignment is in the render body, not an effect. It runs
synchronously during every render, so `session` and `pendingToken` are always current.

**Mitigation for Phase 2.7**: Keep `reinitRef.current = async () => {...}` in the
render body of `useViewerSession`, exactly as it is in ViewerScreen today. Document
this constraint prominently in the hook.

**Verification**: After implementation, verify that `reinitRef.current` sees the
correct `session.link_token` on both the happy path (session set) and the 401 path
(session cleared, pendingToken fallback).

---

### FM-2: Listener duplication across session changes — MEDIUM

**Risk**: The security listeners effect has `deps: [session]`. Every time `session`
object changes — even if `session_id` is the same — React removes all 8 listeners
and re-registers them. This creates a gap window (next microtask) where no listeners
are active. During this window, a user could right-click or print without being blocked.

**Severity**: Low in practice — the gap is one microtask tick (~0.01ms). No known
exploit path. But it is theoretically possible on every re-render that triggers a
new `session` object even with the same ID.

**Mitigation option**: Change `deps: [session]` to `deps: [session?.session_id]`.
Listeners are then only re-registered when the session ID changes, not on every
incidental `session` object re-allocation.

**Recommendation for Phase 2.7**: Adopt `deps: [session?.session_id]` in the hook.
This is strictly safer and more precise. The closures inside `blockRC` and `blockKB`
close over `session` directly (for `session.permissions` and `logEvent` args). To
keep these current, use the stable-ref pattern: store `session` in a ref updated by
a bare `useEffect`, and reference the ref inside the handlers.

**Alternatively**: Keep `deps: [session]` and accept the existing gap. Document it.
Do not change behavior — only refactor structure.

**Decision needed from implementer**: Pick one of the two options above before
implementation. Do not silently change behavior without documenting it.

---

### FM-3: Missing cleanup in auto-create-link effect — LOW

**Risk**: The auto-create-link effect is an async IIFE with no cleanup function and
no AbortController. If `docId` changes (user switches docs) while the IIFE is in
flight, it may still call `setSession`, `setGateInfo`, or `doValidate` for the OLD
document's token.

**Severity**: Low — in practice, `docId` changes require the user to explicitly switch
documents in authenticated mode, which is a deliberate navigation. It is not a
rapid-fire event.

**Pre-existing issue**: This risk exists today. Do NOT fix it during Phase 2.7.
Fixing it would require introducing an AbortController and signal threading, which
is a behavior change outside the refactor scope.

**Action**: Document in hook comment. Add a TODO note for a future sprint.

---

### FM-4: Race condition — session set, then immediately 401 — LOW

**Risk**: After `doValidate` succeeds and sets the session, the page fetch begins.
In rare cases (extreme network timing), the new session token could still 401 on
the very first page fetch if the backend session slot hasn't propagated yet. This
would trigger `reinitRef.current()` immediately after a successful validate.

**Behavior**: `reinitRef.current` calls `getGateRequirements` → finds gate is open →
calls `doValidate` again → session re-set → page reloads. Functionally recovers.

**Severity**: Very low. No user data loss. No security regression.

---

### FM-5: `_setPageRef` is null on first `doValidate` call — NEGLIGIBLE

**Risk**: `_setPageRef.current` is set to `() => setPage(1)` in ViewerScreen's render
body after `useViewerLayout` runs. On the very first render, `_setPageRef.current`
is `null` (initialized as `useRef(null)`). If `doValidate` is called during first
render (impossible — it's called from an async effect), the page reset would be skipped.

**Severity**: Zero. `doValidate` is only ever called from:
1. The auto-create-link effect (`useEffect`, fires after render, by which time
   `_setPageRef.current` has been set)
2. The AccessGate `onSubmit` handler (user interaction, always after mount)

Effects and event handlers never fire before the first render's commit phase.
`_setPageRef.current` is set synchronously in the render body before any effect fires.

---

### FM-6: `toast` call from security effect in extracted hook — LOW

**Risk**: If `useViewerSession` calls `useToast()` internally and the hook is mounted
outside a `ToastProvider`, `toast` would be `null` and calls would throw.

**Current guard**: `ViewerScreen` is always a child of `ToastProvider` (see `App`
render tree). The constraint is architectural, not enforced by code.

**Mitigation**: Add a null-guard: `toast?.('msg', 'warning')`. This matches the
existing `window.SecureDocAPI?.logEvent(...)` optional-chaining style.

---

### FM-7: `doValidate` returned to ViewerScreen — access to setter internals — LOW

`doValidate` is returned from `useViewerSession` so that `AccessGate.onSubmit` can
call it. This means ViewerScreen has a reference to an async function with capture
access to all of `useViewerSession`'s internal state setters. This is intentional
and fine — it is the same function that existed in ViewerScreen today. No new
encapsulation is lost.

---

## 8. Verification Checklist

All items must pass after Phase 2.7 is implemented. Manual tests — cannot be
verified by type-checker or build.

### Session Bootstrap

- [ ] Public-link viewer opens automatically (no gate, no publicToken flow)
- [ ] Admin viewer auto-creates a link for a docId with no existing links
- [ ] Admin viewer reuses the first active link when one exists (does not create duplicate)
- [ ] Link with password gate shows AccessGate password form
- [ ] Link with email gate shows AccessGate email form
- [ ] Link with both gates shows both fields
- [ ] Wrong password → stays on gate, shows 'Wrong password. Try again.'
- [ ] 403 (domain/IP denied) → stays on gate, shows access-denied message
- [ ] 429 (concurrent limit) → stays on gate, shows access-denied message
- [ ] 404 token → terminal gate state, no retry
- [ ] 410 revoked → terminal gate state, no retry
- [ ] 410 expired → terminal gate state, no retry
- [ ] Network error during validate → toast 'Failed to open viewer', error
- [ ] After successful validate → viewer loads from page 1 (page reset confirmed)
- [ ] `initializing=true` spinner shows during bootstrap
- [ ] `initializing=false` after any terminal state (success, gate, error)

### Session Restore (sessionStorage)

- [ ] Reload page on page 5 → restores to page 5 (useViewerLayout state persist)
- [ ] Reload page → reuses stored session_id (no new session slot created)
- [ ] Revoked token after reload → terminal gate (stored session_id cleared)

### DRM: Right-click

- [ ] Right-click on page image blocked when `can_right_click = false`
- [ ] `right_click_attempt` logged via `SecureDocAPI.logEvent`
- [ ] Toast 'Right-click disabled in secure viewer.' appears
- [ ] Right-click works normally when `can_right_click = true`

### DRM: Keyboard

- [ ] Ctrl+P blocked when `can_print = false`
- [ ] `print_attempt` logged
- [ ] Toast 'Action disabled in secure viewer.' appears
- [ ] Ctrl+P works (browser print dialog opens) when `can_print = true`
- [ ] Ctrl+C blocked when `can_copy = false`
- [ ] Ctrl+X blocked when `can_copy = false`
- [ ] Ctrl+A blocked when `can_copy = false`
- [ ] Ctrl+U blocked when `can_copy = false`
- [ ] `copy_attempt` logged for each
- [ ] Ctrl+S blocked when `can_download = false`
- [ ] `download_attempt` logged
- [ ] Cmd+P / Cmd+C / Cmd+S blocked on macOS (metaKey path)
- [ ] Arrow keys NOT blocked (keyboard navigation unaffected)
- [ ] Ctrl+F / Cmd+F opens search (useViewerLayout owns this — ensure it still fires)

### DRM: Print Lifecycle

- [ ] `beforeprint`: `.viewer-page` elements hidden when `can_print = false`
- [ ] `print_attempt` logged on `beforeprint`
- [ ] `afterprint`: `.viewer-page` elements ALWAYS restored to `visibility: visible`
- [ ] Allowed print (`can_print = true`): `beforeprint` does NOT hide pages
- [ ] After print: pages visible regardless of permission setting

### DRM: Blur Overlay

- [ ] Window blur (Alt+Tab, cmd+Tab) shows blur overlay (14px) over document
- [ ] Window focus removes blur overlay
- [ ] `blurred` state correctly drives `filter: blur(14px)` in all 3 page container locations
- [ ] BlurOverlay component renders when `blurred = true` (both text and image viewers)

### DRM: Tab Visibility

- [ ] Switching browser tabs applies blur overlay
- [ ] Returning to tab removes blur overlay
- [ ] Mobile background tap: blur overlay applies (visibilitychange)

### Re-authentication (401 Recovery)

- [ ] Expire session manually (invalidate token in backend)
- [ ] Navigate to next page → 401 triggers
- [ ] `getGateRequirements` called — if gate open, `doValidate` runs automatically
- [ ] Viewer reloads from page 1 after re-authentication
- [ ] If gate has restrictions after 401 → AccessGate overlay appears
- [ ] After re-authenticating through gate → viewer reloads from page 1
- [ ] Toast 'Session expired. Please reload the page.' on `getGateRequirements` network failure

### Listener Cleanup (no duplication)

- [ ] Navigate between documents in admin mode — no duplicate listeners
- [ ] Session change → old listeners removed before new ones registered
- [ ] Component unmount → all listeners removed (DevTools: no lingering 'contextmenu' handlers)

---

## Summary

### Risk Score

| Risk | Severity | Status |
|------|----------|--------|
| stale `reinitRef.current` if moved to effect | CRITICAL | Mitigable — keep in render body |
| Listener duplication on `session` re-alloc | MEDIUM | Mitigable — `deps: [session?.session_id]` option |
| AbortController missing in auto-create-link | LOW | Pre-existing; do not fix in this sprint |
| 401 → re-validate race condition | LOW | Self-healing; no action needed |
| `_setPageRef` null on first render | NEGLIGIBLE | Architecturally impossible |
| `toast` null outside `ToastProvider` | LOW | Mitigable — add optional chaining |
| `doValidate` returned — internal access | LOW | Intentional and safe |

**Overall extraction risk: MEDIUM** (all critical risks are mitigable with clear patterns)

---

### Extraction Strategy

1. Create `frontend/src/hooks/useViewerSession.js`
2. Move state, reinitRef, doValidate (removing `setPage(1)`, replacing with `_onValidatedRef.current?.()`)
3. Move reinitRef.current render-body assignment
4. Move all three effects
5. Call `useToast()` internally
6. Return `{ session, blurred, initializing, gateInfo, setGateInfo, gateError, setGateError, pendingToken, setPendingToken, reinitRef, doValidate }`
7. In ViewerScreen: add `_setPageRef = useRef(null)`, reorder hook calls (`useViewerSession` first), inject `_setPageRef.current = () => setPage(1)` after `useViewerLayout`

---

### Rollback Strategy

Phase 2.7 is isolated to one new file and edits to one block of `app.jsx`. Rollback:

```bash
git revert <phase-2.7-commit>
```

Or manually:
- Delete `frontend/src/hooks/useViewerSession.js`
- Restore the 6 state declarations, reinitRef, doValidate, reinitRef.current assignment,
  and 3 effects to ViewerScreen (all content is in this document and in git history)
- Remove the `_setPageRef` pattern
- Remove the `useViewerSession` import and hook call
- Rebuild

The DRM and session behaviors are entirely self-contained in the extracted block.
No API contract changes. No database changes. Rollback is zero-risk.

---

### Estimated ViewerScreen Reduction

| Block | Lines removed |
|-------|--------------|
| 6 × useState declarations | 6 |
| reinitRef useRef | 1 |
| doValidate function + comment | 33 |
| reinitRef.current assignment + comment | 16 |
| auto-create-link effect + comment | 32 |
| security listeners effect + comment | 22 |
| tab visibility effect + comment | 9 |
| **Subtotal removed** | **~119** |
| import + hook call block (added) | +14 |
| _setPageRef + _setPageRef.current inject (added) | +2 |
| **Net reduction** | **~103 lines** |

`app.jsx` after Phase 2.7: **~5 533 lines** (estimated)  
Running total from original 6 047: **−514 lines (−8.5%)**

---

### Expected Hook LOC

`frontend/src/hooks/useViewerSession.js` — estimated **~145 lines**:

- Boilerplate header (const React, jsdoc): ~8
- State declarations: 6
- reinitRef: 1
- `_onValidatedRef` + stable update effect: 2
- `doValidate`: 33
- `reinitRef.current` assignment: 16
- auto-create-link effect: 32
- security listeners effect: 22
- tab visibility effect: 9
- return statement: 12
- Total: ~141 lines

---

### Recommended Implementation Sequence

```
Step 1  Create useViewerSession.js scaffold
        - Header, const React destructuring, export function signature
        - Add all state declarations
        - Add reinitRef

Step 2  Move doValidate
        - Replace setPage(1) with _onValidatedRef.current?.()
        - Add _onValidatedRef + bare useEffect for stable ref

Step 3  Move reinitRef.current assignment
        - Keep in render body (NOT useEffect)
        - Verify it closes over internal session, pendingToken, doValidate, toast

Step 4  Move auto-create-link effect
        - Verify deps: [docId] (docId derived from doc?.id, pass doc as param)
        - Verify doValidate is in scope (internal function)
        - Verify toast is in scope (useToast() called internally)

Step 5  Move security listeners effect
        - Choose dep strategy: [session] (current) or [session?.session_id] (safer)
        - Verify all 8 listeners registered and 8 removed in cleanup
        - Verify setBlurred is in scope (internal state setter)

Step 6  Move tab visibility effect
        - deps: [session]
        - Verify setBlurred is in scope

Step 7  Build return statement
        - All 11 symbols: session, blurred, initializing, gateInfo, setGateInfo,
          gateError, setGateError, pendingToken, setPendingToken, reinitRef, doValidate

Step 8  Update ViewerScreen
        - Add import
        - Add _setPageRef = useRef(null) before first hook call
        - Replace inline state/ref/effect/function blocks with hook call
        - Inject _setPageRef.current = () => setPage(1) after useViewerLayout
        - Verify usePageLoader still gets onAuth401: () => reinitRef.current?.()
        - Verify AccessGate onSubmit still calls doValidate(pendingToken, email, pw)
        - Verify "All hooks have run" comment remains last before conditional returns

Step 9  Build + verify
        - npm run build (zero errors)
        - Run full DRM verification checklist above

Step 10  Write PHASE2_7_USE_VIEWER_SESSION_REPORT.md
```
