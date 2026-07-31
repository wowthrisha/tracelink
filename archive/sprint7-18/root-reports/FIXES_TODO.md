# Fixes To Do — Adversarial UI Review (V13.0 supplemental pass)

**Method**: fresh, adversarial live pass this sprint — Playwright against the deployed instance at desktop (1440px), tablet (834px and the app's own stated minimum of 768px), and mobile (390px) widths, cross-referenced with source code and raw API responses (not just screenshots) wherever a visual anomaly appeared. The brief was to find real mistakes, not confirm things work — several suspected bugs below were investigated to the point of pulling raw network responses and DOM inline styles rather than trusted on sight, and one suspected bug was **ruled out** after deeper inspection rather than reported anyway (see item 5).

Every finding is **Browser-verified + Source-code verified** (both cited) unless stated otherwise. Ranked most to least severe.

---

## 1. Analytics screen: real data is clipped off-screen and unreachable at the app's own supported minimum width

**Severity: Medium-High.** The app enforces `min-width: 768px required` (its own gate, seen on every screen below that width) — but at exactly that width, the Analytics screen's own layout doesn't fit itself. This is a self-inconsistency: the product asserts "768px is enough," then breaks its own layout at 768px.

**Browser-verified + confirmed via DOM measurement** (not just a screenshot glance): at 768px width, the "Completion" KPI card's bounding box has its right edge at **x=844.5px** — 76.5px past the visible 768px viewport. The right sidebar panel ("Groups at a glance" / "Security Activity") is similarly clipped, its title truncated to "GRO.../GLA..." with every value inside (blocked-today count, active-links count, expiring-soon count) fully invisible. Confirmed there is **no horizontal scroll available to recover this content** — `document.body`'s `scrollWidth` equals `viewportWidth` exactly (834 == 834 at tablet width) with `overflow-x: hidden`. This content is not scrollable, not wrapped, not degraded gracefully — it is simply gone.

**Source-code verified, root cause**: `frontend/src/screens/AnalyticsScreen.jsx:339` — the KPI card row uses `gridTemplateColumns: 'repeat(6,1fr)'`, a fixed 6-column grid with no responsive fallback. Line 390's "Document Performance / Groups at a glance" row uses `gridTemplateColumns: '3fr 1fr'`, also fixed. Neither has a media query or `minmax()` floor. This is inconsistent with the same file's own working pattern at line 272 (`repeat(auto-fill, minmax(220px, 1fr))`), which correctly reflows instead of clipping.

**Recommended fix**: change line 339 to `repeat(auto-fit, minmax(130px, 1fr))` (or explicitly wrap to 3+3 at narrow widths) and give the sidebar column in lines 344/390 a `minmax()` floor with the layout stacking to a single column below ~900px, matching line 272's already-correct approach.

## 2. Notifications / Activity Feed: every entry is generic and indistinguishable — the feed cannot answer its own stated purpose

**Severity: Medium.** The screen's own subtitle reads "Recent activity across **your documents** — views, downloads, link accesses..." A live pass showed 50 consecutive events, the overwhelming majority reading only **"Page viewed" / "35m ago"**, repeated identically dozens of times with no document name, no page number, nothing to distinguish one document's activity from another's. A first-time user cannot answer "which of my documents got viewed?" from this screen — it fails the three-second test outright, and arguably the thirty-second test.

**Source-code verified**: `NotificationsScreen.jsx`'s `eventDetail()` (lines 59-66) is designed to show a detail line — it checks `ev.document_title`, `ev.viewer_email`, `ev.ip_address`, `ev.country`. **Browser-verified via the raw API response** (`GET /api/analytics/events?limit=50&offset=0`): actual event objects contain `event_type`, `page_number`, `link_id`, `ip_hash`, `session_id`, `created_at` — **no `document_title` field exists at all**, and the one IP-related field present is named `ip_hash`, not `ip_address`, so `eventDetail()`'s check for it silently never matches. Even `page_number`, which **is** present in every event, is never read or displayed anywhere in the component.

**Recommended fix**: backend should join and include a human-readable document identifier (title or filename) on each event returned by `/api/analytics/events` — it already has `link_id`, one join away from the document. Frontend should also surface `page_number` in the detail line as a quick partial fix even before the backend join lands (e.g., "Page 2 · via link ****").

## 3. Share-link document picker: identical filenames are indistinguishable before clicking

**Severity: Low-Medium.** The document picker used when creating an access-controlled share link (`Access Control` screen) lists documents by filename, page count, and view count only. When two documents share a filename — which happens naturally with repeated drafts ("Contract.pdf" v1 and v2) and is visibly the case in this account today (a dozen-plus documents literally named `test.pdf`) — the picker renders them as **completely identical list rows**, with no date, no ID, nothing to click the *right* one by.

**Source-code verified**: `components/DocumentPicker.jsx:63-68` renders only `d.filename`, `d.page_count`, `d.total_views` — no `d.created_at`, no `d.id`. This is inconsistent with the Upload and Storage tables elsewhere in the same app, which both show a truncated document ID under the filename for exactly this reason.

**Recommended fix**: add a relative upload date (or the same truncated-ID pattern already used in Upload/Storage) under the filename in `DocumentPicker.jsx`, matching the disambiguation the rest of the app already provides.

## 4. Audit Log table: the "Details" column is reachable but undiscoverable

**Severity: Low.** At narrower widths (≤ ~900px), the Audit Log's rightmost "Details" column (e.g., "name: QA_Test_Org · slug: ...") renders cut off flush against the card's right edge, with no visible scrollbar, no fade, and no affordance hinting that more content exists.

**Browser-verified, and specifically checked for the difference from item 1**: unlike the Analytics bug, this content is **not actually lost** — DOM inspection found an ancestor `<div>` with `overflow-x: auto` and a real 43px of scrollable width (`scrollWidth: 667` vs `clientWidth: 624`). The content is technically reachable by scrolling inside the table area. The defect is discoverability, not data loss: nothing in the UI signals that this column continues off-screen.

**Recommended fix**: a subtle right-edge fade/scroll-shadow when the table has overflow, or reduce the visible-by-default columns and move "Details" to a click-to-expand row, consistent with the product's general preference for removing UI over adding it.

## 5. Ruled out on closer inspection: Storage screen usage bars

Included for transparency, not as a defect. An initial automated check appeared to show every small test file (328 bytes, 11 bytes) rendering a full-width storage usage bar — which would have been a real bug (implying a broken percentage calculation). Investigated further via raw inline-style inspection rather than trusted at first glance: the actual fill-bar element's computed style was `width: 0.0032554%` — mathematically exact for `328 / 10,075,384 bytes`. The apparent "full bar" was the check's own selector matching the *empty track* div (which also happened to have `border-radius: 2px` and was picked up by an overly broad CSS selector), not the fill. **The feature works correctly; the first check was wrong**, and is corrected here rather than left in as a false finding.

## 6. Not a code defect — test-data debris in the live account

The account used for this sprint's testing carries a lot of accumulated QA debris: an organization named `"m"`, a dozen-plus documents named `test.pdf` with no distinguishing content, `temp_test_doc.txt` duplicates, etc. This isn't a product bug (the UI renders exactly what it's given), but it actively made items 1 and 3 above harder to evaluate cleanly and would look unprofessional in front of a customer. Recommend a cleanup pass on this specific test account before any live demo.

---

## Priority order

1. **Analytics overflow at 768px** (item 1) — fix before claiming the app supports its own stated minimum width.
2. **Notifications feed detail** (item 2) — fix before relying on this screen for any real customer workflow; it currently cannot do its job.
3. **Document picker disambiguation** (item 3) — cheap, real usability gap.
4. **Audit Log scroll affordance** (item 4) — cosmetic/discoverability polish.
5. Test-account cleanup (item 6) — do before any demo, not a code change.
