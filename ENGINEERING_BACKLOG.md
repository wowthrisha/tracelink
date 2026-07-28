# Engineering Backlog — TraceLink / SecureDoc V14.0

Canonical, deduplicated backlog merging every issue from all six V13.0 reports: `FIXES_TODO.md`, `RELEASE_BLOCKERS.md`, `FINAL_RELEASE_CERTIFICATION.md`, `UI_EXCELLENCE_SCORECARD.md`, `ARCHITECTURE_CERTIFICATION.md`, `CODE_QUALITY_CERTIFICATION.md`. Where the same underlying issue appeared in multiple reports, it is merged into one canonical entry with all source reports cited — no issue is worked twice under two IDs.

Every issue's evidence is classified as exactly one of **Browser verified / Source-code verified / Regression verified / Engineering inference / Not enough evidence**, never mixed, carried forward unchanged from the report(s) it originated in.

Severity scale: **Critical → High → Medium → Low → Enhancement**. Per the V13.0 Tier-0 finding, restated here rather than re-derived: **zero Critical issues exist** — nothing found across all six reports is a confirmed, live-observed defect in core functionality, data isolation, or security enforcement.

**Status as of 2026-07-26 18:30**: All 3 High-severity items closed and re-verified. Medium tier fully actioned (ENG-004 fixed, ENG-005 deferral re-confirmed with fresh reasoning, ENG-006 audited clean) and re-verified in a dedicated post-tier regression pass (10 screens, zero errors). Zero regressions across both test suites at every checkpoint. Proceeding to Low tier.

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
| ENG-013 | No frontend lint tooling | Enhancement | 13 | Open |
| ENG-014 | No duplicate-code scan run | Enhancement | 14 | Open |
| ENG-015 | Duplicated permissions dict (AD-7) | Enhancement | 15 | Justified, not changed |
| ENG-016 | AccessScreen.jsx oversized (M-13) | Enhancement | 16 | Deferred |
| ENG-017 | Observability wiring unconfirmed | Enhancement | 17 | Open (ops, not code) |
| ENG-018 | Large-PDF stress not retested | Enhancement | 18 | Open |
| ENG-019 | Dashboard modals not re-exercised | Enhancement | 19 | Open |
| ENG-020 | Reading Intelligence hand-verification | Enhancement | 20 | Open |
| ENG-021 | Links return 403 not 404 cross-account (new finding) | Low | 21 | **Closed** |

**Critical: 0. High: 3 (all closed). Medium: 3. Low: 7. Enhancement: 8.**
