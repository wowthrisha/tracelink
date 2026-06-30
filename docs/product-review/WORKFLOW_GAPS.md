# SecureDoc Workflow Gaps
**Date:** 2026-06-30  
**Method:** Full lifecycle tracing of all product workflows, comparing expected user journeys against actual frontend + backend capability

---

## Methodology

Each workflow is traced from start to finish. A "gap" is any point where:
- A logical next action is missing from the UI
- A backend capability exists but is not exposed
- A user expectation (from similar products) is unmet
- A flow requires workarounds

---

## Workflow 1: Document Upload & Organization

### Expected Flow
1. Upload document → see in document list → organize into group → share

### Actual Flow
1. Drag-drop file → upload begins → processing spinner (up to 5min polling) → document appears in list ✓
2. Create group → assign color ✓
3. Move document to group ✓ (via document card action)
4. Quick share from document card ✓

### Gaps
| Step | Gap |
|------|-----|
| Upload | No way to select multiple files at once (single file only per upload interaction) |
| Processing | Processing failure shows "Failed" with no error detail — user can't tell if it's a bad PDF or a server error |
| Organization | No bulk move to group |
| Organization | No folder/subfolder hierarchy — flat group structure only |
| Organization | No sort by date, name, size, or views in document table |
| Organization | No search within a group |
| Lifecycle | No document archiving (separate from deletion) — it's delete or keep |
| Lifecycle | No document versioning — re-uploading a new version creates a new document |

### Severity: HIGH — power users with 100+ documents will struggle to manage their library

---

## Workflow 2: Share Link Creation & Management

### Expected Flow
1. Select document → configure access policy → create link → share link → revoke when done

### Actual Flow
1. Select document in Upload screen → click "Access" or use QuickShare ✓
2. Access screen → Create Link tab → configure 7 permission toggles + 6 policy fields ✓
3. Click "Create Share Link" → link appears in Links tab ✓
4. Copy link URL ✓
5. Revoke individual link → fires immediately, no confirmation ✗

### Gaps
| Step | Gap |
|------|-----|
| Discovery | No way to navigate directly from a document card to "create share link" — must click through Access screen tab |
| Configuration | "⟳ New Share Link" button creates a zero-restriction link instantly — dangerous shortcut |
| Creation | Link created but no "copy link" button appears on the policy form — user must switch to Links tab |
| Sharing | No "send link via email" option in-app |
| Sharing | No QR code generation for the share link |
| Sharing | No expiry countdown shown on the link card |
| Sharing | Embed code is shown but no preview of what the embed looks like |
| Management | Cannot duplicate a link (to create a second link with same settings) |
| Revocation | Single-link revoke has no confirmation, but Revoke All does |
| Post-revoke | After revoking, viewer sees blurred page with no explanation |

---

## Workflow 3: Organization / Team Management

### Expected Flow
1. Create org → invite team members by email → assign roles → share documents with team → remove members when offboarded

### Actual Flow
1. Create org ✓
2. Invite team members — **IMPOSSIBLE** (frontend provides no UI) ✗
3. Assign roles — **IMPOSSIBLE** ✗
4. Share documents with team — **NOT CONNECTED** (documents have no org scoping in the UI) ✗
5. Remove members — **IMPOSSIBLE** ✗

### Backend Capability vs. Frontend Gap

| Backend API | Endpoint | Frontend Exposed? |
|-------------|----------|-----------------|
| Add member | POST /api/orgs/{id}/members | NO |
| List members | GET /api/orgs/{id}/members | YES (read-only) |
| Update member role | PATCH /api/orgs/{id}/members/{uid} | NO |
| Remove member | DELETE /api/orgs/{id}/members/{uid} | NO |
| Verify custom domain | POST /api/orgs/{id}/domain/verify | NO |
| Domain verify token | GET /api/orgs/{id}/domain/token | NO |

**Additionally:** The add_member API requires a user UUID, not an email address. There is no email-based invite flow in the backend. To add a member, you need to know their Supabase user ID. This means even if the frontend were built, the UX would be hostile.

### Severity: CRITICAL — Organizations are the foundation of enterprise accounts. This workflow is completely broken.

---

## Workflow 4: Viewer Analytics Investigation

### Expected Flow
1. Check dashboard for blocked attempts → identify suspicious document → drill into per-viewer activity → investigate specific session → tighten policy

### Actual Flow
1. Upload screen stats bar shows "Blocked Attempts" count (today only) ✓
2. Analytics → Overview → "Blocked today" KPI ✓
3. Analytics → By Document → shows blocked_attempts per document ✓
4. Click document in analytics → page heatmap (page-level views only) ✓
5. Per-viewer session drill: No such view — only aggregate data ✗
6. Navigate to Access screen for that document to see View History ✓
7. View History shows individual sessions ✓
8. Tighten link policy → Edit link ✓

### Gaps
| Step | Gap |
|------|-----|
| Analytics | No date range — all metrics are fixed (today / last 7 days) |
| Analytics | No way to filter by risk score |
| Analytics | "Blocked attempts" at document level doesn't show WHO was blocked |
| Analytics → Access | No direct link from analytics document row to Access screen for that document |
| Per-viewer | No per-viewer analytics — can't see one viewer's session history across documents |
| Per-session | View History in Access shows sessions but no per-page time distribution |
| Export | No export from View History tab — only from Analytics screen |

---

## Workflow 5: API Integration (Programmatic Access)

### Expected Flow
1. Create API key → add to integration → make API calls → rotate key when needed

### Actual Flow
1. Create API key with scopes ✓
2. Copy key (shown once) ✓
3. Use in integration ✓
4. Rotate key: delete old key → create new key → update integration ✗ (no atomic rotation)

### Gaps
| Step | Gap |
|------|-----|
| Scopes | No scope documentation on the UI — developer must infer scope meaning from names |
| Rotation | No "rotate" action — must delete and recreate, causing downtime for any running integration |
| Testing | No API playground or "test this key" button |
| Expiry | No expiry date option — keys are permanent until manually revoked |
| IP restriction | No IP allowlist for API keys (exists for share links but not keys) |
| Audit | API key "Last used" shows relative time but doesn't show which endpoint was last called |

---

## Workflow 6: Webhook Integration

### Expected Flow
1. Register webhook → test it → receive events → investigate delivery failures → rotate secret if compromised

### Actual Flow
1. Register webhook URL + events ✓
2. Copy signing secret (shown once) ✓
3. Send test ping ✓
4. View delivery history ✓
5. Investigate failure: see HTTP status code in delivery history ✓, no response body ✗
6. Rotate signing secret: must delete and recreate webhook — all history lost ✗

### Gaps
| Step | Gap |
|------|-----|
| Event coverage | Only 3 events — missing 10+ lifecycle events |
| Edit | Cannot edit webhook URL or event subscriptions after creation |
| Retry | Cannot manually replay a failed delivery |
| Secret rotation | No secret rotation endpoint — must delete and recreate |
| Response body | Delivery history shows HTTP code but not response body — hard to debug failures |
| Pagination | Delivery history has no pagination — only most recent N deliveries shown |

---

## Workflow 7: Compliance Audit

### Expected Flow
1. Receive compliance request → filter audit log by date range, actor, action type → export to CSV/JSON → submit to auditor

### Actual Flow
1. Navigate to Audit Log ✓
2. Filter by date range: **NOT POSSIBLE** ✗
3. Filter by actor: **NOT POSSIBLE** ✗
4. Filter by action type: **NOT POSSIBLE** ✗
5. Export to CSV: **NOT POSSIBLE** ✗
6. Load more (50 per page): partial workaround, requires manual scrolling

### Severity: CRITICAL for any SOC 2 or compliance-driven enterprise customer

---

## Workflow 8: Viewer Feedback Review

### Expected Flow
1. Share document for review → reviewer leaves comments → owner reviews, replies, resolves → export feedback summary

### Actual Flow
1. Create link with `can_annotate: true` ✓
2. Viewer leaves comments in viewer ✓
3. Owner opens Access → Feedback tab ✓
4. Owner sees all comments with reviewer name and page ✓
5. Owner replies inline ✓
6. Owner resolves individual threads ✓
7. Export: "Export Feedback Conversations" available ✓
8. Export "Reviewer Activity" available ✓

### Gaps
| Step | Gap |
|------|-----|
| Discovery | Feedback badge on sidebar is count-only — can't tell which document has new feedback without clicking through |
| Feedback screen | 'feedback' in sidebar routes to AccessScreen with no document pre-selected — unclear which document's feedback you'll see |
| Search | No search within feedback text |
| Bulk | No bulk resolve all |
| Status | No way to mark a thread as "in progress" or "needs clarification" — only open/resolved binary |
| Notification | No email notification when viewer leaves feedback — only in-app activity feed |

---

## Workflow 9: Storage Management

### Expected Flow
1. Monitor storage growth → identify large documents → set retention policies → receive warning before deletion

### Actual Flow
1. Storage screen → total storage, 30/90 day projections ✓
2. Per-document size and retention policy ✓
3. Set retention: select from dropdown (Never, 30/60/90 days) ✓
4. Deletion warning: there is none — documents expire silently ✗

### Gaps
| Step | Gap |
|------|-----|
| Quota | No storage quota shown — user can't tell how close they are to a limit |
| Expiry warning | No email or notification when a document is about to expire due to retention policy |
| Bulk retention | No bulk set retention policy |
| Archive | No "archive" state visible in UI flow — lifecycle states exist (active/archived/expired) but no way to archive manually |

---

## Workflow 10: Account Lifecycle (First-time User Onboarding)

### Expected Flow
1. Sign up → verify email → arrive at app → guided onboarding → upload first document

### Actual Flow
1. Sign up → "Check your inbox" message → (email arrives, user clicks) → arrive at app
2. Land on Upload screen (upload is the default screen) ✓
3. No onboarding checklist, no guided tour, no empty state CTA buttons

### Gaps
| Step | Gap |
|------|-----|
| Post-signup | No email verification status shown — user can attempt sign-in while unverified |
| Onboarding | No checklist or tour: "Upload a document → Create a share link → View analytics" |
| First doc | Empty state has text but no embedded "Upload" button to trigger the file picker |
| First share | No "share your first document" prompt after successful upload |

---

## Workflow Summary

| Workflow | Status | Severity |
|----------|--------|----------|
| Document upload & organization | Partial — no bulk, no sort | High |
| Share link creation & management | Partial — silent unrestricted create button | High |
| Organization / team management | **BROKEN** — members cannot be added | Critical |
| Analytics investigation | Partial — no date range, no per-viewer drill | High |
| API integration | Partial — no rotation, no scope docs | Medium |
| Webhook integration | Partial — no edit, no replay, 3 events only | Medium |
| Compliance audit | **BROKEN** — audit log has no filters or export | Critical |
| Viewer feedback review | Good — minor gaps | Low |
| Storage management | Partial — no quota, no expiry warnings | Medium |
| New user onboarding | Weak — no guided flow | High |

---

*Workflow gaps analysis complete — 2026-06-30*
