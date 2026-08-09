# Known Limitations

Companion to [`FINAL_RELEASE_CERTIFICATION.md`](FINAL_RELEASE_CERTIFICATION.md) and [`V24_ENGINEERING_STATUS_AND_CERTIFICATION.md`](V24_ENGINEERING_STATUS_AND_CERTIFICATION.md) (the current sprint's certification). Each item states what's actually known versus not, with evidence class.

**Updated V24.0 (2026-08-09)**: several items below were stale — describing closed issues as open, and a resolved tooling gap as still-blocking. Corrected in place rather than left to mislead a future reader; each correction says what changed and when.

## Verification environment

- **~~No browser-automation tool is available in this environment~~ — corrected V24.0**: a working Playwright+Chromium install was found in the host's miniconda3 environment starting V23.0 (2026-08-08), confirmed working against both the live Railway deployment and the local Docker stack. V23.0 and V24.0 both used it for genuine Browser Verified evidence (Access Control, Organizations, general-screen sweep in V23.0; Reading Intelligence pause/resume investigation in V24.0, which found ENG-048). Claims dated V18.0–V22.0 in this repository's documentation that say "no browser tool available" were accurate *for those sessions* — the tool was never searched for outside Claude-Code-native integrations until V23.0 — but should not be read as still true.
- Load/scale testing was never performed (out of scope by every sprint's own explicit constraints — no destructive or synthetic load generation). Scalability findings in this repository are architectural inferences from source review, not measured performance data. Unchanged as of V24.0.

## Open items

- **AUTH-006** (ENG-026, deferred): session token lives in `localStorage`, a real XSS-exposure vector. A phased migration plan exists (`docs/security/SECURITY_HARDENING_PLAN.md`) but hasn't been scheduled. A hash-based CSP (confirmed live in production as of V24.0 — see `V24_ENGINEERING_STATUS_AND_CERTIFICATION.md` §6) narrows the realistic exploit chain to two independent failures rather than one. No live or source XSS has been found in any sprint through V24.0.
- **ENG-038**: `ensure_not_last_owner()` has an unguarded TOCTOU race (no row locking) — two simultaneous requests against an org's last two owners could both pass the check. Pre-existing, not introduced by any session's work; narrow window, low blast radius (an orgless-owner state, not data loss or unauthorized access). 2 clean concurrent-request reproduction attempts (V22.0) found no race — reclassified as low-risk inference, not fixed without a reproducible failing test.
- **ENG-046** (new, V24.0, Low-Medium, partially fixed): CI's `ruff check` had no project-level configuration; `backend/app` is now clean and the ruleset is pinned (`backend/ruff.toml`), but `backend/tests` still has 206 real, pre-existing, zero-runtime-impact lint violations, quantified and left open rather than blind-fixed across many files.

### Resolved since this file was last accurate (corrected V24.0, not silently dropped)

- ~~**ENG-048**: the Viewer's Reading Intelligence active-time counter resets to zero instead of pausing when the browser window loses focus~~ — **closed V24.0** (2026-08-09, same-sprint follow-up). Root cause proven via runtime instrumentation: a `useEffect` dependency-array race meant `currentPage` never got set for the entire session, so the accumulator permanently no-opped (and nothing was ever flushed to the backend either, for sessions that never left page 1). Fixed with a 3-line change, 2 new regression tests (proven meaningful via stash-revert), 9/10 mandated browser tests passing (1 indeterminate for a documented automation-environment reason, not an app defect). Full record: `ENGINEERING_BACKLOG.md` ENG-048.

- ~~**ENG-039**: API keys created with zero granted scopes can still call every endpoint in `orgs.py`, `api_keys.py`, and `billing.py`~~ — **closed V22.0** (2026-08-04). Root-caused and fixed across 21 routes plus 3 sibling instances (ENG-041/042/043); 28+ new regression tests, proven meaningful via stash-revert.
- ~~**ENG-037**: `is_link_active()`... nothing would catch future drift between the two copies~~ — **closed V22.0** (2026-08-05). A 6-test regression tripwire now directly compares both implementations' accept/reject decisions across every boundary case; would fail immediately on future drift.
- ~~**Observability wiring unconfirmed** (ENG-017)~~ — **closed V22.0** (2026-08-04), re-classified with full IMPLEMENTED/WIRED/TESTED evidence. One genuine gap found and fixed (Celery task metrics); one new gap found and filed as ENG-044 (below).

## Missing capabilities

- **No profile/account-settings screen** (ENG-033, PROF-001): a signed-in user has no in-app way to change their password or manage their account. This is new-feature work requiring product/design direction (what fields, what flow), not a bug fix — a full proposal is preserved at `archive/sprint7-18/root-reports/PRODUCT_PROPOSAL.md`, decision options in `docs/governance/ENG-033_DECISION.md`. Unchanged as of V24.0.
- **No automated CD/deploy job** (ENG-034): CI (`.github/workflows/ci.yml`) is comprehensive (lint, full test matrix, migration smoke test, dependency/security scanning, Docker build check) but the Docker build never pushes an image, and no deploy job exists in the workflow. The actual live deployment mechanism is Railway's auto-deploy-from-`origin/main`, which works but is undocumented as a repeatable, reviewable process. Decision options in `docs/governance/ENG-034_DECISION.md`. Unchanged as of V24.0.
- **ENG-044** (found V22.0, still open): Celery worker metrics don't appear on the API's `/metrics` endpoint — separate-process Prometheus registries, no multiprocess-registry wiring exists. Instrumentation itself is correct and unit-tested; this is a deployment-wiring gap needing an ops decision on the shared-volume approach for the target environment (Railway).

## Documentation debt

- ~~`docs/release/` still contains 13 pre-existing historical reports...~~ — **done V24.0** (2026-08-09). All 14 moved to `archive/release-rc1-early-reports/` via `git mv` (history preserved). `docs/release/` now contains exactly 4 current, non-superseded files.
- `docs/product-review/` has 9 files from an earlier product-review sprint not cross-checked against the current `ENGINEERING_BACKLOG.md` — **still not verified as of V24.0** (not in scope for this sprint's Step 4 sweep, which focused on code/CI/changelog currency rather than every docs subdirectory). Flagged here rather than silently left unaddressed, for a future pass.
