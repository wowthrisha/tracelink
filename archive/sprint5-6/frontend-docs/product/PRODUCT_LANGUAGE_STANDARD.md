# Product Language Standard — Sprint 4.8B Phase 2

**Method:** Every term below was identified by reading actual UI labels, tab names, button labels, section headers, API endpoint names, and sidebar items across all source files.  
**Goal:** One vocabulary across the product. Each concept has exactly one name.

---

## Full Terminology Audit Table

| Term Used | Screen / Location | Meaning | Conflict | Recommended Standard |
|-----------|------------------|---------|----------|----------------------|
| **Upload** | Sidebar nav item | The home screen / document library (not a one-time upload action) | Screen name implies action, not place. Conflicts with "↑ Upload PDF" button on same screen | **Documents** (screen name); keep "Upload" only for the button |
| **Viewer** | Sidebar nav item | Document reading experience | "Viewer" is both the screen name and the concept of a person who views a shared document (`viewer_email`, "Viewer" role in Access Log) | **Read** or **Open** for the screen; **Reader** for the person role (avoid reusing "Viewer") |
| **Access Control** | Sidebar nav item, Header title | Screen containing link policy, share links, access log, feedback, and annotations | The name implies security; the screen contains feedback and annotations which are collaboration features, not security | **Share & Manage** or **Document Hub** — captures policy, sharing, viewing history, and feedback in one label |
| **Policy** | Tab inside Access Control | A form to create a NEW share link with restrictions (not to edit an existing link's policy) | "Create New Link" button was added in 4.8A but the tab is still called "Policy" — now misnamed since the tab creates links, not policies | **Create Link** or **New Share Link** |
| **Share Link** | Tab inside Access Control | List of existing share links for the document | Conflicts with "↗ Share" button on document rows (which creates a link immediately via QuickShare) | **Links** (tab name); "Quick Share" for the hover button |
| **Share** | `DocRow.jsx:64` hover button label ("↗ Share") | Opens QuickShareModal — creates a link instantly with default permissions | "Share" also appears in "Share Link" tab, in "Create New Link" flow, and in the concept of sharing generally | **Quick Share** (button label matches modal name) |
| **Access Log** | Tab inside Access Control | Per-document viewer session history: who opened the link, when, from where | Nearly identical to "Audit Log" (sidebar item). Users distinguish these only by knowing the content — names give no clue | **View History** (tab) |
| **Audit Log** | Sidebar nav item | Admin-level system event log: create/update/delete/login actions across the account | Overlaps with "Access Log" — both are logs, neither name distinguishes purpose | **Activity Log** (sidebar) or **System Log** |
| **Notifications** | Sidebar nav item, Screen title | Polled event feed (30s): link_view, document.processed, download events | "Notifications" implies push alerts or preferences. This is an activity stream. Conflicts with webhook "Events" (`ALL_EVENTS` in `WebhooksScreen.jsx:7`) | **Activity** or **Event Feed** |
| **Event** | `WebhooksScreen.jsx:7` (`ALL_EVENTS`), `NotificationsScreen.jsx:23` (`eventLabel`), `AuditLogScreen.jsx:16` (`ACTION_COLORS`) | Three different things: (1) webhook trigger types, (2) activity feed entries, (3) audit log actions | All three screens use "event" for different data shapes | Webhook trigger types → **Trigger**; activity feed rows → **Activity**; audit log rows → **Log Entry** |
| **Feedback** | Tab inside Access Control | Viewer-submitted comments and sticky notes on the document | No conflict in naming, but the location (inside "Access Control" / "Security") is incongruent | **Feedback** (name is correct; location is wrong — see navigation audit) |
| **Annotations** | Tab inside Access Control | Viewer-submitted visual marks: highlight, draw, rectangle, arrow | Separate from "Feedback" (comments/sticky notes) but both are viewer-submitted content | **Annotations** (name is correct; consider grouping Feedback + Annotations under one "Viewer Activity" or "Comments & Marks" section) |
| **Analytics** | Sidebar nav item, Screen title | Engagement metrics: views, sessions, completion rates, page heatmap | No conflict | **Analytics** (keep) |
| **Group** | `UploadScreen.jsx:230` label, DocRow group dropdown, `getGroups()` API | Document folder / category (flat, user-defined, color-coded) | "Group" also appears in Analytics ("by group" tab, `getGroupAnalytics()`). Consistent. | **Group** (keep — consistent across Upload, Analytics, Storage) |
| **Organization** | Sidebar nav item ("Organizations"), `OrgsScreen.jsx` | A workspace / team container (`org_id` on documents and links) | "Org" (abbreviated) appears in Storage screen org breakdown, API (`/api/orgs`), and model. Full word used in UI. | **Organization** (full) in UI; **org** in API and code (already consistent) |
| **Link** | Used everywhere (share link, link card, link policy, link ID, edit link) | A share URL with access policy attached | Not conflated with hyperlinks (which are called "hyperlinks" in the Viewer links sidecar panel). Consistent. | **Link** (keep for share links); **Hyperlink** (viewer hyperlinks — already differentiated) |
| **Risk** | `DocRow.jsx:49`, `AccessScreen.jsx:211`, `AnalyticsScreen.jsx` — badge HIGH/MED/LOW | Document-level risk score (computed from link activity, view count, access restrictions) | Criteria for HIGH/MED/LOW are never displayed in the UI. Risk badge appears without any tooltip or explanation | **Risk** (keep label) — add tooltip explaining criteria |
| **Review** | Not currently used | — | "Feedback" is used for what other products call document review | No action needed — just do not introduce "Review" as a new term |
| **Quick Share** | `QuickShareModal.jsx`, DocRow "↗ Share" button (label is "Share") | Instant one-click link creation with secure defaults | The button says "Share" but the modal title and component name say "Quick Share" — inconsistent | **Quick Share** on the button AND the modal — align both |
| **Viewers** | `AccessScreen.jsx:569` (`viewer_email`), `NotificationsScreen.jsx:36` (`ev.viewer_email`), Access Log column | People who open a shared document via a link | Conflicts with "Viewer" (sidebar item = screen name) | **Viewer** for the role is fine — sidebar item should change to avoid collision (see above) |
| **Status** | Feedback tab column showing "Open" / "Resolved" | Resolution state of a feedback thread | No conflict | **Status** (keep) |
| **Configure** | `UploadProgressPanel.jsx:25` — "Configure Access →" button | Navigate to Access Control after upload | "Configure access" implies technical setup; user intent is "share this document" | **Share Document →** or **Manage Sharing →** |

---

## Recommended Standard Vocabulary

| Concept | Standard Term | Notes |
|---------|--------------|-------|
| Home screen / document library | **Documents** | Replaces "Upload" as screen name |
| One-time upload action | **Upload** | Stays on the button, not the screen |
| Document reading screen | **Reader** | Avoid reusing "Viewer" for screen name |
| People who view shared docs | **Viewers** | Keeps the role name |
| Share link creation form (tab) | **Create Link** | Replaces "Policy" tab |
| Share link list (tab) | **Links** | Replaces "Share Link" tab |
| Per-document view history (tab) | **View History** | Replaces "Access Log" tab |
| Screen containing policy+links+history+feedback | **Share & Manage** | Replaces "Access Control" |
| Instant link creation (button) | **Quick Share** | Both button and modal use this |
| Admin system event log | **Activity Log** | Replaces "Audit Log" |
| Polled event feed screen | **Activity** | Replaces "Notifications" |
| Webhook trigger types | **Triggers** | Replaces "Events" in webhooks context |
| After-upload navigation | **Share Document →** | Replaces "Configure Access →" |

---

## Terms That Are Already Correct

These terms require no change:

- **Analytics** — clear, specific, consistent
- **Storage** — clear, matches the data
- **Billing** — clear, standard
- **Group** — consistent across Upload / Analytics / Storage
- **Organization** (UI) / **org** (code) — consistent
- **Link** — clear, not conflated with hyperlinks
- **Feedback** — correct label, wrong location
- **Annotations** — correct label, wrong location
- **Webhooks** — developer-standard term, correct audience
- **API Keys** — developer-standard term, correct audience
- **Watermark** — clear, consistent

---

*Generated: Sprint 4.8B Phase 2 — no implementation performed.*
