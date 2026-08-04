# V22.0 Baseline — Residual Risk Closure Sprint

Captured before any V22.0 modification. All figures below are the actual observed values from re-running each check fresh, not carried forward from V21.0's own report.

| Check | Result | Evidence |
|---|---|---|
| Working tree | Clean | `git status` → "nothing to commit, working tree clean" |
| Branch | `main` | `git branch --show-current` |
| Commit | `1c31090` — matches the expected V21.0 baseline exactly | `git log --oneline -1` |
| Backend tests | **1706 passed, 1 skipped, 0 failed** | `PYTHONPATH=. python -m pytest tests/ -q` |
| Frontend tests | **13/13 passed** | `npm test` |
| Frontend lint | **exit 0** | `npm run lint` |
| Frontend build | **succeeded, 309.1kb** | `npm run build` |
| Migration head | **027, already applied** | Live query against local Docker Postgres: `SELECT version_num FROM alembic_version` → `027` |
| Docker `api` health | **`{"status":"ok",...}` all subsystems ok** | `curl http://localhost:8000/health` after `docker compose up --build -d api migrate` |
| Root directory contents | 9 canonical `.md` files (`README`, `CHANGELOG`, `CHECKPOINT`, `CODE_OF_CONDUCT`, `CONTRIBUTING`, `ENGINEERING_BACKLOG`, `PROGRESS`, `REGRESSION_REPORT`, `SECURITY`) + `LICENSE`, `Makefile`, `docker-compose.yml`, `start.sh`, `traceview.code-workspace` + directories `archive/`, `audit_artifacts/` (gitignored), `backend/`, `docs/`, `frontend/`, `scripts/`, `tests_e2e/` + 5 gitignored local `.db` test artifacts | `find . -maxdepth 1` |

**Conclusion: baseline is exactly as V21.0 reported it. No investigation needed before proceeding — repository is clean and green.**

## Repository structure (relevant subtrees)

- `backend/app/routers/`: 16 routers — `admin`, `analytics`, `annotations`, `api_keys`, `auth`, `billing`, `documents`, `groups`, `links`, `notifications`, `orgs`, `reading`, `storage`, `viewer`, `webhooks`, plus `__init__`.
- `backend/app/services/`: 26 service modules (+ `adapters/`, `toc/` subpackages).
- `docs/`: `api/`, `architecture/`, `deployment/`, `development/`, `engineering/`, `governance/`, `operations/`, `product-review/`, `reading_analytics/`, `release/`, `security/`, `ui-audit/`.
- `archive/`: `legacy-traceview/`, `root-historical/`, `browser-audit-screenshots/`, `docs-sprint2-3/`, `sprint3-4-reports/`, `sprint4-4-certification/`, `sprint5-6/`, `sprint7-18/`, `sprint18-certification/`.

## Canonical backlog snapshot at baseline (`ENGINEERING_BACKLOG.md`)

39 tracked items: 21 closed, 11 deferred/reviewed/justified, **7 open** — this sprint's actual scope, re-read fresh below rather than trusted from V21.0's summary:

| ID | Title (as currently filed) | Priority | Status (as currently filed) |
|---|---|---|---|
| ENG-017 | Observability wiring (Prometheus scrape/alerting) unconfirmed | Enhancement | Open (ops, not code) |
| ENG-019 | Dashboard screens' individual modals/toggles not re-exercised element-by-element | Enhancement | Open (2/N toggles API-verified) |
| ENG-033 | PROF-001: no profile/account-settings screen | High | Open (needs product/design input) |
| ENG-034 | No CD/deploy job in CI pipeline | Medium | Open (needs ops decision) |
| ENG-037 | `is_link_active()` not actually used by enforcement path | Low | Open (low urgency, needs care) |
| ENG-038 | `ensure_not_last_owner()` TOCTOU race (pre-existing) | Low | Open |
| ENG-039 | API keys with zero scopes can manage Orgs/API-Keys/Billing | Medium-High | Open (needs security-reviewed rollout) |

**Note on V22.0's prompt text**: the mega-prompt's own "Canonical Remaining Items" list names `ENG-039`, `ENG-017`, `ENG-040`, `ENG-037`, `ENG-038`, `ENG-033`, `ENG-034`, and `AUTH-006`. Cross-checking against the actual file: `ENG-040` does not exist in `ENGINEERING_BACKLOG.md` — there is no such entry. `AUTH-006` is not its own ENG-numbered item; it is the subject of `ENG-026` (Deferred, re-confirmed). `ENG-019` (dashboard toggle sweep) is a real open item that the V22.0 prompt's own list omits. These discrepancies are noted here rather than silently resolved — per this sprint's own "do not assume these descriptions are correct" instruction, applied symmetrically to the prompt's own framing, not just to the backlog. Investigated in detail below (see "ENG-040 disposition").
