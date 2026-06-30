# SecureDoc UX Review
**Date:** 2026-06-30  
**Reviewer Persona:** Senior UX Researcher + Principal UX Designer  
**Method:** Full read-through of all 13 screens, interaction model analysis, comparison to industry patterns (Stripe, Notion, Dropbox, DocSend, GitHub)

---

## UX Principles Applied

1. **Progressive disclosure** — show complexity only when needed
2. **Confirmation before destruction** — irreversible actions must confirm
3. **Empty states that teach** — guide users to the next action
4. **Consistency** — same interaction pattern for similar actions
5. **Error prevention over error recovery** — make the wrong action harder than the right one
6. **Feedback on every action** — immediate, specific responses

---

## Information Architecture

### Navigation Model

The sidebar has 11 items: Documents, Viewer, Access, Analytics, Storage, API Keys, Webhooks, Audit Log, Orgs, Notifications, Billing.

**UX Finding:** The sidebar conflates two categories of nav items without visual separation:
- **Document workflows:** Documents, Viewer, Access, Analytics
- **Account/settings:** Storage, API Keys, Webhooks, Audit Log, Orgs, Notifications, Billing

Industry standard (Stripe, GitHub) separates these into primary nav and settings. A first-time user cannot tell whether "Storage" refers to their documents' storage or an integration.

**Recommendation:** Group sidebar items with a thin section divider: "Documents" group at top, "Developer" group (API Keys, Webhooks), "Account" group (Storage, Orgs, Billing, Audit Log, Notifications).

---

### Screen State & URL Routing

**Critical UX Failure:** The app has no URL routing. Every page refresh returns to the Upload (Documents) screen regardless of where the user was. Deep linking to a specific document's analytics is impossible.

Comparison:
- Stripe: every page has a unique URL (`/customers/cus_xxx/invoices`)
- GitHub: deep linking to any repo, PR, or issue works
- SecureDoc: every URL is identical — `localhost:8000`

**Impact:** Support tickets will commonly say "I was on [screen] and refreshed and lost everything." Enterprise admins expect to bookmark specific views.

---

## Per-Screen UX Analysis

### Login Screen

**Grade: B+**

Good: Clean minimal layout, mode switching is smooth, "forgot password" is inline not a separate page.

Issues:
- The "spam folder" hint appears after signup but there's no indication of how long confirmation takes
- After password reset success, user is auto-switched to login mode but the success message disappears — user might not see it before it clears
- No visual hierarchy between the logo area and the form — both compete for attention at the same weight

**Pattern comparison:** Stripe's login puts the CTA (sign in / continue) at maximum visual weight. SecureDoc's submit button is the same visual weight as the mode switcher — cognitive load to find "what do I click."

---

### Upload / Documents Screen

**Grade: B**

Good: Stats bar gives immediate context, drag-drop zone is clear, processing state is communicated with a spinner.

Issues:

**Empty state quality:** "No documents yet — upload your first PDF above" is functional but passive. Compare:
- Notion: "Get started by creating a page" with a CTA button embedded in the empty state
- Dropbox: Animated illustration + "Drag files here or upload" with a prominent button
- SecureDoc: Text only, no illustration, no CTA button embedded

**Sort and filter:** The document table has a search bar but no sort controls. Enterprise users with 100+ documents need to sort by date uploaded, file name, or view count. DocSend solves this with column-header clicking.

**Group management UX:**
- Group delete fires immediately — the most dangerous action in the group management UI has no friction. Deleting a group with 30 documents in it is irreversible.
- The group rename flow (pencil icon) is inconsistent with the link rename flow (pencil icon in AccessScreen). Both use similar UX but different styling.

---

### Viewer Screen

**Grade: A-**

This is the strongest screen in the product. The toolbar is well-organized, the search panel is clean, the two-page mode is a thoughtful premium feature.

Issues:

**Blocked DRM state:** When a viewer tries to print/copy and it's disabled, they get silently blocked. The industry standard (Scribd, DocSend) shows a brief overlay or message: "Printing is disabled for this document." SecureDoc's implementation just... prevents the action. Users will think the browser is broken.

**Session blur:** When the session becomes invalid (max views reached, revoked, expired), the document blurs. This is a correct security behavior but there's no message on the blurred overlay explaining why. Users see a blurred document with no explanation.

**Mobile block:** Blocking mobile at 768px is understandable for beta, but the message says "Mobile support is planned for a future release" — this needs to be removed or updated before any marketing or customer-facing use. Telling a customer "mobile doesn't work" during a sales demo is a deal-killer.

---

### Access Screen (Share Link Management)

**Grade: B+**

This is the most feature-rich screen and is generally well-designed. The tabbed interface works well.

Issues:

**Action hierarchy problem:** The "Create Link" tab has TWO create buttons:
1. "Create Share Link" — creates a link with all the configured policies
2. "⟳ New Share Link" — creates a link with ZERO restrictions instantly

A user scanning for "how do I create a link" sees both buttons and is confused about which one to use. The unrestricted link button should either be removed or moved to a clearly secondary position with a warning.

**Revoke hierarchy problem:** 
- Revoking ALL links: proper confirmation modal with excellent warning copy ✓
- Revoking ONE link: fires immediately with no confirmation ✗
- Deleting a link: `window.confirm()` ✗

Three different UX patterns for three similar actions. This is inconsistency that erodes trust.

**Feedback tab empty state:**  
"No feedback yet — viewers need can_annotate permission enabled"  
This is wrong. Text comments (`comment` type) are separate from visual annotations. A viewer with `can_annotate: false` can still leave a comment if the comment type isn't `annotate`. The empty state misleads the owner about what permission controls feedback.

---

### Analytics Screen

**Grade: B-**

Good information density. The page heatmap is a standout feature.

Issues:

**No date range:** The "last 7 days" sparkline and all aggregate numbers have no date picker. DocSend allows 7d, 30d, 90d, all-time, custom range. This is the #1 analytics UX gap — a user preparing a board report needs to know Q1 numbers, not just last 7 days.

**Undefined metrics:** The UI shows "Completion" and "Risk" as KPIs and table columns but never defines them. Enterprise buyers will ask "what is a 7.4% completion rate?" in their first demo. The answer needs to be one click away (a tooltip, a ? icon, a docs link).

**Click to document:** The "By Document" tab shows document filenames with analytics. There's no link from a document in the analytics table to that document's Access screen. The workflow "I saw this document has high blocked attempts → I want to tighten its policy" requires the user to manually navigate away.

---

### Organizations Screen

**Grade: F**

As documented in PRODUCT_REVIEW.md, this screen cannot fulfill its stated purpose. An organization with no members is meaningless. The members panel shows "No members" with no way to add any.

UX pattern comparison:
- GitHub Organizations: member invite by email, role assignment, pending invites list
- Notion: invite by email with permission levels (full access, edit, view)
- Linear: invite by email with team-level roles
- SecureDoc: displays member list (read-only). Cannot invite. Cannot change roles. Cannot remove.

The empty state "No members in this organization." is particularly bad UX — it identifies a problem (no members) but provides no path to solving it.

---

### API Keys Screen

**Grade: B**

The key-reveal-once pattern is handled correctly with good copy ("Copy this key now. It will not be shown again.").

Issues:

**Scope selection UX:** The 7 scopes are presented as bare code strings:
`documents:read`, `documents:write`, `links:read`, `links:write`, `analytics:read`, `webhooks:read`, `webhooks:write`

There are no descriptions. A developer integrating for the first time needs to know: "if I'm building a document viewer integration, which scopes do I need?" GitHub and Stripe show a description for each scope on the permission selection screen.

**Revoke vs Delete semantics:** The UI shows both "Revoke" and "Delete" for active keys. The difference is subtle:
- Revoke = deactivate but keep record
- Delete = remove permanently

These need UI-level explanation. The current UI provides no hint.

---

### Webhooks Screen

**Grade: B+**

Solid implementation. The delivery history panel is a genuine power-user feature.

Issues:

**Only 3 events:** The event selection is `document.processed`, `link.viewed`, `analytics.completed`. Notably absent:
- `link.created` — when a new share link is created
- `link.revoked` — when a link is revoked
- `document.deleted` — when a document is deleted
- `org.member_added` — team membership events

This limits the use case of webhooks significantly for real integrations.

**Cannot edit after creation:** A common workflow is "I registered a webhook to the wrong URL." The only path is delete and recreate, losing the delivery history in the process.

---

### Audit Log Screen

**Grade: C**

The data is there but it's completely unfiltered. With 10,000 events, "Load more" at 50 per page means 200 clicks to reach old records.

**No search:** The audit log is the primary compliance and security investigation tool. Enterprise security teams need to search: "show me all delete actions by user X between Jan 1 and Jan 31." SecureDoc shows 50 rows with a Load More button.

Comparison:
- Stripe: audit log has actor filter, event type filter, date range filter, CSV export
- AWS CloudTrail: event filter by user, resource, time range, event type, search
- SecureDoc: time descending, 50 per page, load more

---

### Storage Screen

**Grade: B-**

The per-document retention policy is a genuine enterprise-grade feature.

Issues:

**Org name not shown:** The "Storage by Organization" section shows `org_id.slice(0, 8) + "…"` instead of the org name. This is a hardcoded bug — the org name is available in the response and should be used here.

**No quota display:** Users don't know what their storage limit is or how close they are. Even the Pro plan features list says "Unlimited" for documents but makes no mention of a storage cap. Is there one?

---

### Billing Screen

**Grade: C+**

The functional billing flow (checkout → Stripe, manage → portal) works. But the screen itself is extremely sparse.

**Price is hidden:** "Upgrade to Pro" redirects to Stripe. The actual price is never shown on this screen. This is intentional for pricing flexibility, but it means users cannot comparison-shop without clicking through.

**No usage display:** "Document uploads: Up to 10" is on the features list, but there's no counter showing the user's actual usage (e.g., "7 / 10 documents used"). Notion, Linear, and Stripe all show this.

---

### Notifications Screen

**Grade: C+**

The feed design is clean. The 24-event type mapping is complete.

Issues:

**50-item limit:** There are 24 event types and potentially 100+ document views per day. The 50-item feed fills up quickly and becomes a "most recent 50" log rather than a notification system. There's no "load more" on this screen.

**No filtering:** A user with 5 documents wants to see activity for just one. No document filter exists.

**localStorage for read state:** "Mark all read" persists the timestamp in localStorage. This means:
- Opening a new browser tab resets the "new" state
- Opening the app on a different device shows everything as new again
- Clearing browser data resets the counter

This is the wrong persistence layer. Read state should be stored server-side.

---

## Interaction Pattern Consistency Audit

| Action | Upload | Access | API Keys | Webhooks | Orgs |
|--------|--------|--------|----------|---------|------|
| Delete with confirmation modal | ✓ (doc) | ✗ (link) via `window.confirm()` | ✗ no confirm | ✗ no confirm | ✗ no confirm |
| Delete with NO confirmation | ✓ (group) | N/A | ✓ | ✓ | ✓ |
| Revoke with confirmation | N/A | ✗ (single link) | ✗ | N/A | N/A |
| Revoke with confirmation modal | N/A | ✓ (all links) | N/A | N/A | N/A |

**Pattern finding:** There are 5 distinct patterns for "destructive action confirmation" across the product. The only consistent rule appears to be "Revoke All" gets a modal. Every other destructive action is inconsistent.

**Recommendation:** Adopt one pattern:
- **Minor-destructive** (revoke single key/link): inline undo toast for 5 seconds
- **Major-destructive** (delete, org delete, group delete): confirmation modal with action name typed
- **Critical** (revoke all): current pattern is correct ✓

---

## Empty State Quality Audit

| Screen | Empty State Copy | Has CTA? | Grade |
|--------|----------------|----------|-------|
| Documents — no docs | "No documents yet — upload your first PDF above" | ✗ No embedded CTA | C |
| Documents — no search results | "No documents match your search" | ✗ | B |
| Orgs — no orgs | "No organizations yet." | ✗ No CTA, no instructions | D |
| Orgs — no members | "No members in this organization." | ✗ No invite button | F |
| API Keys — no keys | "No API keys yet. Create one to enable programmatic access." | ✗ | B |
| Webhooks — no webhooks | "No webhooks registered yet." | ✗ | C |
| Webhooks — no deliveries | "No deliveries yet. Events will appear here when fired." | N/A | B |
| Audit Log — no events | "No audit events yet." | N/A | B |
| Notifications — no events | "No activity yet. Activity will appear here as your documents are accessed." | N/A | B |
| Access — no links | "No share links yet — create one in the Create Link tab." | ✗ No button | B+ |
| Analytics — no groups | "No groups created yet / Create groups in the Documents screen to organise your files" | ✗ No link to Documents | B |

**Summary:** Only 2/11 empty states have navigation guidance. None embed a CTA button. Notion, Linear, and Stripe all embed a primary action button in every empty state.

---

## UX Score Card

| Category | Score (out of 10) | Notes |
|----------|-----------------|-------|
| Visual design / design language | 8/10 | Consistent dark theme, good density |
| Navigation structure | 6/10 | No URL routing, no nav grouping |
| Empty states | 4/10 | Passive text, no CTAs |
| Confirmation dialogs | 3/10 | Wildly inconsistent |
| Error states | 6/10 | Toast system works well |
| Loading states | 7/10 | Loading spinners present throughout |
| First-time user experience | 5/10 | Good upload flow, poor onboarding |
| Power user experience | 7/10 | Good keyboard shortcuts in viewer, good analytics |
| Mobile experience | 0/10 | Blocked entirely |
| Accessibility | 3/10 | See ACCESSIBILITY_REVIEW.md |
| **Overall** | **4.9/10** | Production-capable for desktop power users; needs work for enterprise |

---

*UX Review complete — 2026-06-30*
