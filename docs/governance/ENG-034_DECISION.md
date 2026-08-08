# ENG-034 — Decision Record: CD / Deploy Pipeline

**Status**: OPEN / DECISION REQUIRED (V22.0, 2026-08-07 — re-confirmed, not implemented)
**Type**: Infrastructure/ops decision, not an engineering defect

## Decision required

Whether to formalize an automated CD/release pipeline in `.github/workflows/ci.yml` (image push + deploy + rollback), and if so, what target platform and trigger model to standardize on.

## Current state

Source-verified: CI (`ci.yml`) already runs lint, the full test matrix against live Postgres+Redis, a migration smoke test, frontend build, `pip-audit`/`npm audit`, a Bandit scan, and a Docker build check — but the build step runs with `push: false`, so no image is ever published, and no deploy/release job exists anywhere in the workflow. In practice, Railway's auto-deploy-from-`origin/main` is the actual live deployment mechanism (established this session), so the product isn't undeployed — but that mechanism is Railway's own git-push trigger, not anything defined or version-controlled in this repository's CI. `docs/release/`'s existing files are one-time point-in-time reports (e.g. an "RC-1" cut), not a repeatable, codified release process.

## Available options

1. **Do nothing (status quo)** — keep relying on Railway's implicit auto-deploy-on-push. Zero engineering cost; works today; but has no rollback automation, no deploy gating on CI passing (Railway deploys independently of whether `ci.yml` is green), and no documented release process for anyone deploying outside Railway.
2. **Gate Railway deploys on CI** — no new deploy job needed; instead configure branch protection so `origin/main` only accepts merges after `ci.yml` passes, which indirectly makes every Railway auto-deploy a tested one. Small, low-risk, but still leaves rollback and non-Railway deployment undocumented.
3. **Add an explicit CD job** — extend `ci.yml` (or a new workflow) to build+push a versioned image to a registry and trigger a Railway (or other target) deploy explicitly from CI, with a defined rollback step (redeploy previous image tag). This is the "complete" answer but requires deciding the deploy target (stay on Railway vs. something else), registry, secrets/credentials management in CI, and a rollback procedure — none of which this engineering pass has the authority or the operational context to decide unilaterally.

## Trade-offs

- Option 1 costs nothing but leaves deploy/rollback entirely manual and undocumented outside Railway's dashboard.
- Option 2 is cheap and meaningfully reduces risk (bad code can't reach production without passing CI first) without requiring any new infrastructure decision.
- Option 3 gives full traceability and rollback but requires ops/infra buy-in on the target platform and credential handling that doesn't currently exist in this repo.

## Recommended default

Option 2 (CI-gated branch protection on `main`) as a low-risk first increment — it doesn't require choosing a deploy target or provisioning new credentials, and closes the most concrete risk (an untested commit reaching production) immediately. Option 3 remains the eventual target but needs an explicit ops decision first.

## What blocks implementation

No decision exists on the deploy target (stay on Railway vs. migrate), on registry/credential provisioning for CI, or on the rollback procedure — all genuinely ops-policy questions, not code questions. Per the governing mandate ("do not choose infrastructure merely to close a backlog item"), this is left **OPEN / DECISION REQUIRED** — no workflow changes implemented.
