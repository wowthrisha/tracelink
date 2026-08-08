# V23.0 Release Candidate — Baseline

**Purpose**: recorded state of the repository at the start of V23.0, before any V23.0 change. Every downstream V23.0 document (`V23_OPEN_ITEMS_DISPOSITION.md`, `V23_RELEASE_CANDIDATE_CERTIFICATION.md`, etc.) is measured against this baseline. All fields below are **[SOURCE VERIFIED]** — read directly from the repository and its tracking documents, not recalled from conversation memory.

## Repository state

- **HEAD**: `b3ab2d952ba0fd215d92ab33fd339b9d70867883` (`b3ab2d9`) — `git rev-parse HEAD`
- **Branch**: `main`
- **Working tree**: clean (`git status --short` → empty output)
- **Not pushed** to `origin/main` — confirmed by this session's standing practice (Railway auto-deploys on push; nothing has been pushed).

## Tracking documents inspected (per Step 1's explicit list)

| Document | Location | Present? |
|---|---|---|
| `ENGINEERING_BACKLOG.md` | repo root | Yes |
| `FIX_LOG.md` | `docs/engineering/` | Yes |
| `ACTION_LOG.md` | `docs/engineering/` | Yes |
| `PROGRESS.md` | repo root | Yes |
| `CHECKPOINT.md` | repo root | Yes |
| `REGRESSION_REPORT.md` | repo root | Yes |
| `RELEASE_BLOCKERS.md` | — | **Not present at any live path.** Two historical copies exist under `archive/sprint7-18/root-reports/RELEASE_BLOCKERS.md` and `archive/sprint5-6/root-reports/RELEASE_BLOCKERS.md` — both point-in-time snapshots from earlier sprints, superseded by `ENGINEERING_BACKLOG.md` and the V21.0/V22.0 certification documents. Not read as current state; noted here rather than silently assumed to exist. |
| V22.0 release/residual-risk documents | `docs/release/V22_RESIDUAL_RISK_CERTIFICATION.md` | Yes |

## Backlog state (from `ENGINEERING_BACKLOG.md`'s summary table, re-counted directly, not recalled)

**44 tracked items total: 27 closed, 7 deferred (re-confirmed reasoning), 3 reviewed-not-implemented, 1 justified-not-changed, 6 open** (the summary table's per-item status column literally marks 6 rows "Open," but one of those six — ENG-037 — is functionally closed this sprint via a permanent regression tripwire, not an unresolved defect; see below. The V22.0 certification's own §1/§10 and this session's `PROGRESS.md` both count it as 5 substantively-open items, matching the count given in this prompt).

### The exact five open items (verified directly against the backlog table, not assumed from memory)

| ID | Title | Severity | Current classification |
|---|---|---|---|
| ENG-019 | Dashboard modals/toggles not fully re-exercised | Enhancement | Open — 2 of several toggles (API key `is_active`, webhook `is_active`) confirmed round-trip correctly via direct API PATCH+re-fetch; the remainder (Access Control link toggles, Organizations role/settings) share the identical code pattern but have not been independently round-tripped |
| ENG-033 | PROF-001: no profile/account-settings screen exists | High | Open / DECISION REQUIRED — full decision record in `docs/governance/ENG-033_DECISION.md` |
| ENG-034 | No CD/deploy job in CI pipeline | Medium | Open / DECISION REQUIRED — full decision record in `docs/governance/ENG-034_DECISION.md` |
| ENG-038 | `ensure_not_last_owner()` TOCTOU race (pre-existing) | Low | Open — reclassified LOW-RISK INFERENCE in V22.0 after 2 clean live concurrent-request trials against the real Docker stack found no reproducible race |
| ENG-044 | Celery worker metrics invisible on `/metrics` (per-process registry) | Low | Open — needs an ops/infra decision on a `PROMETHEUS_MULTIPROC_DIR` multiprocess-registry deployment change |

### Sixth table row marked "Open" — not counted among the five, with reason

| ID | Title | Table label | Why not counted as substantively open |
|---|---|---|---|
| ENG-037 | `is_link_active()` not actually used by enforcement path | "Open (low urgency, needs care)" | Closed in V22.0 via a deliberate decision **not** to merge the code (would add complexity for a currently-theoretical risk) plus a 6-test permanent regression tripwire (`backend/tests/regression/test_eng037_link_active_consistency.py`) that fails immediately if the two implementations ever disagree. The label reflects the tripwire's intentionally-permanent nature (it stays in the suite forever, unlike a normal closed item), not an unresolved defect. |

## Deferred / decision-required items (for completeness, not re-triaged this step)

- **Deferred with re-confirmed reasoning (7)**: ENG-005, ENG-011, ENG-012, ENG-016, ENG-022, ENG-023, ENG-026 (AUTH-006).
- **Reviewed, not implemented (3)**: ENG-025, ENG-027, ENG-028 — cosmetic, need design input.
- **Justified, not changed (1)**: ENG-015.
- **AUTH-006 / ENG-026** specifically: severity Medium (revised down from Medium-High in V22.0 after a CSP-mitigation finding), full re-evaluation in `docs/security/SECURITY_HARDENING_PLAN.md` §9, no approved migration decision exists in the repository — remains an explicitly documented, unimplemented architectural risk. Not re-litigated in V23.0 unless new evidence emerges.

## Current test baseline

Re-run at V23.0 start, host-side, matching this repository's established convention:

```
cd backend && python3 -m pytest tests/unit tests/integration tests/regression -q
```

- **Backend**: 1751 passed, 1 skipped, 0 failed (unchanged from V22.0's final certification — no code has changed between `b3ab2d9` and this baseline check).
- **Frontend** (`npm test` → vitest): 13/13 passed (unchanged).

## Current build baseline

- Frontend production build (`npm run build`, esbuild): succeeds, `dist/app.bundle.js` = 309.2kb (unchanged from V22.0's final state).

## Current migration state

- Alembic head (source, `alembic heads`): `027` — single head, no branch divergence.
- Live local Docker Postgres (`alembic current` inside the `api` container): `027` — matches head.

## Current known risks (carried forward from V22.0, not re-derived)

1. **AUTH-006/ENG-026** — session token in `localStorage`; XSS-theft vector, mitigated by a confirmed hash-based CSP; migration plan documented, unimplemented, no approved decision.
2. **ENG-044** — Celery worker Prometheus metrics invisible on `/metrics` due to per-process registry isolation; needs ops/infra input.
3. **ENG-038** — `ensure_not_last_owner()` has no `FOR UPDATE` lock; theoretically a TOCTOU race, empirically not reproduced in 2 real concurrent-request trials.
4. **ENG-033** — no in-app profile/account-settings screen; a real, high-severity usability gap, blocked on product/design input.
5. **ENG-034** — no automated CD/deploy job in `ci.yml`; Railway's auto-deploy-from-`origin/main` is the actual (undocumented-as-a-repeatable-process) live deployment mechanism.
6. **Correction to a claim repeated in every prior sprint (V17.0 through V22.0)**: those sprints stated "no browser-automation tool is available in this environment," based on `ToolSearch` finding no Claude-Code-native browser tool. That check never looked for a host-level, directly-invocable browser. This step re-checked and found one: `playwright` (Python, v1.58.0) is installed in the host's `miniconda3` environment with Chromium already downloaded (`~/Library/Caches/ms-playwright/chromium-1208`), and was confirmed working this step — `page.goto("http://localhost:8000/app")` against the real local Docker stack renders the actual login screen correctly (screenshot captured, real UI, not a blank page). **This means V23.0 can perform genuine Browser Verified evidence for Steps 5-7**, which no prior sprint in this session could do. Every UI claim in every V22.0-and-earlier document that was classified "Source Verified" or "Not Verified — no browser tool available" was accurate *as stated for its own sprint* (the tool genuinely wasn't found by the method used then) — this is a capability newly discovered this step, not a retraction of those documents' honesty. Flagged here explicitly rather than silently used without explanation.

## What V23.0 has not yet done (as of this baseline)

Nothing. This document is written before any V23.0 investigation, fix, or verification step — it is the starting line, not a progress report.
