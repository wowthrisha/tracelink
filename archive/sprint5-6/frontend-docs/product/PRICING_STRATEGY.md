# Pricing Strategy — SecureDoc

**Date:** 2026-06-23  
**Sprint:** 5.0 — Product Positioning & GTM

---

## Pricing Philosophy

SecureDoc should be **priced as a professional tool, not a consumer SaaS.**

The product solves a real, measurable business problem — unauthorized document distribution and the complete absence of viewing intelligence. The buyer is a professional who will expense this. The value is not entertainment or convenience; it is control over proprietary work product and intelligence about client engagement.

Three principles:
1. **Don't compete on price with Google Drive.** Free tools are not our competition. Anyone comparing SecureDoc to a free product is not yet our customer.
2. **Price below DocSend Business for equivalent features** — but only slightly. Being 30–40% cheaper positions us as better value, not cheap.
3. **Make the upgrade path obvious:** Solo plan is for one person. The jump to Studio should feel necessary, not optional, when a team forms.

---

## Market Reference Points

| Product | Price | What you get |
|---------|-------|-------------|
| Google Drive (view-only) | Free | No analytics, no DRM, no expiry |
| DocSend Starter | $15/mo | Basic tracking, 1 user, limited sharing |
| DocSend Business | $65/user/mo | Full analytics, CRM, unlimited sharing |
| Digify Small Business | $79/mo | DRM, watermarks, basic analytics |
| Digify Professional | $149/mo | More users, more advanced features |
| Egnyte Business | $20/user/mo | Enterprise governance, IT-required |

**SecureDoc target:** $39/mo Solo, $99/mo Studio, $249/mo Team — priced to beat DocSend Business feature-for-feature while adding what DocSend lacks.

---

## Recommended Pricing Tiers

### Free — Always Free

**Purpose:** Acquisition, not revenue. Get the product in front of users who don't yet know if it's worth paying for.

| What's included | Limit |
|-----------------|-------|
| Documents | 5 total |
| Active share links | 3 at a time |
| Link features | Expiry and password only |
| Analytics | View count only (no per-page heatmap) |
| Viewer annotations | ✗ |
| DRM controls (download/copy/print/watermark) | ✗ (watermark always on) |
| API / webhooks | ✗ |
| Document groups | ✗ |
| Support | Community only |

**Why these limits:**
- 5 documents is enough to experience the core value (upload, share, track)
- No per-page analytics on free: the heatmap is the feature that generates the "aha" moment and should be behind a paywall
- No DRM controls on free: the consultant who needs to disable download is a paying customer

---

### Solo — $39/month (billed monthly) · $31/month (billed annually)

**Target:** Independent consultants, solo architects/engineers, founders, individual AEs.

| What's included | Limit |
|-----------------|-------|
| Documents | Unlimited |
| Active share links | Unlimited |
| Link features | All: expiry, password, email restriction, domain restriction, IP allowlist, max views, max concurrent sessions |
| Analytics | Full: per-page heatmap, session time, completion rate, per-link breakdown |
| Viewer annotations | ✓ (comments, sticky notes, highlights) |
| Owner feedback reply | ✓ |
| Feedback resolve/reopen | ✓ |
| DRM controls | All: download, print, copy, right-click, watermark |
| Document groups | ✓ (up to 10 groups) |
| Storage | 10 GB |
| Users | 1 |
| API / webhooks | ✗ |
| Audit log | 30-day retention |
| Support | Email, 48h response |

**Annual pricing note:** $31/mo billed annually = $372/year. Comparable to two DocSend months at Business tier.

**Upgrade trigger from Free → Solo:** "I need to disable download" or "I want to see which pages they spent time on."

---

### Studio — $99/month (billed monthly) · $79/month (billed annually)

**Target:** Small studios, partnership practices, 2–5 person consulting firms, founding sales teams.

| What's included | Limit |
|-----------------|-------|
| Everything in Solo | — |
| Users | 3 seats |
| Additional seats | $25/seat/month |
| Document groups | Unlimited |
| Storage | 50 GB |
| API Keys | ✓ |
| Webhooks | ✓ |
| Audit log | 90-day retention |
| CSV export (analytics, feedback) | ✓ |
| Document embed (iframe) | ✓ |
| Organizations (team workspace) | ✓ |
| Support | Email, 24h response |

**Why the Studio plan exists:**
A single solo operator who brings a partner into their practice needs to share document management. The jump from $39 (1 seat) to $99 (3 seats) is reasonable. The API and webhooks unlock integration for firms with dev resources.

**Upgrade trigger from Solo → Studio:** "I need my assistant/partner to have access" or "I want to connect SecureDoc to our CRM via webhook."

---

### Team — $249/month (billed monthly) · $199/month (billed annually)

**Target:** Architecture firms (5–15 people), engineering consultancies, 10-person sales teams, growing startups managing multiple documents with external parties.

| What's included | Limit |
|-----------------|-------|
| Everything in Studio | — |
| Users | 10 seats |
| Additional seats | $20/seat/month |
| Storage | 200 GB |
| Audit log | 1-year retention |
| Priority support | 4-hour response, email + chat |
| Dedicated onboarding | 1-hour setup call |
| Admin controls | User role management, document visibility controls |
| Custom link domains | 1 custom subdomain (e.g., docs.yourfirm.com) |

**Why the Team plan exists:**
At 5–10 people sharing documents with clients, the lack of admin controls creates chaos. The Team plan adds org-level visibility and a custom subdomain (white-labeling) — critical for firms that want to present the viewer as their own.

**Upgrade trigger from Studio → Team:** "We need custom branding on our links" or "we need admin controls" or "we're over 3 people."

---

### Enterprise — Custom pricing, starting $500/month

**Target:** Architecture/engineering firms 20–100 people, real estate developers, enterprise sales teams.

| What's included |
|-----------------|
| Everything in Team |
| Unlimited seats |
| Unlimited storage |
| SSO (SAML) |
| Custom domain + branding |
| SLA (99.9% uptime guarantee) |
| Dedicated success manager |
| Custom data retention policies |
| Invoice billing (no credit card) |

**When to offer Enterprise:** Any inbound with >10 seats, any organization requiring SSO, any regulated industry requiring data residency guarantees.

---

## Annual Discount

20% off on all annual plans. This is standard SaaS positioning — reward commitment without devaluing monthly pricing.

| Plan | Monthly | Annual (per month) | Annual savings |
|------|---------|-------------------|----------------|
| Solo | $39 | $31 | $96/year |
| Studio | $99 | $79 | $240/year |
| Team | $249 | $199 | $600/year |

---

## Pricing Page Positioning

The pricing page should lead with the value metric, not the price.

**Recommended layout:**
1. Hero: "Stop sending documents into silence." with a 3-line summary of what you get
2. Three plan cards (Solo, Studio, Team) with a monthly/annual toggle
3. Feature comparison table beneath (fold)
4. FAQ below the fold: "What counts as a document?", "Can I change plans?", "What happens when I exceed storage?", "Do my viewers need an account?"
5. No hidden per-document fees. No per-link fees. Unlimited is unlimited.

**Critical copy on pricing page:**
- "Viewers never need an account. They click, they read."
- "Cancel anytime. No lock-in."
- "All plans include full DRM, expiring links, and page analytics."

---

## Pricing Risks and Decisions

**Risk 1: Free plan cannibalizes paid**
Mitigation: The free plan caps are designed to be useful for personal use but insufficient for professional use. 5 documents is not enough for a consultant. The lack of per-page analytics is the key paywall — the most compelling feature is behind it.

**Risk 2: Solo is too cheap**
Consideration: $39 is below DocSend Business ($65). The argument for keeping it here: acquisition. The argument for raising it: signal quality (price = quality perception). **Recommendation: launch at $39 and raise to $49 after the first 200 customers. Do not discount aggressively in year 1.**

**Risk 3: Sales teams churn without CRM integration**
Mitigation: Be honest about this on the pricing page. "Works great for document sharing and tracking. For CRM-integrated proposals, consider our webhooks (Studio and above) to build your own connection." Do not charge teams for a CRM integration that doesn't exist.

**Risk 4: Architecture firms want custom subdomain on Solo**
Decision: Custom subdomain is a Team feature. Architecture firms who want white-labeling on their link URLs will need to upgrade. This is intentional — branding is a team/firm concern, not a solo operator concern.

---

## Freemium Conversion Mechanics

**The upgrade moment for Free → Solo:**
- User tries to share their 6th document: "You've reached the 5-document limit on the Free plan. Upgrade to Solo for unlimited documents."
- User clicks "per-page heatmap" in Analytics: "Page-level analytics are available on the Solo plan and above."
- User tries to disable download: "DRM controls are available on the Solo plan and above."

**The upgrade moment for Solo → Studio:**
- User tries to invite a team member: "Solo plans are single-user. Upgrade to Studio for 3 seats."
- User tries to access API keys: "API access is available on Studio and above."

These upgrade prompts should be immediate, unambiguous, and non-blocking. The user sees what they're missing; they can keep using what they have.

---

## Billing Notes

- Stripe for payment processing (already integrated per `billing.py` router)
- Prorated upgrades: if a user upgrades mid-cycle, prorate the remainder
- Downgrade behavior: at end of billing period, features gate; documents remain accessible (read-only) but sharing features disable
- Trial: 14-day free trial on Solo (no credit card required). After trial, revert to Free tier automatically — do not charge without explicit user action.

---

*Generated: Sprint 5.0 — Product Positioning & GTM. No implementation.*
