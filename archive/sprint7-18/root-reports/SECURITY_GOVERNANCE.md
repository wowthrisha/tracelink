# Security Governance — Sprint V6.0 (Phase 5)

Reviewed: authentication, authorization, tenant/org isolation, audit coverage, rate limiting, share links, viewer permissions, API keys, webhooks, storage, background workers. Per this sprint's own rule, **no partial architectural migrations were implemented** — AUTH-006 (session token storage) remains fully deferred, unchanged from `SECURITY_HARDENING_PLAN.md`/`SECURITY_STATUS.md`.

## Authentication

Unchanged this sprint. JWT-via-Supabase for the SPA, API-key (`sd_...`) for programmatic access, both resolved through `get_current_user`/`require_scope` in `backend/app/auth.py`. No findings.

## Authorization — real bugs found and fixed

| Finding | Status |
|---|---|
| `annotations.py` reimplemented ownership checks inline 10 times, narrower than the shared `documents.py:_get_accessible_document()` — org members who could view a shared org-owned document via `documents.py` were wrongly 403'd on that same document's annotations/feedback/export endpoints | ✅ **Fixed** — all 10 sites now use the shared, org-aware helper. Full detail in `MODULE_BOUNDARIES_AND_CODE_QUALITY.md`. |
| `groups.py`'s 7 endpoints (including all mutations) used bare `Depends(get_current_user)` instead of `Depends(require_scope(...))`, unlike every sibling router (`documents.py`, `links.py`, `webhooks.py`) — an API key scoped only to `documents:read` could still mutate group membership, a real permission-boundary bypass for API-key callers | ✅ **Fixed** (prior sprint, reconfirmed clean this sprint — no regression). |
| Org member self-removal was broken for non-admin roles, contradicting the code's own documented intent (`orgs.py`) | ✅ **Fixed** (prior sprint, reconfirmed, 2 regression tests). |
| `resolve_annotation` (`/api/viewer/annotations/{token}/{id}/resolve`) allows any session on a share link to resolve *any* annotation on it, with no per-viewer ownership check — unlike the stricter same-session-only check on delete/update, and despite a comment claiming it was "uploader-facing" (false — a separate, correctly owner-gated `resolve_feedback` route exists for that). | 📝 **Documented, not changed** — this could be intentional collaborative-review behavior (any reviewer marks a shared thread resolved) rather than a bug; tightening it without product/security sign-off risks breaking a real workflow. The misleading comment was corrected to describe actual behavior; the permission question itself is flagged here for a deliberate decision. |

## Tenant / organization isolation

- `orgs.py`'s permission model is uniform across all 11 org-scoped endpoints — every one resolves the caller's membership via the shared `require_role()`/`_get_org_and_member()` helpers; no endpoint skips the check (confirmed by direct read of every route this sprint and the prior one).
- **Real data-integrity gap, documented not fixed**: deleting an organization does not cascade-delete or block deletion of its documents — `Document.org_id` has no `ForeignKey` constraint at all (unlike `group_id`/`parent_document_id` on the same model), so org-scoped documents are silently orphaned. The delete-org confirmation's copy ("Members will lose access") is not fully accurate — the deleting owner and each document's original uploader retain access via the separate ownership check. This needs a product decision (cascade-delete vs. block vs. reassign), not an engineering guess — same class of open decision as the account-deletion proposal from a prior sprint.
- API keys and webhooks are correctly **not** org-scoped at all (both key off `user_id` only) — by design, not a gap, since org-delete correctly leaves them untouched.

## Audit coverage

Consistent, real gaps found and the highest-value ones closed:

| Endpoint class | Before | After |
|---|---|---|
| Document upload | Not audited (delete was, upload wasn't — an asymmetry) | ✅ Fixed (prior sprint) |
| Webhook create/update/delete | **Zero audit logging on the entire screen/router** | ✅ Fixed this sprint — `webhook.created`/`webhook.updated`/`webhook.deleted` added |
| Document retention-policy change | Not audited despite being the one action on Storage the UI itself treats as consequential enough to confirm | ✅ Fixed this sprint — `document.retention_changed` added |
| API key rotate | Audited, but the event type wasn't registered in the filterable enum — logged but invisible/unqueryable | ✅ Fixed this sprint |
| API key edit (rename/rescope), document reprocess, group CRUD, `annotations.py` mutations, `orgs.py:verify_custom_domain` | Not audited | 📝 Documented, not fixed — see `MODULE_BOUNDARIES_AND_CODE_QUALITY.md` for the full prioritized list; scope was deliberately limited to the highest-value gaps (webhooks, retention) rather than adding audit calls to ~10 more endpoints under time pressure. |

## Rate limiting

Applied consistently via `slowapi`/`limiter` decorators across all public and authenticated mutating endpoints — spot-checked `annotations.py`, `viewer.py`, `webhooks.py`, `links.py`, no gaps found. Rate-limit values themselves are inconsistent magic strings (`"30/minute"` vs `"60/minute"` with no apparent domain logic) — a readability finding, not a security gap; see `MODULE_BOUNDARIES_AND_CODE_QUALITY.md`.

## Share links

`is_link_active()` (revoked/expired/max-views) previously existed as two independently-maintained implementations with a real latent inconsistency at the exact expiry boundary (`link_service.py`'s enforcement vs. `links.py`'s display-flag computation disagreed on whether a link expiring at exactly `now` was active). ✅ **Fixed this sprint** — single shared predicate, matching the actual enforcement semantics.

## Viewer permissions

No new findings this sprint beyond what's already documented in `WORKFLOW_COMPLETENESS.md` (view-limit-reached mislabeling, broken network fallback — both already fixed).

## API keys

Scope-enforcement pattern (`require_scope`) confirmed consistent across `api_keys.py`, `documents.py`, `links.py`, `webhooks.py`, and now `groups.py`. `annotations.py` remains the one router using bare `get_current_user` instead — documented as the next candidate for the same treatment, not applied this sprint (touches ~8 endpoints, wanted dedicated regression coverage rather than a rushed sweep).

## Webhooks

- SSRF re-validation at delivery time (TOCTOU-safe), exponential backoff, per-user cap (20) — all confirmed solid, no findings.
- **Severe, unrelated-to-permissions bug found and fixed**: `app.workers.celery_app.py`'s `include=` list was missing `app.workers.webhook_tasks` entirely. Since a real Celery worker process (`celery -A app.workers.celery_app worker`) only imports task modules listed in `include=` — not modules imported transitively by test code — the `securedoc.deliver_webhook` task was **never registered with the production worker**, meaning `celery_app.send_task("securedoc.deliver_webhook", ...)` calls from `webhooks.py`/`webhook_service.py` would enqueue a task name no worker could execute. **This almost certainly meant every webhook delivery was silently non-functional in production**, despite all the delivery/retry/SSRF logic being correctly written. ✅ **Fixed** — added the missing module to `include=`; verified via `celery_app.loader.import_default_modules()` (which mirrors real worker boot) that all 8 expected task names, including `deliver_webhook`, now register. Added a permanent regression test (`test_worker_tasks.py::TestTaskRegistration`) specifically because this class of bug (correct code, never wired into the actual worker process) is invisible to normal test suites that import task modules directly.

## Storage

Retention-policy changes now both confirmed (prior sprint) and audited (this sprint). No other findings.

## Background workers

Covered above (webhook task registration — the most severe finding of this entire sprint). Also reviewed for fan-out risk: `requeue_orphaned_uploads` (5-minute sweep) dispatches one `process_document.delay()` per orphaned document with no batching — after a worker-fleet outage lasting beyond the orphan threshold, this could burst-dispatch a large number of tasks simultaneously. 📝 Documented in `SCALABILITY_REVIEW.md`, not fixed — needs load-testing to size a safe throttle, not a blind change.

---

## Net assessment

This phase's most consequential finding was not a classic authz/authn bug but a **deployment-wiring defect with security-adjacent consequences**: webhooks are a security-relevant notification channel (e.g., alerting on document access), and their silent failure would have gone undetected by the test suite indefinitely. The two real authorization bugs found (`annotations.py` org-member denial, `groups.py` scope bypass — the latter already fixed last sprint) both erred on the side of *over-restriction* or *under-restriction of API-key callers*, not full unauthorized data exposure to arbitrary users — neither was a critical-severity breach, but both are now closed.
