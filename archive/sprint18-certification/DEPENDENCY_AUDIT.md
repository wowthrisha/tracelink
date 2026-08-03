# Dependency Audit — V18.0 Repository Certification

Covers `backend/requirements.txt`, `backend/requirements-dev.txt`, `tests_e2e/requirements-test.txt`, `frontend/package.json`, `docker-compose.yml`, `backend/Dockerfile`, `.github/workflows/ci.yml`, root `Makefile`.

## Fixed this sprint

| # | Change | File | Evidence | Risk | Verification |
|---|---|---|---|---|---|
| 1 | Removed `factory-boy==3.3.0` | `backend/requirements-dev.txt` | Source verified — zero `import factory`/`from factory import` anywhere in `backend/` | None | Full backend suite 1705 passed/1 skipped/0 failed |
| 2 | Removed `pytest-cov==6.0.0` | `backend/requirements-dev.txt` | Source verified — no `--cov` flag in `pytest.ini`, CI, or Makefile anywhere in the repo | None | Same |
| 3 | Removed direct `anyio==4.7.0` pin | `backend/requirements-dev.txt` | Source verified — zero direct `import anyio` in `backend/`; remains installed transitively via httpx/starlette, which genuinely need it, so nothing breaks | None (confirmed `anyio==4.14.2` still present transitively after removal) | Same |
| 4 | Pinned 5 floating `>=` OpenTelemetry/prometheus packages to exact versions, matching the file's own convention and the versions actually running in the verified-working Docker stack (`prometheus-client==0.26.0`, `opentelemetry-sdk==1.44.0`, `opentelemetry-instrumentation-fastapi==0.65b0`, `opentelemetry-instrumentation-sqlalchemy==0.65b0`, `opentelemetry-exporter-otlp-proto-http==1.44.0`) | `backend/requirements.txt` | Source verified (file inconsistency) + runtime verified (queried `pip show` inside the live Docker `api` container for the actual resolved versions before pinning, rather than guessing) | Low — pins to what's already running and tested, doesn't change behavior | Docker `api` container rebuilt, healthy, `/health` returns `{"status":"ok",...}` with all subsystems ok |
| 5 | Removed `@testing-library/user-event` | `frontend/package.json` | Source verified — zero `userEvent`/`user-event` usage anywhere in `frontend/src` | None | 13/13 tests, lint exit 0, build succeeded |
| 6 | Removed `@vitest/coverage-v8` | `frontend/package.json` | Source verified — no `--coverage` flag or `coverage` key anywhere in `vitest.config.js`, `package.json` scripts, CI, or Makefile | None | Same |
| 7 | `backend-test` CI job now installs `requirements-dev.txt` alongside `requirements.txt` | `.github/workflows/ci.yml` | Source verified — the job ran `pytest tests/ -x -q --tb=short` while only ever installing `requirements.txt`; `pytest`, `pytest-asyncio`, `moto`, `fakeredis` are declared only in `requirements-dev.txt` | Low — additive install step, can only fix a broken/fragile job, can't break a working one | Not independently re-run against live GitHub Actions this sprint (would require pushing to a branch) — flagged as **Insufficient evidence for the exact prior failure mode**, but the missing-install fact itself is source-verified and the fix is a strict superset install |

Frontend `package-lock.json` was regenerated and reconciled across both macOS/arm64 (local) and Linux/Alpine (Docker) per the exact procedure established in this project's ENG-013/ENG-014 fixes: `npm install` locally first, then `npm install` (not `--package-lock-only`) inside a `node:20-alpine` container bind-mounted to the same directory, unioning both platforms' optional-dependency variants into one lockfile — then verified `npm ci --ignore-scripts` succeeds independently and in isolation on **both** platforms (Alpine check used a `/tmp` copy, not the live working directory, to avoid cross-contaminating `node_modules`).

## Found, not changed — recommendations for a future pass

| Finding | Evidence | Recommendation | Risk if left | Effort |
|---|---|---|---|---|
| `httpx==0.28.0` pinned identically in both `requirements.txt` and `requirements-dev.txt` | Source verified | Harmless redundancy — `CONTRIBUTING.md` already documents installing both files together. Low-value cleanup; left alone this sprint to avoid touching a file (`requirements.txt`) more than the OTel fix already did in one pass without a full re-verify cycle in between | None (purely cosmetic duplication) | Trivial |
| `tests_e2e/requirements-test.txt` uses loose `>=` pins throughout, inconsistent with `requirements.txt`/`requirements-dev.txt`'s exact `==` pins | Source verified | A repo-wide pinning-strategy decision (exact-pin everywhere vs. deliberately loose for the E2E suite) is a policy call, not a mechanical fix — flagging for whoever owns CI/test infrastructure policy | Low — E2E suite isn't part of the standard CI gate per `ENGINEERING_GOVERNANCE.md`'s own admission that it "requires live services" | Low once a policy is picked |
| `docker-compose.yml`'s `backup` service reimplements pg_dump backup/rotation entirely inline in its `entrypoint:` shell string, independently of the more full-featured `scripts/backup.sh` (which the compose service never calls) | Source verified — `grep -n "backup.sh" docker-compose.yml` returns no match | Two independent backup implementations can silently drift out of sync. Recommend the compose `backup` service invoke `scripts/backup.sh` directly instead of duplicating its logic — but this is an infra-behavior change (not a pure hygiene fix) that deserves its own test cycle against a real backup/restore drill, not a certification-sprint edit | Medium — a bug fixed in one implementation but not the other could silently produce bad backups | Medium |
| `BACKUP_ENABLED` documented in a `docker-compose.yml` comment but never actually read anywhere (the `backup` service is gated solely by the Compose `profiles: [backup]` mechanism) | Source verified | The comment is misleading, not the mechanism — either wire the env var in, or correct the comment. Left as a documented (not silently dropped) finding rather than guessing which the maintainer intended | Low (confusion risk only) | Trivial once a direction is picked |
| `FRONTEND_BASE_URL` and `TEST_DATABASE_URL` declared in `backend/.env.example` but zero readers anywhere in the repo (`TEST_DATABASE_URL` is misleading — the test suite hardcodes its own `sqlite+aiosqlite://` URLs per file instead) | Source verified | Stale example-env entries; low risk to remove, but touching `.env.example` wasn't verified against every deployment target's actual `.env` this sprint — flagging rather than assuming | Low | Trivial |
| Version pinning: `react`/`react-dom` exact-pinned (no `^`), matching the CDN `<script>` tag's exact `18.3.1` in `SecureDoc.html` | Source verified | **Not a defect** — intentional, confirmed consistent with the CDN-script-tag architecture. Documented here only so a future audit doesn't re-flag it | None | — |

## No duplicate/overlapping tooling found

- Single HTTP client (`httpx`) — no `requests`/`aiohttp` present.
- Single backend test framework (`pytest`) — no unittest-based runner.
- Single frontend test runner (`vitest`) — no jest/mocha.
- Single lint tool per language (`ruff` backend, `eslint` frontend).
- No production `dependencies` block in `frontend/package.json` at all — consistent with the CDN-script-tag + esbuild-bundle architecture (React/ReactDOM loaded as UMD globals, not npm-imported per file).

## Docker / CI structural check — clean

- 7 Compose services, all live; `backup` is intentionally `profiles`-gated, not orphaned.
- No unused Dockerfile `ARG`s or Compose `args:` blocks (none exist).
- Single GitHub Actions workflow (`ci.yml`), 8 jobs, no dead/commented-out steps, no path references to nonexistent scripts.
- `Makefile`'s 10 targets all resolve to real commands/paths.
- `frontend/dist/app.bundle.js` is deliberately tracked in git (`.gitignore` negates the general `dist/` ignore for this one path) — the compiled bundle ships with the image without requiring a build step in every environment; not a stray artifact.

## Not independently re-verified this sprint (flagged, not asserted)

- Whether the CI `backend-test` job's pre-fix state (missing `requirements-dev.txt`) actually failed in a live GitHub Actions run, versus silently working via some runner-level pytest pre-install — the missing-install line is a file-level fact (source verified); the runtime failure mode itself would require an actual CI run to confirm and was not pushed this sprint. **Insufficient evidence** for the exact prior failure symptom, though the fix is safe regardless (a strict superset install cannot make a working job fail).
