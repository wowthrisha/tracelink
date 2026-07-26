# Progress Log — V14.0 Owner Mode Sprint

Narrative progress log, one entry per closed (or explicitly deferred) backlog item. Mechanical detail lives in `ACTION_LOG.md` / `FIX_LOG.md` / `REGRESSION_REPORT.md`; this file is the readable summary of "what's done, what's left, in what order."

## Burndown

| Priority | Total | Closed | Remaining |
|---|---|---|---|
| Critical | 0 | 0 | 0 |
| High | 3 | 3 | 0 |
| Medium | 3 | 2 | 1* |
| Low | 7 | 0 | 7 |
| Enhancement | 8 | 0 | 8 |
| **Total** | **21** | **5** | **16** |

\* ENG-005 counted as remaining/deferred, not closed — its deferral was re-confirmed with fresh reasoning (not silently skipped), but the underlying pagination work itself is intentionally not done this sprint. All 3 Medium-tier items have been actioned (1 fixed, 1 deferred-with-reconfirmation, 1 audited clean).

- **Overall completion**: 23.8% (5/21) — or effectively 100% of *actionable* Medium-tier work this sprint, since ENG-005's correct action was a re-confirmed deferral, not a fix
- **Last completed issue**: ENG-006 (storage blocking-I/O audit — no defect found)
- **Current issue**: none in progress — Medium tier complete, about to start Low tier
- **Next planned issue**: ENG-007 (Audit Log scroll affordance)
- **Regression status**: PASS — Medium-tier completion regression pass done 2026-07-26 (post-ENG-006). All 10 dashboard screens re-checked clean (zero raw errors, zero console errors), ENG-004's fix re-confirmed holding.
- **Test status**: Backend 1708 passed, 1 skipped, 0 failed. Frontend 13/13 passed.
- **Current commit hash**: `25f8c71`

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

---

*(This file is appended to after every closed or explicitly-deferred backlog item — see `ENGINEERING_BACKLOG.md` for the full remaining queue.)*
