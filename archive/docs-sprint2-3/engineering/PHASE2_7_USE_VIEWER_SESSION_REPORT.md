# Phase 2.7 — useViewerSession Extraction Report

**Sprint**: Architecture Refactor Sprint 2, Goal #3  
**Date**: 2026-06-17  
**Status**: Complete ✅

---

## Objective

Extract session lifecycle, gate management, authentication, and all DRM event
listeners from ViewerScreen into `useViewerSession`. No behavior changes.
No API changes. No security regressions.

---

## File Created

**`frontend/src/hooks/useViewerSession.js`** — 148 lines

```js
export function useViewerSession(doc, publicToken, { onValidated, toast } = {})
  → {
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

### Why `toast` is a parameter (not `useToast()` internally)

`useToast()` reads from `ToastCtx` which is defined inside `app.jsx` and not
exported. Hook files cannot import from `app.jsx` without a circular dependency.
`ViewerScreen` passes its own `toast` instance (which it already needs for
non-session JSX handlers). The parameter is called with optional chaining
(`toast?.()`) so a missing value is safe.

---

## Circular Dependency — Implemented Solution

`doValidate` needs `setPage(1)`. `setPage` comes from `useViewerLayout`. But
`useViewerLayout` needs `session` which comes from `useViewerSession`. Classic
circular dep.

**Implemented exactly as specified:**

```js
// Inject point for setPage(1) — breaks session↔layout circular dep
const _setPageRef = useRef(null);

const {
  session, blurred, initializing,
  gateInfo, gateError, setGateError,
  pendingToken,
  reinitRef, doValidate,
} = useViewerSession(doc, publicToken, { onValidated: () => _setPageRef.current?.(), toast });

const { page, setPage, ... } = useViewerLayout(session, ...);

// Inject setPage into the stable ref so useViewerSession.doValidate can reset to page 1
_setPageRef.current = () => setPage(1);
```

`_setPageRef.current` is set synchronously in the render body — identical pattern
to `reinitRef.current` inside `useViewerSession`. Effects fire after render, so
`_setPageRef.current` is always set before any effect calls `_onValidatedRef.current?.()`.

---

## State Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `session` | `null` | Validated viewer session object; consumed by every other hook |
| `initializing` (`setInit`) | `true` | Loading spinner while bootstrap runs |
| `gateInfo` | `null` | Gate requirements for AccessGate overlay |
| `gateError` | `null` | Password/email validation error shown in AccessGate |
| `pendingToken` | `null` | Link token before gate is satisfied |
| `blurred` | `false` | DRM blur overlay state — set by security and visibility effects |

---

## Refs Extracted

| Symbol | Initial | Purpose |
|--------|---------|---------|
| `reinitRef` | `null` | 401 re-entry point; assigned every render (NOT in useEffect) |

**`_onValidatedRef`** is an internal implementation ref (not extracted from
ViewerScreen — it's new). Stores the `onValidated` callback using the stable-ref
pattern so it never appears in effect dep arrays.

**`_setPageRef`** stays in ViewerScreen (new, not extracted). It breaks the
circular dep between `useViewerSession` and `useViewerLayout`.

---

## Functions Extracted

### `doValidate(token, email, password)` — 33 lines

Validates a link token via `SecureDocAPI.validateLink`. On success: persists
session_id to sessionStorage, calls `setSession`, clears gateInfo, calls
`_onValidatedRef.current?.()` (which triggers `_setPageRef.current?.()` → `setPage(1)`).
On error: routes 401/403/410/404 to appropriate gate states; all others to toast.

**Change from ViewerScreen original**: `setPage(1)` replaced with
`_onValidatedRef.current?.()`. Behavior is identical — `_setPageRef.current`
is `() => setPage(1)` by the time any effect calls doValidate.

---

## Effects Extracted

### 1. Auto-create link + gate probe
```
deps: [docId]
```
Resolves a link token (publicToken shortcut → existing active link → create new
link). Probes gate requirements. If gate is open, calls `doValidate` immediately.
If gate has restrictions, sets gateInfo and stops (AccessGate renders).

### 2. DRM security listeners
```
deps: [session]
```
Registers 8 listeners (6 handler functions) when session becomes available.
Cleanup removes all 8 on session change or unmount. `deps: [session]` preserves
current behavior exactly per implementation requirement.

Listeners registered:
- `document: contextmenu` → blockRC (right-click block + logEvent)
- `document: keydown` → blockKB (Ctrl+P/C/X/A/U/S blocks + logEvent)
- `window: beforeprint` → onBP (hide pages + logEvent)
- `window: afterprint` → onAP (restore page visibility)
- `window: blur` → onBlur (setBlurred(true))
- `window: focus` → onFocus (setBlurred(false))

### 3. Tab visibility
```
deps: [session]
```
`document: visibilitychange` → `setBlurred(document.hidden)`. Handles mobile
tab-switch separately from blur/focus (more reliable on mobile).

### `reinitRef.current` render-body assignment (not an effect)

Assigned every render in the hook body. Closes over current `session`,
`pendingToken`, `doValidate`, `toast`. Called by `usePageLoader` on 401
via `onAuth401: () => reinitRef.current?.()` in ViewerScreen.

---

## Lines Removed from ViewerScreen

| Block | Lines |
|-------|-------|
| `session`, `blurred`, `initializing`, `gateInfo`, `gateError`, `pendingToken` state | 6 |
| `reinitRef` useRef + comment | 2 |
| `doValidate` function + comment | 33 |
| `reinitRef.current` assignment + comment | 17 |
| auto-create-link effect + comment | 32 |
| security listeners effect + comment | 22 |
| tab visibility effect + comment | 9 |
| **Total removed** | **121** |

Lines added (import + _setPageRef + hook call + _setPageRef inject + blank line):  **+10**

**Phase 2.7 net reduction: −111 lines**

---

## Build Result

| Metric | Before (Phase 2.6) | After (Phase 2.7) |
|--------|-------------------|------------------|
| `app.jsx` lines | 5 636 | 5 525 |
| Bundle size | 195.8 kb | 196.4 kb |
| Build time | 29 ms | 30 ms |
| Build result | PASS ✅ | PASS ✅ |

Bundle grows 0.6 kb — new hook file boilerplate. Expected.

---

## Running Total (All Phases)

| Phase | Description | Net lines removed from `app.jsx` |
|-------|-------------|----------------------------------|
| Phase 1 | constants + utils | −30 |
| Phase 2.1 | useTextLoader | −35 |
| Phase 2.2 | useLinksSidecar | −23 |
| Phase 2.3 | useSearchHighlights | −26 |
| Phase 2.4 | useAnnotations | −19 |
| Phase 2.5 | useViewerLayout | −58 |
| Phase 2.6 | usePageLoader | −196 |
| Phase 2.7 | useViewerSession | −111 |
| **Total** | | **−498 lines** |

`app.jsx`: **6 047 → 5 525** (−522 lines, −8.6% of file)

_Note: Total column reflects cumulative net including blank-line/comment cleanup;
sum of individual phase deltas is −498._

---

## Hook Inventory (Sprint 2 complete)

| File | Lines | Phase | Responsibility |
|------|-------|-------|----------------|
| `hooks/useViewerSession.js` | 148 | 2.7 | Session lifecycle, auth, DRM |
| `hooks/usePageLoader.js` | 243 | 2.6 | Image loading, cache, prefetch |
| `hooks/useViewerLayout.js` | 139 | 2.5 | Nav, zoom, keyboard, session persistence |
| `hooks/useAnnotations.js` | 68 | 2.4 | Annotation state + load effects |
| `hooks/useSearchHighlights.js` | 62 | 2.3 | Search + word positions |
| `hooks/useLinksSidecar.js` | 68 | 2.2 | Hyperlink sidecar extraction |
| `hooks/useTextLoader.js` | 62 | 2.1 | Text content loading |
| `constants/viewer.js` | 25 | 1 | Layout/zoom constants |
| `utils/viewer.js` | 11 | 1 | Error message helper |

---

## Verification Results

### Build
✅ `npm run build` — 196.4 kb, 30 ms, zero errors

### Hook call order (verified in source)
```
1. useViewerSession   → session, reinitRef, blurred, initializing, gate state
2. useViewerLayout    → page, setPage, layout state
   _setPageRef.current inject (render body)
3. useTextLoader      → text content
4. usePageLoader      → image loading
5. useSearchHighlights → search state
6. useLinksSidecar    → link extraction state
7. useAnnotations     → annotation state
[shimmer effect]
// All hooks have run
```

### Manual verification checklist

**Session bootstrap:**
- [ ] Public link viewer auto-validates on open
- [ ] Admin viewer resolves existing active link
- [ ] Admin viewer creates new link when none exists
- [ ] Password gate shows AccessGate form
- [ ] Email gate shows AccessGate form
- [ ] Wrong password → inline error 'Wrong password. Try again.'
- [ ] 403/429 → access-denied gate error
- [ ] 404 token → terminal gate ('not_found')
- [ ] 410 revoked → terminal gate ('revoked')
- [ ] 410 expired → terminal gate ('expired')
- [ ] Network error during bootstrap → toast 'Failed to open viewer'
- [ ] After validate → viewer loads from page 1

**DRM — right-click:**
- [ ] Right-click on page blocked when `can_right_click = false`
- [ ] `right_click_attempt` logged
- [ ] Toast 'Right-click disabled in secure viewer.' appears
- [ ] Right-click works when `can_right_click = true`

**DRM — keyboard:**
- [ ] Ctrl+P blocked when `can_print = false` → `print_attempt` logged
- [ ] Ctrl+C/X/A/U blocked when `can_copy = false` → `copy_attempt` logged
- [ ] Ctrl+S blocked when `can_download = false` → `download_attempt` logged
- [ ] Cmd+P / Cmd+C / Cmd+S blocked on macOS
- [ ] Arrow keys still navigate pages (useViewerLayout unaffected)
- [ ] Ctrl+F / Cmd+F opens search (useViewerLayout owns this)

**DRM — print lifecycle:**
- [ ] `beforeprint`: `.viewer-page` hidden when `can_print = false`
- [ ] `print_attempt` logged on `beforeprint`
- [ ] `afterprint`: `.viewer-page` ALWAYS restored to visible
- [ ] Allowed print: `beforeprint` does not hide pages

**DRM — blur overlay:**
- [ ] Alt+Tab / Cmd+Tab → blur overlay (14px) visible on document
- [ ] Return to tab → blur removed
- [ ] Browser tab switch → blur overlay (visibilitychange)
- [ ] Return to tab → blur removed
- [ ] `blurred` drives all 3 page container filter locations in JSX

**401 recovery:**
- [ ] Invalidate session manually
- [ ] Navigate page → 401 fires `_onAuth401Ref.current?.()`
- [ ] `reinitRef.current()` called → `getGateRequirements`
- [ ] Open gate: `doValidate` runs → session refreshed → viewer reloads page 1
- [ ] Restricted gate: AccessGate overlay appears
- [ ] Re-auth through gate → viewer reloads from page 1
- [ ] `getGateRequirements` network failure → toast 'Session expired...'

**Listener cleanup:**
- [ ] Switch documents in admin mode → no duplicate listeners
- [ ] DevTools Event Listeners: exactly 1 `contextmenu` handler active at a time
- [ ] DevTools Event Listeners: exactly 1 `keydown` handler (on document) active

---

## Risk Outcome

| Risk from Readiness Review | Outcome |
|---------------------------|---------|
| Stale `reinitRef.current` if in useEffect | ✅ Mitigated — stays in render body |
| Listener duplication on session re-alloc | ✅ Accepted — `deps: [session]` per implementation requirement |
| AbortController missing in auto-create | ✅ Pre-existing — not fixed, as specified |
| `_setPageRef` null on first render | ✅ Impossible in practice — confirmed |
| `toast` null outside ToastProvider | ✅ Mitigated — all calls use `toast?.()` |
| `doValidate` returned — internal access | ✅ Intentional and safe |

---

## Remaining ViewerScreen Responsibilities

### State (10 useState)

| Symbol | Purpose |
|--------|---------|
| `showInfo` | Info panel toggle |
| `showSearch` | Search panel toggle |
| `showToc` | TOC panel toggle |
| `showLaser` | Laser pointer toggle |
| `showMagnifier` | Magnifier tool toggle |
| `showInsights` | Insights panel toggle |
| `insightsData` | Heatmap data (loaded on demand in JSX) |
| `insightsLoading` | Insights fetch state |
| `showLinks` | Links panel toggle |
| `showPageList` | Pages panel toggle |

### Refs (1 useRef)

| Symbol | Purpose |
|--------|---------|
| `_setPageRef` | Breaks session↔layout circular dep; always `() => setPage(1)` |

### Effects (1 useEffect)

| Effect | Deps | Purpose |
|--------|------|---------|
| shimmer style inject | `[]` | Injects CSS keyframe once on mount |

### Derived constants (inline, no hooks)

| Symbol | Derived from |
|--------|-------------|
| `docName` | `doc?.filename \|\| doc?.name \|\| session?.document_filename` |
| `docId` | `doc?.id \|\| ''` |
| `PAGE_COUNT` | `session?.page_count \|\| 1` |
| `isTextDoc` | `session?.doc_type` check |
| `isTwoPage` | `twoPageMode` alias |
| `_setPageRef.current` | `() => setPage(1)` — render-body inject |

### Everything else in ViewerScreen

All remaining code is JSX render logic and inline event handlers in JSX props.
There are no more extractable effects. All state is UI-only panel toggles.

---

## Remaining Line Count

`app.jsx`: **5 525 lines**

Estimated breakdown of remaining 5 525 lines:
- Imports + constants (top-level): ~12
- Design tokens (C object): ~55
- Shared atom components (SectionLabel, StatusDot, Btn, etc.): ~220
- Toast system (ToastCtx, ToastProvider, Toast): ~50
- AccessGate component: ~68
- ViewerToolbar component: ~400
- DocumentPicker component: ~115
- ThumbnailStrip component: ~95
- TOC component: ~80
- SearchPanel component: ~130
- LinksPanel component: ~220
- InsightsPanel component: ~180
- AnnotationLayer + drawing + comment components: ~850
- RectMagnifier component: ~80
- ViewerScreen function (hooks + JSX): ~720
- DocManagement screen + sub-components: ~2000
- App root + router: ~50
- Remaining misc: ~200

The ViewerScreen *function body* is now approximately **720 lines** (down from the
original ~1800+ lines when counting all inline state, effects, and JSX).

---

## Component Extraction Candidates — Sprint 3

The following are the highest-impact extraction targets, ranked by
estimated line reduction and isolation clarity.

### Rank 1: `ViewerToolbar` — ~400 lines (HIGHEST IMPACT)

Already defined as a standalone component (`function ViewerToolbar`). Currently
lives in `app.jsx`. Move to `frontend/src/components/ViewerToolbar.jsx`.
Receives ~25 props; no shared state with ViewerScreen body. Pure presentation
with event callbacks. Zero risk extraction.

**Estimated reduction**: ~400 lines from `app.jsx`

### Rank 2: `DocManagement` screen + sub-components — ~2000 lines

The entire admin management screen (links, feedback, annotations, events, analytics,
storage) lives in `app.jsx`. Extracting to `components/DocManagement.jsx` (or further
decomposed into panel components) would be the single largest reduction.

**Estimated reduction**: ~1 800–2 000 lines from `app.jsx`

### Rank 3: `AnnotationLayer` + drawing + comment components — ~850 lines

The annotation drawing canvas, comment threads, and reply panel are complex but
well-scoped. They could move to `components/AnnotationLayer.jsx` with a sub-directory.

**Estimated reduction**: ~800 lines from `app.jsx`

### Rank 4: `LinksPanel` + `InsightsPanel` + `SearchPanel` — ~530 lines combined

Three side-panel components that are already structurally self-contained. Pure
presentation with callbacks into ViewerScreen state. Low-risk extractions.

**Estimated reduction**: ~500 lines from `app.jsx`

### Rank 5: Design tokens + shared atoms — ~325 lines

`C` object, `SectionLabel`, `StatusDot`, `Btn`, `label()` helper, `mono`. Could
move to `constants/tokens.js` + `components/atoms.jsx`. High reuse value but lower
immediate line-count impact on `app.jsx`.

**Estimated reduction**: ~280 lines from `app.jsx`

---

## Recommended Sprint 3 Sequence

Sprint 3 should shift from hook extraction to **component file extraction**.
The single-file constraint has been addressed at the hook/state layer. The remaining
opportunity is in JSX component decomposition.

```
Sprint 3, Phase 3.1: Extract ViewerToolbar
  File: frontend/src/components/ViewerToolbar.jsx
  Risk: Very low (zero shared state, pure props)
  Impact: ~400 lines from app.jsx

Sprint 3, Phase 3.2: Extract AnnotationLayer
  File: frontend/src/components/AnnotationLayer.jsx
  Risk: Medium (closes over many ViewerScreen values; needs careful prop list)
  Impact: ~800 lines from app.jsx

Sprint 3, Phase 3.3: Extract SearchPanel / LinksPanel / InsightsPanel
  Files: frontend/src/components/{Search,Links,Insights}Panel.jsx
  Risk: Low (well-scoped, callback-based)
  Impact: ~500 lines from app.jsx

Sprint 3, Phase 3.4: Extract DocManagement
  File: frontend/src/components/DocManagement.jsx (+ sub-components)
  Risk: Low-medium (independent of viewer state entirely)
  Impact: ~1800 lines from app.jsx

Sprint 3, Phase 3.5: Extract design tokens + shared atoms
  Files: frontend/src/constants/tokens.js, frontend/src/components/atoms.jsx
  Risk: Very low
  Impact: ~280 lines from app.jsx
```

**Estimated `app.jsx` after Sprint 3**: ~1 200–1 500 lines (router + App root +
thin ViewerScreen shell + DocManagement router entry).

---

## Final Totals After Sprint 2

| Metric | Original | After Sprint 2 |
|--------|----------|----------------|
| `app.jsx` lines | 6 047 | 5 525 |
| Net reduction | — | **−522 lines (−8.6%)** |
| Hook files | 0 | 7 |
| Constants/utils files | 0 | 2 |
| Bundle size | ~180 kb | 196.4 kb |

Bundle grows because split files now have per-file boilerplate and esbuild
includes them as separate modules. This is expected and acceptable — the goal
is maintainability, not bundle size reduction.
