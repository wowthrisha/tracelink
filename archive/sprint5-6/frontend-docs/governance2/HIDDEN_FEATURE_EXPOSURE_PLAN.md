# Hidden Feature Minimal Exposure Plan
Production Readiness — Hidden Feature Recovery, Phase 4
Date: 2026-06-22

Rules: No redesigns. No architecture changes. Reuse existing screens where possible.
Reuse existing patterns (tokens.js, atoms.jsx components, SecureDocAPI pattern).
DO NOT IMPLEMENT. This is a plan only.

---

## Plan 1 — SSE Real-Time Notifications

**Exposure method:** New hook called from existing AppShell. Zero new screens.

### Screen
- `AppShell.jsx` (existing) — adds one `useNotificationStream(token)` call

### New Component
- `src/hooks/useNotificationStream.js` (new file, ~70 lines)

### Implementation Sketch
```javascript
// src/hooks/useNotificationStream.js
export function useNotificationStream(token) {
  const { addToast } = useToast();
  useEffect(() => {
    if (!token) return;
    let es;
    const connect = () => {
      es = new EventSource('/api/notifications/stream', {
        // no auth header support in EventSource — use query param
      });
      es.addEventListener('document.processed', (e) => {
        const data = JSON.parse(e.data);
        addToast(`"${data.filename}" is ready`, 'success');
      });
      es.onerror = () => {
        es.close();
        setTimeout(connect, 5000); // reconnect after 5s
      };
    };
    connect();
    return () => es?.close();
  }, [token]);
}
```

**AppShell.jsx change** (one line in the authenticated render path):
```javascript
useNotificationStream(token);
```

### APIs Used
- `GET /api/notifications/stream` — existing endpoint, auth via JWT in header (need to verify EventSource auth method; may need cookie or query param since EventSource doesn't support custom headers)

### Auth Note
`EventSource` does not support custom `Authorization` headers in the browser. Options:
1. Pass token as query param: `/api/notifications/stream?token={jwt}` — requires backend to accept token in query string
2. Use a cookie for auth — requires changing auth model
3. Use `@microsoft/fetch-event-source` polyfill that supports headers — adds a JS dependency
**Recommended:** Option 1 (query param) — minimal backend change, no new dependencies, consistent with how the viewer uses token-based auth. Check if `get_current_user` in `notifications.py` already accepts query param tokens.

### Effort Estimate: 0.5 days
- New hook: 2–3 hours
- AppShell integration: 30 minutes
- Auth method verification and fix: 1 hour
- Toast message copy and testing: 30 minutes

### Risk Estimate: LOW
- No UX changes for users who don't have Redis configured (stream silently keeps-alive)
- Reconnect logic prevents zombie connections
- If EventSource fails, app works exactly as today (no degradation)
- Only risk: if the JWT query param approach requires backend change, that must be reviewed

---

## Plan 2 — API Keys

**Exposure method:** New screen `ApiKeysScreen.jsx` + DeveloperScreen wrapper + new nav item.

### Screen
- `src/screens/DeveloperScreen.jsx` (new) — tab container with "API Keys" and (later) "Webhooks"
- `src/screens/ApiKeysScreen.jsx` (new) — or inline as component in DeveloperScreen

### New Components
- `src/screens/DeveloperScreen.jsx` — tab host (~40 lines)
- `src/screens/ApiKeysScreen.jsx` — CRUD list (~180 lines)

### Implementation Sketch
```
DeveloperScreen (tab: 'apikeys' | 'webhooks')
└── ApiKeysScreen
    ├── Key list table (name, prefix, scopes badges, status, last_used, expiry)
    ├── [+ New API Key] button → inline form or modal
    │   ├── Name input
    │   ├── Scopes checkboxes (7 scopes from API_SCOPES)
    │   ├── Expiry date picker (optional)
    │   └── [Create] → shows full key ONCE with copy button + warning
    └── Per-row: [Revoke] toggle + [Delete] button
```

### APIs Used
```
GET    /api/api-keys            → list keys (masked)
POST   /api/api-keys            → create key (shows full key once)
PATCH  /api/api-keys/{id}       → revoke (set is_active: false) or rename
DELETE /api/api-keys/{id}       → delete key
```

### api.js Methods to Add (new methods in window.SecureDocAPI)
```javascript
listApiKeys()
createApiKey({ name, scopes, expires_at? })
revokeApiKey(id)   // PATCH is_active: false
deleteApiKey(id)
```

### AppShell.jsx Changes
```javascript
import { DeveloperScreen } from './DeveloperScreen.jsx';
// In navItems array (atoms.jsx):
{ id: 'developer', icon: '◈', label: 'Developer', badge: null }  // new nav group
// In render:
{screen === 'developer' && <DeveloperScreen />}
```

### atoms.jsx Change
Add a new nav group and item to the `navItems` array (the hardcoded sections at line 224).

### Effort Estimate: 1 day
- api.js methods: 1 hour
- DeveloperScreen tab shell: 1 hour
- ApiKeysScreen CRUD: 4–5 hours
- atoms.jsx nav item: 30 minutes
- Testing: 1–2 hours

### Risk Estimate: LOW
- New screen doesn't touch existing screens
- api.js additions are additive (no changes to existing methods)
- Nav item addition is additive
- The "key shown once" pattern requires clear UX copy — risk of confused users otherwise

---

## Plan 3 — Webhooks

**Exposure method:** Second tab in DeveloperScreen (built alongside API Keys).

### Screen
- `DeveloperScreen.jsx` (from Plan 2) — adds "Webhooks" tab
- `src/screens/WebhooksScreen.jsx` (new, ~250 lines)

### New Components
- `WebhooksScreen.jsx` — endpoint list + delivery log sub-view

### Implementation Sketch
```
WebhooksScreen
├── Endpoint list
│   ├── URL, description, events subscribed, active status
│   ├── [+ New Webhook] button → inline form
│   │   ├── URL input
│   │   ├── Description (optional)
│   │   ├── Event checkboxes (document.processed / link.viewed / analytics.completed)
│   │   └── [Create] → shows secret ONCE with copy button
│   └── Per-row: [Test] button + [Edit] inline + [Disable/Enable] toggle + [Delete]
└── Delivery log (click endpoint → expand or navigate to sub-view)
    ├── Table: event_type, status, attempts, response_status, timestamp
    └── Pagination (limit/offset)
```

### APIs Used
```
GET    /api/webhooks                     → list endpoints
POST   /api/webhooks                     → create endpoint
PATCH  /api/webhooks/{id}                → update URL/events/is_active
DELETE /api/webhooks/{id}                → delete endpoint
GET    /api/webhooks/{id}/deliveries     → delivery log (limit=50)
POST   /api/webhooks/{id}/test           → fire test ping
```

### api.js Methods to Add
```javascript
listWebhooks()
createWebhook({ url, events, description? })
updateWebhook(id, patch)
deleteWebhook(id)
getWebhookDeliveries(id, limit?)
testWebhook(id)
```

### Note on `link.viewed` event
The `link.viewed` event type is shown in the "event checkboxes" UI. However, the backend **never dispatches** this event (confirmed in Phase 1 audit — it is defined in WEBHOOK_EVENTS but `viewer.py` never calls `dispatch_webhook_event`). Users who subscribe to `link.viewed` will never receive a delivery. **The UI should either hide `link.viewed` from the event list, or show it as "coming soon."**

### Effort Estimate: 1.5–2 days
- api.js methods: 1.5 hours
- WebhooksScreen: 6–8 hours (list + delivery log sub-view is more complex)
- DeveloperScreen tab addition: 30 minutes
- Testing: 2 hours

### Risk Estimate: MEDIUM
- Secret shown once — same pattern risk as API Keys
- Delivery log is a read-only table (low risk)
- Test-fire button triggers a real HTTP request from the server — user needs a publicly accessible URL to test
- `link.viewed` event display decision required before implementation

---

## Plan 4 — Admin Audit Log

**Exposure method:** Tab inside OrganizationScreen (Plan 5). Can be shipped standalone as personal audit log if Organization feature is delayed.

### Screen Option A (with Organizations): Tab in `OrganizationScreen.jsx`
- `src/screens/OrganizationScreen.jsx` (new, Plan 5) — "Audit Log" as 4th tab
- Shows org-scoped events (requires org + admin/owner role)

### Screen Option B (standalone, personal): New tab in AnalyticsScreen or new section
- Add "Audit Log" tab to `AnalyticsScreen.jsx` (existing screen)
- Shows only own actions (no org_id query param) — useful for personal API key and link management history

### New Components (Option B standalone)
- `src/screens/analytics/AuditLogPanel.jsx` (~120 lines) — read-only table

### Implementation Sketch
```
AuditLogPanel
├── Filters: event_type dropdown (optional), date range (optional)
├── Table: timestamp | event_type | target_type | target_id
└── Pagination (load more button)
```

### APIs Used
```
GET /api/admin/audit-log              → personal events (no org_id)
GET /api/admin/audit-log?org_id={id}  → org events (admin/owner only)
```

### api.js Methods to Add
```javascript
getAuditLog({ org_id?, limit?, offset? })
```

### Effort Estimate: 0.5–1 day
- api.js method: 30 minutes
- AuditLogPanel component: 3–4 hours
- Integration into tab: 1 hour

### Risk Estimate: LOW
- Read-only, no mutations
- Empty state is common (no events logged without API keys or org actions)
- The personal audit log (no org_id) will show an empty table for most users until they create API keys or join an org

---

## Plan 5 — Organizations

**Exposure method:** New screen `OrganizationScreen.jsx` with 3 tabs.

### Screen
- `src/screens/OrganizationScreen.jsx` (new, ~350 lines)

### Tabs
1. **Settings** — org name, slug (read-only after set), is_active
2. **Members** — member table + add member + change role + remove
3. **Domain** — custom domain input + DNS TXT verification flow
4. **Audit Log** — (from Plan 4, added as tab 4)

### Implementation Sketch
```
OrganizationScreen
├── No-org state: "Create your first organization" prompt + create form
├── Org selector (if user belongs to multiple orgs)
└── Tabs:
    ├── Settings: name field, slug display, [Save] button, [Delete Org] button (owner only)
    ├── Members:
    │   ├── Member table: user_id (truncated UUID), role badge, invited_by, joined date
    │   ├── [+ Add Member] → input field for UUID + role select → [Add]
    │   │   ⚠️ UX WARNING: UUID input is poor UX. Display as "User ID (UUID)" with helper text.
    │   └── Per-member: role select (within actor's privileges) + [Remove] button
    ├── Domain:
    │   ├── Current domain display + [Edit]
    │   ├── Verification status badge (Verified / Not Verified)
    │   ├── [Get TXT Record] → shows record to add to DNS
    │   └── [Verify Now] button → calls POST /domain/verify
    └── Audit Log: (AuditLogPanel from Plan 4)
```

### APIs Used
```
GET    /api/orgs                          → list user's orgs
POST   /api/orgs                          → create org
PATCH  /api/orgs/{id}                     → update name/domain
DELETE /api/orgs/{id}                     → delete org
GET    /api/orgs/{id}/members             → list members
POST   /api/orgs/{id}/members             → add member (by UUID)
PATCH  /api/orgs/{id}/members/{uid}       → change role
DELETE /api/orgs/{id}/members/{uid}       → remove member
GET    /api/orgs/{id}/domain/token        → TXT record
POST   /api/orgs/{id}/domain/verify       → verify DNS
GET    /api/admin/audit-log?org_id={id}   → audit log tab
```

### api.js Methods to Add
```javascript
listOrgs()
createOrg({ name, slug? })
updateOrg(id, patch)
deleteOrg(id)
listOrgMembers(orgId)
addOrgMember(orgId, { user_id, role })
updateOrgMember(orgId, userId, { role })
removeOrgMember(orgId, userId)
getOrgDomainToken(orgId)
verifyOrgDomain(orgId)
```

### atoms.jsx Change
New nav item: "Organization" or "Team" (icon: ◫)

### UX Constraint
**Member add requires UUID** — there is no user lookup or email-based invitation in the backend. The UI must accept a raw UUID. This should be called out explicitly with a helper text like "Enter the SecureDoc user ID of the person you want to add." This is a known limitation and should be communicated to users.

### Effort Estimate: 3–4 days
- api.js methods (10 methods): 2–3 hours
- OrganizationScreen shell + tabs: 4 hours
- Settings tab: 2 hours
- Members tab (CRUD + role management): 4–5 hours
- Domain verification tab (multi-step flow): 3 hours
- Audit log tab (reuse AuditLogPanel): 1 hour
- Testing: 3 hours

### Risk Estimate: MEDIUM-HIGH
- Most complex screen in this plan
- Domain verification has external DNS dependency (failure modes)
- UUID-based member add will generate confusion and support tickets
- Last-owner protection handled server-side but UI should show clear error messaging
- Role permission UI must match server-side role_gte logic or users will see mysterious 403s

---

## Implementation Order (by effort and dependency)

| Order | Feature | Prerequisite | Estimated Effort |
|---|---|---|---|
| 1 | SSE Notifications (hook only) | None | 0.5 days |
| 2 | API Keys screen | None | 1 day |
| 3 | Webhooks screen | DeveloperScreen from step 2 | 1.5 days |
| 4 | Audit Log (standalone personal view) | None | 0.5 days |
| 5 | Organizations screen | None (but audit log tab reuses step 4) | 3 days |

**Total estimated frontend effort: ~6.5 days** to expose all 5 features with minimal viable UI.
SSE + API Keys alone takes **1.5 days** and delivers disproportionate value.
