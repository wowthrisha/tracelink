# Engineering Backlog — TraceLink / SecureDoc V14.0

Canonical, deduplicated backlog merging every issue from all six V13.0 reports: `FIXES_TODO.md`, `RELEASE_BLOCKERS.md`, `FINAL_RELEASE_CERTIFICATION.md`, `UI_EXCELLENCE_SCORECARD.md`, `ARCHITECTURE_CERTIFICATION.md`, `CODE_QUALITY_CERTIFICATION.md`. Where the same underlying issue appeared in multiple reports, it is merged into one canonical entry with all source reports cited — no issue is worked twice under two IDs.

Every issue's evidence is classified as exactly one of **Browser verified / Source-code verified / Regression verified / Engineering inference / Not enough evidence**, never mixed, carried forward unchanged from the report(s) it originated in.

Severity scale: **Critical → High → Medium → Low → Enhancement**. Per the V13.0 Tier-0 finding, restated here rather than re-derived: **zero Critical issues exist** — nothing found across all six reports is a confirmed, live-observed defect in core functionality, data isolation, or security enforcement.

---

## HIGH severity

### ENG-001 — Analytics screen clips real data off-screen at the app's own stated minimum width
- **Source reports**: `FIXES_TODO.md` §1
- **Evidence**: Browser verified — at 768px width (the app's own enforced `min-width`), the "Completion" KPI card's right edge measured at x=844.5px via DOM bounding box, 76.5px past the viewport; `document.body.scrollWidth === viewportWidth` with `overflow-x: hidden` confirms zero scroll escape — the content is not degraded, it is unreachable. Source-code verified root cause: `frontend/src/screens/AnalyticsScreen.jsx:339` (`gridTemplateColumns: 'repeat(6,1fr)'`, no responsive fallback) and `:390` (`'3fr 1fr'`, same issue), inconsistent with the file's own working pattern at line 272 (`repeat(auto-fill, minmax(220px, 1fr))`).
- **Affected files**: `frontend/src/screens/AnalyticsScreen.jsx` (lines 339, 344, 390)
- **Estimated effort**: Small (CSS-only change, no logic/data changes)
- **Regression risk**: Low — isolated to grid-template-columns values; no state/behavior touched
- **Dependencies**: None
- **Priority**: 1
- **Status**: **Closed** (2026-07-26) — see `docs/engineering/FIX_LOG.md` "Sprint V14.0 — ENG-001"
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified re-check at 768px, 834px, 1440px via local Docker stack — confirmed no element's bounding-box right edge exceeds viewport width at any of the three; zero regressions in either test suite (backend 1708/1708, frontend 13/13)

### ENG-002 — Notifications / Activity Feed cannot identify which document had activity
- **Source reports**: `FIXES_TODO.md` §2
- **Evidence**: Source-code verified — `NotificationsScreen.jsx` `eventDetail()` (lines 59-66) checks `ev.document_title`, `ev.viewer_email`, `ev.ip_address`, `ev.country`. Browser verified via raw API response (`GET /api/analytics/events?limit=50&offset=0`): actual payload contains `event_type`, `page_number`, `link_id`, `ip_hash`, `session_id`, `created_at` — **no `document_title` field exists**, and `ip_hash` ≠ `ip_address` so that check silently never matches either. `page_number`, which is present, is never displayed.
- **Affected files**: `backend/app/routers/analytics.py` (or wherever `/api/analytics/events` is served — needs a join to include document title), `frontend/src/screens/NotificationsScreen.jsx` (lines 23-66)
- **Estimated effort**: Medium (requires a backend query join, not just a frontend fix)
- **Regression risk**: Low-Medium — touches a real query path; must confirm the join doesn't change response shape for other consumers of the same endpoint
- **Dependencies**: None
- **Priority**: 2
- **Status**: Open
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — trigger a fresh page-view event on a named test document, confirm the Notifications feed shows that document's name/title in the entry; regression-verified — full backend test suite re-run after the query change

### ENG-003 — Cross-account IDOR: architecturally sound, never proven live
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 1 item 1, `SECURITY_CERTIFICATION.md` §2 (referenced), `FINAL_RELEASE_CERTIFICATION.md`
- **Evidence**: Source-code verified — every resource-scoped router filters `WHERE {Resource}.user_id == current_user_id` (or org-membership join). **Not enough evidence** for the live claim — only one real test account existed as of V13.0, so cross-tenant access was never exercised end-to-end. Explicitly flagged in `RELEASE_BLOCKERS.md` as "the single largest gap in this sprint's security work."
- **Affected files**: None (verification task, not a code-change task, unless a defect is actually found)
- **Estimated effort**: Small (create a second disposable test account, attempt cross-account access to Account A's resources by ID, observe result)
- **Regression risk**: None (read-only verification against disposable test data)
- **Dependencies**: Requires creating a second real account — evaluate whether this is safe/appropriate to do against the live production instance before proceeding
- **Priority**: 3
- **Status**: Open
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — attempt to fetch/modify Account A's document/link/API-key by ID while authenticated as Account B; expect 404 on every resource type per the existing query-scoping pattern

---

## MEDIUM severity

### ENG-004 — Share-link document picker cannot disambiguate identically-named documents
- **Source reports**: `FIXES_TODO.md` §3
- **Evidence**: Source-code verified — `frontend/src/components/DocumentPicker.jsx:63-68` renders only `d.filename`, `d.page_count`, `d.total_views` — no `d.created_at`, no ID — inconsistent with the Upload/Storage tables elsewhere in the app, which both show a truncated ID for exactly this reason.
- **Affected files**: `frontend/src/components/DocumentPicker.jsx`
- **Estimated effort**: Small
- **Regression risk**: Low — additive UI change only
- **Dependencies**: None
- **Priority**: 4
- **Status**: Open
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — confirm two same-named documents now render distinguishable rows (date or ID visible)

### ENG-005 — 5 of 6 list endpoints have no pagination
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 2 item 3, `SCALABILITY_CERTIFICATION.md` §1
- **Evidence**: Source-code verified. Priority originally scoped "Before 10,000 users" — not urgent at current per-account volumes, but a real, unbounded-cost query pattern.
- **Affected files**: List endpoints in `backend/app/routers/` (documents, links, api_keys, webhooks — exact set per `SCALABILITY_CERTIFICATION.md` §1)
- **Estimated effort**: Medium (cursor/offset pagination + frontend consumers updated to page through results)
- **Regression risk**: Medium — changes response shape for list endpoints; every frontend consumer must be updated in the same change
- **Dependencies**: None
- **Priority**: 5
- **Status**: Deferred — scoped to "before 10,000 users," current account volumes don't warrant the response-shape churn risk this sprint. Revisit when approaching that threshold.
- **Blocked by**: None
- **Owner**: Unassigned
- **Verification method**: Regression-verified (full test suite) + Browser-verified (existing list screens still render correctly post-pagination)

### ENG-006 — Storage call sites' blocking-I/O safety not exhaustively re-audited
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 2 item 4, `SCALABILITY_CERTIFICATION.md` §9
- **Evidence**: Engineering inference — flagged specifically because this exact bug class (synchronous boto3 calls blocking the async event loop) already caused one confirmed real issue in this codebase (fixed in `viewer.py`'s download path, V4.0). Not confirmed to still exist elsewhere — flagged as an unaudited risk, not a found defect.
- **Affected files**: `backend/app/services/storage_service.py` and all call sites (full audit needed to enumerate)
- **Estimated effort**: Small (verification/audit) — Medium if any additional instances are found and need `run_in_executor` fixes
- **Regression risk**: Low for the audit itself; Medium if fixes are needed (touches request-handling code)
- **Dependencies**: None
- **Priority**: 6
- **Status**: Open
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Source-code verified — grep every `StorageService`/boto3 call site, confirm each async-context call is wrapped in `run_in_executor` or is already using an async client

---

## LOW severity

### ENG-007 — Audit Log "Details" column is reachable but has no scroll affordance
- **Source reports**: `FIXES_TODO.md` §4
- **Evidence**: Browser verified — content is NOT lost (ancestor `overflow-x: auto` div has real scrollable width: `scrollWidth: 667` vs `clientWidth: 624`), but nothing signals the column continues off-screen at narrower widths.
- **Affected files**: `frontend/src/components/access/AccessLog.jsx` or wherever the Audit Log table renders (verify exact file at implementation time)
- **Estimated effort**: Small
- **Regression risk**: Low — cosmetic/CSS addition
- **Dependencies**: None
- **Priority**: 7
- **Status**: Open
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified at 768-900px widths — confirm a visible scroll-shadow/fade appears when the table overflows

### ENG-008 — Rate-limit boundary (429 at request 21) never empirically confirmed
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 1 item 2, `SECURITY_CERTIFICATION.md` §4
- **Evidence**: Source-code verified (limit exists, `viewer.py:158`, `20/minute`, Redis-backed). Not enough evidence for the live trigger boundary — deliberately not pushed to avoid generating artificial traffic in earlier sprints.
- **Affected files**: None (verification only)
- **Estimated effort**: Small
- **Regression risk**: None if bounded to exactly 21 requests against a disposable test link
- **Dependencies**: None
- **Priority**: 8
- **Status**: Open
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — 21 bounded requests against one disposable test link, confirm 429 on request 21, not before or after

### ENG-009 — XSS not individually tested on fields beyond link labels
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 1 item 3, `SECURITY_CERTIFICATION.md` §5
- **Evidence**: Security inference only for untested fields (document filenames, org names, webhook descriptions, API key names) — same JSX pipeline verified safe for link labels, no `dangerouslySetInnerHTML` found in a repo grep, but each field not individually proven.
- **Affected files**: None expected (verification only, unless a gap is found)
- **Estimated effort**: Small
- **Regression risk**: None (read-only verification, disposable test values)
- **Dependencies**: None
- **Priority**: 9
- **Status**: Open
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — same payload pattern used for link labels (`<img src=x onerror=alert(1)>`), applied to each remaining field, confirm inert rendering and zero injected DOM nodes

### ENG-010 — Expired-link enforcement not live-browser-confirmed
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 1 item 4, `UI_EXCELLENCE_SCORECARD.md` (Viewer section)
- **Evidence**: Source-code verified — identical code path (`_check_link_active`, `viewer_service.py:26-35`) and status code as the revoked-link path, which WAS browser-verified. Not enough evidence for the expiry branch specifically, since the dashboard UI only supports date-granularity expiry (earliest achievable value is end-of-current-day).
- **Affected files**: None expected for a fix; possibly `frontend/src/screens/AccessScreen.jsx` if datetime-granularity expiry is added as a byproduct
- **Estimated effort**: Small if tested via direct API call with a short ISO-datetime expiry on a disposable test link (legitimate use of one's own account's API, not a UI change); Medium if the UI itself is extended to support time-of-day granularity
- **Regression risk**: None for the verification path
- **Dependencies**: None
- **Priority**: 10
- **Status**: Open
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — create a disposable link via the app's own API with `expires_at` ~60-90 seconds in the future, wait it out, confirm 410 on access attempt

### ENG-011 — DB connection pooling has no cluster-wide budget across replicas
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 2 item 1, `SCALABILITY_CERTIFICATION.md` §2/§11, `ARCHITECTURE_CERTIFICATION.md` §8
- **Evidence**: Source-code verified — safe today (deployment is effectively single-replica); becomes a real risk only if a second API replica is added without addressing pool sizing across replicas.
- **Affected files**: `backend/app/config.py` (pool_size/max_overflow), deployment configuration
- **Estimated effort**: Medium (requires either a pooler like PgBouncer or coordinated per-replica sizing math)
- **Regression risk**: Medium — connection pool changes affect every request path
- **Dependencies**: None
- **Priority**: 11
- **Status**: Deferred — explicitly scoped to "before running >1 API replica," which this deployment is not doing today. Revisit before any horizontal-scaling change.
- **Blocked by**: A decision to horizontally scale (external, not an engineering task)
- **Owner**: Unassigned
- **Verification method**: N/A until scaling decision is made

### ENG-012 — Process-local viewer cache has no cross-process invalidation broadcast
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 2 item 2, `SCALABILITY_CERTIFICATION.md` §6, `ARCHITECTURE_CERTIFICATION.md` §3
- **Evidence**: Source-code verified — deliberate, documented tradeoff (module's own docstring). Bounded ≤10s staleness for link/permission changes only; revocation is unaffected (already TTL-independent and browser-verified).
- **Affected files**: `backend/app/services/viewer_cache.py`
- **Estimated effort**: Large (requires a pub/sub invalidation mechanism, e.g., Redis pub/sub, across processes)
- **Regression risk**: Medium-High — touches the viewer hot path directly
- **Dependencies**: None
- **Priority**: 12
- **Status**: Deferred — only matters if horizontally scaled AND a customer has a hard requirement for provably-instant (not ≤10s) propagation. Neither condition currently holds. Re-open if either changes.
- **Blocked by**: A customer requirement or a scaling decision (external)
- **Owner**: Unassigned
- **Verification method**: N/A until triggering condition arises

---

## ENHANCEMENT (non-blocking)

### ENG-013 — No frontend equivalent of `ruff` for unused-import detection
- **Source reports**: `CODE_QUALITY_CERTIFICATION.md` §6, `RELEASE_BLOCKERS.md` Tier 3 item 1
- **Evidence**: Source-code verified gap (tooling absence, not a found defect)
- **Affected files**: `frontend/` tooling config (would need ESLint + `no-unused-vars` or equivalent)
- **Estimated effort**: Medium (tool setup + first-pass cleanup of whatever it finds)
- **Regression risk**: Low for setup; depends on findings for any resulting cleanup
- **Priority**: 13
- **Status**: Open — good candidate for this sprint's repository-quality pass if time permits
- **Owner**: Engineering (this sprint, if time permits)
- **Verification method**: Regression-verified (full frontend test suite + build) after any resulting cleanup

### ENG-014 — Systematic duplicate-code scan never run
- **Source reports**: `CODE_QUALITY_CERTIFICATION.md` §4
- **Evidence**: Not enough evidence — no `jscpd`-equivalent scan has been run; only the one already-known instance (ENG-015) is on record.
- **Affected files**: TBD pending scan
- **Estimated effort**: Small (run a scan), effort for any resulting fixes TBD
- **Priority**: 14
- **Status**: Open
- **Owner**: Engineering (this sprint, if time permits)
- **Verification method**: Source-code verified scan output

### ENG-015 — Duplicated 7-key `permissions` dict (AccessScreen.jsx / viewer_session_service.py)
- **Source reports**: `ARCHITECTURE_CERTIFICATION.md` §5 (AD-7), `CODE_QUALITY_CERTIFICATION.md` §4, `RELEASE_BLOCKERS.md` Tier 3 item 3
- **Evidence**: Source-code verified. This is a **deliberate, previously-recorded decision** (V11.0, `ARCHITECTURE_DECISIONS.md` AD-7) — extended rather than consolidated, with rationale on record.
- **Affected files**: `frontend/src/screens/AccessScreen.jsx`, `backend/app/services/viewer_session_service.py`
- **Estimated effort**: Medium if reopened
- **Regression risk**: Medium — touches the permission-check path on both frontend and backend
- **Priority**: 15
- **Status**: Explicitly justified, not re-litigated. Will only reopen this decision if consolidating measurably reduces complexity without regression risk — re-evaluate during this sprint's system-design pass, do not change by default.
- **Owner**: Engineering (evaluate only, this sprint)
- **Verification method**: N/A unless reopened

### ENG-016 — `AccessScreen.jsx` oversized (~900 lines)
- **Source reports**: `ARCHITECTURE_CERTIFICATION.md` §5 (M-13), `CODE_QUALITY_CERTIFICATION.md` §5, `RELEASE_BLOCKERS.md` Tier 3 item 2
- **Evidence**: Source-code verified. Long-standing, deliberately deferred refactor (`ISSUE_DATABASE.md` M-13).
- **Affected files**: `frontend/src/screens/AccessScreen.jsx`
- **Estimated effort**: Large (component decomposition)
- **Regression risk**: Medium-High — large surface area, high chance of subtle behavior changes during extraction
- **Priority**: 16
- **Status**: Deferred — explicitly a large-refactor deferral from a prior sprint. Will only take this on this sprint if all higher-priority items close with time remaining, per "never optimise for speed" but also per not introducing unnecessary regression risk late in a certification sprint.
- **Owner**: Unassigned
- **Verification method**: Regression-verified (full suite) + Browser-verified (every AccessScreen workflow re-tested) if undertaken

### ENG-017 — Observability wiring (Prometheus scrape/alerting) unconfirmed
- **Source reports**: `ARCHITECTURE_CERTIFICATION.md` §7, `RELEASE_BLOCKERS.md` Tier 3 item 4
- **Evidence**: Source-code verified that metrics are instrumented (`app/metrics.py`). Not enough evidence that they're actually scraped/alerted on in production — this is an infrastructure/operations question, not purely a code question.
- **Affected files**: None (deployment/ops verification, not a code change)
- **Estimated effort**: Small (verification only, if access to Railway/monitoring config is available)
- **Priority**: 17
- **Status**: Open — likely outside this sprint's code-focused scope; flag to the account owner rather than resolve in-repo
- **Owner**: Unassigned
- **Verification method**: Not enough evidence until infrastructure access is confirmed

### ENG-018 — Large-PDF (100+ page) Viewer stress not freshly re-tested
- **Source reports**: `UI_EXCELLENCE_SCORECARD.md` (Viewer section), `RELEASE_BLOCKERS.md` Tier 3 item 5
- **Evidence**: Not enough evidence — this sprint's Viewer work prioritized the explicitly-named edge cases (idle/multi-tab/expired/network/broken-PDF) over a fresh large-document stress pass.
- **Affected files**: None expected unless a defect is found
- **Estimated effort**: Small (test with an existing or synthesized 100+ page PDF)
- **Priority**: 18
- **Status**: Open — part of this sprint's Viewer certification pass (see Viewer Certification section of the V14.0 mission)
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — upload/open a 100+ page PDF, verify rendering, search, page nav, and Reading Intelligence metrics all remain correct at that scale

### ENG-019 — Dashboard screens' individual modals/toggles not re-exercised element-by-element this specific sprint
- **Source reports**: `UI_EXCELLENCE_SCORECARD.md` (Dashboard screens section)
- **Evidence**: Not enough evidence for exhaustive per-element re-verification this specific sprint (prior sprints cover this ground; V13.0 focused fresh-load verification + the Viewer). No known defect implied.
- **Affected files**: TBD pending pass
- **Estimated effort**: Medium (systematic pass across ~10 screens)
- **Priority**: 19
- **Status**: Open — part of this sprint's UI Excellence re-review
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified, screen by screen

### ENG-020 — Reading Intelligence metrics not independently hand-verified against backend math this sprint
- **Source reports**: `UI_EXCELLENCE_SCORECARD.md` (Viewer section)
- **Evidence**: Engineering inference only — no placeholder/stale values observed, but displayed values (remaining-time prediction, average page time, difficulty indicators, engagement scores) were not independently recomputed by hand against backend data this specific sprint.
- **Affected files**: `backend/app/services/reading_analytics_service.py`, Viewer frontend components displaying these metrics
- **Estimated effort**: Medium (requires reading the calculation source and cross-checking against live displayed values for a controlled test session)
- **Priority**: 20
- **Status**: Open — part of this sprint's Reading Intelligence certification
- **Owner**: Engineering (this sprint)
- **Verification method**: Source-code verified (read calculation logic) + Browser-verified (cross-check against a controlled live reading session's actual displayed numbers)

---

## Explicitly not on this backlog (verified non-issues)

- **Storage screen usage bars** (`FIXES_TODO.md` §5) — investigated and ruled out; the fill-bar computation is correct (`width: 0.0032554%` for a 328-byte file, verified via DOM inline-style inspection). An earlier automated check mismeasured the empty track div. No action needed.
- **AD-6 (unreachable 640px CSS breakpoint)** — deliberate, previously-recorded non-fix pending a product decision about mobile support scope (`ARCHITECTURE_DECISIONS.md`). Not re-litigated without that product decision being reopened first.
- **Test-data debris in the live QA account** (`FIXES_TODO.md` §6) — not a code defect; an operational cleanup item for the test account itself, tracked separately from the engineering backlog.

---

## Summary table

| ID | Title | Severity | Priority | Status |
|---|---|---|---|---|
| ENG-001 | Analytics screen clips data at 768px | High | 1 | **Closed** |
| ENG-002 | Notifications feed lacks document identity | High | 2 | Open |
| ENG-003 | Cross-account IDOR unverified live | High | 3 | Open |
| ENG-004 | Document picker can't disambiguate duplicates | Medium | 4 | Open |
| ENG-005 | List endpoints lack pagination | Medium | 5 | Deferred |
| ENG-006 | Storage blocking-I/O sites unaudited | Medium | 6 | Open |
| ENG-007 | Audit Log scroll affordance missing | Low | 7 | Open |
| ENG-008 | Rate-limit 429 boundary unconfirmed | Low | 8 | Open |
| ENG-009 | XSS untested beyond link labels | Low | 9 | Open |
| ENG-010 | Expired-link live confirmation missing | Low | 10 | Open |
| ENG-011 | Connection pooling cluster budget | Low | 11 | Deferred |
| ENG-012 | Cache invalidation broadcast | Low | 12 | Deferred |
| ENG-013 | No frontend lint tooling | Enhancement | 13 | Open |
| ENG-014 | No duplicate-code scan run | Enhancement | 14 | Open |
| ENG-015 | Duplicated permissions dict (AD-7) | Enhancement | 15 | Justified, not changed |
| ENG-016 | AccessScreen.jsx oversized (M-13) | Enhancement | 16 | Deferred |
| ENG-017 | Observability wiring unconfirmed | Enhancement | 17 | Open (ops, not code) |
| ENG-018 | Large-PDF stress not retested | Enhancement | 18 | Open |
| ENG-019 | Dashboard modals not re-exercised | Enhancement | 19 | Open |
| ENG-020 | Reading Intelligence hand-verification | Enhancement | 20 | Open |

**Critical: 0. High: 3. Medium: 3. Low: 6. Enhancement: 8.**
