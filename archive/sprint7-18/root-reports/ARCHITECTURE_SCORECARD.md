# Architecture Scorecard — Sprint 7.0

Full repo-wide sweep of `backend/app/**` and `frontend/src/**`: duplicated logic, circular dependencies, permission consistency, audit/analytics logging consistency, N+1 queries, and other maintainability risks. Every finding below is backed by a file:line citation read directly from source.

## Circular dependencies — ✔ Clean

Import graph built and DFS'd across all of `backend/app/**` (routers → services → models) and `frontend/src/**` (local relative imports). No cycles found in either.

## Duplicated logic

| Finding | Status |
|---|---|
| `_get_session_id()` byte-identical in `annotation_service.py:23-27` and `viewer_service.py:53-58` | ✅ **Fixed** — `annotation_service.py` now imports it from `viewer_service.py` instead of reimplementing it (confirmed no circular-import risk before making the change). |
| `admin.py:44-51` manually reimplemented the "get membership → check role_gte → 403" pattern that already exists as `org_service.require_role()` — and had drifted: it always returned the same error text regardless of whether the caller wasn't a member at all vs. had an insufficient role. | ✅ **Fixed** — `admin.py` now calls the shared `require_role()` helper. Behavior-equivalent for all currently-passing tests (verified — no test asserted on the old exact error string) and produces more accurate error messages as a side effect. |
| `fmtDate(iso)` — byte-identical in `OrgsScreen.jsx`, `AccessScreen.jsx`, `ApiKeysScreen.jsx`, `WebhooksScreen.jsx` | ✅ **Fixed** — consolidated into `frontend/src/utils/viewer.js`, all four screens now import the shared version. |
| `_fmtMs(ms)` — same name, **diverging** behavior between `ReadingStatusBar.jsx:13-22` (handles hours, `ms<0` invalid) and `InsightsModal.jsx:16-22` (no hour handling, `ms<=0` invalid) | 📝 **Documented, not fixed** — both are private, file-local helpers; consolidating risks a small display behavior change (exact-zero formatting) in a modal I didn't have room to manually verify against a live account this sprint. Flagged for a follow-up pass. |
| `TabBtn` naming collision — an unrelated private component in `InsightsModal.jsx:51-61` and the shared exported `components/access/TabBtn.jsx` share a name but not props/behavior | 📝 **Documented, not fixed** — confusing but not a bug; renaming touches call sites for marginal benefit, left alone. |

## Permission consistency

| Finding | Status |
|---|---|
| `groups.py` never used `require_scope` — every endpoint (including all mutations) only checked `Depends(get_current_user)`. Since `require_scope` is the only place that inspects an API key's `scopes`, an API key scoped only to `documents:read` could still mutate document-group membership — a real boundary bypass relative to `documents.py`'s equivalent data. | ✅ **Fixed** — all 7 `groups.py` endpoints now use `require_scope("documents:read")` or `require_scope("documents:write")`, matching the convention already used in `documents.py`/`links.py`/`webhooks.py`. Zero behavior change for JWT (browser) users — `require_scope` only restricts `auth_method == "api_key"` callers; verified via the existing regression suite (94/94 relevant tests still pass). |
| `annotations.py`'s document-owner endpoints (list/export annotations, feedback list/reply/resolve/export, visual annotations) all use bare `get_current_user`, never `require_scope`, despite reading/exporting data comparable in sensitivity to what `documents.py` gates. | 📝 **Documented, not fixed** — same class of fix as groups.py but touches ~8 endpoints across a file I didn't have full regression coverage confidence to sweep safely in the time available this sprint. Flagged as the next candidate for the same treatment. |
| `resolve_annotation` (viewer-token-based, `/api/viewer/annotations/{token}/{id}/resolve`) has no per-viewer ownership check — any session on the link can resolve *any* annotation on it, unlike the stricter same-session-only check on delete/update. The route's own comment claimed it was "uploader-facing," which is false — a real, separately-authenticated `resolve_feedback` endpoint (`/api/documents/{doc_id}/feedback/{annotation_id}/resolve`, properly gated on `doc.user_id == current_user`) already exists for that purpose. | ✅ **Fixed (documentation only)** — corrected the misleading comment rather than tightening the permission check itself: this could be intentional collaborative-review behavior (any reviewer can mark a shared thread resolved) rather than a bug, and I didn't have enough context to safely change actual authorization behavior without risking a regression in a real product workflow. Comment now accurately states this route is *not* owner-restricted and points at the endpoint that is. **Flagged for a product/security decision**, not silently changed. |

## Audit logging consistency

`log_audit_event()` is called from `api_keys.py`, `links.py`, `orgs.py` fully, and `documents.py` (delete only, before this sprint).

| Finding | Status |
|---|---|
| Document upload had no audit entry, while document delete did — an asymmetry given upload is the more common and arguably more security-relevant event (who put what into the system). | ✅ **Fixed** — added `document.uploaded` audit logging to `documents.py:upload_document`, and registered the new event type in `AUDIT_EVENT_TYPES` (`models/audit.py`) so it's filterable in the Audit Log UI, matching the existing `document.deleted` pattern exactly (same try/except-swallow-on-failure convention). |
| No audit logging at all on: `reprocess_document`, `extract_sidecars`, every `annotations.py` mutation, every `groups.py` mutation, every `webhooks.py` mutation (webhook endpoints point at externally-controlled URLs — arguably the most security-relevant of this list), `storage.py:update_retention`, `orgs.py:verify_custom_domain`. | 📝 **Documented, not fixed** — this is a real, fairly large list (~15 endpoints). Adding audit logging to all of them mechanically is low-risk in isolation but a large surface to change and verify in one sprint; picked the single highest-value gap (document upload) to fix now and documented the rest as a prioritized follow-up list, ranked: webhooks (external URL exposure) > groups/annotations > storage retention > domain verify. |

## Analytics/event logging consistency

`analytics_svc.log_event()` covers page view, download, and text-chunk fetch in `viewer.py`, but not `get_thumb`, `get_toc`, `search_document`, `get_document_links`, or `get_word_positions` — search in particular seems like a meaningful signal being silently dropped. 📝 **Documented, not fixed** — lower urgency than the audit-logging gaps above (this is product-analytics completeness, not a security/compliance concern); left for a future analytics-completeness pass.

## N+1 / unnecessary queries

| Finding | Status |
|---|---|
| `groups.py:assign_documents_to_group` issued one `SELECT Document WHERE id=...` per document ID in a loop, instead of a single batched query — notable because the sibling `list_groups` in the same file already demonstrates and comments the correct batched pattern two functions above it. | ✅ **Fixed** — rewritten to a single `WHERE Document.id.in_(doc_uuids)` query. |
| `reading_analytics_service.py:795-811` — the `/api/reading/batch` ingestion path issues one `SELECT PageReadingEvent` per item in the batch instead of pre-fetching all existing rows for the batch's `(session_id, page_number)` set in one query. This is the literal batch-ingest hot path. | 📝 **Documented, not fixed** — higher risk to touch without dedicated load-testing (hot ingestion path, called on every reading-analytics flush); flagged for a follow-up with proper before/after query-count verification rather than a same-sprint blind rewrite. |
| `cleanup.py:186-204` also loops per-document, but is explicitly commented as the SQLite-only test fallback, not a production path. | ✔ Not a concern — confirmed via the code's own comment. |

## Repository health (imports, dead code)

See `REPOSITORY_HEALTH.md` for the full sweep; the two items with architectural relevance are cross-referenced here: `documents.py`/`webhooks.py`/`storage.py`/`orgs.py` each had one unused import (all fixed), and the `require_scope` fixes above incidentally made `documents.py`'s formerly-unused `get_current_user` import fully unused too (also removed).

---

## Scorecard summary

| Dimension | Result |
|---|---|
| Circular dependencies | Clean |
| Duplicated logic | 3 of 5 findings fixed; 2 documented (low-risk, low-value to force this sprint) |
| Permission consistency | 1 of 3 findings fixed (groups.py scope enforcement — the clearest real bypass); 2 documented for a follow-up pass |
| Audit logging | 1 of 2 findings fixed (highest-value gap closed); remainder prioritized and documented |
| Analytics logging | Documented, not fixed (lowest urgency of all findings) |
| N+1 queries | 1 of 2 fixed (the safe one); 1 documented (hot-path, needs load-test-verified fix) |
