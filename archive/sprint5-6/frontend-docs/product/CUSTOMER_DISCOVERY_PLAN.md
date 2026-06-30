# Customer Discovery Plan — SecureDoc

**Date:** 2026-06-23  
**Sprint:** 5.1 — Customer Validation System  
**Purpose:** A structured system for recruiting, conducting, synthesizing, and acting on learning from the first 10 beta users.  
**Scope:** First 10 paid or active-trial users only. This is not a 100-user survey. It is 10 deep conversations.

---

## Why 10 Users Before Anything Else

The first 10 users will tell you more than the next 100 if you listen correctly. At this stage:
- Your positioning may be wrong
- Your ICP may be wrong
- Your highest-value feature may not be the one you think it is
- A use case you haven't considered may be where real PMF lives

The goal is not to validate your assumptions. The goal is to stress-test them to destruction and see what survives.

**Rule:** Do not write a single line of new product code until you have completed at least 5 discovery conversations. If the interviews reveal a major model mismatch (e.g., your users expect email invitations, not links), that finding is worth more than any feature you could build in the same time.

---

## Recruiting the First 10

### Profile targets

Aim for this mix across the first 10:

| # | Persona | How to reach |
|---|---------|-------------|
| 2 | Independent consultant (solo) | Personal network, r/consulting |
| 2 | Architecture principal (5–20 person firm) | LinkedIn, personal network, local AIA |
| 2 | Startup founder (active fundraising or recently raised) | YC community, personal network |
| 2 | Professional services firm (consulting, legal, finance) | Founder network, LinkedIn |
| 1 | Sales AE (SMB, 5–50 rep team) | LinkedIn |
| 1 | Engineering consultant (structural/civil/MEP) | LinkedIn, personal network |

**Why this mix:** It covers the top 3 ICP segments plus two secondary segments. After 10 interviews, you should be able to identify which 2–3 profiles show the strongest signal.

### Qualifying questions before scheduling

Before booking the 45-minute interview, send these 3 qualifying questions:

1. "How often do you share documents (PDFs, reports, decks) with people outside your organization?" *(Answer must be at least monthly. Skip anyone who says quarterly or rarely.)*

2. "Do you currently have a tool that lets you track whether someone read a document you sent?" *(If yes — what is it? If DocSend, high-value recruit. If Google Drive, perfect recruit.)*

3. "Have you ever had a situation where a document you shared ended up somewhere it shouldn't have?" *(Yes = red carpet. No = fine, but not ideal.)*

Disqualify:
- Internal file sharing only (no external document sharing)
- Document management (Procore power users, SharePoint IT admins)
- Sending documents once a quarter

---

## Interview Schedule

**Do not bunch all 10 interviews into one week.** Stagger them so you can update your script between rounds based on what you learn.

| Week | Interviews | Goal |
|------|-----------|------|
| Week 1 | 3 (1 consultant, 1 founder, 1 architect) | Validate core problem framing. Are these really the right people? |
| Week 2 | 4 (2 professional services, 1 engineer, 1 sales AE) | Expand to secondary segments. Watch for unexpected use cases. |
| Week 3 | 3 (mix, prioritize highest-signal personas from weeks 1–2) | Go deeper on what's working. Refine your positioning hypothesis. |

**Mandatory gap between rounds:** At least 48 hours. Use this time to update your notes, adjust your script, and share a short summary with your co-founder or team.

---

## The Synthesis System

After each interview, complete these tasks within 24 hours — not later:

### Step 1: Write a 5-sentence summary

Force yourself to answer:
1. What was this person's primary pain in one sentence?
2. What was their reaction to the product (if shown)?
3. What surprised me?
4. What validated my existing assumption?
5. What directly contradicted my existing assumption?

Do not skip the fifth sentence. It is the most important one.

### Step 2: Update the signal tracker

Maintain a simple spreadsheet or doc with one row per participant:

| Name | Persona | Had incident | WTP ($) | Activation? | PMF signal | Key quote |
|------|---------|-------------|---------|-------------|-----------|-----------|
| ... | Consultant | Yes | $50 | Yes (created link) | Strong | "I need to know if they read it before I call." |

### Step 3: Look for patterns after every 3 interviews

After interviews 3, 6, and 10, do a 30-minute synthesis session. Ask:

- **What do the strongest signals have in common?** (persona? pain? use case?)
- **What do the weakest signals have in common?** (persona? different use case?)
- **What word did multiple users use to describe their problem?** (these are your headline copy words)
- **Which feature got the most spontaneous attention?** (not what you showed — what they noticed)
- **Has anyone said "this is exactly what I needed" or equivalent?** If not — why not?

### Step 4: Update the ICP and positioning based on what you learn

After all 10 interviews, rewrite two sentences:

1. "The person who gets the most value from SecureDoc is..."
2. "The moment they realize they need SecureDoc is when..."

If these sentences look significantly different from what you would have written before the interviews — you did the research correctly.

---

## What Each Persona Discovery Looks Like

### Architects — what you're trying to learn

**Core question:** Do architects have a document security problem, or a document review workflow problem?

SecureDoc solves document security (DRM, access controls, expiry). Bluebeam solves document review (markup, redlines, stamps). These are different problems. The risk is that architects sign up for SecureDoc expecting a review tool and leave when they find it's a sharing tool.

**What success looks like in architect discovery:**
- They describe sending drawing sets to clients or building officials and wanting to know if they were opened
- They've had a contractor use their drawings without permission
- They describe wanting to revoke access after a design change
- They do NOT primarily mention "I need to do redlines on this" (that's a Bluebeam problem)

**Red flag in architect discovery:**
- "I need to annotate drawings collaboratively with my structural engineer" — this is a Bluebeam workflow, not SecureDoc
- "We use Procore for all our document management" — hard to displace

### Consultants — what you're trying to learn

**Core question:** Is "did the client read it?" a strong enough daily pain to drive purchase?

Consultants build their follow-up behavior around client engagement signals. If the signal is strong enough — "I wouldn't do a follow-up call without knowing if they read the report first" — then this is a purchasing trigger. If the signal is weak — "I just send it and assume they read it" — then the pain isn't there.

**What success looks like in consultant discovery:**
- "I never know if they read it before our review call"
- "A client shared my competitive analysis with the company we were analyzing"
- "I've had clients reference a report from two years ago — I didn't even know they still had access to it"
- They would use the per-page heatmap to decide what to emphasize in meetings

**Red flag in consultant discovery:**
- "I mostly share reports internally or with partners I trust" — no external sharing, wrong ICP
- "My clients sign NDAs, so I don't worry about it" — not a perceived problem

### Professional Services Firms — what you're trying to learn

**Core question:** Is this a solo problem or a team problem? And who makes the decision?

A 10-person law firm or accounting practice is a different buyer from a solo consultant. The 10-person firm has an operations manager, IT considerations, and team workflow requirements (who can share what). The solo consultant decides alone.

**What success looks like in professional services discovery:**
- They describe a broken document sharing workflow that involves multiple team members
- The decision-maker is in the room (or is the person you're talking to)
- They see SecureDoc as a firm-level system, not a personal tool
- They immediately ask about multi-user access

**Red flag:**
- "We'd need IT to approve this" — not a self-serve buyer, may need enterprise motion
- "We have our own document management system" — too embedded

### Startup Founders — what you're trying to learn

**Core question:** Is SecureDoc a DocSend replacement, or does it serve a different need in the fundraising workflow?

Founders who use DocSend are already educated buyers. They understand the category. The question is whether SecureDoc's additional features (DRM, annotation feedback, IP allowlist) justify switching from a tool they already know.

**What success looks like in founder discovery:**
- They use DocSend and have a specific complaint about it (no DRM, no annotation feedback, expensive for teams)
- They're actively fundraising and would benefit from per-slide analytics right now
- They've had their deck forwarded outside the intended conversation
- They'd use the annotation feature to collect investor questions

**Red flag:**
- "Investors are used to DocSend links" — brand familiarity is a switching barrier
- "I don't worry about who sees my deck — I'd rather it be seen by more people" — wrong mindset for this product

---

## Synthesis Decision Gates

After every 5 interviews, stop and make one of three decisions:

**Decision A: Continue as planned.**  
Signal: 3 of 5 users had the target pain, showed interest in the product, and gave a WTP at or above $29/month.

**Decision B: Pivot segment focus.**  
Signal: One persona (e.g., founders) shows consistently stronger signals than others. Redirect remaining interviews toward that segment. Don't keep interviewing equal numbers of each persona if one is clearly winning.

**Decision C: Stop and rethink.**  
Signal: Fewer than 2 of 5 users showed genuine interest. Multiple users expressed a model mismatch ("I thought this was an email tool"). WTP consistently below $15/month. This is not a failure — this is the entire point of discovery. Go back to the problem framing and reconsider the positioning or segment.

---

## After the 10th Interview: The Learning Review

Schedule a 2-hour internal session (founder + any team members involved in interviews).

Agenda:

**Hour 1: What we heard**
- Read every "Key quote" from the signal tracker out loud
- Identify the 3 phrases that appeared across multiple users
- Identify the 2–3 features that generated the most spontaneous interest

**Hour 2: What we decide**

| Question | Answer |
|----------|--------|
| What is the primary ICP after these 10 interviews? | |
| What is the #1 use case that generated the clearest buying signal? | |
| What assumption did we hold going in that these interviews disproved? | |
| What does the onboarding experience need to change to reflect what we learned? | |
| What is the one sentence we would put on the homepage based on what users said? | |
| Do we have evidence of PMF in any segment? | Yes / No / Partially |

---

## The PMF Threshold for These 10 Users

**You have early PMF evidence if:**
- 4 or more users completed the full workflow (upload → link → share → view analytics) without hand-holding
- 3 or more users said they would be "very disappointed" if SecureDoc went away
- 2 or more users referred another person without being asked
- 1 or more users tried to use a feature that doesn't exist yet (signals they're extending the product in their mind)

**You do not yet have PMF evidence if:**
- Fewer than 3 users completed the core workflow on their own
- The "very disappointed" score across users is below 30%
- Most users needed a guided setup call to get value
- The strongest signal is in a segment you didn't plan for (this is fine — it redirects your focus, not a failure)

---

*Generated: Sprint 5.1 — Customer Validation System. No implementation.*
