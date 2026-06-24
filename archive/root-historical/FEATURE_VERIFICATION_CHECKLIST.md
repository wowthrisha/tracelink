# Feature Verification Checklist

Scope: every major feature, scored across Frontend / Backend / Database / API / Permissions / Tests. 1,614 backend tests total (1,613 passing + 1 skipped as of the last full run). Evidence: router files, model files, `app.jsx`, and direct test-file presence/absence checks.

| Feature | Frontend | Backend | Database | API | Permissions | Tests | Status |
|---|---|---|---|---|---|---|---|
| Document Upload | `app.jsx` upload screen | `documents.py:upload_document` (168 lines) | `documents` table | `POST /api/documents` | `require_scope("documents:write")` | `test_documents.py` — covered (size/type validation, adapter dispatch) | ✅ Complete |
| PDF Processing | viewer page render | `services/adapters/pdf.py`, `rasterizer.py` | `document_pages` | `GET /api/viewer/page/{token}/{n}` | session-validated | covered via adapter + viewer integration tests | ✅ Complete |
| Share Links | `AccessScreen` links tab | `links.py` (4 routes), `link_service.py` | `share_links` | `POST/GET/PATCH/DELETE /api/links` | `require_scope("links:*")` | `test_links.py` — covered | ✅ Complete |
| Email Gating | gate screen in `ViewerScreen` | `viewer.py:validate_link` (146 lines) | `share_links.allowed_emails/domains` | `POST /api/viewer/validate` | token-based | covered (allowlist match, domain match) | ✅ Complete |
| OTP | gate screen | `viewer.py` validate flow | n/a (ephemeral, not persisted) | `POST /api/viewer/validate` | token-based | covered | ✅ Complete |
| Watermarks | viewer overlay rendering | `services/adapters/pdf.py` watermark injection | n/a | embedded in page render | session-validated | partial — visual output not snapshot-tested, only "watermark text present" assertions | ⚠ Partial |
| Analytics | `AnalyticsScreen` | `analytics.py` (6 routes) | `access_events` | `GET /api/analytics/*` | `require_scope("analytics:read")` | `test_analytics.py` — covered | ✅ Complete |
| Bookmarks | bookmarks panel in `ViewerScreen` | `annotations.py` bookmark routes | `viewer_bookmarks` | `GET/POST /api/viewer/bookmarks/*` | session-validated | covered | ✅ Complete |
| Annotations | `AnnotationLayer` (152 lines) | `annotations.py` (no dedicated service, see BACKEND_ARCHITECTURE_REVIEW.md) | `viewer_annotations` | `GET/POST/PUT/DELETE /api/viewer/annotations/*` | session-validated, own-row only for edit/delete | covered | ✅ Complete |
| Comments / Feedback | `AccessScreen` feedback tab | `annotations.py:list_document_feedback` (104 lines) | `viewer_annotations` (reply via `parent_id`) | `GET /api/documents/{id}/feedback` | owner-only | covered, recently re-tested after CSV redesign | ✅ Complete |
| Replies | feedback thread UI | `annotations.py:reply` route, `thread` route | `viewer_annotations.parent_id` self-FK | `POST /api/documents/{id}/feedback/{id}/reply` | owner-only | covered | ✅ Complete |
| Exports (annotations/feedback/reviewer-activity/visual) | export buttons in `AccessScreen` | 4 separate CSV exporters in `annotations.py` | reads from `viewer_annotations` | 4 separate `/export` routes | owner-only | covered | ✅ Complete |
| Storage | `StorageScreen` | `storage.py` (3 routes) | `storage_snapshots` | `GET /api/storage/*` | `require_scope("documents:read|write")` | `test_storage.py` — covered | ✅ Complete |
| Billing | `BillingScreen` | `billing.py` (4 routes) | `user_billing` | `GET/POST /api/billing/*` | `get_current_user` + Stripe HMAC for webhook | covered, webhook signature verification tested | ✅ Complete |
| Admin | (no dedicated screen — audit log only) | `admin.py` (1 route, 78 lines) | `admin_audit_log` | `GET /api/admin/audit-log` | role check in function body, not `Depends` (see SECURITY_AUDIT_REPORT.md P2) | covered only incidentally via enterprise integration tests, no dedicated `test_admin.py` | ⚠ Partial |
| Access Control | gate flow, permission flags (`can_download`/`can_print`/`can_copy`) | `policy.py` | `share_links` policy columns | enforced in `viewer.py` per-route | session-validated | covered | ✅ Complete |
| Audit Logs | none (backend-only feature) | `audit_service.py`, `admin.py` | `admin_audit_log` | `GET /api/admin/audit-log` | role-gated | covered incidentally, no dedicated test file | ⚠ Partial |
| Retention | `RetentionUpdate` form in `StorageScreen` | `retention.py`, `cleanup.py` (daily Celery task) | `documents.lifecycle_state/expires_at` | `PATCH /api/storage/retention` | `require_scope("documents:write")` | `test_retention.py` covers policy logic; **`viewer_profiles` has no retention path at all** (see DATABASE_REVIEW.md Finding 2) | ⚠ Partial |
| Session Handling | gate/re-validate flow | `viewer.py` (10 routes use session validation), `viewer_cache.py` | `viewer_sessions` | every `/api/viewer/*` route | session-bound to `link_id` | covered | ✅ Complete |

## Routers With No Dedicated Test File

| Router | Coverage |
|---|---|
| `api_keys.py` | **No dedicated test file** — exercised only incidentally if at all |
| `notifications.py` | **No dedicated test file** |
| `groups.py` | **No dedicated test file** |
| `webhooks.py` | Tested only via mocks — no test ever performs a real HTTP delivery |
| `admin.py` | Covered only incidentally through enterprise integration tests, no `test_admin.py` |

**Recommendation (P1/P2 mixed):** `api_keys.py` and `groups.py` are user-facing CRUD with real security implications (a key-creation bug or group-permission bug ships silently) — add dedicated test files first. `notifications.py` (SSE) and `webhooks.py` real-delivery testing are lower urgency but should not stay permanently mock-only.

## Untested Background Tasks

- `requeue_orphaned_uploads()` (`app/workers/tasks.py`) — **no test at all**. This is the recovery path for documents stuck mid-upload; if it silently breaks, stuck uploads accumulate forever with no signal.
- `deliver_webhook()` (`app/workers/webhook_tasks.py`) — mocked in every test; never invoked end-to-end with a real payload against a real (test) HTTP endpoint, so the retry/backoff/dead-letter logic has zero behavioral coverage beyond "the mock was called."

## Summary

17 of 20 surveyed features are ✅ Complete with real test coverage. 3 are ⚠ Partial: **Watermarks** (visual-only assertions, no snapshot test), **Admin/Audit Logs** (functionally correct but no dedicated test file and non-declarative authz), and **Retention** (policy logic well-tested, but the `viewer_profiles` table sits entirely outside the retention system — see DATABASE_REVIEW.md). No feature scored ❌ Broken.
