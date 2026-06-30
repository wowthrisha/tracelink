# User Observation Checklist — SecureDoc

**Date:** 2026-06-23  
**Sprint:** 5.1 — Customer Validation System  
**Purpose:** What to watch and record during live screen-share sessions and usability observations.  
**Format:** Used by the interviewer/observer in real time. Check each item as observed. Add notes inline.  
**Session length:** 20–30 minutes of observed product use, preceded by the discovery interview.

---

## Before the Session

- [ ] Confirm the user is sharing their screen (not watching yours)
- [ ] Confirm they have a real document to upload (not a test file) — actual work product
- [ ] Ask them to narrate what they're thinking as they go: *"Just talk through what you're doing and why."*
- [ ] Start recording if they've consented
- [ ] Have this checklist open in a separate window — take notes in real time

---

## Phase 1: Upload Flow

**Watch for:**

- [ ] Did they find the upload button without being directed to it?  
  *(The "↑ Upload PDF" button is in the top-right header. First-time users who don't hover may miss it.)*

- [ ] Did they try to drag and drop before clicking a button?  
  *(Drop zone exists — noting whether they discover it without prompting)*

- [ ] Did they interact with the "Assign to group" or "Delete after" fields before uploading?  
  *(If yes: did they understand what these mean, or did they seem confused/skip them?)*

- [ ] Did they read the "Supported formats" anywhere?  
  *(There's no visible format list on the upload screen — if they have a DOCX, they may be confused)*

- [ ] How long between arriving on the screen and successfully starting an upload?  
  *(>2 minutes = significant friction)*

- [ ] Did they notice the progress bar during upload?

- [ ] After upload completed, did they click "Share Document →" or "Dismiss"?  
  *(Dismiss is a failure state. Note if they hit it accidentally.)*

- [ ] Did they see the "HIGH" risk badge on their document and react to it?  
  *(Note their reaction: confusion, alarm, ignoring, asking what it means)*

- [ ] Did they discover the hover-reveal action buttons on a document row?  
  *(Most users click the row to open the viewer instead. Note the path.)*

**Notes:**

---

## Phase 2: Share / Link Creation Flow

**Watch for:**

- [ ] How did they navigate to the sharing screen?  
  *(Options: clicking "Share Document →" after upload / sidebar "Access Control" / hover "↗ Share" button on doc row)*

- [ ] If they used the sidebar "Access Control" — did they hesitate before clicking it?  
  *(Hesitation = label mismatch)*

- [ ] If they clicked the document row first — did they get confused opening the viewer?  
  *(Row click → Viewer is a wrong path for users who want to share)*

- [ ] On the Create Link tab: did they fill in any policy fields, or go straight to clicking the button?  
  *(Blank form click = users want a "share immediately" path, not a policy configuration form)*

- [ ] Which fields did they interact with first?  
  *(Expiry? Password? Allowed emails? Note the order — this reveals their mental priority)*

- [ ] Did they read the "Allowed Domains" hint (@acme.io) and seem to understand it?  
  *(Confusion here is a recurring issue)*

- [ ] Did they find the "Create New Link" button without scrolling?  
  *(The button is at the bottom-right of the permissions card — below 7 toggles)*

- [ ] Were they confused by the two buttons: "Create New Link" and "⟳ New Link"?  
  *(Users often don't know the difference)*

- [ ] After clicking Create New Link, did they understand they were now on the Links tab?  
  *(The view switches automatically — some users miss that)*

- [ ] Did they successfully copy the link URL?

- [ ] Did they try to open the link themselves (in a new tab) to see what their recipient would see?  
  *(Positive signal — they're thinking about the recipient experience)*

- [ ] Did they see the embed code block and react to it?  
  *(Confusion, ignoring, or "what is this?" are all signals)*

**Notes:**

---

## Phase 3: QuickShare Flow

*Only observe this if they discover QuickShare on their own or if you prompt them to hover over a document row.*

- [ ] Did they discover the hover-reveal action buttons without prompting?  
  *(Hover-reveal discoverability is a known gap)*

- [ ] Did they click "↗ Share" (QuickShare) or "Access" (full Access Control)?

- [ ] In the QuickShare modal: did they read the "watermark on, download off" line?  
  *(Most users skip this — it's the critical DRM disclosure)*

- [ ] Did they copy the link immediately, or did they pause and consider configuring more?

- [ ] Did they see "Configure in Access Control →" at the bottom? Did they click it?

- [ ] Did they close the modal with "Done" after copying, or use the X button?  
  *(If they hit X before copying, the URL is lost — note this)*

**Notes:**

---

## Phase 4: Viewer Experience

*Ask them to open the shared link in a new tab (or in incognito to simulate a recipient experience).*

- [ ] Did they understand what the "← Docs" button does? *(Takes them back to upload dashboard)*

- [ ] Did they explore the viewer toolbar without prompting?  
  *(Note: which buttons did they try? Which did they ignore?)*

- [ ] Did they attempt to zoom, navigate pages, or use search?

- [ ] Did they try to right-click on the document?  
  *(Right-click is disabled by default — their reaction to this tells you how they thought about DRM)*

- [ ] Did they find the per-page magnifier or laser pointer?  
  *(These are toolbar features — not discoverable without hovering)*

- [ ] If they tried to download and it was disabled — how did they react?

- [ ] Did they leave an annotation or comment on the document?  
  *(Test only if can_annotate is enabled on the link — note whether they discovered it)*

**Notes:**

---

## Phase 5: Analytics and Feedback

*After they've created a link and (ideally) had someone view it, walk them through the analytics screens.*

- [ ] Did they navigate to Analytics from the sidebar without prompting?  
  *(Or did you have to point them to it?)*

- [ ] In the Analytics screen, did they understand what "Total Views" means vs. "Active Links"?

- [ ] Did they find the "By Document" tab and click it?

- [ ] Did they try to click a document row in the Analytics table?  
  *(Clicking does nothing — note their reaction when it doesn't respond)*

- [ ] In Access Control → View History — did they understand what the log shows?

- [ ] In Access Control → Feedback — if a viewer left an annotation, did they see it?

- [ ] Did they try to reply to feedback?

- [ ] Did they understand the "Resolve" button on a feedback item?

- [ ] After seeing analytics, did they say anything that suggests they would change their behavior based on this data?  
  *(e.g., "Oh, they spent 3 minutes on page 8 — I should ask them about that")*

**Notes:**

---

## Behavioral Signals to Watch At All Times

### Signals of Engagement (good)

- [ ] Leans forward, increases pace of interaction
- [ ] Says "oh, interesting" or "I didn't expect that"
- [ ] Tries features you didn't mention
- [ ] Asks "can it do X?" (signals a use case worth exploring)
- [ ] Opens the link in a new tab to test it themselves
- [ ] Asks about team features or sharing access with a colleague
- [ ] Verbalizes a specific past incident they wish this product had helped with

### Signals of Confusion (critical to capture)

- [ ] Long pause on a screen without interaction (>10 seconds with no action)
- [ ] Clicks the wrong thing more than once (note what they clicked and what they expected)
- [ ] Reads a label silently but doesn't click *(label not matching their mental model)*
- [ ] Says "I don't know what this means" — note the exact element
- [ ] Closes a modal or navigates away before completing a flow
- [ ] Asks "where do I...?" — note what they were looking for
- [ ] Re-reads the same label multiple times

### Signals of Rejection (record verbatim)

- [ ] "I thought this would let me send an email to someone"  
  *(Model mismatch — link-based sharing not understood)*
- [ ] "This feels like an IT tool, not something I'd use"  
  *(Access Control labeling issue)*
- [ ] "This is a lot of setup for just sharing a PDF"  
  *(Policy form complexity felt unnecessary)*
- [ ] "I already have Google Drive for this"  
  *(Hasn't experienced the differentiation yet — note what they haven't seen)*
- [ ] "How is this different from DocSend?"  
  *(Positioning gap — note what you showed them vs. what created the question)*

---

## Post-Session Scoring (Fill in within 10 minutes of the session)

| Observation area | No problem | Minor friction | Major friction | Blocker |
|-----------------|------------|----------------|----------------|---------|
| Found upload button | | | | |
| Completed share flow without help | | | | |
| Understood the links tab | | | | |
| Discovered hover actions | | | | |
| Opened their own link to test | | | | |
| Read analytics without confusion | | | | |
| Understood Feedback tab | | | | |

**The moment in the session where the user's engagement peaked:**

**The moment they seemed most confused or lost:**

**What they said that surprised me most:**

**Do I think this person will still be using SecureDoc in 30 days? Why?**

---

## Persona-Specific Signals

### Architect
- Watch for: Do they try to zoom into drawing details?
- Watch for: Do they look for a "markup" or "comment" tool (expecting Bluebeam-style behavior)?
- Watch for: Do they try to navigate pages quickly (flipping through a drawing set)?
- Key signal: If they say "I'd use this to send to clients, not to contractors" — note that distinction

### Consultant
- Watch for: Do they try to see who viewed the document before creating the link (wrong order)?
- Watch for: Do they navigate to Analytics immediately after creating a link, even before sharing?
- Watch for: Do they look for a "client name" field anywhere (expecting person-based tracking)?
- Key signal: If they try to navigate to "View History" without prompting — they understand the product

### Professional Services Firm
- Watch for: Do they ask about team permissions or sharing admin access?
- Watch for: Do they mention "our standard is..." — signals existing document process
- Watch for: Do they ask how to restrict which teammates can see which documents?
- Key signal: If they say "I'd want to add my assistant to this" — upgrade signal

### Startup Founder
- Watch for: Do they go to the Analytics tab first thing after uploading?
- Watch for: Do they compare everything to DocSend ("DocSend does it differently...")
- Watch for: Do they care about the investor seeing the document as a mobile-optimized experience?
- Key signal: If they say "which slide did they spend the most time on?" — they'll be a power user once they find the heatmap

---

*Generated: Sprint 5.1 — Customer Validation System. No implementation.*
