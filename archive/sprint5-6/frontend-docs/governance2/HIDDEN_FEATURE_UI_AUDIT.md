# Hidden Feature UI Audit
Production Readiness — Hidden Feature Recovery, Phase 2
Date: 2026-06-22
Source: Direct reading of frontend source files.

---

## Current Frontend Navigation (AppShell.jsx + atoms.jsx)

AppShell.jsx renders a `<Sidebar>` component with a fixed nav items array defined in `atoms.jsx:224-246`:

```
Group 1: Upload, Viewer
Group 2: Access Control
Group 3: Analytics, Storage
Group 4: Billing
```

6 screens rendered in AppShell.jsx:
- `UploadScreen` (screen='upload')
- `ViewerScreen` (screen='viewer')
- `AccessScreen` (screen='access')
- `AnalyticsScreen` (screen='analytics')
- `StorageScreen` (screen='storage')
- `BillingScreen` (screen='billing')

AppShell passes `screen` state through `setActive` on Sidebar. Adding a new nav item requires:
1. Adding an item to the `navItems` array in `atoms.jsx`
2. Adding a `{screen === 'newscreen' && <NewScreen />}` in AppShell.jsx
3. Creating the screen component in `src/screens/`
4. Adding SecureDocAPI methods to `api.js`

---

## Feature 1 — Webhooks

### Existing UI: None

**Confirmed by:**
- No screen file exists: `ls src/screens/` — no `WebhooksScreen.jsx` or similar
- No nav item in `atoms.jsx` navItems array for webhooks
- No AppShell render branch for a webhook screen
- Zero `SecureDocAPI` methods for webhooks in `api.js` (grepped: no matches)
- No existing UI components that reference webhook endpoints

### Partial UI: None
No fragment, panel, or partial component related to webhooks exists anywhere in `src/`.

### What Could Expose It
The natural home is a new **Settings** nav section. The feature could also be a tab within an existing screen, but no existing screen is semantically related to webhooks.

- **Option A (new screen):** `WebhooksScreen.jsx` as `screen='webhooks'` — new Sidebar nav item "Integrations" or "Webhooks"
- **Option B (tab in existing screen):** No existing screen is a natural fit. AccessControl is about links, not integrations. Analytics is read-only. Billing is unrelated.
- **Recommended:** Option A. New nav item "Developer" or "Integrations" grouping Webhooks + API Keys together.

---

## Feature 2 — API Keys

### Existing UI: None

**Confirmed by:**
- No screen file: no `ApiKeysScreen.jsx` or similar
- No nav item in `atoms.jsx`
- No AppShell render branch for API keys
- Zero `SecureDocAPI` methods for api-keys in `api.js`

### Partial UI: None
No fragment anywhere in `src/`.

### What Could Expose It
Natural grouping with Webhooks as a "Developer" section. API Keys are even simpler than Webhooks (no delivery log sub-view).

- **Option A (new screen, separate):** `ApiKeysScreen.jsx` as `screen='apikeys'`
- **Option B (combined with Webhooks):** A `DeveloperScreen.jsx` with two tabs: "API Keys" and "Webhooks"
- **Recommended:** Option B. Both features serve the same persona (a developer building an integration). One screen with two tabs is less nav clutter than two separate screens.

---

## Feature 3 — Organizations

### Existing UI: None

**Confirmed by:**
- No screen file: no `OrgsScreen.jsx`, `OrgScreen.jsx`, `TeamsScreen.jsx`, or similar
- No nav item in `atoms.jsx`
- No AppShell render branch for organizations
- Zero `SecureDocAPI` methods for orgs in `api.js`
- Upload form has no org_id selector despite backend supporting it

### Partial UI: None
No fragment, input field, or component related to organizations exists in `src/`.

### Constraints for Exposure
- **Members are added by UUID only** — no email-based invitation flow in backend. UI must ask for a user UUID, which is a terrible UX. This is the #1 UX gap for the org feature.
- **saml_domain field** exists in Organization but there is no SAML auth flow — the UI should not expose saml_domain.
- **Custom domain verification** is a multi-step flow (set domain → get TXT token → add DNS record → click Verify). This is a 2-screen sub-flow.

### What Could Expose It
- **Option A (new screen):** `OrganizationScreen.jsx` as `screen='organization'` — 3 tabs: Settings, Members, Domain
- **Option B (extend AccessControl):** AccessControl could have an "Organization" tab but it would be jarring (AccessControl is about share links)
- **Recommended:** Option A. Organization settings are distinct enough to warrant their own screen. This is where Notion, Linear, and GitHub put team settings.

---

## Feature 4 — Admin Audit Log

### Existing UI: None

**Confirmed by:**
- No screen file: no `AuditLogScreen.jsx`, `AdminScreen.jsx`, or similar
- No nav item in `atoms.jsx`
- No AppShell render branch
- Zero `SecureDocAPI` methods for audit-log in `api.js`

### Partial UI: None

### Constraints for Exposure
- **Without org_id:** log only shows the current user's own events — useful but limited
- **With org_id:** requires admin/owner role in that org — richer view but requires org setup first
- The current `access_events` table (viewer analytics) is already exposed in AnalyticsScreen and AccessScreen. The admin audit log is different — it tracks admin actions (API key creation, member changes), not document views.

### What Could Expose It
Three viable homes:

- **Option A (tab in Organization screen):** Audit Log as a tab in the Organizations screen — only visible to org admins/owners. Natural grouping: "org settings" → "audit trail". Only works if user has an org.
- **Option B (tab in existing Analytics screen):** Separate "Audit Log" tab in AnalyticsScreen — visible to all users (shows own events), switches to org view when org_id available.
- **Option C (new screen):** Separate `AuditLogScreen.jsx`. Cleanest separation but most nav clutter.
- **Recommended:** Option A (tab in Organization screen) for org-scoped view; also add a personal audit view in the Settings area.

---

## Feature 5 — SSE Real-Time Notifications

### Existing UI: None

**Confirmed by:**
- `AppShell.jsx` has no `EventSource` or `new EventSource(...)` anywhere
- No `useEffect` in AppShell that subscribes to a stream
- No `SecureDocAPI` methods for notifications in `api.js`
- The `notification_service.publish_notification` is called from `tasks.py` but nothing in the frontend receives it
- The toast context (`ToastProvider`) is in place and ready to receive notifications

### Partial UI: Toast infrastructure is ready
**This is the closest any hidden feature has to a "partial UI."** The `ToastProvider` and `useToast` hook are live in the app. A notification would just need to call `addToast(...)` — the display machinery is there. Only the EventSource subscription is missing.

### What Could Expose It
SSE is not a screen — it is background wiring in AppShell.

- **Option A (AppShell useEffect):** Add a `useEffect` in `AppShell.jsx` that opens `new EventSource('/api/notifications/stream', ...)`, listens for events, and pushes toasts via `useToast`. No new screen, no new nav item. The user sees toasts pop up when a document finishes processing.
- **Option B (custom hook):** Extract to `src/hooks/useNotificationStream.js` called from AppShell. Same behavior, cleaner structure.
- **Recommended:** Option B (hook). SSE has non-trivial lifecycle (reconnect on error, cleanup on unmount, connection limit) that is better in a dedicated hook. AppShell already has enough logic.

---

## Summary

| Feature | Existing UI | Partial UI | Recommended Home |
|---|---|---|---|
| Webhooks | None | None | New screen: `DeveloperScreen` (tab 1) |
| API Keys | None | None | New screen: `DeveloperScreen` (tab 2) |
| Organizations | None | None | New screen: `OrganizationScreen` (3 tabs) |
| Admin Audit Log | None | None | Tab in `OrganizationScreen` (for org view); personal view optional |
| SSE Notifications | None | Toast infra ready | New hook `useNotificationStream` called from AppShell |

**SSE is the lowest-effort exposure** — no new screen, no nav changes, no api.js additions, just a hook called from AppShell using existing toast infrastructure.

**API Keys is the second-lowest** — a simple CRUD list, no sub-views.

**Webhooks** requires a CRUD list plus a delivery log sub-view.

**Organizations** is the most complex — three tabs, UUID-based member management (poor UX), multi-step domain verification flow.

**Admin Audit Log** is dependent on Organizations being built first for org-scoped view.
