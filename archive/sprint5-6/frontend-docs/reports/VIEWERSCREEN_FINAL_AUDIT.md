> **HISTORICAL ARCHIVE** — Sprint milestone record. Reflects state at time of writing. Not current state.

# ViewerScreen Final Audit
Sprint 4.2D — Phase 0
Date: 2026-06-22
Status: DO NOT IMPLEMENT — audit only

---

## Executive Summary

ViewerScreen is 840 lines with 8 custom hooks, 7 cross-hook refs, and 2 render-body ref assignments. The extraction is mechanically straightforward (copy-paste, not refactor) but is the highest-risk operation in this codebase due to strict hook call order constraints, ref-in-render-body patterns that cannot be moved to useEffect, and one cross-hook external ref mutation pattern. All risks are understood and documented. **GO WITH WARNINGS** — see Section 9.

---

## 1. Hook Call Order Graph

```
Position  Hook                 Why this position is required
────────  ─────────────────── ──────────────────────────────────────────────────────────
  1       useToast             No deps. Toast needed for all error handlers below.
  2       useState × 9         Local UI state. No deps.
  3       useRef(_setPageRef)  MUST precede useViewerSession so the ref object exists
                               when the onValidated callback closure is created.
  4       useViewerSession     Receives the onValidated callback via _setPageRef.
                               Returns reinitRef needed by usePageLoader (step 9).
  5       Derived constants    docName, docId, PAGE_COUNT, isTextDoc — all read from
                               `session` which useViewerSession provides.
  6       useViewerLayout      Returns page, setPage, twoPageMode, touchRef.
                               MUST precede step 7 (setPage assignment) and all hooks
                               that consume `page` (steps 8, 9, 10, 12).
  7 ⚠    _setPageRef.current  RENDER BODY ASSIGNMENT — NOT in useEffect.
                               Uses setPage returned from step 6.
                               Fills the ref so useViewerSession.doValidate can call
                               setPage(1) on session re-validation. Cannot be moved to
                               useEffect — it would fire one render late, causing a
                               stale setPage reference on the first 401 recovery.
  8       useTextLoader        Consumes session (step 4) + page (step 6).
  9       usePageLoader        Consumes session (step 4) + page + twoPageMode (step 6)
                               + reinitRef (step 4, via onAuth401 callback).
  10      useSearchHighlights  Consumes session (step 4) + page (step 6).
                               Returns wordPositionsRef + wordPositionsFetched needed
                               by useLinksSidecar's onAutoExtractReset callback (step 11).
  11      useLinksSidecar      Consumes session (step 4) + doc.id + isTextDoc (step 5)
                               + wordPositionsRef + wordPositionsFetched (step 10, via
                               onAutoExtractReset closure). MUST come after step 10.
  12      useAnnotations       Consumes session (step 4) + page (step 6) + isTextDoc.
                               Has no deps on steps 7–11. Placed last for readability.
  13      useEffect (shimmer)  Style injection. No deps on any hook output.
```

**Hard ordering constraints (violation → runtime bug):**
- 3 → 4: `_setPageRef` must exist before `useViewerSession` captures it in closure
- 4 → 7: `reinitRef` must be available before render body assignment at step 7 uses it contextually
- 6 → 7: `setPage` must be returned from `useViewerLayout` before the ref is filled
- 4 → 9: `reinitRef` must exist before `usePageLoader` captures it in `onAuth401`
- 10 → 11: `wordPositionsRef` and `wordPositionsFetched` must be available before `useLinksSidecar` captures them in `onAutoExtractReset`

---

## 2. Ref Ownership Graph

### `_setPageRef`
| Role | Owner |
|---|---|
| Creator | ViewerScreen (`useRef(null)` at step 3) |
| Writer | ViewerScreen render body (`_setPageRef.current = () => setPage(1)` at step 7) |
| Reader | useViewerSession internally, via `_onValidatedRef` which stores the callback |

**Pattern:** Created in ViewerScreen before useViewerSession so the ref object is stable. Filled after useViewerLayout provides setPage. useViewerSession stores the callback in its own `_onValidatedRef` and calls it after successful validation. The render-body write ensures setPage is never stale.

**Extraction constraint:** Both the `useRef(null)` and the `_setPageRef.current = () => setPage(1)` assignment must stay in ViewerScreen.jsx at exactly their current positions relative to the hook calls.

---

### `reinitRef`
| Role | Owner |
|---|---|
| Creator | useViewerSession internally (`useRef(null)`) |
| Writer | useViewerSession render body — `reinitRef.current = async () => { ... }` on every render, closing over current `session` and `pendingToken` |
| Reader | usePageLoader, via `_onAuth401Ref` which stores `() => reinitRef.current?.()` |

**Pattern:** `reinitRef` is created AND written inside useViewerSession, NOT in ViewerScreen. The render-body assignment inside useViewerSession is already documented in the hook's JSDoc comment. This pattern is self-contained — extraction of ViewerScreen does not change it.

**No extraction risk** — this ref lives entirely inside useViewerSession.

---

### `annotCacheRef`
| Role | Owner |
|---|---|
| Creator | useAnnotations (`useRef(new Map())`) |
| Writer | ViewerScreen JSX handlers (onDraw, onDelete, CommentPopup onSave, undo handler) |
| Reader | ViewerScreen JSX undo handler (`annotCacheRef.current.set(page, updated)`) |

**Pattern:** Owned by useAnnotations, passed back to ViewerScreen, then written directly in the annotation create/delete callbacks. This is a performance optimization — direct ref mutation avoids re-renders from state updates during draw operations.

**Extraction constraint:** The annotCacheRef usages in ViewerScreen JSX are inline callbacks in the JSX. They must be copied verbatim. No extraction risk since scope doesn't change.

---

### `wordPositionsRef`
| Role | Owner |
|---|---|
| Creator | useSearchHighlights (`useRef({})`) |
| Writer (primary) | useSearchHighlights (`wordPositionsRef.current = map` after API call) |
| Writer (secondary) | useLinksSidecar via `onAutoExtractReset: () => { wordPositionsRef.current = {}; ... }` |
| Writer (tertiary) | ViewerScreen info panel via `onSidecarExtract: () => { pageLinksRef.current = {}; ... wordPositionsRef.current = {}; ... }` |
| Reader | useSearchHighlights (`_computeHighlights` reads `wordPositionsRef.current[pageNum]`) |

**Risk:** `wordPositionsRef` is a cross-hook external write — a ref owned by useSearchHighlights is mutated externally by two other sites. This creates an invisible dependency between useLinksSidecar, ViewerInfoPanel, and useSearchHighlights. Extraction does not change this topology — all three sites remain in the same component body.

---

### `wordPositionsFetched`
| Role | Owner |
|---|---|
| Creator | useSearchHighlights (`useRef(false)`) |
| Writer (primary) | useSearchHighlights (sets to `true` after first fetch) |
| Writer (secondary) | useLinksSidecar via `onAutoExtractReset: () => { ...; wordPositionsFetched.current = false; }` |
| Reader | useSearchHighlights (guard: `if (wordPositionsFetched.current) { recompute only }`) |

**Risk:** Same cross-hook write pattern as wordPositionsRef. The secondary writer (useLinksSidecar's timer callback) resets the guard so useSearchHighlights re-fetches word positions after sidecar extraction completes. If this write is lost during extraction, search highlights silently stop updating after a sidecar re-extract.

---

### `touchRef`
| Role | Owner |
|---|---|
| Creator | useViewerLayout (`useRef({ x: null, y: null, pinchDist: null })`) |
| Writer | ViewerScreen JSX `onTouchStart` (canvas and page container) |
| Reader | ViewerScreen JSX `onTouchEnd` (swipe delta), `onTouchMove` (pinch delta) |

**Pattern:** useViewerLayout creates the ref structure; ViewerScreen's JSX reads and writes the ref fields in touch handlers. No state updates in touch handlers — direct ref mutation is intentional for 60fps touch responsiveness.

**No extraction risk** — all touch handler code is in ViewerScreen's JSX and stays together.

---

### `pageLinksRef`
| Role | Owner |
|---|---|
| Creator | useLinksSidecar (`useRef({})`) |
| Writer (primary) | useLinksSidecar (fills `page → [{x,y,w,h,url,...}]` map after API call) |
| Writer (secondary) | useLinksSidecar auto-extract timer (`pageLinksRef.current = {}` before reload) |
| Writer (tertiary) | ViewerScreen info panel handler (`pageLinksRef.current = {}` on manual re-extract) |
| Reader | ViewerScreen JSX (renders link overlay `<a>` tags for current page) |
| Reader | ViewerToolbar prop: `linksCount={linksLoaded ? (pageLinksRef.current[page] || []).length : 0}` |

**Pattern:** Like wordPositionsRef, this ref is owned by one hook but reset from multiple external sites. The two external reset sites (auto-extract timer and manual re-extract) both do a reset-then-reload pattern. Extraction does not change this.

---

## 3. Session Recovery Chain

```
HTTP 401 from page load
│
├─ usePageLoader.loadPage() detects r.status === 401
│  └─ _onAuth401Ref.current?.()
│     └─ This is: () => reinitRef.current?.()
│        (ViewerScreen passes this as onAuth401 to usePageLoader)
│
├─ reinitRef.current() executes (async function in useViewerSession)
│  ├─ Closes over CURRENT session?.link_token and pendingToken (render-body closure)
│  ├─ sessionStorage.removeItem(`securedoc_sess_${token}`) — clears cached session slot
│  └─ getGateRequirements(token) — probe if re-auth is required
│
├─ BRANCH A: no gate restrictions (status='active', no password/email)
│  ├─ doValidate(token, null, null) is called
│  │  ├─ setInit(true) — shows loading spinner
│  │  ├─ validateLink(token, null, null, null) — no storedSessionId (was removed)
│  │  ├─ setSession({ ...res, link_token: token }) — new session established
│  │  ├─ setGateInfo(null) — clears any gate UI
│  │  └─ _onValidatedRef.current?.()
│  │     └─ This is: () => _setPageRef.current?.()
│  │        └─ _setPageRef.current() = () => setPage(1)
│  │           └─ setPage(1) — viewer resets to page 1
│  │
│  └─ usePageLoader's useEffect fires (session changed) → loadPage(new token, 1, new sessionId)
│     → page loads successfully with new session
│
└─ BRANCH B: gate required (password, email, or blocked)
   ├─ setSession(null) — clears active session
   ├─ setGateInfo(gate) — triggers AccessGate render (early return in ViewerScreen)
   └─ User sees AccessGate, enters credentials, submits → doValidate is called explicitly
      └─ On success → Branch A flow from doValidate onwards
```

**Critical invariant:** The entire chain depends on `reinitRef.current` being assigned in the render body (not useEffect) of useViewerSession. If moved to useEffect, the function would close over the session/pendingToken values from the previous render, causing it to use a stale or missing token.

---

## 4. Event Listener Audit

### Keyboard listeners

| Listener | Hook | Binding | Event | Purpose |
|---|---|---|---|---|
| `blockKB` | useViewerSession | `document` | `keydown` | DRM: block Ctrl+P (print), Ctrl+C/A/X/U (copy), Ctrl+S (download) |
| `h` | useViewerLayout | `window` | `keydown` | Navigation: arrow keys; Ctrl+F → opens search |

**Potential conflict:** Both hooks listen to `keydown`. Analysis:
- useViewerSession handles: Ctrl+P, Ctrl+C, Ctrl+A, Ctrl+X, Ctrl+U, Ctrl+S (with `e.preventDefault()`)
- useViewerLayout handles: ArrowRight, ArrowDown, ArrowLeft, ArrowUp, Ctrl+F
- No key is handled by both — zero conflict. Each has its own cleanup in useEffect return.
- useViewerSession is added to `document`; useViewerLayout is added to `window`. Both bubble correctly from any child element.

**Ownership verdict:** CLEAN. No ambiguity.

---

### Wheel listener

| Listener | Hook | Binding | Event | Options |
|---|---|---|---|---|
| `blockPinchZoom` | useViewerLayout | `window` | `wheel` | `{ passive: false }` |

Single owner. Blocks Ctrl/Cmd+wheel native zoom. Cleanup in useEffect return.

**Important:** `{ passive: false }` is required for `e.preventDefault()` to work in Chrome. Must be preserved exactly in the extracted file.

---

### Fullscreen listener

| Listener | Hook | Binding | Event | Deps |
|---|---|---|---|---|
| `h` | useViewerLayout | `document` | `fullscreenchange` | `[]` (always) |

Single owner. Syncs `isFullscreen` state with browser fullscreen element.

---

### Visibility listener

| Listener | Hook | Binding | Event | Deps |
|---|---|---|---|---|
| `onVis` | useViewerSession | `document` | `visibilitychange` | `[session]` |

Single owner. Blurs document when tab is hidden (mobile tab-switch protection).

---

### Window blur/focus listeners

| Listener | Hook | Binding | Event | Deps |
|---|---|---|---|---|
| `onBlur` | useViewerSession | `window` | `blur` | `[session]` |
| `onFocus` | useViewerSession | `window` | `focus` | `[session]` |

Single owner. Both registered and cleaned up together.

---

### Print listeners

| Listener | Hook | Binding | Event | Deps |
|---|---|---|---|---|
| `onBP` | useViewerSession | `window` | `beforeprint` | `[session]` |
| `onAP` | useViewerSession | `window` | `afterprint` | `[session]` |

Single owner. `onBP` hides `.viewer-page` elements if printing is blocked; `onAP` restores them.

---

### Summary

All 10 event listeners are cleanly owned by one of two hooks. Zero conflicts. Zero ownership ambiguity. All have corresponding cleanup in useEffect return. No listener is registered directly in ViewerScreen — all are inside hooks.

**No listener moves or changes are needed during extraction.**

---

## 5. Dependency Risk Matrix

| Risk Dimension | Score | Evidence | Mitigation |
|---|---|---|---|
| Circular dependency | LOW (1/5) | No import cycles in hooks. The _setPageRef pattern breaks the session↔page circular dep at runtime, not at import level. | None needed. |
| Stale closure | LOW (2/5) | Both render-body ref assignments (`reinitRef.current` in useViewerSession, `_setPageRef.current` in ViewerScreen) are specifically designed to avoid stale closures. `loadPage` uses refs to read non-stale values from stable callbacks. | Preserve render-body assignments exactly. |
| Ref ownership | MEDIUM (3/5) | `wordPositionsRef`, `wordPositionsFetched`, `pageLinksRef`, `annotCacheRef`, `touchRef` are all written from outside their owning hook. If any external write is lost, behavior silently breaks. | Copy JSX callbacks verbatim. Verify grep for all `.current` writes in extracted file. |
| Hook order | HIGH (4/5) | 5 of 8 hooks have hard call-order constraints. Reordering any constrained pair causes bugs (stale ref, missing ref, early conditional return). | Copy hook calls in exact order. Do not reorder for aesthetic reasons. |
| Regression | MEDIUM (3/5) | App.jsx → ViewerScreen.jsx is 840 lines, but semantically identical to current code. The regex of "copy body, adjust import paths" is mechanical. Key failure mode: forgetting to adjust '../' depth for relative imports. | Verify all import paths during review. Build immediately after creation. |

**Weighted overall risk: MEDIUM-HIGH**

---

## 6. Extraction Boundary

### Recommendation: **A) `src/screens/ViewerScreen.jsx`**

**Verdict: Single file. Do not split.**

**Rationale:**

The proposal to create `ViewerContainer.jsx` + `ViewerScreen.jsx` (or similar split) does not improve the architecture:

1. **No decomposable seam exists.** All 8 hooks interlock through shared refs and callbacks. Any split between "container" and "view" would require threading refs through props, which adds a layer of abstraction with no benefit.

2. **The hooks already provide the decomposition.** Each hook (useViewerSession, useViewerLayout, etc.) is already a named, self-contained module. The component shell is the coordinator — splitting the coordinator adds complexity without removing any.

3. **840 lines is not a problem.** The existing hooks reduce the component to ~200 lines of actual JSX. The remaining 640 lines are hook call declarations and the JSX template. This is within industry-normal range for a complex viewer component.

4. **Two files would double the extraction risk.** Creating an interface between ViewerContainer and ViewerScreen introduces a new prop contract that must be correct and stable. The current extraction has zero new contracts.

5. **The sprint plan specifies ViewerScreen.jsx** (named consistently with UploadScreen.jsx, AccessScreen.jsx, etc.). Changing the target name mid-sprint without user approval violates the execution framework.

---

## 7. Rollback Plan

**Single-commit rollback procedure:**

```bash
# Step 1: Delete extracted file (if created)
rm src/screens/ViewerScreen.jsx

# Step 2: Restore app.jsx and AppShell.jsx from git
git checkout HEAD -- src/app.jsx src/screens/AppShell.jsx

# Step 3: Restore bundle
git checkout HEAD -- dist/app.bundle.js

# Step 4: Verify
npm run build
# Expected: same LOC and bundle size as current HEAD
```

**If committed (not just staged):**
```bash
git revert HEAD --no-commit
git checkout HEAD~1 -- src/screens/ViewerScreen.jsx 2>/dev/null || true
npm run build
git add -A && git commit -m "revert: Sprint 4.2D ViewerScreen extraction"
```

**Rollback scope:** 3 files (ViewerScreen.jsx, app.jsx, AppShell.jsx) + 1 build artifact (dist/app.bundle.js). All other files (hooks, components, other screens) are untouched by the extraction.

**Rollback time:** < 2 minutes if pre-committed; < 30 seconds if just file changes.

---

## 8. Verification Matrix (37 scenarios)

### Auth / Gate
| # | Scenario | Expected |
|---|---|---|
| 1 | Load viewer: no doc, authenticated | Shows Header + DocumentPicker inline picker |
| 2 | Load viewer: doc with no gate | Auto-validates, loads page 1, no gate shown |
| 3 | Load viewer: doc with password gate | AccessGate rendered; email field hidden |
| 4 | Load viewer: doc with email + password gate | AccessGate with both fields |
| 5 | Submit correct password | Gate dismissed, session established, page 1 loads |
| 6 | Submit wrong password | Gate stays, error: "Wrong password. Try again." |
| 7 | Submit to blocked IP/domain/email (403) | Gate stays, error from server |
| 8 | Load revoked/expired link (410/404) | Gate shows terminal state (Revoked/Expired/Not Found) |

### Public token
| # | Scenario | Expected |
|---|---|---|
| 9 | URL: `?token=<token>` | Viewer loads without auth check |
| 10 | URL: `#view/<token>` | Viewer loads without auth check |

### 401 Recovery
| # | Scenario | Expected |
|---|---|---|
| 11 | Session expires mid-viewing (no gate) | 401 → silent revalidate → page 1 → continues |
| 12 | Session expires (gate required) | 401 → AccessGate shown → user re-enters credentials |

### Search
| # | Scenario | Expected |
|---|---|---|
| 13 | Ctrl/Cmd+F opens search panel | SearchPanel visible, focus in input |
| 14 | Type query → page has word positions | Yellow highlight overlays on current page |
| 15 | Navigate to result on different page | Page changes, active highlight turns orange |
| 16 | Close search → highlights clear | No highlights, query cleared |
| 17 | Query on text doc (no word positions) | Fallback banner: "Match found on this page" |
| 18 | Sidecar re-extract → search re-fetches | wordPositionsFetched reset, new positions loaded |

### Links
| # | Scenario | Expected |
|---|---|---|
| 19 | Load PDF with hyperlinks | Transparent `<a>` overlays at PDF coordinates |
| 20 | Click link overlay | Opens in new tab |
| 21 | Open links side panel | 30% overlay shows per-page links |
| 22 | Auto-extract fires (old doc) | 15s timer, then sidecarExtracted=true, reload |

### Annotations
| # | Scenario | Expected |
|---|---|---|
| 23 | Enable highlight tool → draw | Annotation saved via API, appears on page |
| 24 | Enable draw tool → draw | Free-draw annotation saved |
| 25 | Undo last annotation | deleteAnnotation API called, overlay removed |
| 26 | Undo when stack empty | No-op (stack length check guards) |
| 27 | Enable comment/sticky_note tool → click | CommentPopup appears, text input focused |
| 28 | Save comment | createAnnotation called, popup closes, annotation appears |
| 29 | Open annotation thread | Modal shows chronological timeline |
| 30 | Reply to thread (Viewer) | Reply sent, thread refreshed |

### Zoom / Layout
| # | Scenario | Expected |
|---|---|---|
| 31 | + / - toolbar buttons | customZoom changes, layoutMode → CUSTOM |
| 32 | Fit Width | Pages fill canvas width |
| 33 | Fit Height | Pages fill viewport height |
| 34 | Two-page spread | Second page slot renders page+1 |
| 35 | Rotation | `rotate(90deg)` applied, aspect ratio flipped |
| 36 | Pinch zoom (touch) | Custom zoom scales from pinch delta |

### Fullscreen
| # | Scenario | Expected |
|---|---|---|
| 37 | Fullscreen button | requestFullscreen; isFullscreen → true |
| 38 | Esc to exit fullscreen | fullscreenchange event → isFullscreen → false |

### DRM
| # | Scenario | Expected |
|---|---|---|
| 39 | Right-click on page (can_right_click: false) | Event blocked, logEvent('right_click_attempt') |
| 40 | Ctrl+P (can_print: false) | Event blocked, logEvent('print_attempt') |
| 41 | Ctrl+C (can_copy: false) | Event blocked, logEvent('copy_attempt') |
| 42 | Ctrl+S (can_download: false) | Event blocked, logEvent('download_attempt') |
| 43 | Alt-Tab away from window | Page blurred (blur event → setBlurred(true)) |
| 44 | Return to window | Blur cleared (focus event → setBlurred(false)) |
| 45 | Switch browser tabs | visibilitychange → blurred based on document.hidden |
| 46 | Print from menu (can_print: false) | beforeprint hides .viewer-page; afterprint restores |

### Panel Toggles
| # | Scenario | Expected |
|---|---|---|
| 47 | Pages strip toggle | Thumbnail strip shows/hides |
| 48 | TOC button | TocSidebar opens |
| 49 | Info panel button | ViewerInfoPanel opens (230px right panel) |
| 50 | Insights button | insightsData fetched, InsightsModal opens |
| 51 | Links button | LinksPanel opens (30% right overlay) |
| 52 | Laser pointer toggle | LaserPointer active |
| 53 | Magnifier toggle | RectMagnifier active |

### Bookmarks
| # | Scenario | Expected |
|---|---|---|
| 54 | Bookmark current page | toggleBookmark API, set.add(page), icon fills |
| 55 | Unbookmark page | toggleBookmark API, set.delete(page), icon clears |

### Text docs (TXT/MD/LOG)
| # | Scenario | Expected |
|---|---|---|
| 56 | Open TXT/MD/LOG | Text chunk loads, no image rendering |
| 57 | Navigate to next chunk | New text content loads |
| 58 | Text with can_copy: false | CSS user-select: none applied |
| 59 | Watermark text set | Watermark overlay renders |

### Download / Print
| # | Scenario | Expected |
|---|---|---|
| 60 | Download (can_download: true) | downloadDocument API called, file saved |
| 61 | Print (can_print: true) | window.print() called, logEvent('printed') |

### Reading progress
| # | Scenario | Expected |
|---|---|---|
| 62 | Navigate to last page | logEvent('completed') fired once |
| 63 | Reading progress bar | Width = (page-1)/(PAGE_COUNT-1) * 100% |

---

## 9. Phase 1 — GO / NO-GO Decision

### **GO WITH WARNINGS**

**Justification:**

The extraction is mechanically safe:
- ViewerScreen is a self-contained function with well-defined inputs (props) and outputs (JSX). No logic needs to be redesigned — it is a direct copy with import path adjustments.
- All 8 hooks are already in separate files with clean exports. No hook code changes.
- All event listeners are inside hooks. No listener moves required.
- The 2 render-body ref assignments are documented in both the hooks and the phase plan. No risk of accidental conversion to useEffect.
- Previous sprints (UploadScreen, AccessScreen, AnalyticsScreen) used the same extraction pattern successfully.

**Warnings (must resolve before writing file):**

| # | Warning | Resolution |
|---|---|---|
| W-01 | **Atoms import is over-specified.** App.jsx imports 14 atoms for ViewerScreen, but ViewerScreen only directly uses `Modal` and `Header`. Must grep to confirm before writing import line. | `grep -E "<(Modal|Header|Btn|Card|Chip|Sidebar|NavItem|Divider|Toggle|Field|SectionLabel|StatusDot|RiskBadge)" src/app.jsx | grep -v import | grep -v "//"`  |
| W-02 | **`ToastProvider` is NOT needed.** App.jsx imports `{ useToast, ToastProvider }` but ToastProvider belongs to AppShell. ViewerScreen only needs `useToast`. | Import only `useToast` from toast.jsx. |
| W-03 | **`Sidebar` and `NavItem` NOT in ViewerScreen.** These are AppShell atoms. Verify with grep before including. | Same grep as W-01. |
| W-04 | **`_errMsg` is used in ViewerScreen.** App.jsx imports it; it must be in ViewerScreen.jsx. | Include `import { _errMsg } from '../utils/viewer.js';` |
| W-05 | **Hook 7 position is absolute.** `_setPageRef.current = () => setPage(1)` must appear between hook calls 6 and 8 in the extracted file. No conditional wrapping, no useEffect. | Verify during file write. |

---

## 10. Verified Atoms for ViewerScreen.jsx

From scanning ViewerScreen JSX (lines 36–879):

| Atom | Used | Evidence |
|---|---|---|
| `Modal` | **YES** | Line 768: `<Modal open={!!threadView}>` |
| `Header` | **YES** | Line 162: `<Header screen="viewer" />` |
| `label` | Unverified | Not seen in JSX scan — verify with grep |
| `SectionLabel` | NO | Not in ViewerScreen JSX |
| `StatusDot` | NO | Not in ViewerScreen JSX |
| `RiskBadge` | NO | Not in ViewerScreen JSX |
| `Chip` | NO | Not in ViewerScreen JSX |
| `Btn` | NO | Not directly — ViewerToolbar receives and renders Btns |
| `Card` | NO | Not in ViewerScreen JSX |
| `Toggle` | NO | Not in ViewerScreen JSX |
| `Field` | NO | Not in ViewerScreen JSX |
| `Divider` | NO | Not in ViewerScreen JSX |
| `Sidebar` | NO | AppShell only |
| `NavItem` | NO | AppShell only |

**Preliminary atoms import for ViewerScreen.jsx:**
```javascript
import { Modal, Header } from '../components/atoms.jsx';
```
**Must be confirmed with grep during Phase 1 before writing the file.**

---

## 11. Import Path Adjustment Map

All imports move from `./X` → `../X` (one level deeper since file moves from `src/` to `src/screens/`):

| app.jsx import | ViewerScreen.jsx import |
|---|---|
| `'./constants/viewer.js'` | `'../constants/viewer.js'` |
| `'./utils/viewer.js'` | `'../utils/viewer.js'` |
| `'./hooks/useTextLoader.js'` | `'../hooks/useTextLoader.js'` |
| `'./hooks/useLinksSidecar.js'` | `'../hooks/useLinksSidecar.js'` |
| `'./hooks/useSearchHighlights.js'` | `'../hooks/useSearchHighlights.js'` |
| `'./hooks/useAnnotations.js'` | `'../hooks/useAnnotations.js'` |
| `'./hooks/useViewerLayout.js'` | `'../hooks/useViewerLayout.js'` |
| `'./hooks/usePageLoader.js'` | `'../hooks/usePageLoader.js'` |
| `'./hooks/useViewerSession.js'` | `'../hooks/useViewerSession.js'` |
| `'./contexts/toast.jsx'` | `'../contexts/toast.jsx'` |
| `'./components/ViewerToolbar.jsx'` | `'../components/ViewerToolbar.jsx'` |
| `'./constants/tokens.js'` | `'../constants/tokens.js'` |
| `'./components/LaserPointer.jsx'` | `'../components/LaserPointer.jsx'` |
| `'./components/RectMagnifier.jsx'` | `'../components/RectMagnifier.jsx'` |
| `'./components/SearchPanel.jsx'` | `'../components/SearchPanel.jsx'` |
| `'./components/InsightsModal.jsx'` | `'../components/InsightsModal.jsx'` |
| `'./components/LinksPanel.jsx'` | `'../components/LinksPanel.jsx'` |
| `'./components/TocSidebar.jsx'` | `'../components/TocSidebar.jsx'` |
| `'./components/PageThumb.jsx'` | `'../components/PageThumb.jsx'` |
| `'./components/ViewerErrorBoundary.jsx'` | not needed (AppShell wraps the screen) |
| `'./components/atoms.jsx'` | `'../components/atoms.jsx'` |
| `'./components/GateMessage.jsx'` | not needed (used only by AccessGate) |
| `'./components/AccessGate.jsx'` | `'../components/AccessGate.jsx'` |
| `'./components/ViewerInfoPanel.jsx'` | `'../components/ViewerInfoPanel.jsx'` |
| `'./components/AnnotationLayer.jsx'` | `'../components/AnnotationLayer.jsx'` |
| `'./components/CommentPopup.jsx'` | `'../components/CommentPopup.jsx'` |
| `'./components/DocumentPicker.jsx'` | `'../components/DocumentPicker.jsx'` |

**Drop from ViewerScreen.jsx:** `ViewerErrorBoundary` (AppShell owns this), `GateMessage` (used by AccessGate internally), `ToastProvider` (AppShell owns this), `Sidebar`, `NavItem` (AppShell only).

**After extraction, app.jsx keeps only:** `import { AppShell } from './screens/AppShell.jsx';`

---

## 12. Expected Final app.jsx (~5 lines)

After ViewerScreen extraction + import cleanup:

```javascript
import { AppShell } from './screens/AppShell.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <AppShell />
);
```

No React destructure needed in app.jsx — no React hooks used in the bootstrap.

---

## Appendix: Ref Usage Confirmation (key sites)

```
_setPageRef  created: app.jsx:53    useRef(null)
             written: app.jsx:85    _setPageRef.current = () => setPage(1)
             read:    useViewerSession.js:52   _onValidatedRef.current?.()

reinitRef    created: useViewerSession.js:32   useRef(null)
             written: useViewerSession.js:76   reinitRef.current = async () => {...}
             read:    app.jsx:96   onAuth401: () => reinitRef.current?.()

annotCacheRef created: useAnnotations.js:25   useRef(new Map())
              written: app.jsx:220/224  annotCacheRef.current.set(page,updated) / .delete(page)
              written: app.jsx:580/582/589/591  onDraw/onDelete handlers
              written: app.jsx:621/623  CommentPopup onSave

wordPositionsRef created: useSearchHighlights.js:18   useRef({})
                 written: useSearchHighlights.js:43   wordPositionsRef.current = map
                 written: app.jsx:117  onAutoExtractReset: wordPositionsRef.current = {}
                 written: app.jsx:742  onSidecarExtract: wordPositionsRef.current = {}

wordPositionsFetched created: useSearchHighlights.js:20   useRef(false)
                     written: useSearchHighlights.js:39   wordPositionsFetched.current = true
                     written: app.jsx:118  onAutoExtractReset: wordPositionsFetched.current = false
                     written: app.jsx:743  onSidecarExtract: wordPositionsFetched.current = false

touchRef     created: useViewerLayout.js:28   useRef({x:null,y:null,pinchDist:null})
             written: app.jsx:318  onTouchStart (canvas)
             written: app.jsx:326  onTouchEnd (canvas)
             written: app.jsx:398  onTouchStart (page container)
             written: app.jsx:408  onTouchMove (page container)
             read:    app.jsx:320/323/408/413 (swipe + pinch reads)

pageLinksRef created: useLinksSidecar.js:25   useRef({})
             written: useLinksSidecar.js:35   pageLinksRef.current = map
             written: useLinksSidecar.js:52   pageLinksRef.current = {} (timer reset)
             written: app.jsx:740  onSidecarExtract: pageLinksRef.current = {}
             read:    app.jsx:198  linksCount prop to ViewerToolbar
             read:    app.jsx:540  link overlay render
             read:    app.jsx:759  LinksPanel prop
```
