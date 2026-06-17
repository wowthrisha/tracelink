# Frontend Architecture Refactor Plan — ViewerScreen Decomposition

**Status**: Analysis complete. No code changed yet.  
**Target**: `frontend/src/app.jsx` lines 1238–2581 (`ViewerScreen` function)  
**Author**: Architecture Refactor Sprint 2, Goal #3  

---

## 1. Current State Inventory

### File structure
```
frontend/src/
└── app.jsx          6 047 lines — the entire application in one file
```

React is loaded via UMD CDN; all symbols (`useState`, `useEffect`, etc.) are
destructured at the top of the file (line 1). esbuild produces a single bundle.
There are no frontend tests.

### ViewerScreen size
| Metric | Value |
|--------|-------|
| Line span | 1238 – 2581 (1 344 lines) |
| `useState` hooks | 53 |
| `useRef` hooks | 12 |
| `useEffect` hooks | 19 |
| `useCallback` hooks | 10 |
| Props received | 3 (`doc`, `publicToken`, `onSelectDoc`) |
| Sub-components called from JSX | 12 |

### Already-extracted child components (in app.jsx, below ViewerScreen)
These exist as standalone functions and are already reasonably self-contained:

| Component | Line | Purpose |
|-----------|------|---------|
| `AnnotationLayer` | 2586 | SVG draw/highlight overlay over page image |
| `CommentPopup` | 2738 | Text input popup for pending comment drafts |
| `AnnotToolbar` | 2768 | Internal annotation tool strip (used by ViewerToolbar) |
| `ViewerToolbar` | 2841 | Chrome-style top toolbar — 27 props today |
| `LaserPointer` | 3156 | GPU-accelerated laser dot (ref-based, no setState) |
| `RectMagnifier` | 3184 | Magnifier window (ref-based, no setState) |
| `InsightsModal` | 3253 | Page heatmap modal overlay |
| `LinksPanel` | 3325 | Hyperlink side panel |
| `SearchPanel` | 3455 | Search overlay (self-contained, own state) |
| `TocSidebar` | 3591 | TOC sidebar (self-contained, own state) |
| `PageThumb` | 3744 | Single page thumbnail |
| `ViewerInfoPanel` | 3891 | Document info + sidecar extract panel |

### Logic still inlined inside ViewerScreen return JSX
- Reading progress bar
- Page thumbnail strip container (wraps `PageThumb`)
- Main canvas (page image + crossfade layers)
- Text document renderer
- Info panel wrapper
- Comment thread modal (threadView / replies)

---

## 2. State Ownership Diagram

```
ViewerScreen
│
├── SESSION / AUTH
│   ├── session              (the validated link session object)
│   ├── initializing         (loading spinner flag)
│   ├── gateInfo             (access requirements — password/email)
│   ├── gateError            (gate error message)
│   ├── pendingToken         (token before session established)
│   └── blurred              (window out-of-focus security blur)
│
├── NAVIGATION
│   ├── page                 (current page number)
│   ├── pageInputStr         (toolbar page-jump text input)
│   ├── twoPageMode          (spread view toggle)
│   └── isFullscreen         (fullscreen API state)
│
├── LAYOUT & ZOOM
│   ├── layoutMode           (AUTO | FIT_WIDTH | FIT_HEIGHT | ACTUAL | CUSTOM)
│   ├── customZoom           (10–400 %)
│   └── rotation             (0 | 90 | 180 | 270)
│
├── PAGE IMAGE LOADING  (PDF/DOCX/DOC)
│   ├── imgSrc               (current page blob URL)
│   ├── imgLoading           (spinner)
│   ├── pageError            (error message)
│   ├── prevImgSrc           (previous page — crossfade background)
│   ├── imgReady             (crossfade trigger from onLoad)
│   ├── imgSrc2              (second page, two-page spread)
│   ├── imgLoading2          (spinner for second page)
│   ├── page2Error           (error for second page)
│   └── pageAspectRatio      (set from naturalWidth/naturalHeight on load)
│
├── TEXT DOCUMENT LOADING  (txt / md / log)
│   ├── textContent          (loaded chunk text)
│   ├── textLoading          (spinner)
│   └── textError            (error message)
│
├── PANEL VISIBILITY  (8 booleans)
│   ├── showSearch
│   ├── showToc
│   ├── showInfo
│   ├── showPageList
│   ├── showLaser
│   ├── showMagnifier
│   ├── showInsights
│   └── showLinks
│
├── INSIGHTS
│   ├── insightsData         (heatmap data from API)
│   └── insightsLoading
│
├── LINKS SIDECAR  (hyperlink extraction)
│   ├── linksLoaded          (sidecar fetch complete flag)
│   ├── visitedLinks         (Set of visited URLs)
│   └── sidecarExtracted     (toast-once flag after manual extract)
│
├── SEARCH
│   ├── searchHighlightQuery (active query string)
│   ├── searchHighlights     (word-position rectangles for current page)
│   ├── searchResultPages    (Set of pages with any match — fallback glow)
│   └── activeHighlightIdx   (which match is orange / active)
│
├── ANNOTATIONS  (10 state values)
│   ├── annotTool            (null | 'highlight' | 'comment' | 'rectangle' | 'arrow' | 'sticky_note' | 'draw')
│   ├── annotColor           (hex color for active tool)
│   ├── annotThickness       (stroke width)
│   ├── annotUndoStack       ([{annotId, page}, …])
│   ├── pageAnnotations      (loaded annotations for current page)
│   ├── commentDraft         ({x, y, coords, type} — pending text input)
│   ├── drawingState         ({startX, startY} — in-progress shape)
│   ├── threadView           ({rootAnnot, root, replies, loading})
│   ├── threadReplyText      (reply composer text)
│   └── threadReplySending   (send-in-flight flag)
│
└── BOOKMARKS
    └── bookmarks            (Set<page_number>)
```

### Refs (not state, but owned by ViewerScreen)
| Ref | Purpose |
|-----|---------|
| `pageCache` | Map(key → blobUrl) — 30-page LRU blob cache |
| `inflightRef` | Map(key → Promise) — request dedup |
| `imgSrcRef` | Mirror of imgSrc for stale-closure access in loadPage |
| `pageImgRef` | `<img>` element — naturalWidth/Height |
| `pageContainerRef` | `.viewer-page` div — passed to RectMagnifier |
| `annotCacheRef` | Map(page → annotation[]) — local annotation cache |
| `pageLinksRef` | Map(page → link[]) — hyperlink sidecar data |
| `autoExtractAttempted` | Fire-once flag for sidecar auto-extract |
| `wordPositionsRef` | Map(page → word[]) — search word positions |
| `wordPositionsFetched` | Once-fetch flag |
| `touchRef` | Touch gesture state (x, y, pinchDist) |
| `reinitRef` | Session auto-revalidation callback (set after hooks) |

---

## 3. Component Dependency Diagram

```
ViewerScreen (1 344 lines today → target ~200 lines)
│
├── [context] ViewerContext.Provider ───────────────────────────┐
│                                                               │
├── components/viewer/Toolbar                                   │
│   └── ViewerToolbar (existing, unchanged)                     │
│       └── AnnotToolbar (existing, unchanged)                  │
│                                                               │
├── SearchPanel (existing, just moved to components/viewer/)    │
│                                                               │
├── InsightsModal (existing, just moved)                        │
│                                                               │
├── [flex row]                                                  │
│   ├── components/viewer/Sidebar                               │
│   │   ├── TocSidebar (existing, unchanged)                    │
│   │   └── PageThumb × N (existing, unchanged)                 │
│   │                                                           │
│   ├── components/viewer/DocumentCanvas                        │
│   │   ├── reading progress bar (inline JSX)                   │
│   │   ├── page image layers (primary + crossfade)             │
│   │   ├── text document renderer                              │
│   │   ├── search highlights overlay                           │
│   │   ├── link overlay anchors                                │
│   │   ├── components/viewer/AnnotationPanel                   │
│   │   │   ├── AnnotationLayer (existing, unchanged)           │
│   │   │   └── CommentPopup (existing, unchanged)              │
│   │   └── two-page spread wrapper                             │
│   │                                                           │
│   └── ViewerInfoPanel (existing, unchanged)                   │
│                                                               │
├── LaserPointer (existing, unchanged)                          │
├── RectMagnifier (existing, unchanged)                         │
├── LinksPanel (existing, unchanged)                            │
│                                                               │
└── components/viewer/CommentsPanel                             │
    └── Modal (existing, unchanged)                             │
                                                               │
ViewerContext (shared, read by Toolbar, Canvas, Sidebar, etc.) ─┘
```

---

## 4. All useState Hooks Grouped by Responsibility

### Group A — Session & Auth (6 hooks)
```
session                  null → { link_token, session_id, permissions, page_count, doc_type, … }
initializing             true → false once doValidate/gate resolves
gateInfo                 null → { status, requires_password, requires_email }
gateError                null → string error message
pendingToken             null → link token string (before session)
blurred                  false → true when window loses focus
```

### Group B — Navigation (4 hooks)
```
page                     1 → integer, current page number
pageInputStr             '' → string while user types in page jump box
twoPageMode              false → true for two-page spread
isFullscreen             false → true when fullscreen API active
```

### Group C — Layout & Zoom (3 hooks)
```
layoutMode               'auto' → LAYOUT enum value
customZoom               100 → integer 10–400
rotation                 0 → 0 | 90 | 180 | 270
```

### Group D — Page Image Loading (9 hooks)
```
imgSrc                   '' → blob URL for current page
imgLoading               false → true while fetch in flight
pageError                null → error string
prevImgSrc               '' → blob URL — crossfade background layer
imgReady                 false → true when <img> fires onLoad
pageAspectRatio          null → '1920/1080' string from naturalWidth/naturalHeight
imgSrc2                  '' → blob URL for second page (two-page mode)
imgLoading2              false → true while second page fetch in flight
page2Error               null → error string for second page
```

### Group E — Text Document Loading (3 hooks)
```
textContent              '' → loaded text chunk
textLoading              false → true while fetch in flight
textError                null → error string
```

### Group F — Panel Visibility (8 hooks)
```
showSearch               false → true
showToc                  false → true
showInfo                 false → true
showPageList             window.innerWidth > 640 → boolean
showLaser                false → true
showMagnifier            false → true
showInsights             false → true
showLinks                false → true
```

### Group G — Insights (2 hooks)
```
insightsData             null → heatmap API response
insightsLoading          false → true while fetch in flight
```

### Group H — Links Sidecar (3 hooks)
```
linksLoaded              false → true after sidecar fetch completes
visitedLinks             Set() → Set of visited URL strings
sidecarExtracted         false → true after manual extract (used as toast-once flag)
```

### Group I — Search (4 hooks)
```
searchHighlightQuery     '' → active query string
searchHighlights         [] → [{x, y, w, h, t}, …] word positions on current page
searchResultPages        Set() → Set of page numbers with any match
activeHighlightIdx       0 → index into searchHighlights
```

### Group J — Annotations (10 hooks)
```
annotTool                null → 'highlight' | 'comment' | 'rectangle' | 'arrow' | 'sticky_note' | 'draw'
annotColor               '#FFE066' → hex color string
annotThickness           2 → integer stroke width
annotUndoStack           [] → [{annotId, page}, …]
pageAnnotations          [] → annotation objects for current page
commentDraft             null → {x, y, coords, type}
drawingState             null → {startX, startY} normalized 0–1
threadView               null → {rootAnnot, root, replies, loading}
threadReplyText          '' → string reply composer text
threadReplySending       false → true while POST in flight
```

### Group K — Bookmarks (1 hook)
```
bookmarks                Set() → Set<integer> page numbers
```

---

## 5. Reusable Custom Hooks

Seven hooks should be extracted into `frontend/src/hooks/`:

### `useViewerSession(docId, publicToken)`
**Owns**: Group A (session, initializing, gateInfo, gateError, pendingToken, blurred)  
**Owns refs**: `reinitRef`  
**Owns effects**: `doValidate`, auto-create link + gate probe, security event listeners (keyboard/mouse/print), tab visibility blur, `reinitRef` assignment  
**Returns**: `{ session, initializing, gateInfo, gateError, pendingToken, blurred, doValidate }`

### `usePageLoader(session, page, isTwoPage, isTextDoc, PAGE_COUNT)`
**Owns**: Group D (imgSrc, imgLoading, pageError, prevImgSrc, imgReady, imgSrc2, imgLoading2, page2Error, pageAspectRatio)  
**Owns refs**: `pageCache`, `inflightRef`, `imgSrcRef`, `pageImgRef`, `pageContainerRef`  
**Owns effects**: page load effect, prefetch effect, two-page load effect, eager page-2 prefetch, imgSrcRef sync  
**Returns**: `{ imgSrc, setImgReady, imgLoading, pageError, prevImgSrc, imgReady, imgSrc2, imgLoading2, page2Error, pageImgRef, pageContainerRef }`  
**Note**: `reinitRef` must be passed in (set by `useViewerSession`).

### `useTextLoader(session, page, isTextDoc)`
**Owns**: Group E (textContent, textLoading, textError)  
**Returns**: `{ textContent, textLoading, textError }`

### `useViewerLayout()`
**Owns**: Groups B + C (navigation + layout/zoom)  
**Owns refs**: `touchRef`  
**Owns effects**: keyboard arrow / Ctrl+F, pinch-zoom wheel block, fullscreen change, state persistence (read/write sessionStorage)  
**Returns**: `{ page, setPage, pageInputStr, setPageInputStr, layoutMode, customZoom, rotation, twoPageMode, isFullscreen, pageStep, PAGE_COUNT_derived, goNext, goPrev, _setLayout, _zoomBy, _zoomTo, toggleFullscreen, setTwoPageMode, setRotation }`

### `useAnnotations(session, page, isTextDoc)`
**Owns**: Group J + Group K (annotations + bookmarks)  
**Owns refs**: `annotCacheRef`  
**Owns effects**: lazy-load annotations, load bookmarks once  
**Returns**: all annotation and bookmark state + setters + `annotCacheRef`

### `useSearchHighlights(session, page, searchHighlightQuery)`
**Owns**: Group I (search highlights)  
**Owns refs**: `wordPositionsRef`, `wordPositionsFetched`  
**Returns**: `{ searchHighlights, searchResultPages, activeHighlightIdx, setActiveHighlightIdx }`

### `useLinksSidecar(session, docId, page, isTextDoc)`
**Owns**: Group H (linksLoaded, visitedLinks, sidecarExtracted)  
**Owns refs**: `pageLinksRef`, `autoExtractAttempted`  
**Returns**: `{ pageLinksRef, linksLoaded, setLinksLoaded, visitedLinks, setVisitedLinks, sidecarExtracted, setSidecarExtracted }`

---

## 6. Context Provider

A `ViewerContext` should be introduced to eliminate prop drilling:

```jsx
// Values read by 3+ components:
const ViewerContext = createContext(null);

// In ViewerScreen return:
<ViewerContext.Provider value={{
  // Session
  session,
  permissions: session?.permissions || {},
  // Navigation  
  page, setPage, PAGE_COUNT, goNext, goPrev,
  // Design tokens (currently shared via module scope — must be explicit in separate files)
  C, mono,
}}>
```

**What moves to context** (currently prop-drilled through ViewerToolbar at 27 props):  
`session`, `page`, `PAGE_COUNT`, `C`, `mono` — these are read by virtually every child.

**What stays as explicit props** (event handlers, component-specific config):  
All `on*` callbacks and boolean state values that are specific to one consumer.

---

## 7. Target Component API

### `components/viewer/Toolbar`
```jsx
// Props received after refactor:
<Toolbar
  doc={doc}
  // Panel toggles — still explicit props
  showSearch={showSearch} setShowSearch={setShowSearch}
  showToc={showToc} setShowToc={setShowToc}
  showInfo={showInfo} setShowInfo={setShowInfo}
  showPageList={showPageList} setShowPageList={setShowPageList}
  showLaser={showLaser} setShowLaser={setShowLaser}
  showMagnifier={showMagnifier} setShowMagnifier={setShowMagnifier}
  showInsights={showInsights} setShowInsights={setShowInsights}
  showLinks={showLinks} setShowLinks={setShowLinks}
  linksCount={linksCount}
  // Annotation toolbar props (can move to AnnotationContext)
  annotTool={annotTool} ... 
  // Inline callbacks (these 50 lines of JSX in ViewerScreen return move here)
  onAnnotUndo={...} onToggleBookmark={...} onDownload={...} onPrint={...}
/>
// Reads from ViewerContext: session, page, PAGE_COUNT, C, mono, layoutMode, etc.
```

### `components/viewer/Sidebar`
```jsx
<Sidebar
  showToc={showToc} onCloseToc={() => setShowToc(false)}
  showPageList={showPageList}
/>
// Reads from ViewerContext: session, page, setPage, PAGE_COUNT
// Internally renders TocSidebar + PageThumb list
```

### `components/viewer/DocumentCanvas`
```jsx
<DocumentCanvas
  layoutMode={layoutMode} customZoom={customZoom} rotation={rotation}
  isTwoPage={isTwoPage}
  imgSrc={imgSrc} imgSrc2={imgSrc2} prevImgSrc={prevImgSrc}
  imgLoading={imgLoading} imgLoading2={imgLoading2}
  imgReady={imgReady} setImgReady={setImgReady}
  pageError={pageError} page2Error={page2Error}
  pageAspectRatio={pageAspectRatio}
  searchHighlights={searchHighlights}
  searchHighlightQuery={searchHighlightQuery}
  searchResultPages={searchResultPages}
  activeHighlightIdx={activeHighlightIdx}
  pageLinksRef={pageLinksRef}
  linksLoaded={linksLoaded}
  blurred={blurred}
  goNext={goNext} goPrev={goPrev}
  // Annotation props passed through to AnnotationPanel
  annotTool={annotTool} ... 
  pageAnnotations={pageAnnotations}
  commentDraft={commentDraft}
  pageImgRef={pageImgRef}
  pageContainerRef={pageContainerRef}
/>
// Reads from ViewerContext: session, page, C, mono
```

### `components/viewer/AnnotationPanel`
```jsx
// Wraps AnnotationLayer + CommentPopup
<AnnotationPanel
  pageAnnotations={pageAnnotations}
  setPageAnnotations={setPageAnnotations}
  annotTool={annotTool}
  annotColor={annotColor}
  annotThickness={annotThickness}
  commentDraft={commentDraft}
  setCommentDraft={setCommentDraft}
  annotCacheRef={annotCacheRef}
  annotUndoStack={annotUndoStack}
  setAnnotUndoStack={setAnnotUndoStack}
  onOpenThread={...}
/>
// Reads from ViewerContext: session, page
```

### `components/viewer/SearchPanel`
```jsx
// Already self-contained. Move file, update import.
// No API change needed.
<SearchPanel
  session={session}
  onClose={...}
  onNavigate={p => setPage(p)}
  onQueryChange={q => setSearchHighlightQuery(q)}
  onActiveChange={idx => setActiveHighlightIdx(idx)}
  onResultsChange={results => setSearchResultPages(...)}
/>
```

### `components/viewer/CommentsPanel`
```jsx
// Wraps the thread Modal at bottom of ViewerScreen
<CommentsPanel
  threadView={threadView}
  setThreadView={setThreadView}
  threadReplyText={threadReplyText}
  setThreadReplyText={setThreadReplyText}
  threadReplySending={threadReplySending}
  setThreadReplySending={setThreadReplySending}
/>
// Reads from ViewerContext: session, page, C, mono
```

---

## 8. Estimated Line Reduction

### ViewerScreen after refactor
```
Current:   1 344 lines (1238–2581)
Extracted:
  useViewerSession         −120 lines
  usePageLoader            −160 lines
  useTextLoader            −40 lines
  useViewerLayout          −100 lines
  useAnnotations           −80 lines
  useSearchHighlights      −55 lines
  useLinksSidecar          −50 lines
  DocumentCanvas JSX       −350 lines
  CommentsPanel JSX        −115 lines
  Toolbar callbacks inline −50 lines
  Sidebar JSX              −35 lines
  Total extracted:         −1 155 lines

Remaining in ViewerScreen:   ~190 lines
```

**ViewerScreen becomes:**
```jsx
function ViewerScreen({ doc, publicToken, onSelectDoc }) {
  const toast = useToast();
  const { session, initializing, gateInfo, gateError, pendingToken, blurred, doValidate }
    = useViewerSession(doc?.id, publicToken, toast);
  const { layoutMode, customZoom, rotation, twoPageMode, isFullscreen, page, setPage, ... }
    = useViewerLayout(session);
  const { imgSrc, imgLoading, pageError, ... }
    = usePageLoader(session, page, twoPageMode, isTextDoc, PAGE_COUNT, reinitRef);
  const { textContent, textLoading, textError }
    = useTextLoader(session, page, isTextDoc);
  const { annotTool, ... }
    = useAnnotations(session, page, isTextDoc);
  const { searchHighlights, ... }
    = useSearchHighlights(session, page, searchHighlightQuery);
  const { pageLinksRef, linksLoaded, visitedLinks, ... }
    = useLinksSidecar(session, doc?.id, page, isTextDoc);

  // Panel visibility — stays here (simple, no effects)
  const [showSearch, setShowSearch] = useState(false);
  // ... 7 more showX booleans

  // All hooks have run — safe to conditionally return
  if (gateInfo && !session) return <AccessGate ... />;
  if (!docId && !publicToken && !initializing) return <DocumentPicker ... />;

  return (
    <ViewerContext.Provider value={{ session, page, setPage, PAGE_COUNT, C, mono }}>
      <div data-testid="viewer-screen" ...>
        <Toolbar doc={doc} showSearch={showSearch} ... />
        {showSearch && <SearchPanel session={session} ... />}
        {showInsights && <InsightsModal ... />}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          <Sidebar showToc={showToc} showPageList={showPageList} />
          <DocumentCanvas ... />
          {showInfo && <ViewerInfoPanel ... />}
        </div>
        <LaserPointer active={showLaser} />
        <RectMagnifier active={showMagnifier} ... />
        {showLinks && <LinksPanel ... />}
        <CommentsPanel threadView={threadView} ... />
      </div>
    </ViewerContext.Provider>
  );
}
```

### Total new files created
```
frontend/src/
├── constants/
│   └── viewer.js           ~20 lines  (LAYOUT, ZOOM_*, _saveLayoutPref, _loadLayoutPref)
├── hooks/
│   ├── useViewerSession.js  ~130 lines
│   ├── usePageLoader.js     ~170 lines
│   ├── useTextLoader.js     ~45 lines
│   ├── useViewerLayout.js   ~110 lines
│   ├── useAnnotations.js    ~90 lines
│   ├── useSearchHighlights.js ~60 lines
│   └── useLinksSidecar.js   ~55 lines
└── components/viewer/
    ├── Toolbar.jsx          ~80 lines  (thin wrapper, moves callbacks out of ViewerScreen)
    ├── Sidebar.jsx          ~50 lines
    ├── DocumentCanvas.jsx   ~380 lines
    ├── AnnotationPanel.jsx  ~60 lines
    ├── SearchPanel.jsx      ~140 lines (moved from app.jsx)
    └── CommentsPanel.jsx    ~130 lines
```

**Net result**: 1 344-line ViewerScreen → ~190 lines. All business logic moves to hooks. All rendering logic moves to components. `app.jsx` itself reduces from 6 047 to ~5 100 lines (existing sub-components remain in app.jsx until Sprint 3 Part 2).

---

## 9. Risks and Mitigations

### Risk 1 — Module scope breakage (HIGH)
**Problem**: `C`, `mono`, `_errMsg`, `LAYOUT`, `ZOOM_*` constants are in module scope (top of app.jsx). All functions close over them for free. When code moves to separate files, these become undefined.  
**Mitigation**: Phase 1 creates `constants/viewer.js` and `utils/helpers.js`. All extracted files import explicitly. Do not extract any file before its dependencies exist.

### Risk 2 — `reinitRef` threading (MEDIUM)
**Problem**: `loadPage` uses `reinitRef.current` via closure (set *after* hooks, line 1509). If `usePageLoader` is a separate hook, it can't receive `reinitRef` before it's assigned.  
**Mitigation**: `reinitRef` is created by `useViewerSession`, returned as part of its return value, and passed to `usePageLoader`. The `reinitRef.current = ...` assignment remains in ViewerScreen (after both hooks run).

### Risk 3 — `annotCacheRef` shared between effects and handlers (MEDIUM)
**Problem**: The ref is written by both the annotation-load effect (in `useAnnotations`) and the `onDraw`/`onDelete` handlers (in `AnnotationPanel`). If they're in different modules, the ref must be the same object.  
**Mitigation**: `annotCacheRef` is created in `useAnnotations`, returned, and passed as a prop to `AnnotationPanel`. Both modules operate on the same Map instance.

### Risk 4 — `pageLinksRef` + `wordPositionsRef` reset in info panel (MEDIUM)
**Problem**: `ViewerInfoPanel.onSidecarExtract` callback resets `pageLinksRef.current = {}`, `wordPositionsRef.current = {}`, and clears `wordPositionsFetched.current`. These refs live in different hooks (`useLinksSidecar` and `useSearchHighlights`).  
**Mitigation**: The info panel's `onSidecarExtract` callback is constructed in ViewerScreen (which has access to all hooks' returned refs) and passed down as a prop. No cross-hook coupling needed.

### Risk 5 — React hook count / order (HIGH)
**Problem**: React requires the same number of hooks in the same order every render. Any reorganization that changes hook count breaks the component.  
**Mitigation**: Extracting hooks into custom hook functions (not conditionally) preserves hook order inside ViewerScreen. The existing rule is followed: the comment "All hooks have run — safe to conditionally return now" remains after all custom hook calls.

### Risk 6 — esbuild multi-file build (LOW)
**Problem**: Current build command is single-file entry (`src/app.jsx`). If new files use ES module `import`/`export`, esbuild must bundle them. Since esbuild handles this natively, the risk is low.  
**Mitigation**: Use standard ES module syntax. Update the esbuild command to specify `--bundle` flag if not already implied (esbuild bundles imports by default).

### Risk 7 — `window.SecureDocAPI` global access (LOW)
**Problem**: All API calls go through `window.SecureDocAPI`, accessible from any module.  
**Mitigation**: No change needed. Continue calling `window.SecureDocAPI.*` directly.

### Risk 8 — No frontend tests exist (LOW risk to detect regressions)
**Problem**: There are zero frontend test files. Any regression is caught only by manual testing.  
**Mitigation**: Manual smoke-test after each phase using the running dev server. The test plan section below specifies what to verify. Do not skip phases.

---

## 10. Migration Strategy

### Phase 1 — Extract constants and pure utilities (LOW RISK)
No component or hook changes. App behavior identical.

**Actions:**
1. Create `frontend/src/constants/viewer.js`:
   - `LAYOUT`, `ZOOM_MIN`, `ZOOM_MAX`, `ZOOM_STEP`, `ZOOM_PRESETS`
   - `_saveLayoutPref(mode, zoom)`, `_loadLayoutPref()`
2. Create `frontend/src/utils/viewer.js`:
   - `_errMsg(e, fallback)` (copy from app.jsx line 50)
3. In `app.jsx`: add imports at top, remove inline definitions.
4. Verify: `npm run build` succeeds.

**Risk**: Low. Pure utility extraction with no side effects.

---

### Phase 2 — Extract custom hooks (MEDIUM RISK)
One hook at a time. Build + manual test after each.

**Order** (least dependencies first):
1. `useTextLoader` — completely isolated, simple
2. `useLinksSidecar` — isolated; only uses `session`, `docId`, `isTextDoc`
3. `useSearchHighlights` — isolated; reads `session`, `page`, `searchHighlightQuery`
4. `useAnnotations` — reads `session`, `page`, `isTextDoc`
5. `useViewerLayout` — reads `session?.session_id` for persistence only
6. `usePageLoader` — most complex; needs `reinitRef` passed in
7. `useViewerSession` — last; most entangled (doValidate, gateInfo, security listeners)

**Test after each**: Navigate pages, verify images load, verify annotate/bookmark/search function.

---

### Phase 3 — Introduce ViewerContext (LOW RISK)
Add context provider to ViewerScreen. All existing prop passing remains identical. Consumers are opt-in.

**Actions:**
1. Add `const ViewerContext = createContext(null)` to `app.jsx`.
2. Wrap ViewerScreen return in `<ViewerContext.Provider value={...}>`.
3. Verify: no behavior change.

---

### Phase 4 — Extract components (HIGH RISK — do one at a time)
**Order** (lowest coupling first):

1. **`CommentsPanel`** — most isolated (threadView, threadReplyText, threadReplySending only). Reads `C`, `mono`, `session` from context.
2. **`Sidebar`** — wraps TocSidebar + PageThumb list. Reads `session`, `page`, `setPage`, `PAGE_COUNT` from context.
3. **`AnnotationPanel`** — wraps AnnotationLayer + CommentPopup. Reads `session`, `page` from context.
4. **`DocumentCanvas`** — largest extraction (~350 lines of JSX). Contains most overlays. Keep as one component; sub-split is optional.
5. **`Toolbar`** — thin wrapper over ViewerToolbar that pulls callbacks inline (onAnnotUndo, onToggleBookmark, onDownload, onPrint) out of ViewerScreen's return JSX.

**Test after each component**: Full viewer golden path — open, navigate, annotate, search, bookmark, download, fullscreen.

---

### Phase 5 — Verify and commit (LOW RISK)
1. `npm run build` — must pass.
2. Smoke test checklist (see Section 11).
3. Update `EXECUTION_LOG.md`.
4. Commit with message `refactor(sprint2/fe): decompose ViewerScreen into hooks and components`.

---

## 11. Test Plan (Manual — No Automated Tests Exist)

Since there are zero frontend tests, manual verification is required after each phase.

### Golden path
- [ ] Open authenticated viewer (with doc) — page 1 loads
- [ ] Open public token viewer — gate prompt if password required
- [ ] Keyboard arrow navigation (←/→)
- [ ] Toolbar page number input jump
- [ ] Zoom in/out, fit-width, fit-height, actual-size
- [ ] Page rotation (90°, 180°, 270°, back to 0°)
- [ ] Two-page spread toggle
- [ ] Fullscreen toggle
- [ ] Search (Ctrl+F), navigate matches, close
- [ ] TOC sidebar open/close, click entry
- [ ] Page thumbnail strip toggle
- [ ] Info panel open/close
- [ ] Links panel open/close, visit links
- [ ] Laser pointer enable/disable
- [ ] Magnifier enable/disable
- [ ] Insights modal open/close
- [ ] Annotate: highlight, draw, rectangle, arrow, comment, sticky note
- [ ] Annotation undo
- [ ] Bookmark page, unbookmark
- [ ] Comment thread open, reply, send
- [ ] Download (if permitted)
- [ ] Print (if permitted)
- [ ] Tab blur — page blurs; tab focus — page unblurs
- [ ] Right-click blocked in secure viewer
- [ ] Copy/print keyboard shortcuts blocked

### Edge cases
- [ ] Open viewer with no doc selected — DocumentPicker shown
- [ ] Expired/revoked link — terminal gate shown
- [ ] Password-protected link — password gate shown
- [ ] Document still processing — status message shown, no page load
- [ ] Text document (txt/md) — text renderer shown instead of image
- [ ] Sidecar auto-extract — links load on next navigation

---

## 12. Constraints Checklist

| Constraint | How addressed |
|------------|--------------|
| DO NOT ADD NEW USER-VISIBLE FEATURES | Architecture only — no new UI |
| DO NOT MODIFY UX | JSX output identical; only component boundaries change |
| DO NOT ADD NEW BUTTONS | No buttons added |
| DO NOT ADD NEW PAGES | No routes/screens added |
| DO NOT ADD NEW DATABASE TABLES | Frontend only |
| DO NOT CHANGE API CONTRACTS | All `window.SecureDocAPI.*` calls unchanged |
| ZERO FEATURE CHANGES | Refactor only |
| ZERO API CHANGES | No backend calls added or changed |
| ZERO DATABASE CHANGES | Frontend only |
| ZERO SECURITY REGRESSIONS | Security event listeners move to `useViewerSession`; same listeners, same behavior |

---

## 13. Implementation Order Summary

```
Phase 1: Extract constants/utils    → 1 day  → Low risk
Phase 2: Extract 7 custom hooks     → 3 days → Medium risk
Phase 3: Add ViewerContext          → 0.5 day → Low risk
Phase 4: Extract 6 components       → 4 days → High risk (per-component)
Phase 5: Verify, document, commit   → 0.5 day → Low risk

Total estimated: ~9 engineer-days
ViewerScreen: 1 344 lines → ~190 lines (~86% reduction)
app.jsx: 6 047 lines → ~5 100 lines (remaining sub-components stay for now)
```
