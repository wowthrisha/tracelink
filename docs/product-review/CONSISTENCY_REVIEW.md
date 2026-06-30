# SecureDoc Consistency Review
**Date:** 2026-06-30  
**Reviewer Persona:** Staff Frontend Engineer + Technical Writer  
**Scope:** Cross-screen consistency of patterns, naming, interaction models, and copy

---

## 1. Destructive Action Confirmation Patterns

This is the most severe consistency failure in the product.

| Screen | Action | Confirmation Pattern |
|--------|--------|---------------------|
| Upload | Delete document | Modal with warning copy ✓ |
| Upload | Delete group | **No confirmation** ✗ |
| Access | Revoke all links | Modal with excellent warning copy ✓ |
| Access | Revoke single link | **No confirmation** ✗ |
| Access | Delete revoked link | `window.confirm()` ✗ |
| API Keys | Revoke key | **No confirmation** ✗ |
| API Keys | Delete key | **No confirmation** ✗ |
| Webhooks | Delete webhook | **No confirmation** ✗ |
| Orgs | Delete org | **No confirmation** ✗ |

**Verdict:** 5 different patterns for destructive confirmation. The product has no consistent rule. Every team member who implemented a deletion did something different.

**Standard to adopt:** All irreversible destructive actions require a `<Modal>` component with:
- Action name in title (e.g., "Delete API Key")
- Warning paragraph describing what will be lost
- Cancel + Confirm buttons, with Confirm in danger color

---

## 2. Loading State Patterns

| Screen | Loading Pattern |
|--------|---------------|
| Upload (document list) | No initial loading indicator — table appears empty |
| Access (links) | `"Loading links…"` plain text in div |
| API Keys | `"Loading…"` plain text centered |
| Webhooks | `"Loading…"` plain text centered |
| Audit Log | `"Loading…"` plain text centered |
| Analytics | `setAnalyticsLoading(true)` but no explicit loading shown in layout |
| Storage | Full-screen `"Loading…"` return before render |
| Billing | `"Loading billing status…"` plain text |
| Notifications | `"Loading…"` plain text centered |

**Pattern:** Loading states are text strings in centered divs. This is functional but inconsistent with the app's card-based design. A skeleton loader or spinner component would be more professional.

**Minor inconsistency:** StorageScreen returns a full-screen loading fallback outside the layout structure. All other screens show loading inline within the Header + content structure.

---

## 3. Empty State Patterns

| Screen/Context | Empty State Text | Has Next-Step Guidance? |
|---------------|----------------|----------------------|
| Upload — no docs | "No documents yet — upload your first PDF above" | Weak (points to "above") |
| Upload — search no results | "No documents match your search" | No |
| API Keys — no keys | "No API keys yet. Create one to enable programmatic access." | No CTA button |
| Webhooks — no webhooks | "No webhooks registered yet." | No |
| Webhooks — no deliveries | "No deliveries yet. Events will appear here when fired." | N/A |
| Audit Log — no events | "No audit events yet." | No |
| Notifications — no events | "No activity yet. Activity will appear here as your documents are accessed." | No |
| Orgs — no orgs | "No organizations yet." | No CTA, period. |
| Orgs — no members | "No members in this organization." | No |
| Access — no links | "No share links yet — create one in the Create Link tab." | Directional guidance ✓ |
| Analytics — no groups | "No groups created yet / Create groups in the Documents screen to organise your files" | Directional ✓ |

**Verdict:** Two-tier quality. Some empty states guide the user to the next action; most don't. "No organizations yet." with a period and no follow-up is the worst offender.

---

## 4. Date/Time Formatting

| Screen | Format Used |
|--------|------------|
| API Keys — Created | `fmtDate`: "Jun 15, 2026" |
| API Keys — Last used | `fmtRelative`: "2h ago", "Never" |
| Webhooks — Created | `fmtDate`: "Jun 15, 2026" |
| Audit Log — Time | `fmtTime`: "Jun 15, 2:30:45 PM" (with seconds) |
| Notifications — Time | `fmtTime` (relative): "2h ago", then date for older |
| Analytics — Export filename | No date stamp |
| Access — Link expiry | ISO date `.slice(0, 10)` → "2026-06-15" (ISO format, not localized) |
| Access — Link created | Same — ISO slice |
| Storage — Expires | `new Date(doc.expires_at).toLocaleDateString()` → localized |

**Pattern inconsistency:**
- Access screen uses raw ISO `.slice(0, 10)` ("2026-06-15")
- Storage screen uses `toLocaleDateString()` ("6/15/2026" or "15/06/2026" depending on locale)
- API Keys and Webhooks use a custom `fmtDate` function → "Jun 15, 2026"

Three different date formats for dates in the same product. The ISO format in Access link cards looks out of place vs. the `fmtDate` format in API Keys.

**Recommended standard:** Use `toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })` everywhere (i.e., the `fmtDate` function), and apply it consistently.

---

## 5. Button Hierarchy and Labels

### Create Actions

| Screen | Button Label |
|--------|-------------|
| Upload | Upload button is drag-zone not a button |
| Access | "Create Share Link" |
| Access | "⟳ New Share Link" (secondary, zero-restriction) |
| API Keys | "+ New API Key" |
| Webhooks | "+ Register Webhook" |
| Orgs | "+ New Organization" |

Inconsistency: "New", "Create", and "Register" are all used for the same semantic concept (add a new item). GitHub and Stripe use "New" consistently. The app should pick one: "New API Key", "New Webhook", "New Organization", "New Share Link".

### Destructive Actions

| Screen | Button Label | Style |
|--------|-------------|-------|
| Access | "Revoke" (single link) | `variant="outline-danger"` |
| Access | "✕ Revoke All Access" | `variant="outline-danger"` |
| Access | "Delete" (revoked link) | `variant="outline-danger"` |
| API Keys | "Revoke" | `variant="ghost"` with `color: C.warning` |
| API Keys | "Delete" | `variant="ghost"` with `color: C.error` |
| Webhooks | "Delete" | `variant="ghost"` with `color: C.error` |

The "Revoke" button in API Keys is styled with `C.warning` (yellow), but in Access it's `outline-danger` (red). Revoke should be consistently warning (yellow) to distinguish from Delete (red).

---

## 6. Terminology Consistency

| Concept | Used As |
|---------|--------|
| "Share Link" / "Share link" | Access screen, Upload QuickShare |
| "link" | API responses, Access screen tabs |
| "Share URL" | Link summary cards |
| "Webhook" | WebhooksScreen (title) |
| "Endpoint" | "Registered Endpoints" section header |
| "Viewer" | "Viewer Screen", "viewer" role, "Viewer Analytics" |
| "Document" | Upload screen, most references |
| "File" | Upload zone: "Drop your file here" |
| "Org" | OrgsScreen component name, sidebar |
| "Organization" | Screen title, button labels |

**Specific inconsistencies:**
- "File" vs "Document": The upload zone says "Drop your file here" but everything else calls them "documents". Pick one ("document" is correct for this product category).
- "Org" vs "Organization": Component names use "Org" internally, titles use "Organization" — acceptable for code but should be consistent in UI text.
- "Revoke" vs "Invalidate": Revoking a link "invalidates" it. The word "Revoke" is used consistently, which is correct.
- "Allowed Emails" vs "Allowed Domains": Inconsistent capitalization in field labels across Create Link and Edit Link.

---

## 7. Icon Usage

| Icon | Used For |
|------|---------|
| `✕` | Close modal, revoke all (as prefix) |
| `⧉` | Copy to clipboard |
| `↗` | Open in new tab |
| `✎` | Rename/edit |
| `↺` | Refresh, Reopen |
| `↩` | Reply |
| `▲` / `▼` | Expand/collapse sections |
| `✓` | Copied confirmation, resolved state |
| `…` | Loading state (inline button) |
| `+` | Create new (API Keys, Webhooks header buttons) |
| `⟳` | "New Share Link" (rotating arrows) |

**Inconsistency:** The "Create" action uses both `+` (API Keys, Webhooks) and `⟳` (Access screen "New Share Link"). These should be unified: `+` for all primary create actions.

**Inconsistency:** Loading state buttons show `…` (ellipsis) in some screens and "…" as text in others. Minor but visible.

---

## 8. Info Cards / Contextual Help

Several screens have an info card at the top explaining the feature:
- API Keys: ◈ icon + explanation + code example of bearer auth
- Webhooks: ⇌ icon + explanation + HMAC example
- Audit Log: ≡ icon + explanation of immutability
- Notifications: ◎ icon + explanation of polling

**Inconsistency:** Analytics, Storage, Billing, Orgs, and Access do NOT have this info card. New users reaching these screens have no contextual help.

**Recommendation:** Either add info cards to all screens or remove from the ones that have them. The pattern works well and should be standardized.

---

## 9. Error Message Quality

| Pattern | Example | Quality |
|---------|---------|---------|
| Generic fallback | "Failed to load API keys" | Poor — no diagnosis |
| Specific server error | Passes through `d.detail` from FastAPI | Good when server provides detail |
| Validation inline | "Name is required", "Select at least one scope" | Good |
| Empty state on error | Tables just stay empty if error occurs | Poor |

The `_errMsg(e, 'Failed to load X')` utility provides a consistent fallback, but when errors occur (network timeout, 500, etc.), the user sees the fallback copy which is only marginally more informative than "An error occurred."

**Recommendation:** Categorize errors: network errors get "Check your connection and try again", 403 gets "You don't have permission to view this", 500 gets "Something went wrong — our team has been notified."

---

## 10. Copy Voice and Tone

**Overall:** The copy is professional and dense. It reads like developer documentation, which is appropriate for the target audience.

**Inconsistencies:**
- British spelling: "organise" (Analytics empty state for groups) vs. American everywhere else
- "—" vs "N/A" vs "-" for null/empty values — inconsistent across tables
- Some toasts end with punctuation ("Key copied to clipboard") some don't ("Webhook paused")
- "webhook" vs "Webhook" — capitalized in buttons, lowercase in toast copy

---

## Consistency Score Card

| Dimension | Score (out of 10) | Notes |
|-----------|-----------------|-------|
| Destructive action patterns | 2/10 | 5 different patterns across 9 actions |
| Loading states | 5/10 | Functional but not designed |
| Empty states | 4/10 | Variable quality, missing CTAs |
| Date formatting | 4/10 | Three formats in use |
| Button labels (create) | 5/10 | "New" vs "Create" vs "Register" |
| Icon usage | 6/10 | Mostly consistent, `+` vs `⟳` issue |
| Terminology | 6/10 | "File" vs "Document" main issue |
| Error messages | 5/10 | Consistent format, inconsistent quality |
| Copy voice | 7/10 | Professional, minor spelling inconsistency |
| Info cards | 4/10 | Present on 4/13 screens |
| **Overall** | **4.8/10** | |

---

*Consistency review complete — 2026-06-30*
