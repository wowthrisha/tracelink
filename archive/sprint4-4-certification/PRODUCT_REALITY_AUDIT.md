# Product Reality Audit
Sprint 4.4 — Production Certification Sprint
Date: 2026-06-22
Auditor role: Product Manager + QA Lead + Lean Six Sigma Black Belt
Method: Trace every user-facing journey end-to-end. Document what actually happens vs. what the UI implies.

"Reality" = what the code actually does, verified from source.
"Promise" = what the UI communicates to the user.

---

## Journey 1 — Owner uploads a document and shares it

### Steps traced:
1. Owner opens UploadScreen → drag-drop or click to upload file
2. File is sent to `POST /api/documents/upload` → Celery pipeline queued → status polling begins
3. Status polls `GET /api/documents/{id}/status` every 2 seconds for up to 5 minutes
4. On `processed` status → document appears in table with green badge
5. Owner clicks document → navigates to AccessScreen
6. Owner clicks "⟳ New Link"
7. **→ TOAST: "New link generated"** — no API call made

**Reality:** Steps 1–5 work correctly. Step 6 is broken. The owner cannot create a share link through the UI. If no share link exists for this document, the viewer workflow is completely inaccessible.

**Promise vs. Reality:**
- Promise: "New Link" button generates a shareable link
- Reality: Button shows a success toast and does nothing

**VERDICT: BROKEN END-TO-END JOURNEY** — If no prior share link exists, the document cannot be shared. This is the most important workflow in the product.

**Defect reference:** UI-002

---

## Journey 2 — Owner shares an existing link with a viewer

*Precondition: A share link already exists (e.g., created via direct API call or before the stub defect was introduced)*

### Steps traced:
1. Owner copies link from AccessScreen Share Link tab ✅
2. Owner sends link to viewer (out of band — email, Slack, etc.)
3. Viewer opens link in browser
4. Browser fetches `GET /api/viewer/gate/{token}` → returns policy requirements ✅
5. If password required: viewer enters password → validated in `POST /api/viewer/validate` ✅
6. Session established → viewer sees document ✅
7. Pages served with watermark via `GET /api/viewer/page/{token}/{page}` ✅
8. Viewer reads document → page view events logged to access_events ✅
9. **Owner receives zero notification** — link.viewed event never dispatched

**Reality:** The viewing experience works correctly end-to-end. The access policy (password, IP, domain, expiry, max_views) is enforced server-side. However, the document owner receives no signal when their document is opened.

**Promise vs. Reality:**
- Promise (implied by product): "Know when your document is opened" (DocSend-style value proposition)
- Reality: Owner must manually check analytics. No push notification, no webhook, no SSE toast.

**VERDICT: FUNCTIONAL but missing key value proposition**

---

## Journey 3 — Owner views analytics after sharing

### Steps traced:
1. Owner opens AnalyticsScreen → Overview tab loaded via `getAnalyticsOverview()` ✅
2. Owner selects "7d" range from range picker → `range` state updated → loadAll called
3. **→ API called WITHOUT range parameter** — same data returned regardless of range selected

**Reality:** Analytics display is functional. Range selector creates the impression of filtered data but all calls return the full dataset. A user with 90 days of data who selects "24h" sees the same numbers.

**Promise vs. Reality:**
- Promise: Range picker filters analytics to the selected time window
- Reality: Range picker changes UI state only; analytics API always returns full history

**VERDICT: MISLEADING UI** — defect is MEDIUM severity but creates false data interpretation risk.

**Defect reference:** UI-004

---

## Journey 4 — Owner tries to export analytics CSV

### Steps traced:
1. Owner is on AnalyticsScreen
2. Owner clicks "↓ Export CSV"
3. **→ TOAST: "Export started — CSV ready in a moment"**
4. Nothing happens. No file downloaded. No background task started.

**Reality:** The export button is a stub. No backend endpoint is called. No CSV is ever produced.

**Promise vs. Reality:**
- Promise: "Export analytics data to CSV"
- Reality: Toast fires; no action occurs

**VERDICT: BROKEN FEATURE** — False-positive feedback loop. Users may wait for an email or download that will never arrive.

**Defect reference:** UI-005

---

## Journey 5 — Owner manages subscription (Billing)

### Steps traced:
1. Owner opens BillingScreen → `GET /api/billing/status` via direct fetch() ✅ (works)
2. Owner clicks "Upgrade to Pro" → `POST /api/billing/checkout` via direct fetch() ✅ (works)
3. Stripe Checkout opens in new tab ✅
4. Owner completes payment on Stripe
5. Stripe sends webhook to `POST /api/billing/webhook` ✅ HMAC-verified
6. Billing row updated → plan = PRO ✅
7. Owner returns to app → BillingScreen shows Pro status ✅

**Reality:** Billing flow works end-to-end. The direct fetch() concern (UI-006) is an architectural defect, not a functional one. Auth failure would give a raw error, but under normal operation billing works.

**Stripe webhook lifecycle fully handled:** subscription.created, subscription.updated, subscription.deleted, invoice.payment_failed (immediate downgrade on first payment failure).

**VERDICT: FUNCTIONAL** ✅

---

## Journey 6 — Owner annotates a document

### Steps traced:
1. Owner opens ViewerScreen for a document
2. Owner selects highlight tool → draws on page
3. `POST /api/annotations` called ✅ — annotation saved with session data
4. Owner returns to AccessScreen → Annotations tab
5. Owner's annotations listed via `GET /api/annotations` ✅
6. CSV export button present on Annotations tab (export method UNVERIFIED from source)

**Reality:** Annotation creation and owner-view work correctly. Annotation export UNVERIFIED.

**VERDICT: FUNCTIONAL with one UNVERIFIED path (export)**

---

## Journey 7 — Owner reviews viewer feedback

### Steps traced:
1. Viewer submits feedback during viewing session (mechanism UNVERIFIED — did not confirm `POST /api/feedback` call in ViewerScreen)
2. Owner opens AccessScreen → Feedback tab
3. Feedback list loaded via `GET /api/feedback` with rich filter options ✅
4. Owner replies inline via `PATCH /api/feedback/{id}` ✅
5. Owner exports feedback (export method UNVERIFIED)

**Reality:** Owner feedback management (read, reply, filter) confirmed functional. Viewer feedback submission mechanism was not verified from ViewerScreen source.

**VERDICT: PARTIAL** — Owner side confirmed. Viewer submission UNVERIFIED.

---

## Journey 8 — Owner manages storage and retention

### Steps traced:
1. Owner opens StorageScreen → `GET /api/storage/dashboard` and `GET /api/storage/forecast` ✅
2. Owner changes retention policy → `PATCH /api/storage/retention` ✅
3. Retention options: never/30_days/60_days/90_days match backend model

**Reality:** Storage management works end-to-end.

**VERDICT: FUNCTIONAL** ✅

---

## Journey 9 — Owner tries to set up webhook notifications (e.g., "notify my CRM when document opened")

### Steps traced:
1. Owner looks for webhooks in navigation → not found
2. Owner searches all screens → no webhook screen exists
3. Owner tries API directly: `POST /api/webhooks` with API key — requires `webhooks:write` scope
4. Owner tries to create API key → no screen
5. Owner is stuck

**Reality:** Both webhooks and API keys require frontend exposure. Neither has any UI. A technically sophisticated owner could discover and use these endpoints via curl/API documentation, but there is no documentation page and no UI.

Additionally: even if owner creates a webhook via API, the `link.viewed` event will never fire (SEC-006). Only `document.processed` and `analytics.completed` would deliver.

**VERDICT: BLOCKED — feature invisible to users**

---

## Journey 10 — Owner sees real-time notification when document is opened

### Steps traced:
1. Document is shared ✅
2. Viewer opens document → `POST /api/viewer/validate` → session created
3. `document.processed` SSE event would fire here? → No, this is for upload completion
4. `link.viewed` SSE notification → NEVER published from viewer.py
5. SSE stream in backend (GET /api/notifications/stream) → frontend never subscribes (no EventSource in AppShell)

**Reality:** Zero real-time notification infrastructure in the frontend. The SSE backend is running but nobody is listening. Even if the frontend hooked in, `link.viewed` notifications are not published.

**VERDICT: BLOCKED — two missing pieces: (1) frontend EventSource subscription, (2) backend link.viewed dispatch**

---

## Product Reality Scorecard

| Journey | Title | Status | Defect |
|---|---|---|---|
| J-01 | Upload + Create Share Link | BROKEN | UI-002 |
| J-02 | Share link viewer access | FUNCTIONAL (no real-time notification) | SEC-006 |
| J-03 | View analytics with range filter | MISLEADING UI | UI-004 |
| J-04 | Export analytics CSV | BROKEN | UI-005 |
| J-05 | Upgrade billing + Stripe webhook | FUNCTIONAL | UI-006 (arch only) |
| J-06 | Annotate document | FUNCTIONAL | — |
| J-07 | Manage viewer feedback | PARTIAL | Viewer submission UNVERIFIED |
| J-08 | Storage + retention management | FUNCTIONAL | — |
| J-09 | Set up webhook integration | BLOCKED | No frontend |
| J-10 | Real-time "document opened" notification | BLOCKED | SEC-006 + SSE not wired |

**Functional journeys: 3** (J-05, J-06, J-08)
**Partially functional: 1** (J-07)
**Broken: 2** (J-01, J-04)
**Misleading: 1** (J-03)
**Blocked / invisible: 2** (J-09, J-10)
**Functional with missing value prop: 1** (J-02)

---

## Most Critical Finding

**Journey 1 (Upload + Create Share Link) is broken.** For a user starting fresh with no prior data, the flow is:

1. Upload document ✅
2. Try to share it → "New Link" button fires a success toast and does nothing ❌
3. User has no way to share the document through the UI

This is not an edge case. This is the central workflow the product exists to perform.

**If share links are being created successfully in production today**, it means either:
(a) They were created before the stub was introduced and are still working, OR
(b) Users are creating links via direct API calls, OR
(c) The stub was never noticed because existing links already existed

**Action required before any production use:** Fix UI-002 immediately.
