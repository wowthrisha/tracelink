# Workflow Comparison
Date: 2026-06-22
Perspective: Founder + Product Lead
Focus: Sharing, Viewing, Tracking, Feedback only.
Competitors: DocSend, Google Drive, Notion, Dropbox

---

## Workflow 1 — Share a Document

**User story:** I have a PDF. I want to send it to someone and control whether they can download it.

### DocSend
1. Upload PDF (drag-drop)
2. Click "Get Link" on the document card
3. Toggle "Disable Download" in a small modal
4. Copy link
**Steps: 4. Time: ~20 seconds.**

### Google Drive
1. Upload PDF
2. Click Share → copy link → change access to "Anyone with the link"
3. Cannot disable download (only prevent re-sharing in Google Workspace)
**Steps: 3. Time: ~15 seconds. Download control: NOT available.**

### Notion
1. Create a page, embed PDF
2. Click Share → Publish to web
3. No download control for PDFs
**Steps: 3. Time: ~30 seconds. Download control: NOT available.**

### Dropbox
1. Upload → Share → copy link
2. No download disable on free tier
**Steps: 3. Time: ~20 seconds. Download control: Paid only, not per-document.**

### SecureDoc
1. Upload PDF
2. Navigate to "Access Control" screen
3. Select document (if not already selected — requires DocumentPicker)
4. Default lands on "Policy" tab
5. Toggle "Download" permission off in the 7-toggle grid
6. Click "Save Policy" (creates share link)
7. Navigate to "Share Link" tab
8. Copy link
**Steps: 8. Time: ~90 seconds (first time) / ~60 seconds (returning user).**

**SecureDoc verdict: BEHIND on speed. WAY ahead on control.**

DocSend has 3 download-related permissions. SecureDoc has 7 permissions + password + email allowlist + domain restriction + IP allowlist + max views + max concurrent sessions + expiry. The depth is unmatched. The friction to get there is 4x DocSend.

**The fix is not to remove features. It is to ship sensible defaults and surface the link in 2 clicks:**
- Upload → click "↗ Share" on the doc row → link created with defaults → copy it. Done in 2 steps.
- Advanced users then click into policy settings.

---

## Workflow 2 — Viewer Opens a Shared Document

**User story:** I received a link. I open it. I read the document.

### DocSend
1. Click link → document opens in browser
2. Optional: Enter email (if owner required NDA/email gate)
3. Read document (browser-rendered PDF viewer)
**Steps: 1-2. Friction: minimal.**

### Google Drive
1. Click link → Google Docs/Drive viewer
2. Must be signed into Google (if restricted)
**Steps: 1. Friction: Google account required for restricted docs.**

### Notion
1. Click link → Notion page loads
2. Scroll to read
**Steps: 1. Friction: minimal.**

### SecureDoc
1. Click link → Access gate renders
2. If password: enter password
3. Document loads in custom viewer
4. Annotations, TOC, Links panel, Insights, Search all available
**Steps: 1-2. Friction: password adds one step.**

**SecureDoc verdict: MATCHED on speed. AHEAD on viewer features.**

The SecureDoc viewer is genuinely better than DocSend's PDF viewer: TOC, page-level search, annotation creation, bookmark, links panel, per-session watermark visible in the viewer. A client receiving a proposal in SecureDoc gets a better reading experience than DocSend.

The one gap: if the owner set a password, the viewer must enter it — and there is no "forgot my link password" recovery flow. The owner must send the password separately.

---

## Workflow 3 — Track Who Viewed Your Document

**User story:** I shared a proposal 3 days ago. I want to know: did they open it? What pages did they read?

### DocSend
1. Open DocSend dashboard
2. See document card with "3 views" badge
3. Click document → see per-viewer breakdown with time spent per page, pages read, % completion
4. Real-time notification: email or push when document is opened
**Steps: 2-3. Time: ~10 seconds. Real-time notification: YES.**

### Google Drive
1. Open Drive → check Activity panel
2. See "viewed by X" — no per-page detail
3. No real-time notification unless using Google Workspace admin tools
**Steps: 2. Per-page detail: NO. Notification: NO.**

### Notion
1. No analytics on page views
**Per-page detail: NO. Notification: NO.**

### Dropbox
1. See basic open count on shared link
2. No per-page detail
**Per-page detail: NO. Notification: NO.**

### SecureDoc
1. Navigate to Analytics screen
2. Select "By Document" tab
3. Find the document in the table
4. See: total views, sessions, avg time on page, completion %, risk score
5. Click row → page heatmap appears below showing page-by-page attention
6. Navigate to Access Control → Access Log for per-viewer event timeline
7. No real-time notification (link.viewed event not dispatched — open issue)
**Steps: 5-6. Per-page detail: YES. Real-time notification: NO (critical gap).**

**SecureDoc verdict: AHEAD on depth. BEHIND on immediacy.**

The page heatmap is a feature DocSend charges for (Pro/Advanced plan). SecureDoc has it at every level. Seeing that a prospect spent 4 minutes on page 7 (the pricing page) is the kind of data that changes sales behavior.

But the missing real-time notification is a critical gap. DocSend's key value proposition is "know the moment your document is opened." SecureDoc cannot deliver this. A consultant who shares a proposal before an important meeting wants to know in real-time if the client opened it. Checking the analytics dashboard manually defeats the purpose.

**This is the single most important missing feature for competitive parity.**

---

## Workflow 4 — Collect Feedback on a Document

**User story:** I shared a design for review. I want to get comments tied to specific pages.

### DocSend
1. Viewer can leave comments on pages (DocSend Rooms feature — paid)
2. Owner sees comments in dashboard
3. No reply threading
**Threading: NO. Page-level: YES (paid).**

### Google Drive
1. Open document in Docs/Slides/Sheets → add comment → assign to reviewer
2. Real-time collaboration (live editing visible)
3. Email notification on comment
**Threading: YES. Page-level: YES. Real-time: YES.**

### Notion
1. Leave comments on any block
2. Email notification on comment
**Threading: YES. Block-level: YES. Real-time: YES.**

### Dropbox
1. No structured commenting on PDFs
**Commenting: NO.**

### SecureDoc
1. Viewer annotates in the viewer (highlight/draw/comment) — requires can_annotate permission
2. Owner sees annotations in Access Control → Annotations tab
3. Owner sees feedback threads in Access Control → Feedback tab
4. Owner can reply inline to feedback threads
5. Export feedback to CSV with reviewer activity breakdown
**Threading: YES. Page-level: YES. Export: YES. Notification to owner on new feedback: NOT WIRED.**

**SecureDoc verdict: AHEAD on structure (threading + export). BEHIND on notification.**

The feedback system is genuinely powerful: threaded conversations, per-page context, reviewer identity, export to CSV with per-reviewer activity. Google Docs has better real-time collaboration, but for reviewing a finalized PDF, SecureDoc's feedback mechanism is more appropriate than comment threads on an editable document.

The gap: the owner doesn't get notified when a viewer leaves feedback. The SSE infrastructure exists; it's just not connected for this event.

---

## Summary Matrix

| Capability | SecureDoc | DocSend | Google Drive | Notion | Dropbox |
|---|---|---|---|---|---|
| Upload + share in under 30 seconds | NO ❌ | YES ✅ | YES ✅ | YES ✅ | YES ✅ |
| Disable download per link | YES ✅ | YES ✅ | NO ❌ | NO ❌ | Paid only |
| Password protection | YES ✅ | YES ✅ | NO ❌ | NO ❌ | YES ✅ |
| Email domain restriction | YES ✅ | YES ✅ | Workspace only | NO ❌ | NO ❌ |
| IP restriction per link | YES ✅ | NO ❌ | NO ❌ | NO ❌ | NO ❌ |
| Max concurrent viewers per link | YES ✅ | NO ❌ | NO ❌ | NO ❌ | NO ❌ |
| Forensic watermark per viewer | YES ✅ | NO ❌ | NO ❌ | NO ❌ | NO ❌ |
| Per-page view analytics | YES ✅ | YES ✅ | NO ❌ | NO ❌ | NO ❌ |
| Page heatmap | YES ✅ | Paid only | NO ❌ | NO ❌ | NO ❌ |
| Real-time "document opened" notification | NO ❌ | YES ✅ | NO ❌ | NO ❌ | NO ❌ |
| Viewer annotations with threading | YES ✅ | Paid only | NO (PDF) | YES ✅ | NO ❌ |
| Feedback export to CSV | YES ✅ | NO ❌ | NO ❌ | NO ❌ | NO ❌ |
| Hyperlink extraction from PDF | YES ✅ | NO ❌ | NO ❌ | NO ❌ | NO ❌ |
| Share in 2 clicks | NO ❌ | YES ✅ | YES ✅ | YES ✅ | YES ✅ |

**SecureDoc wins on: depth of control, analytics, forensic security, annotation quality.**
**SecureDoc loses on: speed of sharing, real-time notification, first-time experience.**

The product has a strong competitive position in the features that matter for serious document security. It loses on the features that matter for casual adoption. This is a positioning choice: if SecureDoc is for enterprises and professionals who care about forensic tracking and access control, the depth is right. If it's competing for anyone who shares a PDF, the friction is too high.

**Recommendation: Pick the serious user. Own the forensic security story. Fix the time-to-first-share.**
