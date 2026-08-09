# Progress Log — V14.0/V15.0 Owner Mode Sprint (continuous)

Narrative progress log, one entry per closed (or explicitly deferred) backlog item. Mechanical detail lives in `ACTION_LOG.md` / `FIX_LOG.md` / `REGRESSION_REPORT.md`; this file is the readable summary of "what's done, what's left, in what order." V15.0 continues V14.0's backlog and evidence — no work is redone, only the process (commit format, per-issue dead-code sweep, dashboard shape) is refined going forward.

## Dashboard

**Reconciled 2026-08-09 (V24.0 continuation, updated after ENG-050)** — see `ENGINEERING_BACKLOG.md`'s "Reconciled totals" note for the full record.

| Field | Value |
|---|---|
| Current issue | Phase 3 full end-to-end workflow regression in progress |
| Previous issue | ENG-050 (Access Control "Revoked" mislabel on never-shared documents, found live during Phase 3, fixed same-day) |
| Next issue | 5 open items (ENG-033/034/038/044/049), each blocked on a named external input, evidence-based low-risk classification, or a low-priority test-quality tightening — not engineering-actionable without that |
| Critical remaining | 0 / 0 |
| High remaining | 1 / 5 (ENG-033 — needs product/design input, decision record on file) |
| Medium remaining | 1 open / 15 total (ENG-034 needs ops decision — decision record in `docs/governance/ENG-034_DECISION.md`; 11 closed incl. ENG-039/041/042/045/050; 3 deferred: ENG-005/023/026 [ENG-026 severity revised Medium-High→Medium]) |
| Low remaining | 3 open / 21 total (ENG-038 reclassified low-risk-inference, ENG-044 needs ops/infra input, ENG-049 new test-coverage-gap finding, low priority; ENG-037/046/047 all closed; 12 closed incl. ENG-040/043; 3 deferred, 3 reviewed-not-implemented) |
| Enhancement remaining | 0 open / 8 total (ENG-019 closed V23.0 — full browser sweep; ENG-017/018/020/013/014 closed; ENG-015 justified, ENG-016 deferred) |
| Overall % | 68.0% (34/50 closed, 11 deferred/reviewed/justified, 5 open) |
| Current commit | (ENG-050 fix commit follows this update) |
| Last regression | PASS — post-ENG-050, 2026-08-09 (`eslint` clean / frontend 15/15 unaffected / build 309.3kb / backend untouched, frontend-only fix). |
| Current blocker | None — all 5 remaining open items are correctly blocked on external input, evidence-based low-risk reclassification, or are a newly-filed, correctly-scoped-out low-priority finding |
| Estimated completion | Every item ENG-001 through ENG-050 is now FIXED, PROVEN FALSE, VERIFIED-AND-DEFERRED, or CLASSIFIED AS A DECISION ITEM — zero unexplained entries, zero contradictory statuses, zero unresolved High/Critical defects, **zero partially-fixed items**. |

\* Backlog expanded from 21 to 31 items this cycle after merging `ISSUE_DATABASE.md`/`TODO_QUEUE.md` findings — see the V16.0 reconciliation entry below. This is real newly-surfaced scope, not re-litigation of closed work.

\* ENG-005/ENG-011/ENG-012 counted as remaining/deferred, though all three deferrals were actively re-confirmed this cycle, not silently carried forward.

## Burndown (recomputed V24.0 continuation, 2026-08-09, post-ENG-050 — 50 items, all triaged)

| Priority | Total | Closed | Deferred (reasoned) | Reviewed/Justified | Open (blocked on external input / low-risk) |
|---|---|---|---|---|---|
| Critical | 0 | 0 | 0 | 0 | 0 |
| High | 5 | 4 | 0 | 0 | 1 (ENG-033 — product/design, decision record on file) |
| Medium | 15 | 11 | 3 | 0 | 1 (ENG-034 — ops/deployment policy, decision record on file) |
| Low | 21 | 12 | 3 | 3 | 3 (ENG-038 — low-risk inference, no reproducible race; ENG-044 — needs ops/infra multiprocess-registry decision; ENG-049 — 2 tests assert less than their docstring promises, new finding, low priority) |
| Enhancement | 8 | 6 | 1 | 1 (justified) | 0 |
| Verification-only (no severity) | 1 | 1 | 0 | 0 | 0 |
| **Total** | **50** | **34** | **7** | **4** | **5** |

`34 + 7 + 4 + 5 = 50`. **ENG-046 is fully closed** — the `backend/tests` remainder (206 violations across 50 files) was individually categorized and fixed (not blind `--fix`), with the literal CI command (`ruff check backend/app backend/tests`) now passing cleanly; that review surfaced **ENG-049** (2 tests asserting less than their docstrings promise, Low severity, test-quality — not a product defect, correctly scoped out). Phase 3's live end-to-end workflow regression then found and fixed **ENG-050** the same day (a misleading "Revoked" status shown on every never-shared document — a real, reproducible Medium-severity UX defect in the single most common first Access Control interaction). See `docs/engineering/FIX_LOG.md`/`ACTION_LOG.md` for the full investigation trail and `ENGINEERING_BACKLOG.md`'s ENG-046/049/050 entries for complete detail.

## V22.0 — Residual Risk Closure sprint (2026-08-04 to 2026-08-08)

**Priority 1 (ENG-039)**: traced the complete API-key authorization path and found a real root-cause defect — `orgs.py`/`api_keys.py`/`billing.py` (21 routes) had no scope enforcement at all, so a zero-scope API key could manage organizations, rotate other keys, and read/change billing. Fixed at the root (6 new scopes added to `API_SCOPES`, all 21 routes scoped, plus a new `_reject_scope_escalation()` guard), with 28 new regression tests proven via `git stash` revert to catch the original bug (12/28 failed pre-fix). Extending the same matrix to all 10 router families found 3 more instances of the identical pattern — **ENG-041** (admin audit-log), **ENG-042** (10 annotation routes), **ENG-043** (notifications SSE stream) — all fixed the same way; 7 other routers confirmed already correct and left untouched.

**Priority 2**: a bounded authorization-consistency review (`docs/security/API_AUTHORIZATION_MATRIX.md`) found no further instances beyond Priority 1's 4 — no unlimited rewrite performed, per the mandate's explicit bound.

**Priority 3 (ENG-017)**: re-classified observability with full IMPLEMENTED/WIRED/TESTED/DEPLOYED/EXTERNALLY-MONITORED evidence — most claims were already correct and simply unconfirmed. One real gap found and fixed: zero Celery worker instrumentation (added task-duration/outcome metrics). One new gap found while live-testing the fix and filed rather than silently worked around: **ENG-044** — worker-recorded metrics are invisible on the API's `/metrics` due to `prometheus_client`'s per-process registry and no multiprocess-registry setup; classified as an ops/infra requirement, left open.

**Priority 4 (ENG-040)**: verification-only sweep of all 8 uploader-controlled Viewer toggles — 7 already fully correct, the 8th (`show_reading_insights`) was the exact defect class this sweep exists to catch, already fixed earlier this sprint (ENG-035/036) before the formal sweep began. No decorative toggles found, none created.

**Priority 5 (ENG-037)**: investigated merging `is_link_active()` into `validate_link()`'s real enforcement path and deliberately did **not** — the merge would add complexity (a reason-code abstraction layer) for a currently-theoretical risk. Added a 6-test regression tripwire instead, closing the actual risk (silent future drift) without touching the app's highest-stakes function.

**Priority 6 (ENG-038)**: per the mandate's explicit instruction not to fix concurrency based on intuition, attempted genuine reproduction against the real Docker stack — 2 real owners, concurrent removal requests via `asyncio.gather`, 2 clean trials. The race did **not** reproduce in either trial. Reclassified from assumed-exploitable to low-risk inference; deliberately did not add a lock without a reproducible failing test.

**ENG-033/034/AUTH-006 (decision and architectural-risk items)**: wrote full decision records for ENG-033 (`docs/governance/ENG-033_DECISION.md`) and ENG-034 (`docs/governance/ENG-034_DECISION.md`) per the mandate's exact required structure — both left OPEN/DECISION REQUIRED, nothing implemented without product/ops sign-off. Re-evaluated AUTH-006 with a new finding (`backend/app/middleware/security_headers.py`'s hash-based CSP is a genuine mitigating control, narrowing the realistic exploit chain to two independent failures) — severity revised Medium-High→Medium, migration plan remains fully documented and unimplemented pending an approved decision (`docs/security/SECURITY_HARDENING_PLAN.md` §9).

**Final re-certification**: full backend suite host-run clean (1751 passed/1 skipped/0 failed — a first attempt via `docker compose exec` surfaced 25 failures traced to pre-existing tests hardcoding a host absolute path, not a regression, resolved by running host-side per this repo's established convention). Frontend 13/13, build 309.2kb, migration head 027 confirmed live. Live API smoke pass plus a full create→validate→edit→propagate→revoke→reject-410 link-lifecycle check against the real Docker stack, using a disposable link on the test account's own document. Final deliverable: `docs/release/V22_RESIDUAL_RISK_CERTIFICATION.md`, verdict **RELEASE STATUS: READY WITH DOCUMENTED LIMITATIONS**.

## V21.0 — Production Release Closure sprint (2026-08-02 to 2026-08-04)

**State recovery**: `git status` at sprint start showed 62 modified/new files — implemented-but-never-committed work spanning multiple earlier sprints (Sprint V6.0 governance fixes, the 2026-07-14 JWKS-outage resilience fix, V10.0-era Viewer/Reading-Intelligence work, dashboard-screen fixes, doc corrections, live-QA evidence). Verified the whole body coherent (full test/lint/build suite passed against it as a unit) before committing it in 8 logically-grouped commits — the repository's working tree is fully clean for the first time this session.

**Targeted re-verification** of the newly-committed authorization-consolidation and Reading-Insights code found and fixed 2 real defects: **ENG-035** (the `show_reading_insights` comparative-insights feature was fully built server-side but had no UI toggle anywhere to actually enable it) and **ENG-036** (the "average page time" comparison query didn't exclude the requesting viewer's own session, making it self-referential for single-reader pages — the fix was proven by a new test asserting an exact numeric value, not just absence of a crash). Surfaced 3 more real findings, documented rather than rushed: **ENG-037** (a "single source of truth" refactor's own claim doesn't match the code — the enforcement path still duplicates the logic), **ENG-038** (a pre-existing TOCTOU race, confirmed via git history not to be a new regression), and **ENG-039** (API keys with zero scopes can manage Organizations/API-Keys/Billing — a real permission gap needing a security-reviewed rollout, previously flagged in an archived report but never actually filed to the backlog until now).

**Documentation consolidation**: archived V18.0's 6 certification deliverables, relocated the still-live security hardening plan into `docs/security/`, corrected every cross-reference, corrected an inflated README claim (unbacked "Supabase SAML integration" — zero SAML code found anywhere in the repo), corrected 3 stale numbers, added a documentation index, and produced ONE consolidated `docs/release/FINAL_RELEASE_CERTIFICATION.md` (superseding every prior scattered `FINAL_*` document) with a companion `KNOWN_LIMITATIONS.md`.

## V20.0 — Backlog triage sprint (2026-08-01)

Triaged the 4 items still open after V18.0 (ENG-032/033/034 surfaced by V18.0's documentation cleanup, plus the pre-existing ENG-017/018/019/020 Enhancement tier) through the same STEP 1/2/3 re-verification discipline used throughout this session. **ENG-032 corrected**: re-verification found the production-safety guard it described already exists (`backend/app/main.py:27-54`) — both the original finding and this session's own earlier check had only looked in `config.py` and missed it. A redundant fix was attempted, caught by its own regression run, and reverted — net zero code change, closed as "no longer reproducible" (this correction is the model this sprint's own ENG-037/038 corrections followed). **ENG-018 and ENG-020 closed** via genuine integration-level verification against the real local Docker stack (a synthesized 120-page PDF for ENG-018; hand-verified reading-analytics math, including confirming a `700.0` wpm result was a documented physiological-plausibility clamp firing correctly, not a placeholder, for ENG-020). **ENG-019 partially verified** (2 of many toggles confirmed round-trip correctly) and left honestly open rather than overclaiming full closure. **ENG-033/034/017 remain open**, each blocked on a named external input outside pure engineering scope, not stalled.

## V18.0 — Repository Certification sprint (2026-07-31)

Full-repository "Zero Technical Debt" certification per the V18.0 mandate — not a product-bug sprint. 5 parallel research passes (backend/frontend dead-code, dependency/CI audit, documentation audit, module-boundary audit) plus a targeted 6th pass on the dependency graph. Produced 6 deliverables, since archived to `archive/sprint18-certification/` as part of V21.0's documentation consolidation: `REPOSITORY_CERTIFICATION.md`, `DEAD_CODE_REPORT.md`, `DEPENDENCY_AUDIT.md`, `MODULE_BOUNDARY_REPORT.md`, `DOCUMENTATION_CLEANUP_PLAN.md`, `FINAL_REPOSITORY_SCORECARD.md`. Fixed: 2 dead imports, 1 dead function + its test class, 1 dead CSS keyframe, 1 duplicate function, 5 dependency-hygiene issues (3 removed packages, 5 re-pinned versions, 1 CI fix), and archived 48 obsolete documentation files (root reduced from 55 `.md` files to 14). Verdict: 8/10 stop conditions fully Met, remaining 8 Substantially met, 0 Not Met — every documented exception has file:line evidence, an effort estimate, and a regression-risk assessment rather than being silently dropped. Full details in `archive/sprint18-certification/FINAL_REPOSITORY_SCORECARD.md`.

**High, Medium, and Low tiers: 0 open items remain** (all closed or deferred/reviewed with fresh, on-record reasoning). Only the Enhancement tier has open items (ENG-017/018/019/020). Per V17.0's explicit gate, a full repository certification pass runs next, before any Enhancement-tier work begins.

### Low tier closed this cycle (V17.0 STEP 1/2/3 process)

| ID | Outcome |
|---|---|
| ENG-024 | Closed — date-formatting consistency (shared `fmtDate()`/local `fmtDateTime()`) |
| ENG-025 | Reviewed, not implemented — empty-state gap partly semantically justified; no canonical pattern without design input |
| ENG-027 | Reviewed, not implemented — 4 animation durations are a defensible sequencing pattern, not a bug |
| ENG-028 | Reviewed, not implemented — icon replacement needs a design decision |
| ENG-030 | Closed — row-level Revoke/Delete buttons now `ghost`+red, matching majority pattern |
| ENG-031 | Closed — owner preview watermark now shows real email, source + integration/API-verified |

## 2026-07-26 — Sprint start

Read all six V13.0 reports (`FIXES_TODO.md`, `RELEASE_BLOCKERS.md`, `FINAL_RELEASE_CERTIFICATION.md`, `UI_EXCELLENCE_SCORECARD.md`, `ARCHITECTURE_CERTIFICATION.md`, `CODE_QUALITY_CERTIFICATION.md`) and merged every issue into `ENGINEERING_BACKLOG.md` — 20 canonical issues (0 Critical, 3 High, 3 Medium, 6 Low, 8 Enhancement), deduplicated across reports, each with severity/evidence/affected files/effort/regression risk/priority/status.

Stood up a full local Docker stack (`docker compose up --build`) specifically so every subsequent fix can be genuinely browser-verified before it ever reaches the production-auto-deploying `origin/main` branch, rather than trusting source-code reasoning alone or verifying against production.

## ENG-001 — Analytics screen overflow at 768px — CLOSED

Real, reproducible bug: at the app's own stated minimum supported width, a whole KPI card and a whole sidebar panel rendered fully off-screen with no scroll escape. Root cause was a fixed (non-responsive) CSS grid template inconsistent with a working pattern already present elsewhere in the same file. Fixed by matching that existing pattern. Browser-verified at 768px/834px/1440px via the local stack — zero clipping, zero visual regression at the wide desktop width. Both test suites unchanged (1708 backend, 13 frontend) — expected, since this was a CSS-only change.

**Next**: ENG-002, Notifications feed.

## ENG-002 — Notifications feed lacks document identity — CLOSED

Real, high-impact usability defect: the endpoint backing the Notifications screen never returned a document identifier, so every entry rendered as an undifferentiated "Page viewed" — the screen could not do what its own subtitle claims. Fixed by extending two queries the endpoint already ran (no new query added) to also carry `Document.filename` through to the response, plus surfacing the already-present-but-unused `page_number` field on the frontend. Browser-verified end-to-end on the local stack: created a real link, generated real view events, confirmed the owner's feed now names the actual document and page for every entry. Both test suites unchanged.

**Next**: ENG-003, cross-account IDOR verification.

## ENG-003 — Cross-account IDOR verification — CLOSED, no defect found

The largest evidence gap cited across all of V13.0's security work: the authorization pattern was architecturally sound by code inspection but had never been proven live against a genuine second account. Created one (against the local stack only — separate database, zero production risk) and directly attempted cross-account access to a real document, share link, and API key. Every attempt was blocked correctly, with zero leakage and zero unauthorized modification, confirmed by re-checking Account A's data afterward. This is now genuinely closed, not just architecturally inferred.

One small side-finding surfaced during this test and logged as a new, low-priority item (ENG-021): link-mutation endpoints answer cross-account attempts with 403 instead of the 404 used everywhere else, a minor inconsistency in the "never confirm resource existence" pattern — not practically exploitable, not yet fixed.

**Next**: ENG-004, document picker disambiguation.

## Post-High-tier regression pass — 2026-07-26 18:01

Per explicit instruction: before starting Medium-priority work, re-ran browser verification on every workflow touched by ENG-001/002/003, against fresh logins (original tokens were ~1hr old, re-authenticated both accounts rather than assume they were still valid).

- Analytics screen re-checked at 768px/834px/1440px — Completion card and Groups-at-a-glance panel both still fully within viewport at all three widths, zero clipping.
- Notifications feed re-checked — still shows the real document name (`sem6 (1).pdf`) on activity entries, not generic undifferentiated text.
- IDOR re-checked — fresh cross-account `GET /api/documents/{A_doc_id}` as Account B still returns 404.
- Backend suite: 1708 passed, 1 skipped, 0 failed (unchanged). Frontend suite: 13/13 passed (unchanged).

**Zero regressions.** Proceeding to Medium-priority tier (ENG-004).

## ENG-004 — Document picker disambiguation — CLOSED

Small, additive fix: the share-link creation flow's document picker showed only filename/pages/views, with no way to tell apart documents sharing a filename. Added an "uploaded {date}" line using the app's existing date formatter. Browser-verified on the local stack, zero layout regression, both test suites unchanged.

## ENG-005 — List-endpoint pagination — DEFERRAL RE-CONFIRMED

Did not silently carry the original "Deferred" status forward. Attempted to pull a fresh production document count to confirm the scale reasoning still held; the saved session token had expired, and re-authenticating solely to refresh a count that couldn't plausibly have changed materially (no new customer onboarding this sprint) was judged disproportionate. Logged explicitly as Not-enough-evidence for an updated exact number, with an engineering inference that the "before 10,000 users" deferral reasoning is unaffected. Still deferred — this time with a real re-examination on record, not a stale carry-forward.

## ENG-006 — Storage blocking-I/O audit — CLOSED, no defect found

Flagged because this exact bug class already caused one real production issue once (V4.0). Full repo-wide audit: all boto3/S3 usage confined to one file, all 6 methods correctly wrap their blocking calls in `run_in_executor`. Clean.

## Medium-tier completion regression pass — 2026-07-26

Per explicit process rule (browser regression pass after each completed tier): re-logged in fresh, swept all 10 dashboard screens for raw error text and console errors — zero found on either. Re-confirmed ENG-004's document-picker fix still shows upload dates. Both test suites re-run, unchanged.

**Medium tier complete. Proceeding to Low tier (ENG-007).**

## ENG-007 — Audit Log scroll affordance — CLOSED (first V15.0 issue)

The Details column was reachable via scroll but had no visual hint that it continued off-screen at narrow widths. Gave the table its own dedicated scroll container and a scroll-position-aware fade — shown only while there's genuinely more to scroll to. Browser-verified: fade present at 834px (real overflow), absent at 900px/1440px (no overflow). First issue processed under V15.0's refined process: expanded regression sweep (TODO/FIXME/console.log/debugger/print() — clean, 5 backend matches all confirmed as instructional comments not real debug code) and migration validation (exit 0) now run alongside the existing test-suite + browser-verification routine.

## ENG-008 — Rate-limit 429 boundary — CLOSED, boundary confirmed exact

Sent exactly 21 wrong-password validate attempts against one disposable test link: attempts 1-20 returned 401 (correctly rejected, not rate-limited yet), attempt 21 returned 429. The configured 20/minute threshold is exact in live behavior, not just in configuration — no off-by-one in either direction. No defect found. Test link revoked immediately after.

## ENG-009 — XSS beyond link labels — CLOSED, no defect found

Tested the same payload already proven inert for link labels against the three remaining untested fields: organization name, API key name, webhook description. All three rendered as literal text, zero injected `<img>` elements, zero JS dialogs, zero console errors — confirmed via screenshot, not just a DOM query. Also source-verified: zero `dangerouslySetInnerHTML` anywhere in the frontend. This closes the last open item from the original security review's XSS coverage. All disposable test resources deleted immediately after.

## ENG-010 — Expired-link live confirmation — CLOSED, live-confirmed

The dashboard UI only supports date-granularity expiry, which made a live wait-it-out test impractical in earlier sprints — the backend schema was checked and confirmed to accept full datetime precision regardless. Created a disposable link expiring 75 seconds out: validate returned 200 before, then 410 "Link expired" after an 80-second wait. Exact same response shape as the already-verified revocation path.

**This closes the last "Not enough evidence" item from `SECURITY_CERTIFICATION.md`'s original review.** Every explicit evidence gap from that review — cross-account IDOR, rate-limit boundary, XSS beyond one field, expired-link enforcement — is now independently live-confirmed, not just architecturally inferred.

## ENG-011 / ENG-012 — Scaling deferrals re-confirmed (not silently skipped)

Neither triggering condition (horizontal scaling for ENG-011's connection pooling, a customer requirement for instant propagation for ENG-012's cache invalidation) arose this sprint. Both remain correctly deferred, now with an active re-check on record rather than a stale carry-forward.

## ENG-021 — Link mutation endpoints return 404 not 403 cross-account — CLOSED

Found during ENG-003's IDOR verification. `links.py`'s revoke/update/hard-delete endpoints leaked "a link with this ID exists" to unauthorized callers via 403, inconsistent with the app-wide 404 pattern (and inconsistent with `links.py`'s own sibling create/list endpoints). Fixed by collapsing both failure branches to 404. Discovered 2 existing tests had been asserting the old, inconsistent 403 — updated them, and added a third test for the hard-delete endpoint which had zero prior cross-account coverage. Proved the tests meaningful via revert-and-confirm-fail, then restore-and-confirm-pass. Browser/API-verified with fresh Account A/B logins: all 3 endpoints now correctly return 404.

**This closes the entire Low-priority tier** — 5 items fixed/verified, 2 correctly deferred with fresh reasoning, 0 open.

## Low-tier completion regression pass — 2026-07-27

Per explicit process rule (regression pass after each completed tier): fresh logins for both test accounts, full sweep of all 10 dashboard screens (zero raw errors, zero console errors), re-confirmed ENG-007's scroll fade still renders at 834px and ENG-021's cross-account link mutation still returns 404. Both test suites re-run (1709 backend, 13 frontend), build succeeded, migration validated (exit 0).

**Zero regressions. Low tier fully closed out. Proceeding to Enhancement tier.**

## V16.0 — Backlog reconciliation (2026-07-28)

Per V16.0's instruction to read `ISSUE_DATABASE.md` and `TODO_QUEUE.md` as canonical sources: found they contradicted each other on ~10 items' completion status. Source-verified a 3/3 sample directly against current code — all confirmed done, `ISSUE_DATABASE.md` was simply stale (never updated after V10.0 shipped those fixes). Reconciled its status column, then merged the 10 genuinely-still-open items into `ENGINEERING_BACKLOG.md` as ENG-022 through ENG-031 (2 already deferred with reasoning, 8 open) — no duplicate tracking, `ENGINEERING_BACKLOG.md` remains the single source of truth.

## ENG-029 — Architecture docs contradiction — CLOSED

`ARCHITECTURE.md` and `OVERVIEW.md` disagreed on cache TTLs and the watermark model. Source-verified ground truth directly against `viewer_cache.py`/`watermark.py`: `ARCHITECTURE.md` had 2 real errors (link/session TTLs both stated as 30s, actual 10s/5s) and mislabeled the visible watermark as "forensic" while omitting the two actual forensic stamps. `OVERVIEW.md` was already correct on both. Fixed `ARCHITECTURE.md` to match, with a source-of-truth citation added to prevent future drift.

## ENG-013 — Frontend lint tooling + dead-code cleanup — CLOSED

Added a minimal ESLint setup (unused-vars only, deliberately narrow scope) — the frontend's equivalent of the backend's `ruff` sweep. 19 findings across 9 files, each individually investigated before removal (not blind auto-fix): traced `TocSidebar.jsx`'s dead `error` state to confirm the existing empty-state UI already covers the failure case; confirmed `ViewerScreen.jsx`'s unused destructures come from hooks that still use that state internally, only removing the unused consumer-side bindings. Converted 5 unused `catch (e)` blocks to parameter-less `catch { }`.

Found and fixed a real Docker build break along the way: the regenerated `package-lock.json` (created on macOS) didn't include Linux/Alpine-only optional platform packages that `esbuild` needs, breaking `npm ci` inside the container. Regenerated the lockfile from inside a `node:20-alpine` container to match the actual build target.

`npm run lint` now exits 0. Full Docker rebuild verified working, browser-verified across 6 screens plus the Viewer (opening a real document to exercise the touched hooks) — all clean, zero console errors. Both test suites unchanged; build shrank slightly (312.9kb → 312.5kb) from the dead-code removal.

## ENG-014 — Duplicate-code scan — CLOSED

Ran `jscpd` for the first time: 24 clones total, 1.70%/0.25% duplicated lines (Python/JSX) — low by industry norms. Reviewed all 24 individually rather than mechanically fixing every match. Fixed one real, valuable case: `analytics_service.py`'s `get_document_analytics` and `get_group_analytics` both independently ran the identical batch link-event-aggregation query block — extracted into a shared helper, removing real drift risk. Investigated the closest remaining candidate (`annotation_export_service.py`/`annotation_thread_service.py`) closely enough to find their `SELECT` shapes genuinely differ, making extraction not worth the added complexity. The remaining 20 clones documented as reviewed, not extracted (small same-file patterns or expected adapter-contract similarity).

Hit the same class of Docker lockfile issue as ENG-013 a second time (installing `jscpd` locally reintroduced the platform-dependency drift) — this time it broke the *local* Mac environment instead when I over-corrected. Fixed properly by installing on both platforms in sequence against one lockfile and verifying `npm ci` independently on each in isolation, not just one.

Browser-verified both refactored code paths (Analytics screen + "By Group" tab) render real data with zero console errors. Both test suites unchanged.

## ENG-024 — Date-formatting consistency — CLOSED

Per V17.0's STEP 1/2/3 process: re-verified the original finding was still reproducible (confirmed — 3 files reimplementing date formatting ad hoc, 1 file repeating an identical expression 3 times), judged it worth fixing (usability + maintainability + reduced future-bug risk), then implemented the smallest safe consolidation. Explicitly investigated and declined to touch a look-alike case (`fmtTime()` duplicated by name across two files) after confirming via source read that the two versions are semantically different — relative vs. absolute time — not true duplication. Browser-verified across 3 screens on the local stack, zero console errors, both test suites unchanged.

---

## V23.0 — ENG-019 browser sweep completion + ENG-045 (2026-08-08)

Per the V23.0 baseline commit, the browser-automation blocker that had kept ENG-019 partially open since V20.0 is resolved (Playwright+Chromium found working in the host miniconda3 environment, confirmed against both the live Railway deployment and the local Docker stack). Completed the full remaining sweep genuinely Browser Verified rather than re-deriving it from memory or re-stating the old partial-verification note.

**Access Control link toggles**: created a disposable link on the live app, toggled Download at creation and Print via the Edit modal, then forced a hard full-page reload before re-opening the Edit modal — both toggles read back correctly, confirming genuine backend persistence rather than client-side state. Confirmed `role="switch"`/`aria-checked` semantics (real accessibility affordance, not styled divs), a success toast on create, and explicit confirmation dialogs on both Revoke and hard Delete. Disposable link fully cleaned up; its full create/update/revoke/delete lifecycle showed up correctly and promptly in the Audit Log. A legacy test link literally named `<img src=x onerror=alert(1)>` rendered as inert text everywhere it appeared, reconfirming ENG-009.

**Organizations role/settings toggles**: found the Members modal's role dropdown and Remove button aren't disabled based on the caller's own role — but verified via source (`orgs.py:414`, `minimum_role="admin"`) and a live self-targeted test that the backend correctly rejects with `403` and the frontend shows an accurate "Requires admin role or higher" toast with a clean dropdown revert. Judged this a minor proactive-affordance polish item, not a defect (documented under ENG-019/ENG-045 rather than filed as new backlog scope for a control that already fails safely). Deliberately did not attempt a live role mutation against the real org's actual owner (the account holder's own org membership) — that would risk altering real production state for no additional evidence the source read + self-targeted 403 test didn't already provide.

**Remaining ~8 screens**: full sweep, zero console errors anywhere, empty states and real data all render correctly.

**ENG-045 (new, found and closed same sprint)**: the sweep surfaced a real, reproducible defect — the sidebar's "Feedback" shortcut is supposed to jump straight to a document's Feedback tab (`AppShell.jsx` renders `<AccessScreen defaultTab="feedback">` for that entry), but selecting a document from that entry point silently switched to the plain Access Control screen instead (landing on "Create Link", sidebar highlight flipping to "Access Control"). Root cause: both the Feedback and Access Control entry points shared the same `onSelectDoc` handler, which unconditionally forced `screen` to `'access'`. Fixed with a dedicated handler for the Feedback entry point (3-line diff, `AppShell.jsx` only). Verified pre-fix on the live app, then rebuilt and verified post-fix on the local Docker stack — both the fixed Feedback flow and the untouched Access Control flow behave correctly. Regression-verified: backend 1751 passed/1 skipped/0 failed (unaffected, frontend-only change), frontend 13/13, `eslint` clean, build succeeded (309.2kb), isolated diff confirmed exactly 3 lines changed in exactly one file.

Both ENG-019 and ENG-045 closed this sprint. Remaining open items (ENG-033, 034, 037, 038, 044) are unchanged from V22.0 — each still blocked on a named external input (product/design/ops decision, or already downgraded to a low-risk inference) rather than being engineering-actionable this session.

---

*(This file is appended to after every closed or explicitly-deferred backlog item — see `ENGINEERING_BACKLOG.md` for the full remaining queue.)*
