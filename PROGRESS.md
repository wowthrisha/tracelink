# Progress Log — V14.0/V15.0 Owner Mode Sprint (continuous)

Narrative progress log, one entry per closed (or explicitly deferred) backlog item. Mechanical detail lives in `ACTION_LOG.md` / `FIX_LOG.md` / `REGRESSION_REPORT.md`; this file is the readable summary of "what's done, what's left, in what order." V15.0 continues V14.0's backlog and evidence — no work is redone, only the process (commit format, per-issue dead-code sweep, dashboard shape) is refined going forward.

## Dashboard

| Field | Value |
|---|---|
| Current issue | none in progress — ENG-008 just closed |
| Previous issue | ENG-008 (closed — rate-limit boundary confirmed exact) |
| Next issue | ENG-009 (XSS testing beyond link labels) |
| Critical remaining | 0 / 0 |
| High remaining | 0 / 3 |
| Medium remaining | 1* / 3 |
| Low remaining | 5 / 7 |
| Overall % | 33.3% (7/21 closed) |
| Current commit | `05ffe83` (ENG-008 commit pending) |
| Last regression | PASS — post-ENG-008, 2026-07-27 (1708 backend; no frontend/build change, no code touched) |
| Current blocker | None |
| Estimated completion | 14 items remaining; no fixed ETA — evidence-first pacing takes priority over speed |

\* ENG-005 counted as remaining/deferred (pagination itself not built), though its deferral was actively re-confirmed, not silently skipped.

## Burndown

| Priority | Total | Closed | Remaining |
|---|---|---|---|
| Critical | 0 | 0 | 0 |
| High | 3 | 3 | 0 |
| Medium | 3 | 2 | 1* |
| Low | 7 | 2 | 5 |
| Enhancement | 8 | 0 | 8 |
| **Total** | **21** | **7** | **14** |

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

---

*(This file is appended to after every closed or explicitly-deferred backlog item — see `ENGINEERING_BACKLOG.md` for the full remaining queue.)*
