# Decision Log — SecureDoc Engineering

## Sprint 3.3 Decisions

---

### D-001: Extract C/mono to constants/tokens.js as prerequisite

**Decision**: Create `constants/tokens.js` before extracting any component that uses C or mono via closure.

**Alternatives considered**:
1. Pass C/mono as props to every component (rejected — inflates prop surfaces, couples component interfaces to token values)
2. Inline tokens per-file (rejected — creates drift; tokens would diverge across files)
3. Extract tokens.js first, then extract components (CHOSEN)

**Why**: The 47 C keys and mono object are shared across 30+ components. A single source of truth avoids synchronization bugs and future token changes needing to touch every file.

**Risk**: Circular import risk was assessed — tokens.js imports nothing, so there is no circular dependency possible.

---

### D-002: Delete MockPage and WatermarkOverlay rather than extract

**Decision**: Delete both components (dead code) rather than moving them to separate files.

**Finding**: `grep -n "<MockPage\|<WatermarkOverlay"` returned zero results. Both are defined but never called.

**Why delete instead of extract**: Dead code has no value. Extracting it would add 2 files with no runtime effect. The watermark and mock-page visual effects are done inline in ViewerScreen. These components are vestigial from a previous design iteration.

**Risk**: Zero — dead code deletion cannot break any behavior.

---

### D-003: Leave GateMessage in app.jsx with AccessGate

**Decision**: Not extracting `GateMessage` in this sprint.

**Why**: GateMessage is only called inside AccessGate (3 calls: not_found, revoked, expired statuses). AccessGate itself is blocked from extraction because it uses the `Btn` atom still in app.jsx. Extracting GateMessage alone would require AccessGate to import it from components/, while AccessGate stays in app.jsx. This creates a tangled dependency with zero architectural gain. Both will move together in the atoms extraction sprint.

---

### D-004: Leave ViewerInfoPanel in app.jsx

**Decision**: Not extracting `ViewerInfoPanel` in this sprint.

**Why**: ViewerInfoPanel uses `SectionLabel`, `RiskBadge`, `StatusDot`, `Divider` (shared atoms still in app.jsx) and `Btn`. All 5 of these dependencies are app.jsx-internal. Extracting ViewerInfoPanel would require either (a) circular imports or (b) extracting atoms first. The atoms extraction is planned for Sprint 3.5+.

---

### D-005: Keep C/mono as props for InsightsModal and LinksPanel

**Decision**: InsightsModal and LinksPanel receive C and mono as props (existing design) — NOT importing from tokens.js.

**Why**: These components were already designed with C/mono as props (added during previous Sprint 3.2 prop-threading work). Changing to tokens.js import would be a refactor-of-a-refactor with no benefit. The prop design works correctly, avoids coupling component to the global token object, and makes the component more testable in isolation.

---

### D-006: Move `_THUMB_CONCURRENCY` semaphore to PageThumb.jsx

**Decision**: The module-level semaphore variables (`_THUMB_CONCURRENCY`, `_thumbQueue`) move with `PageThumb` to `components/PageThumb.jsx`.

**Why**: The semaphore is an implementation detail of PageThumb's fetch strategy. It is not shared with any other component. Leaving it in app.jsx would create a dangling dependency where app.jsx defines module-level state solely for a component it no longer owns. Moving it co-locates the concern.

**Risk**: The semaphore is instantiated once per module boundary. After extraction, it is module-scoped to PageThumb.jsx. Since esbuild bundles into a single output file, there is still only one instance — behavior is unchanged.

---

## Sprint 3.1+3.2 Decisions (Previous)

### D-007: useToast() called internally in useViewerSession

**Decision**: `useViewerSession` calls `useToast()` internally rather than receiving toast as a parameter.

**Why**: Removes prop drilling. The hook is always rendered inside a ToastProvider tree. Optional chaining (`toast?.()`) is preserved for safety — returns null if called outside provider, which cannot happen in current code but is defensive.

### D-008: Separate files for panels (not viewer-panels/ barrel)

**Decision**: Each panel (InsightsModal, LinksPanel, SearchPanel) gets its own file rather than a `viewer-panels/` module.

**Why**: No shared code exists between the three panels. Different dependency profiles. Barrel files impede tree-shaking and obscure import paths. See SPRINT3_PHASE3_1_3_2_REPORT.md for full analysis.
