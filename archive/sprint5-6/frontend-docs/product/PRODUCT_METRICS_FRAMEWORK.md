# Product Metrics Framework — SecureDoc

**Date:** 2026-06-23  
**Sprint:** 5.1 — Customer Validation System  
**Purpose:** Define what to measure, how to interpret it, and what thresholds distinguish product-market fit from failure.  
**Scope:** First 10–100 users. These are not the metrics for a scaled business — they are the metrics for a product finding its footing.

---

## Measurement Philosophy

At this stage, three types of metrics matter:

1. **Activation metrics** — Did the user experience the core value of the product?
2. **Retention metrics** — Did they come back? Do they depend on it?
3. **PMF signals** — Are they telling others? Would they be disappointed if it went away?

Everything else — traffic, signups, social followers, press mentions — is noise until these three are working.

**One rule:** Do not optimize a metric you cannot explain to the user whose behavior created it. If you can't say "we improved this by doing X, which means users are getting more value from Y," the metric is decorative.

---

## The Activation Funnel

### Definition of Activated

A user is **activated** when they have completed the core loop:

> Upload a document → Create a share link → Share that link → Link is viewed → User sees analytics showing who viewed which pages

This is not activation:
- Signing up
- Uploading a document but not creating a link
- Creating a link but never sharing it
- Sharing a link that nobody opened

**The Activation Moment** is specifically: the first time a user sees that someone has viewed their document, and they can see which pages that person spent time on. This is the heatmap moment. Everything before it is setup.

---

## Metric Definitions

### L1 — Signup to First Link (Time-to-Value)

**What it measures:** How long from account creation to the user's first share link being created.

**How to capture:** Track `link.created_at` - `user.created_at` for first link per user.

**Benchmarks:**
| Outcome | Signal |
|---------|--------|
| < 15 minutes | User understood the product immediately. High-intent buyer. |
| 15 min – 2 hours | User explored, understood, got there. Normal. |
| 2 hours – 24 hours | User is interested but encountered friction. Investigate with activation interviews. |
| > 24 hours | User is likely to churn before experiencing value. Trigger a personal outreach. |
| Never | Activation failure. Separate cause: product friction vs. wrong audience vs. wrong timing. |

**Target:** Median time-to-first-link < 30 minutes for beta cohort.

---

### L2 — First Link Viewed Rate

**What it measures:** Of users who created a link, what percentage had that link viewed by at least one person?

**Why it matters:** Creating a link means the user understood the product. Having it viewed means the product is embedded in a real workflow (they actually shared something with a real person). If a user creates links but nobody views them, the product isn't solving a real sharing need — they may be testing, not using.

**How to capture:** Unique users who have at least 1 link with `view_count > 0`.

**Target:** >70% of activated users have at least one viewed link within 7 days of account creation.

**Warning signal:** If <40% of activated users have a viewed link within 7 days, the product may be being used for internal testing rather than real external sharing.

---

### L3 — Analytics Engagement (The Heatmap Moment)

**What it measures:** Of users whose links have been viewed, what percentage navigated to analytics and saw per-page data?

**Why it matters:** The heatmap is the feature that creates the "I can't go back to email" moment. A user who shares a document and never checks the analytics is getting partial value. A user who checks analytics is experiencing the product's core differentiation.

**How to capture:** Track navigation to Analytics → By Document → per-page view (or Viewer → Insights). Any event indicating the user looked at page-level engagement data.

**Target:** >80% of users with a viewed link navigate to analytics within 48 hours of that view.

**If below target:** The analytics aren't being discovered — either navigation is broken or the notification ("your document was viewed") isn't triggering the return visit.

---

### L4 — Week 1 Retention (D7)

**Definition:** User logs in at least once between Day 5 and Day 10 after account creation.

**Why Day 7 specifically:** The first week is when users decide if a tool is worth returning to. If they don't come back in 7 days without a prompt, they almost certainly won't come back at month 1 without significant intervention.

**Target:** D7 retention >60% for beta cohort.

**Breakdown by persona:**
- Founders (fundraising): expect higher D7 retention because the use case is active
- Consultants: may be lower D7 if they shared a document and don't have another deliverable ready for a week
- Architects: may be lower D7 due to slower project cadence

**Note:** D7 retention for a tool people use "a few times a month" will naturally be lower than a daily app. Do not compare to consumer app benchmarks. A consultant may not use SecureDoc every day — but they should log in whenever they have a deliverable to share.

---

### L5 — Month 1 Retention (D30)

**Definition:** User is still an active subscriber 30 days after starting their paid plan.

**Target:** D30 retention >75% for beta cohort.

**Why this matters more than D7 for SecureDoc:** The product is not a daily tool. It's a workflow tool. Some users will have a high-intensity first week (fundraising, delivery of a major report) and then a quieter second and third week. D30 retention is the first clean read on whether the product is embedded in their ongoing work.

**Healthy pattern:** High D7 → Moderate D14 → Stable D30. Flat retention from D14 to D30 is healthy. Sharp drop at D30 indicates the trial was enough and they found no ongoing reason to stay.

**Danger pattern:** High D1 (everyone excited) → Sharp drop by D7 → Near-zero by D30. This means the product had strong appeal at first impression but failed to deliver on it.

---

### L6 — Links Created Per Active User Per Month

**Definition:** Total links created / monthly active users.

**What it signals:** Depth of usage. Are users creating links once (testing) or regularly (embedded in workflow)?

**Benchmark guidance:**
| Rate | Interpretation |
|------|----------------|
| < 1 link/month | Occasional testing. Not embedded. High churn risk. |
| 1–5 links/month | Regular use. Product is part of some workflows. |
| 5–20 links/month | Power user. Product is embedded in their document sharing practice. |
| > 20 links/month | Professional sharing at scale. Strong expansion signal (team plans). |

**Target for beta users:** Median >3 links per month by month 2.

---

### L7 — Feedback / Annotation Engagement Rate

**Definition:** Percentage of users who have at least one viewer annotation on any of their documents.

**Why it matters:** The annotation feedback loop is SecureDoc's primary differentiator from DocSend. If users are sharing documents but no annotations are being left, one of three things is true: (1) their viewers are passive consumers, (2) the can_annotate permission is disabled by default on their links, or (3) viewers don't discover the annotation feature.

**Target:** >30% of active users have received at least one viewer annotation by month 2.

**Action if below target:** Check whether can_annotate is on by default in the link creation form. If it's off by default (which it is per the permissions card defaults), most users will never enable it. This is a product default problem, not a user problem.

---

### L8 — The Sean Ellis PMF Score

**Definition:** "How would you feel if you could no longer use SecureDoc?" measured at day 30.

**Scale:**
- Very disappointed
- Somewhat disappointed
- Not disappointed

**Target:** ≥40% of respondents select "Very disappointed." (This is the Sean Ellis benchmark for early PMF.)

**Context for SecureDoc at this stage:** 40% is the long-term target. With 10 beta users, even 4 "very disappointed" responses is meaningful. The responses matter less than the *reasons* — why are they very disappointed? That tells you what the product actually is to them.

**Interpretation by segment:**

| Segment | Expected VD% without PMF | Target with PMF |
|---------|--------------------------|-----------------|
| Founders (active fundraising) | 10–15% (high churn, situation-dependent) | 40%+ |
| Consultants | 20–30% (moderate habit) | 45%+ |
| Architects | 15–25% (slower workflow) | 35%+ |
| Professional Services | 25–35% (routine use) | 50%+ |

---

### L9 — Referral Rate (NPS Proxy)

**Definition:** Percentage of active users who referred at least one other person to SecureDoc within 30 days (tracked via referral link, promo code, or user self-report in the day-30 survey).

**Why it matters:** Referral rate is the purest PMF signal at this scale. A user who tells someone else about SecureDoc has internalized both the value and the positioning well enough to advocate. At 10 beta users, even 2–3 spontaneous referrals is a strong early signal.

**Target:** ≥20% of beta users refer at least one person within 30 days.

**Note:** Do not measure referrals you actively solicited (e.g., via a referral program). Measure only organic referrals — users who told someone about the product without being asked.

---

### L10 — "Wrong User" Rate

**Definition:** Percentage of signups that were clearly the wrong ICP (disqualified after signup or never activated because of a fundamental model mismatch).

**How to identify wrong users:**
- Never created a link (uploaded a document but stopped there)
- Used the product for internal document sharing only
- Asked "how do I send an email to someone?" in their first session
- Signed up expecting e-signature functionality

**Target:** <20% wrong-user rate from any single acquisition channel. If a channel generates >30% wrong users, it's targeting poorly.

**Action if exceeded:** Review the acquisition channel's messaging. The homepage or ad copy is likely attracting the wrong audience.

---

## Metric Dashboards by Phase

### Phase 1 (First 10 Users) — Manual Tracking

At 10 users, do not build a dashboard. Use a spreadsheet.

Columns: User ID, Persona, Signup Date, First Link Date, First View Date, Analytics Viewed?, D7 Active?, D30 Active?, PMF Score, Churn Reason, Key Quote

Review this weekly. Update after every user interaction (support request, feedback form, interview).

---

### Phase 2 (11–50 Users) — Lightweight Instrumentation

When you have more than 10 users, manual tracking breaks. Add these:

- Event: `link_created` (user_id, timestamp)
- Event: `link_viewed` (link_id, viewer_session_id, timestamp)
- Event: `analytics_opened` (user_id, screen: 'analytics' or 'insights', timestamp)
- Event: `user_returned` (user_id, days_since_signup)
- Event: `link_shared` (how user distributed — clipboard copy vs. direct share)

These events don't require a separate analytics platform. Append them to the existing audit log or events table.

---

### Phase 3 (51–100 Users) — Cohort Analysis

At 50+ users, start analyzing by cohort (signup week) and segment (persona). Ask:

- Is the consultant cohort retaining better or worse than the founder cohort?
- Are users who found the heatmap in week 1 retaining at a higher rate at month 1?
- What's the median time-to-first-link for each persona?

These questions require cohort grouping but not a complex analytics tool. A spreadsheet with pivot tables is sufficient at this stage.

---

## PMF Signals vs. Rejection Signals

### Strong PMF signals (act on these — they tell you what to double down on)

| Signal | What it means |
|--------|--------------|
| User shares SecureDoc with a colleague without being asked | Product value is self-evident |
| User creates a link within minutes of creating an account | Onboarding is working; use case is clear |
| User checks analytics immediately after knowing a link was viewed | The heatmap is the retention feature |
| User upgrades from Free to Solo without a prompt | Self-serve monetization is working |
| User describes a new use case you didn't anticipate | Product has broader application than designed |
| User says "I recommended this to my team" | Expansion signal — Studio/Team plan opportunity |

### Weak signals (investigate, don't act yet)

| Signal | What it means |
|--------|--------------|
| User uploads a document but doesn't create a link | Upload flow may be creating false activation; use case may not match |
| User creates many links but never checks analytics | Analytics not discovered, not valued, or not needed |
| D7 retention high but D30 drops sharply | Initial excitement; not embedded in ongoing workflow |
| User asks about features that don't exist | May be wrong ICP, or may reveal a critical gap |

### Rejection signals (stop and address before scaling)

| Signal | What it means | Response |
|--------|--------------|----------|
| >3 users ask "how do I send an email to someone?" | Link-based model is not understood | Rewrite the onboarding copy to explain the model before signup |
| >3 users describe the product as "confusing" in first 5 minutes | Activation flow is broken | Observe a session live; do not theorize |
| PMF score "Very Disappointed" < 20% at day 30 | Product is not yet a must-have | Stop acquiring new users; do 5 more discovery interviews |
| Churn reason "found another tool" > 50% | You are not winning competitive comparisons | Identify what specific feature caused the switch |
| 0 organic referrals from first 10 users | No one is talking about it | Product works but doesn't inspire advocacy; investigate why |

---

## The One Metric That Matters Most Right Now

Before you have 10 active users, there is one metric more important than all others:

**"Did a user, without hand-holding, complete the full loop: upload → link → share → view → analytics?"**

This is binary. Yes or no. Count how many of your first 10 users did it on their own.

- **7 or more:** You have a functional product with a clear enough UX to activate real users. Now focus on retention.
- **4–6:** The product works for engaged users but friction is preventing unaided completion. Do observation sessions immediately.
- **Fewer than 4:** There is a blocking issue in the activation flow. Stop acquiring new users and fix it first.

This metric cannot be gamed. It cannot be rationalized. Either they did it or they didn't.

---

## Tracking Template (Copy into a Spreadsheet)

| User | Persona | Source | Signup | First Link | First View | Saw Heatmap | D7? | D30? | PMF Score | WTP | Referrals | Key Quote |
|------|---------|--------|--------|-----------|-----------|------------|-----|------|-----------|-----|-----------|-----------|
| U001 | Consultant | Personal | | | | | | | | | | |
| U002 | Architect | LinkedIn | | | | | | | | | | |
| U003 | Founder | YC | | | | | | | | | | |
| ... | | | | | | | | | | | | |

---

*Generated: Sprint 5.1 — Customer Validation System. No implementation.*
