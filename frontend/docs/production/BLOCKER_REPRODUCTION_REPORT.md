# Blocker Reproduction Report
Sprint 4.5A — Production Blocker Elimination
Date: 2026-06-22
Phase: 1 of 7
Method: Direct source reading. Every claim verified from file before fix is attempted.

---

## B-01 — New Link Button Does Not Create Links

**File:** `frontend/src/screens/AccessScreen.jsx`
**Function:** Anonymous `onClick` handler on the "⟳ New Link" `Btn` component
**Line:** 307

**Code as found:**
```jsx
<Btn variant="secondary" onClick={() => toast('New link generated', 'success')} style={{ minWidth: 130 }}>
  ⟳ New Link
</Btn>
```

**Expected behavior:**
1. Button is clicked
2. `POST /api/links` is called with `{ document_id: docId }` (minimal payload — new link with default permissions)
3. Server creates and persists a new share link row in `share_links` table
4. Response contains `share_url` for the new link
5. `fetchLinks()` is called — links list refreshes
6. Tab switches to `'link'` so user sees the new link immediately
7. Toast confirms success

**Actual behavior:**
1. Button is clicked
2. `toast('New link generated', 'success')` fires
3. No API call is made
4. No link is created in the database
5. User sees a success toast for an operation that never occurred

**Evidence that the API method exists:**
- `window.SecureDocAPI.createLink(payload)` exists at `frontend/api.js:261`
- Method posts to `POST /api/links` — confirmed working
- `handleSave` (line 116) already calls `createLink` successfully for the "Save Policy" flow
- `fetchLinks()` callback defined at line 65 and called correctly by other handlers

**Evidence that `docId` is available:**
- `docId` defined at line 63: `const docId = doc?.id || ''`
- The "⟳ New Link" button is only rendered when `docId` is truthy (inside the `doc` conditional block starting at line 171)

**Reproduction steps:**
1. Open SecureDoc with an authenticated owner account
2. Navigate to Access Control screen with a document selected
3. Click "⟳ New Link" button on the Policy tab
4. Observe: toast fires "New link generated"
5. Navigate to Share Link tab
6. Observe: link list is empty OR still shows only pre-existing links — no new link was created

**`creating` state is available:** `const [creating, setCreating] = useState(false)` at line 17 — can be used for loading state on this button

**Fix plan:** Replace the `onClick` handler with an async function that calls `createLink({ document_id: docId })`, handles loading/error states, refreshes links, and switches to the link tab.

---

## B-02 — Credentials in Repository

**File:** `TRACEVIEW_AUDIT_B.md` (repo root: `/Users/thrisha/traceview/securedoc/TRACEVIEW_AUDIT_B.md`)
**Function:** N/A — this is a documentation/audit file, not code
**Lines:** 361–362

**Content found:**
```html
<meta name="supabase-url" content="https://zznenaqcvzxtqxzilpyh.supabase.co" />
<meta name="supabase-anon-key" content="sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc" />
```

**Git history:** Credential appears in commits `ffac077`, `704ca80`, `cc50838`

**CRITICAL CONTEXT (affects severity):**
- Key prefix is `sb_publishable_` — Supabase's naming for anon/public keys
- Supabase publishable keys are DESIGNED to be embedded in client-side HTML; they are not secret keys
- Stripe secrets, JWT secrets, and Redis passwords are in `.env` (not tracked) — confirmed safe
- **Current `frontend/SecureDoc.html`** already uses placeholders: `SECUREDOC_SUPABASE_URL` and `SECUREDOC_SUPABASE_ANON_KEY` — credentials are NOT in the live file
- `TRACEVIEW_AUDIT_B.md` itself rates this as MEDIUM (not P0): "The Supabase anon key is designed to be public (client-facing)"

**REVISED SEVERITY: MEDIUM** (downgraded from P0 in prior governance audit)

**Rationale for downgrade:**
1. Anon keys are not secret. Every Supabase project exposes its anon key in client HTML. This is the design.
2. The live file has already been cleaned to use env placeholders.
3. The risk is not credential theft — it is Supabase RLS misconfiguration. SecureDoc API auth is server-side (JWT via JWKS), limiting the risk.

**Expected behavior:**
- `TRACEVIEW_AUDIT_B.md` should not expose a live project URL + key combination in audit reports
- If the key is truly public-safe, the concern should be documented as accepted risk, not a P0 blocker

**Reproduction steps:**
1. `grep -r "sb_publishable" /Users/thrisha/traceview/securedoc/` — key found in `TRACEVIEW_AUDIT_B.md`
2. `grep "supabase" /Users/thrisha/traceview/securedoc/frontend/SecureDoc.html` — current file uses placeholders only
3. `git -C /Users/thrisha/traceview/securedoc log --oneline | grep -E "ffac077|704ca80|cc50838"` — all three commits confirmed in history

**Fix plan:** Phase 5 (CREDENTIAL_VERIFICATION.md) will document final status and recommendation.

---

## B-03 — javascript: URL Injection Risk in LinksPanel

**File:** `frontend/src/components/LinksPanel.jsx`
**Function:** Link rendering inside `links.map(...)` — anonymous arrow function
**Line:** 79 (the `<a href={link.url}` attribute)

**Code as found:**
```jsx
<a
  href={link.url}
  target="_blank"
  rel="noopener noreferrer"
  onClick={() => { const next = new Set(visitedLinks); next.add(link.url); onVisit(next); }}
```

**Expected behavior:**
- Links with `http://` or `https://` protocol are rendered as clickable anchors
- Links with `javascript:`, `data:`, or `vbscript:` protocols are blocked / rendered inert
- The domain display at line 62 safely extracts hostname for display

**Actual behavior:**
- `link.url` is set directly on `href` with no protocol validation
- `javascript:alert(1)` would be rendered as a clickable link
- React 18 issues a console warning for `javascript:` href but does NOT block rendering or navigation
- `rel="noopener noreferrer"` is present (prevents window.opener access) but does NOT prevent `javascript:` execution

**Attack surface:**
- `link.url` values come from PDF annotation extraction (backend pipeline)
- An attacker uploads a PDF with `javascript:` URI annotations
- Attacker shares the document link with a victim
- Victim views the document, clicks a link in the Links panel
- Arbitrary JavaScript executes in the victim's browser context (within the SecureDoc origin)
- Attacker can steal session tokens, cookies, or perform actions as the victim

**Reproduction steps:**
1. Create a PDF with a hyperlink annotation set to `javascript:alert(document.cookie)`
2. Upload to SecureDoc
3. Share with a link (or view as owner)
4. Open the Links panel on the page containing the annotation
5. Click the displayed link

**Fix plan:** Add protocol guard before rendering href. Block `javascript:`, `data:`, `vbscript:` — preserve `http:` and `https:`. Also fix domain extraction to return null for non-http/https so the link displays as "invalid URL" rather than rendering.

---

## B-04 — Export CSV Button Does Not Export

**File:** `frontend/src/screens/AnalyticsScreen.jsx`
**Function:** Anonymous `onClick` handler on the "↓ Export CSV" `Btn` component
**Line:** 81

**Code as found:**
```jsx
<Btn variant="secondary" size="sm" onClick={() => toast('Export started — CSV ready in a moment', 'success')}>
  ↓ Export CSV
</Btn>
```

**Expected behavior:**
1. Button is clicked
2. A CSV file is generated containing the currently displayed analytics data
3. Browser downloads the file (via blob or data URI)
4. User sees success confirmation

**Actual behavior:**
1. Button is clicked
2. `toast('Export started — CSV ready in a moment', 'success')` fires
3. No file is generated, no download occurs
4. User waits for a CSV that never arrives

**Evidence that no backend export endpoint exists:**
- `grep -n "export\|csv\|CSV" /backend/app/routers/analytics.py` — no export endpoint found
- `grep -n "analytics\|export\|csv" /frontend/api.js` — no analytics export method in api.js

**Data already in frontend state:**
- `docStats` — per-document analytics array (already loaded at screen mount)
- `groupStats` — per-group analytics array (already loaded)
- `overview` — aggregate KPI data
- All state loaded via `Promise.all` at `AnalyticsScreen.jsx:26-34` on mount

**Fix plan:** Client-side CSV generation from already-loaded `docStats` / `groupStats` state — no new endpoint required. Export the current tab's data. Uses a `_downloadBlob` utility pattern already present in `api.js` (lines 618, 624) for CSV download.

---

## Summary

| Blocker | File | Line | Root Cause | Fix Complexity |
|---|---|---|---|---|
| B-01 | `AccessScreen.jsx` | 307 | onClick = toast only, no createLink call | Low — wire existing method |
| B-02 | `TRACEVIEW_AUDIT_B.md` (git history) | 361-362 | Public anon key in audit file + git history | Medium — hygiene, not emergency |
| B-03 | `LinksPanel.jsx` | 79 | href={link.url} with no protocol guard | Low — add protocol check |
| B-04 | `AnalyticsScreen.jsx` | 81 | onClick = toast only, no export logic | Low — client-side CSV from loaded data |
