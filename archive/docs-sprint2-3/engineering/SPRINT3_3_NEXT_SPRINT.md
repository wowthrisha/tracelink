# Sprint 3.4 — Next Best Action

**Authored**: 2026-06-17 (Phase 10 output from Autonomous Engineering Framework)  
**Current state**: app.jsx at 4,289 lines; 22 source files; build 196.6 kb

---

## Critical Path Analysis

The bottleneck is the **shared atom layer** (lines 30–430 in current app.jsx):

```
SectionLabel, StatusDot, RiskBadge, Chip, Btn, Card, Modal,
Toggle, Field, Divider, Header, Sidebar, NavItem  (~405 lines)
```

These atoms are dependencies of:
- `AccessGate` (uses Btn) — blocked
- `ViewerInfoPanel` (uses SectionLabel, RiskBadge, StatusDot, Divider, Btn) — blocked
- All screen components (UploadScreen, AccessScreen, AnalyticsScreen, StorageScreen, LoginScreen, BillingScreen) — all blocked

**Unblocking the atoms enables 6 downstream extractions simultaneously.**

---

## Recommended Sprint 3.4 Scope

### Phase A: Extract Shared Atoms Module

**Create `src/components/atoms.jsx`** — export all 13 shared atom components:
- SectionLabel, StatusDot, RiskBadge, Chip
- Btn, Card, Modal, Toggle, Field, Divider
- Header, Sidebar, NavItem

**Complexity**: Low — these components receive all styling from C (imported via tokens.js) and have no cross-component dependencies among themselves. The `label()` helper function (line 25) is used only within atoms — move it to atoms.jsx.

**Lines freed from app.jsx**: ~405

**Dependency**: tokens.js (already exists ✅)

### Phase B: Extract ViewerInfoPanel

Once atoms are extracted, `ViewerInfoPanel` (121 lines) can be extracted to `components/ViewerInfoPanel.jsx` with:
```js
import { C, mono } from '../constants/tokens.js';
import { SectionLabel, RiskBadge, StatusDot, Divider } from './atoms.jsx';
```

Note: ViewerInfoPanel currently uses `React.useState`/`React.state` directly (line 2930 in current numbering). These must be changed to destructured `{ useState }` in the extracted file.

### Phase C: Extract AccessGate + GateMessage

Once atoms are extracted:
```js
// components/GateMessage.jsx
import { C } from '../constants/tokens.js';

// components/AccessGate.jsx
import { C } from '../constants/tokens.js';
import { Btn } from './atoms.jsx';
import { GateMessage } from './GateMessage.jsx';
```

**Lines freed from app.jsx**: ~83

### Phase D: Extract AnnotationLayer + CommentPopup (if risk assessment clears)

**Risk**: MEDIUM — AnnotationLayer has a drawing state machine. Requires:
1. Full prop audit (all props currently in app.jsx's `annotations`, `activeTool`, `sessionPrefix`, `commentDraft`, `onDraw`, `onDelete`, `onOpenThread`, `C`, `mono`)
2. Verify no shared mutable state between AnnotationLayer and ViewerScreen beyond props
3. Extract only after prop audit confirms clean boundary

**Lines freed if extracted**: ~173

---

## Sprint 3.4 Execution Prompt

```
Sprint 3.4 — Shared Atoms Extraction

Scope:
1. Create src/components/atoms.jsx — export all 13 shared atoms + label() helper
   Import: C, mono from '../constants/tokens.js'
   Export: SectionLabel, StatusDot, RiskBadge, Chip, Btn, Card, Modal, Toggle, Field, Divider, Header, Sidebar, NavItem
   
2. Update app.jsx:
   - Add import { ...all atoms } from './components/atoms.jsx'
   - Remove all atom definitions (~405 lines)
   - Remove label() helper (moves to atoms.jsx)
   
3. Extract components/GateMessage.jsx (16 lines + C import)
4. Extract components/AccessGate.jsx (67 lines + C, Btn imports)
5. Extract components/ViewerInfoPanel.jsx (121 lines + C, mono, atoms imports)
   NOTE: Change React.useState → useState, React.state → this.state (if any)

6. Extract components/AnnotationLayer.jsx + components/CommentPopup.jsx
   ONLY after completing prop audit in Phase 0

Constraints (unchanged):
- DO NOT ADD ANY NEW USER-VISIBLE FEATURES
- DO NOT MODIFY UX
- ZERO API CHANGES
- Build must pass at each step

Success criteria:
- npm run build → PASS
- app.jsx < 3,800 lines after atoms extracted
- app.jsx < 3,200 lines after all Phase A-C extractions
```

---

## Risk Register for Sprint 3.4

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Atoms barrel causes tree-shaking issue | Low | Low | esbuild handles it; single bundle anyway |
| Circular import: atoms imports from atoms | Low | High | Check before writing — atoms have no cross-deps |
| AnnotationLayer prop boundary unclear | Medium | Medium | Do full prop audit in Phase 0; defer if unclear |
| React.useState in ViewerInfoPanel missed | Low | Medium | grep for React.useState before extracting |
| Header/Sidebar use something in app.jsx not yet extracted | Low | Medium | Audit Header/Sidebar deps before extraction |

---

## Projected State After Sprint 3.4

| Metric | Current | After 3.4 |
|--------|---------|-----------|
| app.jsx lines | 4,289 | ~3,500 |
| Source files | 22 | ~28 |
| Shared atoms in separate file | No | Yes |
| AccessGate extractable | No | Yes |
| ViewerInfoPanel extractable | No | Yes |
| Screen extractions unblocked | No | Yes |
