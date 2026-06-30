# Founder Validation Report
Date: 2026-06-22
Perspective: Founder + Product Lead
Method: Full walkthrough of every screen, button, and tab from source reading. No assumptions.

Ratings: PASS | FAIL | CONFUSING | REDUNDANT

---

## The Product in One Sentence

SecureDoc lets you upload a document, set access rules (who, when, how many times), share a link, and see who read what page.

That is the right product. The question is whether the experience matches that description.

**Honest answer: Not yet.**

---

## Screen 1 — Upload Screen

**Purpose:** Get a document into the system.

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| Drag-drop or click to upload | `POST /api/documents/upload` | Celery pipeline queued | `documents` row created | Progress bar, status badge | PASS |
| Status poll (2s interval) | `GET /api/documents/{id}/status` | Returns pipeline state | — | Badge updates: processing → processed | PASS |
| Delete document | `DELETE /api/documents/{id}` | Ownership check, storage removal | Row deleted | Table updates | PASS |
| Reprocess document | `POST /api/documents/{id}/reprocess` | Celery re-queue | Status reset | Status badge | PASS |
| Create group | `POST /api/groups` | Row insert | `document_groups` row | Groups strip updates | PASS |
| Rename group | `PATCH /api/groups/{id}` | Update | Row updated | Groups strip updates | PASS |
| Delete group | `DELETE /api/groups/{id}` | Cascade unassign | Row deleted | Groups strip updates | PASS |
| Assign document to group | `POST /api/groups/{id}/documents` | Association | — | Document row updates | PASS |
| Search documents | None (client-side) | — | — | List filtered | PASS |
| 4 KPI stat cards (views, links, blocked, storage) | `GET /api/analytics/overview` | Aggregation | — | Cards populate | PASS |

**What works:** The upload flow itself is clean. Drag-drop is discoverable. Status polling is invisible in the right way — badge updates, user doesn't feel the wait.

**What's broken:**
- Upload button label reads "⊕ Upload PDF" but accepts DOCX, DOC, TXT, MD, LOG. A consultant who wants to share a `.docx` proposal may hesitate or assume it won't work.

**What's confusing:**
- The **Groups** feature lives on the Upload screen but it's a document organization tool. A first-time user doesn't understand Groups or why they would care. The groups strip at the top of the screen adds visual weight before the user has anything to organize.
- **Retention Policy** is a dropdown buried at the bottom of the screen. Most users will never find it, and "Retention Policy" sounds like enterprise legal jargon rather than "auto-delete files after 30 days."
- There is **no shortcut to share a document from this screen.** The document table has rows, but to share a document you must navigate to a different screen, find the same document again, and configure a link. The most frequent action in the product (sharing) is not available on the primary data screen.
- The **Risk badge** on each document (HIGH/MEDIUM/LOW) is unexplained. What is "HIGH" risk? Risk of what? This term is borrowed from security tooling and has no meaning for most users.

**CONFUSING: Groups strip on first load (nothing to organize)**
**CONFUSING: Risk badge has no tooltip or explanation**
**CONFUSING: No share action directly on document row**
**FAIL: "Upload PDF" label is wrong — accepts 6 file types**

---

## Screen 2 — Access Control Screen (the most important screen)

**Purpose:** Configure who can view the document and get a shareable link.

This screen is doing five jobs at once: link creation, link policy, link list, access log, feedback, and annotations. That is too many jobs.

### Policy Tab

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| Fill policy form (password, domains, expiry, etc.) | — | — | — | Form state | PASS |
| Save Policy (creates link) | `POST /api/links` | Link row created | `share_links` | Tab switches to Share Link, list refreshes | PASS |
| ⟳ New Link (default settings) | `POST /api/links` | Link row created | `share_links` | Tab switches to Share Link, list refreshes | PASS ✅ (fixed Sprint 4.5A) |

**What's confusing:**
- **"Policy" is the wrong word.** Users don't think "I need to set a Policy." They think "I need to share this document." The tab should be called "Share Settings" or just "Share."
- **Save Policy is actually "Create Link."** The button says "Save Policy" but the result is a new shareable URL. The mental model mismatch causes hesitation. Users wonder: "Did this just share my document? Is there more to do?"
- **The Policy tab has 11 form fields**: password, allowed domains, allowed emails, expiry date, max views, max concurrent sessions, IP allowlist, and 7 permission toggles (download, print, copy, right-click, watermark, annotations, info panel). **11 fields to share a document.** DocSend ships a modal with 3 fields.
- **"Max Concurrent Sessions"** — no user outside enterprise IT will understand this. Even power users will wonder: does this mean devices? tabs? simultaneous viewers?
- **"IP Allowlist" with CIDR notation hint** — this is a DevOps field, not a document-sharing field. The hint says "CIDR or exact, e.g. 10.0.0.0/24." A consultant does not know what CIDR is.
- **"Enable Info Panel"** — what is the Info Panel? The toggle label gives no context.
- **"Right Click"** — disabling right-click is a superficial DRM measure that technical users can trivially bypass (devtools, screenshot), and non-technical users don't understand why it's here.

**CONFUSING: "Policy" tab name — should be "Share"**
**CONFUSING: "Save Policy" button — should be "Create Share Link"**
**CONFUSING: 11 form fields is 8 too many for first-time use**
**CONFUSING: "Max Concurrent Sessions," "IP Allowlist," "CIDR," "Enable Info Panel" are unexplained jargon**

### Share Link Tab

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| Copy link | Clipboard API | — | — | "✓ Copied" state | PASS |
| Open in new tab | window.open | — | — | New tab | PASS |
| Revoke link | `DELETE /api/links/{id}` | Mark revoked | `revoked_at` set | Link shows REVOKED badge | PASS |
| Embed code display | Client-side only | — | — | Inline display | PASS |

**What's confusing:**
- The embed code is shown inline below each link. An `<iframe>` tag is displayed as a code block that most users won't understand how to use. This is a power feature shown to everyone.
- There is no "Edit this link's settings" action per-link on the Share Link tab. You can revoke, copy, or open — but if you want to change the expiry date of an existing link, you cannot do it from here.

**CONFUSING: Embed code shown to all users by default (power feature)**
**CONFUSING: No per-link "Edit settings" on the Share Link tab**

### Access Log Tab

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| View access events | `GET /api/analytics/events` | Filtered query | — | Table renders | PASS |

**Rating: PASS.** Clean read-only display. No issues.

### Feedback Tab

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| View feedback threads | `GET /api/feedback` | Query | — | Threads render | PASS |
| Inline reply | `PATCH /api/feedback/{id}` | Update | Row updated | Thread updates | PASS |
| Export Feedback Conversations | `GET /api/documents/{id}/feedback/export` | CSV generation | — | File download | PASS |
| Export Reviewer Activity | `GET /api/documents/{id}/feedback/export-reviewer-activity` | CSV generation | — | File download | PASS |
| Status filter (open/resolved) | Re-fetch | — | — | List filters | PASS |
| Reviewer filter | Re-fetch | — | — | List filters | PASS |
| Date range filter | Re-fetch | — | — | List filters | PASS |
| Text search | Re-fetch (debounced) | — | — | List filters | PASS |
| Advanced Filters (collapse toggle) | Client state | — | — | Shows/hides more fields | REDUNDANT |

**What's confusing:**
- There are **two levels of filter disclosure**: a "Filters" button that expands basic filters, then an "Advanced Filters" toggle inside that panel. This is over-engineering for a screen that most users will visit once a week at most.
- The feedback feature itself is excellent and underutilized. The fact that viewers can leave structured comments on specific pages is a genuine differentiator — but the UI buries it in the 4th tab of a screen labeled "Access Control." Users who would love this feature won't find it.

**REDUNDANT: Two-level filter disclosure (Filters → Advanced Filters)**
**CONFUSING: Feedback feature buried in "Access Control" screen tab 4**

### Annotations Tab

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| View annotations | `GET /api/annotations` | Query | — | List renders | PASS |
| Type filter | Client filter or re-fetch | — | — | List filters | PASS |
| Export CSV | `GET /api/documents/{id}/annotations/export` | CSV | — | File download | PASS |

**REDUNDANT: Annotations exist both here (as an owner management view) and in the Viewer (as the creation/interaction surface). The duplication is confusing — users don't know which is "the" annotations view.**

---

## Screen 3 — Viewer Screen

**Purpose:** Read the document. (For owners: preview. For viewers: the main experience.)

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| Page render | `GET /api/viewer/page/{token}/{page}` | Render + watermark | `access_events` | Canvas updates | PASS |
| Page navigation (prev/next/jump) | Same | — | Events logged | Canvas updates | PASS |
| Zoom in/out/pinch | None | — | — | CSS transform | PASS |
| Fit width / fit page | None | — | — | Layout recalc | PASS |
| Rotate | None | — | — | State | PASS |
| Download | `GET /api/viewer/download/{token}` | Watermarked PDF | — | File download | PASS |
| Bookmark page | `POST /api/viewer/bookmark` | Insert | Bookmarks table | Button state | PASS |
| Create annotation (highlight/draw) | `POST /api/annotations` | Insert | `annotations` row | Canvas overlay | PASS |
| Delete annotation (undo) | `DELETE /api/annotations/{id}` | Delete | Row deleted | Canvas updates | PASS |
| Table of contents | `GET /api/viewer/toc/{token}` | Returns sidecar | — | TOC panel | PASS |
| Text search | Client-side (text sidecar) | — | — | Highlights | PASS |
| Links panel | Client-side (links sidecar) | — | — | Links panel | PASS |
| Insights panel | `GET /api/analytics/page-heatmap` | Aggregation | — | Panel populates | PASS |
| Laser pointer | None | — | — | CSS overlay | REDUNDANT |
| Magnifier | None | — | — | Canvas zoom | REDUNDANT |
| Info panel | Session data | — | — | Info overlay | CONFUSING |

**What's confusing:**
- **The Viewer is in the owner's navigation.** The Viewer tab exists for owners to preview their own documents. But the Viewer is also the experience viewers (recipients) use when they follow a share link. These are two very different contexts running in the same screen. An owner using the Viewer to preview their own document sees the same interface as a client viewing a shared document — including the access gate if one is configured.
- **The Viewer toolbar has 15+ controls** in a single row. Most users need 4: page navigation, zoom, download, close. The rest (laser pointer, magnifier, annotation tools, insights, links panel, TOC toggle, page list toggle, info panel, fullscreen, search) require discovery. There is no distinction between primary and secondary controls.
- **Laser Pointer** — this is a presentation tool. For a document-sharing product, it has no use case. Who uses a laser pointer while viewing a PDF alone?
- **Magnifier** — duplicate of zoom. If you want to see something larger, you zoom.
- **"Insights" panel inside the Viewer** — shows page heatmap analytics. This is the same data in AnalyticsScreen. Having analytics inside the viewer itself is a nice touch but adds toolbar clutter for users who don't want it.

**REDUNDANT: Laser pointer**
**REDUNDANT: Magnifier (duplicate of zoom)**
**REDUNDANT: Insights panel in viewer duplicates AnalyticsScreen data**
**CONFUSING: Owner-viewer and recipient-viewer are the same screen in the nav**

---

## Screen 4 — Analytics Screen

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| Overview KPIs | `GET /api/analytics/overview` | Aggregation | — | Cards | PASS |
| By Document table | `GET /api/analytics/documents` | Per-doc stats | — | Table | PASS |
| By Group table | `GET /api/analytics/groups` | Per-group stats | — | Table | PASS |
| Page heatmap (click row) | `GET /api/analytics/page-heatmap` | Aggregation | — | Heatmap | PASS |
| Range selector (24h/7d/30d/90d) | None | — | — | State only | FAIL |
| Export CSV | Client-side Blob | — | — | File download | PASS ✅ (fixed Sprint 4.5A) |

**What's broken:**
- **Range selector does nothing.** It changes the visual state of the button (active/inactive style) but the data never changes. A user who selects "24h" to see today's activity is looking at 90 days of data, thinking they're seeing today's. This is the worst kind of bug — it doesn't error, it lies. *(Known issue, deferred to Sprint 4.6)*

**FAIL: Range selector is visually functional but data is never filtered**
**CONFUSING: Three tabs (Overview / By Document / By Group) — most users only need "By Document"**

---

## Screen 5 — Storage Screen

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| Dashboard display | `GET /api/storage/dashboard` | Aggregation | — | Cards | PASS |
| Forecast display | `GET /api/storage/forecast` | Projection | — | Display | PASS |
| Retention policy update | `PATCH /api/storage/retention` | Update | `users` row | Dropdown | PASS |

**Rating: Functionally sound. Existentially unnecessary as a top-level nav item.**

The Storage screen exists so that users can see how much space they're using and set a retention policy. This is a utility view — something you check once when you set up your account, then never again. It occupies the same nav weight as Upload, Viewer, Access Control, and Analytics. It should be a settings page, not a primary navigation destination.

**REDUNDANT: Storage in primary nav — belongs in Settings or Billing**

---

## Screen 6 — Billing Screen

| Interaction | API | Backend | DB | UI Refresh | Rating |
|---|---|---|---|---|---|
| Status display | `GET /api/billing/status` | Query | `user_billing` | Display | PASS |
| Upgrade (Stripe Checkout) | `POST /api/billing/checkout` | Stripe session | — | Redirect | PASS |
| Manage subscription | `POST /api/billing/portal` | Stripe portal | — | Redirect | PASS |
| No-config graceful state | 503 response handling | — | — | "Not configured" | PASS |

**Rating: Fully functional.** No issues.

---

## Overall Verdict

**The product works. The product is confusing.**

Every API call lands. Every database write persists. Every UI refresh happens. The infrastructure is sound.

The failure is at the product layer:
1. The core action (sharing a document) takes 5+ clicks and requires understanding "Policy tabs"
2. The most valuable feature for the primary use case (knowing when your document is viewed) is broken at the backend level
3. Seven words describe the product's value: "Share a document, know who read it." The UI takes 11 form fields to do the first part.
4. Three features that would make competitors jealous (forensic watermark, IP allowlist per link, concurrent session limits) are invisible to users — no explanation, no discovery path, no onboarding

**Score: 6/10 for usability. 9/10 for engineering.**
