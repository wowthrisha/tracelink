# Backend Architecture Review

## Layering Today

`backend/app/routers/` (14 files, ~5,821 lines) → `backend/app/services/` (~20 files) → `backend/app/models/` (14 SQLAlchemy models). Workers live in `backend/app/workers/` (Celery tasks + pipeline adapters).

The service layer exists and is used well in places (`link_service.py`, `policy.py`, `retention.py`, `webhook_service.py`, `viewer_cache.py`, `audit_service.py`, `org_service.py`, the `services/adapters/*` registry pattern for file-type-specific processing). The gap is concentrated in exactly two router files.

## Finding 1 (P1): `annotations.py` (1,285 lines) has no service layer

Every piece of business logic — thread-building, filter-matching, profile-name resolution, three separate CSV generators — lives directly in route handler bodies or module-level helper functions inside the router file itself:

- `_resolve_display_name`, `_profile_display_names`, `_parse_filter_date`, `_message_matches_filters`, `_thread_matches_filters`, `_serialize_annotation` — six helper functions doing what a dedicated `annotation_service.py` should own.
- `list_document_feedback` (104 lines) walks every reply, applies up to 5 filter dimensions per message, then serializes — this is exactly the kind of logic a service test should exercise directly instead of only through the HTTP layer.
- Three CSV exporters inlined: `export_feedback` (124 lines, just rewritten for the "Feedback Conversations" redesign), `export_reviewer_activity` (~50 lines), `export_visual_annotations` (~48 lines).

**Recommendation:** extract `app/services/annotation_service.py` with `get_feedback_threads(doc_id, filters)`, `export_feedback_csv(threads)`, `get_reviewer_directory(doc_id)`. This is the single highest-value backend refactor in the repo — it's also the file most recently and most frequently touched (feedback/CSV work across the last several sessions), so every future change to this feature keeps paying the "edit a 1,285-line file" tax until it's split.

## Finding 2 (P1): `viewer.py` (1,203 lines) — same pattern

`download_document` alone is 179 lines (cache lookup + permission check + storage retrieval + streaming + audit logging, all sequential in one function). `get_toc` (100 lines), `get_text_chunk` (130 lines), `search_document` (97 lines) each re-derive PDF sidecar loading/caching logic instead of sharing it. The `_get_cached_link_and_doc` helper (78 lines) is reused by 8 of the 10 routes, which is good — but each caller still re-implements its own post-cache logic rather than delegating to a `viewer_service`.

**Recommendation:** extract `app/services/viewer_service.py` with `serve_page_bytes`, `serve_thumbnail_bytes`, `search_text`, `get_toc_data` — mirrors the `annotation_service` extraction above and should be done in the same pass since both routers share the same cache/session-validation preamble pattern.

## Finding 3 (P2): Route functions exceeding 100 lines

| Function | File | Lines |
|---|---|---|
| `download_document` | viewer.py | 179 |
| `upload_document` | documents.py | 168 |
| `log_viewer_event` | analytics.py | 153 |
| `validate_link` | viewer.py | 146 |
| `get_text_chunk` | viewer.py | 130 |
| `get_page` | viewer.py | 129 |
| `export_feedback` | annotations.py | 124 |
| `get_thumb` | viewer.py | 116 |
| `list_document_feedback` | annotations.py | 104 |
| `get_toc` | viewer.py | 100 |

Ten functions over 100 lines, three over 150. A route handler this long means: harder to unit test without standing up the full HTTP layer, harder to review diffs against, and harder to reuse logic from a second entry point (e.g. a future internal admin tool that needs `search_text` without going through HTTP). Target: route handlers under 60 lines once service extraction (Findings 1-2) lands — they should be "parse input → call service → shape response."

## Finding 4 (P2): Inconsistent list response shapes

Eight list endpoints surveyed return six different wrapper/pagination conventions (`{"documents":[...]}` with no total, vs `{"feedback":[...], "total": len(...)}` with an in-memory count, vs `{"events":[...], "total", "offset", "limit"}` with real DB pagination). See API_CONTRACT_REVIEW.md for the full table. **Recommendation:** standardize new endpoints on `{"items": [...], "total": int, "offset": int, "limit": int}`; this is a service-layer concern as much as a router one — once business logic moves into services returning typed results, a single response-shaping helper in the router layer becomes natural.

## Finding 5 (P3): Authorization expressed inconsistently

`require_scope("documents:read")`-style dependencies are the dominant, good pattern (documents.py, links.py, webhooks.py, storage.py, analytics.py). `admin.py`'s org-role check and `orgs.py`'s owner/admin/viewer hierarchy checks are correct but live in function bodies rather than as declarative dependencies — harder to audit at a glance which routes require which privilege level. Not a vulnerability (tests cover the actual behavior), but a maintainability/auditability gap. **Recommendation:** add a `require_org_role(min_role)` dependency factory analogous to `require_scope()`.

## What's Working Well (don't touch)

- `services/adapters/` registry pattern (`pdf.py`, `word.py`, `presentation.py`, `spreadsheet.py`, `text.py` behind a common `base.py` interface) — clean extension point, exactly the abstraction the annotation/viewer routers are missing.
- `policy.py` + `viewer_cache.py` separation — cache invalidation triggers (link revoke, link update) are centralized and consistently called from `links.py`, not duplicated per-route.
- `webhook_service.py` / `webhook_tasks.py` split — SSRF validation at create-time lives in the service, re-validation at delivery-time lives in the task; correct separation of "can this be configured" from "is this still safe right now."
- `retention.py` / `cleanup.py` — declarative lifecycle states (`active`/`archived`/`expired`/`deleted`) driving a single daily task, not scattered ad-hoc deletion logic.

## Celery / Workers

`celery_app.py` configures a Redis broker/backend. Tasks (`tasks.py`, `cleanup.py`, `webhook_tasks.py`, `pipeline/*.py`) use a `_run_async()` sync wrapper around async business logic — tests call the async functions directly rather than invoking real Celery tasks, and no `CELERY_ALWAYS_EAGER`/real-worker integration test exists in CI. `requeue_orphaned_uploads()` (tasks.py) has no direct test at all (see TECHNICAL_DEBT_REGISTER.md). This isn't an architecture defect — the sync-wrapper-around-testable-async-core pattern is the right shape — but the orphan-requeue recovery path and webhook delivery's retry-exhaustion/dead-letter path are both real production code with no test exercising them end to end.
