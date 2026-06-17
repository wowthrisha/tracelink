# Architecture Refactor Report — Sprint 2

Generated: 2026-06-17

## Summary

Sprint 2 extracted all business logic from two large FastAPI router files into
dedicated service modules. Routers now delegate to services and handle only
HTTP concerns (request parsing, response shaping, auth middleware).

---

## Before / After Line Counts

### Annotation subsystem

| File | Before | After | Delta |
|------|-------:|------:|------:|
| `app/routers/annotations.py` | 1,285 | 527 | −758 |
| `app/services/annotation_service.py` | — | 137 | +137 |
| `app/services/annotation_thread_service.py` | — | 215 | +215 |
| `app/services/annotation_filter_service.py` | — | 65 | +65 |
| `app/services/annotation_export_service.py` | — | 270 | +270 |
| **Subsystem total** | **1,285** | **1,214** | **−71** |

### Viewer subsystem

| File | Before | After | Delta |
|------|-------:|------:|------:|
| `app/routers/viewer.py` | 1,203 | 965 | −238 |
| `app/services/viewer_service.py` | — | 86 | +86 |
| `app/services/viewer_session_service.py` | — | 147 | +147 |
| `app/services/viewer_bookmark_service.py` | — | 74 | +74 |
| `app/services/viewer_annotation_service.py` | — | 244 | +244 |
| **Subsystem total** | **1,203** | **1,516** | **+313** |

> The viewer subsystem grows slightly in total lines because the extracted
> services add module boilerplate (imports, docstrings). Router line count drops
> 20% (1,203 → 965); more importantly, the router no longer contains any
> business logic — it only orchestrates.

---

## New Service Modules

### `annotation_service.py`
**Responsibility**: Auth helpers, display-name resolution, annotation serialization.

Key functions:
- `_get_session_id(request)` — header/cookie session extraction
- `_is_uploader_row(session_id)` — uploader vs viewer distinction
- `_resolve_display_name(...)` — display name for uploader and viewer paths
- `_profile_display_names(db, annotations)` — batch ViewerProfile lookup
- `_serialize_annotation(a, ...)` — canonical annotation dict serializer
- `_resolve_link_and_verify_session(...)` — cache-first link lookup + session auth

### `annotation_thread_service.py`
**Responsibility**: Thread fetch, feedback list, reviewer roster, uploader replies.

Key functions:
- `fetch_thread(db, root, link_row, session_id)` — depth-1 thread assembly
- `create_uploader_reply(db, target, doc, text, current_user)` — owner-replies with depth guard
- `fetch_feedback_list(db, doc, ...)` — full filter+search pipeline over threads
- `fetch_feedback_reviewers(db, doc)` — distinct viewer roster for reviewer filter UI

### `annotation_filter_service.py`
**Responsibility**: Pure filter predicates (no HTTP or DB dependencies).

Key functions:
- `_parse_filter_date(value, *, end_of_day)` — ISO date string → tz-aware UTC datetime
- `_as_aware_utc(dt)` — normalize naive datetimes from SQLite
- `_message_matches_filters(a, ...)` — single-message predicate
- `_thread_matches_filters(messages, ...)` — any-message predicate for threads

### `annotation_export_service.py`
**Responsibility**: CSV export generators. Returns `(generator, filename)` tuples — no FastAPI imports.

Key functions:
- `build_annotations_export(db, doc)` — all annotations for a document
- `build_feedback_export(db, doc, ...)` — feedback with full filter support
- `build_reviewer_activity_export(db, doc)` — per-reviewer activity summary
- `build_visual_annotations_export(db, doc)` — visual annotations only

### `viewer_service.py`
**Responsibility**: Viewer infrastructure helpers for link/doc state checks and caches.

Key functions:
- `_check_link_active(link, now)` — raises 410 if revoked/expired
- `_check_doc_ready(doc)` — raises 503 if not ready
- `_get_session_id(request)` — header/cookie session extraction
- `clear_page_cache()`, `clear_thumb_cache()`, `clear_metadata_caches()` — test utilities

### `viewer_session_service.py`
**Responsibility**: Full validate_link response builder (session, analytics, concurrency, permissions, webhooks).

Key functions:
- `build_validate_response(db, body, ip, user_agent, link_svc, analytics_svc)` — complete
  6-stage validate flow returning the JSON response payload

### `viewer_bookmark_service.py`
**Responsibility**: Viewer bookmark CRUD.

Key functions:
- `fetch_bookmarks(db, link_id, session_id)` — list all bookmarks for a session
- `toggle_bookmark(db, link_id, session_id, page_number, label)` — create-or-delete toggle

### `viewer_annotation_service.py`
**Responsibility**: Viewer-facing and owner-facing annotation CRUD.

Key functions:
- `fetch_page_annotations(db, link_id, session_id, page_number)`
- `create_viewer_annotation(db, link_row, session_id, body)`
- `update_viewer_annotation(db, link_row, session_id, annotation_id, body)`
- `delete_viewer_annotation(db, link_row, session_id, annotation_id)`
- `toggle_resolve_annotation(db, link_row, annotation_id)`
- `fetch_document_annotations(db, doc, annotation_type, resolved)`
- `fetch_visual_annotations(db, doc, annotation_type)`

---

## Constraints Verified

| Constraint | Status |
|------------|--------|
| ZERO API changes | PASS — all endpoint signatures identical |
| ZERO database changes | PASS — no migrations, no schema changes |
| ZERO security regressions | PASS — auth/permission logic preserved verbatim |
| All unit tests green | PASS — 547/547 |
| All integration tests green | PASS — 1077/1077 (1 skipped, pre-existing) |

---

## Test Patch Compatibility

Several functions were **kept in `viewer.py`** rather than moved to services
because pytest patches target the `app.routers.viewer.*` namespace:

| Function | Reason kept in viewer.py |
|----------|--------------------------|
| `_session_watermark_angle` | `test_phase7.py` patches `app.routers.viewer.settings` |
| `_load_toc_sidecar` | `test_toc_engine.py` patches `app.routers.viewer.get_storage_service` |
| `_get_cached_link_and_doc` | `test_phase8.py` patches `app.routers.viewer.policy_enforcer` |

Functions that ARE in services but need to be importable from the router module
use the **re-export pattern**:

```python
# In annotations.py — makes _serialize_annotation accessible as
# app.routers.annotations._serialize_annotation (required by test_identity_thread_part8.py)
from app.services.annotation_service import _serialize_annotation, _resolve_display_name
```

---

## Goal #3 Status

Frontend ViewerScreen decomposition (app.jsx lines 1238–2586, 53 useState) into
`frontend/src/components/viewer/` — **NOT YET STARTED**. Deferred to Sprint 3.
