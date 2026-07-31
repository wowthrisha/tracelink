# Module Boundary Report — V18.0 Repository Certification

Architecture, coupling, and consistency audit of `backend/app/` and `frontend/src/`. All findings are source-verified (file:line or tool output cited); nothing here is a general impression without a concrete example.

## 1. Directory structure

**Backend** (`backend/app/`): `routers/` (16 files, one per domain), `services/` (26 files, plus `adapters/` for format-specific document adapters and `toc/` for table-of-contents extraction), `models/` (15 SQLAlchemy models), `schemas/` (only 4 files — document/group/link; most routers inline their own request/response models instead of a shared schema layer), `middleware/` (8 cross-cutting HTTP concerns), `workers/` + `workers/pipeline/` (Celery tasks + format-conversion pipeline), `utils/` (crypto, SSRF guard). All directory names match their contents — no misplaced files found.

**Frontend** (`frontend/src/`): `screens/` (13, page-level), `components/` (17 top-level + `access/`, `analytics/`, `upload/` subdirectories), `hooks/` (8, all correctly `useX.js`-named), `constants/`, `contexts/` (1 file), `utils/` (2 files: `viewer.js`, `feedback.js`). No misplaced hooks or components found.

**One structural exception**: `backend/app/routers/billing.py` has no corresponding `services/billing_service.py`. All Stripe business logic — subscription upsert/cancel, payment-failure handling, direct DB writes — lives in the router itself (`billing.py:32,187,212,234`), unlike every other domain, which keeps business logic in a service and the router thin. Not fixed this sprint (a real refactor, not a hygiene fix); recommended for a dedicated pass — extracting a `billing_service.py` mirroring the other 15 domains' shape. **Effort: Medium. Regression risk: Medium** (Stripe webhook handling is exactly the kind of code where a refactor-introduced subtle bug is expensive — needs a full webhook-replay test pass, not just unit tests).

## 2. Dependency graph

### 2a. Routers → Services (adjacency, module-level + deferred/function-body imports — this codebase uses function-local imports heavily for startup-cost reasons)

| Router | Services it imports |
|---|---|
| `admin.py` | `org_service` |
| `analytics.py` | `analytics_service`, `policy`, `webhook_service` |
| `annotations.py` | `annotation_service`, `annotation_thread_service`, `annotation_export_service`, `viewer_annotation_service`, `viewer_bookmark_service` |
| `api_keys.py` | `audit_service` |
| `documents.py` | `storage`, `adapters`, `rasterizer`, `watermark`, `text_processor`, `retention`, `audit_service`, `viewer_cache`, `page_cache` |
| `links.py` | `link_service`, `viewer_cache`, `audit_service` |
| `notifications.py` | `page_cache` |
| `orgs.py` | `org_service`, `audit_service` |
| `reading.py` | `policy`, `reading_analytics_service` |
| `storage.py` | `retention`, `audit_service` |
| `viewer.py` | `link_service`, `storage`, `watermark`, `analytics_service`, `policy`, `viewer_cache`, `page_cache`, `viewer_service`, `viewer_session_service`, `toc.cache`, `adapters`, `text_processor` |
| `webhooks.py` | `audit_service` |
| `auth.py`, `billing.py`, `groups.py`, `__init__.py` | none |

`documents.py` and `viewer.py` are the two structurally largest consumers (9 and 12 service imports respectively) — both are also on the "large files" list below (§5), which is consistent: high fan-out and high line count usually co-occur.

### 2b. Service → Service (internal service-layer coupling — 23 edges across 26 files, 16 pure leaves with zero outgoing edges)

Highest in-degree (most depended-upon): **`viewer_cache.py`** — 5 incoming edges (from `annotation_service`, `link_service`, `policy`, `retention`, `viewer_service`), zero outgoing edges. This is the service layer's structural hub — a true shared-cache leaf everyone reaches into, appropriately so for a cache-invalidation module.

Highest out-degree (most dependent on others): `annotation_service.py` and `link_service.py`, tied at 4 outgoing edges each.

### 2c. Frontend: screens → hooks, screens → components

All 8 files in `frontend/src/hooks/` are consumed **exclusively by `ViewerScreen.jsx`** — no other screen imports any hook directly. This is architecturally sound, not a smell: the Viewer is the one screen complex enough to warrant hook extraction; the other 12 screens keep their state inline, which is consistent with their lower complexity.

`atoms.jsx` is imported by 9 of 12 screens — the frontend's structural analog to `viewer_cache.py`: a genuine, appropriately-shared foundation component library, not an accidental god-import.

## 3. Cross-module private-boundary violations

**Finding, corrected from the original single-instance report**: importing an underscore-prefixed "private" symbol from a sibling module is not an isolated case (`annotation_service.py:17 → viewer_service._get_session_id`) — it is a **systemic pattern with 10 confirmed instances**, concentrated in two undeclared "internal APIs":

| Importer | Private symbol(s) imported | From | Evidence |
|---|---|---|---|
| `services/annotation_service.py` | `_get_session_id` | `services/viewer_service.py` | `annotation_service.py:17` |
| `services/annotation_thread_service.py` | `_UPLOADER_SESSION_PREFIX`, `_is_uploader_row`, `_resolve_display_name`, `_profile_display_names`, `_serialize_annotation` | `services/annotation_service.py` | `annotation_thread_service.py:13-19` |
| `services/annotation_thread_service.py` | `_parse_filter_date`, `_thread_matches_filters` | `services/annotation_filter_service.py` | `annotation_thread_service.py:20-23` |
| `services/annotation_export_service.py` | `_is_uploader_row`, `_resolve_display_name`, `_profile_display_names` | `services/annotation_service.py` | `annotation_export_service.py:15-18` |
| `services/annotation_export_service.py` | `_parse_filter_date`, `_thread_matches_filters`, `_as_aware_utc` | `services/annotation_filter_service.py` | `annotation_export_service.py:20-24` |
| `services/viewer_annotation_service.py` | `_profile_display_names`, `_serialize_annotation` | `services/annotation_service.py` | `viewer_annotation_service.py:15-18` |
| `routers/annotations.py` | `_resolve_link_and_verify_session`, `_serialize_annotation`, `_resolve_display_name` | `services/annotation_service.py` | `routers/annotations.py:30-33` |
| `routers/annotations.py` | `_serialize_annotation` (again, in-function) | `services/annotation_service.py` | `routers/annotations.py:407` |
| `routers/orgs.py` | `_slugify` | `services/org_service.py` | `routers/orgs.py:17` |
| `routers/viewer.py` | `_check_link_active`, `_check_doc_ready`, `_get_session_id`, `_session_watermark_angle` | `services/viewer_service.py` | `routers/viewer.py:43-50` (already `# noqa: F401`-flagged by whoever wrote it — an acknowledged, not accidental, boundary crossing) |

**Interpretation**: `annotation_service.py` and `annotation_filter_service.py` are functioning as de facto shared internal APIs for the whole annotation subsystem (4 different consumers reach into their underscore-prefixed helpers), and `viewer_service.py`/`org_service.py` each have one similar leak. This isn't necessarily wrong — the helpers genuinely are shared logic — but the underscore prefix signals "module-private" to any reader, which is actively false for these specific names. **Recommendation**: either promote the shared helpers to a public name (drop the leading underscore, since they're evidently part of the real public contract) or extract them into a proper shared module (e.g. `annotation_helpers.py`) that all 4 consumers import from equally, rather than 3 of them reaching into a 4th's implementation details. **Effort: Medium (mostly renames + import updates). Regression risk: Low** (pure renames, no logic change) **if done as a single atomic pass — do not do it piecemeal**, since a partial rename would leave some call sites on the old private name and some on the new public one.

**Important caveat, source-verified during this same investigation**: `services/annotation_service.py` currently has an *uncommitted* working-tree change that introduced the `_get_session_id` import from `viewer_service.py` (row 1 above) — this specific edge was added, not pre-existing, by a change sitting uncommitted in this repo's working tree right now. Whoever owns that in-progress diff should see this finding before it lands, since it actively creates the exact violation pattern flagged here.

## 4. Naming consistency

Mixed `fetch_*` vs. `get_*` prefixes for read operations, even within the same file: `backend/app/services/page_cache.py` has both `fetch_page_bytes`/`fetch_thumb_bytes` (lines 259, 293) and `get_redis_page_cache` (line 220). The `fetch_*` convention clusters in viewer/annotation services; `get_*` is used everywhere else (`org_service.py`, `storage.py`, `toc/cache.py`, `adapters/registry.py`). **Not a functional issue, purely a readability/consistency one. Effort: Low but wide-reaching** (touches every call site of the renamed function) — better suited to a dedicated "naming pass" than folding into this sprint.

## 5. Large files / "god" candidates

| File | Lines | Note |
|---|---|---|
| `backend/app/services/reading_analytics_service.py` | 1304 | Largest backend file. Internally section-organized (not a disorganized dump), but genuinely doing more than any other single service — analytics ingestion, insight generation, and summary endpoints all in one file. One function, `ingest_batch` (lines 708-925, 218 lines), is the only function in the entire backend crossing the 200-line threshold. |
| `backend/app/routers/viewer.py` | 962 | 10 routes handling rendering, thumbnails, TOC, download, search, and word-positions with heavy inline logic (~90 lines/route vs. `documents.py`'s ~50 lines/route). |
| `backend/app/routers/documents.py` | 724 | — |
| `backend/app/routers/orgs.py` | 611 | — |
| `backend/app/main.py` | 555 | — |
| `backend/app/routers/annotations.py` | 549 | — |
| `frontend/src/screens/AccessScreen.jsx` | 1005 | Largest frontend file by a wide margin. 52 `useState` calls (next-highest is `UploadScreen.jsx` at 24). Also the file with the most internal duplication found this sprint (§ in `DEAD_CODE_REPORT.md`). |
| `frontend/src/screens/ViewerScreen.jsx` | 922 | Consumes all 8 custom hooks (§2c) — the size is largely a consequence of orchestrating that many concerns in one screen, which is architecturally reasonable for the single most complex screen in the app, not automatically a smell. |
| `frontend/src/hooks/useReadingAnalytics.js` | 511 | — |

None of these were split apart this sprint — a file-split is a functional/UI-neutral refactor in principle, but in practice touching a 1000-line file with pre-existing uncommitted changes and 52 pieces of state is exactly the kind of task that needs its own dedicated, carefully-tested sprint, not a certification-pass side effect. Flagged with concrete numbers so a future sprint can scope the work accurately.

## 6. API consistency

- **List-endpoint response shapes**: consistent — every list endpoint returns a domain-named wrapper object (`{"documents":[...]}`, `{"groups":[...]}`, `{"links":[...]}`, `{"webhooks":[...]}`, `{"api_keys":[...]}`, `{"organizations":[...]}`), never a bare array. No inconsistency found here, correcting an earlier assumption that this might be an issue.
- **Auth-dependency inconsistency, real**: `documents.py`, `groups.py`, `links.py`, `webhooks.py`, `analytics.py`, `reading.py`, `storage.py` use scope-based `Depends(require_scope(...))` (API-key callers must hold the specific scope); but `api_keys.py` (all 6 routes), `orgs.py` (all 12 routes — including member invite/role-change/removal), and `billing.py` (all 3 routes) use only `Depends(get_current_user)` with no scope check at all. This means an API key with zero scopes granted can still invite/remove organization members and manage other API keys, as long as it authenticates — a genuine, real permission-boundary gap, not a style inconsistency. **This is the most security-relevant finding in this report.** Recommend filing as a backlog item (candidate: extend `require_scope` coverage to `orgs.py`/`api_keys.py`/`billing.py`, mirroring the existing pattern) rather than fixing inline during a certification sprint, since it changes real authorization behavior for API-key callers and needs its own test-and-verify cycle, ideally with a security-focused reviewer.
- **Error-handling inconsistency, minor**: `reading_analytics_service.py:739,746` returns ad hoc `{"error": ...}` dicts (manually translated by the router into an `HTTPException`), while the sibling `get_document_summary` method in the same class returns `None` and lets the router raise 404 directly — two different error-signaling conventions in one file. Low risk, low urgency; a good candidate for the next time that file is touched for an unrelated reason.

## 7. Configuration centralization

**Real bypass found**: `USE_DEMO_STORAGE` is read via raw `os.getenv`/`os.environ` in 5 separate files (`database.py:41`, `main.py:141,392,409`, `routers/documents.py:272,321`, `workers/celery_app.py:7`) instead of being a field on the centralized `Settings` object in `config.py` (which is otherwise comprehensive — 213 lines covering everything else). This is the one config value bypassing the app's own established pattern. **Effort: Low** (add one field to `Settings`, update 5 call sites to read `settings.use_demo_storage`). **Regression risk: Low-medium** — `USE_DEMO_STORAGE` gates storage-backend selection, so this needs a real test-storage-path verification after the change, not just a lint pass.

## 8. Logging consistency

37+ files correctly use `logger = logging.getLogger(__name__)`. 5 diverge: `database.py:7`, `main.py:215`, `telemetry.py:19`, `billing.py:26` use `_log = logging.getLogger(<hardcoded string>)`, and `middleware/request_id.py:20` uses `logger = logging.getLogger("securedoc.access")`. Cosmetic — doesn't affect log routing/filtering since all still flow through the same root logger config, just a naming-convention drift. Low priority.

## Not fixed this sprint — summary of why

Every finding in this report that wasn't already covered by `DEAD_CODE_REPORT.md`'s "fixed" list represents either (a) a genuine architectural/refactor decision requiring product or security sign-off (billing-in-router, the API-key scope gap, the `fetch_*`/`get_*` naming split, the private-boundary consolidation), or (b) a change to a large, actively-changing file where the regression risk of a rushed edit outweighs the certification value of fixing it same-sprint (the two "god files"). None are silently dropped — each has a concrete effort/risk estimate above so a future sprint can pick them up with full context.
