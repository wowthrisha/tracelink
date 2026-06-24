# Architecture Scorecard — SecureDoc Frontend

**Updated**: 2026-06-17 (Sprint 3.3)

---

## File Structure

| Metric | Sprint 2 start | After Sprint 3.2 | After Sprint 3.3 |
|--------|---------------|-----------------|-----------------|
| `app.jsx` lines | 6,047 | 5,085 | 4,289 |
| Separate source files | 10 | 13 | 22 |
| Custom hooks | 7 | 7 | 7 |
| Component files | 1 | 2 | 9 |
| Context files | 0 | 1 | 1 |
| Constant/utility files | 2 | 2 | 3 |

---

## app.jsx Line Reduction History

| Sprint | Lines removed | Cumulative reduction | Source |
|--------|--------------|---------------------|--------|
| Sprint 2 (hooks) | −962 | −962 (−15.9%) | 7 custom hooks extracted |
| Sprint 3.1+3.2 | −440 | −1,402 (−23.2%) | toast.jsx, ViewerToolbar.jsx |
| Sprint 3.3 | −796 | −2,198 (−36.4%) | tokens.js + 9 components |
| **Total** | | **6,047 → 4,289** | |

---

## Component Ownership Map

### Fully extracted (live in separate files)

| Component | File | C/mono dep | Prop surface |
|-----------|------|-----------|-------------|
| `ViewerToolbar` | components/ViewerToolbar.jsx | via props | 38 props |
| `LaserPointer` | components/LaserPointer.jsx | none | 1 prop |
| `RectMagnifier` | components/RectMagnifier.jsx | none | 3 props |
| `SearchPanel` | components/SearchPanel.jsx | none | 6 props |
| `InsightsModal` | components/InsightsModal.jsx | via props | 5 props |
| `LinksPanel` | components/LinksPanel.jsx | via props | 6 props |
| `TocSidebar` | components/TocSidebar.jsx | tokens.js | 7 props |
| `PageThumb` | components/PageThumb.jsx | tokens.js | 6 props |
| `ViewerErrorBoundary` | components/ViewerErrorBoundary.jsx | tokens.js | 1 prop (children) |
| `ToastProvider` + `useToast` | contexts/toast.jsx | tokens.js | — |

### Remaining in app.jsx

| Component | Lines | Why still in app.jsx | Extraction blocker |
|-----------|-------|---------------------|-------------------|
| Shared atoms (SectionLabel, StatusDot, RiskBadge, Chip, Btn, Card, Modal, Toggle, Field, Divider, Header, Sidebar, NavItem, NavItem) | ~405 | Defines the shared atom library | Target: Sprint 3.5 |
| `GateMessage` | 16 | Used only by AccessGate | Move with AccessGate |
| `AccessGate` | 67 | Uses `Btn` atom | Blocked: needs atoms extracted |
| `ViewerScreen` | ~848 | Main orchestrator; still large | Ongoing reduction via panels |
| `AnnotationLayer` | ~152 | Medium-risk extraction | Sprint 3.4 |
| `CommentPopup` | ~21 | Depends on AnnotationLayer data | Sprint 3.4 |
| `ViewerInfoPanel` | ~121 | Uses 5 shared atoms | Blocked: needs atoms extracted |
| All screen components | ~2,200 | Heavy Btn/Card/Modal/C usage | Blocked: needs atoms extracted |

---

## Design Token Dependency Graph

```
constants/tokens.js (C, mono)
├── contexts/toast.jsx (was: _TC inline subset)
├── components/TocSidebar.jsx
├── components/PageThumb.jsx
├── components/ViewerErrorBoundary.jsx
└── app.jsx (import replaces 44-line inline definition)

C/mono as props (no import needed):
├── components/InsightsModal.jsx
├── components/LinksPanel.jsx
└── components/ViewerToolbar.jsx (passed from ViewerScreen)
```

---

## Bundle Impact

| Sprint | Bundle size | Δ |
|--------|------------|---|
| Sprint 2 start | 196.4 kb | — |
| Sprint 3.2 end | 196.8 kb | +0.4 kb |
| Sprint 3.3 end | 196.6 kb | −0.2 kb |

Bundle size is stable. esbuild inlines all imports into the single output file, so module extraction has near-zero cost.

---

## Architecture Quality Scores (1-10)

| Dimension | Sprint 2 start | Sprint 3.3 |
|-----------|---------------|------------|
| Single responsibility | 3 (one 6047-line file) | 6 (22 files, clear concerns) |
| Separation of concerns | 3 | 7 (hooks, contexts, components, constants) |
| Prop drilling hygiene | 4 | 6 (toast no longer drilled; C/mono still wide on ViewerScreen) |
| Token centralization | 2 (inline in 1 place) | 8 (tokens.js, single source) |
| Dead code | 4 (MockPage, WatermarkOverlay existed) | 9 (dead code deleted) |
| Testability | 2 (monolith) | 6 (components independently importable) |
| **Overall** | **3** | **7** |

---

## Remaining to Target (<3,000 lines)

**Current**: 4,289 lines  
**Target**: <3,000 lines  
**Gap**: −1,289 lines needed

| Step | Est. lines freed | Projected total |
|------|-----------------|-----------------|
| Extract shared atoms (~14 components) | ~405 | ~3,884 |
| Extract AccessGate + GateMessage | ~83 | ~3,801 |
| Extract ViewerInfoPanel | ~121 | ~3,680 |
| Extract AnnotationLayer + CommentPopup | ~173 | ~3,507 |
| Extract UploadScreen | ~416 | ~3,091 |
| Extract AccessScreen subsections | ~300 | **~2,791** ← passes 3k |

Atoms extraction is the critical path enabler — it unblocks AccessGate, ViewerInfoPanel, and all screen extractions simultaneously.

---

## Security Posture

No security regressions across all sprints:
- Auth flow unchanged (useViewerSession behavior identical)
- DRM protections unchanged (session event listeners in useViewerSession)
- Token handling unchanged (sessionStorage patterns preserved)
- API surface unchanged (zero endpoint changes)
- Permission gates unchanged (ViewerErrorBoundary, AccessGate behavior identical)
