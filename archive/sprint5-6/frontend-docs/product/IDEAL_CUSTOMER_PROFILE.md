# Ideal Customer Profile — SecureDoc

**Date:** 2026-06-23  
**Sprint:** 5.0 — Product Positioning & GTM  
**Method:** Segment analysis against actual product capabilities (DRM, access controls, page analytics, annotation feedback loop, webhooks, API).

---

## The One-Line ICP

**A professional services firm or solo operator who shares proprietary documents with external parties as a core business activity, has been burned by unauthorized distribution at least once, and currently has no better solution than "hope the PDF stays private."**

---

## Segment Analysis

### Segment 1: Independent Consultants and Small Advisory Firms

**Who:** Solo to 5-person consulting practices. Strategy, finance, legal, HR, market research, technical advisory. Revenue: $300K–$5M. Primary deliverable: PDF reports, decks, analyses.

**Pain points:**
- Client shares a confidential deliverable with a competitor before the engagement ends
- Can't tell if the client actually read the 40-page report before the review meeting
- Client holds the PDF "forever" after the engagement — no way to revoke access
- Re-shares a prior version of a deliverable, creating confusion and liability
- Has no proof of delivery if there's a dispute about whether a report was sent

**Existing tools:** Email + PDF attachment. Some use Google Drive "view only" links (no real enforcement). Some use Dropbox. Almost none use a real DRM tool — the friction is too high for solo operators.

**Why they switch to SecureDoc:**
- One incident: "A client shared my competitive analysis with the company we were analyzing." This is the trigger. It happens once and they look for a solution immediately.
- The "did they read it?" question is real and daily — consultants build follow-up calls around whether the client engaged with the work.
- No IT department required. Solo operators can't use enterprise DRM tools.

**Why they would NOT switch:**
- "Good enough" mindset — 80% of their clients are trustworthy and they've never had an incident.
- If their deliverables are not sensitive (e.g., public research reports, reference documents).
- If they share documents infrequently (under 5 per month) — the setup cost doesn't justify the subscription.

**Willingness to pay:** $29–$79/month, solo pricing. Will pay more if team features exist. Price-sensitive — will compare vs. DocSend. Will not pay enterprise pricing.

**Acquisition channel:** Word of mouth in consultant communities (r/consulting, MBB alumni Slack, Lenny's community). ProductHunt. LinkedIn content targeting "consulting operations."

**Beachhead fit:** HIGH. This is the founding customer base. Solo operator, clear trigger event, no alternatives, immediate value.

---

### Segment 2: Architecture Firms (2–50 people)

**Who:** Principal architect through mid-size studio. Shares design documents, drawing sets, specifications, and design intent packages with structural engineers, MEP consultants, clients, and contractors.

**Pain points:**
- Contractors screenshot drawings and use them in presentations out of context, creating false expectations with clients
- Cannot revoke a drawing set after it's been issued when the design changes — contractors work from outdated versions
- Does not know if the structural engineer actually reviewed the issued drawing set before the coordination meeting
- Proprietary details and specifications screenshotted and reused by competitors
- Design concepts distributed before the client presentation

**Existing tools:**
- **Bluebeam Revu** — the industry standard for markup and collaboration on PDFs. Very sticky. Handles redlines, stamps, annotations. But Bluebeam is a review/markup tool, not a sharing/DRM tool. Drawings shared out of Bluebeam can be downloaded, forwarded, and printed freely.
- **Autodesk Construction Cloud / BIM 360** — for large firms on Autodesk subscriptions. Document management for the construction phase. Very expensive, project-centric, not suitable for sharing design deliverables with clients.
- **Email + PDF** — the default for 80% of small architecture firms.

**Why they switch to SecureDoc:**
- Version control of issued documents: revoke the old drawing, issue the new one, same link workflow
- Know which pages a contractor spent time on before a meeting (per-page heatmap is significant here)
- Viewer annotation feedback from reviewers — structural engineer annotates pages, architect sees it in the Feedback tab without a Bluebeam markup session
- IP protection on proprietary details

**Why they would NOT switch:**
- If they need native markup/redline workflows — Bluebeam is far superior for collaborative PDF review. SecureDoc's annotation system is lightweight (comments, sticky notes, highlights) not a CAD-grade markup tool.
- If all their sharing is within a Procore or Autodesk ecosystem with connected parties
- If the firm is on a large enterprise Autodesk contract that includes document sharing

**Willingness to pay:** $79–$199/month per studio. Architecture firms are used to software subscriptions (Autodesk, Adobe CC). Price is not the primary barrier; workflow fit is.

**Acquisition channel:** LinkedIn targeting AIA members and principals at 5–50 person firms. Architecture-focused media (Dezeen, ArchDaily audience). AIA chapter events.

**Beachhead fit:** HIGH. Architecture is a strong secondary segment. The viewer annotation feedback loop is a genuine differentiator for this use case. Autodesk/Procore don't serve the "send to a client, track if read, get feedback" workflow well.

---

### Segment 3: Engineering Firms (Structural, MEP, Civil, Geotechnical, 5–100 people)

**Who:** Structural, civil, MEP, or geotechnical engineering consultants. Share calculations, reports, specifications, and certifications with clients, GCs, and review authorities.

**Pain points:**
- Proprietary engineering methodologies embedded in calculation packages shared with clients — clients extract and reuse the approach
- Structural calculations distributed to competitors in contractor negotiations
- Cannot tell if an agency reviewer read the submission before a deadline meeting
- Certifications and stamped documents shared beyond the intended recipient

**Existing tools:**
- SharePoint (Office 365) — common in mid-size engineering firms. Shared folders, no expiry, no analytics, no DRM.
- Email + PDF
- Some use PandaDoc for contract delivery (not for technical documents)

**Why they switch to SecureDoc:**
- Strong IP concern: engineering calculations represent significant professional IP
- Domain restriction (allow only @client.com) maps well to their multi-client model
- Per-link audit trail for professional liability (who accessed what, when)
- IP allowlist for restricted government agency reviews

**Why they would NOT switch:**
- If the calculation review workflow requires active markup (red-line back-and-forth), which SecureDoc doesn't support natively
- If the firm is ISO-certified and requires document management software with version control history and approval workflows (not SecureDoc's scope)
- If their IT policy mandates on-prem or specific cloud providers

**Willingness to pay:** $99–$249/month team pricing. Engineering firms are accustomed to professional software costs (RISA, SAP2000, AutoCAD). IP protection is a compliance argument, not just convenience.

**Acquisition channel:** LinkedIn targeting principals at engineering firms. Engineering association events (ASCE, NSPE). Content targeting "engineering IP protection."

**Beachhead fit:** MEDIUM-HIGH. Strong fit on access controls and audit log. Gap: lacks the calculation markup/review workflow they're used to.

---

### Segment 4: Construction Project Managers (Owner's Representatives, PM Firms)

**Who:** Owner's representative firms or in-house PMs at developers. 1–30 people. Share progress reports, RFIs, submittals, and closeout packages with owners, subcontractors, and lenders.

**Pain points:**
- Can't confirm subcontractors actually read the updated RFI response before they pour concrete
- Lenders require document delivery confirmation for draw requests — email receipts are insufficient
- Progress reports distributed outside the project team
- Closeout packages containing proprietary operational data shared beyond the owner

**Existing tools:**
- **Procore** — the dominant tool for GC-side project management. Very sticky for large GCs. PM firms often use it for field management but not for owner-facing document delivery.
- **Email + PDF** — default for owner-facing documents
- **Google Drive** — for smaller PM operations

**Why they switch to SecureDoc:**
- Subcontractor confirmation: "did Mechanical read the revised RFI before Friday's coordination meeting?" Per-viewer access log addresses this
- Lender documentation: access log serves as delivery receipt
- Price: significantly cheaper than Procore for document delivery only

**Why they would NOT switch:**
- If they're already a full Procore shop — Procore's document management is "good enough" and switching friction is high
- If they share documents only internally or with partners who are already on their system
- If the volume is low (under 5 external shares per month)

**Willingness to pay:** $79–$199/month. Justified as "project documentation software" in overhead budget.

**Acquisition channel:** Construction PM associations (CMAA), LinkedIn targeting owner's rep firms. Positioning against Procore for the specific "external document delivery" use case.

**Beachhead fit:** MEDIUM. Good pain-problem fit but high Procore stickiness. Best opportunity is with PM firms that are not already Procore-heavy.

---

### Segment 5: Startup Founders (Pre-Seed to Series B)

**Who:** Founders actively fundraising or managing investor relations. Shares investor decks, financial models, data room documents, board materials.

**Pain points:**
- Investor deck forwarded to competitors or other portfolio companies without permission
- No visibility into which slide stopped an investor — "they said they'd review the deck but did they?"
- Deck version sent to one investor is now in circulation 6 months later after model changes
- Board materials shared beyond board members

**Existing tools:**
- **DocSend** — the default tool for this use case. Well-known in the startup community.
- Google Slides with view-only link — no analytics, no DRM
- Notion pages — no DRM, no link expiry
- Docusign for term sheet delivery (different use case)

**Why they switch to SecureDoc:**
- Per-slide/per-page analytics (which slides did each investor dwell on) — DocSend has this but at higher price
- Password-protected, expiring links — critical for data room
- Viewer annotation feedback from investors — investors can comment on specific slides. DocSend has no annotation feature.
- IP allowlist for sensitive data rooms (restrict to VC firm's known office IP)
- Revocation: when the round closes or a deck is superseded, revoke all old links

**Why they would NOT switch:**
- DocSend is deeply familiar in the VC community. Partners expect a DocSend link. Brand recognition matters.
- If the founder uses Notion or Pitch for their deck — format migration is friction
- If they need the DocSend → Salesforce integration for CRM tracking

**Willingness to pay:** $29–$79/month. Founders are price-conscious but understand the value of investor intelligence. Will pay for DocSend alternatives if feature-competitive.

**Acquisition channel:** YC community, Indie Hackers, Twitter/X founder community, VC-adjacent content ("DocSend alternative"). ProductHunt. This is also a viral segment — if an investor sees a SecureDoc-powered deck link, that's a discovery moment.

**Beachhead fit:** HIGH. This is the fastest path to early adoption because the need is immediate (active fundraising), the trigger is clear (privacy breach or needing slide analytics), and the community is reachable and vocal.

---

### Segment 6: Sales Teams (SMB and Mid-Market, 5–50 reps)

**Who:** Account executives and sales managers at B2B SaaS or professional services companies. Share proposals, pricing sheets, case studies, and ROI calculators.

**Pain points:**
- Cannot tell if a prospect opened the proposal before the follow-up call
- Pricing sheet forwarded to other vendors in a competitive evaluation
- Outdated proposal version from 6 months ago resurfaced by a prospect
- No signal on which section of the proposal got attention

**Existing tools:**
- **DocSend** — primary competitor for this exact use case
- **Seismic, Highspot, Showpad** — enterprise sales enablement (expensive, IT-managed)
- **PandaDoc** — for proposals with e-signature workflows
- Email + PDF / Google Drive

**Why they switch to SecureDoc:**
- More granular access controls than DocSend
- Viewer annotation: prospect can leave questions directly on the proposal, AE gets notified. This is a differentiated sales workflow no current tool offers.
- Per-page analytics: "Did they read the pricing page?" is the #1 question before a follow-up.
- Cheaper than DocSend Business for small teams

**Why they would NOT switch:**
- CRM integration is non-negotiable for sales teams. DocSend integrates with Salesforce and HubSpot. SecureDoc has no CRM integration. This is a hard blocker for teams with established CRM workflows.
- Sales managers need team-level reporting (who sent what, to whom, engagement by rep). SecureDoc's analytics are document-centric, not rep-centric.
- If the team uses PandaDoc for proposals, they won't maintain two tools.

**Willingness to pay:** $50–$150/seat/month if the tool is embedded in their sales workflow. BUT: without CRM integration, price sensitivity is much higher. This segment would pay $99/month for a team if there was a HubSpot or Salesforce integration.

**Acquisition channel:** Product-led growth via "powered by SecureDoc" on viewer links. LinkedIn targeting sales directors at 50–200 employee B2B companies. G2/Capterra reviews in the "document analytics" category.

**Beachhead fit:** MEDIUM. Strong pain fit but CRM integration is a near-mandatory feature for stickiness. Sales teams will trial but churn without it. Best to target solo AEs and small teams rather than sales organizations.

---

### Segment 7: Builders and General Contractors (Small-Mid, $5M–$100M revenue)

**Who:** Small to mid-size general contractors managing 2–20 active projects. Share subcontractor bid packages, RFIs, drawings, and contract documents with subcontractors and suppliers.

**Pain points:**
- Subcontractors submit bids based on outdated drawings because the contractor can't revoke old versions
- Bid documents shared between competing subcontractors
- Can't prove subcontractor received and acknowledged the bid package addendum

**Existing tools:**
- **Procore** — the dominant tool for mid-size GCs. Very deeply integrated (bidding, contracts, RFIs, submittals, scheduling). Switching cost is extreme.
- **Buildertrend** — for smaller residential builders
- **PlanGrid** (Autodesk) — for drawing management
- Email + PDF for smaller GCs

**Why they switch to SecureDoc:**
- Bid package privacy: restrict drawing access to specific subcontractors via email domain or allowed emails
- Per-link analytics: know which subs opened the bid package
- Addendum distribution with revocation of old packages

**Why they would NOT switch:**
- Procore handles this entire workflow (bidding, ITBs, addenda) for mid-size GCs. Switching cost is enormous.
- Buildertrend has basic document sharing for smaller builders
- The GC's risk model: drawing access is less of a concern than schedule and budget risk

**Willingness to pay:** $79–$149/month. BUT: the switching cost from Procore is too high for most. Only accessible at the small GC level that hasn't committed to Procore yet.

**Acquisition channel:** Construction software comparison sites, local AGC chapter marketing, contractor associations.

**Beachhead fit:** LOW-MEDIUM. Too dominated by Procore. Better to win the PM/owner's rep segment first and approach GCs from there.

---

## Primary ICP Definition

**Primary ICP (go-to-market focus):**

| Attribute | Value |
|-----------|-------|
| Company type | Professional services firm OR solo operator |
| Team size | 1–20 people |
| Revenue | $200K–$10M |
| Industry | Consulting, architecture, engineering, early-stage startup |
| Core activity | Shares proprietary documents with external parties as a primary business function |
| Frequency | 5–50 documents shared per month externally |
| Tech sophistication | Moderate — uses SaaS tools, no dedicated IT, makes their own software decisions |
| Switch trigger | One incident of unauthorized document forwarding OR active need for "read confirmation" |
| Current solution | Email + PDF, Google Drive, or DocSend |
| Budget | $29–$199/month, paid personally or as office overhead |

**Secondary ICP (second-wave):**

Sales AEs at SMB companies (5–50 reps) without a mandated sales enablement tool. Adoption path: individual AE trial → manager adoption → team plan.

---

## Anti-ICP (Do Not Target)

| Profile | Why |
|---------|-----|
| Enterprise IT-managed document environments | Need DLP, CASB, on-prem options — out of scope |
| Full Procore shops | Switching cost too high, Procore handles the use case adequately |
| Organizations needing e-signature | PandaDoc/DocuSign serve this; SecureDoc doesn't |
| Users who share documents under 5x/month externally | Subscription cost doesn't justify value |
| Teams requiring CAD-grade markup (Bluebeam users) | SecureDoc's annotation is lightweight, not a redline tool |

---

*Generated: Sprint 5.0 — Product Positioning & GTM. No implementation.*
