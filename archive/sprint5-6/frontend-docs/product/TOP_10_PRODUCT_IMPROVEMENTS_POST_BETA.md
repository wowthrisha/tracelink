# Top 10 Product Improvements — Post-Beta

**Date:** 2026-06-23  
**Basis:** REAL_WORLD_USAGE_AUDIT.md · USER_ABANDONMENT_POINTS.md  
**Scope:** Changes that would have the highest impact on real user retention and activation, ranked by abandonment risk × affected personas × implementation complexity.  
**Rules:** No implementation detail. No code. Product decisions only.

---

## Rank 1 — Rename "Access Control" to "Share" / "Sharing"

**Priority:** P1  
**Abandonment point:** AP-1  
**Personas affected:** All 5  
**What:** Rename the sidebar nav item, the screen header, and all references from "Access Control" to "Sharing." Update the "Configure in Access Control →" link in QuickShare to "Customize sharing options →" or "Open sharing settings →."  
**Why it matters:** "Access Control" is the most significant labeling mismatch in the product. Five distinct personas with completely different backgrounds — consultant, architect, PM, founder, sales rep — all share the same mental model: "I need to share this document." Not one of them maps "sharing" to "access control." This single change affects every user's first interaction with the core feature. It is the highest-leverage rename in the product.  
**What it doesn't require:** No database changes. No API changes. String-only change across sidebar, header, QuickShare modal.  
**Risk:** None. This is an additive labeling change.

---

## Rank 2 — Show Feedback badge on login without requiring activeDoc

**Priority:** P1  
**Abandonment point:** AP-2  
**Personas affected:** 1, 4, 5  
**What:** On app load (after login), fetch the aggregate unread feedback count across all documents the user owns — not just for `activeDoc`. Surface this count as the sidebar badge. A user who logs in fresh, sees "Feedback (3)" in the sidebar, and knows immediately that attention is needed.  
**Why it matters:** The current implementation makes the feedback badge invisible on fresh login because it depends on `activeDoc`. This means the most important notification surface is dark exactly when the user most needs to see it — on return visits. For founders and sales professionals tracking investor/prospect engagement, this is the difference between a sticky product and one they stop checking.  
**What it doesn't require:** One additional API call on load. No schema change. The endpoint already supports `?resolved=false` filtering.  
**Risk:** Low. Additive behavior on app startup.

---

## Rank 3 — Add email notifications for key events

**Priority:** P1  
**Abandonment point:** AP-6, AP-7  
**Personas affected:** 4, 5 (and 2, 3 for reply notifications)  
**What:** Send an email notification to the document owner when: (a) a viewer opens a shared link, (b) a viewer leaves a comment or sticky note, (c) a viewer's reply is available (for viewers). Configurable — let users opt in per-document or globally.  
**Why it matters:** The browser-polling notification model (check the tab every 30s) requires the user to keep SecureDoc open to receive any signal. For the sales professional who sent a proposal and closed the tab, and the founder waiting for investor feedback, this is a hard blocker. The product has all the event data (link views, annotations) — it just doesn't dispatch them externally. Without email notifications, SecureDoc cannot compete with any document intelligence tool on the market (DocSend, PandaDoc, Notion) for the "be alerted when your doc is read" use case.  
**What it doesn't require:** A transactional email provider integration (e.g., Resend, SendGrid). Backend event hooks exist (webhook system). Email dispatch can be a thin wrapper on existing webhook events.  
**Risk:** Medium. Requires backend email service integration and user preference storage.

---

## Rank 4 — Explain the link-based sharing model

**Priority:** P1  
**Abandonment point:** AP-3  
**Personas affected:** 3, 5  
**What:** On the Sharing screen (renamed from Access Control), add a one-sentence orientation at the top: "SecureDoc shares documents via secure links — create a link, copy it, and send it via email or message." On the QuickShare modal, add the same framing above the URL. No redesign — just 1–2 lines of copy in the right places.  
**Why it matters:** Users from email-attachment and DocuSign backgrounds expect to enter a recipient's email address and click Send. The product's link-based model is valid and even superior in many ways (revocable, trackable, policy-enforced) — but it's never explained. The mismatch causes users to conclude the product is broken or missing a feature. A single sentence of onboarding copy eliminates this.  
**What it doesn't require:** No code change to the sharing logic. Copy only.  
**Risk:** None.

---

## Rank 5 — Surface per-page heatmap from Analytics screen

**Priority:** P1  
**Abandonment point:** AP-5  
**Personas affected:** 2, 4, 5  
**What:** In the Analytics → By Document view, make document rows clickable. Clicking a row opens an expanded in-page detail view (or navigates to a document-specific analytics panel) that shows: page heatmap, per-session time breakdown, unique viewers, and link breakdown. The heatmap data and API already exist — this is a navigation/presentation gap.  
**Why it matters:** "Which slide did they spend the most time on?" is the single highest-value analytics question for investors, clients, and prospects. The data exists in the system. The heatmap is accessible — but only from the Viewer's toolbar, which is not where an analytics-minded user looks. Moving this into the Analytics screen turns SecureDoc from "basic view counts" to "document intelligence" in the user's perception.  
**What it doesn't require:** No new data. No schema change. No new API. Just routing the existing heatmap rendering into the analytics view.  
**Risk:** Low to medium. UI work only.

---

## Rank 6 — Clear the Create Link form after each successful link creation

**Priority:** P1  
**Abandonment point:** AP-4  
**Personas affected:** 3  
**What:** After `handleSave()` completes successfully, reset all policy form fields to their defaults: allowed emails cleared, password cleared, allowed domains cleared, expiry cleared, max views cleared. Keep permission toggles at defaults (watermark on, download off).  
**Why it matters:** A user creating multiple links for different recipients will silently carry the previous recipient's email restriction into each new link. This is not visible. The user will share a link intended for Subcontractor B that silently restricts access to Subcontractor A's email address. This is a correctness bug with security implications, not a UX preference issue.  
**What it doesn't require:** No API change. No schema change. State reset after successful POST.  
**Risk:** Near-zero. Strictly additive and defensive.

---

## Rank 7 — Replace "HIGH/MED/LOW risk" badge with meaningful context

**Priority:** P2  
**Abandonment point:** AP-10  
**Personas affected:** 1, 3, 4  
**What:** Either: (a) add a tooltip to the `RiskBadge` component that explains what the risk score measures ("Risk score is based on number of active links, access restrictions, and view volume"), or (b) show the badge only in Access Control and Analytics — not on the main document list where it's the first thing a new user sees. The Upload Dashboard is not the right place for a risk assessment.  
**Why it matters:** Every new document shows HIGH risk. To a first-time user, this communicates "your document is in danger" when it means "this document has high sharing activity." The label causes support inquiries and erodes trust on first use. Removing it from the Upload Dashboard, or adding a one-sentence tooltip, eliminates this entirely.  
**What it doesn't require:** No data change. Tooltip text or conditional rendering.  
**Risk:** None.

---

## Rank 8 — Make hover-reveal action buttons always visible (or persistent after first use)

**Priority:** P2  
**Abandonment point:** AP-11  
**Personas affected:** 1, 2  
**What:** Show the document row's action buttons (View, Access/Share, Share, Delete) as always-visible, or as visible with reduced opacity that becomes full opacity on hover. The "↗ Share" button — the primary sharing trigger — should not require the user to discover the hover pattern before they can share.  
**Why it matters:** The QuickShare flow is the fastest path to sharing. It's triggered by hovering a document row and clicking "↗ Share." A user who clicks the row (which opens the viewer) never finds the "Share" button. The entire QuickShare workflow depends on a hover-discovery pattern that is invisible on first use. Making these buttons visible at all times (or with low-opacity default) removes a discovery barrier from the highest-frequency action in the product.  
**What it doesn't require:** No API change. CSS opacity adjustment.  
**Risk:** Visual change to the document list — minor redesign risk. Low.

---

## Rank 9 — Fix the "Allowed Domains" hint and add inline explanations for policy fields

**Priority:** P2  
**Abandonment point:** AP-13  
**Personas affected:** 1, 2  
**What:** Fix the `@acme.io` hint to `acme.io`. For each policy field that requires specific input knowledge, add a one-line explanation:
- Allowed Domains: "Restrict to viewers whose email matches these domains (e.g. acme.io)"
- IP Allowlist: "Only allow access from these IP addresses or ranges"  
- Max Concurrent Sessions: "Maximum number of people who can view this link at the same time"  
- Allowed Emails: "One verified email per line — viewers must enter this email to access"  
**Why it matters:** The Create Link form has 10+ fields. Half of them require security knowledge to understand. Users who don't understand "CIDR" or "concurrent sessions" skip them — which is fine. But users who have a legitimate use case (restrict to company email domain) often fail to configure it correctly because the hint format is wrong. Bad hints are worse than no hints.  
**What it doesn't require:** No logic change. Copy and hint text changes only.  
**Risk:** None.

---

## Rank 10 — Add "what your viewer will see" summary before link creation

**Priority:** P2  
**Abandonment point:** AP-17  
**Personas affected:** 4, 5  
**What:** Before creating a link (or in a small confirmation area at the bottom of the Create Link form), show a plain-language summary of the configured policy: "This link will: require a password · expire in 7 days · show a watermark · disable download." Update this summary dynamically as form fields change.  
**Why it matters:** Misconfigured links are a recurring issue. A founder who forgets to enable the password, or a PM who accidentally leaves email restriction from a previous link, creates a security issue without knowing it. A live "what your recipient will experience" summary serves two purposes: it builds user confidence that the policy is correct, and it catches misconfiguration before the link is created. The more the user understands what they're creating, the more they trust the product.  
**What it doesn't require:** No API change. Client-side rendering from existing form state.  
**Risk:** None.

---

## Honorable Mentions (ranked 11–15)

| Rank | Issue | Priority | Abandonment Point |
|------|-------|----------|-------------------|
| 11 | Feedback empty state: "can_annotate" → plain English | P2 | AP-15 |
| 12 | Dismiss button placement next to Share CTA | P2 | AP-19 |
| 13 | Analytics "Completion" shows "—" instead of "0%" | P3 | AP-24 |
| 14 | "← Docs" goes to Upload, not previous screen | P3 | AP-20 |
| 15 | Upload button says "PDF" but accepts DOCX, TXT, MD, LOG | P3 | AP-21 |

---

## Summary Table

| Rank | Improvement | Priority | Personas | Scope |
|------|-------------|----------|----------|-------|
| 1 | Rename "Access Control" → "Sharing" | P1 | All 5 | String changes |
| 2 | Feedback badge on fresh login (all docs) | P1 | 1, 4, 5 | API call on load |
| 3 | Email notifications for views/feedback | P1 | 4, 5 | Backend integration |
| 4 | Explain link-based sharing model | P1 | 3, 5 | Copy only |
| 5 | Per-page heatmap from Analytics screen | P1 | 2, 4, 5 | UI routing |
| 6 | Clear form state after link creation | P1 | 3 | State reset |
| 7 | Risk badge tooltip / move off Upload screen | P2 | 1, 3, 4 | Copy / conditional render |
| 8 | Make doc row actions always visible | P2 | 1, 2 | CSS opacity |
| 9 | Fix domain hints, add field explanations | P2 | 1, 2 | Copy |
| 10 | Policy summary preview before link creation | P2 | 4, 5 | Client-side render |

---

*Generated: Sprint 4.9 — Real World Validation Audit. No implementation.*
