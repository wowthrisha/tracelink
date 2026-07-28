# Issue Database — V10.0 Autonomous Product Excellence

Consolidated from V6.0/V7.0 governance sprint findings (all evidence-verified against source, not bundle-derived) plus fresh review this session. Each issue: ID, severity, source, status. Append new findings below; update status in place as issues are resolved (this file tracks current truth per-issue; historical narrative lives in `ACTION_LOG.md`).

**Reconciliation note (V16.0, 2026-07-28)**: this file had drifted stale relative to `TODO_QUEUE.md` — several items below were marked "Open" here despite `TODO_QUEUE.md`'s own "Completed this session" list showing them done back in V10.0. Source-verified a sample directly against current code (H-1's `@keyframes shake` exists in `SecureDoc.html:156`; H-7's `download_document` PDF write is wrapped in `run_in_executor` with an explanatory comment; M-1's both `<Toggle>` call sites in `AccessScreen.jsx` now pass `label=`) — all 3/3 confirmed done, matching `TODO_QUEUE.md` and contradicting this file's stale "Open" markers. Statuses below updated to match. Genuinely-still-open items were merged into `ENGINEERING_BACKLOG.md` (single source of truth going forward) as ENG-022 through ENG-030.

Severity: **Critical** (breaks a workflow or is a security exposure) · **High** (real bug, wrong/misleading behavior) · **Medium** (consistency/accessibility gap) · **Low** (polish).

## Critical

| ID | Description | Source | Status |
|---|---|---|---|
| C-1 | ~~Webhook deliveries never registered with the Celery worker~~ | V6.0 | **Already fixed** (`celery_app.py` include list, regression test added) |

No other Critical-severity items are currently open — the one found (webhook task registration) was already fixed in V6.0.

## High

| ID | Description | Source | Status |
|---|---|---|---|
| H-1 | ~~`AccessGate.jsx` wrong-password shake animation references `@keyframes shake`, which is never defined anywhere~~ | V7.0 frontend-maturity research | **Fixed in V10.0, reconciled V16.0.** Source-verified: `@keyframes shake` is defined in `SecureDoc.html:156`, matching `AccessGate.jsx:41`'s `animation: shaking ? 'shake .4s' : undefined`. |
| H-2 | ~~Viewer toolbar tooltips advertise arrow-key page navigation that doesn't exist~~ | V7.0 frontend-maturity research | **False positive — corrected this session.** `useViewerLayout.js:70-96` registers a `window` keydown listener handling `ArrowRight`/`ArrowDown` → `goNext()` and `ArrowLeft`/`ArrowUp` → `goPrev()`, invoked from `ViewerScreen.jsx:79`. The V7.0 research agent's grep missed this hook file. Verified by direct code read, not re-implemented — doing so would have created a duplicate, conflicting listener. |
| H-3 | ~~7 hand-rolled modals bypass the shared `Modal` component~~ | V6.0/V7.0 | **Fixed in V10.0** (`TODO_QUEUE.md` item 3 — `ApiKeysScreen.jsx` ×2, `WebhooksScreen.jsx` ×3, `OrgsScreen.jsx` ×4 migrated). Reconciled V16.0. |
| H-4 | `annotations.py` org-member access-control gap | V6.0 | **Already fixed** |
| H-5 | `groups.py` missing `require_scope` enforcement | V6.0 (prior sprint) | **Already fixed** |
| H-6 | ~~Two security-sensitive config defaults (`ip_hash_salt`, `domain_verify_salt`) have no production-time enforcement, unlike HSTS~~ | V7.0 release-readiness research | **False positive — corrected this session.** `main.py:27-54` already enforces both at module import time: if `app_env == "production"` and either salt is at its placeholder default, startup raises `RuntimeError` with a combined message covering all production-readiness checks (Supabase URL, HTTPS, both salts). I initially (wrongly) added a second, redundant `model_validator` to `config.py` mirroring the HSTS pattern before finding this — reverted it once found, since it would have fired earlier than and duplicated `main.py`'s more complete check. The V7.0 research agent's search evidently covered `config.py` but missed `main.py`'s module-level enforcement block. |
| H-7 | ~~`viewer.py:download_document` synchronous PDF write blocks the event loop~~ | V7.0 backend-pattern research | **Fixed in V10.0, reconciled V16.0.** Source-verified: `_write_and_size` is wrapped in `run_in_executor` (`viewer.py:628`) with an explanatory comment confirming this was the deliberate fix ("writing a multi-page PDF to disk is CPU+disk bound and was previously blocking the event loop"). This is a *different* code path than `ENG-006`'s V15.0 storage-service audit — both are now confirmed clean. |
| H-8 | Backup automation (`docker-compose.yml` `backup` service) is gated behind an opt-in compose profile — not running by default | V7.0 release-readiness research | Open (documented as a deliberate deploy-config decision, see `ARCHITECTURE_DECISIONS.md` — not a defect, an infrastructure choice for the operator to make) |

## Medium

| ID | Description | Source | Status |
|---|---|---|---|
| M-1 | ~~Shared `Toggle` switch used twice with no `label` prop passed~~ | V6.0 | **Fixed in V10.0, reconciled V16.0.** Source-verified: both `<Toggle>` call sites in `AccessScreen.jsx` (lines 348, 1019) now pass `label={labelText}`. |
| M-2 | ~~6 of 12 screens have zero `aria-label` usage despite icon-only controls~~ | V6.0 | **Investigated this session, no actionable defect found.** Checked every interactive control on all 6 screens for genuinely icon-only (no visible text) buttons — found none; every control (e.g. "↻ Refresh", "↓ CSV", "↓ JSON") already has an accessible name via its visible text content, which satisfies WCAG without needing an `aria-label`. `AppShell.jsx` has zero interactive controls of its own (pure layout wrapper). The original "zero aria-label usage" count was a real, accurate raw metric, but doesn't correspond to a real accessibility gap on these 6 screens specifically — adding redundant `aria-label`s to already-labeled-by-text-content controls would be noise, not a fix. |
| M-3 | ~~No spacing-token scale exists in `tokens.js`~~ | V7.0 | **Fixed in V10.0** (additive spacing-token scale added). Reconciled V16.0. |
| M-4 | ~~6 routers have silent `except: pass` with no logger at all~~ | V7.0 | **Largely a false positive, corrected this session.** Individually inspected all 15 `except Exception: pass`-style sites across the 6 flagged routers. 11 of 15 wrap `log_audit_event()` calls — not actually silent, since `audit_service.py`'s `log_audit_event` already catches and logs every failure internally (confirmed in V7.0's own code-quality research). 2 more are benign fallback patterns (malformed-JSON-in-a-stored-field, invalid-UUID-in-a-batch-request) with sensible defaults, not worth logging. **2 sites were genuinely silent with zero observability and are fixed**: `links.py:_get_base_url_for_doc`'s custom-domain lookup (now logs a warning before falling back) and `webhooks.py`'s test-ping Celery dispatch failure (now logs an error — previously a broker-connectivity problem here would have been completely invisible). |
| M-5 | `viewer.py:get_page` blocking-I/O-adjacent side effects (session heartbeat + analytics commit) not obviously async-safe from the name | V6.0 | Documented, not a behavior bug — naming/clarity only |
| M-6 | `links.py`'s two DELETE endpoints return 200+body against 8 others returning 204/no-body | V7.0 | Open — merged into `ENGINEERING_BACKLOG.md` as **ENG-022** |
| M-7 | Only 4 of ~11 list endpoints paginate; where present, 4 different default/cap combinations | V7.0 | Open — same underlying issue as `ENGINEERING_BACKLOG.md` **ENG-005**; not duplicated as a new entry |
| M-8 | 14 endpoints across 7 routers validate via raw `body: dict` instead of typed Pydantic schemas | V7.0 | Open — merged into `ENGINEERING_BACKLOG.md` as **ENG-023** |
| M-9 | ~~Delete/revoke toast severity inconsistent~~ | V6.0 | **Fixed in V10.0 for the 2 real `AccessScreen.jsx` single-link toasts** (info→success). The bulk "Revoke All Access" toast's `error` severity was deliberately left unchanged — a documented, considered choice (higher-stakes action warrants stronger emphasis), not an inconsistency. Reconciled V16.0. |
| M-10 | Same "created at" concept renders 3 different ways across screens (`fmtDate`, raw `toLocaleString`, custom `fmtTime`) | V6.0 | Open — merged into `ENGINEERING_BACKLOG.md` as **ENG-024** |
| M-11 | Empty states range from icon+heading+CTA to bare text with no rule | V6.0 | Open — merged into `ENGINEERING_BACKLOG.md` as **ENG-025** |
| M-12 | The app's only responsive CSS breakpoint (640px) is unreachable dead code — `AppShell.jsx` gates at a stricter 768px first | V7.0 | Documented — matches `ARCHITECTURE_DECISIONS.md` AD-6, a deliberate non-fix pending a product decision on mobile/tablet support. Not re-litigated. |
| M-13 | `AccessScreen.jsx` (~900 lines, 3 unrelated feature domains) — large-component maintainability risk | V6.0 | Open — already tracked as `ENGINEERING_BACKLOG.md` **ENG-016** |
| M-14 | `AUTH-006`: session token in `localStorage`, real XSS-exposure vector | V4.0/Sprint7.0 | Deferred — full migration plan exists in `SECURITY_HARDENING_PLAN.md`; merged into `ENGINEERING_BACKLOG.md` as **ENG-026** (tracked, not silently dropped, still correctly deferred as an architecture migration rather than a partial patch) |

## Low

| ID | Description | Source | Status |
|---|---|---|---|
| L-1 | Modal-entrance-animation duration drifts (.15s/.18s/.22s/.25s) for the same semantic "content appears" event | V7.0 | Open — merged into `ENGINEERING_BACKLOG.md` as **ENG-027** |
| L-2 | Icon language mixes geometric Unicode and real emoji within one continuous viewer session | V7.0 | Open — cosmetic, low actionability without a design decision. Merged into `ENGINEERING_BACKLOG.md` as **ENG-028** |
| L-3 | `docs/architecture/ARCHITECTURE.md`/`OVERVIEW.md` contradict each other on watermark model and cache TTLs | V7.0 | Open — merged into `ENGINEERING_BACKLOG.md` as **ENG-029** |
| L-4 | Version numbering incoherent across the repo (4 disagreeing signals) | V7.0 | Open — needs a product/release decision on canonical version, not an engineering fix. Not merged into the backlog (no engineering action possible without that decision). |
| L-5 | `docs/release/` has 14 overlapping files, no canonical release doc | V6.0/V7.0 | Open — will be addressed as part of V16.0's repository-cleanliness pass (archiving historical reports), not a separate ENG item |
| L-6 | Button-variant usage for row-level delete/revoke triggers varies (`ghost`+red-text vs. `outline-danger`) | V6.0 | Open — merged into `ENGINEERING_BACKLOG.md` as **ENG-030** |

## Non-technical-user complexity findings (new this session, see `ACTION_LOG.md` for detail)

Tracked separately as this sprint's specific new research lens — populated as the per-screen review proceeds.

## V11.0 — Viewer Excellence (2026-07-25)

| ID | Severity | Description | Source | Status |
|---|---|---|---|---|
| INSIGHTS-PUBLIC-001 | High | Viewer toolbar's "Insights" button/modal rendered for public share-link viewers (no `publicToken` check), causing a 401 → forced page reload if clicked | V11.0 | **Fixed** — `ViewerScreen.jsx` gated to owner-preview only, `FIX_LOG.md` V11-1 |
| VIEWER-INSIGHTS-001 | Feature (new, not a bug) | No viewer-facing panel existed for reading difficulty / this-page average / pace vs. average reader — mission explicitly asked for this | V11.0 | **Built** — extended existing `/api/reading/session/{id}` endpoint + `ReadingStatusBar.jsx`, `FIX_LOG.md` V11-2/V11-3 |
| TOGGLE-READING-INSIGHTS-001 | Feature (new, not a bug) | No permission existed to let uploaders control whether item above is shown to viewers | V11.0 | **Built** — `show_reading_insights` added to the existing `ShareLink.permissions` pattern, `FIX_LOG.md` V11-2/V11-3 |
| ERRBOUNDARY-RAW-001 | Medium | `ViewerErrorBoundary.jsx` rendered raw `String(error)` to end users instead of a sanitized message | V11.0 | **Fixed** — friendly message + correlation ID, real error stays in console, `FIX_LOG.md` V11-4 |

**Scoped out this session** (see `ARCHITECTURE_DECISIONS.md` AD-7 through AD-11 for full reasoning): a generic feature-toggle framework covering ~12 independent toggles, device/browser/country/timezone capture, reading-replay/timeline UI, reading-speed trend charts, and a blanket pixel-level UI review. Each is a genuine multi-day feature build or a product/legal decision (unhashed-data retention), not something a shallow implementation this session could responsibly ship.

## V12.0 — Final Production Certification (2026-07-26)

| ID | Severity | Description | Source | Status |
|---|---|---|---|---|
| AUDIT-LINK-COMMIT-001 | High (security-relevant) | `link.created`/`link.updated`/`link.revoked` audit events were silently never persisted — `log_audit_event()` flushes but never commits, and 3 of 4 call sites in `links.py` never issued a trailing commit | V12.0 | **Fixed** — `links.py` + `audit.py`, `FIX_LOG.md` V12-1, 3 new regression tests (proven to catch the bug via revert-and-retest) |
| WATERMARK-OWNER-ANON-001 | Low (cosmetic) | Document owner's own preview watermark reads "anonymous" instead of their real email | V12.0 | Noted, not fixed — touches the same owner-preview-link machinery as READ-OWNER-001, deserves its own scoped look. Merged into `ENGINEERING_BACKLOG.md` as **ENG-031** |

**Re-verified live this sprint (all confirmed fixed in production)**: WATERMARK-001, READ-OWNER-001, BILLING-PLAN-BADGE-001 (all V10.0 — `e7ddf47` was pushed and auto-deployed by Railway during this session, though not by this session's own actions).

**Verified as correct, not defects, this sprint**: Edit Link permission propagation (live, end-to-end), Reading Intelligence pause/resume-on-blur (plus an undocumented content-blur security behavior), Reading Intelligence uploader-side data (real, not fabricated), keyboard-only sidebar navigation (proper ARIA role/keyboard handling), mobile block (intentional, matches `ARCHITECTURE_DECISIONS.md` AD-6).

**Explicitly out of scope this sprint** (not a defect list — see `FIX_LOG.md`/`REGRESSION_REPORT.md` V12.0 sections for reasoning): full WCAG 2.2 AA audit, full performance profiling (N+1 query audit, render-count analysis), full dead-code sweep, offline/slow-network simulation. Each is a genuine multi-day audit in its own right; a shallow pass would produce unverified claims rather than real evidence.
