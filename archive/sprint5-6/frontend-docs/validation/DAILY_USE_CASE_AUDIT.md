# Daily Use Case Audit
Date: 2026-06-22
Perspective: Founder + Product Lead
Question: Can a real user complete their most common weekly task in under 30 seconds?

30-second target: the time it takes to pour a glass of water. If your product takes longer for the most common action, users will find a workaround.

Personas:
- Architect — shares design documents with clients and contractors
- Consultant — shares proposals, reports, invoices with prospects and clients
- Builder — shares technical specifications with subcontractors and suppliers
- Client — receives documents, reviews them, leaves feedback

---

## Persona 1 — The Architect

**Who they are:** A solo architect or small firm. Shares 5-10 PDFs per week. Needs to know if a client reviewed the drawings before a meeting. Doesn't want construction docs downloaded to the client's laptop.

**Most common task:** Share a new drawing PDF with a specific client and prevent them from downloading it.

### Task walkthrough (current product):

| Step | Action | Screen | Time |
|---|---|---|---|
| 1 | Navigate to Upload screen | (from wherever) | ~2s |
| 2 | Drag PDF onto drop zone | Upload | ~5s |
| 3 | Wait for "processed" status | Upload | ~10-30s (depends on file) |
| 4 | Navigate to Access Control screen | Sidebar | ~2s |
| 5 | See DocumentPicker — must select the document | Access Control | ~5s |
| 6 | Land on Policy tab — 11 form fields | Access Control | (reading/configuring) |
| 7 | Find "Download" toggle in the 7-toggle grid (3rd row, position varies) | Access Control | ~10s |
| 8 | Toggle Download off | Access Control | ~2s |
| 9 | Click "Save Policy" (or "Create Share Link") | Access Control | ~2s |
| 10 | Tab switches to Share Link | Access Control | ~1s |
| 11 | Click "⧉ Copy" | Access Control | ~2s |
| **Total** | | | **~45-65s** (excluding upload processing) |

**Under 30 seconds? NO.**

**Friction points:**
1. **Document picker on Access Control** — arriving on the screen shows a "Select a document" prompt. You have to click and pick the document you just uploaded. The system knows which document you just uploaded; it should be pre-selected.
2. **Policy form cognitive load** — 11 fields. The architect needs 1 (disable download). The rest are noise until they have a reason to care.
3. **Two-step to get the link** — "Save Policy" creates the link, then you must navigate to the Share Link tab to copy it. The link URL should appear immediately after creation.

**What the experience should feel like:**
- Upload PDF → click "↗ Share" on the document row → a modal appears with a pre-generated link and a "Disable download" toggle → copy link. Done in 3 clicks, under 20 seconds.

**Verdict: FRICTION. 45-65 seconds vs. 20-second target.**

---

## Persona 2 — The Consultant

**Who they are:** Solo consultant or small agency. Shares proposals and reports with prospects. Most important daily need: "Did they read my proposal yet?" Uses this to time follow-up calls.

**Most common task:** Know when a specific prospect opens a proposal for the first time.

### Task walkthrough (current product):

| Step | Action | Screen | Time |
|---|---|---|---|
| 1 | Upload proposal PDF | Upload | ~20s (upload + processing) |
| 2 | Create share link (as above) | Access Control | ~45s |
| 3 | Send link to prospect | (email client, out of band) | ~30s |
| 4 | Wait |  | (hours or days) |
| 5 | Check Analytics screen for views | Analytics | ~5s |
| 6 | Realize the range filter doesn't work | Analytics | ~5s (confusion) |
| 7 | Navigate to Access Control → Access Log | Access Control | ~10s |
| 8 | See viewer event (if prospect opened it) | Access Control | ~5s |

**Core feature (real-time notification): NOT AVAILABLE.**

The consultant's primary need — "notify me when my document is opened" — does not exist in SecureDoc. DocSend sends an email the moment the document is opened. Slack integrations, Salesforce integrations, and Zapier flows are built around this event.

In SecureDoc, the consultant must manually check the analytics or access log. If they forget to check, they might call the prospect before they've read the proposal, or miss the 5-minute window when the prospect is actively engaged with the document.

This is the most commercially damaging gap in the product. The target user for a document-sharing tool with per-page analytics is a sales-oriented professional. Sales-oriented professionals need real-time signals.

**Verdict: MISSING CORE FEATURE. The product does not deliver the key value proposition for this persona.**

**What needs to happen:**
1. Fix `link.viewed` dispatch in `viewer.py` (15-minute backend change)
2. Wire SSE hook in AppShell (1-day frontend change)
3. Show toast: "Your proposal was just opened by someone@domain.com"

That is the single change that would make this persona love the product.

---

## Persona 3 — The Builder

**Who they are:** Construction project manager or developer. Shares specifications, drawings, and contracts with subcontractors. Needs to restrict access to the company email domain. Doesn't want specs forwarded to competitors.

**Most common task:** Share a specification PDF restricted to emails from a specific company domain.

### Task walkthrough (current product):

| Step | Action | Screen | Time |
|---|---|---|---|
| 1 | Upload spec PDF | Upload | ~20s |
| 2 | Navigate to Access Control | Sidebar | ~2s |
| 3 | Select document | Document Picker | ~5s |
| 4 | Find "Allowed Domains" field | Policy tab | ~8s (it's in the first card, but the form is dense) |
| 5 | Type "@contractor.com" in the field | Policy | ~5s |
| 6 | Click "Save Policy" / "Create Share Link" | Policy | ~2s |
| 7 | Copy link | Share Link tab | ~3s |
| **Total** | | | **~45s** |

**Under 30 seconds? NO.**

**Additional friction:** The "Allowed Domains" field has hint text: "Comma-separated, e.g. @acme.io". This is helpful. But "Allowed Domains" sounds like it might mean website domains. The builder might wonder: "Does this mean the domain of my company website, or the email domain of the people I'm sending this to?" The field should be labeled "Restrict to email domain(s)."

**Friction points:**
1. Same document picker / navigation issue as Persona 1
2. "Allowed Domains" label is ambiguous
3. No feedback that the restriction is active — the share link looks identical whether restricted or not. There should be a visual indicator on the link: "🔒 Email-restricted" badge.

**Verdict: FRICTION. 45 seconds vs. 20-second target. Achievable with quick share shortcut.**

---

## Persona 4 — The Client (Viewer)

**Who they are:** A client, prospect, or reviewer receiving a shared document. They didn't sign up for SecureDoc. They just got a link.

**Most common task:** Open a shared document and read it on any device.

### Task walkthrough (current product):

| Step | Action | Screen | Time |
|---|---|---|---|
| 1 | Click link | Browser | ~1s |
| 2 | (If password-protected) Enter password | Access Gate | ~5s |
| 3 | Document loads | Viewer | ~2-5s depending on size |
| 4 | Read document | Viewer | — |

**Under 30 seconds? YES — core reading is fast.**

**Secondary task: Leave feedback on page 3.**

| Step | Action | Screen | Time |
|---|---|---|---|
| 1 | Reading document | Viewer | — |
| 2 | Want to leave a comment | Viewer | (looking for how) |
| 3 | Find annotation tool in dense toolbar | Viewer toolbar | ~10s to discover |
| 4 | Click annotation tool | Viewer | ~2s |
| 5 | Select area on page | Viewer | ~5s |
| 6 | Type comment | Comment input | ~15s |
| 7 | Submit | Viewer | ~2s |
| **Total** | | | **~35-40s** |

**Under 30 seconds? BARELY FAILS — mostly due to toolbar discovery.**

The annotation tool is in a dense 15-icon toolbar. A client viewing a PDF has no idea that they can annotate it unless they discover the pencil/highlight icon. There is no prompt, no "Leave your feedback" call-to-action for viewers who have annotation permission.

**Friction points:**
1. Toolbar icons are not labeled — user must hover to discover what each does
2. No visual invitation to leave feedback if the owner granted annotation permission
3. After leaving an annotation, there is no confirmation that the owner received it

**Secondary task: Check if a specific page has the information they need.**

The TOC is there. Search is there. These work. The client can navigate efficiently.

**Verdict: PASS for core reading. FRICTION for feedback discovery.**

---

## Summary

| Persona | Core Task | Under 30s? | Primary Friction |
|---|---|---|---|
| Architect | Share PDF, disable download | NO (45-65s) | No quick-share; policy form too long; two steps to get link |
| Consultant | Know when doc is opened | IMPOSSIBLE | link.viewed not wired; no real-time notification |
| Builder | Share with email domain restriction | NO (45s) | Same as architect + ambiguous label |
| Client (viewer) | Read shared document | YES (~8s) | None for core reading |
| Client (viewer) | Leave feedback | BARELY (35s) | Annotation discovery; no invitation UX |

---

## The 30-Second Fix

Every owner persona fails the 30-second test due to one root cause: **there is no direct path from "document" to "share link."**

The fix requires no backend work:

**Add a "↗ Share" button on every document row in the Upload screen.**

When clicked:
1. Call `POST /api/links` with `{document_id, permissions: {watermark_enabled: true, can_download: false}}` (sensible defaults)
2. Show the resulting link URL in a small popover with a "Copy" button
3. Done

That is 2 clicks and 5 seconds. Every owner persona goes from FAIL to PASS.

The Policy screen remains for users who want to configure password, email restriction, expiry, etc. But the default path is instant.

This is the highest-leverage product change in the entire codebase.
