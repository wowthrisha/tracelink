# Repository Health — Sprint 7.0

Repo-wide sweep of `backend/app/**` and `frontend/src/**` (excluding `frontend/dist`, `archive/`, `docs/`).

| Check | Result |
|---|---|
| `TODO` / `FIXME` comments | **Clean** — zero hits in either tree. |
| `console.log` / `debugger` in `frontend/src` | **Clean** — zero hits (`console.error`/`console.warn` exist and are intentional, e.g. `ViewerErrorBoundary.jsx`, `usePageLoader.js`). |
| `print(` in `backend/app` | **Clean** — the only occurrences are inside comments/docstrings showing how to generate a secret key (`config.py`, `main.py`), not debug leftovers. |
| Circular imports (backend and frontend) | **Clean** — full import graph built and checked, no cycles. |
| Naming conventions (Python snake_case, JS camelCase) | **Clean** — no confirmed violations beyond the `TabBtn`/`fmtTime` name collisions noted below (not violations, just same-name-different-thing). |

## Fixed this sprint

- **Unused imports removed** (4 files, confirmed unused via full-file grep before removal, not just spot-checked):
  - `backend/app/routers/documents.py` — `get_current_user` (file uses `require_scope` exclusively)
  - `backend/app/routers/webhooks.py` — `Optional`, `get_current_user`
  - `backend/app/routers/storage.py` — `func`
  - `backend/app/routers/orgs.py` — `Query`
- **Duplicate helper consolidated**: `fmtDate(iso)` was byte-identical across `OrgsScreen.jsx`, `AccessScreen.jsx`, `ApiKeysScreen.jsx`, `WebhooksScreen.jsx` — moved into `frontend/src/utils/viewer.js` alongside the already-shared `_errMsg`, all four screens updated to import it.
- **Duplicate service function consolidated**: `_get_session_id()` was byte-identical in `annotation_service.py` and `viewer_service.py` — the former now imports from the latter.
- **Duplicated auth-check logic consolidated**: `admin.py` reimplemented `org_service.require_role()` with drifted error messages — now calls the shared helper.
- **Stale documentation fixed**: `annotations.py`'s `resolve_annotation` route was commented "uploader-facing" but isn't (see `ARCHITECTURE_SCORECARD.md`) — comment corrected to describe actual behavior.
- **Bundle-mangling test fragility fixed**: `test_bundle_ends_with_reactdom_render` (`backend/tests/integration/test_phase2.py`) used a `\w+` regex to match esbuild's minified identifier, which doesn't account for esbuild's minifier legitimately using `$`-prefixed names once it exhausts short alphanumeric ones. This started failing after this sprint's source changes shifted the bundle's identifier count enough to trigger a `$`-prefixed name at that position — not a real regression, a pre-existing regex gap. Fixed to `[\w$]+`.

## Documented, not touched

- `_fmtMs(ms)` — same name, diverging behavior between `ReadingStatusBar.jsx` and `InsightsModal.jsx` (see `ARCHITECTURE_SCORECARD.md`) — left alone to avoid a display-behavior change I couldn't fully verify live this sprint.
- `TabBtn` naming collision between a private `InsightsModal.jsx` component and the shared exported `components/access/TabBtn.jsx` — confusing but not a bug; not renamed.
- `fmtTime` in `NotificationsScreen.jsx` vs. `AuditLogScreen.jsx` — same name, genuinely different (and both individually correct) behavior: relative "Xm ago" vs. absolute timestamp. Confirmed this is a naming coincidence, not a duplicate-logic bug — no action needed.
- A dead, frontend-unreferenced `POST /{org_id}/members` endpoint in `orgs.py` alongside the actively-used `invite_member_by_email` — not removed, since deleting an API endpoint is an API-surface change outside "fix only when safe" for this sprint.

## Unused-import spot-check coverage

In addition to the 4 confirmed-and-fixed cases above, `annotations.py`, `link_service.py`, `webhook_service.py`, `notification_service.py`, and a sample of frontend screens/hooks/components were checked — no further unused imports found.

---

# Sprint V6.0 — Phase 9 static analysis + deep dead-code sweep

Full repo-wide dead-code sweep (dead files, dead routes/endpoints, unused React components/hooks/utilities/CSS/exports), traced manually via import/reference grep since neither backend nor frontend has automated unused-export tooling wired in. "Confirmed dead" below means every reference was actually traced, not inferred from naming.

## Confirmed dead — removed this sprint

- **`frontend/src/components/analytics/RangeBtn.jsx`** — exported component with zero references anywhere outside its own file (including `AnalyticsScreen.jsx`, its logical consumer, which has no range-selector UI using it). **Deleted.**
- **`frontend/api.js:formatBytes()`** — zero references anywhere in `frontend/src`; `StorageScreen.jsx` has its own local, separately-implemented byte formatter instead, confirming this was an orphaned duplicate. **Removed.**
- **CSS classes `.header-btn-label` and `.screen-enter`** — the app has no dedicated `.css` files (all styling is inline style objects, except one global `<style>` block in `SecureDoc.html` for resets/animations); these two classes were defined in that block with zero `className` usages anywhere. The sibling classes `.toolbar-btn-label` (6 uses) and `.header-root` (1 use) in the same block ARE used, confirming these two were simply leftover. **Removed.**
- **`frontend/docs/`** — a 3-level-deep directory tree (`certification/`, `governance/`, `implementation/`) containing zero files at any level, verified with `find -type f` before removal. **Removed** — see `ENGINEERING_GOVERNANCE.md`.

## Confirmed dead — NOT removed this sprint (frontend-orphaned but plausibly intentional external API surface)

These `frontend/api.js` wrapper functions and their corresponding backend routes have zero call sites anywhere in the SPA, but the backend routes are authenticated via `get_current_user`, which accepts API keys — meaning an external API-key consumer could plausibly use them even though the browser app doesn't:

- `getViewerReadingSummary()` → `GET /api/reading/session/{session_id}` — session-token-authenticated (not API-key), so genuinely orphaned even by external-consumer standards; the SPA's reading-progress UI computes everything client-side and never calls this. Closer to confidently dead than the items below, but left untouched this sprint out of caution — removing a wrapper function is cheap, but removing the backend route itself (which would be the real cleanup) needs a deliberate decision, not a same-sprint judgment call under time pressure.
- `updateAnnotation()`, `resolveAnnotation()` (viewer-session-authenticated, not API-key) — superseded in the UI by the newer `getFeedback`/`resolveFeedback`/`replyToFeedback` endpoints; the SPA's comment UI never calls these.
- `getDocumentAnnotations()`, `exportAnnotations()` (API-key-authable via `get_current_user`) — superseded in the UI by `/annotations-visual` and `/feedback`, but plausibly intentional external API surface.

**Recommendation, not action taken**: confirm with whoever owns the external API surface (if any exists) before removing either the frontend wrappers or the backend routes. Removing a backend route is an API-surface change this sprint's own rules keep out of "fix only when safe."

## Likely dead — unverified, flagged for a second check

- `GET /api/documents/{document_id}/versions` (`documents.py:get_document_versions`) — no call site anywhere in the SPA (`api.js` has no wrapper at all), same auth pattern as every other used route in the file, so the auth pattern alone doesn't distinguish "API-only." Not confidently dead — could be a partially-built or feature-flagged frontend feature not yet wired up.
- `GET /api/orgs/{org_id}/domain/token`, `POST /api/orgs/{org_id}/domain/verify` — zero references in `OrgsScreen.jsx`, but the docstrings describe a manual DNS-TXT-record admin workflow, reading like deliberately API/CLI-only operations rather than an abandoned SPA feature.

## Functional bug found via dead-code tracing (not itself dead code)

- `backend/app/workers/webhook_tasks.py` is not literally an unused file (imported directly by `test_enterprise_product.py`), but tracing its actual production import path found that **no production code ever imports it** — `celery_app.py`'s `include=` list omitted it entirely, meaning its `@celery_app.task` never registers with a real Celery worker process. This is a severe functional/reliability bug, not dead code — full detail and the fix in `SECURITY_GOVERNANCE.md`.

## Nothing else found (clean categories)

- **Dead files**: every router is registered in `main.py`; every screen is imported from `AppShell.jsx`; every hook and utility function (besides the two removed above) is imported and called somewhere reachable from the two entry points.
- **Unused React components/hooks**: besides `RangeBtn.jsx` (removed), all components under `components/` and all 8 hooks under `hooks/` are confirmed imported and reachable.
- **Unused CSS**: besides the 2 classes removed above, no other dead class names found — confirmed there are no dedicated `.css` files to sweep beyond the one global stylesheet.
- **Dead exports within used files**: spot-checked `atoms.jsx` (all 14 exports used), `api.js`, and 2–3 backend service files — no further dead exports found beyond `formatBytes`.

## Migration validation

`alembic/versions/` chain checked: migration `027` (new this sprint, adds the webhook-delivery composite index) is the only file claiming `down_revision = "026"` — confirmed single linear head, no branching.

## Lint / type-checking — tooling gap, not a run result

Checked for configured lint/type-check tooling before claiming to have run either: no `.eslintrc*`, no `lint` script in `frontend/package.json`, and no `mypy`/`ruff`/`flake8` in `backend/requirements-dev.txt` or a `pyproject.toml` anywhere in the repo. **Neither lint nor type checking is wired into this project at all** — this isn't a "clean" result, it's an absence of tooling. Noted honestly rather than fabricating a pass. Not set up this sprint — introducing a linter/type-checker for the first time is a project-wide tooling decision (config, initial-baseline noise, CI wiring) outside "fix only when safe" scope, but it's a real gap worth a deliberate follow-up, especially given `backend/app` is plain Python with no static type enforcement despite consistent type hints already being used throughout.

## Final validation (Sprint V6.0)

- `cd backend && python -m pytest tests/unit tests/integration tests/regression -q` → **1702 passed, 1 skipped, 0 failed**
- `cd frontend && npm test` → **13/13 passed**
- `cd frontend && npm run build` → succeeded, 311.3kb, no errors
- Migration chain: single linear head (`027`)
- Repo-wide TODO/FIXME/console.log/debugger sweep on this sprint's diff: clean
