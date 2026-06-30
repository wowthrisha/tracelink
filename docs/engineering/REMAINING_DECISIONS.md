# Remaining Decisions
**Generated:** 2026-06-30  
**Author:** Autonomous Engineering Improvement Program  

These items require a **product/business decision** and cannot be safely implemented without input. They are not engineering blockers — the engineering work is understood; only the direction is unclear.

---

## RD-001 — Full Email Invite Flow vs Direct-Add-Only (High)

**Current state:** `POST /api/orgs/{org_id}/members/invite` adds users directly if they already have a SecureDoc account. If they don't, it returns a 404 error.

**Business decision needed:**
- (A) Keep current behavior: invitee must self-register first
- (B) Send invite email: create a pending-invite table, send email, invitee follows link to register + join org
- (C) Admin-creates account: use Supabase service role to create an unconfirmed account for the invitee

Option B is the enterprise-standard UX but requires an email service (SMTP/SendGrid), a `pending_invites` table, and invite-token validation logic.

**Estimated effort for Option B:** 1–2 weeks  
**Stakeholder:** Product, Engineering

---

## RD-002 — URL Routing Strategy (High)

**Current state:** No URL routing. All navigation state is in-memory in `AppShell.jsx`. Refreshing the browser always returns to the Upload screen.

**Business decision needed:**
- (A) Hash-based routing (`#/documents`, `#/access/doc-id`) — no server config needed
- (B) History API routing (`/documents`, `/access/doc-id`) — needs server-side fallback (return `index.html` for all routes)
- (C) Defer: not a priority before v1.0

Note: This is a large refactor (AppShell + all 13 screens). Option A is lower risk.

**Estimated effort:** 1–2 weeks  
**Stakeholder:** Product, Engineering

---

## RD-003 — Analytics Date Range Implementation (Medium)

**Current state:** All analytics are fixed to "last 7 days" for sparklines and "all time" for aggregates. The backend analytics endpoints have no date range parameters.

**Business decision needed:**
- (A) Add `start_date`/`end_date` params to all `/api/analytics/*` endpoints, add date picker to AnalyticsScreen
- (B) Keep all-time aggregates, only add period presets (7d/30d/90d) without custom ranges
- (C) Defer until analytics rearchitecture

**Estimated effort for Option A:** 1 week  
**Stakeholder:** Product

---

## RD-004 — Webhook Event Coverage (Medium)

**Current state:** Only 3 webhook events (`document.processed`, `link.viewed`, `analytics.completed`).

**Business decision needed:** Which additional events to support. Candidates:
- `link.created`, `link.revoked` — useful for audit trails
- `document.deleted`, `document.uploaded` — useful for integrations
- `org.member_added`, `org.member_removed` — useful for directory sync
- `api_key.created`, `api_key.revoked` — useful for security monitoring

Each event requires:
1. Backend service to fire the event at the right time
2. `WEBHOOK_EVENTS` constant update in `webhooks.py`
3. Webhook UI update to expose new events

**Estimated effort:** 1 week for full set  
**Stakeholder:** Product, Developer Relations

---

## RD-005 — Mobile Support Strategy (Medium)

**Current state:** App is hard-blocked at 768px viewport width (`AppShell.jsx`). Mobile users see nothing.

**Business decision needed:**
- (A) Admin-only web app stays desktop-only; viewer link gets mobile-responsive viewer
- (B) Full mobile-responsive admin interface (large refactor)
- (C) Native mobile app via React Native (separate project)

Option A (mobile viewer only) is the pragmatic choice for a document security product.

**Estimated effort for Option A:** 2–3 weeks  
**Stakeholder:** Product, Engineering

---

## RD-006 — Free Plan Enforcement UX (Medium)

**Current state:** When a free plan user uploads their 11th document, they get a generic server error. No counter is shown in the UI, no upgrade prompt appears.

**Business decision needed:**
- Plan limit enforcement messaging: what copy/CTA to show at 80%, 100% capacity
- Whether to show the counter only for free users, or for all users (Pro quota too)
- Whether hitting the limit should block upload or show an upgrade modal

**Estimated effort:** 1 day for counter + warning; 1 additional day for upgrade modal  
**Stakeholder:** Product, Growth

---

## RD-007 — Notification Read State Persistence (Low)

**Current state:** "Mark all read" stores a timestamp in `localStorage` (`LS_LAST_SEEN` key). Opening in a new browser or different device resets all notifications to unread.

**Business decision needed:**
- (A) Add `user_notification_reads` table; persist last-seen server-side
- (B) Acceptable UX: in-app notifications are per-device, expected behavior
- (C) Defer until notifications are email-based (no in-app reads needed)

**Estimated effort for Option A:** 1 day  
**Stakeholder:** Product

---

## RD-008 — SAML/SSO Configuration UI (Enterprise)

**Current state:** `Organization.saml_domain` field exists in the DB and is exposed via API, but there is no UI to configure it. Enterprise SSO requires ACS URL, Entity ID, and IdP metadata.

**Business decision needed:** Does SecureDoc support SAML SSO in the current product tier, and if so, what does the setup flow look like?

**Estimated effort:** 2–3 weeks (backend SSO assertion validation + frontend config UI)  
**Stakeholder:** Enterprise Sales, Engineering

---

*All items above are tracked for discussion. Once a direction is chosen for each, engineering can implement without further review.*
