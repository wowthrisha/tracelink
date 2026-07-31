# Sprint 7.0 Baseline

Reviewed `VERIFIED_ISSUES.md`, `SECURITY_HARDENING_PLAN.md`, `PRODUCT_PROPOSAL.md`, `COMMIT_SUMMARY.md`, and current repo state (`git log`, `git status`) before starting Sprint 7 work.

**Repo state at baseline**: `main` @ `31e2966` ("fix: V4.0 verified engineering remediation"), pushed to `origin/main`. Working tree has one unrelated, pre-existing in-progress change (`backend/app/auth.py`, `traceview.code-workspace`, `test_jwks_outage.py`, and four `*_REPORT.md`/`*_ANALYSIS.md` files from a separate JWKS-outage task) — not part of this sprint, left untouched, same as last sprint. 16 backend routers, 13 frontend screens.

---

## Completed (from prior sprint, per `VERIFIED_ISSUES.md` / `COMMIT_SUMMARY.md`)

- 7 verified, source-confirmed UX fixes shipped in `31e2966`: AUTH-001, AUTH-002, AUTH-007, DASH-001, DASH-003, DASH-008, ANAL-006.
- Full regression baseline established: backend 1699 passed / 1 skipped / 0 failed; frontend 13/13 passed; build clean.
- 6 audit claims (ACCESS-006, AUDIT-001, ORG-001, AUTH-003, AUTH-005, ACCESS-003) investigated and found to not describe real defects — no action needed, already correct or intentional.

## Deferred (planned, with a document, but not implemented)

- **AUTH-006** — session token in `localStorage`. Full migration plan exists in `SECURITY_HARDENING_PLAN.md` (phased: CORS/dual-read → frontend cutover+CSRF → header-path deprecation → optional refresh-token stretch). Sprint 7 Phase 4 scope is explicitly the *low-risk* subset of this plan only (see Phase 4 section below) — the cookie/CSRF migration itself stays deferred per this sprint's own instruction not to implement partial security migrations.
- **PROF-001** — no in-app profile/account screen. Full proposal exists in `PRODUCT_PROPOSAL.md`. Sprint 7 is explicitly scoped to *not* add new product features, so this stays deferred regardless of Phase 5's org-workflow review touching adjacent territory.

## Blocked (no path forward without input outside engineering)

- **AUTH-004** — no ToS/Privacy pages exist in the repo to link to from signup. Blocked on legal content, not code.
- **PROF-001's account-deletion sub-scope** — `PRODUCT_PROPOSAL.md` §3 flags that org-ownership-transfer-on-delete needs a product decision before an engineer can safely build cascading account deletion. Same blocker applies to anything Sprint 7 finds in the Organizations "Delete organization" / "Transfer ownership" workflow that depends on the same undecided policy — noted where relevant in Phase 5.

## Remaining — carried over from the prior audit

- 30 issues from the original product audit (`VERIFIED_ISSUES.md`'s "needs browser re-validation" bucket) still have no real browser evidence and are not in this sprint's scope, which is a fresh source-level review, not a continuation of that specific list. They stay open, unaffected by Sprint 7.

## New scope — Sprint 7 Phases 2–7 (not yet started as of this baseline)

This sprint is a fresh, source-grounded review distinct from the prior audit-triage cycle — it inspects the actual implementation directly rather than cross-checking third-party claims. Nothing below has been assessed yet; this baseline exists to mark the starting line before that work begins:

- Phase 2 — end-to-end completeness review of 17 named workflows (Upload, OCR, Protection, Share, Viewer, Reading Analytics, Notifications, Organizations, Invite Member, Role Management, API Keys, Webhooks, Storage, Billing, Audit Log, Password Reset, Delete)
- Phase 3 — architecture review (duplication, circular deps, inconsistent permission/audit/analytics handling, performance)
- Phase 4 — low-risk security hardening only, from `SECURITY_HARDENING_PLAN.md`
- Phase 5 — Organizations system deep-dive (create/invite/accept/role/remove/delete/transfer)
- Phase 6 — repository health sweep (TODO/FIXME/console.log/debugger/dead code/unused imports/duplicate helpers/stale docs/naming)
- Phase 7 — full validation (backend/frontend tests, build, lint, migration checks)

Findings and fixes for each are reported in `WORKFLOW_COMPLETENESS.md`, `ARCHITECTURE_SCORECARD.md`, `SECURITY_STATUS.md`, `REPOSITORY_HEALTH.md`, and rolled up in `SPRINT7_COMPLETION_REPORT.md`.
