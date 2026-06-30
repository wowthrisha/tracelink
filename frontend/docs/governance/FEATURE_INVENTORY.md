# Feature Inventory
Production Readiness Audit — Phase 1
Date: 2026-06-22
Source: Direct code reading. Every status is verified from source files.

---

## Summary

| Status | Count |
|---|---|
| Complete (frontend + backend) | 18 |
| Partial (backend complete, no frontend UI) | 7 |
| Partial (frontend complete, backend partial) | 1 |
| Missing (no implementation) | 2 |

---

## Core Document Workflow

### F-01 — Document Upload
- **Frontend Screen:** UploadScreen.jsx
- **Backend Endpoints:** `POST /api/documents/upload`, `GET /api/documents/{id}/status`
- **Database Tables:** `documents`, `document_pages`
- **Status:** ✅ Complete
- **Business Value:** Core workflow. Multi-format: PDF, DOCX, PPTX, XLSX, TXT, MD, LOG
- **Technical Debt:** Upload form has no org_id selector despite org_id being supported server-side

### F-02 — Document Processing Pipeline
- **Frontend Screen:** UploadScreen (status polling)
- **Backend Endpoints:** Celery `process_document` task
- **Database Tables:** `documents` (status enum: uploaded → processing → ready/error)
- **Status:** ✅ Complete
- **Business Value:** Core. Pipeline files: `pdf.py`, `docx_pdf.py`, `pptx_pdf.py`, `xlsx_pdf.py`, `text.py`
- **Technical Debt:** LibreOffice dependency for DOCX/PPTX/XLSX is a heavy production dependency; single point of failure

### F-03 — Document Listing + Groups
- **Frontend Screen:** UploadScreen.jsx (list + group sidebar)
- **Backend Endpoints:** `GET /api/documents`, `GET/POST/PATCH/DELETE /api/groups`, `PUT /api/groups/{id}/documents`
- **Database Tables:** `documents`, `document_groups`
- **Status:** ✅ Complete
- **Business Value:** Essential for multi-document workflows
- **Technical Debt:** None significant

### F-04 — Document Reprocessing + Sidecar Extraction
- **Frontend Screen:** UploadScreen.jsx (reprocess button)
- **Backend Endpoints:** `POST /api/documents/{id}/reprocess`, `POST /api/documents/{id}/extract-sidecars`
- **Database Tables:** `documents`
- **Status:** ✅ Complete
- **Business Value:** Recovery path for failed processing

### F-05 — Document Version History
- **Frontend Screen:** None
- **Backend Endpoints:** `GET /api/documents/{id}/versions`
- **Database Tables:** `documents` (version, parent_document_id columns)
- **Status:** ⚠️ Partial — **Backend GET only; no frontend UI; no API endpoint to create a new version**
- **Business Value:** HIGH — version control is a standard enterprise expectation
- **Technical Debt:** Model has `version` and `parent_document_id` columns; recursive CTE query is implemented; but `POST /api/documents/{id}/versions` to create a version does not exist. Current flow: upload a new file with same name. No version chain is created.

### F-06 — Document Retention + Lifecycle
- **Frontend Screen:** StorageScreen.jsx (retention update)
- **Backend Endpoints:** `PATCH /api/documents/{id}/retention`, `GET /api/storage/dashboard`, `GET /api/storage/forecast`
- **Database Tables:** `documents` (retention_policy, lifecycle_state, expires_at)
- **Status:** ✅ Complete
- **Business Value:** Required for enterprise compliance

### F-07 — Document Deletion
- **Frontend Screen:** UploadScreen.jsx
- **Backend Endpoints:** `DELETE /api/documents/{id}`
- **Database Tables:** `documents` (cascade)
- **Status:** ✅ Complete

---

## Sharing + Access Control

### F-08 — Share Link Creation
- **Frontend Screen:** AccessScreen.jsx
- **Backend Endpoints:** `POST /api/links`, `GET /api/links`, `DELETE /api/links/{id}`, `PATCH /api/links/{id}`
- **Database Tables:** `share_links`
- **Status:** ✅ Complete
- **Business Value:** Core product differentiator
- **Capabilities confirmed:** password protection, allowed_emails list, allowed_domains, IP allowlist, max_views, max_concurrent_sessions, expiry date, per-permission JSON

### F-09 — Document Viewer (PDF)
- **Frontend Screen:** ViewerScreen.jsx + 8 hooks
- **Backend Endpoints:** `GET /api/viewer/gate/{token}`, `POST /api/viewer/validate`, `GET /api/viewer/page/{token}/{page}`, `GET /api/viewer/thumb/{token}/{page}`, `GET /api/viewer/toc/{token}`, `GET /api/viewer/search/{token}`, `GET /api/viewer/words/{token}`, `GET /api/viewer/download/{token}`
- **Database Tables:** `viewer_sessions` (via policy service), `access_events`
- **Status:** ✅ Complete
- **Business Value:** Core. Renders server-rasterized PDF pages; no client-side PDF parsing
- **Technical Debt:** None significant post Sprint 4.2D

### F-10 — Document Viewer (Text/MD/LOG)
- **Frontend Screen:** ViewerScreen.jsx (`isTextDoc` branch)
- **Backend Endpoints:** `GET /api/viewer/text/{token}/{chunk}`
- **Database Tables:** `documents`
- **Status:** ✅ Complete
- **Business Value:** Extends viewer to non-PDF document types

### F-11 — Document Viewer (DOCX/PPTX/XLSX)
- **Frontend Screen:** ViewerScreen.jsx (renders as PDF pages after conversion)
- **Backend Endpoints:** Same as PDF viewer (documents are converted by LibreOffice pipeline)
- **Database Tables:** `documents`, `document_pages`
- **Status:** ✅ Complete
- **Technical Debt:** DOCX/PPTX quality degrades for complex formatting; known limitation

### F-12 — DRM / Download Control
- **Frontend Screen:** ViewerScreen.jsx (via useViewerSession.js)
- **Backend Endpoints:** `POST /api/analytics/events` (blocked action logging)
- **Database Tables:** `access_events`
- **Status:** ✅ Complete
- **Capabilities confirmed:** right-click block, Ctrl+P/S/C/A/U block, print interception (beforeprint), tab blur, CSS user-select none
- **Technical Debt:** Browser-side DRM only; DevTools bypass is inherent; screenshots not preventable

### F-13 — Viewer Authentication Gate
- **Frontend Screen:** ViewerScreen.jsx (AccessGate component)
- **Backend Endpoints:** `GET /api/viewer/gate/{token}`, `POST /api/viewer/validate`
- **Database Tables:** `share_links`, `viewer_sessions`
- **Status:** ✅ Complete
- **Capabilities confirmed:** password gate, email gate, domain gate, IP allowlist

---

## Annotations + Feedback

### F-14 — Viewer Annotations (Visual)
- **Frontend Screen:** ViewerScreen.jsx (AnnotationLayer component)
- **Backend Endpoints:** `GET/POST/PUT/DELETE /api/viewer/annotations/{token}/{page}`, `PATCH /api/viewer/annotations/{token}/{id}/resolve`
- **Database Tables:** `viewer_annotations`
- **Status:** ✅ Complete
- **Capabilities confirmed:** highlight, draw, rectangle, arrow, comment pin, resolve
- **Business Value:** HIGH — differentiates from basic PDF link sharing

### F-15 — Annotation Threads (Feedback)
- **Frontend Screen:** ViewerScreen.jsx (thread modal), AccessScreen.jsx (feedback tab)
- **Backend Endpoints:** `GET /api/viewer/annotations/{token}/{id}/thread`, `POST /api/documents/{id}/feedback/{ann_id}/reply`, `GET /api/documents/{id}/feedback`, `GET /api/documents/{id}/feedback/reviewers`
- **Database Tables:** `viewer_annotations` (parent_id for threading)
- **Status:** ✅ Complete
- **Business Value:** HIGH — enables document review workflows

### F-16 — Annotation + Feedback Export
- **Frontend Screen:** AccessScreen.jsx (export buttons)
- **Backend Endpoints:** `GET /api/documents/{id}/annotations/export`, `GET /api/documents/{id}/feedback/export`, `GET /api/documents/{id}/feedback/export-reviewer-activity`, `GET /api/documents/{id}/annotations` (visual)
- **Database Tables:** `viewer_annotations`
- **Status:** ✅ Complete
- **Technical Debt:** Each export is a separate endpoint; reviewer activity is a third CSV

### F-17 — Viewer Bookmarks
- **Frontend Screen:** ViewerScreen.jsx (TocSidebar bookmark integration)
- **Backend Endpoints:** `GET /api/viewer/bookmarks/{token}`, `POST /api/viewer/bookmarks/{token}/{page}`
- **Database Tables:** `viewer_bookmarks`
- **Status:** ✅ Complete

### F-18 — Access Log + Event Analytics
- **Frontend Screen:** AccessScreen.jsx (AccessLog component), AnalyticsScreen.jsx
- **Backend Endpoints:** `GET /api/analytics/events`, `POST /api/analytics/events`, `GET /api/analytics/overview`, `GET /api/analytics/documents`, `GET /api/analytics/groups`, `GET /api/analytics/page-heatmap`
- **Database Tables:** `access_events`
- **Status:** ✅ Complete
- **Business Value:** HIGH — viewer identity + behavior tracking is the core value prop

---

## Platform Features

### F-19 — Authentication (Login / Signup / Password Reset)
- **Frontend Screen:** LoginScreen.jsx
- **Backend Endpoints:** `POST /api/auth/register`, Supabase direct for signin/reset
- **Database Tables:** Supabase-managed
- **Status:** ✅ Complete
- **Capabilities confirmed:** login, signup, forgot password (Supabase `/auth/v1/recover`), password reset via token (Supabase `/auth/v1/user` PUT), auto-detect reset callback from URL hash

### F-20 — Billing + Plan Management
- **Frontend Screen:** BillingScreen.jsx
- **Backend Endpoints:** `GET /api/billing/status`, `POST /api/billing/checkout`, `POST /api/billing/portal`, `POST /api/billing/webhook`
- **Database Tables:** `user_billing`
- **Status:** ⚠️ Partial — **BillingScreen uses direct `fetch()` calls, not `SecureDocAPI`**. Billing feature-gating (free plan document limit) is correctly implemented in the backend. Stripe integration is conditional on `STRIPE_SECRET_KEY` env var. No Stripe keys = "not configured" UI state.
- **Business Value:** Required for monetization
- **Technical Debt:** BillingScreen bypasses the `SecureDocAPI` abstraction layer; direct fetch in screen component

### F-21 — Storage Dashboard
- **Frontend Screen:** StorageScreen.jsx
- **Backend Endpoints:** `GET /api/storage/dashboard`, `GET /api/storage/forecast`
- **Database Tables:** `documents`, `storage_snapshots`
- **Status:** ✅ Complete
- **Business Value:** Required for enterprise storage compliance awareness

### F-22 — Organizations + Membership
- **Frontend Screen:** None
- **Backend Endpoints:** Full CRUD: `GET/POST /api/orgs`, `GET/PATCH/DELETE /api/orgs/{id}`, `GET/POST /api/orgs/{id}/members`, `PATCH/DELETE /api/orgs/{id}/members/{uid}`, `GET /api/orgs/{id}/domain/token`, `POST /api/orgs/{id}/domain/verify`
- **Database Tables:** `organizations`, `org_memberships`
- **Status:** ⚠️ Partial — **Backend is fully implemented with 4-tier role hierarchy (viewer/editor/admin/owner), custom domain verification, saml_domain field; zero frontend UI**
- **Business Value:** HIGH — required for multi-user enterprise workflows
- **Technical Debt:** Document upload form does not expose org_id selector despite backend supporting it

### F-23 — Webhooks
- **Frontend Screen:** None
- **Backend Endpoints:** Full CRUD: `GET/POST /api/webhooks`, `GET/PATCH/DELETE /api/webhooks/{id}`, `GET /api/webhooks/{id}/deliveries`, `POST /api/webhooks/{id}/test`
- **Database Tables:** `webhook_endpoints` (inferred from webhook_tasks.py)
- **Status:** ⚠️ Partial — **Backend complete with SSRF protection, delivery logs, test endpoint; zero frontend UI**
- **Business Value:** MEDIUM — essential for integrations

### F-24 — Public API Keys
- **Frontend Screen:** None
- **Backend Endpoints:** Full CRUD: `GET/POST /api/api-keys`, `GET/PATCH/DELETE /api/api-keys/{id}`
- **Database Tables:** `api_keys`
- **Status:** ⚠️ Partial — **Backend complete (SHA-256 stored keys, scope enforcement, expiry); zero frontend UI**
- **Business Value:** HIGH — required for any integration story

### F-25 — Admin Audit Log
- **Frontend Screen:** None
- **Backend Endpoints:** `GET /api/admin/audit-log`
- **Database Tables:** `admin_audit_log`
- **Status:** ⚠️ Partial — **Backend implemented with org-scoped access control; zero frontend UI**
- **Business Value:** MEDIUM — required for enterprise compliance/SOC2

### F-26 — SSE Real-Time Notifications
- **Frontend Screen:** None (AppShell does not subscribe to EventSource)
- **Backend Endpoints:** `GET /api/notifications/stream`
- **Database Tables:** None (in-memory pub/sub)
- **Status:** ⚠️ Partial — **Backend streaming endpoint exists with per-user connection limit; zero frontend consumer**
- **Business Value:** MEDIUM — improves UX (real-time processing status, new feedback alerts)
- **Technical Debt:** In-process connection registry; breaks under horizontal scaling

---

## Missing Features (No Implementation)

### F-27 — Email Notifications to Uploader
- **Frontend:** None
- **Backend:** None (no SMTP, no email service integration)
- **Status:** ❌ Missing
- **Business Value:** **CRITICAL** — "notify me when someone views my document" is the #1 use case for DocSend-style products. Without it, uploaders must manually check analytics to know if a document was opened.

### F-28 — Document Watermark (Visual, Per-Viewer)
- **Frontend:** ViewerScreen.jsx has `session.watermark_text` CSS text-shadow overlay — confirmed working
- **Backend:** `watermark.py` service has `apply_viewer_forensic_stamp()` for metadata watermark; visual watermark text comes from session
- **Status:** ✅ Complete (both visual CSS overlay and forensic metadata stamp)
- **Note:** Reclassified from Missing — implementation confirmed

### F-29 — Link Access Notification (Real-Time, to Uploader)
- **Frontend:** None  
- **Backend:** SSE endpoint exists but not wired to "link accessed" events
- **Status:** ❌ Missing — distinct from email notifications; even the real-time notification channel isn't wired to viewer access events
