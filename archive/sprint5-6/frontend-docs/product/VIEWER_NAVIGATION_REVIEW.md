# Viewer Navigation Review — Sprint 4.8 Phase 2

**Method:** Source code trace of `ViewerScreen.jsx`, `AppShell.jsx`, `ViewerToolbar.jsx`, `atoms.jsx` (Header, Sidebar), and `useViewerLayout.js` hook surface.  
**Recommendation:** Option C — Remember current document + explicit "Back to Documents" button.

---

## Current State: Exact Behavior

### How activeDoc persists

`AppShell.jsx:29`: `const [activeDoc, setActiveDoc] = useState(null);`  
`AppShell.jsx:35`: `const handleViewDoc = doc => { setActiveDoc(doc); setScreen('viewer'); };`

Once a user clicks "View" on a document row, `activeDoc` is set. It persists across ALL screen navigations — if the user goes to Analytics, then back to Viewer, they see the same document. The state is never cleared except by clicking "View" on a different document.

### The navigation dead-end

`ViewerScreen.jsx:152–161`: If `!docId && !publicToken && !initializing`, a `DocumentPicker` is shown inline. This is only reached if `activeDoc` is null.

Once `activeDoc` is set (which happens after the user views any document), the Viewer goes directly to that document every time. **There is no visible button to switch documents or go back to the list.**

The only escape paths from the Viewer, once a document is loaded:
1. Click **Upload** in the sidebar — navigates to UploadScreen. The user can click "View" on a different doc.
2. Click **Viewer** in the sidebar — reloads the same document (no change).
3. No button within the Viewer screen itself to navigate to the document list.

### State carried by the Viewer

The Viewer maintains significant state via hooks. Resetting `activeDoc` to null would destroy this state:

| Hook | State that would be lost |
|------|--------------------------|
| `useViewerLayout` | Zoom level, layout mode (single/two-page), rotation, custom zoom |
| `useAnnotations` | Unsaved annotation drafts, undo stack (`annotUndoStack`), bookmark state |
| `useSearchHighlights` | Active search query, highlight positions, word positions cache |
| `useLinksSidecar` | Sidecar extraction state, visited links |
| `usePageLoader` | Page image cache (in-memory) |
| `useViewerSession` | Session token, gate state |

Source: `ViewerScreen.jsx:47–130`

---

## Option Evaluation

### Option A — Always reset Viewer

**Behavior:** Whenever the user navigates away from Viewer and returns, `activeDoc` is cleared. Viewer shows DocumentPicker.

**Evidence against:**
- Destroys all in-flight state (zoom, annotations, search) that `useViewerLayout`, `useAnnotations`, etc. maintain.
- Users reading a long document mid-session lose their position.
- Annotation drafts are lost.
- Multiple round-trips are needed for users who compare documents or switch between Viewer and Analytics.
- No standard product does this — browsers remember scroll position, PDF readers remember the page.

**Verdict:** Rejected.

---

### Option B — Remember current document (status quo)

**Behavior:** `activeDoc` persists. Returning to Viewer shows the same document.

**Current behavior.** The problem:
- Users with one document never hit the dead-end (no need to switch).
- Users with 2+ documents must navigate to Upload, find the document, hover over it, and click "View" — a 3-step detour just to switch documents.
- The Viewer looks like a terminal screen with no escape. First-time users will not know they can switch documents.

**Verdict:** Rejected as-is (but "remember" is correct — just needs an escape hatch).

---

### Option C — Remember current document + explicit "Back to Documents"

**Behavior:** `activeDoc` persists across navigation (preserves all hook state). A visible "← Documents" or "⊕ Documents" button is added to the ViewerToolbar.

**Evidence for:**
1. The ViewerToolbar already has a slot for document-level actions — it renders `doc` and `docName` props and shows page controls, zoom, and annotation tools. A breadcrumb-style "← Documents" button fits the existing pattern.
2. No state is lost — `activeDoc` remains set. Pressing "Back" is equivalent to clicking "Upload" in the sidebar, but discoverable within the viewer itself.
3. The `DocumentPicker` already exists (`src/components/DocumentPicker.jsx`) and renders an inline document selector. It is already used as the "no document selected" fallback in ViewerScreen.jsx:153–161. Adding a "switch document" mode using the same component requires no new backend work.

**Implementation surface:** ViewerToolbar receives `onSelectDoc` already as a prop chain: `AppShell.jsx:108` → `ViewerScreen.jsx:29` → `ViewerToolbar` (currently unused at toolbar level for navigation). Adding a button that calls `onSelectDoc(null)` (to show DocumentPicker) or navigates via `AppShell.setScreen('upload')` is a 1-line change in the toolbar.

**Risk:** None. This is additive. No state is removed. Existing Viewer behavior is unchanged.

---

## Recommendation: Option C

### Exact change

**In `ViewerToolbar.jsx`:** Add a "← Docs" breadcrumb/button at the left edge of the toolbar, before the document name display. Wire it to reset `activeDoc` to null or navigate to the upload screen.

**In `AppShell.jsx`:** Pass `onBack={() => setScreen('upload')}` (or `setActiveDoc(null)`) down through the Viewer chain.

**Alternative:** Add it to `Header` in `atoms.jsx` for all screens via a `onBack` prop — the `viewer` screen is the only screen where "back to list" is needed, so a viewer-specific button is preferable.

### Supporting evidence — what other products do

Every document viewer (Google Docs, Notion, Figma, DocSend) has a visible back arrow or breadcrumb that returns the user to the document list. SecureDoc's Viewer has none.

---

## Current Navigation Map (authenticated mode)

```
Upload Screen
   [click "View"]     → Viewer Screen (activeDoc set)
   [hover → "Access"] → Access Screen (activeDoc set)
   [hover → "Share"]  → QuickShareModal

Viewer Screen
   [toolbar: page nav, zoom, annotations, search, TOC, laser, magnifier]
   [NO back button]
   [NO document switcher]
   → Only exit: click sidebar item

Access Screen
   Policy | Share Link | Log | Feedback | Annotations tabs
   [NO link back to Viewer for this doc]
```

With Option C, the Viewer becomes:

```
Viewer Screen
   [← Docs] [docName] | [page nav] [zoom] [annotations] [search] ...
              ↓ click ← Docs
   Upload Screen (activeDoc preserved in memory; DocumentPicker shown if user returns to Viewer tab)
```

---

*Generated: Sprint 4.8 Phase 2 — no implementation performed.*
