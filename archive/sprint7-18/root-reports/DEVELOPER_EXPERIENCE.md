# Developer Experience — Sprint V7.0 (Phase 8)

Simulated a new engineer's first day, walking through each of 8 onboarding tasks against the actual current documentation and repo state — not assumptions about what should work.

| Task | Verdict | Where they'd get stuck |
|---|---|---|
| **Run the project** | **Would not succeed unassisted** | README's environment-variable table is factually wrong: `JWT_SECRET` is listed as required but nothing in `backend/app/config.py` reads it (auth is JWKS-based, no shared secret); `SUPABASE_SERVICE_KEY` is misnamed (the real field is `SUPABASE_SERVICE_ROLE_KEY`); `STORAGE_BACKEND` doesn't exist at all as a config field (the real switch is `USE_DEMO_STORAGE=1`, mentioned nowhere in the README). `.env.example` doesn't even contain the variables the README told them to fill in. No install instructions for native PostgreSQL/Redis. `DEVELOPER_GUIDE.md`'s own `docker compose up -d postgres redis` command uses service names that don't match `docker-compose.yml`'s actual `db`/`redis` names — a copy-pasted command fails outright. (Silver lining: `config.py` has sane defaults for everything, so the app *will* boot with just `.env.example` + `USE_DEMO_STORAGE=1` — but nothing tells a newcomer that.) |
| **Understand the architecture** | **Succeeds — a genuine strength** | `docs/architecture/OVERVIEW.md`/`ARCHITECTURE.md` clearly explain request flow, auth model, Celery pipeline, and caching, and mostly match the code (see `DOCUMENTATION_MATURITY.md` for the real gaps here — staleness and two factual contradictions between the pair, which a newcomer wouldn't know to distrust). |
| **Debug issues** | **Partially works** | `RUNBOOK.md` has real dev-relevant content (Celery status, log inspection) but is written for a deployed/named-container environment (`docker restart securedoc-api`) — a newcomer running `uvicorn --reload` natively has to translate every command themselves. No "inspect the DB locally via psql" guidance exists. |
| **Deploy** | **Actionable, but propagates the same wrong env vars** | `DEPLOYMENT.md` is concrete and a newcomer could follow it structurally, but its own "Environment Variables" table repeats the exact same errors as the README (`JWT_SECRET`, `SUPABASE_SERVICE_KEY`, `STORAGE_BACKEND` all marked "Required: Yes" and all wrong) — the friction resurfaces later in the day, not just at setup. |
| **Write tests** | **Mostly succeeds** | `conftest.py`'s shared fixtures (`client`, `db_session`, `ready_document`) make "copy a neighboring test" easy, and `DEVELOPER_GUIDE.md` documents the `unit`/`integration` split clearly. Gap: a third real test category, `tests/regression/` (4 files, covering security invariants), is never mentioned in any engineer-facing doc — only findable in an internal governance document. A newcomer adding a security-invariant test would likely (and reasonably) put it in `integration/` instead. |
| **Add features** | **Succeeds — a genuine strength** | `DEVELOPER_GUIDE.md` gives an explicit, correct 10-step backend flow (router→schema→service→model→migration→metrics→tests→register) and 6-step frontend flow. This is one of the best onboarding assets in the repo. One small drift: the guide says frontend tests belong in `frontend/src/tests/`, but the actual convention is colocated `__tests__/` folders — a newcomer's test file wouldn't be picked up where the doc said to put it. |
| **Review code** | **No structural support** | No PR template, no CODEOWNERS file, no dedicated style guide beyond a short section in `DEVELOPER_GUIDE.md` and an ad hoc checklist in `CONTRIBUTING.md` (tests pass, no stray `print()`/`console.log`, no secrets, migrations included). Reasonable as a checklist, but there's no way to know who owns/reviews which part of the codebase. |
| **This codebase's specific quirk: no build framework on the frontend** | **Guaranteed confusion, entirely undocumented** | Production React loads via CDN UMD script tags, not `import React from 'react'`, and there's no router library — confirmed real (`package.json` lists `react`/`react-dom` as devDependencies only, actual runtime React comes from `unpkg.com` in `SecureDoc.html`). Every doc that mentions this states it as a fact ("React 18, esbuild IIFE bundle") with zero explanation of *why*, and no warning that adding a standard `import React from 'react'` would be wrong. Any engineer coming from Vite/CRA/Next.js will burn real time here before realizing the pattern is intentional. |

## Top 6 friction points, in the order a new engineer would actually hit them

1. **README's environment-variable table is factually wrong** — hit in the first 5 minutes, before the app even starts.
2. **`.env.example` doesn't contain the variables the docs reference** — can't "fill in credentials" for fields that don't exist in the file.
3. **No native PostgreSQL/Redis install instructions**, blocking the non-Docker quick-start path immediately.
4. **`DEVELOPER_GUIDE.md`'s docker-compose command references wrong service names** — a literal copy-paste failure.
5. **The frontend's no-bundler/no-router architecture is undocumented** — first confusing surprise once actually writing code.
6. **`DEPLOYMENT.md` repeats the same bogus required env vars** — the friction resurfaces later, at first deploy.

Lower-priority but real: `tests/regression/` undocumented for engineers, no PR template/CODEOWNERS, RUNBOOK oriented toward prod container names over local dev, `DEVELOPER_GUIDE.md`'s frontend test-location guidance drifted from actual convention.

## What's already strong

Architecture documentation, the add-a-feature workflow guide, and the test-fixture pattern are all genuinely good and shouldn't be touched — the friction here is concentrated almost entirely in the **first-run environment setup path** (README + `.env.example` + `DEVELOPER_GUIDE.md`'s quick-start command), which is exactly the part of onboarding a new engineer hits before they have enough context to route around a mistake themselves. That concentration is actually good news: 4 of the top 6 friction points are fixed by correcting the same small set of documentation facts, not by a broad rewrite.

## Fixed this sprint (documentation corrections only, not application code)

Per this sprint's scope (assessment-focused, "no more bug fixes" refers to application behavior — these are factually incorrect documentation references, which Phase 7's own instruction explicitly calls out: "fix broken references"):

- `README.md`'s environment-variable table corrected: removed `JWT_SECRET` (unused), renamed `SUPABASE_SERVICE_KEY` → `SUPABASE_SERVICE_ROLE_KEY`, replaced the nonexistent `STORAGE_BACKEND` entry with the real `USE_DEMO_STORAGE` switch.
- `docs/development/DEVELOPER_GUIDE.md`'s quick-start docker-compose command corrected from `postgres redis` to the actual service names `db redis`.

Not fixed this sprint: `.env.example`'s missing variables and `DEPLOYMENT.md`'s duplicate wrong table — both real, both flagged in `TECH_DEBT_REGISTER.md` as P0 (cheap, high-friction), left for a follow-up pass focused specifically on environment-variable documentation end-to-end rather than partial fixes in this already-large sprint.
