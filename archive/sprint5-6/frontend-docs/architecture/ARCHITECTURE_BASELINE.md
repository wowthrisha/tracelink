# Architecture Baseline
Sprint 4.0 — Phase 6
Date: 2026-06-18

Reference point for all future Sprint 4+ reviews. Captures the full component/hook/context/screen graph as of post-Sprint 3.5 state.

---

## Component Graph

```
app.jsx (root)
├── ToastProvider (contexts/toast.jsx)
│   └── App
│       ├── Sidebar (atoms.jsx)
│       │   └── NavItem (atoms.jsx)
│       ├── [SCREEN 1] UploadScreen
│       │   ├── Header (atoms.jsx)
│       │   ├── Card (atoms.jsx)
│       │   ├── Modal (atoms.jsx)
│       │   ├── StatCard (upload/StatCard.jsx)
│       │   ├── DocRow (upload/DocRow.jsx)
│       │   │   ├── StatusDot (atoms.jsx)
│       │   │   ├── RiskBadge (atoms.jsx)
│       │   │   └── Btn (atoms.jsx)
│       │   ├── UploadDropZone (upload/UploadDropZone.jsx)
│       │   ├── UploadMetadataPanel (upload/UploadMetadataPanel.jsx)
│       │   │   ├── SectionLabel (atoms.jsx)
│       │   │   └── Btn (atoms.jsx)
│       │   └── UploadProgressPanel (upload/UploadProgressPanel.jsx)
│       │       ├── StatusDot (atoms.jsx)
│       │       ├── Btn (atoms.jsx)
│       │       └── Card (atoms.jsx)
│       ├── [SCREEN 2] ViewerScreen
│       │   ├── ViewerErrorBoundary (components/ViewerErrorBoundary.jsx)
│       │   ├── ViewerToolbar (components/ViewerToolbar.jsx) [C/mono as props]
│       │   ├── TocSidebar (components/TocSidebar.jsx)
│       │   ├── SearchPanel (components/SearchPanel.jsx)
│       │   ├── LinksPanel (components/LinksPanel.jsx) [C/mono as props]
│       │   ├── InsightsModal (components/InsightsModal.jsx) [C/mono as props]
│       │   ├── LaserPointer (components/LaserPointer.jsx)
│       │   ├── RectMagnifier (components/RectMagnifier.jsx)
│       │   ├── PageThumb (components/PageThumb.jsx) [sidebar thumbnails]
│       │   ├── ViewerInfoPanel (components/ViewerInfoPanel.jsx)
│       │   ├── AnnotationLayer (components/AnnotationLayer.jsx) [C/mono as props]
│       │   ├── CommentPopup (components/CommentPopup.jsx) [C as prop]
│       │   ├── AccessGate (components/AccessGate.jsx)
│       │   │   ├── GateMessage (components/GateMessage.jsx)
│       │   │   └── Btn (atoms.jsx)
│       │   └── DocumentPicker (components/DocumentPicker.jsx)
│       │       ├── SectionLabel (atoms.jsx)
│       │       └── StatusDot (atoms.jsx)
│       ├── [SCREEN 3] AccessScreen (inline in app.jsx)
│       │   ├── Header (atoms.jsx)
│       │   ├── Card, Modal, Btn, Toggle, Field, Chip, Divider (atoms.jsx)
│       │   ├── SectionLabel, StatusDot, RiskBadge (atoms.jsx)
│       │   ├── [inline] TabBtn
│       │   ├── [inline] PermRow
│       │   ├── [inline] AccessLog
│       │   └── DocumentPicker (components/DocumentPicker.jsx)
│       ├── [SCREEN 4] AnalyticsScreen (inline in app.jsx)
│       │   ├── Header (atoms.jsx)
│       │   ├── Card, Btn, Chip (atoms.jsx)
│       │   ├── [inline] KpiCard
│       │   ├── [inline] RangeBtn
│       │   ├── [inline] SparkChart
│       │   ├── [inline] DonutChart
│       │   └── [inline] DocAnalyticsRow
│       ├── [SCREEN 5] StorageScreen (inline in app.jsx)
│       │   ├── Header (atoms.jsx)
│       │   └── Card, Btn, StatusDot (atoms.jsx)
│       ├── [SCREEN 6] LoginScreen (inline in app.jsx)
│       │   └── Btn, Field (atoms.jsx)
│       └── [SCREEN 7] BillingScreen (inline in app.jsx)
│           └── Card, Btn, Toggle (atoms.jsx)
```

---

## Hook Graph

All hooks are used exclusively in `ViewerScreen` (inside app.jsx).

```
ViewerScreen
├── useViewerSession(doc, publicToken, { onValidated })
│   ├── imports: _errMsg (utils/viewer.js)
│   └── imports: useToast (contexts/toast.jsx)
├── usePageLoader({ session, page, twoPageMode, isTextDoc, onAuth401 })
│   └── (no imports — React UMD only)
├── useTextLoader(session, page, isTextDoc)
│   └── imports: _errMsg (utils/viewer.js)
├── useSearchHighlights(session, page)
│   └── (no imports — React UMD only)
├── useAnnotations(session, page, isTextDoc)
│   └── (no imports — React UMD only)
├── useLinksSidecar(session, docId, isTextDoc, { onAutoExtractReset })
│   └── (no imports — React UMD only)
├── useViewerLayout(session, { onToggleSearch })
│   └── imports: LAYOUT, ZOOM_MIN, ZOOM_MAX, _saveLayoutPref, _loadLayoutPref (constants/viewer.js)
└── useToast()  [also used in: UploadScreen, AccessScreen, AnalyticsScreen, StorageScreen, LoginScreen, BillingScreen]
```

---

## Context Graph

```
contexts/toast.jsx
  ├── exports: ToastCtx (React context)
  ├── exports: useToast() → reads ToastCtx
  └── exports: ToastProvider → wraps App in app.jsx

Consumers of useToast():
  ├── hooks/useViewerSession.js
  ├── components/DocumentPicker.jsx
  └── app.jsx (ViewerScreen, UploadScreen, AccessScreen, AnalyticsScreen,
               StorageScreen, LoginScreen, BillingScreen)
```

---

## Screen Graph

| Screen | Location | LOC (est.) | State vars | API calls | Hooks |
|---|---|---|---|---|---|
| `UploadScreen` | app.jsx inline | ~380 | ~12 | upload, poll, groups CRUD, doc list | useToast |
| `ViewerScreen` | app.jsx inline | ~700 | ~8 direct + hook state | page, session, annotations, links, search, insights | 8 custom hooks + useToast |
| `AccessScreen` | app.jsx inline | ~700 | ~15 | permissions, groups, feedback, access log | useToast |
| `AnalyticsScreen` | app.jsx inline | ~500 | ~8 | analytics metrics, doc list | useToast |
| `StorageScreen` | app.jsx inline | ~160 | ~4 | storage usage, doc list | useToast |
| `LoginScreen` | app.jsx inline | ~235 | ~4 | login | useToast |
| `BillingScreen` | app.jsx inline | ~195 | ~5 | plan info, billing | useToast |
| `App` | app.jsx inline | ~100 | screen routing | — | — |

---

## Module Dependency Layers

```
Layer 0 — Leaves (no imports):
  constants/tokens.js
  constants/viewer.js
  utils/viewer.js

Layer 1 — Single-dependency:
  contexts/toast.jsx         ← tokens.js
  components/atoms.jsx       ← tokens.js
  components/GateMessage.jsx ← tokens.js
  components/LaserPointer.jsx (no imports)
  components/RectMagnifier.jsx (no imports)
  components/SearchPanel.jsx  (no imports)
  components/InsightsModal.jsx (no imports — props only)
  components/LinksPanel.jsx   (no imports — props only)
  components/AnnotationLayer.jsx (no imports — props only)
  components/CommentPopup.jsx (no imports — props only)
  components/ViewerToolbar.jsx (no imports — props only)
  hooks/useAnnotations.js    (no imports)
  hooks/useLinksSidecar.js   (no imports)
  hooks/usePageLoader.js     (no imports)
  hooks/useSearchHighlights.js (no imports)
  hooks/useTextLoader.js     ← utils/viewer.js
  hooks/useViewerLayout.js   ← constants/viewer.js

Layer 2 — Multi-dependency:
  components/AccessGate.jsx  ← tokens.js, atoms.jsx, GateMessage.jsx
  components/ViewerInfoPanel.jsx ← tokens.js, atoms.jsx
  components/TocSidebar.jsx  ← tokens.js
  components/PageThumb.jsx   ← tokens.js
  components/ViewerErrorBoundary.jsx ← tokens.js
  components/DocumentPicker.jsx ← tokens.js, atoms.jsx, toast.jsx
  components/upload/StatCard.jsx ← tokens.js, atoms.jsx
  components/upload/DocRow.jsx ← tokens.js, atoms.jsx
  components/upload/UploadDropZone.jsx ← tokens.js
  components/upload/UploadMetadataPanel.jsx ← tokens.js, atoms.jsx
  components/upload/UploadProgressPanel.jsx ← tokens.js, atoms.jsx
  hooks/useViewerSession.js  ← utils/viewer.js, toast.jsx

Layer 3 — Root:
  app.jsx ← all above
```

---

## Data Flow Summary

### Document Access Flow
```
User action → App (screen router) → ViewerScreen
  → useViewerSession (token resolution + gate probe)
  → AccessGate (gate UI if required) or ViewerToolbar + page rendering
  → usePageLoader (image fetch per page)
  → useTextLoader (text layer per page)
  → useAnnotations (annotation fetch per page)
  → useSearchHighlights (search result overlay)
  → useLinksSidecar (link extraction)
  → useViewerLayout (zoom/mode/scroll)
```

### Upload Flow
```
User action → UploadScreen
  → UploadDropZone (file selection)
  → simulate() in UploadScreen (API upload call)
  → polling loop (MAX_POLL_ATTEMPTS × 2s)
  → UploadProgressPanel (progress display)
  → UploadMetadataPanel (group/retention assignment)
```

### Admin Flow
```
User action → AccessScreen
  → Tab routing (permissions / groups / feedback / access log)
  → DocumentPicker (shared with ViewerScreen)
  → Permission/group API calls
  → AccessLog (inline sub-component)
```

---

## Remaining Inline Components (Targets for Sprint 4.1+)

| Component | Location | LOC | Sprint target |
|---|---|---|---|
| `buildFeedbackFilters` | app.jsx module-level | ~12 | Sprint 4.1 → `utils/feedback.js` |
| `TabBtn` | app.jsx / AccessScreen | ~15 | Sprint 4.1 → `components/access/TabBtn.jsx` |
| `PermRow` | app.jsx / AccessScreen | ~20 | Sprint 4.1 → `components/access/PermRow.jsx` |
| `AccessLog` | app.jsx / AccessScreen | ~60 | Sprint 4.1 (readiness review) |
| `KpiCard` | app.jsx / AnalyticsScreen | ~25 | Sprint 4.1 → `components/analytics/KpiCard.jsx` |
| `RangeBtn` | app.jsx / AnalyticsScreen | ~15 | Sprint 4.1 → `components/analytics/RangeBtn.jsx` |
| `SparkChart` | app.jsx / AnalyticsScreen | ~40 | Sprint 4.1 → `components/analytics/SparkChart.jsx` |
| `DonutChart` | app.jsx / AnalyticsScreen | ~40 | Sprint 4.1 → `components/analytics/DonutChart.jsx` |
| `DocAnalyticsRow` | app.jsx / AnalyticsScreen | ~30 | Sprint 4.1 → `components/analytics/DocAnalyticsRow.jsx` |
| `UploadScreen` | app.jsx | ~380 | Sprint 4.2 |
| `AccessScreen` | app.jsx | ~700 | Sprint 4.2 |
| `AnalyticsScreen` | app.jsx | ~500 | Sprint 4.2 |
| `StorageScreen` | app.jsx | ~160 | Sprint 4.2 |
| `LoginScreen` | app.jsx | ~235 | Sprint 4.2 |
| `BillingScreen` | app.jsx | ~195 | Sprint 4.2 |
| `ViewerScreen` | app.jsx | ~700 | Sprint 4.2 (last, highest risk) |
| `App` | app.jsx | ~100 | Sprint 4.2 |
