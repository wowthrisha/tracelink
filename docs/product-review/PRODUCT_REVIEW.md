# SecureDoc Product Review
**Date:** 2026-06-30  
**Reviewers:** Principal PM · Senior UX Researcher · Staff Frontend Engineer · Principal Backend Engineer · Enterprise Security Architect · QA Lead · Accessibility Expert · Technical Writer · First-time Customer · Enterprise Admin · SaaS Founder  
**Scope:** All 13 screens, all backend routers, all workflows, all edge cases

---

## Executive Summary

SecureDoc is a technically solid, security-first document sharing platform with a clean, dense UI. The core happy path (upload → create link → share → view analytics) works well and is production-grade. However, the platform has several **product failures** — features that exist in the backend but are completely unexposed in the frontend, plus destructive actions throughout with no confirmation dialogs.

**Overall Assessment:** Production-capable for solo and small-team use. NOT ready for enterprise or team accounts without fixing the organizations workflow. Several medium-risk UX gaps will frustrate power users.

---

## Screen-by-Screen Review

### 1. Login Screen (LoginScreen.jsx)

**What works:**
- Clean, minimal design consistent with the app's dark theme
- Four mode states: login, signup, forgot, reset — all correctly implemented
- Supabase password-reset hash parsing is handled correctly
- Spam folder hint on signup confirmation is a good touch
- Progressive disclosure (forgot password inline vs. separate page)

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| L-01 | Password minimum is 6 characters — industry standard is 8–12 minimum | Medium |
| L-02 | No password strength indicator on signup | Medium |
| L-03 | No social/SSO login (Google, Microsoft, GitHub) | Medium |
| L-04 | No rate-limiting feedback — after N failed attempts, no message | Medium |
| L-05 | Email confirmation state is confusing: user sees "check inbox" but can still type into sign-in form | Low |
| L-06 | No "stay signed in" / "remember me" checkbox | Low |
| L-07 | Reset password flow requires hash in URL — if user opens link in different browser, token is lost | Medium |

**First-time customer perspective:** The login screen is clean and professional. Signing up is straightforward but after clicking "Create Account" the app just shows a success message with no clear next step — "check your spam folder" feels passive and doesn't communicate when the user will be able to start.

---

### 2. Upload Screen (UploadScreen.jsx)

**What works:**
- Drag-and-drop plus click-to-browse upload zone
- Group organization with color coding
- Document table with search and filter
- Delete confirmation modal with good warning copy ✓
- QuickShareModal for fast link creation
- Polling (MAX_POLL_ATTEMPTS=150) with good processing feedback
- Stats bar: Total Documents, Active Shares, Views Today, Blocked Attempts

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| U-01 | Group delete has NO confirmation dialog — fires immediately | Critical |
| U-02 | No bulk selection (bulk delete, bulk move to group) | High |
| U-03 | No sort controls (by name, date, size, views) | High |
| U-04 | No column to show document type (PDF vs DOCX vs TXT) | Medium |
| U-05 | No document size shown in table | Medium |
| U-06 | No way to rename a document after upload | Medium |
| U-07 | Processing failure state shows generic "Failed" with no error detail | Medium |
| U-08 | Free plan limit (10 documents) enforced silently — no counter shown | Medium |
| U-09 | QuickShareModal creates a link with default settings and no confirmation | Low |
| U-10 | No keyboard navigation in the document table | Medium |

---

### 3. Viewer Screen (ViewerScreen.jsx)

**What works:**
- Full PDF viewer with Chrome-style toolbar
- Two-page mode, zoom, rotation, fullscreen
- Laser pointer and magnifier tools
- In-viewer text search with highlights
- TOC sidebar, page thumbnail panel
- Links panel for extracted hyperlinks
- AI Insights modal
- Forensic watermarking
- AccessGate with password entry for protected links
- Comment/annotation system for viewers
- Text document support (txt, md, log)

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| V-01 | Mobile hard-blocked at 768px — no graceful degradation, just a wall | High |
| V-02 | No print warning — DRM "can_print: false" blocks print but there's no message explaining why | High |
| V-03 | No copy warning — right-click disabled silently, copy blocked silently | Medium |
| V-04 | No viewer-facing "you have X pages remaining" or time limit messaging | Medium |
| V-05 | Public token in URL hash (#view/...) is visible in browser history | High |
| V-06 | Session blurred state has no message explaining why (max sessions reached? expired?) | High |
| V-07 | No keyboard shortcuts documentation visible to viewer | Low |
| V-08 | No page jump input validation — entering 0 or > page_count silently fails | Medium |

---

### 4. Access Screen (AccessScreen.jsx)

**What works:**
- Excellent link creation form: password, expiry, max views, max concurrent sessions, IP allowlist, allowed emails/domains
- All 7 permission toggles: download, print, copy, right-click, watermark, annotations, info panel
- Link rename inline ✓
- "Revoke All Access" modal with excellent confirmation copy ✓
- Embed code generation ✓
- Feedback tab with full filter suite (status, reviewer, date, page, role)
- Inline reply-to-feedback from the dashboard
- Annotations tab with type filter and CSV export

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| A-01 | Delete link (revoked) uses `window.confirm()` instead of a proper modal — inconsistent with rest of app | High |
| A-02 | No password strength indicator on link password field | Medium |
| A-03 | No bulk resolve/export for feedback threads | Medium |
| A-04 | Empty feedback state says "viewers need can_annotate permission enabled" — misleading since comments (comment type) are separate from visual annotations | High |
| A-05 | Revoke single link has no confirmation — only Revoke All has one | High |
| A-06 | "⟳ New Share Link" button creates a link with ALL defaults (no password, no expiry, no restrictions) silently | Critical |
| A-07 | No way to duplicate an existing link's settings to create a new link with same policy | Medium |
| A-08 | Expiry field uses browser date picker — timezone is implicit (T23:59:59 hardcoded) with no indication | Medium |
| A-09 | Feedback empty state for annotations tab says "No visual annotations yet" — doesn't explain how viewers enable them | Medium |
| A-10 | No way to send the share link directly from this screen (email, copy button on Create Link tab) | Medium |

---

### 5. Analytics Screen (AnalyticsScreen.jsx)

**What works:**
- Three tabs: Overview, By Document, By Group
- KPI row: 6 metrics with good icons
- Sparkline chart for views over time (7 days)
- Donut chart for access outcomes
- Per-document page heatmap (click to expand)
- Group comparison cards and table
- CSV export on all three tabs
- Risk badge per document and group

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| AN-01 | No date range picker — hardcoded to last 7 days with no way to change | Critical |
| AN-02 | "Risk" score is never explained — LOW/MEDIUM/HIGH with no legend | High |
| AN-03 | "Completion" metric is undefined in UI — what percentage threshold counts? | High |
| AN-04 | "Avg Session" metric is undefined — is this time-on-page or time-in-session? | Medium |
| AN-05 | Documents in analytics table have no link to access that document's Access screen | High |
| AN-06 | No real-time refresh — stale data with no "last updated" timestamp | Medium |
| AN-07 | CSV export filenames are generic (analytics_overview.csv) — no date stamp | Low |
| AN-08 | heatmap truncated to top 20 pages with no load-more | Low |
| AN-09 | Group analytics shows no time dimension — impossible to compare week over week | High |

---

### 6. Organizations Screen (OrgsScreen.jsx)

**PRODUCT FAILURE** — This screen cannot fulfill its core purpose.

**What works:**
- Create organization with name
- List organizations
- Rename organization
- View members (read-only: Member, Role, Joined columns)
- Delete organization

**Critical gaps:**
| # | Issue | Severity |
|---|-------|----------|
| O-01 | **NO invite member flow** — members panel is completely read-only | Critical |
| O-02 | **NO role management** — cannot promote member from viewer → admin | Critical |
| O-03 | **NO remove member action** — cannot remove a member from the UI | Critical |
| O-04 | **Delete organization fires with NO confirmation dialog** | Critical |
| O-05 | Empty organizations state has no CTA — just "No organizations yet." with no explanation | High |
| O-06 | Empty members state has no invite button — just "No members in this organization." | Critical |
| O-07 | Backend add_member API requires a UUID — there is no invite-by-email flow even in the backend | Critical |
| O-08 | Organization description field doesn't exist at all (backend or frontend) | Medium |
| O-09 | Cannot transfer ownership via UI | High |
| O-10 | Domain verification UI (custom_domain, SAML) exists in backend but is completely absent from frontend | High |

**Assessment:** An organization created in this app becomes a dead end. You can create it, see it, rename it, and delete it. You cannot add a single other person to it. This is the definition of a feature that doesn't work.

---

### 7. API Keys Screen (ApiKeysScreen.jsx)

**What works:**
- Create key with name and granular scope selection (7 scopes)
- Full key shown once with copy button ✓
- Table: name, prefix, scopes, last used, created, status
- Relative timestamps for "Last used"
- Revoke (deactivates without deleting)
- Delete

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| K-01 | Revoke has no confirmation modal | High |
| K-02 | Delete has no confirmation modal | High |
| K-03 | Cannot edit key name or scopes after creation — must delete and recreate | High |
| K-04 | Scope descriptions are missing — just code strings, no explanation of what each scope allows | High |
| K-05 | No expiry date for API keys | Medium |
| K-06 | No IP restriction for API keys | Medium |
| K-07 | "Last used" shows "Never" but doesn't update until page refresh | Low |

---

### 8. Webhooks Screen (WebhooksScreen.jsx)

**What works:**
- Register webhook with URL, description, 3 event subscriptions
- HMAC-SHA256 signing secret shown once ✓
- Delivery history: event, status, HTTP code, attempts, timestamp
- Pause/Resume toggle
- Test ping button
- Active/Paused status badge

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| W-01 | Delete webhook has no confirmation modal | High |
| W-02 | Cannot edit URL or events after registration — must delete and recreate | High |
| W-03 | Only 3 events available (document.processed, link.viewed, analytics.completed) — no events for: link.created, link.revoked, org.member_added, auth events | High |
| W-04 | "20 / 20" limit shown but no explanation of why there's a limit | Low |
| W-05 | Delivery history shows max N entries — no total count, no pagination | Medium |
| W-06 | No ability to replay a failed delivery | Medium |
| W-07 | Cannot rotate the signing secret without deleting and recreating the webhook | High |

---

### 9. Audit Log Screen (AuditLogScreen.jsx)

**What works:**
- Immutable event log with pagination (50 per page, load-more)
- Color-coded action types (create=green, delete=red, view=muted, etc.)
- Columns: Time, Action, Resource, Actor, IP/Context

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| AL-01 | No date range filter | Critical |
| AL-02 | No action type filter | Critical |
| AL-03 | No actor/email filter | High |
| AL-04 | No export (CSV or JSON) | High |
| AL-05 | Resource ID truncated to 8 chars — cannot search or copy full ID | High |
| AL-06 | "IP / Context" column is vague — shows IP address OR metadata context OR nothing | Medium |
| AL-07 | No total events shown per filter — only total across entire log | Low |
| AL-08 | No search across audit log | Critical |

---

### 10. Storage Screen (StorageScreen.jsx)

**What works:**
- Total storage, 30-day and 90-day projections
- Per-org storage breakdown with bar chart
- Per-document table with lifecycle state, size, expiry, retention policy
- Inline retention policy dropdown (Never, 30/60/90 days)

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| ST-01 | Org breakdown shows truncated UUID (8 chars) not org name | High |
| ST-02 | No storage quota shown — user doesn't know what their limit is | High |
| ST-03 | No bulk-set retention policy | Medium |
| ST-04 | Retention policy "Never" is the default — not obvious this means "keep forever" | Medium |
| ST-05 | No way to download a document from this screen | Low |
| ST-06 | "Lifecycle state" column shows active/archived/expired/deleted — "archived" state never explained | Medium |

---

### 11. Billing Screen (BillingScreen.jsx)

**What works:**
- Shows current plan (Free vs Pro) with subscription status
- Renewal date display for Pro subscribers
- Feature comparison list
- Upgrade → Stripe checkout redirect
- Manage → Stripe portal
- Billing disabled state handled gracefully with admin message

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| B-01 | Pro plan price is never shown — user must click Upgrade to discover price | High |
| B-02 | No usage meters — user can't see current document count vs. free tier limit (10) | High |
| B-03 | No invoice/payment history | Medium |
| B-04 | Free plan 10-document limit is in feature list but never enforced at upload time with a visible counter | High |
| B-05 | No team/seat pricing visible | Medium |

---

### 12. Notifications Screen (NotificationsScreen.jsx)

**What works:**
- Activity feed with 24 event types mapped to human labels
- 30-second polling
- "New" badge and mark-all-read
- Rich event detail: document title, viewer email, IP, country

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| N-01 | Limited to 50 events — no pagination, no load-more | High |
| N-02 | No event type filter | High |
| N-03 | No document filter (see events for just one document) | High |
| N-04 | "Mark all read" stored in localStorage — clears on new browser/incognito | Medium |
| N-05 | No notification preferences — cannot choose which events trigger in-app alerts | High |
| N-06 | No email notifications at all | High |
| N-07 | Polling uses setInterval with no backoff — active polling even when tab is background | Low |

---

### 13. AppShell (AppShell.jsx)

**What works:**
- Public viewer mode via hash token (#view/...) or query param
- Billing success redirect from Stripe
- Feedback badge on sidebar
- Mobile-block wall for <768px

**Gaps and issues:**
| # | Issue | Severity |
|---|-------|----------|
| SH-01 | No URL routing — refresh always returns to 'upload' screen | Critical |
| SH-02 | No loading state during initial auth check — flash of login screen | High |
| SH-03 | 'feedback' screen renders AccessScreen with defaultTab="feedback" but there's no doc pre-selected — confusing | High |
| SH-04 | Feedback badge count refreshes on activeDoc change but not on return from feedback tab | Medium |
| SH-05 | Public token visible in browser URL and history | High |
| SH-06 | Mobile block at 768px is too aggressive — iPads at 1024px work fine but 769px tablets are blocked | Medium |

---

## Backend Router Review

### orgs.py
- Full CRUD exists: create, list, get, update, delete org ✓
- Full member management: add, list, update_role, remove ✓
- Domain verification via DNS TXT record ✓
- RBAC with owner > admin > viewer roles ✓
- **CRITICAL GAP:** `add_member` accepts only `user_id` (UUID) — no email invite flow. Means even if the frontend were built, admins would need to know the target user's Supabase UUID.

### links.py
- Full link CRUD with all policy fields ✓
- Custom domain support via org verification ✓
- `require_scope("links:write")` properly enforced ✓

### api_keys.py, webhooks.py, analytics.py, audit.py
All backend routers are complete and correctly scoped. Frontend coverage of backend features varies:
- API Keys: Frontend covers ~80% of backend capability
- Webhooks: Frontend covers ~70% of backend capability
- Analytics: Frontend covers ~85% of backend capability
- Audit: Frontend covers ~40% of backend capability (no filters, no export)
- Orgs: Frontend covers ~20% of backend capability (no member management at all)

---

## Risk Summary

| Priority | Count | Examples |
|----------|-------|---------|
| Critical | 8 | Org invite/member management missing, group delete no confirmation, single link revoke no confirmation, "New Share Link" creates unrestricted link silently, no URL routing, audit log no filters/export |
| High | 28 | Analytics no date range, audit no search, delete confirmations missing throughout, scope docs missing, mobile blocked, billing no usage meter |
| Medium | 22 | Password minimums, sort/bulk missing, token in URL, retention labels unclear, notification preferences absent |
| Low | 8 | CSV filenames, badge refresh timing, lazy scroll in notifications |

---

*Review complete — 2026-06-30*
