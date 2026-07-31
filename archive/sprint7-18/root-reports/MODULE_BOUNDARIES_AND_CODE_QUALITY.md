# Module Boundaries & Code Quality — Sprint V6.0 (Phases 2–3)

## Module boundaries

**Cross-layer dependency violations**: none found. Full import-graph check across `backend/app/{models,services,routers}` confirms models never import services/routers, and services never import routers — the intended layering holds cleanly.

**Circular dependencies**: none in backend routers/services/models, none in frontend local-relative imports, and (checked specifically this sprint) no `frontend/src/hooks/*.js` imports from `frontend/src/screens/*.jsx` — hooks never depend on the screens that use them.

**Shared mutable state**: none found. `usePageLoader.js`'s `pageCache` is a `useRef` scoped correctly inside the hook, not a module-level leak.

### Business logic living in routers (should be in services)

| Finding | Status |
|---|---|
| `documents.py:_check_upload_quota` — full billing-plan quota rule inline in the router | 📝 Documented — moving this is a real improvement but touches the upload hot path; deferred as a follow-up rather than risked this sprint. |
| `documents.py:upload_document` (~180 lines) — group/org/parent-version resolution, retention computation, storage upload, and task dispatch all inline | 📝 Documented — see Large Functions below; a genuine split candidate, not attempted this sprint (high blast radius, needs dedicated test coverage per extracted piece). |
| `orgs.py:verify_custom_domain` — DNS TXT-record verification logic in the router | 📝 Documented — self-contained, low-risk to move, just not prioritized over correctness fixes this sprint. |
| `orgs.py` — "last owner" protection duplicated across `update_member_role` and `remove_member` | ✅ **Fixed** — extracted `ensure_not_last_owner(db, org_id)` into `org_service.py`, both call sites now use it. |
| `links.py:_validate_ip_allowlist`, `_get_base_url_for_doc` — validation/domain-resolution logic in the router | 📝 Documented, not moved. |
| `links.py:_link_to_summary`'s `is_active` computation **duplicated** `link_service.py`'s `validate_link()` revoked/expired logic — two independent sources of truth for the same rule, and they had subtly different edge-case behavior at the exact expiry instant | ✅ **Fixed** — extracted a pure `is_link_active(link, now)` predicate into `link_service.py`, matching `validate_link()`'s actual enforcement semantics exactly (not the summary's slightly-off version); `_link_to_summary` now calls it. |
| `webhooks.py` — per-user webhook cap (`_MAX_WEBHOOKS_PER_USER`) enforced inline instead of in `webhook_service.py` | 📝 Documented, not moved. |

### Presentation logic in services

`viewer_profile.py:derive_display_name` and `annotation_service.py:_resolve_display_name` generate UI-facing copy ("Document Owner", "Anonymous Viewer") server-side. **Not a bug** — this copy is also needed by CSV exports which must render server-side, so it can't simply move to the frontend without duplicating it there too. Documented as intentional shared formatting, not flagged for change.

### Frontend components bypassing their owning screen/hook

7 "reusable" components call `window.SecureDocAPI` directly instead of receiving data via props: `PageThumb.jsx`, `TocSidebar.jsx`, `SearchPanel.jsx`, `DocumentPicker.jsx`, `ViewerInfoPanel.jsx`, `QuickShareModal.jsx`, `AccessLog.jsx`. 📝 **Documented as a coordinated major refactor**, not attempted this sprint — fixing all 7 consistently means threading fetch/callback props through several screens at once. `QuickShareModal.jsx` and `AccessLog.jsx` are the smallest, lowest-risk starting points if this is picked up later.

### Fan-in / fan-out

High fan-in (`viewer_cache.py`: 11 backend files, `page_cache.py`: 9, `components/atoms.jsx`: 22 frontend files, `utils/viewer.js`: 14) is appropriate — these are genuinely shared low-level utilities matching their documented single responsibility, not overloaded god-functions.

High fan-out (`documents.py`: 35 internal imports, `viewer.py`: 25, `ViewerScreen.jsx`: 27) — consistent with the business-logic-in-router findings above; reducing it follows naturally from those extractions rather than being a separate fix.

---

## Code quality

### Large functions/components

| Function/Component | Size | Verdict |
|---|---|---|
| `documents.py:upload_document` | ~180 lines | Real SRP violation — validation, ID resolution, storage, retention, dispatch all inline and independently testable. Not split this sprint (high-traffic endpoint, needs careful test coverage per extracted piece). |
| `viewer.py:download_document` | ~155 lines | Real violation — reimplements link/session/permission validation inline instead of reusing existing cached-lookup/active-check helpers, compounding the `links.py` duplication found in Module Boundaries above. |
| `viewer.py:get_page` | ~110 lines | Borderline — a single cache-first pipeline, but watermarking and analytics logging are logically separable. |
| `reading_analytics_service.py:ingest_batch` | ~220 lines, largest function in the repo | Worth splitting (validation / session upsert / aggregation / complexity update are separable), but the surrounding file already factors out `compute_*` helpers well — this is "large orchestrator," not a monolith. |
| `analytics_service.py:get_document_analytics`/`get_overview` | ~120–140 lines each | Not a real violation — large but cohesive (single job: assemble one payload). |
| `AccessScreen.jsx` | ~900 lines, 53 `useState` calls | Real SRP violation — owns share-link CRUD, feedback moderation, and visual-annotation review as three genuinely distinct feature domains sharing only `docId`. Natural split: `LinksTab`/`FeedbackTab`/`AnnotationsTab`. |
| `ViewerScreen.jsx` | 919 lines, 12 `useState` | Large but cohesive — one continuous render/interaction pipeline, not three domains bolted together. |
| `UploadScreen.jsx` | 466 lines, 24 `useState` | Milder concern — file-drop, quota/plan, group/org, and retention UI mixed, but less severe than AccessScreen. |

**None of these were split this sprint** — every one is a multi-file, test-coverage-dependent restructuring, exactly the category the mission says to document rather than implement. Ranked by value/risk: `AccessScreen.jsx`'s 3-way tab split is the best next candidate (clean natural boundaries, high readability payoff); `upload_document`'s extraction is next (clear separable steps, but higher traffic = higher care needed).

### Duplicate validation (same layer)

`AccessScreen.jsx` reimplements the identical expiry-not-in-past / max-views≥1 checks twice in the same file (`handleSave` at the create-link form, `EditLinkModal.handleSubmit`) with near-identical but not-quite-matching error copy. 📝 Documented — a shared `validateLinkForm()` would remove this drift risk; small and safe, not done this sprint purely due to time, not risk.

### Duplicate/inconsistent permission checks

**Real access-control bug, fixed**: `annotations.py` reimplemented `str(doc.user_id) != str(current_user["user_id"])` inline 10 times — narrower than `documents.py`'s existing `_get_accessible_document()`, which also grants access to org members of org-owned documents. Net effect before the fix: an org member who could view/download a shared org-owned document via `documents.py` got a hard 403 on that same document's annotations/feedback/export endpoints. ✅ **Fixed** — all 10 sites now call the shared `_get_accessible_document()` helper (imported from `documents.py`), closing the gap and unifying on one source of truth. As a side effect, unauthorized access now returns 404 instead of 403 at these 10 endpoints, matching `documents.py`'s existing no-existence-leak convention — one existing test asserted the old 403 and was updated to expect 404, with reasoning recorded inline in the test.

Style variance also found and left as-is (lower value than the access bug): `annotations.py` cast both sides to `str()` before comparing; `documents.py` compares raw UUIDs; several routers bake ownership into the SQL `WHERE` clause instead. Not unified this sprint.

### Audit-logging boilerplate — investigated, mostly not a bug

The code-quality agent flagged `orgs.py` as inconsistently wrapping `log_audit_event()` calls in `try/except: pass` (5 call sites unwrapped) and recommended extracting a `safe_audit_log()` helper. **Verified against source before acting**: `log_audit_event()` (`audit_service.py`) already catches every exception internally and is documented as never raising — the "unwrapped" `orgs.py` sites were never actually at risk, and the wrapped sites elsewhere carry pure redundant boilerplate (~15 call sites). This is real, but it's a readability nit, not a bug, once verified. Fixed the misleading docstring to make the no-raise guarantee explicit ("callers do NOT need to wrap this call"); did **not** do the larger mechanical removal of ~15 redundant try/except blocks across `api_keys.py`/`documents.py`/`links.py` — cosmetic, non-trivial diff size for zero behavior change, lower priority than the real bugs fixed this sprint. Documented as a safe future cleanup.

### Duplicate analytics-logging boilerplate

Only 3 call sites (`viewer.py`), not wrapped in try/except at all (in contrast to audit logging). Noted as an inconsistency in failure-tolerance policy between the two logging types, but with only 3 sites a dedicated wrapper isn't clearly worth it — documented, not changed.

### Response serialization drift

`_org_response`, `_member_response`, `_key_response`, `_group_to_response`, `_ep_response`, `_link_to_summary` each hand-roll their own dict-building convention independently; `documents.py` instead uses Pydantic response models built inline. Three different conventions for the same underlying concern (API response shaping). 📝 Documented — real drift risk (e.g. `DocumentSummary` and `DocumentDetail` are assembled independently rather than one extending the other) but unifying response-building across 6+ routers is a large mechanical change, not attempted this sprint.

### Magic strings/numbers

- Rate-limit strings (`"30/minute"`, `"60/minute"`, etc.) repeated as bare literals across `analytics.py`, `reading.py`, `annotations.py`, `viewer.py` with no named constant.
- Pagination `limit` defaults diverge with no apparent domain reason: `admin.py` uses 50, `webhooks.py` uses 50 (cap 200), `analytics.py` uses both 50 and 100 (cap 500) in different endpoints.
- Document status strings (`"uploaded"`, `"processing"`, `"ready"`, `"error"`) hardcoded across `viewer_service.py`, `viewer.py`, `documents.py` with no shared enum — contrast with `RETENTION_POLICIES`, which *is* correctly centralized in `models/document.py`.

📝 All documented, not fixed — each is a real but low-severity readability/consistency issue; introducing new shared constants across many call sites is exactly the kind of change that risks subtle typos/mismatches if rushed, so it's left for a dedicated pass rather than done under this sprint's time pressure.

### Hidden side effects

`viewer.py:get_page` reads as a page-fetch getter but performs a session-heartbeat DB upsert and commits an analytics event as side effects — not obvious from the name to a caller reasoning about retry-safety. Documented, not changed (the side effects are intentional and load-bearing; the finding is about naming/documentation clarity, not correctness).
