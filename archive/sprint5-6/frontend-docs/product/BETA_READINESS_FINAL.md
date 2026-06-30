# Beta Readiness Final Decision — Sprint 4.8B Phase 5

**Basis:** Evidence from PRODUCT_NAVIGATION_AUDIT.md, PRODUCT_LANGUAGE_STANDARD.md, FIRST_TIME_USER_REPORT.md, RESPONSIVE_AUDIT.md, and direct source code review.  
**Scope:** Issues visible to real paying users only. No speculative features. No future roadmap.  
**Date:** 2026-06-23

---

## Scoring

Each dimension is scored 1–10. The overall verdict is based on the lowest scores, not the average.

---

### 1. Product Experience — 6 / 10

**What works well:**
- Upload → QuickShare → Copy URL flow is genuinely fast when the user knows where to look
- The Viewer is high quality: page rendering, DRM enforcement, annotation tools, concurrent session limiting, laser pointer, magnifier, TOC, search
- Access control depth (IP allowlist, domain restriction, password, expiry, session limit, max views) is exceptional for the product tier
- Feedback with replies and resolve/reopen (4.8A) is functional end-to-end
- Analytics KPIs, page heatmap, group analytics are all real data

**What hurts the experience:**
- Feedback is buried inside "Access Control" — a security screen. This is the single biggest experience gap for collaboration-oriented customers
- "Configure Access →" after upload takes users to the wrong mental model for sharing
- Non-functional `⌕ Filter` button in the primary header (`UploadScreen.jsx:204`) is a credibility problem — it fires a "coming soon" toast
- "Policy" tab creates new links but is not labeled as such
- No URL routing — refreshing or using browser back wipes the current screen

**Evidence:** `UploadProgressPanel.jsx:25`, `UploadScreen.jsx:204`, `AccessScreen.jsx:154`, `AppShell.jsx:29–30`

---

### 2. Discoverability — 5 / 10

**What is discoverable:**
- Upload: immediately visible and prominent
- Analytics: clearly labeled in sidebar, useful on day one
- Share (via Configure Access path): 6 steps but findable
- Notifications: in sidebar (wrong label, but findable)

**What is not discoverable:**
- Feedback: requires knowing to look in "Access Control" → "Feedback" tab. Zero indication in sidebar, zero count badge, no path from Notifications to Feedback
- Quick Share: `opacity: 0` hover-only — invisible until discovered by accident (`DocRow.jsx:59`)
- Page heatmap: requires clicking a document name in the Analytics → Documents tab — no affordance
- Unread notification count: tracked in code (`NotificationsScreen.jsx:46`) but `badge: null` in sidebar (`atoms.jsx:253`) — users cannot see they have unread events

**Predicted first-session outcome:** A first-time user shares a document, monitors Analytics for views, never finds Feedback.

**Evidence:** `DocRow.jsx:59`, `atoms.jsx:253`, `NotificationsScreen.jsx:46`

---

### 3. Workflow Quality — 7 / 10

**Strengths:**
- Share link creation end-to-end: works, creates real link with correct permissions
- Edit Link (4.8A): works, pre-populates all fields, calls PATCH correctly
- Revoke all / Revoke single: works
- Feedback reply + resolve (4.8A): works
- Viewer back navigation (4.8A): works
- Document row click → Viewer (4.8A): fixed
- Group assignment, group filter, group analytics: works consistently
- Storage retention policy change: works
- API key scope selection, webhook delivery history: works

**Gaps:**
- No path from Viewer → share current document
- No path from Analytics → manage a document's links
- No path from Notifications → open the document that was viewed
- After upload: "Configure Access →" CTA (wrong label for the intent)
- `⌕ Filter` in header fires a toast — a broken workflow element in the primary view

**Evidence:** All screen files as read above

---

### 4. Consistency — 5 / 10

**Naming inconsistencies (see PRODUCT_LANGUAGE_STANDARD.md for full table):**
- "Upload" sidebar label ≠ "Upload Dashboard" screen title ≠ what the screen does (document library)
- "Policy" tab creates links; "Share Link" tab manages links — naming does not communicate the relationship
- "Access Log" (tab) vs "Audit Log" (sidebar) — two names for two different log types with identical vocabulary
- "Notifications" screen is a polled event feed, not notification preferences
- "Events" means three different things in three screens (webhook triggers, activity feed entries, audit log actions)
- "↗ Share" button opens "Quick Share" modal — button and modal name differ
- "Configure Access →" button leads to an "Access Control" screen for a sharing workflow
- Unread badge tracking exists in code but is not connected to the sidebar

**Visual consistency (no issues found):**
- Design tokens (`C.*`, `mono`) are used consistently across all screens
- Card, Btn, Chip, Modal, Field, Header, SectionLabel atoms are used consistently
- Color system (teal primary, error red, success green, warning amber) is consistent

**Evidence:** `atoms.jsx:222–263`, `AccessScreen.jsx:153–158`, `WebhooksScreen.jsx:7`, `NotificationsScreen.jsx:22–29`

---

### 5. Responsiveness — 3 / 10

**Critical failures:**
- Sidebar (`atoms.jsx:270`): `width: 210, flexShrink: 0` — no responsive collapse on any screen size. This single issue cascades to every authenticated screen on mobile
- Modals: all use fixed pixel widths (420–520px) with no `maxWidth: 95vw` — clip on phones
- Upload stats grid: `repeat(4, 1fr)` — 41px columns on 375px phone
- Document hover actions: `opacity: 0` / `onMouseEnter` — touch-incompatible; primary document actions are unreachable on touch devices

**Partial mitigations:**
- Storage table has `overflowX: auto` — table scrolls horizontally on mobile
- Notifications screen uses single-column layout — mostly works on mobile

**Tablet (768px):** Every screen is degraded but functional with scroll. No outright breakage except modals and sidebar.  
**Phone (375px):** Core document management (upload, share, feedback) is not usable.

**Evidence:** `atoms.jsx:270`, `UploadScreen.jsx:211`, `DocRow.jsx:59`, `AccessScreen.jsx:225`, `AccessScreen.jsx:280`

---

### 6. Security — 9 / 10

**Strengths (verified in source):**
- JWT auth on all owner endpoints, scope-based API key auth
- Ownership verification at every endpoint (doc.user_id == current_user["user_id"])
- `invalidate_link()` called on every link PATCH — in-flight viewer sessions see policy changes within one page turn
- IP allowlist, domain restriction, password, expiry, max views, max concurrent sessions — all enforced server-side
- Watermark enabled by default in QuickShare (`QuickShareModal.jsx:7–14`)
- Rate limiting on all write endpoints (`@limiter.limit("30/minute")`)
- Feedback resolve ownership chain: JWT → document → link → annotation (4.8A, `annotations.py`)
- Session token-based viewer access, separate from owner JWT

**Minor gap:**
- No rate limit on share link creation per document (found in 4.8 audit — not addressed yet)
- "Risk" badge (HIGH/MED/LOW) shown without explanation — users don't know what triggers HIGH

**Evidence:** `links.py:200–252`, `viewer_annotation_service.py:152–168`, `annotations.py` (owner resolve added 4.8A)

---

### 7. Reliability — 8 / 10

**Strengths:**
- 13/13 tests passing consistently through all 4.8A commits
- Build is clean (245kb, no warnings)
- Error boundaries: `ViewerErrorBoundary` wraps the Viewer in `AppShell.jsx:108`
- All async operations have try/catch with user-facing toast errors
- Polling in `NotificationsScreen` has interval cleanup in `useEffect` return
- All API methods follow the same auth/error pattern

**Gaps:**
- No URL routing means accidental browser refresh loses the user's current position
- `activeDoc` context is not persisted — a refresh while viewing a document returns to Upload
- No retry logic on failed uploads (poll stops at `MAX_POLL_ATTEMPTS = 150`)
- No offline/connectivity error differentiation — API errors and network errors produce the same generic toast

**Evidence:** `AppShell.jsx:29–30`, `UploadScreen.jsx:14`

---

## Score Summary

| Dimension | Score | Verdict |
|-----------|-------|---------|
| Product Experience | 6/10 | Functional with friction |
| Discoverability | 5/10 | Core feature (Feedback) is hidden |
| Workflow Quality | 7/10 | Primary workflows complete; cross-screen paths missing |
| Consistency | 5/10 | Terminology conflicts across 6 areas |
| Responsiveness | 3/10 | Mobile fails at sidebar level; touch actions unreachable |
| Security | 9/10 | Enterprise-grade; minor gaps only |
| Reliability | 8/10 | Stable; no URL routing is the primary gap |

**Weighted average:** 6.1 / 10

---

## Decision: GO WITH CONDITIONS

SecureDoc is NOT ready for an unmanaged self-serve beta. It IS ready for a **managed beta with selected customers** on desktop/laptop only.

---

## GO conditions — what is ready today

1. **Core sharing workflow works end-to-end** — upload, create link, set policy, copy URL, viewer opens correctly
2. **Security controls are production-grade** — IP allowlist, domain restriction, password, expiry, session limits, watermark, revocation
3. **Viewer quality is high** — DRM, annotations, bookmarks, TOC, search, page thumbnails, concurrent session limiting
4. **Analytics are real** — page heatmap, per-document stats, group rollup, CSV export
5. **Edit Link (4.8A) works** — updating an existing link no longer creates ghost links
6. **Feedback with Resolve (4.8A) works** — owner can reply and close feedback threads
7. **Document row click (4.8A) is fixed** — clicking a doc opens the Viewer
8. **Viewer back navigation (4.8A) works** — "← Docs" button in toolbar

---

## CONDITIONS — what must be in place before unmanaged beta

**Condition 1 — Remove ⌕ Filter stub (UploadScreen.jsx:204)**  
A "coming soon" toast on a primary header button is a trust-breaking element. Remove the button entirely. The inline search already exists and works (`UploadScreen.jsx:268`).  
Effort: 1 line.

**Condition 2 — Sidebar mobile collapse OR restrict beta to desktop**  
`atoms.jsx:270`: fixed 210px sidebar breaks every screen on mobile. For a managed desktop-only beta, explicitly communicate "desktop Chrome/Firefox required." For any mobile user, this is a hard block. If mobile is not in beta scope, document and enforce this.  
Effort: 2 hours (hamburger collapse) OR 0 hours (document the constraint).

**Condition 3 — Make Feedback discoverable**  
The collaboration value proposition (share → get feedback → reply → resolve) is not completeable by a first-time user without documentation. At minimum:  
(a) Add unread count badge to sidebar: connect `NotificationsScreen` unread tracking to sidebar badge  
(b) OR add Feedback as a visible item/indicator somewhere outside Access Control  
Effort: 2 hours (sidebar badge only).

**Condition 4 — Rename "Configure Access →" to "Share Document →"** (`UploadProgressPanel.jsx:25`)  
This is a 3-word change that removes the most confusing CTA in the first-session flow.  
Effort: 1 line.

---

## WATCH LIST — issues that do not block managed beta but must be tracked

| Issue | Source | Impact |
|-------|--------|--------|
| No URL routing | `AppShell.jsx:29` | Browser back broken; refresh loses position |
| "⌕ Filter" stub | `UploadScreen.jsx:204` | Credibility — fire after Condition 1 |
| "Policy" tab name | `AccessScreen.jsx:154` | Confusion for first-time users |
| Touch-incompatible hover actions | `DocRow.jsx:59` | All primary doc actions unreachable on touch |
| Fixed-width modals | All modal definitions | Clip on viewports < 520px |
| No notification badge on sidebar | `atoms.jsx:253` | Unread events not visible |
| "Notifications" label mismatch | `atoms.jsx:254` | Implies push preferences, is an event stream |
| Analytics document rows non-navigable | `AnalyticsScreen.jsx` | Click does nothing |
| Risk badge undocumented | DocRow, AccessScreen | HIGH/MED criteria unknown to users |
| No link creation rate limit | `links.py` | Potential abuse by API users |

---

## What This Is NOT

This report does not recommend:
- Adding AI features
- Adding dashboards
- Adding new infrastructure (SSO, email service, CDN)
- Adding new database tables
- Adding speculative features

Every finding above is traceable to a specific line of existing code and visible to a real user today.

---

*Generated: Sprint 4.8B Phase 5 — no implementation performed. Do not commit. Do not push.*
