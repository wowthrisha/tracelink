# Feature Simplification Plan
Date: 2026-06-22
Perspective: Founder + Product Lead
Method: Evaluate every feature against: Would a real user find this? Would they use it weekly?

Verdicts: KEEP | SIMPLIFY | REMOVE | MERGE

Rule: Do not remove anything that a paid user would complain about losing.
Rule: Simplify means: hide behind "Advanced" or rename to plain language. No code deletion.

---

## Navigation

| Item | Current Label | Verdict | Rationale |
|---|---|---|---|
| Upload | "Upload" | KEEP | Core action, correct label |
| Viewer | "Viewer" | SIMPLIFY | Rename to "Preview" — "Viewer" sounds like it's for recipients |
| Access Control | "Access Control" | SIMPLIFY | Rename to "Share" — that is the action the user wants |
| Analytics | "Analytics" | KEEP | Correct. Users understand analytics. |
| Storage | "Storage" | MERGE | Move to Settings or Billing sidebar. Not a primary screen. |
| Billing | "Billing" | KEEP | Necessary. |

**Net effect: 6 nav items → 5 nav items (Storage removed from primary nav)**

---

## Upload Screen

| Feature | Verdict | Rationale |
|---|---|---|
| Upload button label "⊕ Upload PDF" | SIMPLIFY | Rename to "⊕ Upload Document" — accepts 6 types |
| Drag-drop zone | KEEP | Discoverable, essential |
| Document table with status badges | KEEP | Essential |
| Search bar | KEEP | Essential at scale |
| "Share" action on document row | KEEP (ADD) | The most frequent action is missing. Add a "↗ Share" button per row that jumps to the Share screen with that doc pre-selected. |
| 4 KPI stat cards | KEEP | Gives instant context |
| Groups strip | SIMPLIFY | Move to a collapsible panel or secondary nav. Don't show until user has 3+ documents. Groups add cognitive load before there's a reason for them. |
| Retention Policy dropdown | MERGE | Move to Storage settings (or just show in the Storage screen). Not an upload-time decision. |
| Risk badge on documents | SIMPLIFY | Rename to "Exposure" and add a tooltip: "Documents with active share links and many viewers have higher exposure." Or remove — nobody understands "risk" in this context. |

---

## Share Screen (renamed from Access Control)

The Access Control screen has 5 tabs. The mental model of a user coming here is: "I want to share this document." Not "I want to control access, manage feedback, review annotations, and audit logs."

### Tab Structure — Current vs Proposed

| Current Tab | Verdict | Proposed |
|---|---|---|
| Policy | SIMPLIFY | Rename to "Share Settings" — split into Basic and Advanced |
| Share Link | KEEP | Rename to "Active Links" — clearer |
| Access Log | KEEP | Rename to "Who Viewed" — much clearer |
| Feedback | KEEP | Move to first-class feature, possibly its own nav item |
| Annotations | MERGE | Merge with Feedback tab — both are "things viewers left behind" |

### Policy / Share Settings Tab — Form Fields

| Field | Verdict | Rationale |
|---|---|---|
| Password | KEEP — in Basic | Most common security need. Simple label: "Require password" |
| Allowed Domains | KEEP — in Basic | Rename to "Restrict to email domain(s)" — "allowed domains" sounds like IT |
| Expiry Date | KEEP — in Basic | Simple and useful. Rename to "Expire link after" |
| Max View Count | SIMPLIFY — in Basic | Rename to "Max opens" or keep "Max views." Simple. |
| Allowed Emails | KEEP — in Advanced | Power feature for invited-only sharing. "Allow only these emails" |
| Max Concurrent Sessions | SIMPLIFY — in Advanced | Rename to "Prevent link sharing (max simultaneous viewers)" — then the value is obvious |
| IP Allowlist | SIMPLIFY — in Advanced | Rename to "Restrict by IP address" and hide CIDR hint behind a tooltip. Most users paste an IP, not CIDR. |
| can_download | KEEP — in Basic | "Allow download" |
| can_print | KEEP — in Basic | "Allow printing" |
| can_copy | KEEP — in Basic | "Allow copying text" |
| watermark_enabled | KEEP — in Basic | "Show watermark" |
| can_annotate | KEEP — in Basic | "Allow annotations" |
| can_right_click | REMOVE from default UI | Right-click disable is security theater. Trivially bypassed. Move to an "Extra restrictions" drawer if at all. |
| enable_info | SIMPLIFY | Rename to "Show document info panel" — or remove entirely; the info panel should always be visible |

**Net effect on Policy form: 11 visible fields → 6 Basic + 4 Advanced (collapsed by default)**

### Save Policy button

| Button | Verdict | Rationale |
|---|---|---|
| "Save Policy" | SIMPLIFY | Rename to "Create Share Link" — that is what it does |
| "⟳ New Link" | KEEP | Useful for creating a second link with different settings. Rename to "Quick Share Link" for clarity. |

---

## Viewer Screen

| Feature | Verdict | Rationale |
|---|---|---|
| Page navigation | KEEP | Essential |
| Zoom in/out/pinch | KEEP | Essential |
| Fit width / fit page | KEEP | Essential |
| Rotation | KEEP | Useful |
| Download | KEEP | Essential (when permitted) |
| Bookmark | KEEP | Useful |
| Annotations (highlight/draw) | KEEP | Differentiator |
| Table of contents | KEEP | Useful for long docs |
| Text search | KEEP | Essential |
| Links panel | KEEP | Unique to SecureDoc — but needs discovery |
| Insights panel | SIMPLIFY | Move to a secondary toolbar group or collapse by default. Valuable but competes for toolbar space. |
| Info panel | SIMPLIFY | Make it a small "ℹ" button that shows document metadata. Currently unclear what "Info Panel" means. |
| **Laser pointer** | **REMOVE** | Zero use case for a document-sharing product. Presentation tool. |
| **Magnifier** | **REMOVE** | Duplicate of zoom. Use zoom instead. |
| Fullscreen | KEEP | Useful |
| Page list (thumbnails) | KEEP | Useful for navigation |

**Net effect: 2 tools removed from toolbar, making primary controls more discoverable**

---

## Analytics Screen

| Feature | Verdict | Rationale |
|---|---|---|
| Overview tab | SIMPLIFY | Merge with By Document. The overview KPIs can live above the document table. Having a separate "Overview" tab with 6 KPI cards adds a tab for data that should lead to document-level drill-down. |
| By Document tab | KEEP as primary | This is the most useful view. Should be the default. |
| By Group tab | KEEP — secondary | Useful once a user has groups. |
| Range selector | KEEP (fix) | Has to actually filter the data. |
| Page heatmap | KEEP | Differentiator — nobody else shows page-level attention data. |
| Export CSV | KEEP | Just fixed. Works now. |

**Proposed: Default tab is "By Document." Overview KPIs shown as a collapsible banner at the top of that tab.**

---

## Storage Screen

| Feature | Verdict | Rationale |
|---|---|---|
| Storage dashboard (total/used) | MERGE | Move to Billing screen sidebar — "X GB used of Y GB" is billing-adjacent |
| Storage forecast | SIMPLIFY | Only relevant when approaching limits. Show as a warning banner when >80% used, not a permanent screen. |
| Retention policy | MERGE | Move to a "Settings" screen (which doesn't exist yet) or to Billing. |

**Net effect: Storage screen removed from primary nav. Data surfaces contextually.**

---

## Features Nobody Would Discover (with current UI)

These features exist, work, and are differentiators — but users have no way to learn they exist:

| Feature | Where it hides | Discovery action needed |
|---|---|---|
| Forensic steganographic watermark | Backend — invisible | Add a "Forensic watermark active" badge in the Viewer. Add tooltip: "Every viewer's copy is uniquely marked — even screenshots can be traced to a specific session." |
| IP Allowlist | Policy tab, Advanced (buried) | Surface as a feature highlight on first use. "Enterprise-grade: restrict by IP address." |
| Max Concurrent Sessions | Policy tab, Advanced (buried) | Surface as: "Prevent link sharing — limit how many people can view at once." |
| Links panel in Viewer | Toolbar icon | Add a tooltip on hover: "All hyperlinks extracted from this document, by page." |
| Insights panel in Viewer | Toolbar icon | Add label or tooltip: "See which pages got the most attention." |
| Feedback from viewers | Access Control tab 4 | Should be promoted to its own nav item or always-visible badge. |

---

## Summary Table

| Action | Item | Impact |
|---|---|---|
| RENAME | "Access Control" → "Share" | High — reduces navigation friction |
| RENAME | "Policy" tab → "Share Settings" | High — users understand what they're doing |
| RENAME | "Save Policy" → "Create Share Link" | High — eliminates confusion |
| RENAME | "Viewer" → "Preview" | Low — clarity for owners |
| RENAME | "Who Viewed" for Access Log tab | Medium — immediately clear |
| REMOVE | Laser pointer from Viewer toolbar | Medium — reduces clutter |
| REMOVE | Magnifier from Viewer toolbar | Low — duplicate of zoom |
| REMOVE | can_right_click from default form | Medium — declutters, removes security theater |
| MOVE | Storage screen → contextual/Billing | Medium — removes nav clutter |
| MOVE | Groups strip → collapsible panel | Medium — reduces first-use cognitive load |
| MOVE | Retention Policy → Storage/Settings | Low — belongs with storage management |
| HIDE | Advanced form fields behind collapse | High — main form goes from 11 fields to 6 |
| ADD | "↗ Share" button on Upload document rows | High — the most-needed missing affordance |
| MERGE | Annotations tab into Feedback tab | Low — two views of viewer-left content |
