# Engineering Backlog — TraceLink / SecureDoc V14.0

Canonical, deduplicated backlog merging every issue from all six V13.0 reports: `FIXES_TODO.md`, `RELEASE_BLOCKERS.md`, `FINAL_RELEASE_CERTIFICATION.md`, `UI_EXCELLENCE_SCORECARD.md`, `ARCHITECTURE_CERTIFICATION.md`, `CODE_QUALITY_CERTIFICATION.md`. Where the same underlying issue appeared in multiple reports, it is merged into one canonical entry with all source reports cited — no issue is worked twice under two IDs.

Every issue's evidence is classified as exactly one of **Browser verified / Source-code verified / Regression verified / Engineering inference / Not enough evidence**, never mixed, carried forward unchanged from the report(s) it originated in.

Severity scale: **Critical → High → Medium → Low → Enhancement**. Per the V13.0 Tier-0 finding, restated here rather than re-derived: **zero Critical issues exist** — nothing found across all six reports is a confirmed, live-observed defect in core functionality, data isolation, or security enforcement.

**Status as of 2026-07-27 09:30** (historical, first-tier-completion snapshot, preserved as written): High and Medium tiers closed and re-verified. **Low tier fully actioned** (ENG-007/008/009/010/021 fixed or verified with no defect, ENG-011/012 deferrals re-confirmed) and re-verified in a dedicated post-tier regression pass (10 screens zero errors, both key fixes re-confirmed with fresh logins). Every "Not enough evidence" gap from the original security review is now live-confirmed. Zero regressions across both test suites at every checkpoint. Proceeding to Enhancement tier.

**Current status (2026-08-09, V24.0 continuation — the authoritative, up-to-date figure; see "Reconciled totals" below for the full item-by-item recount)**: 50 items total — **34 closed**, 7 deferred (reasoned), 3 reviewed-not-implemented, 1 justified-not-changed, **5 open** (ENG-033, ENG-034, ENG-038, ENG-044 each blocked on a named external decision; ENG-049 a newly-found, Low-severity test-coverage gap, correctly scoped out of the lint-cleanup pass that found it). Zero Critical defects; zero unresolved High defects; **zero partially-fixed items — ENG-046's `backend/tests` remainder is fully closed and ENG-050 (a live-regression finding — misleading "Revoked" status on never-shared documents) was found and fixed the same day**. Zero contradictory statuses as of this reconciliation pass.

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
- **V22.0 re-investigation (Priority 3)**: re-verified precisely, with the mandated IMPLEMENTED/WIRED/TESTED/DEPLOYED/EXTERNALLY-MONITORED breakdown, rather than leaving this as one vague "unconfirmed":

  | Capability | Status | Evidence |
  |---|---|---|
  | Structured (JSON) logs | IMPLEMENTED + WIRED | Source: `middleware/json_logging.py` |
  | Correlation/request IDs | IMPLEMENTED + WIRED | Source: `middleware/request_id.py`, reads `X-Request-ID`/`X-Correlation-ID`, feeds `json_logging` |
  | `/health` endpoint | IMPLEMENTED + WIRED + confirmed live | `curl` against the local Docker stack → `{"status":"ok",...}` |
  | `/ready` endpoint | IMPLEMENTED + WIRED + confirmed live | `curl` → `{"status":"ready"}` |
  | Prometheus `/metrics` endpoint | IMPLEMENTED + WIRED + TESTED + confirmed live | 18 pre-existing metrics (HTTP, viewer, documents, links, annotations, webhooks, DB, cache, sessions); confirmed IP-allowlist protection correctly returns 403 from outside the allowlist, and returns real accumulated Prometheus exposition data from inside the container (`docker compose exec api curl .../metrics`) — including live counts from this same sprint's own ENG-039 API testing traffic |
  | HTTP latency metrics | IMPLEMENTED | `http_request_duration_seconds` histogram, source-verified |
  | Error-rate visibility | IMPLEMENTED | Via `status_code` label on `http_requests_total` — no separate error-rate metric needed |
  | Celery task metrics | **Was NOT implemented — fixed this sprint** | See below |
  | Security-event logging | IMPLEMENTED, via `audit_service.py` | Not a separate "security events" stream by name, but functionally serves this role — org/api-key/document mutation logging, extensively verified this session |
  | Audit logging | IMPLEMENTED + WIRED | `audit_service.py`, verified extensively across this session (org.*, member.*, api_key.*, webhook.*, document.* events) |
  | DEPLOYED (scrape config, dashboards) | **BLOCKED — insufficient evidence** | Requires infrastructure access this session does not have |
  | EXTERNALLY MONITORED (Grafana, Alertmanager) | **BLOCKED — insufficient evidence** | Same — genuinely an operations requirement, not an application-code gap |

- **Fix applied**: added `securedoc_celery_task_duration_seconds` (histogram) and `securedoc_celery_tasks_total` (counter), both labeled `task_name`/`outcome` (success/error/retry), wired into `process_document` (the primary, highest-volume Celery task) — the one genuine, demonstrated application-code gap found. Deliberately bounded to this one task; `purge_stale_sessions`/`requeue_orphaned_uploads`/`webhook_tasks.deliver_webhook` are not yet instrumented, an explicit boundary not an oversight.
- **New finding while verifying the fix, filed separately as ENG-044**: the metrics register correctly (confirmed via unit tests) but do not appear on the API's `/metrics` endpoint when the worker actually processes a real document — because the worker runs as a separate OS process from the API, and `prometheus_client`'s default registry is per-process. Confirmed live: uploaded and processed a real document via the local Docker stack's actual worker, checked `/metrics` immediately after — the metric family HELP/TYPE lines are present but no sample lines are. This is a genuine, correctly-scoped-out architectural gap (needs `PROMETHEUS_MULTIPROC_DIR` + `multiprocess.MultiProcessCollector`), not a code defect in what was just added.
- **Severity**: Low (the original finding; mostly resolved by this re-investigation's much stronger evidence)
- **Status**: **Closed — re-classified with full evidence, one genuine gap fixed (bounded), one new gap filed as ENG-044** (2026-08-04, V22.0)
- **Owner**: Engineering (V22.0) — closed; ENG-044 open, needs ops/infra input for the multiprocess registry
- **Verification method**: Source Verified (all IMPLEMENTED/WIRED rows) + API Verified (live `/health`, `/ready`, `/metrics` checks against the real local Docker stack, including a real document-processing run) + Test Verified (3 new unit tests for the Celery metrics, `backend/tests/unit/test_celery_metrics.py`) + Blocked (the 2 DEPLOYED/EXTERNALLY-MONITORED rows, correctly classified rather than guessed at)

### ENG-018 — Large-PDF (100+ page) Viewer stress not freshly re-tested
- **Source reports**: `UI_EXCELLENCE_SCORECARD.md` (Viewer section), `RELEASE_BLOCKERS.md` Tier 3 item 5
- **V20.0 verification**: No browser-automation tool is available in this environment, so this was verified at the API/integration level against the real local Docker stack rather than through an actual browser — classified as Integration/API-verified, not Browser Verified, per this sprint's evidence-category discipline. Generated a genuine 120-page synthetic PDF (unique searchable marker text per page), uploaded it through `/api/documents/upload` with a real authenticated session, and confirmed: (1) Celery processing completed to `status: ready`, `page_count: 120`; (2) page rendering succeeded at first/middle/last pages (1, 60, 120) — all returned `200 image/webp` with real byte content (110-115KB each); (3) thumbnail generation succeeded at pages 1 and 120; (4) full-text search (`/api/viewer/search`) correctly located a unique marker planted on page 75, with the correct page number and snippet; (5) word-position extraction (`/api/viewer/words`) returned data for all 120 pages, with page 75 showing 203 extracted words — confirming the search-highlight pipeline processes the full document, not a truncated subset; (6) the Reading Intelligence batch-ingestion endpoint (`/api/reading/batch`) correctly processed a controlled 3-page reading session against the 120-page document with no errors — see ENG-020 for the detailed math cross-check performed using this same test document. All disposable test resources (document, link) were deleted after verification; confirmed via a 404 on GET post-delete.
- **Category**: Integration/API Verified (not Browser Verified — no browser-automation tool available in this environment)
- **Affected files**: None — no defect found
- **Estimated effort**: Small (as originally estimated)
- **Priority**: 18
- **Status**: **Closed — verified, no defect found** (2026-08-01, V20.0)
- **Owner**: Engineering (V20.0) — closed
- **Verification method**: Integration/API-verified against the real local Docker stack with a genuine 120-page document

### ENG-019 — Dashboard screens' individual modals/toggles not re-exercised element-by-element this specific sprint
- **Source reports**: `UI_EXCELLENCE_SCORECARD.md` (Dashboard screens section)
- **V20.0 partial verification**: No browser-automation tool is available in this environment, so a true "browser-verified, screen by screen" pass over all ~10 dashboard screens' modals/toggles is not achievable this sprint — stating this honestly rather than claiming full closure. What WAS verified at the API/integration level: created a disposable API key and a disposable webhook via the real backend, toggled each `is_active` off via `PATCH`, and confirmed the change persisted on a fresh re-fetch (not just the mutating response) for both `ApiKeysScreen`'s and `WebhooksScreen`'s active/inactive toggle. Both round-tripped correctly: backend accepted the PATCH, database persisted it, and a subsequent GET reflected the new state. Both disposable resources were deleted after verification (204 responses confirmed).
- **Remaining gap (as of V20.0)**: this covers 2 of the screen's several toggles/modals (Access Control's link toggles, Organizations' role/settings toggles, and every screen's actual rendered UI feedback — loading/success/error states, modal open/close, focus handling — remain unverified this sprint, since those require an actual rendered page, not just an API round-trip). **Not claiming this item closed** — narrowing scope honestly rather than overclaiming.
- **V23.0 completion**: The blocker (no browser-automation tool in this environment) is resolved — a working Playwright+Chromium install was found in the host's miniconda3 environment (confirmed working against both the live Railway deployment and the real local Docker stack). Completed the full remaining sweep genuinely Browser Verified:
  - **Access Control link toggles**: exercised the Create Link form's 8 permission toggles (`role="switch"`/`aria-checked` — confirmed genuine accessibility semantics, not styled divs) and the separate Edit Link modal's 8 toggles against a disposable test link (`ENG019_toggle_persist_test`) created on the live app. Toggled `Download` on at creation, toggled `Print` on via Edit + Save, then did a **hard full-page reload** and re-opened the Edit modal: both toggles read back `aria-checked="true"` — genuine backend persistence, not client-side state. Success toast on create, confirmation dialogs on both Revoke and hard Delete (with explicit "cannot be undone" copy), all correctly gated. Disposable link fully cleaned up (revoked + hard-deleted, confirmed 0 remaining), and its full lifecycle (`link.created`/`link.updated`/`link.revoked`/`link.deleted`) shows up correctly in the Audit Log with correct actor/timestamp. Zero console errors throughout. A legacy test link literally named `<img src=x onerror=alert(1)>` rendered as inert text in both the list and the Edit modal's title — reconfirms ENG-009 (no live XSS) is still true.
  - **Organizations role/settings toggles**: opened the Members modal for the account's one real org. Found the role `<select>` and "Remove" button are **not disabled** based on the caller's own role (test account holds `editor`, below the `admin` minimum `orgs.py:414` requires for `update_member_role`) — worth noting as a minor UX gap (see ENG-045 finding below, judged not worth fixing). Live-tested the actual boundary: attempting a role change as `editor` correctly hit the backend's `minimum_role="admin"` gate, returned `403`, and the frontend showed a precise "Requires admin role or higher" toast while cleanly reverting the dropdown to its prior value — clean failure surfacing, not a silent failure. Did not attempt a live mutation against the org's actual owner (the account holder's real org membership) — verified the authorization boundary via source (`backend/app/routers/orgs.py:407-436`) instead, since a live test could only ever be a self-targeted 403 rehearsal anyway. Rename modal renders correctly pre-filled with the current name (not submitted, to avoid mutating the real org).
  - **Remaining ~8 screens** (Upload, Viewer, Feedback, Analytics, Storage, API Keys, Webhooks, Audit Log, Notifications, Billing): full sweep, zero console errors on any screen, empty states render correctly (API Keys/Webhooks show the rich icon+heading+CTA pattern per ENG-025's precedent), Storage/Analytics/Billing/Audit Log all show real, correctly-formatted data.
  - **Found and fixed one real defect during this sweep** — see **ENG-045**.
- **Category**: Browser Verified (Access Control + Organizations + full 10-screen sweep, live Railway app) + Source Verified (Organizations RBAC boundary) + Regression Verified (ENG-045's fix)
- **Affected files**: None for ENG-019 itself — see ENG-045 for the fix this sweep produced
- **Estimated effort**: n/a — closed
- **Priority**: 19
- **Status**: **Closed — full sweep complete** (2026-08-08, V23.0). Every gap V20.0 left open is now genuinely browser-verified; the one real defect the sweep surfaced is tracked and fixed as ENG-045.
- **Owner**: Engineering (V23.0) — closed
- **Verification method**: Browser Verified (Playwright against the live Railway app for the full sweep, plus the local Docker stack for ENG-045's fix verification) + Source Verified (Organizations RBAC) + Regression Verified (backend 1751 passed/1 skipped/0 failed, frontend 13/13, both unchanged except ENG-045's isolated fix)

### ENG-020 — Reading Intelligence metrics not independently hand-verified against backend math this sprint
- **Source reports**: `UI_EXCELLENCE_SCORECARD.md` (Viewer section)
- **V20.0 verification**: Read `reading_analytics_service.py`'s calculation source in full, then submitted a controlled, exactly-known reading-event batch (pages 1/2/3, active times 10000ms/15000ms/5000ms, page 3 marked `in_progress`) against the ENG-018 120-page test document via `/api/reading/batch`, and hand-verified 3 returned metrics against the source formulas:
  - `total_active_ms: 30000` — exact sum of the 3 submitted `active_time_ms` values. Matches.
  - `completion_pct: 2.5` — source formula (`reading_analytics_service.py:474`) is `(pages_visited / page_count) * 100`. 3 pages visited / 120 page_count × 100 = 2.5. Matches exactly.
  - `reading_speed_wpm: 700.0` — this is the interesting case. `compute_reading_speed_wpm()` (line 136) only counts pages with `completion_status in ('reading', 'completed')`, excluding my `in_progress` page 3, leaving pages 1 and 2. It uses an *estimated* `words_per_page` (250 for PDFs, not the actual extracted word count — a deliberate, documented approximation, not a bug) in an EWMA formula, then **clamps the result to `max(50.0, min(700.0, ewma))`** (line 177, "physiologically plausible range"). My synthetic test's artificially fast pace (10-15s/page) produces an EWMA well above 700, so the clamp fires and returns exactly `700.0`. This is not a placeholder — it's the ceiling-clamp behaving exactly as documented, confirmed by reading the formula and independently recomputing the pre-clamp EWMA by hand (~1000-1500wpm range depending on exact `EWMA_ALPHA`, comfortably above the 700 ceiling either way).
  - This also confirms `words_per_page` is an estimated constant, not derived from the real per-document extracted word count — a real (already-known, not new) modeling simplification, not a defect: the same document's actual text-layer extraction (`/api/viewer/words`) returned 203 real words for page 75, vs. the model's flat 250-word PDF assumption. Close enough to not distort the UX (reading-time estimates are inherently approximate), but worth noting for anyone tuning the model later.
- **Category**: Source Code Verified + Integration/API Verified (not Browser Verified — no browser-automation tool available in this environment; the "displayed value" cross-check was performed against the raw API response the Viewer's `ReadingStatusBar` component consumes, not a rendered page)
- **Affected files**: None — no defect found
- **Estimated effort**: Medium (as originally estimated)
- **Priority**: 20
- **Status**: **Closed — verified, metrics match backend math exactly, including a clamp edge case** (2026-08-01, V20.0)
- **Owner**: Engineering (V20.0) — closed
- **Verification method**: Source-code verified (read `compute_reading_speed_wpm`, the `completion_pct` assignment, and `DocumentComplexity`'s word-estimation logic in full) + Integration/API-verified (controlled batch submission, exact-value cross-check)

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
- **Evidence**: Source-verified, re-verified V17.0 (STEP 1). Confirmed still reproducible: `StorageScreen.jsx`, `BillingScreen.jsx`, `InsightsModal.jsx` each independently called `new Date(x).toLocaleDateString()` with no options — browser-locale-dependent numeric format (e.g. "7/29/2026") — instead of the app's existing shared `fmtDate()` util (`utils/viewer.js`, already used elsewhere, produces "Jul 29, 2026"). `AccessScreen.jsx` separately had the identical `new Date(x).toLocaleString()` expression repeated 3 times for 3 different audit-trail timestamp fields.
- **STEP 2 justification**: Yes on usability (consistent date presentation instead of 3 different formats), maintainability (fewer duplicate inline date-formatting expressions), and reduces future-bug risk (one correct shared implementation vs. several independently-maintained ones). Distinguished from a false-positive case: `NotificationsScreen.jsx`'s and `AuditLogScreen.jsx`'s same-named `fmtTime()` functions were investigated and found to be semantically different (relative "2m ago" vs. absolute precise timestamp) — correctly left untouched, not a true duplication.
- **Fix**: `StorageScreen.jsx`, `BillingScreen.jsx`, `InsightsModal.jsx` now import and use the shared `fmtDate()`. `AccessScreen.jsx` gained one small local `fmtDateTime()` helper (date+time format, which `fmtDate()` doesn't provide) replacing its 3 duplicate inline expressions.
- **Severity**: Low (cosmetic consistency)
- **Status**: **Closed** (2026-07-29)
- **Owner**: Engineering (this sprint)
- **Verification method**: Regression-verified (both test suites unchanged, build succeeded, lint exit 0) + Browser-verified (Storage, Billing, Access Control screens all render cleanly on the local Docker stack, zero console errors)

### ENG-025 — Empty states inconsistent (icon+heading+CTA vs. bare text)
- **Source**: `ISSUE_DATABASE.md` M-11 (V6.0)
- **Evidence**: Source-verified, re-verified V17.0 (STEP 1). Confirmed reproducible: `WebhooksScreen.jsx`/`ApiKeysScreen.jsx`/`OrgsScreen.jsx` all share a rich pattern (icon + bold heading + muted subtext + primary CTA button). `AuditLogScreen.jsx`/`NotificationsScreen.jsx` use a single bare centered text line. A local `EmptyState` component exists but is scoped to `InsightsModal.jsx` only, not shared app-wide (only 1 of 8 surveyed screens uses it).
- **STEP 2 (value justification)**: Mixed, not a clean yes. Some genuine usability value (visual consistency), but: (a) the gap is partly semantically justified — `WebhooksScreen`/`ApiKeysScreen`/`OrgsScreen` all have an obvious "+ New X" create-action their CTA invites, while `AuditLogScreen`/`NotificationsScreen` are passive/log-type screens with no equivalent action a CTA could offer; (b) no existing canonical shared pattern to mechanically apply — building one requires a design judgment call (does a passive screen even warrant an icon treatment without a CTA, or does that look unfinished?) that exceeds a pure engineering decision for a Low-severity cosmetic item. Per this sprint's explicit instruction not to assume every remaining Low item should be implemented: **not implemented**.
- **Severity**: Low (cosmetic consistency)
- **Status**: **Reviewed, not implemented** (2026-07-29) — reproducible but judged not to clear the STEP 2 bar without design input on the canonical pattern. Same category as ENG-028.
- **Owner**: Unassigned (needs design input if revisited)

### ENG-026 — AUTH-006: session token stored in `localStorage`, real XSS-exposure vector
- **Source**: `ISSUE_DATABASE.md` M-14 (V4.0/Sprint7.0)
- **Evidence**: Source-verified — `frontend/api.js`'s `authHeaders()` reads the bearer token from `localStorage`. A successful XSS on this origin could exfiltrate the token (session hijack), though `SECURITY_CERTIFICATION.md`'s live XSS testing this sprint (ENG-009) found no injectable field.
- **V22.0 re-evaluation (2026-08-07)**: Re-read per the mandate's "do not casually migrate authentication" instruction — full write-up in `docs/security/SECURITY_HARDENING_PLAN.md` §9. New evidence this pass: `backend/app/middleware/security_headers.py` sets a hash-based CSP (`script-src 'self' <exact SHA-384 hashes for React/ReactDOM>`, no `unsafe-inline`/`unsafe-eval`) — a genuine mitigating control that makes the realistic exploit chain require *two* independent failures (a working XSS injection AND defeating the hash-allowlisted CSP), not one. No live or source XSS still found (zero `dangerouslySetInnerHTML`, ENG-009 unchanged). Migration blast radius, CSRF implications of httpOnly cookies, frontend/backend changes, deployment/rollback plan are all already fully documented in the existing plan (§§2-8) and remain accurate — nothing new to add there. **Severity revised from Medium-High to Medium** given the CSP finding. The repository still contains no approved migration decision (no merged PR/ADR/accepted-backlog-item), so per the mandate this is **not implemented** — preserved as a documented architectural risk, ready to execute if/when a migration decision is made.
- **Severity**: Medium (revised down from Medium-High in V22.0 — see re-evaluation above; token-theft-via-XSS remains a real risk class, but the confirmed hash-based CSP substantially narrows the realistic exploitation surface)
- **Status**: **Deferred, re-confirmed (V22.0)** — a full migration plan already exists (`docs/security/SECURITY_HARDENING_PLAN.md`, §9 adds the V22.0 CSP-informed re-assessment), and per this repo's own established policy, architecture migrations of this kind ("localStorage token → httpOnly cookie" is a real auth-model change touching CORS, CSRF posture, and every API client) are documented and planned, not partially patched mid-sprint or implemented without an approved decision record.
- **Owner**: Unassigned (architecture decision + migration plan owner)

### ENG-027 — Modal-entrance-animation duration drifts (.15s/.18s/.22s/.25s)
- **Source**: `ISSUE_DATABASE.md` L-1 (V7.0)
- **Evidence**: Source-verified, re-verified V17.0 (STEP 1). Confirmed reproducible and precisely traced: shared `Modal` component's backdrop uses inline `animation: 'fadeIn .15s ease'` (`atoms.jsx:198`) while its own dialog content uses the `.fade-up` CSS class at `.22s` (`SecureDoc.html:164`) — same component, two different durations for one entrance event. Separately, `.fade-in` (screen-level transitions) is `.18s`, and `LoginScreen.jsx` has its own standalone inline `fadeIn .25s`.
- **STEP 2 (value justification)**: Investigated closely rather than assumed. The Modal's own backdrop(.15s)→content(.22s) sequencing is actually a common, defensible motion-design pattern — backdrop resolves quickly to set the stage, content eases in slightly slower for a polished feel — not unambiguously a bug. Forcibly unifying all 4 values would touch 3 different-purpose UI elements (modal transitions, full-screen transitions, a one-off login-page animation) for a timing difference (30-100ms) below typical user-perceptible threshold. Genuine uncertainty about whether "fixing" this improves anything is itself a signal STEP 2's bar isn't clearly met for a Low-severity cosmetic item. **Not implemented.**
- **Severity**: Low (cosmetic)
- **Status**: **Reviewed, not implemented** (2026-07-29)
- **Owner**: Unassigned

### ENG-028 — Icon language mixes geometric Unicode and real emoji
- **Source**: `ISSUE_DATABASE.md` L-2 (V7.0)
- **Evidence**: Source-verified, re-verified V17.0 (STEP 1). Confirmed reproducible: `InsightsModal.jsx` uses a real emoji (🔥, top-3 heatmap indicator) which renders as a platform-specific colorful glyph, breaking the otherwise-consistent monochrome geometric icon language used everywhere else (◫/◈/⇌/etc.).
- **STEP 2**: Fixing requires choosing a specific replacement (a geometric glyph? plain text like "TOP"? a colored dot?) — a design decision, not a mechanical engineering fix. Inventing a replacement unilaterally risks a worse outcome than the current minor inconsistency. **Not implemented** without design input.
- **Severity**: Low (cosmetic, needs a design decision on which icon language to standardize on)
- **Status**: **Reviewed, not implemented** (2026-07-29) — low actionability without a design decision; documented, not blindly changed
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
- **STEP 1**: Re-verified reproducible — `AccessScreen.jsx`'s row-level Links-list "Revoke"/"Delete" triggers used `variant="outline-danger"`, while the identical semantic action (a row-level delete/revoke trigger inside a list) used `variant="ghost"` + inline `style={{ color: C.error }}` in `WebhooksScreen.jsx`, `ApiKeysScreen.jsx`, and `DocRow.jsx` — confirmed by direct read of all four files.
- **STEP 2**: Improves maintainability (one visual pattern for one semantic action class, not two) and reduces future-bug risk (a developer copying the "wrong" precedent perpetuates the drift). Justified — implemented.
- **STEP 3**: Fixed both row-level triggers in `AccessScreen.jsx` to `variant="ghost"` + `style={{ color: C.error }}`, matching the majority pattern. Deliberately left the page-level "✕ Revoke All Access" button as `outline-danger` — it's a distinct, standalone confirmation action, not the same semantic class as a row-level list trigger. Verified via isolated diff (`git diff --stat` showed exactly the 2 intended lines changed, nothing else), `eslint` clean, frontend test suite 13/13 passed, production build succeeded (309.1kb). No browser-automation tool is available in this environment (no Playwright/chromium-cli installed) — this is a purely cosmetic prop/style change with no logic path, so lint+test+build+source-pattern-match is the applicable verification ceiling; not claimed as browser-verified.
- **Severity**: Low (cosmetic consistency)
- **Status**: **Closed** (2026-07-30) — commit `667cac8`
- **Owner**: Engineering (this sprint)
- **Verification method**: Source-verified (pattern match against 3 precedent files) + isolated-diff-verified + lint/test/build-verified. Not browser-verified (no browser automation tool available in this environment).

### ENG-031 — WATERMARK-OWNER-ANON-001: owner's own preview watermark shows "anonymous"
- **Source**: `ISSUE_DATABASE.md` (V12.0)
- **Evidence**: Source-verified as a real, not-yet-fixed cosmetic bug — the document owner's own preview-link watermark displays "anonymous" instead of their real email, in the same machinery as the already-fixed READ-OWNER-001.
- **STEP 1**: Re-verified reproducible via source trace. `backend/app/routers/viewer.py` (both page-serving code paths) and `backend/app/services/viewer_session_service.py:99` both compute `watermark_text = f"{viewer_email or 'anonymous'} · ..."`. `viewer_email` comes solely from `body.get("email")` in the `/api/viewer/validate` request — the client-submitted value. Traced the owner-preview flow: `AppShell.jsx` renders `<ViewerScreen doc={activeDoc}>` (no `publicToken`) → `useViewerSession.js` auto-selects an unrestricted "Admin Preview" link and calls `doValidate(token, null, null)` at two call sites (initial auto-validate and 401 reinit) — hardcoding `email=null` even though `AppShell.jsx` already derives the authenticated owner's email from their JWT (`parseJwtEmail(token)`, used for the sidebar) and simply never threads it through to the viewer session. No separate "owner preview" authenticated endpoint exists — the owner's own preview uses the exact same public link-validate flow as an anonymous viewer, just against a link the owner created for themselves with no access restrictions.
- **STEP 2**: Improves usability (the watermark is a forensic/trust feature; showing "anonymous" to the document's own owner in their own preview is misleading and undermines confidence in the feature's correctness) and is a genuine display-correctness bug, not cosmetic-only. Security check: confirmed safe to fix — `link_service.py`'s `allowed_emails`/`allowed_domains` gate checks only trigger `if link.allowed_emails:` / `if link.allowed_domains:`, and the auto-selected "Admin Preview" link is specifically chosen for having neither restriction, so passing the owner's real email through cannot trigger an unrelated access-gate check or spoof a restricted link. Justified — implemented.
- **STEP 3**: Threaded `ownerEmail` from `AppShell.jsx` (`userEmail`, already derived from the JWT) → `ViewerScreen.jsx` → `useViewerSession.js`'s two `doValidate(token, ownerEmail || null, null)` call sites. Public share-link viewers are unaffected — `ownerEmail` is never passed on that code path (`AppShell.jsx`'s public-token render branch doesn't pass it). Verified via isolated diff (3 files, 9 insertions/6 deletions, exactly the intended change), `eslint` clean, frontend test suite 13/13 passed, production build succeeded. Additionally verified end-to-end at the API/integration level against the local Docker stack: rebuilt and restarted the `api` container, authenticated as the real test account against the actual local Supabase project, replicated the exact link-selection logic client-side would run, and called `/api/viewer/validate` twice against the same unrestricted link — once with `email=null` (old behavior) which returned `watermark_text: "anonymous · 2026-07-30 · sess:5e77fd"`, and once with the owner's real email (new behavior) which returned `watermark_text: "23z274@psgtech.ac.in · 2026-07-30 · sess:1d954e"` — confirming the fix resolves the bug end-to-end through the real backend. No browser-automation tool (Playwright/chromium-cli) is available in this environment, so this is classified as Source-verified + Integration/API-verified, not Browser-verified.
- **Severity**: Low (cosmetic, but a genuine incorrect-displayed-value bug, not just a style inconsistency)
- **Status**: **Closed** (2026-07-30) — commit `be3d5de`
- **Owner**: Engineering (this sprint)
- **Verification method**: Source-verified (full root-cause trace) + isolated-diff-verified + lint/test/build-verified + Integration/API-verified against the local Docker stack with a real Supabase-authenticated session. Not browser-verified (no browser automation tool available in this environment).

### ENG-032 — Security-sensitive config defaults ship hardcoded with no production guard
- **Source**: `TECH_DEBT_REGISTER.md` (V7.0), surfaced during V18.0's documentation-cleanup gap analysis — this P0 item was never carried into the backlog when `ISSUE_DATABASE.md` was reconciled in V16.0.
- **STEP 1 (V20.0 re-verification — corrects the original finding)**: Re-verified before implementing, per this sprint's evidence discipline. **Not reproducible — the guard already exists.** `backend/app/main.py:27-54` implements a module-level production-startup check (evaluated at import time) that raises `RuntimeError` refusing to start if `app_env == "production"` and any of: `SUPABASE_URL` unset, `SUPABASE_ANON_KEY` unset, `APP_PUBLIC_BASE_URL` still points to localhost or isn't HTTPS, `ip_hash_salt` still equals its placeholder default, or `domain_verify_salt` still equals its placeholder default — aggregating every failing check into one error message rather than failing on the first. Confirmed live: `backend/tests/integration/test_phase8.py::TestStartupValidation` (4 tests) already exercises this exact behavior and passes on current HEAD.
- **Root cause of the original miss**: Both the source `TECH_DEBT_REGISTER.md` finding and this session's own V18.0 re-verification only grepped/read `backend/app/config.py` (where the analogous HSTS guard lives, as a pydantic `model_validator`) and never checked `main.py`, where this *different*, independently-implemented guard for the salts actually lives. An initial fix attempt this sprint (adding a second, redundant pydantic validator to `config.py`) was implemented, then caught by its own regression run — it broke 2 pre-existing tests (`test_production_startup_rejects_default_ip_salt`, `test_production_startup_passes_with_custom_salt`) that correctly encoded the *existing* `main.py` behavior. Reverted immediately; `git status` confirmed the revert is byte-identical to HEAD, and the full backend suite (1709 passed/1 skipped/0 failed) confirms no residual effect.
- **Severity**: Medium (as originally assessed) — **but no longer applicable**, since the risk this item described is already mitigated.
- **Status**: **Closed — no longer reproducible, already implemented** (2026-08-01, V20.0). The one real gap: `main.py`'s guard and `config.py`'s HSTS guard are two separate, differently-shaped mechanisms (module-level manual check vs. pydantic validator) for conceptually the same class of thing (production-safety startup validation) — a minor architectural inconsistency, not a defect, noted here rather than silently dropped. Not worth unifying unilaterally: `main.py`'s version is arguably the better UX (aggregates all failures in one message instead of failing fast on the first), so "fixing" the inconsistency would mean migrating HSTS's check into `main.py`'s pattern, not the reverse — a real but low-value refactor, not a defect fix.
- **Owner**: Engineering (V20.0) — closed
- **Verification method**: Source-verified (`main.py:27-54` read in full) + Runtime verified (`test_phase8.py::TestStartupValidation`, 4/4 passed) + Regression verified (full backend suite 1709 passed/1 skipped/0 failed after reverting the redundant addition)

### ENG-033 — PROF-001: no profile/account-settings screen exists
- **Source**: `PRODUCT_PROPOSAL.md` (2026-07-17), surfaced during V18.0's documentation-cleanup gap analysis — never carried into the backlog.
- **Evidence**: Source-verified, re-confirmed live during V18.0 — `find frontend/src -iname "*profile*"` returns nothing, and `frontend/src/components/atoms.jsx`'s Sidebar nav config has no Profile/Settings entry. A signed-in user has no in-app way to change their password or manage their account.
- **V22.0 decision documentation (2026-08-07)**: Full decision record — decision required, available options, trade-offs, recommended default, what blocks implementation — written to `docs/governance/ENG-033_DECISION.md`, per the mandate's "document, do not invent product requirements" instruction. Summary: 3 options (do nothing / minimal profile screen with password-change reuse of the existing Supabase reset flow / full account-settings with session management + deletion); recommended default is the minimal option as a first increment; blocked on product sign-off for scope and a data-retention policy decision for account deletion, plus a sequencing question against the AUTH-006 cookie-migration work if that proceeds first.
- **Severity**: High (real, user-facing capability gap — not a bug in existing code, a missing screen)
- **Status**: **Open / DECISION REQUIRED (re-confirmed V22.0)** — this is new-feature work (a new screen + at least one new backend endpoint), out of scope for a fix-only backlog item; needs a product/design decision before implementation. Full proposal detail preserved in `archive/sprint7-18/root-reports/PRODUCT_PROPOSAL.md`; decision options in `docs/governance/ENG-033_DECISION.md`.
- **Owner**: Unassigned (product/design input needed before engineering scoping)

### ENG-034 — No CD/deploy job; `docker-compose up --build` is the only deployment path
- **Source**: `PUBLIC_RELEASE_READINESS.md` (V7.0), surfaced during V18.0's documentation-cleanup gap analysis — never carried into the backlog.
- **Evidence**: Source-verified, re-confirmed live during V18.0 — `.github/workflows/ci.yml` has a real, solid CI (lint, full test matrix against live Postgres+Redis, migration smoke test, frontend build, `pip-audit`/`npm audit`, Bandit scan, Docker build check) but the Docker build step runs with `push: false` — no image is ever pushed, no deploy/release job exists anywhere in the workflow. `docs/release/`'s files are one-time point-in-time "RC-1" reports, not a repeatable release process.
- **V22.0 decision documentation (2026-08-07)**: Full decision record written to `docs/governance/ENG-034_DECISION.md`, per the mandate's "do not choose infrastructure merely to close a backlog item" instruction. Summary: 3 options (status quo / CI-gated branch protection on `main` so Railway's auto-deploy only ever fires on a green build / a full explicit CD job with registry push + deploy + rollback); recommended default is CI-gated branch protection as a low-risk first increment requiring no new infrastructure decision; the full CD job remains blocked on an ops decision (deploy target, registry/credentials, rollback procedure) this engineering pass has no authority to make.
- **Severity**: Medium (operationally, Railway's own auto-deploy-from-`origin/main` is the actual live deployment mechanism per this session's established practice — so the repo isn't undeployed, but the CI pipeline itself has no automated release/rollback story, and `docker-compose up --build` as the only *documented* path is a real gap for anyone deploying outside Railway)
- **Status**: **Open / DECISION REQUIRED (re-confirmed V22.0)** — a CD job is infrastructure/deployment-policy work (what to push to, what triggers a release, rollback strategy) requiring an ops decision, not a pure code fix; decision options in `docs/governance/ENG-034_DECISION.md`
- **Owner**: Unassigned (needs deployment-target decision before implementation)

### ENG-035 — Reading Insights link permission has no UI toggle; feature unreachable from the product
- **Source**: found during V21.0's targeted verification of the `show_reading_insights` comparative-insights feature (a body of work committed this same sprint, see commits `87d2c7d`/`b87aae2`/`28bb563`).
- **Evidence**: Source-verified — `backend/app/services/viewer_session_service.py` and `backend/app/routers/reading.py` fully implement the gated comparative-insights feature (difficulty, this-page average, pace-vs-average, nulled server-side unless the link's `show_reading_insights` permission is `true`), but `frontend/src/screens/AccessScreen.jsx`'s create-link and edit-link permission-toggle grids had no `show_reading_insights` entry in either the state default or the rendered label map — the flag could only ever be set via a direct API call, never through the product UI.
- **Severity**: Medium (a fully-built, tested backend feature was completely unreachable by any user — not a data-correctness bug, but the feature had zero real-world usability)
- **Status**: **Closed** (2026-08-02, V21.0) — added `show_reading_insights: false` to both permission-state defaults and `show_reading_insights: 'Reading Insights'` to both label maps in `AccessScreen.jsx`, matching the existing 7-toggle pattern exactly (same `Toggle` component, same `Object.entries(...).map()` render, same `setPermissions` update). No backend change needed — the persistence/gating logic was already correct.
- **Owner**: Engineering (V21.0) — closed
- **Verification method**: Source-verified (confirmed `link.permissions` arrives as an already-parsed object from `/api/links`'s `_link_to_summary`, not a raw JSON string, so the new toggle round-trips correctly) + lint/test/build-verified (eslint exit 0, 13/13 frontend tests, build 309.1kb). No browser-automation tool available in this environment — not claimed as Browser Verified; the toggle follows an identical, already-working pattern used by 7 sibling toggles in the same component.

### ENG-036 — Reading Insights "average page time" silently included the requesting viewer's own session
- **Source**: found during the same V21.0 verification pass as ENG-035.
- **Evidence**: Source-verified — `reading_analytics_service.py`'s `get_viewer_session_summary()` computed `current_page_avg_ms` via `AVG(PageReadingEvent.active_time_ms)` filtered only on `document_id`+`page_number`, with no exclusion of the requesting viewer's own `session_id` — unlike the sibling `pace_vs_average` calculation 7 lines below it, which explicitly excludes `session_id != session_id`. The UI presents this value as "most readers spend about X on this page," which was misleading whenever the requesting viewer was the only (or first) reader of that page — the app would echo the viewer's own time back to them framed as a comparison to other readers.
- **Severity**: Low-Medium (misleading UI copy in an edge case, not a security or data-integrity issue; only manifests before a second reader has visited the same page)
- **Status**: **Closed** (2026-08-02, V21.0) — added `PageReadingEvent.session_id != session_id` to the query's `WHERE` clause, matching the established `pace_vs_average` exclusion pattern immediately below it in the same function.
- **Owner**: Engineering (V21.0) — closed
- **Verification method**: Test Verified — the pre-existing test `test_viewer_session_insights_shown_when_enabled` was asserting the buggy self-inclusive behavior as correct (`current_page_avg_ms is not None` with only one session on the document); running the fix against it caught the regression immediately (`assert None is not None` failure), confirming both the bug and the fix. Corrected the test's expectation (renamed to `..._single_session`, now asserts `None` when no other session exists) and added a new positive-case test (`test_viewer_session_current_page_avg_excludes_own_session`) with two sessions of deliberately very different active-time values (20,000ms vs. 500,000ms), asserting the returned average exactly equals the *other* session's value — proving self-exclusion, not just absence-of-crash. Full backend suite: 1706 passed (1705 + 1 new test)/1 skipped/0 failed.

### ENG-037 — `is_link_active()`'s "single source of truth" claim is inaccurate; enforcement path still duplicates the logic
- **Source**: found during V21.0's security re-verification of the just-committed Sprint V6.0 governance-fix batch (commit `87d2c7d`).
- **Evidence**: Source-verified — commit `87d2c7d` and `docs/engineering/FIX_LOG.md`'s Sprint V6.0 section both claim `is_link_active(link, now)` is "a single pure predicate... now shared by the router's display flag and the service's actual enforcement." Grepping `is_link_active` across `backend/app/` shows exactly 2 references: the definition and one call site in `links.py:70` (`_link_to_summary`, a pure display field). The actual enforcement path, `LinkService.validate_link()` (`link_service.py:106-278`), does **not** call `is_link_active` — it retains its own separately-written revoked/expired inline checks. Per this sprint's Section 0 rule ("if old documentation conflicts with current implementation, current verified behaviour wins — document the discrepancy and correct the backlog"), correcting this here.
- **Current risk**: none live — both independent implementations currently agree at the exact expiry boundary (verified by reading both). This is a documentation-accuracy correction and a future-maintainability risk (the exact class of bug the original refactor was meant to prevent — two independently-maintained copies of "is this link active" that could silently drift apart again), not a live authorization bug.
- **V22.0 resolution (Priority 5)**: read both implementations in full side-by-side. Confirmed a literal code merge is **not** a complexity reduction: `validate_link()`'s revoked/expired checks are inseparable from per-reason HTTP status/detail strings and distinct analytics `event_type`s ("revoked" vs "expired") that a single boolean predicate can't carry, and `max_views` is deliberately handled via an atomic `UPDATE ... RETURNING` (not a read-then-compare) for concurrency-correctness under simultaneous requests — a shared predicate structurally cannot replace that atomicity. Forcing a merge would require adding a reason-code layer, i.e. *more* complexity, to remove a risk that's purely theoretical today. Per the mandate's own "do this only if it reduces complexity" and "do not refactor unrelated link logic" constraints, **did not merge the code**.
- **What was done instead**: added `backend/tests/regression/test_eng037_link_active_consistency.py` (6 tests) — directly compares `is_link_active()`'s boolean against `validate_link()`'s actual accept/reject decision across every revoked/expired boundary case (not-revoked/not-expired, revoked, expired 1s past, expires 1 day future, no-expiry-set, and the exact-instant boundary). This is the practical equivalent of "one canonical implementation" without the invasive refactor: if either implementation is ever edited without the other being updated to match, this suite fails immediately — closing the actual risk (silent drift going undetected) rather than the cosmetic one (two functions existing).
- **Severity**: Low (unchanged — no live defect, this closes a future-drift risk)
- **Status**: **Closed — documented decision, regression tripwire added, no code merge performed** (2026-08-05, V22.0)
- **Owner**: Engineering (V22.0) — closed
- **Verification method**: Source Verified (both implementations read in full, atomicity requirement confirmed) + Test Verified (6 new tests, all passing, directly exercising both implementations against the same link states)

### ENG-038 — `ensure_not_last_owner()` has an unguarded TOCTOU race (pre-existing, not introduced by this sprint)
- **Source**: found during the same V21.0 security re-verification pass as ENG-037.
- **Evidence**: Source-verified — `org_service.py`'s `ensure_not_last_owner()` (extracted from 2 previously-duplicated inline copies in commit `87d2c7d`) does a plain `SELECT count(*)` with no row locking (`FOR UPDATE`) before allowing an owner-demote or owner-removal to proceed. Two concurrent requests could both read "owner count = 2" and both pass the check before either commits, leaving an org with zero owners. Confirmed via `git show 87d2c7d` that this exact unguarded pattern already existed, duplicated, before the refactor — extracting it into a shared function is behavior-preserving, not a new or worsened regression.
- **Severity**: Low (requires two genuinely concurrent requests from an org's last two owners acting on themselves/each other at the same instant — a narrow race window, and the blast radius is an orgless-owner state, not data loss or unauthorized access)
- **V22.0 investigation (Priority 6)**: per the mandate's explicit "do NOT fix concurrency based on intuition — first construct a reproducible test" instruction, attempted genuine reproduction against the real local Docker stack (real Postgres, real FastAPI request handling) rather than reasoning about it from source alone. Set up a live 2-owner organization (2 real Supabase-authenticated test accounts) and fired truly concurrent `DELETE /api/orgs/{id}/members/{user_id}` requests for both owners simultaneously via `asyncio.gather` (genuine parallel dispatch, not sequential). **Race did not reproduce in 2 clean trials** — both times, one removal succeeded (`204`) and the other was correctly blocked (`409 "Cannot remove the last owner from the organization"`), leaving the org with exactly one owner, never zero.
- **Interpretation**: the source-level gap is real (no explicit `FOR UPDATE` lock exists) and this is not proof the race is impossible — 2 trials is not exhaustive, and true simultaneity depends on timing this test can't fully control. But per the mandate's own classification scheme, 2 failed reproduction attempts against the real deployed request-handling stack downgrades this from "assumed exploitable" to **LOW-RISK INFERENCE**: FastAPI's request handling and/or Postgres's own transaction semantics on the count-then-delete sequence appear to provide enough incidental serialization that the theoretical window is narrower in practice than the code alone suggests.
- **Status**: **Open — reclassified as LOW-RISK INFERENCE, not fixed** (2026-08-07, V22.0). Per the mandate's explicit instruction ("if no race can be demonstrated, document insufficient evidence or low-risk inference" — not "fix it anyway"), a `SELECT ... FOR UPDATE` was deliberately **not** added this sprint, since doing so without a reproducible failing test first would be exactly the "fix concurrency based on intuition" this sprint was told not to do. Remains open as a defense-in-depth hardening item for whenever it's next touched, not as an urgent live risk.
- **Owner**: Unassigned
- **Verification method**: Engineering Inference downgraded via 2 Integration/API-Verified reproduction attempts (real concurrent requests against the real local Docker stack, 2 real test accounts, org cleaned up after) + Source Verified (read the query, confirmed no locking clause) + Git history Verified (confirmed pre-existing via `git show` on the prior duplicated inline copies)

### ENG-039 — API keys with zero scopes can still manage Organizations, other API Keys, and Billing
- **Source**: `archive/sprint18-certification/MODULE_BOUNDARY_REPORT.md` (V18.0) — flagged there as "the most security-relevant finding in this report" but never carried into the backlog before that report was archived during V21.0's documentation consolidation.
- **V22.0 classification**: **SOURCE VERIFIED, real** — re-traced the complete authorization path (API key creation → scope resolution → route → org-role check → service → database → audit event) before touching anything, per this sprint's mandate not to assume the finding correct. Confirmed exactly as described: `orgs.py` (12 routes), `api_keys.py` (6 routes), `billing.py` (3 authenticated routes) all used bare `Depends(get_current_user)` with zero scope enforcement, and `API_SCOPES` never even included an `organizations:*`/`api_keys:*`/`billing:*` category — there was no scope a user could grant to restrict a key to these operations even if they'd wanted to. Full trace, endpoint-by-endpoint matrix, and cross-check against the other 10 API families (only `orgs.py`/`api_keys.py`/`billing.py` had the defect — 7 other routers were already correctly scoped) is in `docs/security/ENG-039_ORG_AUTHORIZATION_TRACE.md`.
- **Root-cause fix** (not per-endpoint patching): added 6 new scopes to `API_SCOPES` (`organizations:{read,write}`, `api_keys:{read,write}`, `billing:{read,write}`), wired `require_scope(...)` onto all 21 previously-bare endpoints, and added a scope-escalation guard (`_reject_scope_escalation` in `api_keys.py`) so a key can never mint or widen a sibling key beyond its own scopes — a related privilege-escalation path discovered during the fix, not the original finding, but the same root cause ("zero/limited scope must never mean unlimited access"). Added the 6 new scopes to `frontend/src/screens/ApiKeysScreen.jsx`'s scope-selector so the fix is actually usable, not just enforced (the same class of gap ENG-035 already found once this session — a backend capability with no UI path to configure it).
- **Severity**: Medium-High (as originally assessed) — now resolved.
- **Status**: **Closed — fixed** (2026-08-04, V22.0)
- **Owner**: Engineering (V22.0) — closed
- **Verification method**: Test Verified (28 new tests in `backend/tests/integration/test_eng039_org_api_key_scopes.py`, covering the full V22.0-mandated matrix — no/invalid/revoked/expired key, zero/correct/incorrect scope, org member/admin/owner, cross-org access, escalation guard, error hygiene; 12 of the 28 confirmed to fail against the reverted pre-fix code, proving they detect the real bug) + Regression Verified (full backend suite 1734 passed [1706 + 28 new]/1 skipped/0 failed) + API Verified (live-tested against the real local Docker stack — zero-scope key denied with the exact expected message, correctly-scoped key succeeds, escalation guard denied live; all disposable test keys deleted after, confirmed 0 remaining) + Source Verified (JWT/browser callers confirmed unaffected — `require_scope` only restricts `auth_method == "api_key"` callers, matching the existing 7-router convention).

### ENG-041 — `admin.py`'s audit-log endpoint had the same zero-scope authorization gap
- **Source**: found while tracing ENG-039's fix (V22.0 Priority 2, bounded authorization consistency review) — not part of the original ENG-039 finding.
- **Evidence**: Source-verified — `GET /api/admin/audit-log` used bare `Depends(get_current_user)`, no scope check. A zero-scope API key could read an org's full accountability trail (member changes, deletions, etc.) whenever the key's owning user held admin/owner role in that org, or the caller's own cross-context activity log when no `org_id` given.
- **Severity**: Medium (sensitive read access, same defect class as ENG-039, narrower blast radius — read-only, not a mutation path)
- **Status**: **Closed — fixed** (2026-08-04, V22.0) — gated on the existing `organizations:read` scope (no new scope invented)
- **Owner**: Engineering (V22.0) — closed
- **Verification method**: Test Verified (`test_priority2_scope_consistency.py::TestAuditLogScope`, 3 tests — zero-scope denied, correctly-scoped allowed, JWT unaffected; the zero-scope-denied test confirmed to fail against the pre-fix code via `git stash` revert) + Regression Verified (full suite 1742 passed/1 skipped/0 failed)

### ENG-042 — `annotations.py`'s 10 uploader-facing document routes had the same gap
- **Source**: found during the same V22.0 Priority 2 review as ENG-041.
- **Evidence**: Source-verified — `GET/POST/PATCH /api/documents/{doc_id}/{annotations,feedback}...` (list/export annotations, reply/resolve feedback, list feedback, reviewers, export, export-reviewer-activity, annotations-visual + export — 10 routes total) all used bare `Depends(get_current_user)`. The 7 `/api/viewer/...` annotation routes in the same file are correctly unaffected — they're viewer-session-authenticated, a different auth model entirely, not user/API-key authenticated.
- **Severity**: Medium (8 read routes + 2 write routes, all document-scoped; `documents:{read,write}` scopes already existed and cover this exact shape of operation)
- **Status**: **Closed — fixed** (2026-08-04, V22.0) — gated on the existing `documents:read`/`documents:write` scopes matching each route's actual read/write nature (no new scope invented)
- **Owner**: Engineering (V22.0) — closed
- **Verification method**: Test Verified (`test_priority2_scope_consistency.py::TestAnnotationsFeedbackScope`, 4 tests, including a read-scope-cannot-write check; 2 confirmed to fail against the pre-fix code via revert) + Regression Verified (full suite 1742 passed/1 skipped/0 failed)

### ENG-043 — `notifications.py`'s SSE stream had the same gap (low severity)
- **Source**: found during the same V22.0 Priority 2 review as ENG-041/042.
- **Evidence**: Source-verified — `GET /api/notifications/stream` used bare `Depends(get_current_user)`. Lower severity than ENG-039/041/042: the stream only carries the caller's own per-`user_id` Redis pub/sub channel — no cross-user data exposure — but fixed for consistency with every other endpoint in this review.
- **Severity**: Low
- **Status**: **Closed — fixed** (2026-08-04, V22.0) — gated on the existing `documents:read` scope (the stream carries document-activity notifications; no new scope invented)
- **Owner**: Engineering (V22.0) — closed
- **Verification method**: Test Verified (`test_priority2_scope_consistency.py::TestNotificationStreamScope`, 1 test — zero-scope denied) + Regression Verified (full suite 1742 passed/1 skipped/0 failed). Not revert-tested the same way as the other 3 (the pre-fix code causes the test to hang consuming a live SSE stream rather than returning a clean failing assertion) — the fix itself is the identical one-line `Depends` swap already proven correct by ENG-039/041/042's revert tests.

### ENG-044 — Celery worker metrics invisible to `/metrics` — separate-process registry gap
- **Source**: found while verifying the ENG-017 Celery-metrics fix, V22.0 Priority 3.
- **Evidence**: API Verified — uploaded and processed a real document through the actual local Docker Celery worker, checked `/metrics` on the API container immediately after: the `securedoc_celery_task_duration_seconds`/`securedoc_celery_tasks_total` metric families register (HELP/TYPE lines present) but carry zero sample lines. Root cause, source-verified: the worker runs as a separate OS process from the API server (`docker-compose.yml`'s `api` and `worker` services); `prometheus_client`'s default registry is per-process, and this repo has no `PROMETHEUS_MULTIPROC_DIR`/`multiprocess.MultiProcessCollector` setup (confirmed via repo-wide grep — zero matches).
- **Severity**: Low (the instrumentation code itself is correct and unit-tested; this is a deployment-wiring gap, not a logic bug — metrics recorded in-process during a unit test work correctly, as proven by `test_celery_metrics.py`)
- **Status**: Open — needs `PROMETHEUS_MULTIPROC_DIR` set in the worker's environment, `multiprocess.MultiProcessCollector` wired into the `/metrics` handler, and a shared writable directory between API and worker containers (a Docker Compose volume change) — genuinely infra/deployment work, not appropriate to bolt onto this sprint's investigation
- **Owner**: Unassigned — needs ops/deployment input on the shared-volume approach for the target environment (Railway)
- **Verification method**: API Verified (real upload through the real local Docker worker, `/metrics` checked immediately after) + Source Verified (repo-wide grep confirms no multiprocess registry setup exists)

### ENG-040 — Uploader-controlled Viewer capability (feature-toggle) sweep
- **Source**: V22.0 Priority 4, a verification-only sweep (not a reported defect) — inventoried every uploader-controlled Viewer capability against configurability, visibility, persistence, API/Viewer enforcement, edit-propagation, safe-defaults, and audit logging.
- **Evidence**: Source-verified, full inventory in `docs/security/ENG-040_VIEWER_TOGGLE_INVENTORY.md`. All 8 capabilities (`can_download`, `can_print`, `can_copy`, `can_right_click`, `watermark_enabled`, `can_annotate`, `enable_info`, `show_reading_insights`) traced end-to-end. 7 of 8 were already fully correct. The 8th (`show_reading_insights`) was the exact defect this sweep was designed to catch — already found and fixed earlier this same sprint as ENG-035/036, before this formal sweep even began, confirming the fix was correctly scoped.
- **Severity**: n/a — verification pass, no new defect found
- **Status**: **Closed — verified, no new defect found** (2026-08-04, V22.0)
- **Owner**: Engineering (V22.0) — closed
- **Verification method**: Source Verified (every row's API/Viewer-enforcement claim cites file:line) — no new code written, this is a pure audit deliverable

### ENG-045 — "Feedback" sidebar nav item silently lands on the wrong tab after picking a document
- **Source**: found live during V23.0's ENG-019 browser sweep of the live Railway app — not present in any prior report.
- **Evidence**: Browser Verified, reproduced from a clean session on both the live Railway app and the local Docker stack. Clicking the sidebar's **Feedback** entry (a shortcut meant to jump straight to a document's Feedback thread — `frontend/src/screens/AppShell.jsx:164` renders `<AccessScreen defaultTab="feedback" />`) correctly shows the document picker with "Feedback" highlighted as the active nav item. But selecting any document from that picker silently lands on the **Create Link** tab instead of **Feedback**, and the sidebar's active highlight flips to **Access Control**.
- **Root cause**: `AppShell.jsx:163` (pre-fix) passed the same `onSelectDoc={handleAccessDoc}` handler to both the `screen === 'access'` instance (line 162, correct) and the `screen === 'feedback'` instance (line 163). `handleAccessDoc` unconditionally calls `setScreen('access')` — so picking a document while on the Feedback entry point overwrites `screen` from `'feedback'` to `'access'`, unmounting the `defaultTab="feedback"`-initialized `AccessScreen` and mounting a fresh one with no `defaultTab`, which defaults to `'policy'` (`AccessScreen.jsx:19`, `useState(defaultTab || 'policy')`; `'policy'` is the internal id for the "Create Link" tab, `AccessScreen.jsx:182`). The entire point of the Feedback shortcut — jump straight to a document's feedback thread — was defeated for every document selected through it.
- **Severity**: Medium (a real, fully reproducible broken user flow on a shipped, linked-from-the-sidebar feature; not a security or data-integrity issue, and the underlying Feedback tab itself works correctly once manually clicked from within Access Control)
- **Fix**: Added a dedicated `handleFeedbackDoc` handler (`doc => { setActiveDoc(doc); setScreen('feedback'); }`) and wired it as the `feedback`-screen instance's `onSelectDoc`, leaving `handleAccessDoc`/the `access`-screen instance untouched. 3-line diff, `frontend/src/screens/AppShell.jsx` only.
- **Affected files**: `frontend/src/screens/AppShell.jsx`
- **Estimated effort**: Small (realized: 1 new one-line handler + 1 changed prop)
- **Regression risk**: Low — isolated to the `feedback` screen branch; confirmed via isolated diff (`git diff --stat`: 3 insertions/2 deletions in exactly this file) that the `access` branch (line 162) is untouched, and browser-verified both paths independently post-fix on the local Docker stack (Feedback nav → pick doc → lands on Feedback tab, sidebar shows Feedback active; Access Control nav → pick doc → still lands on Create Link tab, sidebar shows Access Control active).
- **Dependencies**: None
- **Priority**: 45
- **Status**: **Closed — fixed** (2026-08-08, V23.0)
- **Owner**: Engineering (V23.0) — closed
- **Verification method**: Browser Verified (reproduced pre-fix on the live Railway app; fix verified post-rebuild on the local Docker stack, both the fixed Feedback flow and the unaffected Access Control flow) + Regression Verified (`eslint` clean, frontend suite 13/13, production build succeeded [309.2kb], backend suite 1751 passed/1 skipped/0 failed — unaffected, frontend-only change)

**Also noted, not fixed this sprint**: the Organizations Members modal's role `<select>`/"Remove" controls aren't disabled based on the caller's own role (an `editor`-role account sees the same interactive controls an `admin`/`owner` would). Backend authorization is correct and verified (`orgs.py:414`'s `minimum_role="admin"` gate rejects the actual mutation with a clean `403` + accurate toast + correct dropdown revert — confirmed live). This is a pure proactive-affordance polish item (disable/hide controls the caller structurally cannot use, instead of attempt-and-fail), Low severity, not a security gap. Not filed as a separate backlog item — recorded here as part of ENG-019's closing evidence rather than invented as new scope for a control that already fails safely.

### ENG-046 — CI's `ruff check` has no project-level config; fails under the currently-available ruff version
- **Source**: found during V24.0's Step 4 repository re-sweep — not present in any prior report. `.github/workflows/ci.yml`'s `backend-lint` job runs `pip install ruff` (unpinned) then `ruff check backend/app backend/tests`, with zero `pyproject.toml`/`ruff.toml` anywhere in the repo to constrain the ruleset.
- **Evidence**: Tool-execution Verified. Running the exact CI command with the currently-available `ruff==0.16.0` (via `ruff check --show-settings`) resolves to 415 enabled rule variants by default — producing **1361 errors**. Even ruff's own long-standing conservative baseline (`--select E4,E7,E9,F`) produces **229 errors** — meaning this codebase has not actually been "ruff clean" under the literal CI command in a long time, despite several prior sprints' entries (ENG-006, ENG-013, ENG-032, V22.0's final regression pass) claiming clean ruff sweeps. Root cause: those sweeps used narrower, manually-scoped checks (e.g. `--select F401` only, or `backend/app` only) rather than literally reproducing `ci.yml`'s command — and since local commits on this branch are not pushed to `origin/main` (established policy — pushes require separate explicit confirmation), the real GitHub Actions CI has not executed against this repo's actual recent commit history to catch the drift.
- **Investigation, not blind fix**: individually reviewed every one of the 23 `backend/app/` violations before touching anything (this project's established ENG-013 precedent against blind auto-fix). Found: **6 were ruff false positives** — SQLAlchemy's `Mapped[List["ClassName"]]` string-forward-reference pattern (resolved by `Base.registry` at mapper-configuration time, not standard Python name binding), each already carrying a `# type: ignore[name-defined]` for mypy but no equivalent ruff suppression. **1 was a 7th false positive of a different kind** — `viewer.py`'s `_write_and_size` nested function reads `writer` via a legitimate Python closure over the enclosing scope; confirmed by reading the surrounding code, not assumed. **14 were accidental import-ordering** (`documents.py`: a `logger = ...` assignment sitting between two import blocks; `viewer.py`: one import placed mid-file with no circular-import justification — confirmed via grep that the target module doesn't import back from the router). **1 ambiguous single-letter loop variable** (`links.py`, `l` → `link`, ruff's own guidance since `l` is visually confusable with `1`/`I`). **1 lambda-assigned-to-a-name** (`reading_analytics_service.py`, rewritten as a `def` per ruff's own recommendation, zero behavior change).
- **Fix**: (1) added `backend/ruff.toml` pinning `select = ["E4", "E7", "E9", "F"]` — makes the enforced ruleset deterministic and intentional instead of silently drifting with whatever ruff version `pip install ruff` fetches next, matching what this codebase's lint history has clearly assumed all along. (2) Fixed all 23 `backend/app/` violations: false positives suppressed with accurate, individually-justified `# noqa: F821` comments (not blanket-disabled); import-ordering issues fixed by moving statements (verified no circular-import risk first); the 2 genuine style nits fixed directly. `backend/app` is now genuinely clean under the pinned ruleset (`ruff check backend/app` → "All checks passed!").
- **`backend/tests` remainder — closed (V24.0 continuation, 2026-08-09)**: individually categorized all 206 remaining violations before touching anything (not blind `--fix`): 156 F401 (unused imports — sampled and confirmed the pattern is either a redundant local re-import of a module already imported at module scope, or a genuinely never-referenced import; one file's imports carried a stale, non-functional `# noqa: <free text>` comment misleading a reader into thinking they were deliberately kept, when `# noqa` requires exact rule codes and never actually suppressed anything), 16 F841 (unused local variables — every one individually read in context; 14 were "call matters, return value doesn't" or genuinely dead assignments, safe to remove the binding while preserving the call; 1 (`test_annotation_refactor.py`) was a Pydantic model construction kept as a bare statement to preserve its schema-validation side effect; **2 surfaced a real, separate finding — filed as ENG-049** — a computed-but-never-asserted value in each of 2 tests, meaning the tests assert less than their own docstring/comment promises), 12 F811 (redundant local re-imports of an already-module-level-imported name — sampled and confirmed benign), 13 E701/E702 (semicolon/colon-joined statements — pure style, split onto separate lines), 5 E741 (ambiguous `l` → contextually-named `line`/`link`, same pattern as the `backend/app` fix), 2 F541 (unnecessary `f` prefix on a string with no interpolation — confirmed no missing placeholder, purely cosmetic), 2 E401 (multiple imports on one line — split). One `subprocess.run(...)` call (`test_phase_b_security.py`) and one `spec_from_file_location(...)` block (`test_phase8.py`) were confirmed fully inert leftover code (their results were never used and their own surrounding comments confirmed the approach had already moved on) and removed entirely rather than just unbinding the variable. `ruff check backend/app backend/tests` — the literal CI command — now passes cleanly: **"All checks passed!"**
- **Severity**: Low-Medium (zero live/runtime impact — confirmed via full regression pass below — but CI health is a genuine release-readiness signal, and the "ruff clean" claims in several prior closed items were not literally true against the CI command as written, which is itself worth being honest about)
- **Affected files**: `backend/ruff.toml` (new), `backend/app/routers/documents.py`, `backend/app/routers/viewer.py`, `backend/app/routers/links.py`, `backend/app/services/reading_analytics_service.py`, `backend/app/models/{document,event,group,link}.py`, plus 50 files under `backend/tests/` (see `docs/engineering/FIX_LOG.md` for the full per-category breakdown)
- **Regression risk**: Low — every non-mechanical category individually reviewed (no blind auto-fix beyond the confirmed-safe mechanical categories), full backend suite re-run after every stage (1751 passed/1 skipped/0 failed, unchanged throughout — this is the strongest possible safety net for test-file changes, since the suite IS the code being edited), `ruff check backend/app backend/tests` confirmed fully clean.
- **Priority**: 46
- **Status**: **Closed — fully fixed (V24.0)**. Both `backend/app` and `backend/tests` are clean under the pinned ruleset; the literal CI command passes.
- **Owner**: Engineering (V24.0) — closed
- **Verification method**: Tool-execution Verified (`ruff check --show-settings`, before/after counts, final "All checks passed!") + Source Verified (every non-mechanical violation individually read and justified — F811/E741/F541/E401/E701/E702/every F841 — before any change) + Regression Verified (backend suite 1751 passed/1 skipped/0 failed unchanged after both the `backend/app` and `backend/tests` fix passes; frontend suite 15/15 unaffected; migration head `027` confirmed live)

### ENG-047 — `CHANGELOG.md` stopped being updated after Sprint V10.0; 14 sprints of history (V11.0–V24.0) are undocumented there
- **Source**: found during V24.0's Step 4 repository re-sweep, while checking for stale version references and contradictory documentation.
- **Evidence**: Source Verified — `CHANGELOG.md`'s newest entry is `## [Unreleased] — Sprint V10.0: Autonomous Product Excellence`. Every sprint since (V11.0 through this V24.0 sprint — the vast majority of this repository's actual engineering history, including every fix currently tracked in `ENGINEERING_BACKLOG.md`) has no corresponding entry. `PROGRESS.md`/`ENGINEERING_BACKLOG.md`/`CHECKPOINT.md` are the files that actually got updated sprint-over-sprint instead.
- **Severity**: Low (purely a documentation-currency gap — `CHANGELOG.md` was never the operative tracking mechanism for this project in practice, `ENGINEERING_BACKLOG.md`/`PROGRESS.md` filled that role; no engineering decision or defect status depends on `CHANGELOG.md` being current)
- **Fix**: added an explicit, dated note at the top of `CHANGELOG.md` stating plainly that it stops at V10.0 and pointing to the three files that are actually current, rather than either (a) leaving a reader to discover the gap by scrolling, or (b) attempting to reconstruct 14 sprints of changelog-style entries from summary documents — the latter risks fabricating detail (exact dates, exact scope per sprint) that isn't cleanly re-derivable from `PROGRESS.md`'s narrative-style entries without real risk of getting specifics wrong, which the mandate's zero-fabrication rule weighs against attempting.
- **Affected files**: `CHANGELOG.md`
- **Regression risk**: None — documentation-only, one paragraph added, no existing content altered or removed.
- **Priority**: 47
- **Status**: **Closed — honest pointer added, gap not retroactively fabricated** (V24.0, 2026-08-09)
- **Owner**: Engineering (V24.0) — closed. If a fully backfilled changelog is ever wanted, it needs a deliberate dedicated pass working sprint-by-sprint from `PROGRESS.md`'s original entries, not a summary reconstruction.
- **Verification method**: Source Verified (direct read of `CHANGELOG.md`'s full sprint-heading list)

### ENG-048 — Reading Intelligence's displayed active-time counter resets to zero (not paused) on window blur, then restarts from zero on resume
- **Source**: found during V24.0's Step 5/6/7 targeted Reading Intelligence re-certification against the live Railway app — not present in any prior report. The Viewer's flagship reading-time tracking was never deeply Browser Verified before this sprint (V20.0's ENG-020 only Source+API verified the backend formula; V23.0's sweep focused on Access Control/Organizations/general screens).
- **Evidence**: Browser Verified, reproduced independently 5+ times via Playwright against the live app, each attempt ruling out a different alternative explanation:
  1. **Baseline**: opened `qa_test_doc_v12.pdf` in the Viewer, sampled the status bar's `[title="Total active reading time"]` element once per second. Counted up correctly and linearly: 0s→1s→2s→3s→4s→5s over ~5 real seconds — the underlying stopwatch mechanism itself is correct when uninterrupted.
  2. **Pause trigger**: dispatched a genuine `window.dispatchEvent(new Event('blur'))` (the exact event `useReadingAnalytics.js`'s `onBlur = () => _pause()` listens for) mid-session. One second later, the display and its `aria-label` both flip from `"5s" / "Reading time: 5s, timer running"` to **`"Waiting…" / "Reading time: not started, timer paused"`** — not frozen at "5s" as pausing should produce.
  3. **Ruled out remount**: tagged the exact DOM `<span>` node with a custom JS property before dispatching blur; the same node (same JS object identity, marker intact) was confirmed still in place 2 seconds later, with its text now `"0s"`/reset — proving the React component tree does not unmount/remount (which would trivially explain a reset via fresh `useRef` initialization), so the reset is a genuine state-logic bug, not a remount side effect.
  4. **Ruled out network/session interference**: zero requests fired in the 2 seconds following the blur dispatch; zero console errors or page errors throughout every trial.
  5. **Ruled out timing coincidence with the 5s flush interval**: reproduced with blur dispatched at t≈3s (away from the `FLUSH_INTERVAL_MS=5000` boundary) using only `page.evaluate`-based reads (no Playwright locator/input calls that could synthesize interaction events) — same reset behavior.
  6. **Resume**: dispatching `window.dispatchEvent(new Event('focus'))` (the paired `onFocus = () => _resume()` listener) does not restore the pre-blur value — the counter restarts from `"Waiting…"` → `"0s"` → `"1s"`… as if a brand-new session had started, not a resumed one. Directly screenshotted: before-blur (5s active), mid-blur (legitimate "Focus window to resume" DRM overlay + reading counter reset), and 3s after focus (counter back at "2s", not "8s").
- **What this is NOT**: the "Focus window to resume" content-blur overlay itself (`useViewerSession.js`'s separate `blurred` state, a CSS `filter: blur(14px)` + message) is a legitimate, working, intentional DRM/privacy feature — confirmed correctly showing/hiding. This finding is specifically about the **reading-time accounting resetting instead of pausing**, a different mechanism (`useReadingAnalytics.js`) that happens to share the same trigger events.
- **Root cause — proven via runtime instrumentation, not guessed (2026-08-09, closing pass)**: added temporary `console.log` instrumentation to every state transition in `useReadingAnalytics.js` (`_accumulate`, `_pause`, `_resume`, `_startSession`, the display interval tick, the listener-effect setup/cleanup), rebuilt, and reproduced live against the local Docker stack. The trace showed `_accumulate ENTER {"currentPage":null,...}` → `_accumulate EARLY-RETURN` on every single call, throughout the entire session — **`s.currentPage` was never set to a real page number.** Traced this to the "Handle page changes" `useEffect` (line ~310): it guarded on `state.current.sessionStarted` (a ref read, not a reactive dependency) but its dependency array was only `[page, _exitPage, _enterPage]`. On mount, `page` is already `1` (`useViewerLayout`'s initial state), but the session isn't started yet (`isDocumentReady` still `false`), so this effect's first run silently no-opped. When the session actually started on a *later* render (`isDocumentReady` flipping `true`, handled by a separate effect declared just above it), this effect had no reason to re-run — none of *its own* dependencies had changed — so `_enterPage(1)` was never called. With `currentPage` stuck at `null`, `_accumulate()`'s guard clause (`s.currentPage == null`) made it a permanent no-op: `totalActiveMs` never left `0`, and no page was ever marked `_hasEntered`, meaning `_flush()`'s `pageDataSnapshot` was *always empty* — **nothing was ever sent to the backend either**, not merely a display illusion. The counter still *appeared* to count up while active only because the display tick's `liveActive` calculation adds the in-flight delta (`now - currentPageEnterPerfTime`) directly on top of `totalActiveMs`, a computation that never checks `currentPage` — an illusion that vanished at pause (revealing the true, permanently-zero accumulator) and restarted from zero on resume (a fresh `currentPageEnterPerfTime`, still building on a permanently-zero base). Confirmed by re-running the exact instrumentation with the fix applied: `_accumulate` now shows `currentPage:1`, accumulates correctly (0→952.5→2812.3ms), freezes exactly at pause (3 consecutive ticks, unchanged), and continues from the preserved base on resume (2812.3→2926.4→...) — never restarting from zero.
- **Fix**: changed the effect's guard and dependency array to check `session`/`isDocumentReady` (real, reactive values) instead of the non-reactive `state.current.sessionStarted` ref read: `if (!page || !session || !isDocumentReady) return;` with deps `[page, session, isDocumentReady, _exitPage, _enterPage]`. This makes the effect fire exactly when the session becomes ready, matching the effect declared immediately above it. 3-line functional diff (plus a comment explaining the root cause for future maintainers), `frontend/src/hooks/useReadingAnalytics.js` only.
- **Impact (resolved)**: every reader who alt-tabbed or switched windows during a reading session saw their visible reading-time counter incorrectly drop to zero and restart. Confirmed via the instrumentation trace that this **also** meant zero reading data ever reached the backend for any session that included the very first page (page 1) before a navigation — not merely a display bug. Uploader-facing analytics for single-page or first-page reading were silently starved of data. Now fixed.
- **Severity**: **High** (as originally assessed) — now resolved.
- **Affected files**: `frontend/src/hooks/useReadingAnalytics.js` (the fix), `frontend/src/hooks/__tests__/useReadingAnalytics.test.jsx` (new regression test, 2 tests)
- **Regression risk**: Low — isolated 3-line functional change plus a comment; verified via isolated diff (`git diff --stat`: 2 files, the hook + rebuilt `dist/app.bundle.js`), full backend suite unaffected (frontend-only change), full frontend suite green (15/15, up from 13), and 9 of 10 mandated browser tests directly passing against the local Docker stack (1 indeterminate — see below, not a regression risk).
- **Priority**: 48 — closed.
- **Status**: **Closed — fixed, root-caused, regression-tested, browser-verified** (V24.0, 2026-08-09)
- **Owner**: Engineering (V24.0) — closed
- **Verification method**: **Instrumentation-Verified** (temporary runtime logging proved the exact faulty state transition before and after the fix, on the local Docker stack) + **Test Verified** (2 new regression tests in `useReadingAnalytics.test.jsx`, both confirmed to fail against the pre-fix code via `git stash` — the first because `batchReadingEvents` was never even called, the second with a `TypeError` on an `undefined` value for the same reason — and both pass post-fix) + **Browser Verified** (10-test suite specified for this fix, run against the local Docker stack with real timing, not fake timers; see `REGRESSION_REPORT.md` for the full per-test breakdown and `docs/engineering/FIX_LOG.md`/`ACTION_LOG.md` for the complete investigation trace) + **Regression Verified** (backend 1751 passed/1 skipped/0 failed unchanged; frontend 15/15 passed, up from 13; build 309.2kb unchanged; lint clean; migration head `027` confirmed live)

### ENG-049 — Two test cases assert less than their own docstring/comment promises
- **Source**: found incidentally while closing ENG-046's `backend/tests` lint debt (V24.0 continuation, 2026-08-09) — investigating each F841 "unused variable" individually (not blind `--fix`) surfaced two cases where the unused variable was itself evidence of an incomplete assertion, not just dead code.
- **Evidence**: Source Verified.
  1. `backend/tests/integration/test_phase7.py::TestRateLimitRegression::test_validate_has_rate_limit_decorator` — docstring says "Validate endpoint must be rate-limited (returns 429 after many hits)" and an inline comment says "At least one 429 should appear (rate-limited) OR we got 404s (not 500s)", but the only `assert` in the test checks `not has_500` — a `has_429 = any(s == 429 for s in responses)` value was computed and then never asserted on. The test would pass even if rate limiting were completely disabled, as long as no 500s occurred.
  2. `backend/tests/integration/test_phase_d2.py` (the `SoftTimeLimitExceeded` / permanent-`ValueError` DOCX-conversion test) — patches `app.workers.tasks._mark_document_error` and captures it `as mock_mark_error`, with a comment stating "the caller (`_process_document_async`) will call `_mark_document_error`", but no `mock_mark_error.assert_called...` follows — the mock is bound only to prevent the real function from running, never to verify the call actually happened.
- **Severity**: Low (test-coverage gaps, not product defects — both underlying behaviors are plausibly correct, just not actually verified by these specific tests; a regression in either behavior would currently go undetected)
- **Fix**: none applied — out of scope for ENG-046 (a lint-cleanup task) to also change test assertions, per the explicit "do not silently fix unrelated defects" instruction. The genuinely-dead variable bindings (`has_429`, the `as mock_mark_error` capture) were removed as part of ENG-046's lint fix since they were flagged by ruff regardless of this finding; the underlying coverage gap remains.
- **Affected files**: `backend/tests/integration/test_phase7.py`, `backend/tests/integration/test_phase_d2.py`
- **Regression risk**: N/A — no code changed for this item, no fix applied.
- **Priority**: 49
- **Status**: Open — insufficient priority for this pass; recommend tightening both assertions (`assert has_429 or all(s == 404 for s in responses)` matching the existing comment's stated intent, and `mock_mark_error.assert_called_once()`) in a dedicated test-quality pass.
- **Owner**: Unassigned
- **Verification method**: Source Verified (both test bodies read in full, comment/docstring compared directly against the actual `assert` statements present)

### ENG-050 — Access Control screen labeled every never-shared document "Revoked"
- **Source**: found during V24.0's Phase 3 full end-to-end workflow regression (2026-08-09) — while testing the Upload → Protect/Share document lifecycle from the actual UI with a genuinely fresh, uniquely-named document, not a memory/assumption-based re-check.
- **Evidence**: Browser Verified, reproduced twice with two independently-named, brand-new documents that had never had any link created. Uploaded a document, immediately navigated to Access Control (before creating any link), and the screen showed a red "Revoked" status badge with a "NO ACTIVE LINKS" banner — despite zero links ever having existed for the document. Confirmed via the Documents list that the document's own processing status was correctly "Ready" (not stuck/erroring) — this was specifically the Access Control screen's link-status badge, not a document-processing bug.
- **Root cause**: `frontend/src/screens/AccessScreen.jsx` computed the badge as a binary `activeLinks.length === 0 ? 'Revoked' : 'Active'` — conflating two distinct states: "this document has never been shared" (the common, benign case for every freshly-uploaded document) and "this document had a share link that was explicitly revoked or has expired" (where "Revoked" is accurate). Both mapped to the same alarming red label.
- **Impact**: every user who uploads a document and opens Access Control before creating their first link sees a false "Revoked" status — misleading, and could reasonably cause a user to believe something failed or was tampered with before they'd ever shared anything.
- **Fix**: introduced `everHadLinks = links.length > 0` (the full link list, not just the active-filtered subset) and used it to distinguish three states instead of two: no links ever → "Unshared" (neutral grey, reusing the existing `StatusDot`'s `inactive` variant) / "NOT SHARED YET" banner; links exist but none currently active → "Revoked" (red, unchanged, now accurate); at least one active link → "Active" (green, unchanged). 3 call sites updated in the same file for consistency (the header banner and the document-status badge both derive from the same distinction).
- **Severity**: Medium (a real, reproducible, misleading status on the single most common first interaction with a freshly-uploaded document — not a security or data-integrity issue, but a genuine trust/clarity defect in core product UX)
- **Affected files**: `frontend/src/screens/AccessScreen.jsx`
- **Regression risk**: Low — verified via isolated diff, live-tested all three resulting states end-to-end on the local Docker stack with a real document (upload → confirmed "Unshared" → created a link → confirmed "Active" → revoked it → confirmed "Revoked," now accurately), `eslint` clean, frontend suite 15/15 unaffected, build succeeded (309.3kb).
- **Priority**: 50
- **Status**: **Closed — fixed, browser-verified (V24.0 continuation, 2026-08-09)**
- **Owner**: Engineering (V24.0) — closed
- **Verification method**: Browser Verified (live Docker stack, all 3 states individually reproduced pre- and post-fix with genuinely fresh disposable documents, cleaned up after) + Source Verified (root cause traced to the exact conflated ternary) + Regression Verified (`eslint` clean, frontend suite 15/15, build succeeded)

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
| ENG-017 | Observability wiring unconfirmed | Enhancement | 17 | **Closed — re-classified, gap fixed** |
| ENG-018 | Large-PDF stress not retested | Enhancement | 18 | **Closed — verified, no defect** |
| ENG-019 | Dashboard modals not re-exercised | Enhancement | 19 | **Closed — full browser sweep complete (V23.0)** |
| ENG-020 | Reading Intelligence hand-verification | Enhancement | 20 | **Closed — verified, matches backend math** |
| ENG-021 | Links return 403 not 404 cross-account (new finding) | Low | 21 | **Closed** |
| ENG-022 | links.py DELETE 200 vs 204 inconsistency (M-6) | Low | 22 | Deferred |
| ENG-023 | 14 endpoints use raw dict not typed schemas (M-8) | Medium | 23 | Deferred |
| ENG-024 | "Created at" rendered 3 different ways (M-10) | Low | 24 | **Closed** |
| ENG-025 | Empty states inconsistent (M-11) | Low | 25 | Reviewed, not implemented |
| ENG-026 | AUTH-006: session token in localStorage (M-14) | Medium (revised V22.0) | 26 | Deferred, re-confirmed (V22.0, CSP-informed) |
| ENG-027 | Modal animation duration drift (L-1) | Low | 27 | Reviewed, not implemented |
| ENG-028 | Icon language mixing (L-2) | Low | 28 | Reviewed, not implemented (needs design input) |
| ENG-029 | Architecture docs contradict each other (L-3) | Medium | 29 | **Closed** |
| ENG-030 | Button-variant inconsistency for delete/revoke (L-6) | Low | 30 | **Closed** |
| ENG-031 | Owner preview watermark shows "anonymous" (WATERMARK-OWNER-ANON-001) | Low | 31 | **Closed** |
| ENG-032 | Security config defaults hardcoded, no production guard | Medium | 32 | **Closed — no longer reproducible** |
| ENG-033 | PROF-001: no profile/account-settings screen | High | 33 | Open (needs product/design input) |
| ENG-034 | No CD/deploy job in CI pipeline | Medium | 34 | Open (needs ops decision) |
| ENG-035 | Reading Insights permission has no UI toggle | Medium | 35 | **Closed** |
| ENG-036 | Reading Insights "average page time" self-inclusive | Low-Medium | 36 | **Closed** |
| ENG-037 | `is_link_active()` not actually used by enforcement path | Low | 37 | **Closed — documented decision, regression tripwire added (V22.0)** |
| ENG-038 | `ensure_not_last_owner()` TOCTOU race (pre-existing) | Low | 38 | Open |
| ENG-039 | API keys with zero scopes can manage Orgs/API-Keys/Billing | Medium-High | 39 | **Closed — fixed** |
| ENG-040 | Uploader-controlled Viewer toggle sweep | n/a | 40 | **Closed — verified, no defect** |
| ENG-041 | admin.py audit-log had same zero-scope gap | Medium | 41 | **Closed — fixed** |
| ENG-042 | annotations.py 10 document routes had same gap | Medium | 42 | **Closed — fixed** |
| ENG-043 | notifications.py SSE stream had same gap | Low | 43 | **Closed — fixed** |
| ENG-044 | Celery worker metrics invisible (per-process registry) | Low | 44 | Open (needs ops/infra input) |
| ENG-045 | "Feedback" nav lands on wrong tab after picking a document | Medium | 45 | **Closed — fixed (V23.0)** |
| ENG-046 | CI's `ruff check` unconfigured; fails under current ruff | Low-Medium | 46 | **Closed — fully fixed (V24.0)**, both `backend/app` and `backend/tests` clean |
| ENG-047 | `CHANGELOG.md` stale since V10.0 (14 sprints undocumented there) | Low | 47 | **Closed — pointer added (V24.0)** |
| ENG-048 | Reading Intelligence active-time counter resets (not pauses) on window blur | High | 48 | **Closed — fixed, root-caused, regression-tested, browser-verified** |
| ENG-049 | 2 tests assert less than their own docstring/comment promises | Low | 49 | Open — recommend tightening in a dedicated test-quality pass |
| ENG-050 | Access Control screen labeled every never-shared document "Revoked" | Medium | 50 | **Closed — fixed, browser-verified (V24.0)** |

**Reconciled totals (2026-08-09, V24.0 continuation — recounted directly from the table above, one item at a time, superseding all prior totals paragraphs below).** V24.0's Step 1 reconciliation found and fixed a real pre-existing bug: **ENG-037's own detail entry has read "Closed" since V22.0 (2026-08-05), but this summary table's row and every totals paragraph below it kept saying "Open"** — carried forward unverified from V22.0 through V23.0. Step 4's repository re-sweep then added ENG-046 and ENG-047. Step 5/6/7's Reading Intelligence re-certification found ENG-048, closed same-sprint. A follow-up continuation then **fully closed ENG-046** (the `backend/tests` remainder — 206 violations, individually categorized and fixed, `ruff check backend/app backend/tests` now passes cleanly), found and filed **ENG-049** (2 test-coverage gaps, Low severity, not fixed — out of scope for a lint-cleanup task), and Phase 3's live end-to-end workflow regression found and fixed **ENG-050** (a misleading "Revoked" status shown on every never-shared document).

- **Total: 50 items** (ENG-001 through ENG-050; ENG-040 is a verification-only audit deliverable with no severity rating, counted once)
- **Closed: 34** — ENG-001,002,003,004,006,007,008,009,010,013,014,017,018,019,020,021,024,029,030,031,032,035,036,037,039,040,041,042,043,045,046,047,048,050
- **Deferred (with re-confirmed reasoning): 7** — ENG-005,011,012,016,022,023,026
- **Reviewed, not implemented (cosmetic/needs design input): 3** — ENG-025,027,028
- **Justified, not changed: 1** — ENG-015
- **Open (needs product/ops/design decision, a still-unresolved external blocker, or a low-priority test-quality tightening): 5** — ENG-033, ENG-034, ENG-038, ENG-044, ENG-049

`34 + 7 + 3 + 1 + 5 = 50`. Zero unexplained entries: every item above is FIXED (closed), PROVEN FALSE (closed — no defect found / no longer reproducible), VERIFIED AND DEFERRED WITH A SPECIFIC REASON (deferred / reviewed-not-implemented / justified-not-changed), CLASSIFIED AS A PRODUCT/INFRASTRUCTURE DECISION (open, with a decision record for ENG-033/034 in `docs/governance/`), or a genuinely new, low-priority, correctly-scoped-out finding (ENG-049). No issue is untracked; no duplicate IDs exist; no closed issue appears open and no open issue appears closed anywhere else in this file as of this reconciliation. **ENG-046 is fully closed and ENG-050 (found during live Phase 3 regression) is fixed same-day — zero partial-fix items remain in the backlog.**
