> **MIGRATED** — This file has been migrated to `docs/governance/ACTION_LOG.md` (2026-06-22, A-144). Append new entries to the governance location. This copy preserved for path compatibility.

# Action Log
SecureDoc Frontend — Autonomous Engineering Framework
Append-only. Each entry records a concrete file change or system action.

---

## Sprint 3.3

Date: 2026-06-15

| # | Action | File | Change |
|---|---|---|---|
| A-001 | CREATE | `src/constants/tokens.js` | Extracted C (47 keys) and mono from app.jsx; single source of truth |
| A-002 | MODIFY | `src/contexts/toast.jsx` | Replaced `_TC` inline color subset with `import { C }` from tokens.js |
| A-003 | CREATE | `src/components/LaserPointer.jsx` | Extracted from app.jsx |
| A-004 | CREATE | `src/components/RectMagnifier.jsx` | Extracted from app.jsx |
| A-005 | CREATE | `src/components/SearchPanel.jsx` | Extracted from app.jsx |
| A-006 | CREATE | `src/components/InsightsModal.jsx` | Extracted from app.jsx; C+mono as props |
| A-007 | CREATE | `src/components/LinksPanel.jsx` | Extracted from app.jsx; C+mono as props |
| A-008 | CREATE | `src/components/TocSidebar.jsx` | Extracted from app.jsx; imports C from tokens.js |
| A-009 | CREATE | `src/components/PageThumb.jsx` | Extracted from app.jsx; includes `_THUMB_CONCURRENCY`/`_thumbQueue` semaphore |
| A-010 | CREATE | `src/components/ViewerErrorBoundary.jsx` | Extracted class component from app.jsx |
| A-011 | MODIFY | `src/app.jsx` | Added imports for all extracted components + tokens.js |
| A-012 | DELETE | `src/app.jsx` | Removed C/mono inline definition (~44 lines) |
| A-013 | DELETE | `src/app.jsx` | Removed inline ViewerErrorBoundary class |
| A-014 | DELETE | `src/app.jsx` | Removed LaserPointer, RectMagnifier, InsightsModal inline definitions |
| A-015 | DELETE | `src/app.jsx` | Removed LinksPanel, SearchPanel, TocSidebar, semaphore, PageThumb, MockPage, WatermarkOverlay (lines 2133–2700 via Python deletion) |
| A-016 | BUILD | `dist/app.bundle.js` | 5,085 → 4,289 lines in app.jsx; bundle 196.7 kb ✅ |

---

## Sprint 3.4

Date: 2026-06-17

| # | Action | File | Change |
|---|---|---|---|
| A-017 | CREATE | `src/components/atoms.jsx` | ~310 lines; 14 atoms + label() + NAV_SECTIONS (private); imports C, mono from tokens.js |
| A-018 | CREATE | `src/components/GateMessage.jsx` | 17 lines; imports C from tokens.js |
| A-019 | CREATE | `src/components/AccessGate.jsx` | ~73 lines; imports C, Btn, GateMessage |
| A-020 | CREATE | `src/components/ViewerInfoPanel.jsx` | ~120 lines; imports C, mono, SectionLabel, RiskBadge, StatusDot, Divider from atoms |
| A-021 | MODIFY | `src/app.jsx` | Added 4 import lines: atoms, GateMessage, AccessGate, ViewerInfoPanel |
| A-022 | DELETE | `src/app.jsx` | Removed atoms block (lines 28–434, 407 lines) via Python bottom-to-top deletion |
| A-023 | DELETE | `src/app.jsx` | Removed GateMessage + AccessGate block (lines 1035–1117, 83 lines) via Python |
| A-024 | DELETE | `src/app.jsx` | Removed ViewerInfoPanel block (lines 2137–2252, 116 lines) via Python |
| A-025 | BUILD | `dist/app.bundle.js` | 4,293 → 3,687 lines in app.jsx; bundle 196.7 kb ✅ |
| A-026 | CREATE | `docs/engineering/ANNOTATION_LAYER_READINESS_REVIEW.md` | Phase 4 readiness review; DO NOT EXTRACT in Sprint 3.4 |
| A-027 | CREATE | `docs/engineering/RISK_REGISTER.md` | Phase 0 risk register; Sprint 3.3 + 3.4 entries |
| A-028 | CREATE | `docs/engineering/ACTION_LOG.md` | This file |
| A-029 | CREATE | `docs/engineering/DECISION_LOG.md` | Phase 7 decision log |
| A-030 | CREATE | `docs/engineering/ARCHITECTURE_SCORECARD.md` | Phase 6 scorecard |

---

## Sprint 3.5

Date: 2026-06-18

| # | Action | File | Change |
|---|---|---|---|
| A-031 | CREATE | `src/components/AnnotationLayer.jsx` | ~148 lines; C/mono as props; const { useState, useRef } = React |
| A-032 | CREATE | `src/components/CommentPopup.jsx` | ~18 lines; C as prop; focus-on-mount via setTimeout |
| A-033 | CREATE | `src/components/DocumentPicker.jsx` | ~72 lines; imports C, SectionLabel, StatusDot, useToast |
| A-034 | CREATE | `src/components/upload/StatCard.jsx` | ~26 lines; imports C, mono, SectionLabel |
| A-035 | CREATE | `src/components/upload/DocRow.jsx` | ~78 lines; imports C, mono, StatusDot, RiskBadge, Btn |
| A-036 | CREATE | `src/components/upload/UploadDropZone.jsx` | ~28 lines; imports C, mono; props from UploadScreen |
| A-037 | CREATE | `src/components/upload/UploadMetadataPanel.jsx` | ~28 lines; imports C, SectionLabel, Btn; props from UploadScreen |
| A-038 | CREATE | `src/components/upload/UploadProgressPanel.jsx` | ~28 lines; imports C, mono, StatusDot, Btn, Card; props from UploadScreen |
| A-039 | MODIFY | `src/app.jsx` | Added 9 import lines for new components |
| A-040 | DELETE | `src/app.jsx` | Removed AnnotationLayer (with 3 comment lines) via Python — lines 1481–1633 |
| A-041 | DELETE | `src/app.jsx` | Removed CommentPopup + comment via Python — lines 1635–1659 |
| A-042 | DELETE | `src/app.jsx` | Removed DocumentPicker block via Python — lines 562–634 |
| A-043 | DELETE | `src/app.jsx` | Removed DocRow via Python — lines 478–552 |
| A-044 | DELETE | `src/app.jsx` | Removed StatCard via Python — lines 457–476 |
| A-045 | MODIFY | `src/app.jsx` | Replaced UploadDropZone inline JSX with component call (Python content replace) |
| A-046 | MODIFY | `src/app.jsx` | Replaced UploadMetadataPanel inline JSX with component call (Python content replace) |
| A-047 | MODIFY | `src/app.jsx` | Replaced UploadProgressPanel inline JSX with component call (Python content replace) |
| A-048 | FIX | `src/app.jsx` | Deleted orphaned unclosed DocumentPicker comment block (lines 394–398) |
| A-049 | BUILD | `dist/app.bundle.js` | 3,687 → 3,275 lines in app.jsx; bundle 197.4 kb ✅ |

---

## Sprint 4.0

Date: 2026-06-18

| # | Action | File | Change |
|---|---|---|---|
| A-050 | CREATE | `docs/engineering/REPOSITORY_INVENTORY.md` | Phase 0 — full source/export/import/build artifact inventory; 33 source files, 6,345 lines |
| A-051 | CREATE | `docs/engineering/DEAD_CODE_AUDIT.md` | Phase 1 — confirmed 0 dead functions/imports/exports; 1 blank-line cluster flagged |
| A-052 | CREATE | `docs/engineering/DEPENDENCY_AUDIT.md` | Phase 2 — confirmed 0 circular deps, 0 duplicate utilities; DAG verified clean |
| A-053 | CREATE | `docs/engineering/BUILD_HYGIENE_AUDIT.md` | Phase 3 — dist/ commit confirmed intentional (!frontend/dist/ in .gitignore); 3 malformed root files documented |
| A-054 | MODIFY | `src/app.jsx` | Phase 4 — collapsed 3 blank lines to 1 at line 387 (Sprint 3.5 deletion artifact) |
| A-055 | DELETE | `securedoc/200` | Phase 4 — deleted empty shell-accident file |
| A-056 | DELETE | `securedoc/404` | Phase 4 — deleted empty shell-accident file |
| A-057 | CREATE | `docs/engineering/SECURITY_BASELINE.md` | Phase 5 — 5 surfaces audited; 0 Critical, 0 High; 2 open Medium items (backend verification) |
| A-058 | CREATE | `docs/engineering/ARCHITECTURE_BASELINE.md` | Phase 6 — full component/hook/context/screen graph; 17 inline targets remaining for Sprint 4.1+ |
| A-059 | BUILD | `dist/app.bundle.js` | Phase 7 — 3,275 → 3,273 lines in app.jsx; bundle 197.4 kb ✅ |

---

## Sprint 4.1

Date: 2026-06-18

| # | Action | File | Change |
|---|---|---|---|
| A-060 | CREATE | `src/components/access/TabBtn.jsx` | Phase 1 — access tab button; imports C from tokens.js; useState hover |
| A-061 | DELETE | `src/app.jsx` (PermRow) | Phase 1 — dead code removal; PermRow was defined but never called (R-027) |
| A-062 | CREATE | `src/components/analytics/KpiCard.jsx` | Phase 2 — KPI stat card; imports C, mono, SectionLabel |
| A-063 | CREATE | `src/components/analytics/RangeBtn.jsx` | Phase 2 — range selector button; imports C, mono |
| A-064 | CREATE | `src/components/analytics/SparkChart.jsx` | Phase 2 — 28-pt area chart; imports C, mono; gradient id=aGrad documented (R-028) |
| A-065 | CREATE | `src/components/analytics/DonutChart.jsx` | Phase 2 — donut chart; imports C, mono |
| A-066 | CREATE | `src/components/analytics/DocAnalyticsRow.jsx` | Phase 2 — analytics table row; imports C, mono, RiskBadge |
| A-067 | CREATE | `src/utils/feedback.js` | Phase 3 — buildFeedbackFilters pure function; no imports |
| A-068 | MODIFY | `src/app.jsx` | Added 7 import lines (TabBtn, KpiCard, RangeBtn, SparkChart, DonutChart, DocAnalyticsRow, buildFeedbackFilters) |
| A-069 | DELETE | `src/app.jsx` (6 analytics inline + TabBtn + buildFeedbackFilters) | Removed 8 inline definitions via Python bottom-to-top deletion (-179 lines net) |
| A-070 | CREATE | `docs/engineering/SCREEN_EXTRACTION_READINESS_REVIEW.md` | Phase 4 — full screen dependency/state/context/API/toast/risk analysis |
| A-071 | BUILD | `dist/app.bundle.js` | Phase 5 — 3,273 → 3,094 lines in app.jsx; bundle 197.5 kb ✅ |

---

## Sprint 4.2A

Date: 2026-06-22

| # | Action | File | Change |
|---|---|---|---|
| A-072 | APPEND | `docs/engineering/RISK_REGISTER.md` | Phase 0 — R-031 through R-035; App/LoginScreen/BillingScreen/StorageScreen assessment |
| A-073 | CREATE | `src/screens/LoginScreen.jsx` | Phase 2 — 8 state vars, URL hash lazy inits, 3 API calls, localStorage write; ~190 lines |
| A-074 | CREATE | `src/screens/BillingScreen.jsx` | Phase 3 — 4 state vars, authHeaders() module-level (D-022), raw fetch; ~155 lines |
| A-075 | CREATE | `src/screens/StorageScreen.jsx` | Phase 4 — 4 state vars, useToast, fmtBytes() + lifecycleBadge() module-level (D-023); ~155 lines |
| A-076 | CREATE | `src/screens/AppShell.jsx` | Phase 1 — App routing logic + parseJwtEmail (D-021); receives 4 inline screens as props (D-020); ~105 lines |
| A-077 | MODIFY | `src/app.jsx` | Added `import { AppShell }` line |
| A-078 | DELETE | `src/app.jsx` | Removed StorageScreen section + function (lines 2397–2556 in pre-sprint numbering) |
| A-079 | DELETE | `src/app.jsx` | Removed ROOT APP header + parseJwtEmail + LOGIN SCREEN + LoginScreen (lines 2558–2802) |
| A-080 | DELETE | `src/app.jsx` | Removed BILLING SCREEN header + BillingScreen (lines 2804–3000) |
| A-081 | DELETE | `src/app.jsx` | Removed App function (lines 3002–3092) |
| A-082 | MODIFY | `src/app.jsx` | Changed `render(<App />)` to `render(<AppShell UploadScreen=... ViewerScreen=... AccessScreen=... AnalyticsScreen=... />)` |
| A-083 | BUILD | `dist/app.bundle.js` | Phase 5 — 3,094 → 2,400 lines in app.jsx; bundle 197.8 kb ✅ |

---

## Sprint 4.2B

Date: 2026-06-22

| # | Action | File | Change |
|---|---|---|---|
| A-084 | APPEND | `docs/engineering/RISK_REGISTER.md` | Phase 0 — R-036 through R-040; AccessLog/AnalyticsScreen/AppShell assessment |
| A-085 | CREATE | `src/components/access/AccessLog.jsx` | Phase 1 — 2 state vars, useCallback, useToast, getEvents(docId,50); no pagination/filter (R-036); ~55 lines |
| A-086 | MODIFY | `src/app.jsx` | Phase 1 — added `import { AccessLog }` line |
| A-087 | DELETE | `src/app.jsx` (AccessLog) | Phase 1 — removed inline AccessLog definition (lines 1953-2003 pre-deletion) |
| A-088 | CREATE | `src/screens/AnalyticsScreen.jsx` | Phase 2 — 9 state vars, useToast, 4 API calls, all 5 chart sub-components; lbl rename avoids import shadow (R-038); ~280 lines |
| A-089 | DELETE | `src/app.jsx` (AnalyticsScreen) | Phase 2 — removed section header + AnalyticsScreen function (-395 lines) |
| A-090 | MODIFY | `src/screens/AppShell.jsx` | Phase 3 — added `import { AnalyticsScreen }`, removed AnalyticsScreen prop from signature (D-024) |
| A-091 | MODIFY | `src/app.jsx` | Phase 3 — removed `AnalyticsScreen={AnalyticsScreen}` from render call |
| A-092 | BUILD | `dist/app.bundle.js` | Phase 4 — 2,400 → 1,955 lines in app.jsx; bundle 197.9 kb ✅ |
| A-093 | CREATE | `docs/engineering/SPRINT4_2C_EXECUTION_PLAN.md` | Phase 8 — UploadScreen + AccessScreen scope |

---

## Sprint 4.2C

Date: 2026-06-22

| # | Action | File | Change |
|---|---|---|---|
| A-094 | APPEND | `docs/engineering/RISK_REGISTER.md` | Phase 0 — R-041 through R-049; UploadScreen/AccessScreen assessment |
| A-095 | CREATE | `src/screens/UploadScreen.jsx` | Phase 1 — 18 state vars; fileRef + pollRef; 12 API calls; _detectFileType + _isDocType + MAX_POLL_ATTEMPTS module-level; ~278 lines |
| A-096 | DELETE | `src/app.jsx` (UploadScreen section) | Phase 1 — removed blank + SCREEN 1 header + UploadScreen function (lines 44-395, -352 lines) |
| A-097 | DELETE | `src/app.jsx` (upload imports) | Phase 1 — removed 5 upload sub-component imports (StatCard, DocRow, UploadDropZone, UploadMetadataPanel, UploadProgressPanel) |
| A-098 | MODIFY | `src/screens/AppShell.jsx` | Phase 1 — added import { UploadScreen }; removed UploadScreen from props signature |
| A-099 | MODIFY | `src/app.jsx` | Phase 1 — removed UploadScreen={UploadScreen} from render call |
| A-100 | BUILD | `dist/app.bundle.js` | Phase 1 verify — 198.0 kb ✅ |
| A-101 | CREATE | `src/screens/AccessScreen.jsx` | Phase 3 — 35 state vars; label_txt preserved; 7-key permissions default; 10+ API calls; 4 useCallback; NO useRef; ~530 lines |
| A-102 | DELETE | `src/app.jsx` (AccessScreen section) | Phase 3 — removed 2 blanks + SCREEN 3 header + AccessScreen function (lines 888-1595, -708 lines) |
| A-103 | DELETE | `src/app.jsx` (dead imports) | Phase 3 — removed 8 dead imports (TabBtn, AccessLog, KpiCard, RangeBtn, SparkChart, DonutChart, DocAnalyticsRow, buildFeedbackFilters) |
| A-104 | MODIFY | `src/screens/AppShell.jsx` | Phase 3 — added import { AccessScreen }; removed AccessScreen from props; updated comment |
| A-105 | MODIFY | `src/app.jsx` | Phase 3 — removed AccessScreen={AccessScreen} from render call; props now { ViewerScreen } only |
| A-106 | BUILD | `dist/app.bundle.js` | Phase 3 verify — 882 lines in app.jsx; 198.0 kb ✅ |
| A-107 | CREATE | `docs/engineering/POST_SCREEN_EXTRACTION_AUDIT.md` | Phase 5 — extraction results, verification checklist, import hygiene map, risk assessment, security review |
| A-108 | APPEND | `docs/engineering/ARCHITECTURE_SCORECARD.md` | Phase 6 — Sprint 4.2C snapshot; quality scores 9.7 → 9.9/10 |
| A-109 | APPEND | `docs/engineering/ACTION_LOG.md` | Phase 7 — A-094 through A-109 |
| A-110 | APPEND | `docs/engineering/DECISION_LOG.md` | Phase 7 — D-026 through D-028 |

---

## Sprint 4.2D

| # | Action | File | Change |
|---|---|---|---|
| A-111 | VERIFY | `src/app.jsx` | Phase 0 — boundary grep: ViewerScreen lines 36–879; ReactDOM at 880; total 882 lines |
| A-112 | VERIFY | `src/app.jsx` | Phase 0 — hook order confirmed (useToast:37 → _setPageRef:53 → useViewerSession:61 → useViewerLayout:82 → render-body:85 → useTextLoader:87 → usePageLoader:96 → useSearchHighlights:107 → useLinksSidecar:115 → useAnnotations:136) |
| A-113 | VERIFY | `src/app.jsx` | Phase 0 — atom audit: only Modal (line 768) and Header (line 162) used as JSX in ViewerScreen body; GateMessage/ToastProvider/ViewerErrorBoundary import-only |
| A-114 | CREATE | `src/screens/ViewerScreen.jsx` | Phase 1 — 872 lines; export function added; 25 imports with ../paths; _setPageRef render-body assignment at line 78; hook order preserved exactly |
| A-115 | BUILD | `dist/app.bundle.js` | Phase 1 verify — 198.0 kb ✅ (with ViewerScreen.jsx added, before app.jsx modification) |
| A-116 | MODIFY | `src/screens/AppShell.jsx` | Phase 2 — added import { ViewerScreen } from './ViewerScreen.jsx'; removed ViewerScreen from props; updated comment |
| A-117 | MODIFY | `src/app.jsx` | Phase 2 — removed all 28 viewer imports, React destructure, section comment, ViewerScreen function (lines 1-879); kept only AppShell import + ReactDOM render call; 882 → 5 lines |
| A-118 | MODIFY | `src/app.jsx` | Phase 2 — render call updated: <AppShell ViewerScreen={ViewerScreen} /> → <AppShell /> |
| A-119 | BUILD | `dist/app.bundle.js` | Phase 3 verify — 198.0 kb ✅ (final extraction build) |
| A-120 | VERIFY | `src/screens/ViewerScreen.jsx` | Phase 3 — circular dep check: ViewerScreen does not import AppShell; AppShell correctly imports ViewerScreen; no cycles |
| A-121 | VERIFY | `src/screens/ViewerScreen.jsx` | Phase 3 — excluded imports confirmed absent: GateMessage, ToastProvider, ViewerErrorBoundary, Sidebar, NavItem; TocSidebar grep false positive explained |
| A-122 | VERIFY | `src/screens/ViewerScreen.jsx` | Phase 4 — verification matrix: 62 scenarios checked; all code paths present; auth/gate, 401 recovery, search, links, annotations, zoom, DRM, panels, bookmarks, text docs, watermark, shimmer verified |
| A-123 | APPEND | `docs/engineering/ARCHITECTURE_SCORECARD.md` | Phase 5 — Sprint 4.2D snapshot; quality score 9.9 → 10/10 |
| A-124 | APPEND | `docs/engineering/DECISION_LOG.md` | Phase 5 — D-029 |
| A-125 | APPEND | `docs/engineering/RISK_REGISTER.md` | Phase 5 — R-055 through R-057 |
| A-126 | CREATE | `docs/engineering/SPRINT4_2D_REPORT.md` | Phase 6 — extraction summary, metrics, verification results, lessons |
| A-127 | CREATE | `docs/engineering/SPRINT4_2E_REPOSITORY_STABILIZATION_PLAN.md` | Phase 6 — next sprint plan |

---

## Sprint 4.2E

| # | Action | File | Change |
|---|---|---|---|
| A-128 | CREATE | `docs/engineering/REPOSITORY_STABILIZATION_AUDIT.md` | Phase 0 — 50-file source inventory; 7 import hygiene findings; git state; 5 dependency findings |
| A-129 | MODIFY | `src/components/access/AccessLog.jsx` | Phase 1 — IH-001: fixed redundant atoms import path (`../../components/atoms.jsx` → `../atoms.jsx`) |
| A-130 | BUILD | `dist/app.bundle.js` | Phase 1 verify — 198.0 kb ✅ (after IH-001 fix) |
| A-131 | CREATE | `docs/architecture/` | Phase 3 — new subdirectory |
| A-132 | CREATE | `docs/security/` | Phase 3 — new subdirectory |
| A-133 | CREATE | `docs/reports/` | Phase 3 — new subdirectory |
| A-134 | CREATE | `docs/risks/` | Phase 3 — new subdirectory |
| A-135 | CREATE | `docs/decisions/` | Phase 3 — new subdirectory |
| A-136 | MOVE | 17 docs from `docs/engineering/` | Phase 3 — ARCHITECTURE_BASELINE, ARCHITECTURE_SCORECARD, DEPENDENCY_AUDIT, REPOSITORY_INVENTORY → architecture/; SECURITY_BASELINE → security/; 10 reports/audits → reports/; RISK_REGISTER → risks/; DECISION_LOG → decisions/ |
| A-137 | CREATE | `docs/engineering/DOCS_MIGRATION_LOG.md` | Phase 3 — migration log documenting 17 moved files and rationale |
| A-138 | APPEND | `docs/architecture/ARCHITECTURE_SCORECARD.md` | Phase 6 — Sprint 4.2E snapshot; quality score 9.9 → 10/10 |
| A-139 | CREATE | `docs/engineering/REPOSITORY_HEALTH_SCORE.md` | Phase 6 — 97/100 score; 5 dimensions; upgrade candidates |
| A-140 | APPEND | `docs/engineering/ACTION_LOG.md` | Phase 7 — A-128 through A-140 |
| A-141 | APPEND | `docs/decisions/DECISION_LOG.md` | Phase 7 — D-031 |
| A-142 | APPEND | `docs/risks/RISK_REGISTER.md` | Phase 7 — R-061 |
| A-143 | CREATE | `docs/engineering/SPRINT4_3_SECURITY_HARDENING_PLAN.md` | Phase 8 — next sprint plan |
