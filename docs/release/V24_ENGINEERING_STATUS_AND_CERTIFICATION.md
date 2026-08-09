# TraceLink (SecureDoc) — V24.0 Final Truth, Cleanup & Release Certification

**This is the authoritative certification for the V24.0 sprint** ("Final Truth, Cleanup & Release Certification"). It builds on, and does not contradict, `docs/release/FINAL_RELEASE_CERTIFICATION.md` (V21.0) and `docs/release/V22_RESIDUAL_RISK_CERTIFICATION.md` (V22.0) — their product/UI/Viewer/architecture/security findings are unchanged and not re-litigated here except where V24.0 found new evidence. This document covers what V24.0 reconciled, found, fixed, or left open, and gives the release-readiness verdict this mandate requires.

Evidence types follow this repository's established convention: **[BROWSER VERIFIED]**, **[SOURCE VERIFIED]**, **[TEST VERIFIED]**, **[API VERIFIED]**, **[ENGINEERING INFERENCE]**, **[INSUFFICIENT EVIDENCE]**. Every claim below is tagged.

## 1. Baseline

V24.0 started from commit `2051314` (V23.0's baseline) and, over the course of this sprint, produced commits through `94b35c1` on branch `main`. **[SOURCE VERIFIED]** via `git log`. Working tree is clean at every commit boundary (confirmed via `git status --short` before each commit). Not pushed to `origin/main` this sprint — Railway's auto-deploy-on-push means none of V24.0's work (including ENG-045's Feedback-nav fix from V23.0, and ENG-046's lint fixes from this sprint) has reached the live production instance yet. No destructive action was taken against real user/customer data at any point.

## 2. Step 1 — Reconciliation: a real pre-existing tracking bug, found and fixed

Cross-checked every open/closed claim in `CHECKPOINT.md`/`PROGRESS.md` against `ENGINEERING_BACKLOG.md`'s own per-item detail entries, one item at a time across all 45 items that existed at sprint start — not trusting the prior session's own summary. **[SOURCE VERIFIED].**

Found: **ENG-037's detail entry has read "Closed — documented decision, regression tripwire added" since 2026-08-05 (V22.0)**, but its summary-table row and every rollup table in `CHECKPOINT.md`/`PROGRESS.md` kept it labeled "Open (low urgency, needs care)" — a narrative/table drift traced back to V22.0's own closing summary (which never updated the machine-readable row to match its own correct prose), that survived unnoticed through V23.0. `PROGRESS.md` had even acquired a footnote rationalizing the contradiction as a deliberate style choice rather than resolving it.

Fixed: corrected the summary-table row, replaced `CHECKPOINT.md`'s stale dual-table section (an old 44-item table left sitting next to a newer, correct V23.0 prose note — itself a fresh instance of the same class of bug) with one single reconciled table, and rewrote `PROGRESS.md`'s Dashboard/Burndown tables (which predated V23.0 entirely). Every count was recomputed programmatically from a full item-by-severity-by-status list, not by hand, and verified to close exactly at every stage of this sprint (see §7's final totals).

## 3. Step 2/3 — Re-evaluation of ENG-033/034/038/044/AUTH-006: no change

Re-verified all five against **current source**, not memory. **[SOURCE VERIFIED]** for each:

- **ENG-033** (no profile screen): `find frontend/src -iname "*profile*"` still empty. Classification unchanged: **D. PRODUCT DECISION REQUIRED.**
- **ENG-034** (no CD job): `.github/workflows/ci.yml` line 182 still `push: false`. Classification unchanged: **E. OPERATIONS/INFRASTRUCTURE DECISION REQUIRED.**
- **ENG-038** (TOCTOU race): `ensure_not_last_owner()` still has no `FOR UPDATE` lock. No new reproduction attempt made (would be a 3rd; nothing in the surrounding code changed since V22.0's 2 clean non-reproducing trials). Classification unchanged: **C. ARCHITECTURAL RISK, not fixed, evidence-backed low-risk inference stands.**
- **ENG-044** (Celery metrics cross-process gap): `metrics.py`'s own inline comment still documents the exact gap; zero `MultiProcessCollector` implementation matches repo-wide. Classification unchanged: **E. OPERATIONS/INFRASTRUCTURE DECISION REQUIRED.**
- **AUTH-006/ENG-026** (token in `localStorage`): confirmed still true (`frontend/api.js` lines 29/34/166); CSP mitigation confirmed still in place (§6 below). Classification unchanged: **C. ARCHITECTURAL RISK, deferred with an existing migration plan.**

No speculative fix was implemented for any of these, per the mandate's explicit prohibition on inventing fixes for decision-required items.

## 4. Step 4 — Repository re-sweep: two new items found

Grepped backend/frontend for TODO/FIXME/debugger/console.log/print(/unused imports, and checked CI configuration and documentation currency. **[SOURCE VERIFIED] + [TOOL-EXECUTION VERIFIED].**

**ENG-046 (Low-Medium, partially fixed)**: `.github/workflows/ci.yml`'s `ruff check backend/app backend/tests` has no project-level config and an unpinned `pip install ruff`. Reproducing it with the currently-available `ruff==0.16.0` gives 1361 errors under its zero-config default, or 229 even under ruff's own conservative baseline (`E4,E7,E9,F`) — meaning several prior sprints' "ruff clean" claims were true only against narrower ad hoc checks, not this literal command. Individually reviewed and fixed all 23 `backend/app/` hits (7 confirmed false positives — 6 SQLAlchemy string-forward-refs, 1 legitimate closure — suppressed with specific `# noqa` comments; 14 accidental import-ordering fixes, circular-import-safety verified first; 2 genuine style nits). Added `backend/ruff.toml` pinning the ruleset. `backend/app` is now genuinely clean. `backend/tests`' 206 remaining violations are real, pre-existing, zero-runtime-impact debt — explicitly quantified and left open rather than blind-`--fix`'d across many files without review, matching this project's ENG-013 precedent.

**ENG-047 (Low, closed)**: `CHANGELOG.md` stopped being updated after Sprint V10.0 — 14 sprints of subsequent history were never added there. Added an honest, dated pointer to the actually-current trackers (`ENGINEERING_BACKLOG.md`/`PROGRESS.md`/`CHECKPOINT.md`) rather than attempting to reconstruct 14 sprints of entries from summary documents, which risks fabricating specifics the zero-fabrication rule weighs against.

## 5. Step 5/6/7 — Reading Intelligence re-certification: ENG-048, a genuine unresolved High-severity defect

This is V24.0's most significant finding and **the one item this sprint cannot close, fix, or explain away.**

**[BROWSER VERIFIED]**, reproduced 5+ times against the live Railway app via Playwright, each attempt specifically designed to rule out a different alternative explanation:

- The stopwatch itself is correct when uninterrupted: counts up linearly 0s→5s over ~5 real seconds.
- Dispatching a genuine `window.dispatchEvent(new Event('blur'))` (the exact event `useReadingAnalytics.js`'s pause handler listens for) causes the displayed active-time counter and its `aria-label` to drop to **`"Waiting…" / "not started, timer paused"`** one second later — not frozen at its prior value, as pausing should produce.
- **Ruled out component remount**: tagged the actual DOM node with a JS marker property before blur; the same node (same identity, marker intact) was confirmed present 2 seconds later with reset text — proving this is a state-logic bug, not a remount side effect that would trivially explain a reset via fresh `useRef` initialization.
- **Ruled out network/session interference**: zero requests fired in the 2 seconds after blur; zero console or page errors throughout every trial.
- **Ruled out timing coincidence with the 5-second flush interval and Playwright-interaction-event noise**: reproduced with blur dispatched away from the flush boundary, using only `page.evaluate` reads with no locator/input calls that could synthesize interaction events.
- On a paired `focus` dispatch, the counter restarts from `"0s"` rather than resuming from its pre-pause value — confirmed both via timed sampling and before/after screenshots.
- The separate, legitimate "Focus window to resume" DRM content-blur overlay (`useViewerSession.js`'s `blurred` state — a CSS filter, working correctly) is a different mechanism and is explicitly not what this finding is about.

**Root cause**: not pinned, honestly reported as such. Read `useReadingAnalytics.js` in full (511 lines) — `_pause()`, `_accumulate()`, and the display `setInterval`'s `liveActive` computation all read correctly on paper; no line resets `totalActiveMs` after initialization. An attempt to intercept `window.SecureDocAPI.batchReadingEvents` (which reads the same ref value independent of the display layer) to observe it directly was inconclusive — no flush fired within the observation window. Per this project's own established discipline against fixing subtle state/timing bugs on intuition (the same standard V22.0 applied to ENG-037/038), **no fix was attempted**. This needs a live DevTools breakpoint session, which browser automation alone cannot provide.

**Impact**: every reader who alt-tabs or switches windows during a session sees their reading-time counter incorrectly reset — directly undermining trust in the product's flagship feature. Whether the *persisted* backend value is also affected wasn't conclusively determined.

Filed as **ENG-048, High severity, Open** — the top-priority item for the next engineering session.

Beyond this, the rest of the Reading Intelligence and general-screen re-certification found no new defects: Access Control link toggles, Organizations role/settings, and 8 other dashboard screens were already thoroughly Browser Verified in V23.0 and are not re-litigated here.

## 6. Step 8/9 — Bounded security and scalability review: no new findings

**[API VERIFIED]**: live HTTP header check against the deployed app (`curl -sD -`) confirms every security header documented in AUTH-006's re-evaluation is genuinely present in production right now: hash-based CSP (`default-src 'none'`, exact SHA-384 script hashes, no `unsafe-inline`/`unsafe-eval`), HSTS with `preload`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Cross-Origin-Opener-Policy: same-origin`, `X-Permitted-Cross-Domain-Policies: none`.

**[SOURCE VERIFIED]**: webhook delivery uses genuine HMAC-SHA256 payload signing (`X-SecureDoc-Signature`), not a stub. Webhook URL registration is protected by a real SSRF guard (`validate_ssrf_url`) blocking loopback/link-local/reserved/configured-blocked IP ranges, failing closed on unparseable input. Rate limiting is still configured across viewer endpoints (20–120/minute by sensitivity). Connection pooling has `pool_pre_ping=True` and tunable `pool_size`/`max_overflow` — matches ENG-011's existing scale-when-needed deferral, nothing new.

One minor observation investigated and **deliberately not filed** as a defect: webhook URL validation doesn't pass `allow_http=False`, so `http://` endpoints are technically permitted in production. Judged a defensible design tradeoff (common for webhook systems to support local/test receivers) rather than a clear defect, per the mandate's explicit instruction against manufacturing marginal findings.

**Scalability**: source analysis only, per the mandate's prohibition on generating load against production. No new engineering-actionable findings — existing deferrals (ENG-005 pagination, ENG-011/012 connection pooling/cache invalidation) remain correctly deferred with no new triggering condition.

## 7. Reconciled backlog state — final numbers for this sprint

**[SOURCE VERIFIED]**, recomputed programmatically from `ENGINEERING_BACKLOG.md`'s full 48-row table, not estimated:

| Status | Count | IDs |
|---|---|---|
| Closed | 31 | ENG-001–004,006–010,013,014,017–021,024,029–032,035–037,039–043,045,047 |
| Deferred (reasoned) | 7 | ENG-005,011,012,016,022,023,026 |
| Reviewed, not implemented | 3 | ENG-025,027,028 |
| Justified, not changed | 1 | ENG-015 |
| **Open** | **6** | **ENG-033, ENG-034, ENG-038, ENG-044, ENG-046, ENG-048** |
| **Total** | **48** | — |

`31 + 7 + 3 + 1 + 6 = 48`. Every closed item has verification evidence on file. Every open item is one of: a documented product/ops decision blocker (ENG-033, ENG-034, ENG-044), an evidence-downgraded low-risk architectural inference (ENG-038), a quantified zero-runtime-impact cleanup remainder (ENG-046), or **one confirmed-real, unresolved, High-severity defect (ENG-048)**.

## 8. Step 14 — Final validation evidence

| Check | Result | Evidence class |
|---|---|---|
| Backend suite (`pytest tests/`) | **1751 passed, 1 skipped, 0 failed** | **[TEST VERIFIED]** — host-run, final commit |
| Frontend suite (`vitest`) | **13/13 passed** | **[TEST VERIFIED]** |
| Frontend build (`esbuild`) | **succeeded, 309.2kb** (unchanged from V22.0/V23.0) | **[TEST VERIFIED]** |
| Frontend lint (`eslint`) | **clean** | **[TEST VERIFIED]** |
| Backend lint (`ruff check backend/app`, newly pinned) | **clean — "All checks passed!"** | **[TEST VERIFIED]** |
| Backend lint (`ruff check backend/app backend/tests`, the literal CI command) | **206 errors remain** — `backend/tests` debt, quantified as ENG-046, not fixed this pass | **[TEST VERIFIED]**, honestly reported as failing |
| Migrations (`alembic`) | **single head (`027`); live DB `alembic current` = `027`** | **[TEST VERIFIED]** against the live local Docker Postgres |
| `git status` | **clean** (except this sprint's own commits) | **[SOURCE VERIFIED]** |
| Security headers (live) | **all present and correct** | **[API VERIFIED]** |
| Reading Intelligence pause/resume | **confirmed broken, then root-caused and fixed same sprint (ENG-048) — see §11** | **[BROWSER VERIFIED]** + **[INSTRUMENTATION VERIFIED]** |
| Full browser smoke of Access Control/Organizations/8 other screens | Covered in V23.0, not re-run this sprint (no new evidence to gather — those screens weren't touched by V24.0's code changes) | **[BROWSER VERIFIED]**, carried forward from V23.0 |

## 9. Release verdict (superseded by §11 — see below)

~~Per the mandate's own acceptance criteria, this sprint does not declare "release ready" or "zero defects." ... Verdict: NOT YET RELEASE READY — one confirmed, unresolved, High-severity product defect (ENG-048) blocks a clean release declaration.~~

**This verdict is superseded — see §11.** ENG-048 was closed in a same-sprint follow-up pass immediately after this document was first written. Preserved above (struck through) as an honest record of the state at the time this certification was first drafted, rather than silently rewritten.

## 10. Known limitations carried forward (not re-derived — see `docs/release/KNOWN_LIMITATIONS.md` for the full V21.0 list, unchanged)

In addition to that file's existing content: **ENG-046** — `backend/tests` has 206 lint violations under the now-pinned ruleset, zero runtime impact; **ENG-044** — Celery worker metrics invisible on `/metrics` pending a multiprocess-registry ops decision; **AUTH-006** — session token in `localStorage`, mitigated by a hash-based CSP, full migration plan on file pending approval. (ENG-048 is no longer a known limitation — see §11.)

## 11. ENG-048 closed — updated verdict (2026-08-09, same-sprint follow-up)

Per explicit follow-up instruction, ENG-048 was picked up as a dedicated fix task immediately after this certification was first drafted. **Root cause proven via runtime instrumentation** (temporary `console.log` tracing at every state transition in `useReadingAnalytics.js`, on the local Docker stack — not a live DevTools session, which turned out unnecessary): a `useEffect` dependency-array race. The "handle page changes" effect guarded on a non-reactive ref read (`state.current.sessionStarted`) with a dependency array that didn't include `isDocumentReady`/`session`; on mount the effect ran once (as a no-op, since the session wasn't ready yet) and then never re-fired once the session actually started, because none of *its own* dependencies had changed. `s.currentPage` therefore stayed `null` for the entire session, `_accumulate()`'s guard made it a permanent no-op, and — a discovery beyond what was known when ENG-048 was filed — no page was ever marked entered, so nothing was ever flushed to the backend either for a session that never left page 1.

**Fix**: 3-line functional change to the effect's guard/dependency array (`frontend/src/hooks/useReadingAnalytics.js`), checking `session`/`isDocumentReady` instead of the ref.

**Verification — [TEST VERIFIED] + [BROWSER VERIFIED] + [INSTRUMENTATION VERIFIED]**:
- 2 new regression tests, both proven to fail against the pre-fix code via `git stash` (not tautological).
- Full backend suite unaffected: 1751 passed/1 skipped/0 failed.
- Full frontend suite: 15/15 passed (up from 13).
- `eslint` clean, build succeeded (309.2kb, unchanged), migration head `027` confirmed live.
- 9 of the 10 mandated browser tests passed directly against the local Docker stack with real timing (blur-freeze, blur-then-additive-resume, 5× repeated blur/focus, simulated tab-hide via `visibilitychange` override, page navigation, refresh + re-open, 30s idle threshold, uploader-facing View History/Analytics, predicted-remaining-time display). The 10th (genuine multi-tab switching) was indeterminate — a documented headless-Chromium limitation (a second real page in the same browser context doesn't flip `document.hidden` on the original tab), not an app defect, and directly covered by the `visibilitychange`-override test exercising the identical underlying mechanism.

**Updated verdict**: every acceptance-criteria item in §9 that was previously a "✗" is now resolved. Zero verified Critical or unresolved High defects. Zero contradictory statuses. Reconciled backlog: 48 items, **32 closed**, 7 deferred, 3 reviewed-not-implemented, 1 justified, **5 open** — all five blocked on a named external input or quantified zero-runtime-impact cleanup debt, none unilaterally engineering-actionable.

**RELEASE STATUS: READY WITH DOCUMENTED LIMITATIONS** — matching the same verdict class as V22.0's certification. The remaining 5 open items (ENG-033, ENG-034, ENG-038, ENG-044, ENG-046) are exactly the kind of decision-blocked or low-risk-quantified items that verdict class is meant to describe; none represent an unresolved functional or security defect.
