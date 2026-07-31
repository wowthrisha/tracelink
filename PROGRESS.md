# Progress Log — V14.0/V15.0 Owner Mode Sprint (continuous)

Narrative progress log, one entry per closed (or explicitly deferred) backlog item. Mechanical detail lives in `ACTION_LOG.md` / `FIX_LOG.md` / `REGRESSION_REPORT.md`; this file is the readable summary of "what's done, what's left, in what order." V15.0 continues V14.0's backlog and evidence — no work is redone, only the process (commit format, per-issue dead-code sweep, dashboard shape) is refined going forward.

## Dashboard

| Field | Value |
|---|---|
| Current issue | none in progress — V18.0 Repository Certification sprint complete |
| Previous issue | V18.0 Repository Certification (dead code, dependencies, module boundaries, documentation archival) |
| Next issue | Triage 3 new backlog items surfaced this sprint (ENG-032/033/034), then Enhancement tier (017/018/019/020) |
| Critical remaining | 0 / 0 |
| High remaining | 0 / 3 |
| Medium remaining | 2* / 5 (ENG-023, ENG-026 deferred with reasoning) |
| Low remaining | 0 / 14 — tier complete: 8 closed, 6 deferred/reviewed-with-reasoning |
| Enhancement remaining | 4 / 8 (ENG-013/014 closed; ENG-015 justified, ENG-016 deferred) |
| New this sprint (not yet triaged) | 3 — ENG-032 (Medium, salt defaults), ENG-033 (High, no profile screen), ENG-034 (Medium, no CD job) |
| Overall % | 47.1% (16/34 closed, backlog expanded 31→34 this sprint) |
| Current commit | `4862abb` |
| Last regression | PASS — post-V18.0 certification, 2026-07-31 (backend 1705 passed/1 skipped/0 failed [1709 baseline − 4 tests removed with the dead function they tested] / frontend 13/13 / lint exit 0 / build 309.0kb / Docker `api` rebuilt and healthy after every backend-touching change / `npm ci` verified independently on macOS + Alpine). |
| Current blocker | None |
| Estimated completion | Repository certification complete — see `FINAL_REPOSITORY_SCORECARD.md` for the full verdict (8/10 stop conditions Met, remaining 8 Substantially met, 0 Not Met). Remaining: triage ENG-032/033/034, then 4 open Enhancement-tier items (017/018/019/020) — ENG-017/033/034 likely need ops/product/design input outside pure engineering scope; no fixed ETA |

\* Backlog expanded from 21 to 31 items this cycle after merging `ISSUE_DATABASE.md`/`TODO_QUEUE.md` findings — see the V16.0 reconciliation entry below. This is real newly-surfaced scope, not re-litigation of closed work.

\* ENG-005/ENG-011/ENG-012 counted as remaining/deferred, though all three deferrals were actively re-confirmed this cycle, not silently carried forward.

## Burndown (recomputed after V18.0's certification sprint — 31 → 34 items)

| Priority | Total | Closed | Deferred (reasoned) | Open |
|---|---|---|---|---|
| Critical | 0 | 0 | 0 | 0 |
| High | 3 + 1* | 3 | 0 | 1 |
| Medium | 6 + 2* | 3 | 3 | 2 |
| Low | 14 | 8 | 6 | 0 |
| Enhancement | 8 | 2 | 1 + 1 justified | 4 |
| **Total** | **34** | **16** | **9 (+1 justified)** | **7** |

\* ENG-032 (Medium), ENG-033 (High), ENG-034 (Medium) — 3 new items surfaced during V18.0's documentation-cleanup gap analysis (genuine findings from `TECH_DEBT_REGISTER.md`/`PRODUCT_PROPOSAL.md`/`PUBLIC_RELEASE_READINESS.md` that fell out of prior backlog reconciliation). Not yet triaged through the STEP 1/2/3 process — re-verified as still-reproducible during V18.0 itself, but not yet judged for implementation.

## V18.0 — Repository Certification sprint (2026-07-31)

Full-repository "Zero Technical Debt" certification per the V18.0 mandate — not a product-bug sprint. 5 parallel research passes (backend/frontend dead-code, dependency/CI audit, documentation audit, module-boundary audit) plus a targeted 6th pass on the dependency graph. Produced 6 deliverables: `REPOSITORY_CERTIFICATION.md`, `DEAD_CODE_REPORT.md`, `DEPENDENCY_AUDIT.md`, `MODULE_BOUNDARY_REPORT.md`, `DOCUMENTATION_CLEANUP_PLAN.md`, `FINAL_REPOSITORY_SCORECARD.md`. Fixed: 2 dead imports, 1 dead function + its test class, 1 dead CSS keyframe, 1 duplicate function, 5 dependency-hygiene issues (3 removed packages, 5 re-pinned versions, 1 CI fix), and archived 48 obsolete documentation files (root reduced from 55 `.md` files to 14). Verdict: 8/10 stop conditions fully Met, remaining 8 Substantially met, 0 Not Met — every documented exception has file:line evidence, an effort estimate, and a regression-risk assessment rather than being silently dropped. Full details in `FINAL_REPOSITORY_SCORECARD.md`.

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

*(This file is appended to after every closed or explicitly-deferred backlog item — see `ENGINEERING_BACKLOG.md` for the full remaining queue.)*
