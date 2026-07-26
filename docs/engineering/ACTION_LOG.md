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
