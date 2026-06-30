# Repository Inventory
Sprint 4.0 — Phase 0
Date: 2026-06-18

---

## Source File Inventory (frontend/src/)

33 files across 6 directories.

### Root (src/)
| File | Lines | Role |
|---|---|---|
| `app.jsx` | 3,275 | Root — all screens, routing, App component |

### constants/
| File | Lines | Exports |
|---|---|---|
| `tokens.js` | 40 | `C` (47 keys), `mono` |
| `viewer.js` | 27 | `LAYOUT`, `ZOOM_*`, `_saveLayoutPref`, `_loadLayoutPref` |

### contexts/
| File | Lines | Exports |
|---|---|---|
| `toast.jsx` | 47 | `ToastCtx`, `useToast`, `ToastProvider` |

### utils/
| File | Lines | Exports |
|---|---|---|
| `viewer.js` | 12 | `_errMsg` |

### hooks/ (7 files)
| File | Lines | Exports |
|---|---|---|
| `useAnnotations.js` | 67 | `useAnnotations` |
| `useLinksSidecar.js` | 68 | `useLinksSidecar` |
| `usePageLoader.js` | 242 | `usePageLoader` |
| `useSearchHighlights.js` | 61 | `useSearchHighlights` |
| `useTextLoader.js` | 48 | `useTextLoader` |
| `useViewerLayout.js` | 139 | `useViewerLayout` |
| `useViewerSession.js` | 168 | `useViewerSession` |

### components/ (16 files)
| File | Lines | Exports |
|---|---|---|
| `atoms.jsx` | 411 | `label`, `SectionLabel`, `StatusDot`, `RiskBadge`, `Chip`, `Btn`, `Card`, `Modal`, `Toggle`, `Field`, `Divider`, `Sidebar`, `NavItem`, `Header` |
| `AccessGate.jsx` | 72 | `AccessGate` |
| `AnnotationLayer.jsx` | 155 | `AnnotationLayer` |
| `CommentPopup.jsx` | 20 | `CommentPopup` |
| `DocumentPicker.jsx` | 78 | `DocumentPicker` |
| `GateMessage.jsx` | 17 | `GateMessage` |
| `InsightsModal.jsx` | 70 | `InsightsModal` |
| `LaserPointer.jsx` | 28 | `LaserPointer` |
| `LinksPanel.jsx` | 128 | `LinksPanel` |
| `PageThumb.jsx` | 108 | `PageThumb` |
| `RectMagnifier.jsx` | 67 | `RectMagnifier` |
| `SearchPanel.jsx` | 136 | `SearchPanel` |
| `TocSidebar.jsx` | 125 | `TocSidebar` |
| `ViewerErrorBoundary.jsx` | 23 | `ViewerErrorBoundary` |
| `ViewerInfoPanel.jsx` | 120 | `ViewerInfoPanel` |
| `ViewerToolbar.jsx` | 397 | `ViewerToolbar` |

### components/upload/ (5 files)
| File | Lines | Exports |
|---|---|---|
| `DocRow.jsx` | 80 | `DocRow` |
| `StatCard.jsx` | 25 | `StatCard` |
| `UploadDropZone.jsx` | 26 | `UploadDropZone` |
| `UploadMetadataPanel.jsx` | 32 | `UploadMetadataPanel` |
| `UploadProgressPanel.jsx` | 33 | `UploadProgressPanel` |

**Total: 33 source files, 6,345 lines**

---

## Dead File Inventory

**None found.** Every component file is imported by app.jsx. Verified via cross-reference of all exports against all import statements.

---

## Dead Component Inventory

**None found.** All named exports are consumed by at least one importer:
- All 14 atoms are used in app.jsx (verified by grep, min count 1)
- All viewer constants used (LAYOUT: 9, ZOOM_MIN: 2, ZOOM_MAX: 2, ZOOM_STEP: 2, ZOOM_PRESETS: 2, _saveLayoutPref: 2, _errMsg: 25 in app.jsx)
- `_loadLayoutPref` used exclusively in useViewerLayout.js (not app.jsx — intentional encapsulation)

---

## Unused Export Inventory

**None confirmed.** One note:

| Export | File | Status |
|---|---|---|
| `_loadLayoutPref` | `constants/viewer.js` | Used by `useViewerLayout.js` only — NOT imported by app.jsx — correct encapsulation, not dead |

---

## Unused Import Inventory

**None found.** All imports in app.jsx verified in use:
- All 14 atoms from atoms.jsx: minimum 1 use each in app.jsx body
- `mono`: 84 uses in app.jsx
- `ToastProvider`: 9 uses, `useToast`: 7 uses
- All viewer constants: used (LAYOUT 9×, ZOOM_MIN/MAX/STEP/PRESETS 2× each, _saveLayoutPref 2×)
- All component imports: imported and referenced in JSX

No unused imports found in any extracted component file.

---

## Build Artifact Inventory

| File | Size | Status |
|---|---|---|
| `frontend/dist/app.bundle.js` | 202,180 bytes (197.4 kb) | Intentionally committed — see `securedoc/.gitignore` line `!frontend/dist/` |

---

## Untracked File Inventory (git status)

| Path | Size | Created | Assessment |
|---|---|---|---|
| `securedoc/].md` | 31,909 bytes | 2026-06-04 | Malformed filename — content is TraceView Pilot Deployment Guide Phase D2.7. Shell redirect accident (`> ].md`). Should be renamed or deleted. |
| `securedoc/200` | 0 bytes | 2026-06-04 | Empty file, likely a shell accident |
| `securedoc/404` | 0 bytes | 2026-06-04 | Empty file, likely a shell accident |
| `frontend/src/app.jsx` | 3,275 lines | modified | Sprint 3.5 extractions |
| `frontend/src/hooks/useViewerSession.js` | 168 lines | modified | Refactor: toast from prop to internal useToast() call |
| `frontend/dist/app.bundle.js` | 202,180 bytes | rebuilt | Intentionally committed |
| `securedoc/*.md` (50+ files) | varies | prior sessions | Repo-level audit documents from prior engineering sessions |
| `frontend/docs/engineering/*.md` (9 files) | varies | Sprints 3.4–3.5 | Current sprint engineering docs |

---

## Documentation Directory Inventory

Two separate engineering docs directories exist:

| Path | Files | Content |
|---|---|---|
| `securedoc/docs/engineering/` | 22 files | Phase 1–2 reports, Sprint 2 audit, Sprint 3.3 report (prior sessions) |
| `frontend/docs/engineering/` | 9 files | Sprint 3.4–3.5 reports, Risk Register, Action Log, Decision Log, Scorecard (current) |

**Recommendation:** Consolidate to `securedoc/docs/engineering/` as the canonical location, or document clearly which is current. Both are untracked (not committed).
