# Changelog

All notable changes to SecureDoc are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

**Note (added V24.0, 2026-08-09):** this file's per-sprint entries stop at V10.0 — sprints V11.0 through the current V24.0 were never backfilled here. For everything since V10.0, `ENGINEERING_BACKLOG.md` (canonical open/closed issue tracker), `PROGRESS.md` (narrative sprint log), and `CHECKPOINT.md` (current-state snapshot) are the authoritative, actively-maintained sources — not this file. Not backfilling the gap retroactively here rather than risk reconstructing 14 sprints of detail from summary rather than original evidence; see `ENGINEERING_BACKLOG.md` ENG-047 for the tracked gap.

---

## [Unreleased] — Sprint V10.0: Autonomous Product Excellence

Continuous observe→verify→fix→retest→regression→log loop against the V6.0/V7.0 governance backlog, executed under explicit autonomous-fix authority. Full narrative in `docs/engineering/ACTION_LOG.md`; per-fix detail in `docs/engineering/FIX_LOG.md`; current open-issue state in `docs/engineering/ISSUE_DATABASE.md`. Built on top of the still-uncommitted V6.0/V7.0 changes below; also uncommitted.

### Fixed (7)

- A wrong-password shake animation on the public share-link gate was silently broken (referenced a CSS keyframe that didn't exist) — now animates.
- 9 modals across API Keys, Webhooks, and Organizations screens migrated onto the shared, accessible `Modal` component — they previously were the only modals in the app with no focus-trap, no Escape-to-close, and no entrance animation.
- The two document-permission toggle switches on Access Control now announce what they control to screen readers.
- A synchronous PDF write in the document-download endpoint was blocking the server's event loop — offloaded to match the pattern already used one line above it.
- Two genuinely silent failure points (a custom-domain lookup, a webhook test-ping dispatch) now log instead of failing invisibly.
- A spacing-token scale was added for future UI work (additive — no existing code touched).
- Delete/revoke toast severity standardized on the Access Control screen to match the rest of the app.

### Investigated and correctly left unchanged — 3 false positives caught before acting

Prior-sprint research claimed the Viewer's arrow-key page navigation didn't exist (it does — a different hook file implements it correctly), that two security-sensitive config defaults had no production-time enforcement (they do — in `main.py`, just not where the research looked), and that 15 routers had silent, unlogged exception handling (13 of 15 wrap a function that already logs its own failures internally). Each was verified against source before being ruled out rather than "fixed" on faith. Full reasoning for each in `docs/engineering/ISSUE_DATABASE.md`.

### Verification

Backend: 1702 passed, 1 skipped, 0 failed, checked after every logical fix (4 full-suite runs this session, all clean). Frontend: 13/13 passed, build clean (308.4kb, down from 311.3kb). No regressions found.

### Not implemented this session (by design)

The large-refactor tier of the backlog — AUTH-006's token-storage migration, full pagination rollout, typed-schema migration, an `AccessScreen.jsx` 3-way split, documentation-set consolidation — remains untouched, each with a recorded reason in `docs/engineering/ARCHITECTURE_DECISIONS.md`. Four items newly requiring a product/architecture decision (not an engineering fix) are recorded in `docs/engineering/REMAINING_DECISIONS.md`.

---

## [Unreleased] — Sprint V6.0: Engineering Governance

Full governance pass: every repo directory reviewed for purpose/placement, module boundaries and code quality audited, a complete UI-to-API contract matrix built across all 12 screens, security/scalability/consistency reviews, and a deep dead-code sweep. Full evidence in `ENGINEERING_GOVERNANCE.md`, `MODULE_BOUNDARIES_AND_CODE_QUALITY.md`, `UI_API_CONTRACT.md`, `SECURITY_GOVERNANCE.md`, `SCALABILITY_REVIEW.md`, `CONSISTENCY_MATRIX.md`, `REPOSITORY_HEALTH.md`, `ENGINEERING_EXCELLENCE_REPORT.md`; root-caused per fix in `FIX_LOG.md`. No product features added or existing workflows redesigned. Built on top of the still-uncommitted Sprint 7.0 changes below; also uncommitted.

### Fixed — most significant

- **Webhook deliveries were silently non-functional in production**: the Celery worker process never registered the `deliver_webhook` task at all (missing from `celery_app.py`'s `include=` list) — every webhook send was enqueuing a task name no worker could execute. This is the most severe bug found this sprint. Added a permanent regression test.
- **Real access-control bug**: `annotations.py` denied org members access to annotations/feedback on documents they could otherwise view, because it reimplemented a narrower ownership check instead of using the existing org-aware helper. Fixed across all 10 affected endpoints.
- **Three CSV exports had zero error handling** (unhandled promise rejections) and **copy-to-clipboard reported success even when the copy failed** in three separate screens — both fixed.
- Webhook and document-retention actions previously had **no audit-log coverage at all**; both now log.
- Billing's Refresh button and the Viewer's document-search both failed completely silently or misleadingly on error — both now give real feedback.

### Fixed — consistency & cleanup

- Two destructive-action confirmation dialogs corrected (Delete Document now names the document itself; Storage retention-change now uses proper warning styling).
- Two duplicated business-logic implementations consolidated (`links.py`'s is-link-active check, which had a real edge-case disagreement with its own service layer; `orgs.py`'s last-owner check).
- `api_key.rotated` audit events were being logged but were invisible/unqueryable (missing from the filterable event-type enum) — fixed.
- One missing database index added (webhook deliveries).
- Dead code removed: an unused component, an unused API helper, two dead CSS classes, and an empty nested directory tree.

### Documented, not implemented (by design — see the phase reports for full reasoning)

A substantial list of real-but-lower-priority findings across every phase — large functions/components worth splitting, ~10 more audit-logging gaps, unbounded list-endpoint pagination, date-format/toast-severity/empty-state inconsistencies across screens, missing ARIA labels, and documentation consolidation (14 overlapping release docs, a 5-major-version-stale certification doc, a missing canonical database-schema doc) — were investigated, evidenced, and deliberately left undone this sprint because each needs either a coordinated multi-file change, a product decision, or dedicated follow-up time disproportionate to "fix only when safe." Full lists in the phase-specific reports.

### Verification

Backend: 1702 passed, 1 skipped, 0 failed, including 1 new worker-registration regression test. Frontend: 13/13 passed, build clean. Migration chain: single linear head. Repo-wide TODO/FIXME/console.log/debugger/print sweep: clean.

---

## [Unreleased] — Sprint 7.0: Enterprise Architecture & Workflow Completion

Reviewed all 17 core workflows (Upload/OCR, Protection/Share/Viewer, Reading Analytics/Notifications, Organizations, API Keys/Webhooks/Storage/Billing, Audit Log/Password Reset/Delete) plus a repo-wide architecture and health sweep, directly against source — not against bundle inspection or unverified claims. Full evidence in `WORKFLOW_COMPLETENESS.md`, `ARCHITECTURE_SCORECARD.md`, `SECURITY_STATUS.md`, `REPOSITORY_HEALTH.md`, root-caused per fix in `FIX_LOG.md`. No new product features added, per this sprint's own scope rule. Built on top of `31e2966`; changes below are uncommitted pending an explicit commit instruction.

### Fixed (17)

- Viewer: view-limit-reached was mislabeled "Link Expired"; a broken network-error fallback silently 400'd with no error shown (now shows a real error + Retry button); garbled HTML-entity icons in the access gate now render as real emoji.
- Access control: no warning for password/email-gated links left with no expiry; no tooltip distinguishing Revoke from Delete; "Revoke All Access" always claimed success even on partial/total failure — now reports accurately.
- Storage: retention-policy changes fired immediately with zero confirmation despite being able to schedule a document for deletion — now confirmed; per-document table had no empty state.
- Delete consistency: document/group delete had a missing loading state and a modal that closed before the async call resolved; API key delete confirmation had copy-pasted webhook terminology; org member removal was the only destructive action in the app with zero confirmation — all fixed to match the rest of the app's pattern.
- Password reset left a stale, reusable-looking token in the URL after success — now cleared.
- Audit log export silently truncated at 500 rows with no warning — now reports the true total and what was actually exported.
- **Real bug**: organization members below admin role could not leave an organization at all, contradicting the code's own "self-removal at any role" intent — fixed with 2 new regression tests.
- **Permission-boundary gap**: `groups.py` endpoints didn't enforce API-key scopes like every sibling router does — an under-scoped API key could mutate group membership; now consistent.
- Document upload now writes an audit-log entry, matching document deletion (was a real asymmetry).
- Architecture cleanup: consolidated 3 duplicated implementations (`_get_session_id`, `fmtDate`, `admin.py`'s reimplemented role-check) onto shared helpers; fixed an N+1 query in group-document assignment; removed 4 confirmed-unused imports; corrected a stale/misleading code comment.
- Fixed a pre-existing test-fragility bug in `test_bundle_ends_with_reactdom_render` (regex didn't account for esbuild's `$`-prefixed minified names).

### Documented, not fixed this sprint (deliberately — see reports for why)

- AUTH-006 (session token storage) — untouched; the sprint's own rule against partial security migrations applies to every phase of that plan, including the "safe" first one.
- No cascade/block on document orphaning when an organization is deleted, and no "Transfer Ownership" feature — both need a product decision, not an engineering guess.
- Several more audit/analytics-logging gaps, a hot-path N+1 in reading-analytics batch ingestion, webhook delivery-failure visibility, and a `_fmtMs` display inconsistency — all catalogued with reasoning in `ARCHITECTURE_SCORECARD.md` / `WORKFLOW_COMPLETENESS.md` rather than guessed at under time pressure.

### Verification

Backend: 1701 passed, 1 skipped, 0 failed (`pytest tests/unit tests/integration tests/regression`), including 2 new regression tests. Frontend: 13/13 passed, build clean. Migrations: single linear head, no schema changes. Repo-wide TODO/FIXME/console.log/debugger/print sweep: clean.

---

## [31e2966] — Engineering remediation from product-audit triage

Triaged all 49 issues from the `TraceLink_Product_Audit` artifacts against the current implementation before touching any code — see `ENGINEERING_TRIAGE.md` for the evidence-integrity findings and `VERIFIED_ISSUES.md` for the disposition of every issue. Committed as `31e2966`, pushed to `origin/main`.

### Fixed

- **AUTH-001** `frontend/src/screens/LoginScreen.jsx` — Signup form now shows a password-length hint ("At least 6 characters.").
- **AUTH-002** `frontend/src/screens/LoginScreen.jsx` — Password field gained a Show/Hide visibility toggle.
- **AUTH-007** `frontend/src/screens/LoginScreen.jsx` — Network failures on login (`Failed to fetch`, etc.) now show "Unable to reach the server. Check your connection and try again." instead of the raw browser error.
- **DASH-001** `frontend/src/components/atoms.jsx` — Documents screen retitled from "Upload Dashboard" to "Documents" — the screen is a full document hub, not just an upload tool.
- **DASH-003** `frontend/src/screens/UploadScreen.jsx` — Security/watermark notice moved from a 10px footer line to a bordered banner near the top of the screen.
- **DASH-008** `frontend/src/components/upload/UploadMetadataPanel.jsx` — "+ New group" button changed from `ghost` to `secondary` variant for visibility.
- **ANAL-006** `frontend/src/screens/AnalyticsScreen.jsx` — Groups analytics widget no longer silently truncates past 5 groups; added a "Show all N" / "Show fewer" toggle.

### Deferred (planned, not implemented this cycle)

- **AUTH-006** — Session-token storage hardening (`localStorage` → httpOnly cookie). Real XSS-exposure finding, but the correct fix is an auth-architecture migration touching 60 frontend call sites and 72 backend dependency sites — full plan in `SECURITY_HARDENING_PLAN.md`.
- **PROF-001** — In-app profile/account settings screen does not exist. New-feature scope, not a bug fix — proposal in `PRODUCT_PROPOSAL.md`.
- **AUTH-004** — No ToS/Privacy links on signup. Blocked on legal content that doesn't exist yet in this repo; a link to a nonexistent page would be worse than the current state.

### Investigated, not changed — audit claims found inaccurate

- **ACCESS-006, AUDIT-001, ORG-001** — each claims a protection is missing; in all three cases the protection already exists in current source (confirmation modal, admin-role check, unprotected-link warning respectively). No code change made.
- **AUTH-003, AUTH-005, ACCESS-003** — describe intentional design choices or unavoidable properties of client-side REST calls, not defects.

### Verification

`npm test` (frontend, 13/13 passed) · `npm run build` (succeeded) · `pytest tests/unit tests/integration tests/regression` (backend, 1699 passed / 1 skipped / 0 failed) · diff scanned for TODO/FIXME/console.log/debugger (none found).

### Outstanding

30 of the 49 audited issues sit on 12 screens the audit's own session-tracking confirms were never opened in a browser; their evidence traces to static inspection of the minified production bundle rather than observed behavior. None were implemented — see `VERIFIED_ISSUES.md` for the full list. They need a genuine browser re-validation pass before further action.

---

## [8.1.0] — 2026-06-30 — Release Candidate 1

### Fixed

- **FIX-007** `backend/app/routers/viewer.py` — Removed duplicate `_session_watermark_angle` definition. Canonical implementation is in `app/services/viewer_service.py`. Stale `import hashlib as _hashlib` also removed. Test import paths corrected in `test_phase7.py`.

### Certification

1624 passed / 1 skipped / 0 failures. See [`docs/release/RC1_CERTIFICATION.md`](docs/release/RC1_CERTIFICATION.md).

---

## [8.0.0] — 2026-06-29 — Sprint 6.1 Product Polish

### Fixed

- **UX-001** `frontend/src/screens/UploadScreen.jsx` — Upload button changed from "↑ Upload PDF" to "↑ Upload". The button accepts PDF, DOCX, DOC, TXT, MD, and LOG files.
- **UX-002** `frontend/src/screens/UploadScreen.jsx`, `AnalyticsScreen.jsx` — "Total Views" stat card renamed to "Views Today". The underlying field `total_views_today` is today's count only, not all-time.
- **UX-003** `frontend/src/screens/NotificationsScreen.jsx` — `eventLabel()` expanded from 5 mappings to 25+. All backend event types now display human-readable labels (previously showed raw snake_case).
- **UX-004** `frontend/src/screens/BillingScreen.jsx` — Billing "not configured" message no longer exposes the `STRIPE_SECRET_KEY` environment variable name.
- **UX-005** `frontend/src/components/atoms.jsx` — `RiskBadge` returns `—` instead of an empty bordered box when `level` is undefined.
- **UX-006** `frontend/src/screens/AccessScreen.jsx` — Removed `|| 'HIGH'` fallback; documents with no risk score now show `—` instead of a red HIGH badge.
- **UX-007** `frontend/src/components/DocumentPicker.jsx` — Fixed "1 pages · 1 views" grammar; both counts are now conditionally pluralized.

---

## [7.x] — Sprint 6.0 Engineering Excellence

Key fixes from Sprint 6.0 (FIX-005 through FIX-011):

- **FIX-005** `documents.py` — Storage import moved to module level
- **FIX-006** `analytics.py` — `func` imported at module level (not inside function)
- **FIX-008** `analytics_service.py` — `_by_link` helper moved to module level
- **FIX-009** `orgs.py` — `asyncio.get_running_loop()` replaces deprecated `get_event_loop()`
- **FIX-010** `links.py` — Removed redundant document fetch in `list_links`
- **FIX-011** `retention.py` — Sidecar prefixes tuple includes all four types (`toc`, `text`, `links`, `words`)

For full Sprint 6.0 details see [`archive/sprint5-6/frontend-docs/certification/`](archive/sprint5-6/frontend-docs/certification/).
