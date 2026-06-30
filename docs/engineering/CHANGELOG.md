# Changelog

## [3.2.1] — 2026-06-30

### Added

**Organization Management**
- Invite members by email via new `POST /api/orgs/{org_id}/members/invite` endpoint (looks up user by email in Supabase, adds directly as member)
- Remove member button in MembersPanel (disabled for last owner)
- Inline role selector in MembersPanel (owner/admin/viewer, saves immediately)
- Member count displayed in panel header
- Empty state copy when org has no members yet

**Audit Log**
- Date-from and date-to filter inputs
- Event type dropdown filter (all known event types from `AUDIT_EVENT_TYPES`)
- "Apply Filters" and "Clear" buttons
- "Filtered" chip indicator when filters are active
- "↓ Export CSV" button — fetches up to 500 events and triggers browser download
- Filter-aware empty state copy ("No audit events match your filters")

**API Keys**
- Edit modal for changing key name and scopes (PATCH to existing endpoint)

**Webhooks**
- Edit modal for changing URL, description, and events (PATCH to existing endpoint)

**Confirmation Modals**
- Delete Organization: styled modal with warning banner
- Delete Group: styled modal with warning banner ("Documents will become ungrouped")
- Revoke Share Link: styled modal with confirmation
- Delete Share Link: styled modal with warning banner
- Quick Link (unrestricted): warning modal explaining no restrictions, "Create Anyway" required
- Revoke API Key: amber warning modal
- Delete API Key: red warning modal
- Delete Webhook: red warning modal

**API Client (`api.js`)**
- `updateApiKey(keyId, patch)` — PATCH `/api/api-keys/{keyId}`
- `inviteOrgMember(orgId, email, role)` — POST `/api/orgs/{orgId}/members/invite`
- `updateOrgMemberRole(orgId, userId, role)` — PATCH `/api/orgs/{orgId}/members/{userId}`
- `removeOrgMember(orgId, userId)` — DELETE `/api/orgs/{orgId}/members/{userId}`
- `getAuditLog` now accepts `{ dateFrom, dateTo, eventType }` filter params

**Backend**
- `GET /api/audit-log` now accepts `date_from`, `date_to`, `event_type` query params with validation
- `GET /api/audit-log` response now includes `available_event_types` list
- `GET /api/storage` response now includes `org_name` field per org entry

### Changed

**Atoms / Component Library**
- `Btn`: added `loading` prop — shows "…", sets `aria-busy="true"`, disables without strikethrough
- `Modal`: added `role="dialog"`, `aria-modal="true"`, `aria-label={title}` to dialog container
- `Field`: changed to `<label>` wrapping `<input>` for proper form field association

**Toast**
- Container now has `role="status"` and `aria-live="polite"` for screen reader announcements

**Share Links Screen**
- "+ Quick Share Link" renamed to "+ Quick Link" — makes destructive nature clearer
- "No feedback yet" empty state now reads: "No feedback yet. Viewers can leave comments when they view this document."

**Storage Screen**
- Org entries now show `org_name` (org display name) instead of raw UUID

**Analytics Screen**
- "organise" → "organize" (British → American English)

### Fixed

- Removed all `window.confirm()` calls — replaced with accessible `<Modal>` dialogs
- All table `<th>` elements now have `scope="col"` (UploadScreen, OrgsScreen, ApiKeysScreen, AuditLogScreen)
- All icon-only buttons now have `aria-label` (close buttons, rename, open-in-tab)
- `AuditLogScreen` now reads `ev.event_type` field with fallback to `ev.action`
- `MembersPanel` read-only view replaced with full management UI

### Security

- Zero-restriction share link creation now requires explicit user confirmation via warning modal
- `window.confirm()` replaced with `<Modal>` (browser dialogs can be spoofed; Modal cannot)
- New `/members/invite` endpoint: validates org membership, checks for existing member, enforces role allowlist, requires admin/owner JWT

### Not Changed

- Database schema (no new migrations)
- Authentication / JWT flow
- Redis / Celery pipeline
- Rasterization / streaming
- All existing API contracts
- Security controls (SSRF protection, content policy, watermarking)
- Backend test suite (1624 tests, all pass)

---

## [3.2.0] — (prior release)

V3.2 introduced parallel upload pipeline, link panel, viewer fit modes, and insights. See git log for details.
