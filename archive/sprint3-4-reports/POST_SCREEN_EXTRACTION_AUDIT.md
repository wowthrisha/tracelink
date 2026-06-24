> **HISTORICAL ARCHIVE** — Sprint milestone record. Reflects state at time of writing. Not current state.

# Post-Screen Extraction Audit
Sprint 4.2C — UploadScreen + AccessScreen
Date: 2026-06-22

---

## Summary

Sprint 4.2C completes the extraction of all screens except ViewerScreen. app.jsx now contains only the DocumentViewer (ViewerScreen) and its bootstrap render call.

---

## Extraction Results

| Screen | File | LOC | Status |
|---|---|---|---|
| AppShell | `src/screens/AppShell.jsx` | ~115 | Extracted Sprint 4.2A |
| LoginScreen | `src/screens/LoginScreen.jsx` | ~190 | Extracted Sprint 4.2A |
| BillingScreen | `src/screens/BillingScreen.jsx` | ~155 | Extracted Sprint 4.2A |
| StorageScreen | `src/screens/StorageScreen.jsx` | ~155 | Extracted Sprint 4.2A |
| AnalyticsScreen | `src/screens/AnalyticsScreen.jsx` | ~280 | Extracted Sprint 4.2B |
| UploadScreen | `src/screens/UploadScreen.jsx` | ~278 | Extracted Sprint 4.2C |
| AccessScreen | `src/screens/AccessScreen.jsx` | ~530 | Extracted Sprint 4.2C |

---

## app.jsx State After Sprint 4.2C

| Metric | Before Sprint 4.2C | After Sprint 4.2C | Change |
|---|---|---|---|
| app.jsx LOC | 1,955 | 882 | −1,073 |
| Inline screens | 3 (UploadScreen, ViewerScreen, AccessScreen) | 1 (ViewerScreen only) | −2 |
| AppShell props | 3 (Upload, Viewer, Access) | 1 (Viewer only) | −2 |
| Source files | 48 | 50 (+2) | +2 |
| Bundle size | 197.9 kb | 198.0 kb | +0.1 kb |

---

## Verification Checklist

### UploadScreen
- [x] UploadScreen.jsx created — 18 state vars, fileRef, pollRef, all API calls
- [x] pollRef cleanup effect migrated (`useEffect(() => () => clearInterval(pollRef.current), [])`)
- [x] fileRef wired to both UploadDropZone prop AND Header button onClick
- [x] _detectFileType and _isDocType promoted to module-level (no state closure)
- [x] MAX_POLL_ATTEMPTS promoted to module-level const
- [x] AppShell.jsx updated: added `import { UploadScreen }`, removed from props signature
- [x] app.jsx render call updated: removed `UploadScreen={UploadScreen}` prop
- [x] 5 upload sub-component imports removed from app.jsx (StatCard, DocRow, UploadDropZone, UploadMetadataPanel, UploadProgressPanel)
- [x] Build: 198.0 kb ✅

### AccessScreen
- [x] AccessScreen.jsx created — 35 state vars, 10+ API calls, all callbacks
- [x] `label_txt` naming preserved (avoids shadowing label() atom import)
- [x] `permissions` default object: all 7 keys (can_download, can_print, can_copy, can_right_click, watermark_enabled, can_annotate, enable_info)
- [x] No useRef in React destructure (AccessScreen uses setTimeout, not useRef)
- [x] React.Fragment used for feedback rows (global UMD React object — no import needed)
- [x] AnnotationLayer and CommentPopup NOT imported (ViewerScreen-only — confirmed by code audit)
- [x] AppShell.jsx updated: added `import { AccessScreen }`, removed from props signature
- [x] app.jsx render call updated: removed `AccessScreen={AccessScreen}` prop
- [x] 8 dead imports removed from app.jsx (TabBtn, AccessLog, KpiCard, RangeBtn, SparkChart, DonutChart, DocAnalyticsRow, buildFeedbackFilters)
- [x] Build: 198.0 kb ✅

---

## Import Hygiene After Sprint 4.2C

Imports remaining in app.jsx after cleanup — ALL used by ViewerScreen:

| Import | Used by |
|---|---|
| LAYOUT, ZOOM_MIN, ZOOM_MAX, ZOOM_STEP, ZOOM_PRESETS, _saveLayoutPref | ViewerScreen |
| _errMsg | ViewerScreen |
| useTextLoader | ViewerScreen |
| useLinksSidecar | ViewerScreen |
| useSearchHighlights | ViewerScreen |
| useAnnotations | ViewerScreen |
| useViewerLayout | ViewerScreen |
| usePageLoader | ViewerScreen |
| useViewerSession | ViewerScreen |
| useToast, ToastProvider | ViewerScreen |
| ViewerToolbar | ViewerScreen |
| C, mono | ViewerScreen |
| LaserPointer | ViewerScreen |
| RectMagnifier | ViewerScreen |
| SearchPanel | ViewerScreen |
| InsightsModal | ViewerScreen |
| LinksPanel | ViewerScreen |
| TocSidebar | ViewerScreen |
| PageThumb | ViewerScreen |
| ViewerErrorBoundary | ViewerScreen |
| label, SectionLabel, StatusDot, RiskBadge, Chip, Btn, Card, Modal, Toggle, Field, Divider, Sidebar, NavItem, Header | ViewerScreen |
| GateMessage | ViewerScreen |
| AccessGate | ViewerScreen |
| ViewerInfoPanel | ViewerScreen |
| AnnotationLayer | ViewerScreen |
| CommentPopup | ViewerScreen |
| DocumentPicker | ViewerScreen |
| AppShell | bootstrap render call |

---

## Risk Assessment

| Risk ID | Description | Status |
|---|---|---|
| R-041 | pollRef interval leak | MITIGATED — cleanup effect in UploadScreen.jsx |
| R-042 | fileRef dual ownership | MITIGATED — same ref object, semantics unchanged |
| R-043 | Inner helpers | MITIGATED — promoted to module-level |
| R-044 | 12 API endpoints | PRESERVED — all verbatim |
| R-045 | AccessScreen no useRef | DOCUMENTED — only useState/useEffect/useCallback |
| R-046 | label_txt naming | PRESERVED — no rename |
| R-047 | permissions default | PRESERVED — all 7 keys |
| R-048 | No AnnotationLayer in AccessScreen | DOCUMENTED — confirmed by code audit |
| R-049 | React.Fragment global | CONFIRMED — no import needed |

---

## Security Surface Review

No security regression introduced. All auth and permission boundaries unchanged:
- AccessScreen permissions object: all 7 keys preserved with correct defaults (watermark_enabled: true, can_download: false, etc.)
- handleSave: still creates link via SecureDocAPI with payload.permissions — unchanged
- handleRevoke: still revokes all links atomically — unchanged
- poll interval: cleanup on unmount prevents ghost API calls — unchanged
- All localStorage reads still go through SecureDocAPI (AppShell/BillingScreen only)

---

## What Remains

ViewerScreen is the only remaining inline screen (882 lines total in app.jsx, of which ~840 are ViewerScreen).

Sprint 4.2D target: Extract ViewerScreen to `src/screens/ViewerScreen.jsx`.

Key complexity factors for Sprint 4.2D:
- 8 custom hooks with inter-hook dependencies
- `_setPageRef.current` assigned in render body (NOT useEffect)
- `reinitRef.current` also assigned via hook return
- refs assigned inside render: `_setPageRef.current = () => setPage(1)` at line 85
- ~840 LOC, highest-risk extraction in the codebase
