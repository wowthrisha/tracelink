# Code Quality Certification — TraceLink / SecureDoc

**Method**: AST-verified static analysis (`ruff`, installed this sprint specifically to replace manual grep-guessing for dead-code detection) across the full backend, plus a targeted grep sweep for debug artifacts, TODO/FIXME markers, and orphaned frontend files. Full detail and per-file reasoning is in `docs/engineering/FIX_LOG.md` ("Sprint V13.0 — Repository Cleanup"); this document summarizes and scores that work alongside a fresh review of test coverage and known duplication.

Every finding is classified as exactly one of **Browser-verified / Source-code verified / Engineering inference / Not enough evidence**.

---

## 1. Dead code — imports and variables

**Source-code verified**: `ruff check --select F401,F811,F841` found 26 unused imports and 6 unused local variables across the backend. 23 of the 26 imports were auto-removed with zero regression risk (unused imports cannot affect runtime behavior). 3 were restored with an explanatory `# noqa: F401` comment after the auto-fix broke 5 test files' imports — `clear_page_cache`/`clear_thumb_cache`/`clear_metadata_caches` in `routers/viewer.py` are re-exported for tests that patch `app.routers.viewer.*`, a cross-file usage pattern a single-file static analyzer cannot see. This was caught by running the full test suite immediately after the auto-fix, not by trusting the tool blindly.

Each of the 6 unused-variable findings was investigated individually rather than batch-removed, per the explicit instruction to prove code unused before deleting it. Two were not cosmetic:
- `services/toc/cache.py`: tracing the unused variable led to discovering the entire sync `get_cached_toc()` function has zero callers anywhere in the repo (confirmed via full-repo grep) — the whole dead function was removed, not just the variable.
- `services/analytics_service.py`: tracing the unused variable led to an unnecessary database query that fed it — removed the variable, the query, and its else-branch default, a genuine query-count reduction.

One case (`reading_analytics_service.py:1073`) required keeping a function call for its side effect (lazily creating a `DocumentComplexity` row) while dropping only the unused assignment — cleanup that stops at the line, not the statement, when the statement has a real effect.

**Verification**: `ruff check --select F401,F811,F841 app/` → 0 remaining findings. Full backend suite (`pytest tests/unit tests/integration tests/regression`) → **1708 passed, 1 skipped, 0 failed**, identical to the pre-cleanup baseline — confirming zero regressions from every cleanup change.

## 2. Debug artifacts and TODO markers

**Source-code verified**: grep sweep for `print(`, `import pdb`/`breakpoint()`, `console.log`/`debugger;`, and `TODO`/`FIXME` across `backend/app/` and `frontend/src/` (excluding tests/pycache) — **zero matches in every category**. The codebase entered this sprint already clean of debug artifacts, which is a genuinely strong signal (most codebases of this size accumulate at least a few stray `console.log`s).

## 3. Orphaned files and unused CSS

**Source-code verified**: every file under `frontend/src/components/` and `frontend/src/hooks/` checked for being referenced by name elsewhere in `src/` — zero orphaned files found. Every CSS class in `SecureDoc.html`'s embedded stylesheet checked against actual `className` usage — zero newly-found unused classes (the one known piece of dead CSS, an unreachable 640px breakpoint, is pre-existing and deliberately left per `ARCHITECTURE_DECISIONS.md` AD-6, not re-litigated here).

## 4. Code duplication

**Source-code verified**: the one significant duplication on record — a 7-key `permissions` dict duplicated across `AccessScreen.jsx` and `viewer_session_service.py` — was identified in V11.0 and deliberately extended rather than consolidated at that time, with recorded rationale (`ARCHITECTURE_DECISIONS.md` AD-7). Not revisited this sprint since it's a known, deliberate tradeoff rather than newly-discovered drift.

**Not enough evidence**: no fresh, exhaustive duplication scan (e.g. `jscpd` or equivalent token-based duplicate-detection tool) was run this sprint — the above is what's already on record from prior sprints, not a new sweep.

## 5. Naming, module boundaries, oversized components

**Source-code verified**: `AccessScreen.jsx` (~900 lines) remains oversized by conventional component-size norms — tracked as `ISSUE_DATABASE.md` M-13, a deliberate refactor deferral, not revisited this sprint. No other file was flagged for size during this pass.

**Not enough evidence**: no fresh line-count/complexity audit of the full frontend or backend was performed beyond confirming M-13's continued existence — a comprehensive module-boundary review was out of scope for this sprint's time budget.

## 6. What this cleanup explicitly did not cover

Per `docs/engineering/FIX_LOG.md`'s own disclosure, stated plainly rather than silently omitted:
- **Frontend unused-import detection** — no ESLint (`no-unused-vars`) or equivalent AST tool was installed/run this sprint. The orphaned-*file* check performed is not equivalent to an unused-*import-within-a-used-file* check. This is a real, acknowledged gap.
- **Duplicate business logic / duplicate validation / duplicate permission checks** — beyond the one already-known instance (§4), no new systematic duplication sweep was performed.

## 7. Test coverage signal

**Source-code verified**: 1708 tests passing, 1 skipped, across `tests/unit`, `tests/integration`, `tests/regression` — this is a substantial existing suite (not newly written this sprint) that provided real regression protection during the cleanup work (it caught the ruff auto-fix breakage immediately). **Not enough evidence**: this document does not independently verify test *coverage percentage* or identify untested code paths — only that the existing suite passes and is large enough to have caught a real regression during this sprint's work.

---

## Score: 8/10

**Why not higher**: the frontend has no equivalent of `ruff` running against it — unused-import detection there is an acknowledged, real gap, not a false claim of completeness. No fresh duplication-detection tool was run beyond confirming what was already on record. These are stated gaps, not silently-covered ones, but they do cap the score below what a codebase with matched frontend+backend tooling coverage would earn.

**Why not lower**: the backend cleanup was rigorous — AST-verified, individually investigated (not batch-deleted), caught its own tool's mistake via the test suite before it shipped, and left the repo at 0 remaining static-analysis findings with zero test regressions. The codebase was already free of debug artifacts and TODO markers going in, which is itself a quality signal about ongoing discipline, not just this sprint's work. Known debt (M-13, AD-6, AD-7) is tracked with recorded rationale rather than accumulated silently.
