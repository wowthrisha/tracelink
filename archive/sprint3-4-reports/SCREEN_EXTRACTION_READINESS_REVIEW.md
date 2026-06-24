> **HISTORICAL ARCHIVE** — Sprint milestone record. Reflects state at time of writing. Not current state.

# Screen Extraction Readiness Review
Sprint 4.1 — Phase 4
Date: 2026-06-18

DO NOT EXTRACT SCREENS IN THIS SPRINT. This is a readiness analysis only.

---

## 1. Screen Dependency Graph

```
App (root)
├── LoginScreen      ← onLogin callback
├── ViewerScreen     ← doc, publicToken, onSelectDoc (+ 8 hooks)
├── AccessScreen     ← doc, onSelectDoc
├── AnalyticsScreen  ← (no props)
├── StorageScreen    ← (no props)
└── BillingScreen    ← onPlanChange callback

ToastProvider wraps all screens.
parseJwtEmail() (module-level helper at line 2562) is used only by App.
authHeaders() is defined INSIDE BillingScreen — must move with the screen.
```

---

## 2. State Ownership Map

| Screen | State Variables | Count | Notes |
|---|---|---|---|
| `LoginScreen` | mode, resetToken, email, password, newPassword, loading, error, info | 8 | `mode` init reads URL hash for password-reset flow |
| `BillingScreen` | billing, loading, actionLoading, error | 4 | `authHeaders()` is an inner function — must migrate |
| `StorageScreen` | dashboard, forecast, loading, updatingId | 4 | `fmtBytes()` and `lifecycleBadge()` are inner helpers |
| `AnalyticsScreen` | range, analyticsTab, overview, docStats, groupStats, analyticsLoading, selectedHeatmapDoc, heatmapData, heatmapLoading | 9 | All sub-components extracted (Sprint 4.1) |
| `UploadScreen` | dragging, uploading, progress, uploadDone, uploadedDoc, search, deleteModal, docs, overview, docsLoading, deleting, groups, activeGroupFilter, selectedGroupId, groupModal, groupForm, groupSaving, retentionPolicy | 18 | fileRef, pollRef (refs); polling loop up to 5 min |
| `AccessScreen` | tab, links, linksLoading, creating, revokeModal, revoking, linkCopied, saved, feedbackItems, feedbackLoading, feedbackFilter, feedbackViewerFilter, feedbackDateFrom, feedbackDateTo, feedbackPage, feedbackRoleFilter, feedbackReviewerFilter, feedbackReviewers, feedbackFiltersOpen, feedbackAdvancedOpen, replyDraft, replyText, visualAnnotations, visualLoading, visualTypeFilter, password, showPass, expiry, maxViews, maxConcurrentSessions, allowedEmails, allowedDomains, ipAllowlist, label_txt, permissions | ~35 | AccessLog still inline (has own API call) |
| `ViewerScreen` | showInfo, showSearch, showToc, showLaser, showMagnifier, showInsights, insightsData, insightsLoading, showLinks, showPageList + all hook state | ~10 direct | 8 custom hooks add ~30 more state variables |
| `App` | token, screen, activeDoc, plan | 4 | Screen router only |

---

## 3. Context Usage Map

| Screen | useToast | ToastProvider | localStorage | sessionStorage |
|---|---|---|---|---|
| `App` | ✗ | wraps all | R/W `securedoc_token` | — |
| `LoginScreen` | ✗ | ✗ | W `securedoc_token` | — |
| `BillingScreen` | ✗ | ✗ | R `securedoc_token` (in authHeaders) | — |
| `StorageScreen` | ✓ | ✗ | — | — |
| `AnalyticsScreen` | ✓ | ✗ | — | — |
| `UploadScreen` | ✓ | ✗ | — | — |
| `AccessScreen` | ✓ | ✗ | — | — |
| `ViewerScreen` | ✓ | ✗ | — | R/W `securedoc_sess_*` (via useViewerSession) |

**Key insight:** LoginScreen and BillingScreen do NOT use useToast. They use local `error`/`info` state for UI feedback. This simplifies their extraction.

---

## 4. API Ownership Map

| Screen | API Calls | Pattern | Count |
|---|---|---|---|
| `LoginScreen` | auth, forgotPassword, resetPassword | `window.SecureDocAPI.*` | 3 |
| `BillingScreen` | /api/billing/status, /api/billing/checkout, /api/billing/portal | raw `fetch()` with `authHeaders()` | 3 |
| `StorageScreen` | getStorageDashboard, getStorageForecast, updateRetention | `window.SecureDocAPI.*` | 3 |
| `AnalyticsScreen` | getAnalyticsOverview, getDocumentAnalytics, getGroupAnalytics, getPageHeatmap | `window.SecureDocAPI.*` | 4 |
| `UploadScreen` | getDocuments, getAnalyticsOverview, getGroups, upload, poll, deleteDoc, reprocessDoc, createGroup, updateGroup, deleteGroup, assignDocGroup | `window.SecureDocAPI.*` | ~11 |
| `AccessScreen` | getLinks, createLink, revokeLink, getFeedback, getFeedbackReviewers, replyToFeedback, getVisualAnnotations, exportVisualAnnotations | `window.SecureDocAPI.*` | 8 |
| `ViewerScreen` | via hooks (page images, text, search, annotations, links, session) | hook-abstracted | ~8 |
| `App` | — | — | 0 |

**BillingScreen anomaly:** Uses raw `fetch()` instead of `window.SecureDocAPI.*`. Must carry `authHeaders()` function when extracted.

---

## 5. Toast Usage Map

| Screen | Toast calls | Triggers |
|---|---|---|
| `StorageScreen` | error, success | API failures, retention update |
| `AnalyticsScreen` | error, success | API failure, CSV export |
| `UploadScreen` | error, success, info | Upload errors, file processing, group operations |
| `AccessScreen` | error, success, info | Link CRUD, feedback, revoke, reply |
| `ViewerScreen` | error, info, warning | Page load errors, DRM events, session errors |
| `LoginScreen` | — | Uses local `error` and `info` state |
| `BillingScreen` | — | Uses local `error` state |

---

## 6. AccessLog Readiness Assessment

`AccessLog` (lines 1992–2041 in the pre-Sprint-4.1 app.jsx, now ~1812–1862) is still inline in the AccessScreen region of app.jsx.

**Profile:**
- Props: `docId` (string)
- State: `events` (array), `loading` (boolean)
- Context: `useToast()`
- API: `window.SecureDocAPI.getEvents(docId, 50)`
- Atoms: `Card`, `SectionLabel`, `Chip`, `Btn`, `RiskBadge`, `label()` from atoms.jsx
- React: `useState`, `useCallback`, `useEffect`

**Assessment:** MEDIUM risk. AccessLog is effectively a self-contained sub-screen with its own API call and context. It CAN be extracted as `components/access/AccessLog.jsx` following the DocumentPicker pattern (which also uses useToast). The extraction is low-risk — all its deps are importable and it has no shared state with AccessScreen. Recommend extraction in Sprint 4.2 Phase 1 (before AccessScreen extraction, to reduce AccessScreen's complexity).

**Blocker:** None. Ready for extraction in Sprint 4.2.

---

## 7. Risk Ranking

| Screen | LOC est. | State vars | API calls | Risk | Blocker |
|---|---|---|---|---|---|
| `App` | ~90 | 4 | 0 | LOW | None — but extract last (needs all screens as imports) |
| `LoginScreen` | ~235 | 8 | 3 | LOW | URL hash parsing for reset flow; localStorage write |
| `BillingScreen` | ~195 | 4 | 3 | LOW-MEDIUM | raw fetch + local authHeaders(); must migrate together |
| `StorageScreen` | ~155 | 4 | 3 | LOW-MEDIUM | Two inner helpers (fmtBytes, lifecycleBadge) must migrate |
| `AnalyticsScreen` | ~350 | 9 | 4 | MEDIUM | Sub-components already extracted ✓ |
| `UploadScreen` | ~380 | 18 | 11 | MEDIUM-HIGH | fileRef, pollRef, 5-min polling loop, 18 state vars |
| `AccessScreen` | ~700 | ~35 | 8 | HIGH | AccessLog still inline; 35 state vars; 8 API endpoints |
| `ViewerScreen` | ~700 | ~40 (incl. hooks) | via 8 hooks | VERY HIGH | Ref patterns, hook circular deps, session lifecycle |

---

## 8. Recommended Extraction Order

```
Sprint 4.2 Phase 1  → App                 (router shell, extract first to define entry point)
Sprint 4.2 Phase 2  → LoginScreen         (smallest, no toast, 8 state vars)
Sprint 4.2 Phase 3  → BillingScreen       (4 state vars, carry authHeaders)
Sprint 4.2 Phase 4  → StorageScreen       (4 state vars, carry fmtBytes/lifecycleBadge)
Sprint 4.2 Phase 5  → AnalyticsScreen     (sub-components done, manageable)
Sprint 4.2 Phase 6  → AccessLog           (extract before AccessScreen to reduce its scope)
Sprint 4.2 Phase 7  → UploadScreen        (complex but all sub-components done)
Sprint 4.2 Phase 8  → AccessScreen        (AccessLog extracted first; still large)
Sprint 4.2 Phase 9  → ViewerScreen        (last — highest risk, most hook complexity)
```

**Expected LOC reduction from Sprint 4.2:** ~2,800 lines from app.jsx. Target: < 300 lines remaining (just imports + ReactDOM.render call).

---

## 9. Pre-Extraction Checklist (for Sprint 4.2)

Before extracting each screen:
- [ ] Read current state of app.jsx section (line numbers shift per sprint)
- [ ] Verify all sub-components are already extracted or will be extracted first
- [ ] Identify all `_errMsg` call sites → import from utils/viewer.js in extracted file
- [ ] Identify all `useToast` uses → import from contexts/toast.jsx in extracted file
- [ ] Identify all atom uses → import from components/atoms.jsx in extracted file
- [ ] Check for any module-level helpers referenced → extract to utils/ or carry into screen file
- [ ] Build after each extraction before proceeding to next screen
- [ ] Use Python bottom-to-top deletion for app.jsx inline blocks
- [ ] DO NOT use walk-back heuristics for any section-header comment blocks with `═` or `─` chars
