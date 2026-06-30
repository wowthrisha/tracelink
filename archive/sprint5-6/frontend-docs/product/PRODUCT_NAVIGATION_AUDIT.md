# Product Navigation Audit — Sprint 4.8B Phase 1

**Method:** Source code trace of `atoms.jsx` (Sidebar, NAV_SECTIONS, Header), `AppShell.jsx` (screen routing), all screen components, and `DocRow.jsx` (in-row navigation triggers).  
**Roles:** Founder · Product Manager · Paying Customer · UX Reviewer · Staff Engineer

---

## Current Navigation Architecture

### Routing mechanism

`AppShell.jsx:29–30`: `const [screen, setScreen] = useState('upload')` — single string drives the entire app. No URL routing. Every screen change is an in-memory `setScreen()` call.

**Implication:** Browser back/forward buttons do nothing. Refreshing the page always returns to Upload. Sharing a deep link to Analytics or a specific document is impossible. This is the most structurally significant navigation gap in the product.

---

### Sidebar Structure (atoms.jsx:222–263)

```
[no label]
  ⊕  Upload
  ◫  Viewer

Security
  ◈  Access Control

Insights
  ▦  Analytics
  ◻  Storage

Developers
  ⌗  API Keys
  ⇌  Webhooks
  ≡  Audit Log

Workspace
  ◉  Organizations
  ◎  Notifications

Account
  ◇  Billing
```

**Total items:** 12 across 6 sections. Every item is visible at identical visual weight on first login. There is no collapse, no fold, no progressive disclosure.

---

## Screen-by-Screen Navigation Analysis

### Upload (screen: `upload`)

**What it is:** Document library + upload zone + group management  
**What its name implies:** A place to upload files  
**Navigation from here:**
- Row click → Viewer (`onView`)
- "Access" hover button → Access Control (`onAccess`)
- "↗ Share" hover button → QuickShareModal (overlay, no screen change)
- After upload completes: "Configure Access →" button → Access Control

**Dead ends:** None — all actions lead somewhere  
**Hidden actions:** QuickShare is hover-only. On a first visit with no documents, the groups filter strip is invisible. The `⌕ Filter` button at `UploadScreen.jsx:204` fires `toast('Search feature coming soon', 'info')` — a non-functional stub in a visible primary header position.

**Navigation confusion:**
- The "Upload" sidebar label implies this is a one-time action page, not the home screen / document library.
- After upload, "Configure Access →" opens Access Control — a security-flavored label for what is actually "share this document."

---

### Viewer (screen: `viewer`)

**What it is:** Full-screen document viewer with toolbar  
**Navigation from here:**
- "← Docs" back button (added in 4.8A) → Upload screen
- No link to Access Control for the current document
- No link to Analytics for the current document

**Dead ends (remaining):**
- A user who wants to share the document they're viewing has no path to do so from within the Viewer. They must leave to Upload, find the document, hover, and click Share.
- A user who wants to see who has viewed the document must leave to Access Control. No breadcrumb, no shortcut.
- `activeDoc` is preserved on "← Docs" navigation, but if the user then navigates to Analytics or Storage via sidebar, `activeDoc` is not cleared. Returning to Viewer shows the previous document silently — correct behavior, but not communicated.

---

### Access Control (screen: `access`)

**What it is:** 5-tab screen — Policy, Share Link, Access Log, Feedback, Annotations  
**What its name implies:** Security/permission management  
**Navigation from here:**
- No link back to Viewer for the current document
- No link to Analytics for the current document
- Tabs: Policy, Share Link, Access Log, Feedback, Annotations

**Navigation confusion:**
- "Feedback" and "Annotations" are not access control concepts. A paying customer managing viewer feedback has to navigate through a screen labeled "Access Control" and "Security" to reach a feedback review workflow. This is the most significant labeling mismatch in the product.
- "Access Log" (tab) and "Audit Log" (sidebar item) are easily confused. Both show logs. Access Log shows per-document viewer events. Audit Log shows admin-level system events. These names do not distinguish their purposes.

**Structural issue:** The Access Control screen is doing 4 jobs:
1. Link policy creation (Policy tab)
2. Link management (Share Link tab)
3. View history (Access Log tab)
4. Viewer feedback management (Feedback tab)
5. Viewer annotations review (Annotations tab)

A consultant managing feedback does not think "I need to go to Security → Access Control to read comments." This is a discoverability failure.

---

### Analytics (screen: `analytics`)

**What it is:** Engagement metrics — KPIs, per-document views, per-group views, page heatmap  
**Navigation from here:** None (no cross-links to documents or Access Control)  
**Dead ends:** Clicking a document name in the analytics table (`DocAnalyticsRow`) does nothing — it's display-only. A PM wants to click "see this document's share links" from the analytics view and cannot.

---

### Storage (screen: `storage`)

**What it is:** Per-document storage breakdown with retention policy controls  
**Navigation from here:** None  
**Structural note:** Storage belongs under "Insights" alongside Analytics — correct grouping. But the screen is entirely disconnected: clicking a document row does nothing. A user who wants to delete a high-storage document must navigate back to Upload and find it there.

---

### API Keys, Webhooks, Audit Log (screen: `apikeys`, `webhooks`, `auditlog`)

**What these are:** Developer integrations and admin logging  
**Navigation from here:** None  
**Structural concern:** These three screens are shown at identical visual weight to Upload and Viewer for every user including non-technical founders and consultants. A first-time user sees "API Keys" and "Webhooks" in the primary navigation as peer items to the core document workflow.

---

### Organizations (screen: `orgs`)

**What it is:** Create/rename/delete orgs, read-only members panel  
**Navigation from here:** None  
**Dead end:** The members panel is read-only. Adding a member requires a raw Supabase UUID. There is no user search. This screen reaches a functional dead-end immediately after creation.

---

### Notifications (screen: `notifications`)

**What it is:** Polled event feed (30s interval, `document.processed`, `link.viewed`, `analytics.completed`, `link_view`, `download`)  
**What the label implies:** Push notification settings / alert preferences  
**Dead ends:** Event entries are display-only. Clicking a notification about a document that was viewed does not navigate to that document's Access Control or Analytics. It is a read-only activity log, not a notification center.

---

### Billing (screen: `billing`)

**What it is:** Plan status, upgrade/downgrade  
**Navigation from here:** Stripe redirect on upgrade — external  
**No dead ends.**

---

## Navigation Defect Summary

| # | Screen | Issue | Severity |
|---|--------|--------|----------|
| 1 | All | No URL routing — browser back/forward broken | Critical |
| 2 | Upload | Screen label says "Upload"; it is the document library home | High |
| 3 | Upload | `⌕ Filter` stub fires "coming soon" toast (`UploadScreen.jsx:204`) | High |
| 4 | Upload | "Configure Access →" after upload navigates to a security-flavored screen for a sharing workflow | Medium |
| 5 | Access Control | Feedback and Annotations are in the "Security" section | High |
| 6 | Access Control | No path back to Viewer for the current document | Medium |
| 7 | Access Control | "Access Log" (tab) vs "Audit Log" (sidebar) — overlapping names, different data | High |
| 8 | Viewer | No path to share current document (must leave to Upload) | Medium |
| 9 | Viewer | No path to view analytics for current document | Low |
| 10 | Analytics | Document rows are non-navigable (click does nothing) | Medium |
| 11 | Storage | Document rows are non-navigable (click does nothing) | Low |
| 12 | Notifications | Name implies push alert center; it is a polled activity log | High |
| 13 | Sidebar | 12 items at uniform weight — Developers section visible to all users | High |
| 14 | Sidebar | "Viewer" and "Upload" in unlabeled section; inconsistent with other labeled sections | Low |
| 15 | All | `activeDoc` context not communicated when switching screens | Low |

---

## Duplicate Navigation

- **"Access Log"** (tab inside Access Control) and **"Audit Log"** (sidebar item): both show log data. Different data sets, identical vocabulary.
- **"Notifications"** (sidebar) and **"Audit Log"** (sidebar): both show event history. Notifications = user events. Audit Log = admin actions. No visual distinction.
- **"Share" button** (DocRow hover) and **"Share Link" tab** (Access Control): two different paths to create share links. The hover button is faster but undiscoverable.

---

## Hidden Screens / Features

| Feature | How to reach it | Discoverability |
|---------|----------------|-----------------|
| QuickShare | Hover over document row → click "↗ Share" | Hidden — no indication until hover |
| Feedback | Sidebar → Access Control → Feedback tab | Two clicks inside a security-named screen |
| Annotations | Sidebar → Access Control → Annotations tab | Two clicks inside a security-named screen |
| Edit Link | Sidebar → Access Control → Share Link tab → Edit button | Three navigations from home |
| Page heatmap | Sidebar → Analytics → select document in table | Non-obvious |

---

*Generated: Sprint 4.8B Phase 1 — no implementation performed.*
