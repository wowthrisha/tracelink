# Code Standardization — Sprint V7.0 (Phase 2)

Repo-wide consistency audit: naming, folder structure, exception handling, logging, response models, permissions, audit logging, dependency injection, async patterns, imports, comments, documentation. Assessment only, per this sprint's scope — no fixes implemented here except where explicitly noted as a documentation correction (not app-code).

## Already well-standardized (no manufactured findings)

- **Dependency injection**: `db: AsyncSession = Depends(get_db)` followed by `user: dict = Depends(get_current_user)` (or `require_scope(...)`) is near-universal across all 16 routers — dozens of matching call sites, essentially zero structural variance. No router manually constructs a session or instantiates a service in place of injection.
- **Exception handling for expected errors**: `raise HTTPException(status_code=..., detail=...)` is universal (200+ call sites across all 16 routers) for 404/403/422-class errors, and there's a real global safety net — `main.py`'s `@app.exception_handler(Exception)` logs and returns a generic 500, so routers correctly don't need per-route catch-alls for the unexpected case.
- **Module boundaries**: verified twice now (V6.0 and this sprint) — zero cross-layer violations between models/services/routers.
- **Error response shape**: consistently the standard FastAPI `HTTPException(detail=...)` shape everywhere; no router hand-rolls a custom error dict.

## Genuinely inconsistent — documented, not fixed (app-code changes, out of this sprint's scope)

| Dimension | Finding |
|---|---|
| **Logging** | 6 of 16 routers (`admin.py`, `api_keys.py`, `groups.py`, `links.py`, `orgs.py`, `webhooks.py`) have **no logger at all**, yet all six contain `except Exception: pass` blocks that are genuinely silent — no log line before suppression. Where a logger does exist, naming varies: most use `logging.getLogger(__name__)`, but `billing.py` hardcodes `"securedoc.billing"` and `annotations.py` uses the unusual `__import__("logging").getLogger(__name__)` instead of a normal top-level import. |
| **Async patterns** | Two confirmed instances of synchronous, blocking work inside an `async def` handler not offloaded via `run_in_executor`: `viewer.py:get_page` (session-heartbeat + analytics-log side effects, previously flagged) and, newly found this sprint, `viewer.py:download_document` lines 614-617 — a synchronous `PdfWriter.write()` call to disk, immediately adjacent to a correctly-offloaded watermarking step one line above it. |
| **Imports — `log_audit_event` placement** | 7 of 8 routers that call it import it **locally inside the function body**; `webhooks.py` alone imports it at module top. No discernible rule (not a circular-import necessity — `webhooks.py` proves top-level import works). |
| **Imports — PEP8 grouping** | No `isort`/`ruff`-import-sort enforcement exists. `orgs.py`/`notifications.py` follow clean stdlib/third-party/local grouping; `groups.py`/`analytics.py` have no blank line between groups; `documents.py` interleaves a `logger = ...` statement between the third-party and local import blocks. |
| **Validation — typed vs. raw dict** | Only 3 of 16 routers (`documents.py`, `links.py`, `groups.py`) use typed Pydantic request schemas from `schemas/`. 14 endpoints across 7 files (`orgs.py` alone: 5) accept raw `body: dict` with manual `.get()` extraction — `analytics.py:209` even has an inline code comment acknowledging the risk ("SEC: validate body field types explicitly — body: dict accepts any JSON type"). This is the single largest standardization gap found this sprint (also flagged independently in `LONG_TERM_MAINTAINABILITY.md` as the highest-leverage backend finding). |
| **Response models** | `response_model=` declared on routes in only 3 of 16 routers; 110+ route handlers elsewhere return raw dicts with no declared OpenAPI response schema. |
| **Comments/docstrings** | No enforced convention — module-level docstrings exist in only 2 of 10 sampled files; function-docstring density varies by file with no evident rule tied to complexity (some simple CRUD handlers are documented while some genuinely tricky cache/session services are not). |
| **REST resource naming** | `annotations.py` and `storage.py` don't use `APIRouter(prefix=...)` like the other 14 files — they hardcode full paths per-route instead. `annotations.py` additionally straddles two resource families (`/api/viewer/...` and `/api/documents/...`) in one file. |
| **Action-endpoint convention** | RPC-style verb suffixes (`/rotate`, `/reprocess`, `/test`, `/domain/verify`) coexist with PATCH-on-resource (`/resolve`) for the same conceptual "trigger a state transition" action, with no documented rule for which to use. |
| **HTTP status codes** | Creates and deletes are 95% consistent (201/204 respectively) with two named exceptions: `links.py`'s two DELETE endpoints return 200+body against 8 other DELETE endpoints that correctly return 204/no-body. |

## Permissions & audit logging — status

Already covered in depth by prior work (`SECURITY_GOVERNANCE.md`, `MODULE_BOUNDARIES_AND_CODE_QUALITY.md`) and reconfirmed clean this sprint for the two most recently-touched routers: `webhooks.py` and `storage.py` both correctly call `log_audit_event` before `db.commit()` (same transaction), matching the established pattern. The `require_scope` vs. bare `get_current_user` split (finer-grained scope enforcement in `analytics.py`/`documents.py`/`groups.py`/`links.py`/`reading.py`/`storage.py`/`webhooks.py` vs. coarser `get_current_user` in `admin.py`/`billing.py`/`annotations.py`/`api_keys.py`/`notifications.py`/`orgs.py`) is unchanged from prior findings — `orgs.py` is the heaviest user of the coarser pattern (12 call sites, zero `require_scope` usage).

## Frontend standardization

See `FRONTEND_MATURITY.md` for spacing/iconography/animation/keyboard/responsive findings (new this sprint) and `CONSISTENCY_MATRIX.md` (V6.0) for confirmation-dialog/empty-state/date-format/toast/loading-text/button-variant/ARIA/terminology findings — not re-derived here.

## Ranked top-6 standardization opportunities (backend)

1. Silent `except Exception: pass` in the 6 loggerless routers — highest value, real observability blind spots.
2. The `viewer.py:download_document` blocking-write instance — a second confirmed case of the same async anti-pattern already known from `get_page`.
3. `log_audit_event` import placement — trivial, mechanical, 7-vs-1 split.
4. Response-model coverage on the 13 routers that skip it — restores OpenAPI self-documentation.
5. Logger naming/instantiation style — two named outliers to fix.
6. Import grouping/ordering — cosmetic, automatable via a linter (see `DEVELOPER_EXPERIENCE.md` for the broader finding that no linter is configured at all).

None of these were implemented this sprint — each is an application-code change, and this sprint's mission is explicitly assessment-only ("the objective is no longer fixing bugs... focus only on engineering maturity"). They are ranked and ready for a dedicated standardization pass.
