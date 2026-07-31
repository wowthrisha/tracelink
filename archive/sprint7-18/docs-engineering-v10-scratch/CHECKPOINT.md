# Checkpoint — V12.0 Final Production Certification

Overwritten on each update (history lives in `PROGRESS.md`/`ACTION_LOG.md`). Read this first to resume.

---

**Status**: Sprint complete for the scope actually executed. One real, security-relevant bug found and fixed; extensive live verification of the Viewer, Access Control, and Reading Intelligence; all 3 prior-sprint fixes confirmed live in production.

**Headline finding**: `AUDIT-LINK-COMMIT-001` — link creation, editing, and revocation were never actually appearing in the Audit Log in production, despite the code visibly calling the logging function on every request. Root cause: the audit write was flushed but never committed, and got silently rolled back when each request's database session closed. This is exactly the kind of gap a source-code read alone would have missed (the code *looks* correct) and that only the mission's "browser evidence always wins" methodology caught — verified via the raw audit API, not the UI. Fixed, tested (with the tests proven meaningful by reverting the fix and watching them fail), and the 3 missing link event types added to the audit filter allowlist.

**Also confirmed this sprint**: all 3 V10.0 fixes (watermark, owner-lockout, plan badge) are live in production — the commit was pushed and auto-deployed by Railway sometime after the prior sprint, without this session doing so explicitly. Live Viewer mechanics (search, zoom, keyboard nav, fullscreen, Links panel) all verified working. Edit Link permission propagation verified end-to-end, live, across two separate browser sessions. Reading Intelligence pause/resume-on-blur verified live, plus discovery of an undocumented content-blur security behavior on tab-hidden. Reading Intelligence data confirmed real, not fabricated. Keyboard-only navigation confirmed fully functional. Mobile block confirmed intentional (not a bug).

**Verification**: backend 1708 passed / 1 skipped (was 1705 — 3 new tests, zero regressions, each proven to actually catch the bug it targets). No frontend code changed this sprint (all findings were either backend-only or verification-only), so no frontend suite re-run was needed beyond the prior sprint's baseline.

**Deploy status**: the AUDIT-LINK-COMMIT-001 fix is local-only, not deployed. The V11.0 fixes (viewer-facing reading insights panel, error boundary sanitization) remain local-only from the prior sprint too.

**Deliberately not attempted this sprint** (see `FIX_LOG.md`/`REGRESSION_REPORT.md` V12.0 sections for full reasoning): full WCAG 2.2 AA audit, full performance profiling (N+1 queries, render counts, memory leaks), full dead-code sweep, offline/slow-network simulation. Each is a genuine multi-day audit — a shallow pass would produce unverified claims, not real evidence, which the mission's own "never claim perfection unless every claim has been verified" standard explicitly rules out.

**One noted-not-fixed cosmetic item**: the document owner's own preview watermark reads "anonymous" instead of their real email. Low severity, touches the same owner-preview-link machinery as READ-OWNER-001 — queued as its own scoped item (`TODO_QUEUE.md` #24) rather than rushed alongside everything else found this sprint.

**Resume instruction**: if continuing this mission, the two most valuable next steps are (1) deploying the accumulated local-only fixes (V11.0 + V12.0), since none of this sprint's findings help anyone until they ship, and (2) the product/architecture decisions already queued in `REMAINING_DECISIONS.md` from prior sprints — those, not more find-and-fix passes, are now the limiting factor on this repository reaching genuine "enterprise production" status.
