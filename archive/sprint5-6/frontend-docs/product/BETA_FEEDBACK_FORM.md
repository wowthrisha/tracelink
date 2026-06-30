# Beta Feedback Form — SecureDoc

**Date:** 2026-06-23  
**Sprint:** 5.1 — Customer Validation System  
**Purpose:** Lightweight, well-timed feedback collection across the user lifecycle.  
**Principle:** Short enough to complete in under 2 minutes. Timed to moments of peak engagement or decision. Never automated away — every response gets a human read.

---

## Form 1: Day 1 Onboarding Check-In

**Triggered:** 24 hours after account creation.  
**Delivery:** Email (plain text, from founder's email — not a marketing domain). Subject: "How did your first day with SecureDoc go?"  
**Length:** 3 questions, 90 seconds to complete.  
**Response rate target:** >40%

---

**Email body:**

> Hi [First name],
>
> You signed up for SecureDoc yesterday. I'm [founder name], and I built this.
>
> One question before anything else: did you manage to create a share link and see someone view it?
>
> Yes / Not yet / Had a problem
>
> If you clicked "Not yet" or "Had a problem" — reply to this email and I'll help you get set up. Literally, I'll do it with you on a call if that's useful.
>
> Two more questions while I have you:
>
> **What made you sign up?** (One sentence is fine.)
>
> **What do you most want to learn from the first document you share?**
>
> That's it. Reply here — I read every one.
>
> — [Founder name]

---

**What you're learning:**

| Question | Signal when answered |
|----------|---------------------|
| Did you create a link? | Activation rate. Non-activation in 24h predicts churn. |
| What made you sign up? | Acquisition channel accuracy; which pain point triggered signup |
| What do you want to learn? | Validates or challenges your assumed primary use case per persona |

**Action triggers:**
- "Not yet" or "Had a problem" → Same-day personal reply offering setup help
- Mentions a competitor by name → Flag for positioning research
- Mentions a use case you didn't expect → Add to discovery notes

---

## Form 2: Week 1 Product Check-In

**Triggered:** 7 days after account creation.  
**Delivery:** Email, from founder. Subject: "Quick check-in — what have you learned so far?"  
**Length:** 5 questions, under 2 minutes.  
**Response rate target:** >35%

---

**Email body:**

> Hi [First name],
>
> A week in. Three quick questions:
>
> **1. Have you shared a document with an external person using SecureDoc?**
> [ ] Yes — it worked well
> [ ] Yes — but I ran into friction
> [ ] Not yet
>
> **2. The most useful thing about SecureDoc so far is:**
> (free text, 1–2 sentences)
>
> **3. The thing that confused me most was:**
> (free text, 1–2 sentences)
>
> **4. How did your recipient experience the shared link?**
> [ ] They opened it without issues
> [ ] They had a question or problem
> [ ] I don't know yet / haven't shared with anyone
> [ ] They never opened it
>
> **5. On a scale of 1–5, how likely are you to keep using SecureDoc after the trial?**
> 1 (will cancel) — 2 — 3 — 4 — 5 (definitely keeping it)
>
> If you rated 1, 2, or 3 — I'd really like to understand why. Reply here or book 15 minutes: [calendar link]
>
> — [Founder name]

---

**What you're learning:**

| Question | Signal |
|----------|--------|
| Have you shared externally? | Whether they completed the core workflow |
| Most useful thing | What's actually landing vs. what you assumed would land |
| Most confusing thing | Highest-friction points by persona — compare across 10 responses |
| Recipient experience | Whether the viewer side of the product is invisible or jarring |
| Likelihood to keep using (1–5) | Leading indicator of month-1 retention. Anyone scoring ≤3 should get a call. |

**Action triggers:**
- Score of 1–2 → Call within 24 hours. Do not send automated follow-up. Human only.
- "Confused by" mentions the same thing 3+ times across users → Priority UX fix
- "Most useful" mentions something unexpected → Investigate if it's a feature you're underselling

---

## Form 3: Day 30 Retention Survey

**Triggered:** 30 days after account creation, or 3 days before trial ends (whichever comes first).  
**Delivery:** Email. Subject: "One honest question about SecureDoc."  
**Length:** 4 questions, 2 minutes.  
**Response rate target:** >30%

---

**Email body:**

> Hi [First name],
>
> You've been using SecureDoc for a month. I have one honest question:
>
> **"How would you feel if SecureDoc went away tomorrow?"**
>
> [ ] Very disappointed — I depend on it now
> [ ] Somewhat disappointed — I'd miss it but could find something else
> [ ] Not disappointed — I haven't really used it
> [ ] Not disappointed — it didn't solve my problem
>
> This question matters more than any other I could ask. It's the one question that tells me whether this product actually fits the way you work.
>
> Three follow-ups:
>
> **What type of documents have you been sharing with SecureDoc?**
>
> **Has the product done anything that surprised you — good or bad?**
>
> **What's the single most important thing we could change or add to make this a must-have for you?**
>
> If you selected "Very disappointed" — I'd love to feature your experience. Are you open to a quick conversation?
>
> — [Founder name]

---

**What you're learning:**

| Response | Interpretation |
|----------|----------------|
| "Very disappointed" ≥ 40% | Strong PMF signal (Sean Ellis benchmark). You have a product. |
| "Very disappointed" 25–39% | Partial fit. Find the segment where it's highest and double down. |
| "Very disappointed" < 25% | PMF not yet achieved. Do not scale. Go back to discovery. |
| "Not disappointed — didn't solve my problem" | Wrong segment, wrong positioning, or product gap — interview these users first |

**Secondary signals:**
- "What documents have you shared?" → Validates or refines the ICP
- "Surprised you — good or bad" → Surfaces delight features and unexpected friction
- "Most important change" → First backlog input from real users

---

## Form 4: Exit Survey (Churn)

**Triggered:** When a user cancels, downgrades to Free, or fails to renew.  
**Delivery:** Immediate, automatic email. But the response goes to a human, not a database. Subject: "Before you go — one question."  
**Length:** 2 questions, 30 seconds.  
**Response rate target:** >20% (churn surveys have low response rates — every response is gold)

---

**Email body:**

> Hi [First name],
>
> I saw you cancelled SecureDoc. Before you go — one honest question:
>
> **Why did you stop using it?**
>
> [ ] I don't share enough documents to justify the cost
> [ ] I found another tool that works better
> [ ] It was too confusing to use
> [ ] The features I needed weren't there
> [ ] I was just testing it — wasn't the right time
> [ ] Something else (reply with details)
>
> That's it. No obligation to explain further.
>
> If your situation changes — your account data is still here. You can come back anytime.
>
> — [Founder name]

---

**What you're learning from churn:**

| Reason | Action |
|--------|--------|
| "Don't share enough documents" | Wrong segment. Improve qualification. Not a product problem. |
| "Found another tool" | Ask which one. Identify the feature gap that caused the switch. |
| "Too confusing" | Activation failure. Note which persona said this most. Triggers UX priority. |
| "Features weren't there" | Ask what feature. This is a roadmap signal. |
| "Just testing" | Determine if they were ever the real ICP. |

**Rule:** Anyone who says "found another tool" or "features weren't there" gets a personal reply asking for 10 minutes to understand what they were looking for. These are the most valuable conversations you will have.

---

## Form 5: Feature-Specific Pulse (Ad Hoc)

**When to send:** After any user has used a specific feature at least once.  
**Examples:**
- User saw their first per-page heatmap → send the heatmap pulse
- User received their first viewer annotation → send the feedback pulse
- User created their 5th link → send the links pulse

**Format:** One-question, inline in product (tooltip or notification) OR short email.

### Heatmap Pulse

> "You just saw your first page heatmap. What did you learn that you didn't already know?"
> (Free text, reply directly)

### Viewer Annotation Pulse

> "A viewer just left a note on your document. Was this useful, or was it unexpected?
> [ ] Useful — I would have missed this otherwise
> [ ] Interesting — I'm not sure what to do with it
> [ ] Unexpected — I didn't know this was possible"

### Link Revocation Pulse

> "You just revoked a link. What prompted you to do that?"
> (Free text)

### QuickShare Pulse

> "You used Quick Share. Did the link work as expected for your recipient?"
> (Yes / No / I don't know yet)

---

## Feedback Collection Principles

1. **Plain text emails outperform HTML forms.** A plain email from a real person gets opened, read, and replied to. A designed survey feels like marketing and gets ignored.

2. **Always give a reply path.** Every feedback email should have "reply to this email" as an option. Some users write paragraphs. Those are the most valuable responses.

3. **Send from the founder's email, not a no-reply domain.** This changes the response rate meaningfully.

4. **Never send more than one feedback email in 7 days.** Respect the user's attention.

5. **Follow up on every 1–2 score within 24 hours.** These are not complaints — they are product research.

6. **Keep a running doc of verbatim quotes.** The best PMF evidence is a quote from a customer saying "I can't imagine going back to email." Don't paraphrase it. Capture it exactly.

---

*Generated: Sprint 5.1 — Customer Validation System. No implementation.*
