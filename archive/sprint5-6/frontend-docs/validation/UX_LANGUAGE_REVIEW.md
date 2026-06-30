# UX Language Review
Sprint: 4.6 — Workstream 3
Date: 2026-06-22
Status: DESIGN ONLY — Do not implement without sprint approval

Method: Evaluate every visible label, button, tab, and field name against one test:
"Would a non-technical professional understand what this does on first read?"

Verdicts: KEEP | RENAME | REMOVE | MOVE

Rule: RENAME means a text change only — zero behavior change.
Rule: REMOVE means remove from the default visible UI — the underlying feature may remain behind an Advanced toggle.
Rule: MOVE means relocate to a less prominent position — not deletion.

---

## Navigation Labels

| Screen | Current Label | Verdict | Proposed Label | Rationale |
|---|---|---|---|---|
| Upload screen | **Upload** | KEEP | Upload | Correct. Clear action. |
| Viewer screen | **Viewer** | RENAME | Preview | "Viewer" implies recipients use it. Owners use this tab to preview. "Preview" is what owners think they're doing. |
| Access Control screen | **Access Control** | RENAME | Share | The action is sharing. "Access Control" is enterprise IT jargon — it tells users nothing about what the screen does. |
| Analytics screen | **Analytics** | KEEP | Analytics | Professionals understand this word. |
| Storage screen | **Storage** | MOVE | (remove from primary nav) | Storage is a utility screen visited once at setup. It has the same nav weight as Upload and Share. Move data to Billing. |
| Billing screen | **Billing** | KEEP | Billing | Necessary, correct. |

**Net change: 6 nav items → 5 nav items. Two renames. One removal from primary nav.**

---

## Upload Screen

### Buttons and Labels

| Element | Current | Verdict | Proposed | Rationale |
|---|---|---|---|---|
| Upload button | **⊕ Upload PDF** | RENAME | ⊕ Upload Document | The button accepts PDF, DOCX, DOC, TXT, MD, LOG — not just PDF. The label creates doubt for users with non-PDF files. |
| Document row status | **processing / ready / error** | KEEP | processing / ready / error | Status labels are clear. |
| Risk badge | **HIGH / MEDIUM / LOW** | RENAME | Exposure: High / Medium / Low | "Risk" has no meaning without context. "Exposure" paired with a tooltip ("This document has X active links and Y views") is self-explanatory. |
| Groups strip label | **Groups** | KEEP | Groups | Acceptable label. The groups strip itself (visibility on first load) is a layout decision, not a label problem. |
| Retention Policy dropdown | **Retention Policy** | RENAME | Auto-delete after | "Retention Policy" is legal jargon. "Auto-delete after: 30 days / 90 days / Never" is immediately understood by anyone. |
| (proposed) Share button on row | (new) | — | ↗ Share | See QUICK_SHARE_DESIGN.md |

---

## Share Screen (renamed from Access Control)

### Tab Labels

| Current Tab | Verdict | Proposed | Rationale |
|---|---|---|---|
| **Policy** | RENAME | Share Settings | "Policy" reads as an IT compliance word. "Share Settings" tells the user exactly what they're configuring. |
| **Share Link** | RENAME | Active Links | The tab contains a list of all created links — active, revoked, expired. "Share Link" sounds like the tab that generates a link (which is actually the Policy/Share Settings tab). "Active Links" describes the content correctly. |
| **Access Log** | RENAME | Who Viewed | "Access Log" is a developer/security term. "Who Viewed" is immediately understood by any professional. |
| **Feedback** | RENAME | Reviews | "Feedback" is generic. In document-sharing context, "Reviews" implies structured per-document commentary, which is what this tab contains. It's also the word professionals use ("send it for review"). |
| **Annotations** | MOVE | (merge into Reviews tab) | Annotations and Feedback are both "things viewers left on the document." Showing them in two separate tabs suggests they are different categories of equal importance. They are not — feedback threads are the primary content; annotations are supplementary marks. Merge into Reviews with a filter toggle. |

**Net change on Share screen: 4 renames, 1 tab merge (5 tabs → 4 tabs).**

### Share Settings Form (formerly Policy tab)

#### Basic fields (visible by default)

| Current Label | Verdict | Proposed Label | Rationale |
|---|---|---|---|
| **Password** | KEEP | Require password | Minimal change. Adding "Require" clarifies it's opt-in. |
| **Allowed Domains** | RENAME | Restrict to email domain(s) | "Allowed Domains" sounds like website whitelisting. "Restrict to email domain(s)" describes the actual behavior: "only people with @company.com email can open this." |
| **Expiry Date** | RENAME | Link expires on | More natural language. "Expiry Date" is form-field shorthand. |
| **Max View Count** | RENAME | Max opens | Shorter and plain. "Max views" is also acceptable. Avoid "count" — it sounds like a metric, not a limit. |
| **can_download** toggle | RENAME | Allow download | The current label starts with a technical permission key name. "Allow download" is the plain English version. |
| **can_print** toggle | RENAME | Allow printing | Same pattern. |
| **can_copy** toggle | RENAME | Allow copying text | "Can copy" is vague — copying what? "Allow copying text" is specific. |
| **watermark_enabled** toggle | RENAME | Show watermark | Plain. The tooltip should add: "Each viewer's copy includes a unique mark — even screenshots can be traced to their session." |
| **can_annotate** toggle | RENAME | Allow annotations | Same pattern. |

#### Advanced fields (hidden behind collapse by default)

| Current Label | Verdict | Proposed Label | Rationale |
|---|---|---|---|
| **Allowed Emails** | RENAME (to Advanced) | Allow only these emails | Move to Advanced. Power feature for invited-only links. Plain label. |
| **Max Concurrent Sessions** | RENAME (to Advanced) | Max simultaneous viewers | "Concurrent sessions" is a DevOps term. "Max simultaneous viewers" describes what it means to a document owner. Tooltip: "If 3 people try to open this link at the same time and you set max to 2, the third viewer is blocked until one closes the document." |
| **IP Allowlist** | RENAME (to Advanced) | Restrict by IP address | "Allowlist" is a technical term. "Restrict by IP address" says what it does. CIDR notation hint should be moved to a tooltip — don't show "10.0.0.0/24" in the input hint; most users paste a plain IP address. |
| **can_right_click** toggle | REMOVE | (remove from default form) | Right-click blocking is security theater. It is trivially bypassed by any user who opens browser developer tools or takes a screenshot. Showing it in the share form implies it is meaningful protection — it is not. If retained at all, move to an "Extra restrictions" section with a clear caveat: "This discourages casual copying but does not prevent determined users." |
| **enable_info** toggle | RENAME (to Advanced) | Show document info panel | "Enable Info" is opaque — info about what? Rename and move to Advanced. Most users should leave this on. |

**Net change on form: 11 visible fields → 6 visible fields (Basic) + 4 fields in Advanced collapse + 1 field removed or demoted.**

### Buttons

| Current Button | Verdict | Proposed | Rationale |
|---|---|---|---|
| **Save Policy** | RENAME | Create Share Link | This is the action that creates and returns a share URL. "Save Policy" implies saving a configuration that may or may not have done anything. "Create Share Link" is the actual outcome. |
| **⟳ New Link** | RENAME | + New Link | The ⟳ icon implies refresh or retry. "+" is the conventional "create new" affordance. Label can stay "New Link" — it's clear enough. |

---

## Viewer Screen (toolbar and panels)

### Toolbar Controls

| Current Label/Icon | Verdict | Proposed | Rationale |
|---|---|---|---|
| Page navigation (◄ ► / page input) | KEEP | — | Standard navigation. No label needed. |
| Zoom in / Zoom out | KEEP | — | Universal. |
| Fit Width | KEEP | — | Common viewer term. |
| Fit Page | KEEP | — | Common viewer term. |
| Rotate | KEEP | — | Clear. |
| Download | KEEP | — | Clear. |
| Bookmark | KEEP | — | Clear. |
| Fullscreen | KEEP | — | Clear. |
| Annotation tools (highlight, draw) | KEEP | — | These are discoverable via tooltip. |
| Table of Contents | KEEP | TOC | Abbreviation is acceptable in a toolbar context. |
| Search | KEEP | — | Universal. |
| Links panel | KEEP | Links | Tooltip: "All hyperlinks extracted from this document, organized by page." Improves discoverability. |
| Insights panel | KEEP | Insights | Tooltip: "See which pages received the most attention from viewers." Improves discoverability. |
| Info panel | RENAME | ℹ Info | Replace text label with a standard "ℹ" button. Tooltip: "Document metadata and session info." |
| **Laser Pointer** | **REMOVE** | — | No use case in a document-sharing product. Presentation tool. Increases toolbar cognitive load for zero user benefit. |
| **Magnifier** | **REMOVE** | — | Duplicate of zoom. Zoom in/out achieves the same result with no additional controls. |
| Page list (thumbnails) | KEEP | Pages | Tooltip: "Show page thumbnails for navigation." |

**Net change on toolbar: 2 tools removed, 3 tooltips added for discoverability.**

---

## Analytics Screen

| Element | Current | Verdict | Proposed | Rationale |
|---|---|---|---|---|
| Tab: Overview | **Overview** | KEEP | Overview | Acceptable. |
| Tab: By Document | **By Document** | RENAME | Documents | Shorter. The "By" is implied by being in a tabbed analytics view. |
| Tab: By Group | **By Group** | RENAME | Groups | Same pattern. |
| Range selector | **24h / 7d / 30d / 90d** | KEEP labels, FIX behavior | 24h / 7d / 30d / 90d | Labels are fine — the bug is that they don't filter data, not that the labels are wrong. See Rank 4 improvement. |
| Export CSV button | **Export CSV** | KEEP | Export CSV | Clear. |
| Page heatmap section | **Page Heatmap** | RENAME | Page Attention | "Heatmap" is a visualization term. "Page Attention" explains what it represents: where viewers spent the most time. |

---

## Storage Screen (proposed: merged into Billing)

If the Storage screen is removed from primary nav (as recommended), the following data points should surface in the Billing screen:

| Storage element | Proposed destination | Proposed label |
|---|---|---|
| Total storage used | Billing screen — Usage section | Storage used: X GB of Y GB |
| Storage forecast | Billing screen — Usage section | At current rate, you'll reach your limit in ~N months |
| Retention policy | Settings or Billing — Usage section | Auto-delete documents after: [dropdown] |
| Near-limit warning | Upload screen — banner | You've used 85% of your storage. Manage in Billing → |

---

## Summary: All Renames

| Location | Current | Proposed |
|---|---|---|
| Sidebar nav | Access Control | Share |
| Sidebar nav | Viewer | Preview |
| Upload screen | ⊕ Upload PDF | ⊕ Upload Document |
| Upload screen | Risk badge | Exposure badge |
| Upload screen | Retention Policy dropdown | Auto-delete after |
| Share screen — tab | Policy | Share Settings |
| Share screen — tab | Share Link | Active Links |
| Share screen — tab | Access Log | Who Viewed |
| Share screen — tab | Feedback | Reviews |
| Share screen — button | Save Policy | Create Share Link |
| Share screen — button | ⟳ New Link | + New Link |
| Share form | Password | Require password |
| Share form | Allowed Domains | Restrict to email domain(s) |
| Share form | Expiry Date | Link expires on |
| Share form | Max View Count | Max opens |
| Share form | can_download | Allow download |
| Share form | can_print | Allow printing |
| Share form | can_copy | Allow copying text |
| Share form | watermark_enabled | Show watermark |
| Share form | can_annotate | Allow annotations |
| Share form | Allowed Emails | Allow only these emails |
| Share form | Max Concurrent Sessions | Max simultaneous viewers |
| Share form | IP Allowlist | Restrict by IP address |
| Share form | enable_info | Show document info panel |
| Analytics screen — tab | By Document | Documents |
| Analytics screen — tab | By Group | Groups |
| Analytics screen | Page Heatmap | Page Attention |

## Summary: Removes (from default visible UI)

| Item | Location | Disposition |
|---|---|---|
| Laser Pointer | Viewer toolbar | Remove entirely |
| Magnifier | Viewer toolbar | Remove entirely |
| can_right_click toggle | Share Settings form | Remove from form or move to Advanced with caveat |
| Annotations tab | Share screen | Merge into Reviews tab |
| Storage screen | Primary nav | Move to Billing screen |

---

## Implementation Estimate

All changes are text and layout. No API changes. No database changes. No backend changes.

- Navigation label changes (atoms.jsx NAV_SECTIONS): 15 minutes
- Share screen tab renames + form field relabeling (AccessScreen.jsx): 1.5 hours
- Viewer toolbar removes + tooltip additions (ViewerScreen.jsx / ViewerToolbar): 1 hour
- Analytics tab renames (AnalyticsScreen.jsx): 30 minutes
- Upload screen label changes (UploadScreen.jsx): 30 minutes

**Total: ~3.5 hours. Zero backend work. Zero database changes. Zero API contract changes.**
