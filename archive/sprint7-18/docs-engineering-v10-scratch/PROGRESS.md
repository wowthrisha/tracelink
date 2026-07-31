# Progress — V11.0 Viewer Excellence

Append-only. Each entry is a phase of this sprint.

---

## Phase 1: Research — what already exists (2026-07-25)

Before writing any code, spawned a research pass over the existing Reading Intelligence Engine, Viewer status bar, InsightsModal, permissions model, and error boundary. Finding: the backend Reading Intelligence Engine (3 tables, EWMA speed model, 6 engagement scores, drop-off detection, NL insights, 6 REST endpoints) and the frontend reading status bar (timer, tab-blur-aware pause/resume, page progress) **already exist and closely match the mission's spec**, built in an earlier sprint. This determined the scope of everything that followed — see `ARCHITECTURE_DECISIONS.md` AD-7 through AD-11 for the full list of what the mission asked for that was deliberately not built, and why.

## Phase 2: Real bug — Insights modal exposed to public viewers (2026-07-25)

Found via the research pass, not newly discovered by testing: the Viewer toolbar's "Insights" button had no ownership check, so a public share-link viewer could click it and trigger 4 uploader-only API calls that 401 and force-reload the viewer's page. Fixed in `ViewerScreen.jsx` (3 call sites: `hasInsights` prop, modal render condition, data-fetch callback). Frontend suite 13/13, build clean.

## Phase 3: New feature — viewer-facing page insights + permission toggle (2026-07-25)

Built the one genuinely-missing piece from the mission that was well-specified and scoped: a viewer-facing panel showing page difficulty, this-page average reading time, and pace-vs-average-reader — gated behind a new `show_reading_insights` link permission. Reused the existing viewer-safe `/api/reading/session/{id}` endpoint (extended, not replaced) and the existing `ShareLink.permissions` pattern (extended with one new key, not a new framework). Caught and fixed a real bug during implementation before it ever ran: `ShareLink.permissions` is a JSON string column, not an ORM dict — the first draft would have thrown `AttributeError` on every request. 2 new integration tests added. Full backend suite: 1705 passed (was 1703), 1 skipped. Frontend suite 13/13, build clean.

## Phase 4: Real bug — error boundary leaked raw error text (2026-07-25)

`ViewerErrorBoundary.jsx` rendered `String(error)` directly to users. Replaced with a friendly message + correlation ID; the real error stays in the console via `componentDidCatch`. Frontend suite 13/13, build clean.

## Phase 5: Documentation and closeout (2026-07-25)

`FIX_LOG.md`, `ISSUE_DATABASE.md`, `TODO_QUEUE.md`, `ARCHITECTURE_DECISIONS.md` all updated. `PROGRESS.md` and `CHECKPOINT.md` created (this sprint's first use of these two filenames). Final suite-wide verification run clean. **Nothing committed or deployed this sprint** — all 4 changes exist only in the local working tree, per standing git policy (commit only on explicit request).

---

# Progress — V12.0 Final Production Certification

## Phase 1: Re-verify prior fixes live, browser-first (2026-07-26)

Per the mission's golden rule ("do not trust previous reports, verify everything again — browser evidence always wins"), re-checked all 3 V10.0 fixes against the live deployed instance before doing anything else. Unexpected discovery: `origin/main` was already at the V10.0 fix commit (`e7ddf47`) — it had been pushed (not by this session) and Railway had auto-deployed it. All 3 fixes confirmed live via direct evidence: watermark pixel analysis, DOM state check for the owner-lockout gate, 3 fresh page loads for the plan badge.

## Phase 2: Deep live Viewer certification (2026-07-26)

Uploaded a fresh 10-page test document with unique searchable terms per page. Verified live, in a real browser: in-document search (found the correct page), zoom presets, keyboard page navigation (ArrowRight), fullscreen toggle (DOM-verified — `document.fullscreenElement` correctly toggled despite no visible screenshot difference, a known headless-browser limitation), Links panel (correct empty state for a document with no hyperlinks), thumbnail rendering (confirmed transient gray thumbnails settle correctly). Confirmed the annotation toolbar is correctly permission-gated (absent by default, matching `can_annotate: false`).

## Phase 3: Access Control live permission verification — major finding (2026-07-26)

Attempted to verify permission toggles propagate live; discovered the "Document Permissions" grid on the Create Link tab is draft form state for a new link, not a live document default (no API call fires until a link is actually created — this was a correct realization, not a bug). Pivoted to the mission's actual ask: edited an *existing* link's Annotations permission and verified, across two separate browser sessions (owner + anonymous viewer), that the change propagates immediately. While verifying this reached the Audit Log, found **AUDIT-LINK-COMMIT-001**: link.created/updated/revoked events were silently never persisted, due to a missing `db.commit()` after the audit-log write's flush-only call. Root-caused precisely (traced through `link_service.py`'s internal commits vs. the router's audit-log placement), fixed in 3 call sites, added the 3 missing event types to the audit filter allowlist, and added 3 regression tests — each proven meaningful by reverting the fix via `git stash` and confirming they fail, then restoring the fix and confirming they pass.

## Phase 4: Reading Intelligence live verification (2026-07-26)

Dispatched real `blur`/`visibilitychange` events against a live, actively-reading session. Confirmed the timer pauses and — beyond what the mission's checklist named — the entire document content visibly blurs while the tab is hidden, a deliberate anti-shoulder-surfing behavior. Confirmed resume works and inactive time is never counted. Checked the owner-only Insights modal's Pages and Reading tabs against real generated traffic — confirmed data is real (53 actual views broken down per page) and that the app shows honest zeros/dashes rather than fabricated numbers when session data is insufficient.

## Phase 5: Scoped accessibility + responsive pass (2026-07-26)

Keyboard-only Tab navigation confirmed to move focus through the sidebar; a Tab×3 + Enter sequence (zero mouse interaction) correctly navigated to the Access Control screen, confirming the `role="button"` + `onKeyDown` pattern used for sidebar nav (rather than native `<button>`) works correctly in practice, not just by reading the source. Mobile viewport (390×844) confirmed to show a clear, deliberate "desktop only" message rather than a broken layout — matches the already-documented product decision from an earlier sprint.

## Phase 6: Documentation and closeout (2026-07-26)

`FIX_LOG.md`, `ISSUE_DATABASE.md`, `TODO_QUEUE.md`, `CHECKPOINT.md`, root `REGRESSION_REPORT.md` all updated. Full backend suite re-run clean: 1708 passed (up from 1705), 1 skipped, 0 regressions. **Nothing deployed this sprint** — the audit-commit fix, like the prior sprint's viewer-insights work, exists only in the local working tree pending an explicit deploy request.
