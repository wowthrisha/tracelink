# End-to-End Validation Matrix
Production Readiness Audit — Phase 2
Date: 2026-06-22
Source: Direct code reading. Every status verified from source files, not historical reports.

Status key: ✅ Working | ⚠️ Partial / Gap | ❌ Broken / Missing

---

## W-01 — Document Upload Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. User selects file | UploadScreen.jsx | ✅ | Accepts PDF/DOCX/PPTX/XLSX/TXT/MD/LOG |
| 2. Optional group assignment | UploadScreen.jsx | ✅ | Group dropdown populated from GET /api/groups |
| 3. POST /api/documents/upload | api.js → uploadDocument() | ✅ | Returns 202 + document ID immediately |
| 4. Celery task enqueued | tasks.py process_document | ✅ | Runs async via Redis queue |
| 5. Pipeline selects processor | pipeline/ dispatch | ✅ | pdf.py / docx_pdf.py / pptx_pdf.py / xlsx_pdf.py / text.py |
| 6. PDF rendered to pages | pdf.py (416 lines) | ✅ | Poppler/PyMuPDF rasterization |
| 7. Sidecar extraction (TOC/links/words) | pdf.py | ✅ | TOC tree + link rectangles + word positions stored as JSON |
| 8. Status polling (GET /status) | UploadScreen.jsx | ✅ | 2s poll until `ready` or `error` |
| 9. Document appears in list | UploadScreen.jsx | ✅ | List refreshes on status ready |
| **Gap** | org_id | ⚠️ | Backend accepts org_id on upload form; frontend upload form has no org_id selector |

**Overall: ✅ Working** (org_id gap is a missing feature, not a broken flow)

---

## W-02 — Share Link Creation Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Select document → AccessScreen | AppShell.jsx routing | ✅ | |
| 2. Configure link settings | AccessScreen.jsx | ✅ | Password, expiry, max_views, allowed_emails, IP allowlist |
| 3. POST /api/links | api.js → createLink() | ✅ | Returns ShareLink with token |
| 4. Link displayed to user | AccessScreen.jsx | ✅ | Copy-to-clipboard on token |
| 5. Link revocation | AccessScreen.jsx → deleteLink() | ✅ | DELETE /api/links/{id} |
| 6. Link update (PATCH) | AccessScreen.jsx → updateLink() | ✅ | PATCH /api/links/{id} |
| **Gap** | Download permission UI | ⚠️ | `can_download` permission is stored in DB; not visible in link creation UI (backend enforces it but user can't set it) |

**Overall: ✅ Working** (download permission UI gap noted)

---

## W-03 — Viewer Access Flow (Password-Protected)

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Viewer opens share URL | ViewerScreen.jsx | ✅ | Token parsed from URL path |
| 2. GET /api/viewer/gate/{token} | viewer.py | ✅ | Returns policy metadata without creating session |
| 3. Password prompt shown | AccessGate component | ✅ | If `requires_password: true` |
| 4. POST /api/viewer/validate | viewer.py (rate limited 20/min) | ✅ | Returns session_id, link_token |
| 5. Session stored in sessionStorage | useViewerSession.js | ✅ | Key: `securedoc_sess_{token}` |
| 6. Pages loaded (GET /api/viewer/page) | viewer.py (rate limited 120/min) | ✅ | Serves rasterized page images |
| 7. Session expiry / 401 recovery | useViewerSession.js | ✅ | Clears sessionStorage, re-authenticates |
| 8. DRM applied (if `can_print: false`) | useViewerSession.js | ✅ | Event listeners registered |
| 9. Max views enforcement | viewer.py | ✅ | 403 when view_count >= max_views |

**Overall: ✅ Working**

---

## W-04 — Viewer Access Flow (Email-Gated)

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. GET /api/viewer/gate/{token} | viewer.py | ✅ | Returns `requires_email: true` |
| 2. Email entry form shown | AccessGate component | ✅ | |
| 3. POST /api/viewer/validate with email | viewer.py | ✅ | Checks `allowed_emails` JSON and `allowed_domains` |
| 4. Email logged to access_events | analytics.py | ✅ | `viewer_email` field populated |
| **Gap** | No email notification to uploader | ❌ | Uploader is NOT notified when viewer opens link — must check AccessLog manually |

**Overall: ✅ Working** (notification gap is missing feature, not broken flow)

---

## W-05 — Viewer Access Flow (IP-Restricted)

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. POST /api/viewer/validate | viewer.py | ✅ | Server-side IP check against `ip_allowlist` JSON |
| 2. 403 returned on IP mismatch | viewer.py | ✅ | Frontend shows error state |

**Overall: ✅ Working**

---

## W-06 — PDF Document Viewing

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Thumbnails loaded | GET /api/viewer/thumb | ✅ | Used for ThumbnailSidebar |
| 2. TOC loaded | GET /api/viewer/toc | ✅ | Used for TocSidebar, page numbers |
| 3. Page rendered on canvas/img | ViewerScreen.jsx | ✅ | Server-rasterized images, no client-side PDF |
| 4. Zoom/fit modes | ViewerScreen.jsx | ✅ | fit-width / fit-page / custom zoom |
| 5. Page navigation | ViewerScreen.jsx | ✅ | Thumbnail click, TOC click, prev/next |
| 6. Watermark overlay | ViewerScreen.jsx | ✅ | CSS text-shadow overlay when `watermark_text` present |
| 7. Search | GET /api/viewer/search/{token} | ✅ | Returns page + position rectangles |
| 8. Hyperlinks panel | GET /api/viewer/links/{token} | ✅ | Sidebar with extracted PDF links |
| 9. Word positions | GET /api/viewer/words/{token} | ✅ | Used for text selection overlay |

**Overall: ✅ Working**

---

## W-07 — Text/Markdown Document Viewing

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. `isTextDoc` detection | ViewerScreen.jsx | ✅ | Based on `doc.file_type` from gate response |
| 2. Text chunks loaded | GET /api/viewer/text/{token}/{chunk} | ✅ | Chunked loading |
| 3. Rendered in `<pre>` | ViewerScreen.jsx | ✅ | No XSS risk (pre element, not innerHTML) |
| 4. Copy control applied | ViewerScreen.jsx | ✅ | `userSelect: none` when `can_copy: false` |

**Overall: ✅ Working**

---

## W-08 — Annotation Creation + Threading

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. `can_annotate` check | AnnotationLayer / ViewerScreen | ✅ | Guards all annotation API calls and UI |
| 2. Create annotation | POST /api/viewer/annotations/{token}/{page} | ✅ | highlight/comment/draw/arrow/rectangle/sticky_note/bookmark |
| 3. Thread reply | GET /api/viewer/annotations/{token}/{id}/thread | ✅ | Thread modal in viewer |
| 4. Uploader sees annotations | GET /api/documents/{id}/annotations | ✅ | Separate auth path (owner token) |
| 5. Owner replies to feedback | POST /api/documents/{id}/feedback/{ann_id}/reply | ✅ | Uploader-side reply |
| 6. Viewer sees reply | GET /api/viewer/annotations/{token}/{id}/thread | ✅ | Thread updated with owner reply |
| 7. Resolve annotation | PATCH /api/viewer/annotations/{token}/{id}/resolve | ✅ | Sets resolved state |

**Overall: ✅ Working**

---

## W-09 — Feedback Export Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Owner opens AccessScreen | AppShell routing | ✅ | |
| 2. Feedback list loaded | GET /api/documents/{id}/feedback | ✅ | |
| 3. Export feedback CSV | GET /api/documents/{id}/feedback/export | ✅ | Direct blob download |
| 4. Export reviewer activity | GET /api/documents/{id}/feedback/export-reviewer-activity | ✅ | Second CSV with per-reviewer stats |
| 5. Export visual annotations | GET /api/documents/{id}/annotations/export | ✅ | Third CSV (all annotation types) |

**Overall: ✅ Working**

---

## W-10 — Analytics Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Viewer event logged | POST /api/analytics/events (rate limited 60/min) | ✅ | page_view, dwell_time, blocked_action etc. |
| 2. Event validated server-side | analytics.py | ✅ | event_type whitelist, page_number bounds check |
| 3. Owner views AnalyticsScreen | AppShell routing | ✅ | |
| 4. Overview stats | GET /api/analytics/overview | ✅ | Total views, unique viewers, avg dwell |
| 5. Per-document breakdown | GET /api/analytics/documents | ✅ | |
| 6. Group analytics | GET /api/analytics/groups | ✅ | |
| 7. Page heatmap | GET /api/analytics/page-heatmap | ✅ | Per-page dwell times |
| 8. Events log | GET /api/analytics/events (owner auth) | ✅ | Raw event table with filters |

**Overall: ✅ Working**

---

## W-11 — Storage + Retention Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Storage dashboard | GET /api/storage/dashboard | ✅ | Total/used/available breakdown |
| 2. Storage forecast | GET /api/storage/forecast | ✅ | Growth trend projection |
| 3. Set retention policy | PATCH /api/documents/{id}/retention | ✅ | Sets retention_policy + expires_at |
| 4. Lifecycle state transitions | backend worker | ✅ | `purge_stale_sessions` + `requeue_orphaned_uploads` tasks |

**Overall: ✅ Working**

---

## W-12 — Billing Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. BillingScreen loads | AppShell routing | ✅ | |
| 2. Status check | GET /api/billing/status (direct fetch) | ✅ | Returns plan, status, period_end |
| 3. Upgrade (Stripe Checkout) | POST /api/billing/checkout (direct fetch) | ✅ | Returns Stripe checkout URL |
| 4. Portal (manage subscription) | POST /api/billing/portal (direct fetch) | ✅ | Returns Stripe portal URL |
| 5. Webhook (Stripe → backend) | POST /api/billing/webhook | ✅ | Signature verified, plan updated |
| 6. No Stripe keys configured | billing.py `billing_enabled` property | ✅ | Graceful "not configured" state |
| **Gap** | BillingScreen bypasses SecureDocAPI | ⚠️ | Direct fetch() in component; not using window.SecureDocAPI pattern |

**Overall: ✅ Working** (SecureDocAPI bypass is a code smell, not a functional gap)

---

## W-13 — Authentication Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Login | LoginScreen.jsx → Supabase password grant | ✅ | |
| 2. Signup | LoginScreen.jsx → POST /api/auth/register | ✅ | Backend creates user in Supabase + billing row |
| 3. Forgot password | LoginScreen.jsx → Supabase /auth/v1/recover | ✅ | Email sent by Supabase |
| 4. Reset password (from email link) | LoginScreen.jsx (URL hash detection) | ✅ | Auto-detects `type=recovery` in URL hash, shows reset form |
| 5. Token persistence | localStorage['securedoc_token'] | ✅ (⚠️ MEDIUM risk) | Working but in localStorage (CG-003) |
| 6. Logout | AppShell.jsx | ✅ | Clears token, resets state |

**Overall: ✅ Working**

---

## W-14 — Webhook Configuration Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Create webhook endpoint | POST /api/webhooks | ✅ Backend only | Backend: SSRF protection, URL validation, secret signing |
| 2. List / edit / delete | GET/PATCH/DELETE /api/webhooks/{id} | ✅ Backend only | |
| 3. View delivery logs | GET /api/webhooks/{id}/deliveries | ✅ Backend only | |
| 4. Test delivery | POST /api/webhooks/{id}/test | ✅ Backend only | |
| **Gap** | No frontend UI | ❌ | Users cannot configure webhooks through the application |

**Overall: ❌ Not Accessible** (backend complete; zero frontend path)

---

## W-15 — API Key Management Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Create API key | POST /api/api-keys | ✅ Backend only | SHA-256 stored, scope enforcement |
| 2. List / delete / rotate | GET/PATCH/DELETE /api/api-keys/{id} | ✅ Backend only | |
| **Gap** | No frontend UI | ❌ | Users cannot create or manage API keys |

**Overall: ❌ Not Accessible** (backend complete; zero frontend path)

---

## W-16 — Organization Management Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. Create org | POST /api/orgs | ✅ Backend only | 4-tier roles: viewer/editor/admin/owner |
| 2. Manage members | GET/POST/PATCH/DELETE /api/orgs/{id}/members | ✅ Backend only | |
| 3. Custom domain verification | GET /api/orgs/{id}/domain/token + POST verify | ✅ Backend only | TXT record DNS verification |
| 4. SAML domain field | orgs model: saml_domain | ⚠️ Field only | No SAML authentication flow implemented |
| **Gap** | No frontend UI | ❌ | Users cannot create or manage organizations |

**Overall: ❌ Not Accessible** (backend complete; zero frontend path)

---

## W-17 — Real-Time Notifications Flow

| Step | Component | Status | Notes |
|---|---|---|---|
| 1. SSE stream endpoint | GET /api/notifications/stream | ✅ Backend only | Per-user connection limit, chunked transfer |
| 2. Frontend subscription | AppShell.jsx | ❌ | No EventSource(); SSE events never delivered to UI |
| 3. Processing status notifications | viewer accessed events | ❌ | SSE events not emitted on document ready or link access |

**Overall: ❌ Not Accessible** (backend exists; frontend never subscribes)

---

## Gap Summary

| Gap | Workflow | Severity | User Impact |
|---|---|---|---|
| No email notification when viewer opens link | W-04 | HIGH | Uploader must poll manually |
| No frontend for Webhooks | W-14 | HIGH | Integration story blocked |
| No frontend for API Keys | W-15 | HIGH | Developer integration blocked |
| No frontend for Organizations | W-16 | HIGH | Multi-user workflows blocked |
| SSE not wired to frontend | W-17 | MEDIUM | Real-time updates not delivered |
| No version creation endpoint | W-01 (F-05) | MEDIUM | Version control unusable |
| Download permission not settable from UI | W-02 | LOW | `can_download` always default |
| BillingScreen bypasses SecureDocAPI | W-12 | LOW | Code consistency only |
| No org_id selector on upload | W-01 | LOW | Org assignments require API calls |
