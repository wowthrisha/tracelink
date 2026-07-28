# Action Log — V10.0 Autonomous Product Excellence

Format per entry: Timestamp / Module / Screen / Observation / Root Cause / Decision / Files Modified / Tests Executed / Result / Next Action.

---

### Entry 1

- **Timestamp**: 2026-07-23T00:00
- **Module**: Session bootstrap
- **Screen**: N/A
- **Observation**: Starting V10.0 with a large, already-evidenced backlog from V6.0/V7.0 governance sprints (see `ISSUE_DATABASE.md`) rather than needing fresh discovery for most known issues.
- **Root Cause**: N/A
- **Decision**: Set up the 10 required tracking files under `docs/engineering/` (appending to the one pre-existing file, `FIX_LOG.md`, from a much earlier Jun-30 sprint rather than overwriting it). Consolidated all known open issues into `ISSUE_DATABASE.md` with severity and status. Recorded deliberate non-fixes in `ARCHITECTURE_DECISIONS.md` upfront so the fix loop below only touches items genuinely safe to auto-fix.
- **Files Modified**: `docs/engineering/{SESSION_STATE,ISSUE_DATABASE,TODO_QUEUE,ARCHITECTURE_DECISIONS,SCREENSHOT_INDEX,TEST_HISTORY,REGRESSION_LOG,UI_CHANGELOG,ACTION_LOG}.md` created.
- **Tests Executed**: Backend baseline confirmed — 1702 passed, 1 skipped.
- **Result**: Bootstrap complete.
- **Next Action**: Begin TODO_QUEUE item 1 (H-1: broken shake animation).

### Entry 2

- **Timestamp**: 2026-07-23T00:05
- **Module**: Viewer
- **Screen**: ViewerScreen / AccessGate
- **Observation**: Worked H-1 and H-2 from the queue.
- **Root Cause**: H-1 — `AccessGate.jsx:41` references `animation: 'shake .4s'` but `@keyframes shake` was never defined in the shared stylesheet. H-2 — believed missing per V7.0 research, but direct code read found `useViewerLayout.js:70-96` already registers a working `window` keydown listener for ArrowRight/ArrowDown/ArrowLeft/ArrowUp → goNext/goPrev, wired from `ViewerScreen.jsx:79`. The prior research agent's grep simply missed this hook file.
- **Decision**: H-1 fixed (added the missing keyframe). H-2 is a false positive — corrected in `ISSUE_DATABASE.md` rather than implementing a duplicate, conflicting listener.
- **Files Modified**: `frontend/SecureDoc.html` (added `@keyframes shake`).
- **Tests Executed**: pending batch run (see next entry).
- **Result**: H-1 fixed; H-2 closed as false-positive, no code change.
- **Next Action**: H-3 — migrate hand-rolled modals onto the shared `Modal` component.

### Entry 3

- **Timestamp**: 2026-07-23T00:35
- **Module**: Backend / Viewer, Backend / Config
- **Screen**: N/A (backend)
- **Observation**: Worked M-1 (Toggle aria-label), M-2 (aria-label audit), H-6 (config salt enforcement), H-7 (blocking PDF write).
- **Root Cause**: M-1 — `AccessScreen.jsx`'s two `Toggle` usages never passed the `label` prop despite `labelText` being in scope at both sites. H-7 — `viewer.py:download_document`'s final PDF write (`writer.write(tmp_f)`) was synchronous and blocked the event loop, unlike the per-page watermarking step one call above it which correctly used `run_in_executor`.
- **Decision**: M-1 fixed (trivial, 2 call sites). M-2 investigated and closed as not-actionable — every control on the 6 flagged screens already has an accessible name via visible text; AppShell has no interactive controls of its own. H-6 investigated and found to be a **false positive** — `main.py:27-54` already enforces this exact production-safety check (found only after I'd already added a redundant duplicate validator to `config.py`, which I then reverted rather than ship duplicated validation logic). H-7 fixed — wrapped the write in `run_in_executor`, mirroring the existing pattern one line above it.
- **Files Modified**: `frontend/src/screens/AccessScreen.jsx` (M-1), `backend/app/routers/viewer.py` (H-7). `backend/app/config.py` was edited then reverted (H-6, net no change).
- **Tests Executed**: Backend full suite 1702 passed/1 skipped (both after the H-7 fix and after reverting the H-6 attempt). Frontend build/test pending next batch.
- **Result**: 2 real fixes shipped (M-1, H-7); 2 false-positive findings corrected in `ISSUE_DATABASE.md` (H-6, and M-2 downgraded to non-actionable) rather than acted on blindly.
- **Next Action**: M-4 — add loggers to the 6 silent-except routers.

### Entry 4

- **Timestamp**: 2026-07-23T01:10
- **Module**: Backend / Links, Backend / Webhooks
- **Screen**: N/A (backend)
- **Observation**: Completed M-4 investigation across all 15 silent-except sites in the 6 flagged routers.
- **Root Cause**: 11 of 15 sites wrap `log_audit_event`, which already self-logs internally — not actually silent. 2 are benign fallback patterns not worth logging. 2 are genuinely silent: `links.py`'s custom-domain lookup and `webhooks.py`'s test-ping Celery dispatch.
- **Decision**: Fixed the 2 genuine gaps with loggers + targeted log lines; left the other 13 unchanged (verified non-issues, not fixed defensively).
- **Files Modified**: `backend/app/routers/links.py`, `backend/app/routers/webhooks.py`.
- **Tests Executed**: Full backend suite, 1702 passed, 1 skipped.
- **Result**: 2 real silent-failure gaps closed; `ISSUE_DATABASE.md` corrected to reflect the true scope (2 real issues, not 15).
- **Next Action**: M-3 (spacing tokens) and M-9 (toast severity), then move to the broader workflow-completion and non-technical-user review pass.

### Entry 5

- **Timestamp**: 2026-07-24T00:00
- **Module**: Frontend / multiple screens (Access, Analytics, Upload, API Keys, Webhooks, Organizations, Audit Log, Billing)
- **Screen**: AccessScreen, AnalyticsScreen, UploadScreen, ApiKeysScreen, WebhooksScreen, OrgsScreen, AuditLogScreen, BillingScreen
- **Observation**: Ran TODO_QUEUE.md item 11 (non-technical-user terminology pass) via a research agent auditing all 12 screens for jargon (DRM, watermarking, API keys, webhooks, organizations, audit log) shown to users with no plain-language explanation. Agent returned 22 findings/OK items across 8 screens, capped and prioritized by traffic.
- **Root Cause**: The app already has good conventions for this (a `hint` prop on `Field`, a `tooltip`/`title` pattern on Analytics' `KpiCard`) but they weren't consistently applied — several jargon terms (Watermark toggle, IP Allowlist, Scopes, "DRM events" in a tooltip meant to explain DRM) shipped with zero or self-referential explanation. Also found, while in `AccessScreen.jsx`'s permission grid: a third unlabeled `Toggle` call site (in the edit-link modal) that M-1's earlier `replace_all` fix missed because its formatting didn't match the search pattern — a real accessibility gap, not part of this terminology pass's original scope.
- **Decision**: Fixed 9 of the highest-traffic/highest-severity findings by extending existing patterns (added a `PERMISSION_HINTS` map + `title` attrs to both `AccessScreen.jsx` permission grids, reworded the IP Allowlist hint, fixed the missed third `Toggle` label, removed self-referential "DRM events" from the Analytics tooltip, added a matching tooltip to `StatCard` for Upload's Blocked Attempts stat — additive `tooltip`/`title` prop, no existing stat cards broken since the prop is optional, added a Scopes explainer line to both API Keys modals, led the Webhooks info card with a plain definition before the HMAC/payload details, added an "optional, skip if working alone" clause to the Organizations subtitle, reframed the Audit Log subtitle around user intent, added a Watermarking row hint to the Billing plan comparison). Left `StorageScreen.jsx`'s "Storage by Organization" header (low-traffic, multi-org-only edge case) and the two developer-facing API Keys/Webhooks info cards' remaining technical detail (Bearer auth syntax, HMAC signing detail) unchanged — those screens are inherently for technical integrators, so the jargon there is appropriate rather than a defect.
- **Files Modified**: `frontend/src/screens/AccessScreen.jsx`, `frontend/src/screens/AnalyticsScreen.jsx`, `frontend/src/screens/UploadScreen.jsx`, `frontend/src/components/upload/StatCard.jsx`, `frontend/src/screens/ApiKeysScreen.jsx`, `frontend/src/screens/WebhooksScreen.jsx`, `frontend/src/screens/OrgsScreen.jsx`, `frontend/src/screens/AuditLogScreen.jsx`, `frontend/src/screens/BillingScreen.jsx`.
- **Tests Executed**: Frontend suite 13/13 passed; production build clean (309.8kb, up from 308.4kb — expected, added copy).
- **Result**: 9 real plain-language/accessibility gaps closed (including 1 previously-missed unlabeled `Toggle`), all additive and zero-risk (optional props, new hint text, no renamed identifiers or removed functionality). TODO_QUEUE.md item 11 substantially addressed for the highest-traffic screens; full 12-screen sweep intentionally scoped to what a bounded research pass could responsibly cover in one session.
- **Next Action**: TODO_QUEUE.md items 12-14 (full 14-workflow walkthrough, per-button validation audit, dead-code re-sweep) remain queued and unstarted.

### Entry 6 — Sprint V11.0 (2026-07-25)

- **Timestamp**: 2026-07-25T00:00
- **Module**: Backend (`reading_analytics_service.py`, `reading.py`, `viewer_session_service.py`) + Frontend (`ViewerScreen.jsx`, `useReadingAnalytics.js`, `ReadingStatusBar.jsx`, `AccessScreen.jsx`, `ViewerErrorBoundary.jsx`)
- **Screen**: Viewer (owner preview + public share-link), Access Control (permissions grid, both Create-Link and Edit-Link forms)
- **Observation**: Mission asked for a from-scratch "Adobe Acrobat + DocSend + Kindle" Viewer redesign. A research pass before writing any code found the backend Reading Intelligence Engine and the frontend reading status bar already fully built from an earlier sprint. Scoped remaining work to 4 real, verifiable items: (1) the Insights modal had no ownership check and would 401+force-reload a public viewer who clicked it; (2) no viewer-facing panel existed for reading difficulty/this-page-average/pace-vs-average (only computed server-side for uploader-only endpoints); (3) no permission existed to let uploaders control (2); (4) the error boundary rendered raw error text to users.
- **Root Cause**: (1) `hasInsights`/modal-render condition checked only `doc?.id || session?.document_id`, never `publicToken`. (2)/(3) genuinely missing — never built. (4) `String(this.state.error)` rendered directly.
- **Decision**: Fixed all 4. For (2)/(3), extended the *existing* `/api/reading/session/{id}` endpoint and the *existing* `ShareLink.permissions` pattern rather than building new infrastructure — see `ARCHITECTURE_DECISIONS.md` AD-7 for why a generic feature-toggle framework was explicitly not built. Caught a real bug mid-implementation: `ShareLink.permissions` is a JSON string column, not a dict — first draft would have crashed every request; fixed before any test ran.
- **Files Modified**: `backend/app/services/reading_analytics_service.py`, `backend/app/routers/reading.py`, `backend/app/services/viewer_session_service.py`, `frontend/src/screens/ViewerScreen.jsx`, `frontend/src/hooks/useReadingAnalytics.js`, `frontend/src/components/ReadingStatusBar.jsx`, `frontend/src/screens/AccessScreen.jsx`, `frontend/src/components/ViewerErrorBoundary.jsx`. Tests: `backend/tests/integration/test_reading_api.py` (+2 new tests).
- **Tests Executed**: Backend full suite 1705 passed (was 1703), 1 skipped, 0 failed. Frontend suite 13/13 passed at every step. Build clean (312.2kb final).
- **Result**: 4 real items shipped and verified. 5 mission items deliberately not built this sprint, each with documented reasoning (`ARCHITECTURE_DECISIONS.md` AD-7 through AD-11) rather than shipped shallow/unverified.
- **Next Action**: none queued from this sprint — the remaining mission scope (generic toggle framework, device/geo capture, replay, trend charts, blanket UI review) each needs a product decision or its own dedicated sprint before engineering work should start, per `CHECKPOINT.md`.

### Entry 7 — Sprint V12.0 (2026-07-26)

- **Timestamp**: 2026-07-26T00:00
- **Module**: Backend (`links.py`, `models/audit.py`) + live verification across Viewer, Access Control, Reading Intelligence, Accessibility
- **Screen**: Viewer (owner + anonymous), Access Control (Create Link, Edit Link, Links list), Audit Log, sidebar navigation
- **Observation**: Mission mandated re-verifying everything live, browser-first, trusting no prior report. Re-checked all 3 V10.0 fixes — found they're already live in production (the fix commit `e7ddf47` had been pushed, apparently by the user outside this conversation, and Railway auto-deployed it). Deep-tested the Viewer (search/zoom/keyboard/fullscreen/links/thumbnails/annotations) — all correct. Attempted to verify Access Control permission propagation; corrected a wrong assumption about the Create-Link form being a live document default (it's draft state), then properly tested Edit Link on an existing link, confirming live propagation across two browser sessions. While confirming this reached the Audit Log, found it didn't — for ANY link action, ever.
- **Root Cause**: `log_audit_event()` only flushes, never commits (by design, so callers control the transaction). 3 of `links.py`'s 4 audit-logging call sites (`create_link`, `revoke_link`, `update_link`) called it *after* their primary action had already committed its own transaction, with no subsequent commit for the audit entry — so it was added, flushed, and then silently rolled back when the request-scoped session closed. The local test suite's shared-session fixture masked this exact failure mode (a flushed-but-uncommitted row is still visible to an in-test query on the same session).
- **Decision**: Fixed all 3 call sites with an added `await db.commit()`. Added the 3 missing link event types (`link.created`, `link.updated`, `link.deleted`) to `AUDIT_EVENT_TYPES` so they're also selectable as explicit filters, not just visible in the unfiltered list. Added 3 regression tests using a rollback-based verification technique specifically designed to catch this class of bug (distinguishing "flushed" from "committed" within the shared test-session fixture) — and proved they're meaningful by reverting the fix via `git stash`, confirming all 3 fail, then restoring the fix and confirming all 3 pass.
- **Files Modified**: `backend/app/routers/links.py`, `backend/app/models/audit.py`, `backend/tests/regression/test_link_lifecycle.py`.
- **Tests Executed**: Full backend suite 1708 passed (up from 1705), 1 skipped, 0 failed.
- **Result**: 1 real, security-relevant bug found, root-caused, and fixed — the audit trail for every link lifecycle action was completely non-functional in production despite the code appearing correct on read. Also: extensive positive verification (Reading Intelligence pause/resume-on-blur plus an undocumented content-blur security feature, real non-fabricated uploader-side reading data, working keyboard-only navigation, intentional mobile block). One low-severity cosmetic item noted (owner-preview watermark shows "anonymous") but not fixed this sprint.
- **Next Action**: deploy the accumulated local-only fixes (V11.0's viewer-insights/error-boundary work, V12.0's audit-commit fix) — none of this sprint's findings help a real user until they ship. Beyond that, the product/architecture decisions already queued in `REMAINING_DECISIONS.md` are the limiting factor, not further find-and-fix passes.

### Entry 8 — Sprint V13.0, Scalability Certification (2026-07-26)

- **Timestamp**: 2026-07-26T01:00
- **Module**: Full backend architecture review (database, caching, workers, storage, observability)
- **Observation**: User redirected from a live security-boundary probe (interrupted) to an explicit, tightly-scoped ask: an architecture-only scalability certification, no synthetic load against production, findings labeled by evidence type (browser-verified / source-code / engineering inference), no fabricated benchmark numbers.
- **Decision**: Wrote `SCALABILITY_CERTIFICATION.md` covering all 23 requested subsystems. Headline findings: (1) 5 of 6 list endpoints have no pagination — unbounded result sets, real but not yet urgent; (2) DB connection pooling is per-process with no cluster-wide budget — latent risk the moment horizontal scaling turns on; (3) the viewer's hot-path cache (`viewer_cache.py`) is explicitly documented by its own authors as process-local with a bounded ≤10s staleness window on link/permission changes — re-examined the V12.0 "Edit Link propagates instantly" finding in this light: that test's success doesn't contradict the ≤10s bound, it just means the test's request happened to land on the right worker process. Positive findings: IDOR-resistant authorization pattern used consistently, real Prometheus instrumentation already in place, sound Celery failure-recovery design, Redis-backed (not in-memory) rate limiting.
- **Files Modified**: `SCALABILITY_CERTIFICATION.md` (new, root-level).
- **Tests Executed**: N/A — this is a documentation/architecture-review deliverable, no code changed.
- **Result**: A defensible, evidence-labeled scalability assessment with per-subsystem priority tiers (Immediate/Before 1k/Before 10k/Before 100k/Future), explicitly listing what it does NOT cover (no measured throughput, no production resource data, no frontend performance, no full storage-layer blocking-I/O audit) rather than overclaiming completeness.
- **Next Action**: the live security-boundary probe (auth bypass, IDOR, rate limits) that was interrupted remains not yet done — awaiting direction on whether/how to proceed with it, plus the repository cleanup sweep and FINAL_RELEASE_CERTIFICATION.md scoring from the V13.0 mission.

### Entry 9 — Sprint V14.0, ENG-001 (2026-07-26)

- **Timestamp**: 2026-07-26T16:44
- **Module**: Frontend (`AnalyticsScreen.jsx`)
- **Screen**: Analytics
- **Observation**: `ENGINEERING_BACKLOG.md` ENG-001 (highest-priority open item): the Analytics screen's KPI row and two two-column panel rows used fixed CSS grid templates (`repeat(6,1fr)`, `2fr 1fr`, `3fr 1fr`) with no responsive fallback, causing the "Completion" KPI card and the "Groups at a glance" sidebar panel to render fully off-screen and unreachable (`overflow-x: hidden`, no scroll escape) at the app's own stated 768px minimum supported width.
- **Root Cause**: `frontend/src/screens/AnalyticsScreen.jsx:339,344,390` used fixed-column/fixed-ratio grid templates, inconsistent with the same file's own working responsive pattern at line 272 (`repeat(auto-fill, minmax(220px,1fr))`).
- **Decision**: Changed all three grids to `repeat(auto-fit, minmax(...px, 1fr))` (140px for the 6 KPI cards, 320px for the charts row, 280px for the table/sidebar row), matching the file's own already-correct pattern. This trades the desktop-only 2:1/3:1 visual ratio for guaranteed no-clip behavior at every width — verified this is not a visual regression at 1440px (screenshots below).
- **Files Modified**: `frontend/src/screens/AnalyticsScreen.jsx` (3 lines changed)
- **Tests Executed**: Frontend suite 13/13 passed. Backend full suite 1708 passed, 1 skipped, 0 failed (unchanged from baseline — this is a frontend-only CSS change). Live verification: stood up the full local stack via `docker compose up --build` (Postgres+Redis+API+worker), logged in with the same test account (shared Supabase project, separate local DB), and re-measured the exact DOM elements that were previously clipped at 768px, 834px, and 1440px.
- **Verification (Browser-verified)**: At 768px, "Completion" label right edge now at x=663.9 (was 844.5, viewport is 768) — fully inside viewport. "Groups at a glance" panel right edge now at x=729 (was clipped/truncated) — fully inside viewport and fully legible. At 834px and 1440px, same measurements confirm no clipping, and 1440px screenshot shows no visual regression (charts now render at 50/50 instead of 2:1, still clean and well-proportioned).
- **Result**: ENG-001 closed. Zero regressions across both test suites.
- **Next Action**: proceed to ENG-002 (Notifications feed lacks document identity).

### Entry 10 — Sprint V14.0, ENG-002 (2026-07-26)

- **Timestamp**: 2026-07-26T16:52
- **Module**: Backend (`app/routers/analytics.py`) + Frontend (`NotificationsScreen.jsx`)
- **Screen**: Notifications
- **Observation**: `ENGINEERING_BACKLOG.md` ENG-002. `GET /api/analytics/events` never returned a document identifier — only `link_id` — so every Notifications feed entry rendered as generic "Page viewed" with zero way to tell which document had activity, despite the frontend's `eventDetail()` already being written to display `ev.document_title` if it existed.
- **Root Cause**: the endpoint already computed `doc_ids` (user's documents) and `link_ids` (their share links) to scope the query, but discarded the document-filename association once it had the ID lists — no join back to `Document.filename` was ever added to the response payload.
- **Decision**: Extended the existing `user_docs_q` query to also select `Document.filename`, and the existing links query to also select `ShareLink.document_id`, building two small in-memory maps (`doc_titles`, `link_document_titles`) to attach `document_title` to each returned event — no new query, no N+1, reuses data the endpoint already fetches. Also added `page_number` to the frontend's `eventDetail()` for `page_viewed` events specifically, since the field was already present in the API response but never displayed.
- **Files Modified**: `backend/app/routers/analytics.py` (lines ~131-186), `frontend/src/screens/NotificationsScreen.jsx` (lines 59-67)
- **Tests Executed**: Backend full suite 1708 passed, 1 skipped, 0 failed (unchanged from baseline — additive field, no existing test asserts on exact response shape). Frontend suite 13/13 passed.
- **Verification (Browser-verified)**: Local Docker stack — created a real share link on a real local document (`sem6 (1).pdf`), opened it anonymously, navigated pages to generate live `page_viewed`/`opened`/`right_click_attempt` events, then confirmed as the owner that the Notifications feed now shows `"sem6 (1).pdf · page 3"`, `"sem6 (1).pdf · page 2"`, etc. for every entry instead of the previous bare `"Page viewed"` with no document reference. Screenshot: `eng002_notifications_after.png`.
- **Result**: ENG-002 closed. The Notifications screen can now actually answer its own stated purpose ("recent activity across your documents").
- **Next Action**: proceed to ENG-003 (cross-account IDOR verification).

### Entry 11 — Sprint V14.0, ENG-003 (2026-07-26)

- **Timestamp**: 2026-07-26T17:00
- **Module**: Full-stack — authorization verification, no module changed
- **Screen**: N/A (direct API testing)
- **Observation**: `ENGINEERING_BACKLOG.md` ENG-003 — the single largest gap flagged repeatedly across V13.0's security work: the query-scoped authorization pattern (`WHERE user_id == current_user_id`) was verified sound by source-code inspection, but never proven against a real second account. Resolved this sprint by creating a genuine second account (`eng003.idor.test2@mailinator.com`) against the **local Docker stack** — same shared Supabase auth project as production, but a completely separate local database, so this never touched production data.
- **Root Cause**: N/A — this was a verification task, not a bug-fix task.
- **Decision**: Signed up Account B, confirmed via its real confirmation email (retrieved from Mailinator's public inbox, since no `SUPABASE_SERVICE_ROLE_KEY` was available locally to confirm via the admin API directly), logged in, then directly attempted cross-account access to Account A's real document, share link, and a disposable API key created specifically for this test: `GET /api/documents/{A_doc_id}` → 404, `GET /api/documents/{A_doc_id}/status` → 404, `GET/DELETE /api/api-keys/{A_key_id}` → 404, `GET /api/links?document_id={A_doc_id}` → 404, `PATCH/DELETE/DELETE-hard /api/links/{A_link_id}` → 403. Account B's own document list did not contain Account A's document ID. Confirmed Account A's resources were untouched after every attempt. **No defect found** — the authorization pattern holds under a genuine live cross-account test, not just by code inspection.
- **New finding during this verification**: link-mutation endpoints return `403` for cross-account access where documents/API-keys return `404` — a minor inconsistency with the app's own stated "never confirm resource existence" pattern. Not practically exploitable (link IDs are random UUIDs). Logged as new backlog item **ENG-021** (Low priority) rather than silently ignored.
- **Files Modified**: None (verification only). Cleanup: deleted the disposable API key created on Account A for this test (`DELETE /api/api-keys/{key_id}` as A, 204).
- **Tests Executed**: N/A — no code changed, no regression risk. Full test suites not re-run for this entry (nothing to regress).
- **Result**: ENG-003 closed with **no defect found** — this sprint's largest cited evidence gap is now closed with genuine live proof, not just architectural confidence. One new, unrelated, low-priority finding (ENG-021) surfaced and logged rather than left unrecorded.
- **Next Action**: proceed to ENG-004 (document picker disambiguation) or ENG-021 (link 403/404 consistency), per backlog priority order.

### Entry 12 — Sprint V14.0, ENG-004 (2026-07-26)

- **Timestamp**: 2026-07-26T18:10
- **Module**: Frontend (`components/DocumentPicker.jsx`)
- **Screen**: Access Control (document picker used when creating a share link)
- **Observation**: `ENGINEERING_BACKLOG.md` ENG-004 (first Medium-tier item). The document picker rendered only filename, page count, and view count — two documents with the same filename (common with repeated drafts, and visibly the case in this account's own test data with a dozen-plus `test.pdf` entries) were completely indistinguishable before clicking.
- **Root Cause**: `DocumentPicker.jsx:63-68` never read `d.created_at`, unlike the Upload/Storage tables elsewhere in the app which both show a date/ID for exactly this reason.
- **Decision**: Added an "uploaded {date}" suffix to the existing metadata line, reusing the already-existing `fmtDate()` helper from `utils/viewer.js` (same formatter used elsewhere in the app) rather than writing a new one.
- **Files Modified**: `frontend/src/components/DocumentPicker.jsx` (1 import line + 1 line changed)
- **Tests Executed**: Frontend 13/13 passed. Backend 1708 passed, 1 skipped, 0 failed (unchanged — frontend-only change). Grepped test files for `DocumentPicker`/`doc-picker-item` references first — none found, confirming low regression risk before starting.
- **Verification (Browser-verified)**: Local Docker stack, Access Control screen — both of Account A's real local documents now show `"uploaded May 9, 2026"` in the picker row. Screenshot confirms no layout regression.
- **Result**: ENG-004 closed.
- **Next Action**: proceed to ENG-005 (list-endpoint pagination) — currently marked "Deferred" in the backlog; will re-confirm that deferral is still the right call (rather than silently skip) before moving to ENG-006.

### Entry 13 — Sprint V14.0, ENG-005 re-confirmation (2026-07-26)

- **Timestamp**: 2026-07-26T18:20
- **Module**: N/A — deferral re-confirmation, not a code change
- **Observation**: Per explicit process instruction, did not silently carry ENG-005's "Deferred" status forward without checking. Attempted to re-fetch a current production document count as a fresh data point; the saved production auth token had expired.
- **Decision**: Judged re-authenticating to production solely to refresh a count disproportionate — no new customer onboarding occurred this sprint, so the ~30-document scale from `SCALABILITY_CERTIFICATION.md` §1 (captured earlier the same day) is not expected to have materially changed. Logged this explicitly as **Not enough evidence** for an updated exact number, with **Engineering inference** that the underlying "before 10,000 users" deferral reasoning is unaffected by the gap. Deferral reconfirmed, not silently repeated.
- **Files Modified**: None.
- **Tests Executed**: N/A.
- **Result**: ENG-005 remains Deferred, now with an explicit re-confirmation record instead of a stale unexamined status.
- **Next Action**: proceed to ENG-006 (storage blocking-I/O audit).

### Entry 14 — Sprint V14.0, ENG-006 (2026-07-26)

- **Timestamp**: 2026-07-26T18:25
- **Module**: Backend (`app/services/storage.py`) — audit only
- **Observation**: `ENGINEERING_BACKLOG.md` ENG-006 (last Medium-tier item). Flagged because this exact bug class — a synchronous boto3 call blocking the async event loop — already caused one confirmed real issue in this codebase (fixed in `viewer.py`'s download path, V4.0). Never re-audited elsewhere.
- **Root Cause**: N/A — audit found no defect.
- **Decision**: Grepped the full backend for every `boto3`/S3-call-shaped reference. All real usage is confined to `services/storage.py`; the one other match (`workers/pipeline/pdf.py`) was PyPDF's unrelated `get_object()` method (PDF object model, not S3), and that file runs inside the Celery worker process, not the async API event loop, so it wouldn't be in scope for this concern even if it had been real. Read all 6 methods on `StorageService` directly (not assumed from the docstring) — every one wraps its boto3 call in `run_in_executor(_STORAGE_EXECUTOR, ...)`. The module's own docstring already states this as a deliberate contract; the code verifiably lives up to it.
- **Files Modified**: None — no defect found, nothing to fix.
- **Tests Executed**: N/A (audit only, no code changed).
- **Result**: ENG-006 closed, no defect found. **This closes the Medium-priority tier** (ENG-004 fixed, ENG-005 deferral re-confirmed, ENG-006 audited clean).
- **Next Action**: per process rule, perform a browser-based regression pass before moving into the Low-priority tier.

### Entry 15 — Sprint V15.0, ENG-007 (2026-07-27)

- **Timestamp**: 2026-07-27T08:33
- **Module**: Frontend (`screens/AuditLogScreen.jsx`) — first issue under the refined V15.0 process (stricter commit format, expanded per-issue regression sweep)
- **Screen**: Audit Log
- **Observation**: `ENGINEERING_BACKLOG.md` ENG-007. The events table's Details column was reachable via horizontal scroll at narrow widths but had zero visual affordance signaling more content existed off-screen. The backlog's originally-guessed file (`components/access/AccessLog.jsx`) was wrong — confirmed the real file is `screens/AuditLogScreen.jsx` before editing.
- **Root Cause**: the table had no dedicated scroll container of its own; it relied on an ancestor's incidental `overflow-x: auto`, with nothing indicating scrollability to the user.
- **Decision**: Wrapped the table in its own `overflow-x: auto` div with a `ref`, added a `showScrollFade` state driven by an `onScroll` handler plus a mount/resize check (`scrollWidth - clientWidth - scrollLeft > 4`), and rendered a conditional right-edge gradient fade only while there's genuinely more to scroll to — not a static always-on decoration, so it correctly disappears once the user has scrolled to the end.
- **Files Modified**: `frontend/src/screens/AuditLogScreen.jsx`
- **Tests Executed**: Frontend 13/13 passed. Backend 1708 passed, 1 skipped, 0 failed (unchanged). Build succeeded (esbuild, 312.9kb). Migration validation: local `migrate` container exited 0. **New V15.0 regression-sweep step**: grepped for TODO/FIXME/console.log/debugger/print()/pdb across the full repo — 5 backend matches, all confirmed false positives (comments showing users an example `python -c "...print(...)"` CLI command to generate a secret key, not real debug code); 0 frontend matches.
- **Verification (Browser-verified)**: Local Docker stack — at 834px (genuine table overflow, `scrollWidth 634 > clientWidth 582`) the fade div renders in the DOM with the correct gradient at the table's right edge; at 900px and 1440px (no overflow) it correctly does not render at all.
- **Result**: ENG-007 closed.
- **Next Action**: proceed to ENG-008 (rate-limit 429 boundary verification).

### Entry 16 — Sprint V15.0, ENG-008 (2026-07-27)

- **Timestamp**: 2026-07-27T08:45
- **Module**: N/A — bounded live verification, no code changed
- **Observation**: `ENGINEERING_BACKLOG.md` ENG-008. The 20/minute rate limit on `POST /api/viewer/validate` was source-verified (`viewer.py:158`) but its actual trigger point was never empirically confirmed, deliberately, to avoid generating artificial traffic in earlier sprints.
- **Root Cause**: N/A — verification task.
- **Decision**: Created one disposable password-protected test link (local stack), sent exactly 21 wrong-password validate attempts in sequence. Results: attempts 1-20 → `401` (correctly rejected as wrong password, not yet rate-limited); attempt 21 → `429`. The boundary is exact — not off-by-one in either direction. Test link revoked immediately after.
- **Files Modified**: None.
- **Tests Executed**: Backend full suite 1708 passed, 1 skipped, 0 failed (unchanged — no code touched). Repo-wide TODO/FIXME/console.log/debugger/print() sweep re-run: still clean.
- **Result**: ENG-008 closed. No defect found — the rate limiter's documented threshold is also its actual enforced threshold, now proven live rather than assumed from configuration alone.
- **Next Action**: proceed to ENG-009 (XSS testing beyond link labels).

### Entry 17 — Sprint V15.0, ENG-009 (2026-07-27)

- **Timestamp**: 2026-07-27T08:55
- **Module**: N/A — bounded live verification, no code changed
- **Observation**: `ENGINEERING_BACKLOG.md` ENG-009. Only the link-label field had been live-tested for XSS in earlier sprints; document filenames, org names, webhook descriptions, and API key names were flagged as Security inference only, not individually proven.
- **Root Cause**: N/A — verification task.
- **Decision**: Source-verified first: repo-wide grep confirms zero `dangerouslySetInnerHTML` usage anywhere in `frontend/src`. Then live: created a disposable organization, API key, and webhook, each named/described with the same payload already proven inert for link labels (`<img src=x onerror=alert(1)>`). Visited the Organizations, API Keys, and Webhooks screens — payload rendered as literal visible text on all 3 (screenshot-confirmed), zero injected `<img>` elements, zero JS dialogs, zero console errors. All 3 test resources deleted immediately after.
- **Files Modified**: None.
- **Tests Executed**: Backend full suite 1708 passed, 1 skipped, 0 failed (unchanged).
- **Result**: ENG-009 closed, no defect found. This closes the last open item from `SECURITY_CERTIFICATION.md`'s original "Not enough evidence" list for XSS coverage.
- **Next Action**: proceed to ENG-010 (expired-link live confirmation).

### Entry 18 — Sprint V15.0, ENG-010 (2026-07-27)

- **Timestamp**: 2026-07-27T09:10
- **Module**: N/A — bounded live verification, no code changed
- **Observation**: `ENGINEERING_BACKLOG.md` ENG-010. Expired-link enforcement (`_check_link_active`, `viewer_service.py:26-35`) was source-verified as the identical code path to revocation, but never live-tested itself, since the dashboard UI's expiry field is date-only (earliest achievable value is end-of-current-day, impractical to wait out).
- **Root Cause**: N/A — verification task.
- **Decision**: Checked the link-creation schema directly (`schemas/link.py:16`) and confirmed `expires_at` accepts a full `datetime`, not just a date — the UI's date-only granularity is a frontend input constraint, not a backend limitation. Created a disposable link via the API with `expires_at` 75 seconds in the future. `POST /api/viewer/validate` returned `200` immediately (link still active), then `410 {"detail":"Link expired"}` after waiting 80 seconds. Exact same status/response shape as the already-verified revocation path.
- **Files Modified**: None.
- **Tests Executed**: Backend full suite 1708 passed, 1 skipped, 0 failed (unchanged).
- **Result**: ENG-010 closed, no defect found, now live-confirmed rather than source-inferred. **This closes the last item from `SECURITY_CERTIFICATION.md`'s original "Not enough evidence" list** — every explicit evidence gap flagged in that review (cross-account IDOR, rate-limit boundary, XSS beyond one field, expired-link enforcement) has now been independently proven live.
- **Next Action**: proceed to ENG-011/ENG-012 (connection pooling / cache invalidation — both currently Deferred, will re-confirm reasoning per process rule) or ENG-021 (link 403/404 consistency) — next in priority order.

### Entry 19 — Sprint V15.0, ENG-011/ENG-012 re-confirmation + ENG-021 (2026-07-27)

- **Timestamp**: 2026-07-27T09:20
- **Module**: Backend (`app/routers/links.py`), tests (`tests/regression/test_auth_enforcement.py`)
- **Observation**: Re-confirmed ENG-011 (connection pooling) and ENG-012 (cache invalidation broadcast) deferrals per process rule — neither triggering condition (horizontal scaling, a customer requirement for instant propagation) has arisen this sprint; both remain correctly deferred, now with an active re-check on record. Then implemented ENG-021 (found during ENG-003's IDOR verification): `links.py`'s 3 mutation endpoints (`revoke_link`, `update_link`, `delete_link_permanently`) returned `403 "Not authorized"` for cross-account access, inconsistent with the app-wide `404` pattern used in `documents.py`/`api_keys.py` and even by `links.py`'s own sibling `create`/`list` endpoints.
- **Root Cause**: the 3 mutation handlers checked link existence (404 if absent) then document ownership (403 if present-but-not-yours) as two separate branches with two different status codes, rather than collapsing both into a single 404 like the read/create endpoints already did.
- **Decision**: Changed all 3 authorization-failure branches to `404 "Link not found"`. Discovered in the process that 2 existing tests (`test_user_a_cannot_revoke_user_b_link`, `test_user_a_cannot_patch_user_b_link`) asserted the old `403` — inconsistent with their own sibling tests (`create`/`list`) in the same test class, which already correctly expected `404`. Updated both. Also added a third test for the hard-delete endpoint, which had zero prior cross-account test coverage at all.
- **Files Modified**: `backend/app/routers/links.py`, `backend/tests/regression/test_auth_enforcement.py`
- **Tests Executed**: Reverted the source fix via `git stash` to confirm all 3 tests fail against pre-fix code (403 vs 404) — proving they're meaningful, not tautological — then restored the fix and confirmed all pass. Full suite: **1709 passed** (up from 1708 — the new hard-delete test), 1 skipped, 0 failed. Repo-wide TODO/FIXME/console.log/debugger/print() sweep on changed files: clean.
- **Verification (Browser/API-verified)**: Local Docker stack, fresh logins for both test accounts. `PATCH`/`DELETE`/`DELETE .../hard` on Account A's link as Account B all return `404 {"detail":"Link not found"}` — indistinguishable from a genuinely nonexistent link ID.
- **Result**: ENG-021 closed. ENG-011/ENG-012 deferrals re-confirmed, not silently carried forward. **This closes the entire Low-priority tier.**
- **Next Action**: browser regression pass (per process rule, after completing a tier), then proceed to Enhancement tier.

### Entry 20 — Sprint V16.0, backlog reconciliation + ENG-029 (2026-07-28)

- **Timestamp**: 2026-07-28T20:40
- **Module**: Documentation (`docs/engineering/ISSUE_DATABASE.md`, `ENGINEERING_BACKLOG.md`, `docs/architecture/ARCHITECTURE.md`)
- **Observation**: V16.0 explicitly requires reading `ISSUE_DATABASE.md` and `TODO_QUEUE.md` as canonical sources before touching code. Found the two contradicted each other on completion status for ~10 items (`ISSUE_DATABASE.md` marked several "Open" that `TODO_QUEUE.md`'s own "Completed this session" list showed done back in V10.0).
- **Root Cause**: `ISSUE_DATABASE.md` was never updated after V10.0 shipped those fixes — a stale-documentation defect in its own right.
- **Decision**: Source-verified a 3/3 sample directly against current code (H-1 `@keyframes shake` exists; H-7 `download_document`'s PDF write is wrapped in `run_in_executor`; M-1 both `Toggle` call sites pass `label=`) — all confirmed done. Reconciled `ISSUE_DATABASE.md`'s status column to match verified reality rather than either stale doc. Merged the 10 genuinely-still-open items into `ENGINEERING_BACKLOG.md` as ENG-022 through ENG-031 (2 already deferred with re-confirmed reasoning, 8 open) — `ENGINEERING_BACKLOG.md` remains the single source of truth, nothing duplicated across files.

  Then processed the highest-priority newly-surfaced open item: **ENG-029** (architecture docs contradict each other on watermark model and cache TTLs). Source-verified ground truth directly: `viewer_cache.py`'s actual TTLs are `LINK_TTL_SEC=10.0`, `SESSION_TTL_SEC=5.0` — `ARCHITECTURE.md` stated both as 30s (wrong); `OVERVIEW.md` already had the correct 10s/5s. Also `ARCHITECTURE.md` mislabeled the main visible per-session watermark as "forensic," omitting the two actual (separate) near-invisible forensic stamps that `watermark.py` implements. `OVERVIEW.md` was already accurate on this too.
- **Files Modified**: `docs/engineering/ISSUE_DATABASE.md` (reconciliation), `ENGINEERING_BACKLOG.md` (10 new entries), `docs/architecture/ARCHITECTURE.md` (2 corrected lines, source-of-truth citation added).
- **Tests Executed**: Backend full suite 1709 passed, 1 skipped, 0 failed (unchanged — docs-only change).
- **Result**: Backlog now genuinely comprehensive across all canonical sources, not just this sprint's own findings. ENG-029 closed — both architecture docs now agree and match source.
- **Next Action**: proceed through the remaining open items in priority order — Enhancement-tier ENG-013 onward, plus the newly-merged Low-severity items (ENG-024, 025, 027, 028, 030, 031).
