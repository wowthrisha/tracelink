# API Maturity Report — Sprint V7.0 (Phase 4)

REST-convention consistency audit across all 16 backend routers — pagination, filtering, sorting, error responses, HTTP status codes, validation, authorization, audit logging, analytics logging. This is a pure API-design audit, distinct from the prior sprint's UI-to-API contract mapping.

## Already consistent (no findings)

- **Error response shape**: `HTTPException(detail=...)` universally, 200+ call sites across all 16 files — no hand-rolled error dict anywhere.
- **Resource naming at the collection level**: consistently plural nouns (`/api/documents`, `/api/orgs`, `/api/groups`, `/api/webhooks`, `/api/api-keys`), with consistent nesting for org-scoped sub-resources.
- **Analytics event logging** (`viewer.py`'s 3 call sites): identical call shape, same placement relative to the response — the one dimension found fully consistent end-to-end.
- **Audit logging transaction placement**: reconfirmed this sprint for the most recently-added call sites (`webhooks.py`, `storage.py`) — audit call before `db.commit()`, same transaction, matching every existing site.

## Real inconsistencies found

| Dimension | Finding | Severity |
|---|---|---|
| **Pagination — coverage** | Only 4 of ~11 list endpoints paginate at all (`admin.py` audit log, `analytics.py` ×3). Unbounded: `documents.py:list_documents`, `groups.py:list_groups`, `links.py:list_links`, `orgs.py:list_orgs`, `orgs.py:list_members`, `webhooks.py:list_webhooks`, `api_keys.py:list_api_keys`. | **Highest** — also flagged as a scalability risk in `SCALABILITY_REVIEW.md`; this is the single most consequential API-maturity gap. |
| **Pagination — defaults/caps** | Where it does exist, four different default/cap combinations: 50/500, 100/500, 50/500 (three different endpoints in `analytics.py` alone don't even agree with each other), and 50/200 (`webhooks.py`). | High |
| **Filtering vocabulary** | No shared filter-param convention. `date_from`/`date_to` appears exactly once (`admin.py`) and is never reused, including on `analytics.py`'s structurally-similar `/events` endpoint, which has no date filter at all. `page-heatmap`'s `document_id` is inconsistently required vs. the optional pattern used elsewhere. | Medium |
| **Sorting** | No endpoint anywhere exposes client-controlled sort order — all ordering is hardcoded server-side. Internally consistent (uniformly absent) but a real maturity gap, especially for audit-log and webhook-delivery endpoints that are prime candidates for user-controlled sort. | Medium |
| **Validation — typed vs. raw** | Only 3 of 16 routers use typed Pydantic schemas; 14 endpoints across 7 files accept raw `body: dict`. `orgs.py` alone has 5 untyped write endpoints. (Also flagged in `CODE_STANDARDIZATION.md` as the top backend maintainability gap — same finding, two angles.) | High |
| **HTTP status codes — DELETE** | `links.py`'s two DELETE endpoints return 200+body against 8 other DELETE endpoints across the codebase that correctly return 204/no-body. | Medium |
| **Router structure** | `annotations.py` and `storage.py` don't use `APIRouter(prefix=...)` like the other 14 files — hardcoded full paths instead. `annotations.py` additionally spans two resource families in one file. | Low-medium |
| **Action-endpoint convention** | RPC-verb-suffix (`/rotate`, `/reprocess`, `/test`, `/domain/verify`) and PATCH-on-resource (`/resolve`) both exist for the same conceptual "action" semantics, no documented rule for which to use when. | Low |

## What "endpoint feels different from another" looks like in practice

A consumer building against this API today would need to know, endpoint by endpoint: whether the list they're calling paginates at all, and if so what the default page size is; whether the resource they're creating validates via a typed schema (giving them a clear 422 on a bad field) or a raw dict (giving them a possibly-confusing runtime error instead); and whether a delete they issue returns an empty 204 or a 200 with a body they need to check for `deleted: true`. None of these are security or correctness bugs — every endpoint works — but collectively they mean the API doesn't yet "feel like one product," which is exactly the maturity bar this phase is measuring against.

## Recommended sequencing (not implemented this sprint)

1. Pagination coverage — highest leverage, ties directly to a real scalability risk, not just a style question.
2. Typed-schema migration for the 7 raw-`dict` routers — improves both API maturity and developer safety simultaneously.
3. Standardize pagination defaults/caps to one convention.
4. Fix the two `links.py` DELETE status codes.
5. Router-structure cleanup (`annotations.py` prefix/scope split, `storage.py` prefix).
6. Establish and document a filtering/sorting-parameter convention for future endpoints, rather than retrofitting existing ones immediately.

None of the above were implemented this sprint — every one is a genuine API-contract change (even the "small" ones, like adding a `response_model` or switching a raw-dict endpoint to a typed schema, can change validation-error shapes for existing consumers), which this sprint's own governance ("do not redesign working architecture," documentation-only phase) correctly keeps out of scope.
