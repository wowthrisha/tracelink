# Decision Log
SecureDoc Frontend — Autonomous Engineering Framework
Append-only. Records architectural and implementation decisions with rationale.

---

## Sprint 3.3

### D-001 — Extract design tokens to constants/tokens.js
**Decision:** Create `src/constants/tokens.js` as single source of truth for all 47 C keys and mono.
**Rationale:** C was defined inline in app.jsx and duplicated (_TC subset) in toast.jsx. Any future color change required hunting multiple definitions. Centralizing eliminates divergence risk.
**Alternatives considered:** (a) Keep inline — rejected, divergence risk. (b) CSS variables — rejected, would require UX-visible changes to all components.
**Impact:** Zero visual change. All existing C references unchanged. toast.jsx updated from _TC to C.

### D-002 — C/mono as props vs import in extracted components
**Decision:** Components that already received C/mono as props continue to do so (InsightsModal, LinksPanel, ViewerToolbar, AnnotationLayer, CommentPopup). Components that referenced C/mono via closure get an import statement in their extracted file.
**Rationale:** Changing prop-passing components to imports would alter their external interface and require caller changes. The prop pattern is already clean for those components.
**Impact:** Zero caller changes needed for prop-passing components.

### D-003 — Semaphore colocates with PageThumb
**Decision:** `_THUMB_CONCURRENCY` and `_thumbQueue` module-level state moves to `components/PageThumb.jsx`.
**Rationale:** The semaphore is purely an implementation detail of PageThumb's fetch throttling. Keeping it in app.jsx after extraction would create an invisible dependency between files.
**Impact:** Encapsulation improved. No behavioral change — semaphore scope is now module scope of PageThumb.jsx.

### D-004 — Delete MockPage and WatermarkOverlay
**Decision:** Delete both components rather than extract them.
**Rationale:** Zero call sites found via grep. Dead code extraction wastes time and adds file count for zero value.
**Impact:** app.jsx reduced. No functional change.

### D-005 — Python-based line deletion for Unicode mismatch
**Decision:** Use Python bottom-to-top line deletion when Edit tool fails on Unicode box-drawing characters.
**Rationale:** Comment strings containing `─` (U+2500) and `—` (U+2014) cause Edit tool string match failure. Python file I/O with line number ranges bypasses encoding issues.
**Pattern:** Always delete bottom-to-top to preserve line number accuracy for subsequent deletions.

---

## Sprint 3.4

### D-006 — Export label() from atoms.jsx
**Decision:** Export the `label()` helper function from atoms.jsx even though it is a simple style factory.
**Rationale:** `label()` is called at 8+ locations in screen components still inside app.jsx (lines 766, 2628, 2764, 2912, 3037, 3150, 3306, 3403). Exporting it avoids duplicating the definition in app.jsx after atoms extraction.
**Impact:** app.jsx import line updated to include `label`. No call site changes.

### D-007 — NAV_SECTIONS stays module-private in atoms.jsx
**Decision:** `NAV_SECTIONS` constant is NOT exported from atoms.jsx.
**Rationale:** It is used exclusively by `Sidebar`. Exporting it would expose internal nav structure to all importers. Module-private const above the Sidebar function is correct ownership.
**Impact:** Callers cannot import NAV_SECTIONS — intended.

### D-008 — emoji in AccessGate as direct characters
**Decision:** Replace `'🔐'` surrogate pair escapes with direct emoji literals (🔐 🔒 📧).
**Rationale:** Surrogate pair escapes are a JavaScript UCS-2 encoding artifact. Direct emoji chars are standard UTF-8 and more readable. Same visual output.
**Impact:** Zero visual change. No behavioral change.

### D-009 — Fix React.useState in ViewerInfoPanel
**Decision:** In extracted ViewerInfoPanel.jsx, add `const { useState } = React;` and use `useState` instead of `React.useState`.
**Rationale:** All other extracted components use destructured React globals. Consistency prevents confusion. `React.useState` would still work (React is a global UMD), but it's inconsistent.
**Impact:** Zero behavioral change.

### D-010 — Defer AnnotationLayer and CommentPopup extraction to Sprint 3.5 (Sprint 3.4)
**Decision:** Do not extract AnnotationLayer or CommentPopup in Sprint 3.4 per explicit Phase 4 instruction.
**Rationale:** Phase 4 is a readiness review only. Extraction in same sprint as review skips the approval gate. ANNOTATION_LAYER_READINESS_REVIEW.md confirms extraction is LOW-MEDIUM risk and safe for Sprint 3.5.
**Impact:** app.jsx retained these components in Sprint 3.4. Extracted in Sprint 3.5.

---

## Sprint 3.5

### D-011 — UploadDropZone/UploadMetadataPanel/UploadProgressPanel extracted as prop-receivers
**Decision:** Extract the three inline JSX sections of UploadScreen into named components that receive all needed state and handlers as props.
**Rationale:** These sections are cohesive units (drop target, metadata options, progress display) but were inline JSX with no component boundary. Extraction without redesign requires full prop drilling — all state stays in UploadScreen.
**Alternatives considered:** (a) Leave inline — rejected, Sprint 3.5 target is named components in `components/upload/`. (b) Move state into each component — rejected, would require UploadScreen to lift-state-up pattern, which is a redesign violation.
**Impact:** UploadScreen unchanged in behavior. 3 new props-only components.

### D-012 — DocumentPicker placed in components/ not components/upload/
**Decision:** `DocumentPicker.jsx` lives in `src/components/` (not `src/components/upload/`).
**Rationale:** The inline comment in the original code says "Shared empty-state component shown in Viewer and Access Control when no document is selected yet." It is called from ViewerScreen and AccessScreen, not just UploadScreen. Placing it in `upload/` would misrepresent ownership.
**Impact:** Import path from app.jsx: `'./components/DocumentPicker.jsx'`.

### D-013 — Use dynamic Python pattern match for function deletions, not hardcoded line numbers
**Decision:** Re-find function boundaries dynamically in the Python deletion script rather than using pre-computed line numbers that would become stale after earlier deletions.
**Rationale:** Multiple deletions in a single script cause cumulative line number shifts. Dynamic re-finding eliminates stale-offset bugs.
**Failure mode encountered:** Walk-back heuristic stopped before the `/*` opening of DocumentPicker's docblock, leaving an orphaned unclosed comment. Fixed in same sprint (A-048). Future sprints should use explicit grep-verified line ranges or content-based deletion for comment blocks with `─` characters.
**Impact:** Build error encountered and fixed within same sprint. Lesson recorded for Sprint 4.

---

## Sprint 4.0

### D-014 — dist/app.bundle.js is intentionally committed
**Decision:** Accept `frontend/dist/app.bundle.js` as a tracked, committed build artifact.
**Rationale:** Root `.gitignore` has `dist/` (ignored globally) then `!frontend/dist/` (explicitly un-ignored). This is a deliberate deployment choice: the static bundle is served directly from the repository via Railway/Cloudflare, eliminating the need for a CI build step before deploy.
**Alternatives considered:** (a) Add `frontend/dist/` to .gitignore and build in CI — rejected, would add CI complexity for a single-file output. (b) Move to CDN build pipeline — future consideration, not Sprint 4 scope.
**Impact:** No change to current practice. Documented to prevent future accidental `.gitignore` additions.

### D-015 — Preserve ].md content, delete 200 and 404
**Decision:** Delete `securedoc/200` and `securedoc/404` (0-byte shell accidents). Do NOT delete `securedoc/].md` — content is "TraceView Pilot Deployment Guide Phase D2.7" (31,909 bytes), which may be the only copy of this document.
**Rationale:** The `].md` filename is clearly a shell redirect accident (`> ].md`) but the content is real operational documentation. Deleting it would destroy the document. The user should rename it to `PILOT_DEPLOYMENT_GUIDE.md` and commit it.
**Impact:** `200` and `404` deleted (A-055, A-056). `].md` remains untracked; flagged for user action.

### D-016 — Accept useViewerSession toast refactor
**Decision:** Accept uncommitted change in `useViewerSession.js` that moves `toast` from a prop parameter to an internal `useToast()` call.
**Rationale:** App.jsx never passed `toast` to `useViewerSession` — the parameter was dead at the call site. The refactor improves encapsulation (hook manages its own toast instance). The `import { useToast }` addition is consistent with how other hooks and components access toast.
**Impact:** Zero behavioral change. Hook signature simplified: `{ onValidated, toast }` → `{ onValidated }`. All callers (just app.jsx) were already compatible.

---

## Sprint 4.1

### D-017 — Delete PermRow instead of extracting it
**Decision:** Delete `PermRow` from app.jsx without creating `components/access/PermRow.jsx`.
**Rationale:** Phase 0 grep confirmed `PermRow` is defined at line 1973 but has zero call sites. The AccessScreen permissions UI uses its own inline toggle grid (lines 1521–1541) with direct state mutation — not `PermRow`. Extracting dead code wastes time and adds an unused file.
**Alternatives considered:** (a) Extract anyway in case it was intended for future use — rejected; dead code should not be shipped. (b) Leave in app.jsx — rejected; dead code in a 3,000-line file increases maintenance burden.
**Impact:** PermRow deleted (A-061). No call sites exist so zero behavioral change. Risk Register updated (R-027).

### D-018 — Extract SparkChart with gradient ID caveat documented
**Decision:** Extract SparkChart exactly as-is, including the `id="aGrad"` SVG gradient. Add a code comment noting the collision risk.
**Rationale:** The gradient ID is document-scoped in HTML/SVG. If two SparkChart instances rendered simultaneously, both would define `id="aGrad"` and the second definition would win (or behavior would be undefined across browsers). Current usage has exactly 1 SparkChart (in the overview tab, which is mutually exclusive with other tabs). The risk is theoretical given current routing.
**Alternatives considered:** (a) Parameterize the ID with a prop — rejected, adds complexity with no immediate benefit. (b) Use a module-scoped unique ID generator — rejected, Math.random() is unavailable in workflow scripts (not relevant here, but adds complexity).
**Impact:** SparkChart extracted with inline comment (R-028). Future work: parameterize ID if multiple instances are ever needed.

### D-019 — AccessLog deferred to Sprint 4.2
**Decision:** Do not extract AccessLog in Sprint 4.1. Schedule for Sprint 4.2 Phase 6, before AccessScreen extraction.
**Rationale:** AccessLog has its own API call (`getEvents`) and context dependency (`useToast`). It is not a pure prop-receiver. The correct extraction pattern (following DocumentPicker) requires: import `_errMsg`, `useToast`, and all atoms it uses. This is low-complexity but out of Sprint 4.1 scope (which targets pure/stateless sub-components).
**Impact:** AccessLog remains inline in app.jsx. Documented in SCREEN_EXTRACTION_READINESS_REVIEW.md Phase 4 (R-029).

---

## Sprint 4.2A

### D-020 — AppShell receives still-inline screens as props (circular dep avoidance)
**Decision:** `AppShell.jsx` receives `UploadScreen`, `ViewerScreen`, `AccessScreen`, `AnalyticsScreen` as props rather than importing them from app.jsx.
**Rationale:** Importing from app.jsx would create a circular dependency: AppShell → app.jsx → AppShell. The prop-injection pattern is the only way to extract App routing logic while the four heaviest screens remain inline. As each screen is extracted in Sprints 4.2B+, its prop is replaced by a direct import inside AppShell — zero caller changes needed each time.
**Alternatives considered:** (a) Defer AppShell extraction until all screens extracted — rejected, the sprint explicitly targets App routing logic; (b) Reverse the dependency (app.jsx imports screens, not AppShell) — not possible since app.jsx is the entry file.
**Impact:** app.jsx render line passes four screen components as props. This is temporary scaffolding replaced incrementally in Sprint 4.2B+.

### D-021 — parseJwtEmail moves to AppShell.jsx
**Decision:** Move `parseJwtEmail()` from app.jsx into `src/screens/AppShell.jsx` as a module-level helper.
**Rationale:** It is used exclusively by App() at `const userEmail = token ? parseJwtEmail(token) : '';`. Co-locating with the consumer (now AppShell) is the correct ownership. `src/utils/auth.js` was also considered but adds a file for a single 5-line utility.
**Impact:** Zero behavioral change. parseJwtEmail no longer in app.jsx.

### D-022 — BillingScreen authHeaders() promoted to module-level
**Decision:** `authHeaders()` was an inner function of BillingScreen in app.jsx. It is now a module-level function in `BillingScreen.jsx`.
**Rationale:** Inner functions in React component bodies are redefined every render. Since authHeaders() has no closure dependency on component state, module-level is semantically identical and more efficient. The localStorage.getItem('securedoc_token') call inside it is unchanged.
**Impact:** No behavioral change. Slightly more efficient (defined once, not per-render).

### D-023 — StorageScreen fmtBytes() and lifecycleBadge() promoted to module-level
**Decision:** `fmtBytes()` and `lifecycleBadge()` were inner functions of StorageScreen in app.jsx. They are now module-level functions in `StorageScreen.jsx`.
**Rationale:** Neither function closes over component state. Both are pure (fmtBytes) or near-pure (lifecycleBadge returns JSX with no state dependency). Module-level placement avoids per-render redefinition and is the correct ownership pattern for stateless helpers.
**Impact:** No behavioral change. lifecycleBadge() JSX output is identical (same style objects, same text).

---

## Sprint 4.2B

### D-024 — AnalyticsScreen migrated from AppShell prop to direct import
**Decision:** In Sprint 4.2A, AnalyticsScreen was passed as a prop to AppShell to avoid circular dependency. After extracting it to `src/screens/AnalyticsScreen.jsx`, AppShell now imports it directly.
**Rationale:** The prop-injection pattern (D-020) was temporary scaffolding. Once a screen is extracted to its own file, the correct pattern is a direct import — cleaner signatures, no prop threading, no risk of caller forgetting to pass the prop.
**Alternatives considered:** Keep as prop for consistency with remaining 3 inline screens — rejected; the whole point of D-020 was to allow incremental migration. Each extracted screen immediately becomes an import.
**Impact:** AppShell props reduced from 4 to 3. app.jsx render call updated. No behavioral change.

### D-026 — UploadScreen inner helpers promoted to module-level
**Decision:** `_detectFileType()`, `_isDocType()`, and `MAX_POLL_ATTEMPTS` are promoted from inside the UploadScreen function body to module-level in UploadScreen.jsx.
**Rationale:** None of the three close over any React state or props. Promoting to module-level avoids per-render redefinition (same pattern as D-022/D-023 for authHeaders/fmtBytes). MAX_POLL_ATTEMPTS is a constant so it benefits most — promoted to a `const` at module scope.
**Impact:** Zero behavioral change. The polling loop still reads MAX_POLL_ATTEMPTS correctly via closure over the module constant.

### D-027 — AccessScreen confirmed: no useRef, no AnnotationLayer/CommentPopup
**Decision:** AccessScreen.jsx imports only `useState, useEffect, useCallback` (no `useRef`). It does NOT import AnnotationLayer or CommentPopup.
**Rationale:** Code audit of the full 703-line AccessScreen confirmed: (1) linkCopied and saved timeouts use `setTimeout` directly, not useRef. (2) The "Annotations" tab shows a server-side visual annotations table — it does NOT render the interactive AnnotationLayer overlay. AnnotationLayer and CommentPopup are exclusively ViewerScreen components. The sprint execution plan (R-048) documented this correctly.
**Impact:** Cleaner import graph. AccessScreen has no dependency on viewer components. Future ViewerScreen extraction is unblocked.

### D-028 — 8 dead imports removed from app.jsx after AccessScreen extraction
**Decision:** After AccessScreen extraction, 8 import lines were deleted from app.jsx: TabBtn, AccessLog, KpiCard, RangeBtn, SparkChart, DonutChart, DocAnalyticsRow, buildFeedbackFilters.
**Rationale:** All 8 were used only by AccessScreen (TabBtn, AccessLog, buildFeedbackFilters) or AnalyticsScreen (KpiCard, RangeBtn, SparkChart, DonutChart, DocAnalyticsRow). Both screens are now extracted to their own files with their own imports. Leaving dead imports in app.jsx adds confusion and causes esbuild to potentially include their modules twice (once via app.jsx, once via the extracted screen). Removal is zero-risk since no remaining app.jsx code references them.
**Impact:** app.jsx import block reduced to 28 lines, all used by ViewerScreen. Build: 198.0 kb ✅.

### D-025 — AnalyticsScreen `label` parameter renamed to `lbl` in tab map
**Decision:** In the tabs `.map()` callback, destructured parameter `label` was renamed to `lbl` in `AnalyticsScreen.jsx`.
**Rationale:** In app.jsx, the local `label` parameter (from `[id, label]` destructuring) shadowed the imported `label()` function. This works in app.jsx because `label()` isn't called within that scope. In AnalyticsScreen.jsx, the imported `label` is used throughout the file at `label(9)` — keeping the shadow would make the code harder to read and is error-prone for future edits. Renaming to `lbl` eliminates the shadow with zero visual change.
**Impact:** Zero behavioral change. Tab labels render identically. Future maintainers see a clean, non-shadowed import.

---

## Sprint 4.2D

### D-029 — ViewerScreen.jsx atoms import limited to {Modal, Header}
**Decision:** ViewerScreen.jsx imports only `{ Modal, Header }` from atoms.jsx, not all 14 atoms in the original app.jsx import line.
**Rationale:** Phase 0 grep audit confirmed that of the 14 atoms in app.jsx's import line (label, SectionLabel, StatusDot, RiskBadge, Chip, Btn, Card, Modal, Toggle, Field, Divider, Sidebar, NavItem, Header), only `Modal` (line 768: thread modal) and `Header` (line 162: no-doc picker early return) are used as JSX components in ViewerScreen's body. The other 12 were present in app.jsx because they are used by other extracted screens (AccessScreen, UploadScreen, AppShell) that formerly shared the file. Including unused imports would add dead imports to the new file, contradicting the import hygiene improvement this sprint achieves.
**Alternatives considered:** (a) Include all 14 for safety — rejected, dead imports are worse than minimal imports; unused imports are confusing and could shadow names in future edits. (b) Include 14 but comment out the unused ones — rejected, commented imports are still dead code.
**Impact:** ViewerScreen.jsx has a minimal, correct atoms import. 12 atoms not included. No behavioral change.

### D-030 — app.jsx is now a 5-line entry point
**Decision:** After ViewerScreen extraction, app.jsx contains only `import { AppShell } from './screens/AppShell.jsx';` and the `ReactDOM.createRoot` render call. The React destructure, section header comment, and all 27 viewer imports were removed entirely.
**Rationale:** With ViewerScreen extracted, app.jsx has no React hook calls, no JSX logic, and no direct component definitions. The React destructure line `const { useState, ... } = React` is only needed by files that call React hooks — app.jsx no longer qualifies. Removing it removes dead global state from the entry point. The section header comment was an artifact of the old multi-screen file structure. The final file (5 lines) is the correct minimum: an import and a render call.
**Alternatives considered:** (a) Keep the React destructure for "symmetry" — rejected, dead global assignments in the entry point have no value. (b) Add a module-level comment explaining the architecture — rejected, ARCHITECTURE_SCORECARD.md is the right place for that; app.jsx should be minimal.
**Impact:** app.jsx reduced from 882 to 5 lines. ReactDOM bootstrap line updated: `<AppShell ViewerScreen={ViewerScreen} />` → `<AppShell />`. esbuild bundle unchanged at 198.0 kb.

---

## Sprint 4.2E

### D-031 — Documentation reorganized into semantic subdirectories
**Decision:** Moved 17 files from flat `docs/engineering/` into `docs/architecture/`, `docs/security/`, `docs/reports/`, `docs/risks/`, and `docs/decisions/`. Kept `ACTION_LOG.md` and sprint plans in `docs/engineering/`.
**Rationale:** At 26 files, the flat directory was hard to navigate. Semantic grouping (architecture decisions vs. security vs. completed reports vs. living risk/decision registers) matches how engineers look for information: "where is the risk register?" not "which engineering doc do I want?"
**Alternatives considered:** (a) Keep flat — rejected; 26+ files in one directory scales poorly as the project grows. (b) Archive completed sprints only — rejected; the architecture and security docs also benefit from separation from operational logs.
**Impact:** 17 files moved. Historical ACTION_LOG references to `docs/engineering/ARCHITECTURE_SCORECARD.md` etc. are now stale paths — acceptable since logs are historical records. Future sprint prompts should use new paths.
