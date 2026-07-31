# Workflow Validation Report — Live QA Sprint

## Mission

Act as the final human QA engineer before release. No code review first — drive the actual deployed product with a real browser, exactly as a customer would, and prove every workflow reaches START → MIDDLE → END → ERROR PATH → RECOVERY → SUCCESS. Fix what's broken, retest, repeat. Never stop halfway.

## Method

Playwright (Python, headless Chromium) driving `https://wowmyspace--tracelink.up.railway.app` — the live deployed instance — logged in as a real test account (`23z274@psgtech.ac.in`). No mocks, no stubs, no local dev server. Every claim in this report is backed by a screenshot, a network trace, or a full test-suite run; where a check gave a false result, the correction and the reason are logged in place rather than silently fixed.

## What was validated

All 7 workflow groups named in the mission: the full document lifecycle (Upload → Protect → Configure Access → Create Share Link → Read → Reading Intelligence → Analytics → Notifications → Audit Log → Delete), Organizations (Create → Members/Invite → Assign Role → Remove Member → Delete Org), API Keys, Webhooks, Billing, Storage, and Reading Analytics (folded into Reading Intelligence + Analytics, since no separate screen exists for it). Full pass/fail breakdown per sub-step: `WORKFLOW_COMPLETION_MATRIX.md`. Chronological record of every action: `WORKFLOW_ACTIVITY_LOG.md` / `docs/ui-audit/ACTION_LOG.md`. Screenshot inventory: `WORKFLOW_SCREENSHOTS.md`.

## Bugs found, root-caused, fixed, and verified

### WATERMARK-001 — Critical

The visible watermark — this product's core security promise — was a near-total no-op on every shared document in production. Reproduced live: opened a real password-protected share link as a genuinely anonymous viewer, fetched the rendered page, and even at 8x contrast enhancement there was zero watermark signal. Root cause, isolated at the unit level: `WatermarkService.apply_visible_watermark` (`backend/app/services/watermark.py`) pasted each rotated watermark tile onto the overlay using the tile's own RGBA data as its own paste mask. That blends the alpha value twice — once for pixel color, once for the resulting alpha — squaring a 22%-opacity watermark down to roughly 4.7% effective opacity, invisible after WEBP compression on real content. Fixed by compositing each tile through an intermediate transparent layer with `Image.alpha_composite()` instead. Verified: a blank-page unit repro went from 0 non-white pixels to 61,018; a regression test (`test_apply_visible_watermark_is_actually_visible`) was added specifically because the *existing* test suite already had 13 watermark tests and none of them would have caught this — they checked byte-level difference, not visibility. Full backend suite: 1703 passed, 1 skipped, no regressions.

### READ-OWNER-001 — High

A document owner, fully authenticated with their own session, could get locked out of their own document's internal Viewer by their own share link. Reproduced live: after creating a password-protected share link for a test document, clicking that same document from the owner's own Upload dashboard routed through `/api/viewer/gate/{token}` using that password-protected link — showing the owner the same "Password Required" gate a public recipient would see. Root cause: `frontend/src/hooks/useViewerSession.js`'s auto-link-resolution effect fetched all active links for the document and used `active[0].token` — whichever link the API happened to return first — with no regard for whether that link carried restrictions. A dedicated unrestricted "Admin Preview" link is only auto-created when *no* links exist yet; once the owner creates their first restricted share link, that safety net silently stops applying. Fixed: prefer a link with no viewer-facing restrictions, falling back to one explicitly labeled "Admin Preview", and only creating a fresh one if neither exists. Verified: frontend suite 13/13, build clean.

### BILLING-PLAN-BADGE-001 — High

The persistent sidebar plan badge showed "FREE" for a real Pro-plan account on every screen in the app except the Billing screen itself — reproduced on 3 separate fresh page loads. Root cause: `AppShell.jsx` hardcoded `const [plan, setPlan] = useState('free')` and the *only* place that ever called `setPlan` with the real value was `BillingScreen`'s own data-load callback — so the badge was wrong by default on every session until the user happened to visit Billing. Fixed with a mount-time fetch of `/api/billing/status` in `AppShell.jsx`, mirroring the same call `BillingScreen` already makes. Verified: frontend suite 13/13, build clean.

**Deploy status for all three: fixed in the local working tree, NOT deployed.** The live Railway instance still exhibits all three bugs as of this report, since nothing has been pushed this session — consistent with this session's standing policy of never committing or deploying without an explicit request. This is the single most important caveat in this report: **the live site a real user would hit right now still has these bugs.**

## The incident

An early Delete-workflow test script used a CSS attribute selector broad enough to match "Delete group" buttons instead of the intended per-document delete control. The first click was caught and cancelled correctly, but a second attempt (testing the confirm path) hit the same wrong element and confirmed deletion of a real, pre-existing group ("Automated Testing Group"). Its 2 member documents were preserved — the app correctly ungroups rather than cascade-deletes — but the group itself, per the app's own confirmation dialog, could not be recovered. This was disclosed to the user immediately and in full, before any further destructive testing continued. Every destructive-action script written after this point resolves its target by exact identifier (unique filename text scoped to a single row, or a resource's exact database ID) and includes a hard abort if the confirmation dialog that appears doesn't explicitly name the expected target.

## What could not be tested, and why

**Organizations: Accept Invite** does not exist as a feature in this application. Confirmed by reading the invite modal's own copy and by testing its actual behavior: "Add Member" adds an *existing* SecureDoc user by email immediately — there is no invitation token, no pending state, and no accept step. This is an architectural fact about the product, not a gap in this session's testing.

**Organizations: Assign Role / Remove Member for a second real member** — this environment has exactly one test account. What *was* tested without a second account: the full modal UX, the error path for a non-existent email, and both safety-relevant edge cases available with a single member (blocking the sole owner from demoting or removing themselves — both correctly blocked, one at the API layer with a 409 and one even more strongly at the UI layer with a disabled button). Testing a real role change or removal *of another person* requires a second real account or backend test fixtures; flagged as a follow-up in `REMAINING_DECISIONS.md` rather than fabricated here.

## Regression status

Backend: 1703 passed, 1 skipped — unchanged from session baseline, run fresh after all three fixes. Frontend: 13/13 passed, build clean (310.2kb) after every frontend-touching change this sprint. Zero regressions introduced.

## Stop-condition assessment against the mission's own criteria

- "Every workflow completes successfully" — yes, for all 7 workflow groups, with the two explicitly-scoped exceptions above (a feature that doesn't exist, and an edge case that needs a second account).
- "Every edge case has been exercised" — the edge cases reachable with the tools and accounts available this session were exercised (wrong password, non-existent invite email, self-demotion, self-removal, cancel paths on every destructive dialog, non-listening webhook endpoint). Edge cases requiring infrastructure not available here (a second real account, a live webhook receiver, a configured Stripe test-mode account) are named explicitly above rather than skipped silently.
- "Every workflow has screenshots" and "before/after evidence" — 86 screenshots filed and indexed (`WORKFLOW_SCREENSHOTS.md`), before/after evidence captured for all 3 fixed bugs (`docs/ui-audit/BEFORE_AFTER_INDEX.md`).

The one condition genuinely unmet: the fixes exist only locally. Until they're deployed, the live product still has all three bugs this report found. That's the next decision for the user, not something this session should do unilaterally.
