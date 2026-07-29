# Engineering Backlog — TraceLink / SecureDoc V14.0

Canonical, deduplicated backlog merging every issue from all six V13.0 reports: `FIXES_TODO.md`, `RELEASE_BLOCKERS.md`, `FINAL_RELEASE_CERTIFICATION.md`, `UI_EXCELLENCE_SCORECARD.md`, `ARCHITECTURE_CERTIFICATION.md`, `CODE_QUALITY_CERTIFICATION.md`. Where the same underlying issue appeared in multiple reports, it is merged into one canonical entry with all source reports cited — no issue is worked twice under two IDs.

Every issue's evidence is classified as exactly one of **Browser verified / Source-code verified / Regression verified / Engineering inference / Not enough evidence**, never mixed, carried forward unchanged from the report(s) it originated in.

Severity scale: **Critical → High → Medium → Low → Enhancement**. Per the V13.0 Tier-0 finding, restated here rather than re-derived: **zero Critical issues exist** — nothing found across all six reports is a confirmed, live-observed defect in core functionality, data isolation, or security enforcement.

**Status as of 2026-07-27 09:30**: High and Medium tiers closed and re-verified. **Low tier fully actioned** (ENG-007/008/009/010/021 fixed or verified with no defect, ENG-011/012 deferrals re-confirmed) and re-verified in a dedicated post-tier regression pass (10 screens zero errors, both key fixes re-confirmed with fresh logins). Every "Not enough evidence" gap from the original security review is now live-confirmed. Zero regressions across both test suites at every checkpoint. Proceeding to Enhancement tier.

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
- **Affected files**: `backend/app/routers/analytics.py`, `frontend/src/screens/NotificationsScreen.jsx`
- **Estimated effort**: Medium (requires a backend query join, not just a frontend fix)
- **Regression risk**: Low-Medium — touches a real query path; must confirm the join doesn't change response shape for other consumers of the same endpoint
- **Dependencies**: None
- **Priority**: 2
- **Status**: **Closed** (2026-07-26) — see `docs/engineering/FIX_LOG.md` "Sprint V14.0 — ENG-002"
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — real share link created on local Docker stack, real page-view events generated anonymously, confirmed Notifications feed shows document name + page number on every entry; regression-verified — both test suites re-run unchanged (1708 backend, 13 frontend)

### ENG-003 — Cross-account IDOR: architecturally sound, never proven live
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 1 item 1, `SECURITY_CERTIFICATION.md` §2 (referenced), `FINAL_RELEASE_CERTIFICATION.md`
- **Evidence**: Source-code verified — every resource-scoped router filters `WHERE {Resource}.user_id == current_user_id` (or org-membership join). **Not enough evidence** for the live claim — only one real test account existed as of V13.0, so cross-tenant access was never exercised end-to-end. Explicitly flagged in `RELEASE_BLOCKERS.md` as "the single largest gap in this sprint's security work."
- **Affected files**: None — verification confirmed the existing pattern is sound; no defect found, no code change needed
- **Estimated effort**: Small (create a second disposable test account, attempt cross-account access to Account A's resources by ID, observe result)
- **Regression risk**: None (read-only/reverted verification against disposable test data)
- **Dependencies**: Requires creating a second real account — resolved by testing against the **local Docker stack** (separate local database, same shared Supabase auth project) rather than production, so zero production risk
- **Priority**: 3
- **Status**: **Closed** (2026-07-26) — see `docs/engineering/ACTION_LOG.md` Entry 11. **No defect found.**
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser/API-verified — created a second real account (`eng003.idor.test2@mailinator.com`, confirmed via its own signup email), authenticated as Account B, and directly attempted: `GET /api/documents/{A_doc_id}` → 404; `GET /api/documents/{A_doc_id}/status` → 404; `GET/DELETE /api/api-keys/{A_key_id}` → 404; `GET /api/links?document_id={A_doc_id}` → 404; `PATCH/DELETE/DELETE-hard /api/links/{A_link_id}` → 403. Account B's own document list does not contain Account A's document ID. Confirmed Account A's document, link, and API key were all still present and unmodified after every attempt.

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
- **Status**: **Closed** (2026-07-26) — see `docs/engineering/FIX_LOG.md` "Sprint V14.0 — ENG-004"
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — confirmed both of Account A's local documents now render an "uploaded {date}" line using the app's existing `fmtDate()` formatter; zero layout regression; both test suites unchanged

### ENG-005 — 5 of 6 list endpoints have no pagination
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 2 item 3, `SCALABILITY_CERTIFICATION.md` §1
- **Evidence**: Source-code verified. Priority originally scoped "Before 10,000 users" — not urgent at current per-account volumes, but a real, unbounded-cost query pattern.
- **Affected files**: List endpoints in `backend/app/routers/` (documents, links, api_keys, webhooks — exact set per `SCALABILITY_CERTIFICATION.md` §1)
- **Estimated effort**: Medium (cursor/offset pagination + frontend consumers updated to page through results)
- **Regression risk**: Medium — changes response shape for list endpoints; every frontend consumer must be updated in the same change
- **Dependencies**: None
- **Priority**: 5
- **Status**: **Deferral re-confirmed** (2026-07-26 18:20) — see note below. Still Deferred.
- **Blocked by**: None
- **Owner**: Unassigned
- **Verification method**: Regression-verified (full test suite) + Browser-verified (existing list screens still render correctly post-pagination)

**Re-confirmation note**: before moving past this item to ENG-006, explicitly re-checked rather than silently carried the deferral forward. Attempted to re-fetch a current production document count for an updated data point; the saved production session token had expired and re-authenticating solely to refresh this count was judged disproportionate — no new customer onboarding occurred during this sprint, so the order of magnitude (`~30 documents`, per `SCALABILITY_CERTIFICATION.md` §1, captured earlier the same day) has not materially changed. **Not enough evidence** for an updated exact count; **Engineering inference** that the underlying decision is unaffected — the response-shape churn risk across 5 endpoints and their frontend consumers still clearly outweighs a currently-nonexistent performance symptom. Deferral stands.

### ENG-006 — Storage call sites' blocking-I/O safety not exhaustively re-audited
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 2 item 4, `SCALABILITY_CERTIFICATION.md` §9
- **Evidence**: Engineering inference — flagged specifically because this exact bug class (synchronous boto3 calls blocking the async event loop) already caused one confirmed real issue in this codebase (fixed in `viewer.py`'s download path, V4.0). Not confirmed to still exist elsewhere — flagged as an unaudited risk, not a found defect.
- **Affected files**: `backend/app/services/storage.py` (audited, no changes needed)
- **Estimated effort**: Small (verification/audit) — Medium if any additional instances are found and need `run_in_executor` fixes
- **Regression risk**: None — no code changed, audit found the pattern already correct
- **Dependencies**: None
- **Priority**: 6
- **Status**: **Closed** (2026-07-26) — **no defect found**
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Source-code verified — all boto3 usage confined to `services/storage.py` (confirmed via repo-wide grep, one false-positive match in `workers/pipeline/pdf.py` was PyPDF's unrelated `get_object()` method, not S3, and that file runs in the Celery worker, not the async API event loop anyway). All 6 methods (`upload_file`, `download_bytes`, `delete_file`, `list_keys_with_prefix`, `file_exists`, `generate_presigned_url`) correctly wrap their boto3 call in `run_in_executor(_STORAGE_EXECUTOR, ...)` — confirmed by direct read, not assumed. The module's own docstring already documents this as a deliberate contract ("Consistent use of _STORAGE_EXECUTOR for all S3 operations"), and the code lives up to it.

---

## LOW severity

### ENG-007 — Audit Log "Details" column is reachable but has no scroll affordance
- **Source reports**: `FIXES_TODO.md` §4
- **Evidence**: Browser verified — content is NOT lost (ancestor `overflow-x: auto` div has real scrollable width: `scrollWidth: 667` vs `clientWidth: 624`), but nothing signals the column continues off-screen at narrower widths.
- **Affected files**: `frontend/src/screens/AuditLogScreen.jsx` (confirmed exact file at implementation time — not `components/access/AccessLog.jsx` as originally guessed)
- **Estimated effort**: Small
- **Regression risk**: Low — additive UI change (scroll wrapper + conditional fade), no existing behavior altered
- **Dependencies**: None
- **Priority**: 7
- **Status**: **Closed** (2026-07-27) — see `docs/engineering/FIX_LOG.md` "Sprint V15.0 — ENG-007"
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser-verified — at 834px (genuine overflow: scrollWidth 634 vs clientWidth 582) the fade renders in the DOM with the correct gradient at the table's right edge; at 900px/1440px (no overflow) the fade correctly does not render. Scroll-position-aware (hides once scrolled to the end), not a static always-on decoration.

### ENG-008 — Rate-limit boundary (429 at request 21) never empirically confirmed
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 1 item 2, `SECURITY_CERTIFICATION.md` §4
- **Evidence**: Source-code verified (limit exists, `viewer.py:158`, `20/minute`, Redis-backed). Not enough evidence for the live trigger boundary — deliberately not pushed to avoid generating artificial traffic in earlier sprints.
- **Affected files**: None (verification only, no defect found)
- **Estimated effort**: Small
- **Regression risk**: None — bounded to exactly 21 requests against a disposable test link, revoked immediately after
- **Dependencies**: None
- **Priority**: 8
- **Status**: **Closed** (2026-07-27) — **no defect found, boundary confirmed exact**
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser/API-verified — created one disposable password-protected test link, sent exactly 21 wrong-password `POST /api/viewer/validate` attempts: requests 1-20 returned `401` (correctly rejected, not yet rate-limited), request 21 returned `429` — the exact configured boundary (`20/minute`, `viewer.py:158`), not off-by-one in either direction. Test link revoked immediately after (`204`... actual response `200`).

### ENG-009 — XSS not individually tested on fields beyond link labels
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 1 item 3, `SECURITY_CERTIFICATION.md` §5
- **Evidence**: Security inference only for untested fields (document filenames, org names, webhook descriptions, API key names) — same JSX pipeline verified safe for link labels, no `dangerouslySetInnerHTML` found in a repo grep, but each field not individually proven.
- **Affected files**: None — no defect found
- **Estimated effort**: Small
- **Regression risk**: None (read-only verification, disposable test values, all cleaned up)
- **Dependencies**: None
- **Priority**: 9
- **Status**: **Closed** (2026-07-27) — **no defect found**
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Source-verified — repo-wide grep confirms zero `dangerouslySetInnerHTML` usage anywhere in `frontend/src`. Browser/API-verified — created a disposable organization, API key, and webhook, each named/described with `<img src=x onerror=alert(1)>`, then visited the Organizations, API Keys, and Webhooks screens: payload rendered as literal visible text in all 3 (confirmed via screenshot), `document.querySelectorAll('img[src="x"]')` returned 0 matches on every screen, zero JS dialogs fired, zero console errors. All 3 disposable test resources deleted immediately after (204 each).

### ENG-010 — Expired-link enforcement not live-browser-confirmed
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 1 item 4, `UI_EXCELLENCE_SCORECARD.md` (Viewer section)
- **Evidence**: Source-code verified — identical code path (`_check_link_active`, `viewer_service.py:26-35`) and status code as the revoked-link path, which WAS browser-verified. Not enough evidence for the expiry branch specifically, since the dashboard UI only supports date-granularity expiry (earliest achievable value is end-of-current-day).
- **Affected files**: None — no defect found
- **Estimated effort**: Small — tested via direct API call with a short ISO-datetime expiry on a disposable test link (the schema already accepts full datetime precision, `schemas/link.py:16`, even though the dashboard UI only exposes date-granularity)
- **Regression risk**: None (read-only verification, disposable test link, deleted after)
- **Dependencies**: None
- **Priority**: 10
- **Status**: **Closed** (2026-07-27) — **no defect found, live-confirmed**
- **Blocked by**: None
- **Owner**: Engineering (this sprint)
- **Verification method**: Browser/API-verified — created a disposable link via the API with `expires_at` 75 seconds in the future. `POST /api/viewer/validate` returned `200` immediately (link still active), then `410 {"detail":"Link expired"}` after waiting 80 seconds past the expiry — the exact same status/response shape as the already-verified revocation path. This closes the last "Not enough evidence" item from `SECURITY_CERTIFICATION.md`'s original review. Test link deleted after (`200`).

### ENG-011 — DB connection pooling has no cluster-wide budget across replicas
- **Source reports**: `RELEASE_BLOCKERS.md` Tier 2 item 1, `SCALABILITY_CERTIFICATION.md` §2/§11, `ARCHITECTURE_CERTIFICATION.md` §8
- **Evidence**: Source-code verified — safe today (deployment is effectively single-replica); becomes a real risk only if a second API replica is added without addressing pool sizing across replicas.
- **Affected files**: `backend/app/config.py` (pool_size/max_overflow), deployment configuration
- **Estimated effort**: Medium (requires either a pooler like PgBouncer or coordinated per-replica sizing math)
- **Regression risk**: Medium — connection pool changes affect every request path
- **Dependencies**: None
- **Priority**: 11
- **Status**: **Deferral re-confirmed (2026-07-27)** — still Deferred. No horizontal-scaling change occurred this sprint (nothing in `docker-compose.yml`, Railway config, or any code touched this sprint alters replica count); the triggering condition ("before running >1 API replica") remains unmet. Not silently carried forward — actively re-checked.
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
- **Status**: **Deferral re-confirmed (2026-07-27)** — still Deferred. Neither triggering condition (horizontal scaling, or a customer requirement for provably-instant propagation) has arisen this sprint. Not silently carried forward — actively re-checked.
- **Blocked by**: A customer requirement or a scaling decision (external)
- **Owner**: Unassigned
- **Verification method**: N/A until triggering condition arises

---

## ENHANCEMENT (non-blocking)

### ENG-013 — No frontend equivalent of `ruff` for unused-import detection
- **Source reports**: `CODE_QUALITY_CERTIFICATION.md` §6, `RELEASE_BLOCKERS.md` Tier 3 item 1
- **Evidence**: Source-code verified gap (tooling absence, not a found defect)
- **Affected files**: `frontend/eslint.config.js` (new), `frontend/package.json` (added `lint` script + `type: module`), 9 files cleaned of dead code it found
- **Estimated effort**: Medium (tool setup + first-pass cleanup of whatever it finds)
- **Regression risk**: Low for setup; each of the 19 findings was individually investigated (not blind auto-fix) before removal
- **Priority**: 13
- **Status**: **Closed** (2026-07-29)
- **Owner**: Engineering (this sprint)
- **Verification method**: Regression-verified — 19 findings across 9 files, each investigated individually (e.g. `TocSidebar.jsx`'s unused `error` state traced to confirm the UI already falls back to its empty state correctly without it; `ViewerScreen.jsx`'s `drawingState`/`sidecarExtracted` confirmed as unused destructures from hooks that still use them internally, not orphaned state). Fixed all 19; `npm run lint` now exits 0. Along the way, hit and fixed a real Docker build break: the lockfile generated on macOS didn't include Linux/Alpine-only optional platform dependencies for esbuild, causing `npm ci` to fail in the container — regenerated `package-lock.json` from inside a `node:20-alpine` container to match the actual build target. Both test suites unchanged (1709 backend, 13 frontend), build succeeded (312.5kb, down from 312.9kb from the dead-code removal), migration validated (exit 0), full Docker rebuild + browser-verified (Upload/Access Control/API Keys/Webhooks/Billing/Viewer all clean, zero console errors, Viewer opens and renders correctly with the touched hooks).

### ENG-014 — Systematic duplicate-code scan never run
- **Source reports**: `CODE_QUALITY_CERTIFICATION.md` §4
- **Evidence**: Source-code verified. Installed `jscpd` and ran it against the full `frontend/src` + `backend/app` trees (min 10 lines / 50 tokens). Result: 24 clones total — 22 Python (1.70% duplicated lines), 2 JSX (0.25%). Both figures are low by industry norms (typical healthy-codebase thresholds are often cited around 3-5%).
- **Fixed**: One genuine, valuable duplication — `analytics_service.py`'s `get_document_analytics` and `get_group_analytics` both independently implemented the identical 4-5-query batch link-event-aggregation block (28 and 24 lines respectively). Extracted into a shared `_aggregate_link_event_counts()` helper. This was real drift risk: two copies of the same GROUP BY queries, one could be fixed/changed without the other being updated. Verified: `test_analytics.py`'s 20 tests pass unchanged, full suite 1709 passed / 1 skipped / 0 failed.
- **Investigated, not extracted**: `annotation_export_service.py`/`annotation_thread_service.py` (3 clone pairs) — genuine overlap (author_role validation, date parsing, base WHERE filter) but the two functions' `SELECT` shapes differ (`build_feedback_export` selects a single `ViewerAnnotation` entity; `fetch_feedback_list` selects `(ViewerAnnotation, ShareLink.label)` as a tuple for display). A clean shared extraction would need a parameterized query-builder — added complexity for a ~15-line saving. Judged not worth it.
- **Reviewed at appropriate depth, not extracted** (remaining 20 clones): same-file clones in `annotations.py`, `documents.py`, `groups.py`, `links.py`, `orgs.py`, `viewer.py`, `reading_analytics_service.py`, `workers/pipeline/pdf.py`, `AccessScreen.jsx` — each is a small (11-20 line) same-file repeat of a pattern like "check ownership, raise 404" or "fetch + validate" across two endpoints/branches in the same file; low drift risk since one person editing the file sees both copies together, and each is small enough that extraction would add an indirection layer for marginal benefit. Cross-file: `adapters/presentation.py`/`adapters/spreadsheet.py` and `adapters/text.py`/`adapters/word.py` — these are file-format adapters implementing a shared conversion contract; structural similarity between sibling adapters following the same interface is expected, not accidental duplication. `ApiKeysScreen.jsx`/`WebhooksScreen.jsx` (11 lines) — small, similar modal boilerplate, same reasoning as the same-file router cases.
- **Affected files**: `backend/app/services/analytics_service.py` (fixed); all others reviewed only
- **Estimated effort**: Small (scan) + Small (the one fix made)
- **Regression risk**: Low — the one fix is a pure extraction (identical queries, same call sites), verified via the existing analytics test suite
- **Priority**: 14
- **Status**: **Closed** (2026-07-29)
- **Owner**: Engineering (this sprint)
- **Verification method**: Source-code verified scan output (24 clones, categorized above); regression-verified (`test_analytics.py` 20/20, full suite 1709/1709 unchanged)

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

### ENG-021 — Link mutation endpoints return 403 (not 404) for cross-account access, inconsistent with documents/API-keys
- **Source reports**: none — newly discovered during ENG-003 verification, not present in any V13.0 report
- **Evidence**: Browser/API-verified — `PATCH /api/links/{id}`, `DELETE /api/links/{id}`, `DELETE /api/links/{id}/hard` all returned `403 Not authorized` when Account B targeted Account A's link ID, whereas the equivalent cross-account attempts on `/api/documents/{id}` and `/api/api-keys/{id}` both returned `404`. The rest of the app's documented pattern (`SECURITY_CERTIFICATION.md` §2) deliberately uses 404 everywhere specifically to avoid confirming a resource's existence to an unauthorized caller. A 403 on links technically confirms "a link with this ID exists, just not yours" — a minor deviation from that pattern. Not practically exploitable (link IDs are random UUIDs, not enumerable), but an inconsistency worth fixing for defense-in-depth consistency.
- **Affected files**: `backend/app/routers/links.py` (`revoke_link`, `update_link`, `delete_link_permanently`), `backend/tests/regression/test_auth_enforcement.py`
- **Estimated effort**: Small (change the authorization-failure branch from `403` to `404` in the 3 link-mutation handlers, matching the pattern already used in `documents.py`/`api_keys.py`)
- **Regression risk**: Low-Medium — realized: 2 existing tests (`TestCrossUserLinkAccess::test_user_a_cannot_revoke_user_b_link`, `test_user_a_cannot_patch_user_b_link`) asserted the old `403`, inconsistent with their own sibling tests in the same class (create/list) which already correctly expected `404`. Updated both to `404`, and added a third test for the hard-delete endpoint, which had zero prior cross-account coverage.
- **Dependencies**: None
- **Priority**: 21 (Low)
- **Status**: **Closed** (2026-07-27)
- **Owner**: Engineering (this sprint)
- **Verification method**: Regression-verified — reverted the source fix via `git stash`, confirmed all 3 tests fail against pre-fix code (proving they're meaningful, not tautological), restored the fix, confirmed all 3 pass. Full suite: 1709 passed (up from 1708), 1 skipped, 0 failed. Browser/API-verified on the local Docker stack with fresh Account A/B logins: `PATCH`/`DELETE`/`DELETE .../hard` on Account A's link as Account B all now return `404 {"detail":"Link not found"}` — indistinguishable from a nonexistent link ID.

## V16.0 — merged from ISSUE_DATABASE.md / TODO_QUEUE.md (2026-07-28)

Reading the full canonical-source list per V16.0's instructions surfaced 10 items genuinely still open in `ISSUE_DATABASE.md` that predate this backlog and were never merged in. Also surfaced: `ISSUE_DATABASE.md` itself had drifted stale (several items marked "Open" there were actually fixed back in V10.0, confirmed by `TODO_QUEUE.md`'s own completion record and spot-verified 3/3 against current source) — reconciled directly in `ISSUE_DATABASE.md`, not duplicated here.

### ENG-022 — `links.py` DELETE endpoints return 200+body, 8 others return 204/no-body
- **Source**: `ISSUE_DATABASE.md` M-6 (V7.0)
- **Evidence**: Source-verified API inconsistency.
- **Severity**: Low (API contract change)
- **Status**: Deferred — explicitly listed in `TODO_QUEUE.md`'s "NOT queued" list (changing response status codes is a breaking API contract change for any existing client). Not undertaken without a deliberate versioning decision.
- **Owner**: Unassigned

### ENG-023 — 14 endpoints across 7 routers validate via raw `body: dict` instead of typed Pydantic schemas
- **Source**: `ISSUE_DATABASE.md` M-8 (V7.0)
- **Evidence**: Source-verified.
- **Severity**: Medium (real validation/maintainability gap, but broad)
- **Status**: Deferred — explicitly listed in `TODO_QUEUE.md`'s "NOT queued" list as an API contract change. A mechanical per-endpoint migration is real work with real regression risk across 14 sites; not undertaken piecemeal.
- **Owner**: Unassigned

### ENG-024 — "Created at" concept renders 3 different ways across screens
- **Source**: `ISSUE_DATABASE.md` M-10 (V6.0)
- **Evidence**: Source-verified — `fmtDate()`, raw `toLocaleString()`, and a custom `fmtTime()` all exist and are used inconsistently for the same semantic concept.
- **Severity**: Low (cosmetic consistency)
- **Status**: Open
- **Owner**: Engineering (this sprint, Enhancement tier)

### ENG-025 — Empty states inconsistent (icon+heading+CTA vs. bare text)
- **Source**: `ISSUE_DATABASE.md` M-11 (V6.0)
- **Evidence**: Source-verified, no fixed rule exists.
- **Severity**: Low (cosmetic consistency)
- **Status**: Open
- **Owner**: Engineering (this sprint, Enhancement tier)

### ENG-026 — AUTH-006: session token stored in `localStorage`, real XSS-exposure vector
- **Source**: `ISSUE_DATABASE.md` M-14 (V4.0/Sprint7.0)
- **Evidence**: Source-verified — `frontend/api.js`'s `authHeaders()` reads the bearer token from `localStorage`. A successful XSS on this origin could exfiltrate the token (session hijack), though `SECURITY_CERTIFICATION.md`'s live XSS testing this sprint (ENG-009) found no injectable field.
- **Severity**: Medium-High in isolation (token-theft-via-XSS is a real class of risk) — **but** the actual exploit path requires a successful XSS first, and none has been found live or in source (zero `dangerouslySetInnerHTML` anywhere, JSX escaping confirmed working on every field tested).
- **Status**: **Deferred, re-confirmed** — a full migration plan already exists (`SECURITY_HARDENING_PLAN.md`, referenced in `ISSUE_DATABASE.md`), and per this repo's own established policy, architecture migrations of this kind ("localStorage token → httpOnly cookie" is a real auth-model change touching CORS, CSRF posture, and every API client) are documented and planned, not partially patched mid-sprint. Re-confirming this deferral rather than silently carrying it: the risk is real but requires a *second* vulnerability (XSS) to be exploitable, and this sprint's XSS testing (ENG-009) found none live.
- **Owner**: Unassigned (architecture decision + migration plan owner)

### ENG-027 — Modal-entrance-animation duration drifts (.15s/.18s/.22s/.25s)
- **Source**: `ISSUE_DATABASE.md` L-1 (V7.0)
- **Evidence**: Source-verified.
- **Severity**: Low (cosmetic)
- **Status**: Open
- **Owner**: Engineering (this sprint, Enhancement tier, if time permits)

### ENG-028 — Icon language mixes geometric Unicode and real emoji
- **Source**: `ISSUE_DATABASE.md` L-2 (V7.0)
- **Evidence**: Source-verified.
- **Severity**: Low (cosmetic, needs a design decision on which icon language to standardize on)
- **Status**: Open — low actionability without a design decision; documented, not blindly changed
- **Owner**: Unassigned (needs design input)

### ENG-029 — Architecture docs contradict each other on watermark model and cache TTLs
- **Source**: `ISSUE_DATABASE.md` L-3 (V7.0)
- **Evidence**: Source-verified against `backend/app/services/viewer_cache.py` (`LINK_TTL_SEC=10.0`, `DOC_TTL_SEC=60.0`, `PAGE_TTL_SEC=300.0`, `SESSION_TTL_SEC=5.0`) and `backend/app/services/watermark.py` (3 distinct mechanisms: `apply_visible_watermark`, `apply_forensic_stamp`, `apply_viewer_forensic_stamp`). `ARCHITECTURE.md` had 2 real errors: link-snapshot TTL stated as 30s (actual 10s) and session-validation TTL stated as 30s (actual 5s); and it mislabeled the main visible per-session watermark as "forensic" while omitting the two actual (separate) near-invisible forensic stamps entirely. `OVERVIEW.md` was already correct on both counts.
- **Severity**: Medium (incorrect documentation actively misleads future engineering work)
- **Status**: **Closed** (2026-07-28) — `ARCHITECTURE.md` corrected to match verified source, with an explicit source-of-truth file citation added to prevent future drift.
- **Owner**: Engineering (this sprint)
- **Verification method**: Source-verified (direct read of `viewer_cache.py` and `watermark.py`); regression-verified (backend suite unchanged, 1709 passed, 1 skipped — docs-only change).

### ENG-030 — Button-variant usage for row-level delete/revoke triggers varies
- **Source**: `ISSUE_DATABASE.md` L-6 (V6.0)
- **Evidence**: Source-verified — `ghost`+red-text vs. `outline-danger` both used for the same semantic action class.
- **Severity**: Low (cosmetic consistency)
- **Status**: Open
- **Owner**: Engineering (this sprint, Enhancement tier, if time permits)

### ENG-031 — WATERMARK-OWNER-ANON-001: owner's own preview watermark shows "anonymous"
- **Source**: `ISSUE_DATABASE.md` (V12.0)
- **Evidence**: Source-verified as a real, not-yet-fixed cosmetic bug — the document owner's own preview-link watermark displays "anonymous" instead of their real email, in the same machinery as the already-fixed READ-OWNER-001.
- **Severity**: Low (cosmetic, but a genuine incorrect-displayed-value bug, not just a style inconsistency)
- **Status**: Open
- **Owner**: Engineering (this sprint)

## Explicitly not on this backlog (verified non-issues)

- **Storage screen usage bars** (`FIXES_TODO.md` §5) — investigated and ruled out; the fill-bar computation is correct (`width: 0.0032554%` for a 328-byte file, verified via DOM inline-style inspection). An earlier automated check mismeasured the empty track div. No action needed.
- **AD-6 (unreachable 640px CSS breakpoint)** — deliberate, previously-recorded non-fix pending a product decision about mobile support scope (`ARCHITECTURE_DECISIONS.md`). Not re-litigated without that product decision being reopened first.
- **Test-data debris in the live QA account** (`FIXES_TODO.md` §6) — not a code defect; an operational cleanup item for the test account itself, tracked separately from the engineering backlog.

---

## Summary table

| ID | Title | Severity | Priority | Status |
|---|---|---|---|---|
| ENG-001 | Analytics screen clips data at 768px | High | 1 | **Closed** |
| ENG-002 | Notifications feed lacks document identity | High | 2 | **Closed** |
| ENG-003 | Cross-account IDOR unverified live | High | 3 | **Closed — no defect found** |
| ENG-004 | Document picker can't disambiguate duplicates | Medium | 4 | **Closed** |
| ENG-005 | List endpoints lack pagination | Medium | 5 | Deferred |
| ENG-006 | Storage blocking-I/O sites unaudited | Medium | 6 | **Closed — no defect found** |
| ENG-007 | Audit Log scroll affordance missing | Low | 7 | **Closed** |
| ENG-008 | Rate-limit 429 boundary unconfirmed | Low | 8 | **Closed — boundary exact** |
| ENG-009 | XSS untested beyond link labels | Low | 9 | **Closed — no defect found** |
| ENG-010 | Expired-link live confirmation missing | Low | 10 | **Closed — live-confirmed** |
| ENG-011 | Connection pooling cluster budget | Low | 11 | Deferred |
| ENG-012 | Cache invalidation broadcast | Low | 12 | Deferred |
| ENG-013 | No frontend lint tooling | Enhancement | 13 | **Closed** |
| ENG-014 | No duplicate-code scan run | Enhancement | 14 | **Closed** |
| ENG-015 | Duplicated permissions dict (AD-7) | Enhancement | 15 | Justified, not changed |
| ENG-016 | AccessScreen.jsx oversized (M-13) | Enhancement | 16 | Deferred |
| ENG-017 | Observability wiring unconfirmed | Enhancement | 17 | Open (ops, not code) |
| ENG-018 | Large-PDF stress not retested | Enhancement | 18 | Open |
| ENG-019 | Dashboard modals not re-exercised | Enhancement | 19 | Open |
| ENG-020 | Reading Intelligence hand-verification | Enhancement | 20 | Open |
| ENG-021 | Links return 403 not 404 cross-account (new finding) | Low | 21 | **Closed** |
| ENG-022 | links.py DELETE 200 vs 204 inconsistency (M-6) | Low | 22 | Deferred |
| ENG-023 | 14 endpoints use raw dict not typed schemas (M-8) | Medium | 23 | Deferred |
| ENG-024 | "Created at" rendered 3 different ways (M-10) | Low | 24 | Open |
| ENG-025 | Empty states inconsistent (M-11) | Low | 25 | Open |
| ENG-026 | AUTH-006: session token in localStorage (M-14) | Medium-High | 26 | Deferred, re-confirmed |
| ENG-027 | Modal animation duration drift (L-1) | Low | 27 | Open |
| ENG-028 | Icon language mixing (L-2) | Low | 28 | Open, needs design input |
| ENG-029 | Architecture docs contradict each other (L-3) | Medium | 29 | **Closed** |
| ENG-030 | Button-variant inconsistency for delete/revoke (L-6) | Low | 30 | Open |
| ENG-031 | Owner preview watermark shows "anonymous" (WATERMARK-OWNER-ANON-001) | Low | 31 | Open |

**Critical: 0. High: 3 (all closed). Medium: 5 (2 closed, 1 deferred, 2 new: 1 deferred, 1 open). Low: 14 (5 closed, 3 deferred, 6 open). Enhancement: 8.**

Updated totals after merge: **31 tracked issues, 10 closed, 5 deferred-with-reconfirmed-reasoning, 16 open.**
