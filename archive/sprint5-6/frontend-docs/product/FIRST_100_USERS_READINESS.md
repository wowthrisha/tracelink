# First 100 Users Readiness — Sprint 4.8 Phase 4

**Method:** Role-play analysis grounded in actual source code. Every judgment references a specific file, behavior, or endpoint.

---

## Role 1 — Architect

*Evaluating technical depth, reliability, and extensibility.*

### What would delight them?

- **Viewer architecture is genuinely solid.** Image-based rasterization (not PDF.js), DRM enforcement at the page level, CORS-scoped S3 pre-signed URLs with short expiry, concurrent session limiting. These are production-grade security primitives — not demos. (`useViewerSession.js`, `viewer.py`)
- **Cache architecture is intentional.** `invalidate_link()` in `viewer_cache.py` is called on every link update, ensuring in-flight viewers see policy changes within one page turn. This is not a naive "clear everything" — it's targeted eviction.
- **Webhook delivery is async and retried.** Celery-based (`webhook_tasks.py`). Failed deliveries are retried, tracked, and exposed via delivery history UI. This is real infrastructure, not a stub.
- **Scope-based API key auth is clean.** `require_scope()` in `auth.py` is a single guard function. JWT users bypass scope check entirely (appropriate for browser clients). API key callers are scoped. Clean separation.
- **`version` and `parent_document_id` on the Document model** signal that versioning was considered architecturally, even if not exposed in the UI yet.

### What would confuse them?

- **`⊕ Filter` button in the Upload screen header fires `toast('Search feature coming soon', 'info')`** — a non-functional UI element at the top of the primary screen. (`UploadScreen.jsx:204`). This is a dead stub in production.
- **`PATCH /api/links/{id}` exists but is never called from the frontend.** An architect would find this in the router, see the cache invalidation wired up, and then look at the frontend and find `updateLink` is absent from `api.js`. This looks like a ship-gate item that was missed.
- **`api.js` is a global singleton (`window.SecureDocAPI`), not a module.** This is a deliberate architectural choice for serving as a static file, but it is unusual and creates implicit global state that can be hard to test.
- **Groups are user-scoped, not org-scoped.** The org model exists, but group queries filter by `user_id`, not `org_id`. An architect would notice the inconsistency and ask about the roadmap for multi-user groups.

### What would make them stop using SecureDoc?

- **No observability into viewer failures.** The Viewer's error state is a blank page with a retry button (`ViewerErrorBoundary.jsx`). No error code, no structured logging to the owner. An architect sharing a document externally has no visibility into viewer failures.
- **No rate limit on share link creation.** The `POST /api/links` endpoint has no per-document link count cap in the business logic layer. A script could create thousands of links for one document. The 20-webhook cap exists for webhooks; no equivalent for links.

### What would make them pay?

- The **concurrent session limiting** (`max_concurrent_sessions` on `ShareLink`) is genuinely enterprise-grade. No PDF sharing tool in this space does session concurrency control at the link level.
- The **IP allowlist + domain restriction + password + expiry in a single link policy** is a strong value proposition for anyone sharing regulated documents.

---

## Role 2 — Consultant

*Evaluating client-facing workflows and meeting ROI expectations.*

### What would delight them?

- **QuickShare is a killer feature for demos.** One hover → click → URL in under 3 seconds. No configuration required. The watermark-on, download-off default is the right choice for a consultant sharing a draft report. (`QuickShareModal.jsx`)
- **Feedback tab in Access Control.** Seeing client comments on specific pages, with timestamps and reviewer identities, inline in the management UI. This is what consultants need for document review cycles.
- **Embed code is included automatically.** Every share link in the Share Link tab shows `<iframe>` embed code. Consultants who want to put a document in a client portal get the embed code without asking.
- **Access Log shows viewer location and IP.** Knowing that "client X opened the document at 9:47 AM and spent 12 minutes on page 4" is actionable intelligence for a consultant preparing a follow-up call.

### What would confuse them?

- **No "Resolve" button on feedback threads.** Consultants use document feedback as an action list. The Status column shows "Open" and "Resolved" — but there is no button to mark a thread as resolved. The feedback tab is read-only for resolution. (`AccessScreen.jsx:550–554`)
- **"Save Policy" creates a new link.** A consultant who shared a report with a client, gets new feedback, updates their allowed email list, and clicks "Save Policy" — has now created a NEW share URL. The client's bookmarked link still works (with old policy). The consultant has no idea. (`AccessScreen.jsx:116`)
- **Policy form shows blank fields, not current link settings.** When a consultant returns to the Policy tab to update an existing link, they see empty fields. They have no way to know what the current policy is without going to the Share Link tab and reading the metadata. (`AccessScreen.jsx:43–60`)

### What would make them stop using SecureDoc?

- **No email notification when a client opens a document.** The Notification Center polls analytics events, but there are no outbound emails. A consultant who shares a proposal on Monday and checks SecureDoc on Friday may have missed a client opening it Tuesday and waiting for a call.
- **The "Quick Share → modify later" workflow is broken.** A consultant shares a document quickly, then wants to add a password before a client presents it internally. They cannot. They must revoke and re-share with a new URL.

### What would make them pay?

- **Viewer annotations + owner replies.** A consultant can leave replies to client highlights directly in the document. This creates a structured review loop that replaces email chains.
- **Page engagement heatmap.** Seeing that clients spent 4 minutes on the pricing page and skipped the technical appendix entirely is actionable intelligence worth paying for.

---

## Role 3 — Procurement Manager

*Evaluating security controls, compliance, and enterprise policy requirements.*

### What would delight them?

- **IP allowlist + domain restriction + password are available on every link.** Most document sharing tools offer these only at the premium tier. SecureDoc exposes all three per link. (`AccessScreen.jsx:246–270`)
- **Watermark is enabled by default.** The `QUICK_SHARE_DEFAULTS` in `QuickShareModal.jsx:7–14` and the Permission defaults in `AccessScreen.jsx:52–61` default `watermark_enabled: true`. A procurement manager sharing vendor pricing sheets sees watermarking as a baseline, not an upsell.
- **Audit log is immutable and accessible.** `GET /api/admin/audit-log` exists and the UI (`AuditLogScreen.jsx`) exposes it. A procurement manager can show auditors a timestamped record of who accessed what and when.
- **Max view count.** Setting `max_views: 1` for a confidential document means the link self-destructs after first view. This is a procurement manager's dream for sharing NDA drafts.

### What would confuse them?

- **No export of the access log from the UI.** The Audit Log screen (`AuditLogScreen.jsx`) has no Export CSV button, unlike the Analytics screen which does. A procurement manager preparing a compliance report needs an export.
- **"Risk" labels (HIGH/MED/LOW) have no documented criteria.** The risk field appears in `DocRow.jsx:49`, `AccessScreen.jsx:211`, and `AnalyticsScreen.jsx:171`. There is no tooltip or explanation of what "HIGH" risk means. Procurement managers will ask about this in a security review.
- **Max concurrent sessions field.** This is powerful but arcane. "Max Concurrent Sessions: 1" means only one viewer can be in the document at the same time, globally. A procurement manager who sets this to 1 for a procurement committee review will create a very bad experience if 3 people open it simultaneously.

### What would make them stop using SecureDoc?

- **No document download of the access log for audit purposes.** All audit evidence is in-UI only.
- **No SSO / SAML integration.** Procurement managers in enterprises expect to provision users via Okta or Azure AD. Without SSO, every new team member needs a manual account. This is a blocker for enterprise adoption at scale.
- **The sidebar has 12 navigation items.** A procurement manager onboarding their team will get questions about "API Keys", "Webhooks", and "Audit Log" — which are developer-facing. These being visible at the same level as "Upload" creates confusion about what the product is for.

### What would make them pay?

- IP allowlist per link (not per account) is genuinely unusual and valuable.
- Max concurrent sessions is a unique capability.
- Watermarking of converted images (rather than overlay JS) makes watermarks tamper-resistant — a strong compliance argument.

---

## Role 4 — Startup Founder

*Evaluating speed, value, and whether this replaces a current manual process.*

### What would delight them?

- **Upload → shareable link in under 60 seconds.** The end-to-end flow (drag drop → processing → QuickShare copy) is genuinely fast when it works. The 2-second polling interval means a 10-page PDF is ready in 10–20 seconds.
- **The viewer looks professional.** Page-by-page rendering with a dark toolbar, page thumbnails, zoom, annotation tools. This looks like a product, not an MVP.
- **No download by default.** A founder sharing an investor deck doesn't need to configure anything to prevent download. The right default is already set.
- **Groups let them stay organized.** A founder with decks organized by investor round (Series A, Series B), customer (Acme, Beta, Gamma), and function (Board, Legal, HR) can keep all of these straight with named groups.

### What would confuse them?

- **The sidebar has 12 items including "Webhooks" and "Audit Log."** A founder opening SecureDoc for the first time sees Upload, Viewer, Access Control, Analytics, Storage, API Keys, Webhooks, Audit Log, Organizations, Notifications, Billing. This is overwhelming. They expect: Documents, Share, Analytics, Settings.
- **"Access Control" is not obvious vocabulary.** A founder wants to "manage who can see my doc." "Access Control" is a security term that signals enterprise complexity, not a simple permission toggle.
- **Clicking a document row opens Access Control, not the Viewer.** This is the #1 likely first-use frustration. New users click their document to open it. They land on a form with password fields and IP allowlists. `DocRow.jsx:15 onClick={onAccess}`.
- **The Storage screen serves no value at < 10 documents.** A founder with 5 documents who clicks "Storage" sees "12.4 MB used · 5 documents" — no actionable information. The 30-day projection card requires enough history to be meaningful.

### What would make them stop using SecureDoc?

- **The first time they "save a new policy" expecting to update their existing link, they create a ghost link.** A founder who shared a deck with 10 investors, then updates the allowed email list, has now created an 11th link. The original link is unchanged. The new contacts they were trying to add cannot access it unless they get the new URL. They will blame the product for being broken.
- **No mobile viewer optimization.** A founder whose investor is opening the doc on a phone will see an unoptimized experience. The Viewer is designed for desktop (toolbar, two-page mode, etc.).

### What would make them pay?

- **Link analytics per viewer email.** Knowing that "Partner X at Acme VC opened page 4 (Deal Terms) and spent 8 minutes there" is the kind of insight that closes rounds faster. This exists in the analytics infrastructure — it just needs to be surfaced per-link, not just per-document.
- **The instant QuickShare.** Competing products (DocSend, Docsend clones) require creating a "space" first. SecureDoc has zero overhead for a quick share.

---

## Readiness Summary

| Capability | Status for First 100 Paying Users |
|-----------|------------------------------------|
| Core share-link flow | Ready — but link edit is broken (creates new URL silently) |
| Viewer quality | Ready — professional, DRM, annotations |
| Access control depth | Ready — IP allowlist, domain, password, expiry, session limiting |
| Analytics | Ready — heatmap, group analytics, CSV export |
| Feedback loop | Not ready — no resolve action |
| Link modification | Not ready — PATCH endpoint unused |
| Onboarding/navigation | Not ready — sidebar overwhelm, wrong default row click action |
| Mobile experience | Unknown — not evaluated (no UI testing tools available) |
| Email notifications | Not ready — no outbound email on viewer events |

---

*Generated: Sprint 4.8 Phase 4 — no implementation performed.*
