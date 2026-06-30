# Hidden Feature ROI Analysis
Production Readiness — Hidden Feature Recovery, Phase 3
Date: 2026-06-22

Rating scale: HIGH / MEDIUM / LOW across 4 dimensions.
Effort = frontend only (backend is already complete for all features).

---

## Feature 1 — SSE Real-Time Notifications

### Business Value: HIGH
Real-time "document finished processing" feedback is standard UX for any async-upload workflow. Every cloud file tool (Dropbox, Drive, Notion) shows a completion signal. Currently, a user who uploads a large document must stare at a spinner or manually refresh to check status. An SSE notification turns a polling UX into a push UX. Secondarily, `link.viewed` notifications (requires wiring — see backend audit) would be the #1 daily-use-case unlock for DocSend-comparable positioning.

### Customer Value: HIGH
Direct daily impact for every user who uploads documents. The feedback loop is: upload → go do something else → toast appears "Your document is ready." This is the difference between a polished tool and a rough one. Users with multiple tabs open would benefit immediately.

### Engineering Effort: LOW
The backend stream endpoint, Redis pub/sub, and `notification_service` are production-ready. The frontend `ToastProvider` already exists. The only work is:
1. A new `useNotificationStream.js` hook (~60 lines) with EventSource, reconnect logic, and disconnect cleanup
2. One `useNotificationStream(token)` call in `AppShell.jsx` (~2 lines)
3. No new screens, no nav changes, no `api.js` additions required

Estimated effort: **0.5 days**

### Support Burden: LOW
SSE is read-only. If the stream breaks, the app degrades silently (polling fallback is already the current behavior). No new user-facing error states required beyond a missed toast.

### Rating: **HIGH value, LOW effort — ship immediately**

---

## Feature 2 — API Keys

### Business Value: HIGH
API keys unlock the integration market. Any user who wants to automate document uploads, programmatically create share links, or build a Zapier/n8n integration currently cannot — the only way to interact with SecureDoc is through the browser UI. API keys with scope control (`documents:write`, `links:read`, etc.) are the foundation for all developer workflows.

### Customer Value: MEDIUM-HIGH
The primary customer for API keys is a technical user or developer. For non-technical users, API keys have zero direct value. However, for the users who DO need integrations, they are a hard blocker. A sales operations user who wants to automatically send a document link when a deal moves to "Demo Requested" in their CRM cannot do this today.

### Engineering Effort: LOW
The backend is complete (SHA-256 key storage, scopes, audit logging). The UI is a simple CRUD list:
- Show a table of existing keys: name, prefix (`sd_a1b2c3...`), scopes, active status, last used, expiry
- "Create Key" button → modal with name + scopes checkboxes → show full key ONCE with copy button
- Revoke/delete buttons per row
Estimated effort: **1 day** (screen + api.js methods)

### Support Burden: LOW-MEDIUM
Users will inevitably lose their API keys (full key shown only once). The recovery path is "delete old key, create new one" — standard developer tooling behavior. Will generate support requests from users who expect to see their full key again. Clear UI copy ("this key will not be shown again") mitigates this.

### Rating: **HIGH value, LOW effort — ship immediately after security sprint**

---

## Feature 3 — Webhooks

### Business Value: HIGH
Webhooks are the integration primitive that technical users and companies expect. `document.processed` fires when an upload is ready — a workflow automation could immediately send a link to a client. `link.viewed` (once wired) fires when a recipient opens a document — a CRM integration could log the view event. This is the #1 feature request category for B2B SaaS tools at this stage.

### Customer Value: MEDIUM
Webhooks serve a subset of customers: those building integrations. For the majority of solo users, webhooks have no immediate value. The value compounds as the customer base grows and more teams integrate SecureDoc into their workflows.

### Engineering Effort: MEDIUM
More complex than API Keys because of the delivery log sub-view:
- Endpoint list with CRUD
- Create endpoint: URL + event type checkboxes + optional description → secret shown ONCE
- Per-endpoint detail: delivery log table (event_type, status, attempts, response_status, last_attempt_at) with pagination
- Test-fire button
Plus: the `link.viewed` event needs to be wired in `viewer.py` before webhooks deliver full value
Estimated effort: **1.5–2 days**

### Support Burden: MEDIUM
Webhooks generate support requests: "why isn't my webhook firing?" (usually firewall or bad URL), "what's the payload format?", "my delivery failed after 4 retries." The delivery log UI reduces support burden by giving users self-service debugging. The test-fire endpoint is already built.

### Rating: **HIGH value, MEDIUM effort — ship after API Keys**

---

## Feature 4 — Organizations

### Business Value: HIGH
Organizations unlock the multi-user market. Currently, every user operates in complete isolation — documents, links, and analytics are per-user with no way to share access with a colleague. The org model supports 4-tier roles (viewer/editor/admin/owner), org-scoped document visibility, and custom domain verification. This is required for any team or company use case.

### Customer Value: HIGH
For solo users: zero immediate value. For teams and companies: organizations are the difference between "a tool one person uses" and "a tool a team uses." Enterprise buyers evaluate whether a tool has team collaboration before purchasing. The org model also opens the path to per-seat pricing.

### Engineering Effort: HIGH
The most complex feature to expose:
- Organization list and creation (simple)
- Member management table: show members, add member (UUID required — poor UX), change role, remove member
- Custom domain tab: multi-step DNS verification flow
- **Critical UX gap:** adding a member requires knowing their Supabase user UUID — there is no email-based invitation in the backend. This makes the member UI nearly unusable in practice. Users would need to get their UUID from somewhere else and paste it in.
- Audit log tab (reads from admin audit log)
Estimated effort: **3–4 days for basic org + member UI; UX quality is limited by UUID-only member add**

### Support Burden: HIGH
Organizations introduce permission errors ("I can't see my colleague's document"), role confusion ("why can't I create a link?"), and the UUID-based member add creates constant support tickets ("how do I add someone?"). The domain verification flow has DNS-related failure modes.

### Rating: **HIGH value, HIGH effort — meaningful UX requires solving the UUID member-add problem first**

---

## Feature 5 — Admin Audit Log

### Business Value: MEDIUM
Audit logs are a compliance requirement for enterprise and SOC2-certified products. For solo users and small teams, they have zero daily value. For enterprises, they are a checkbox item in vendor evaluation. Currently, audit events ARE being written to the database for all org/member/api_key operations — the data exists, only the read UI is missing.

### Customer Value: LOW-MEDIUM
Most current customers will never look at an audit log. The customer who cares is the IT administrator at a company that has procured SecureDoc for a team. That customer is likely not yet in the user base.

### Engineering Effort: LOW
The backend endpoint is a single paginated read. The UI is a read-only table:
- Event type, actor, target, timestamp columns
- Filter by event type (optional)
- Pagination
No create/edit/delete operations.
Estimated effort: **0.5–1 day** if built as a tab in OrganizationScreen (no new nav item)

### Support Burden: LOW
Read-only table. Users can't break anything. The only confusion is "why is this event here" — answerable with a tooltip per event type.

### Rating: **MEDIUM value, LOW effort — ship as a tab inside Organizations screen, not standalone**

---

## ROI Summary Matrix

| Feature | Business Value | Customer Value | Effort | Support Burden | ROI Rank |
|---|---|---|---|---|---|
| SSE Notifications | HIGH | HIGH | LOW (0.5d) | LOW | **#1** |
| API Keys | HIGH | MEDIUM-HIGH | LOW (1d) | LOW-MEDIUM | **#2** |
| Webhooks | HIGH | MEDIUM | MEDIUM (1.5-2d) | MEDIUM | **#3** |
| Admin Audit Log | MEDIUM | LOW-MEDIUM | LOW (0.5-1d) | LOW | **#4** |
| Organizations | HIGH | HIGH | HIGH (3-4d) | HIGH | **#5 (gated on UX fix)** |

Organizations rank last not because of low value but because the UX constraint (UUID-only member add) makes the feature near-unusable without a prior backend change to support email-based invitations or user lookup. Building the UI without solving this would result in a confusing, support-heavy feature that damages trust.
