# V24 Checkpoint — Deep Browser Certification

**Timestamp:** 2026-08-11 (session start)
**Purpose:** Allow a new Claude session to resume this V24 certification without repeating completed work.

## 0. State recovered from source-of-truth files

Read in full before starting: `SESSION_RECOVERY.md`, `PRODUCTION_REGRESSION_CERTIFICATION.md`, `BUG_REMEDIATION_REPORT.md`, `CHECKPOINT.md`. (`ENGINEERING_BACKLOG.md`, `docs/engineering/FIX_LOG.md`, `docs/engineering/ACTION_LOG.md`, `PROGRESS.md` are the ENG-XXX-numbered sprint history — not re-read line by line this pass since `CHECKPOINT.md`'s V23.0 section already summarizes the relevant handoff; they remain the source of truth for anything ENG-XXX-numbered.)

## 1. Repository / deploy state

- **Branch:** `main`
- **HEAD:** `31242b8` — `docs(V23.0): final remediation report + regression certification + checkpoint`
- **Working tree:** Clean
- **Ahead of `origin/main` by 12 commits** (9 from the V23.0 BUG-00X/OBS-001 sprint + 3 pre-existing). **Nothing pushed.** `origin/main` auto-deploys to live production Railway — do not push without explicit user confirmation.
- **Local Docker stack:** `api` (healthy, 3h up), `worker` (healthy, 4h up), `db`/`redis`/`beat` (healthy, weeks up). `/health` → 200. This stack has every V23.0 fix deployed (rebuilt after each commit last session).
- **Production Railway:** unverified this session — has received none of the V23.0 fixes (per above).

## 2. V23.0 backlog outcome (full detail in `BUG_REMEDIATION_REPORT.md`)

| ID | Status |
|---|---|
| BUG-001 (TOC/Search nav) | Not reproducible — investigated exhaustively, no code changed |
| BUG-002 (Viewers tab crash) | Fixed, Source+Regression Verified |
| BUG-003 (Analytics label mismatch) | Fixed, Source+Regression Verified |
| BUG-004 (expired doc still active — security) | Fixed, API+Browser Verified |
| BUG-005 (blocked download/print no feedback) | Fixed, **Browser Verified** |
| BUG-006 (Export dropdown dark theme) | Fixed, Source+Regression Verified — **live visual check still pending, owner login required** |
| BUG-007 (webhook checkbox alignment) | Fixed, Source+Regression Verified — **live visual check still pending, owner login required** |
| BUG-008 (analytics help icon a11y) | Fixed, Source+Regression Verified — **live visual check still pending, owner login required** |
| OBS-001 (sign-in flash) | Reproduced live, fixed, **Browser Verified** both before/after |

## 3. Outstanding blocker — READ THIS FIRST

**The browser tab (`tabId` in the active `claude-in-chrome` session) is on the Sign In screen and has been for the entire prior session.** The assistant does not enter credentials into login forms under any circumstances — not a preference, a standing boundary that does not lift under authorization, urgency, or repeated instruction.

This blocks nearly everything in Phases 1–3 of the V24 mandate: BUG-006/007/008 live verification, and every owner-authenticated screen (Dashboard, Documents, Access Control, Analytics, Organizations, API Keys, Webhooks, Audit Log, Notifications, Billing, Storage, Profile, Settings). Only the **Public Viewer** workflow (`/v/{token}`, no login) is reachable without the user signing in.

**Do not attempt to work around this** (no scripted login, no credential harvesting, no bypassing the gate). If the user has not signed in by the time this session needs to produce a result, document the blocker honestly rather than fabricating verification.

## 4. What this session will do given the blocker

1. Ask the user to sign in (already pending from last session — repeating the ask is not productive; state it once, then proceed with what's possible).
2. In parallel / while waiting: exercise the **Public Viewer** workflow end-to-end using disposable share links (the established no-login pattern from V23.0 — create a throwaway document directly via the `worker` container, generate a link, drive the browser against `/v/{token}`), covering Phase 3's "PUBLIC VIEWER" workflow and as much of Phase 4 (adversarial) and Phase 5 (Reading Intelligence viewer-side) as is reachable without an owner session.
3. Do NOT fabricate screenshots, workflow completions, or verification for any owner-authenticated screen. Mark those `[INSUFFICIENT EVIDENCE]` / `NOT VERIFIED — blocked on sign-in` rather than guessing.
4. Once signed in (whenever that happens, this session or a future one), resume with Phase 1 (BUG-006/007/008) then Phase 2 onward per the full mandate.

## 5. Do NOT redo

- Do not re-investigate BUG-001, or re-fix BUG-002–005/OBS-001 — closed with passing tests and (for 002/004/005/OBS-001) live evidence. Only reopen on a fresh, objectively-demonstrated regression.
- Do not re-run the full backend/frontend regression suite speculatively before making any change — baseline from last session: backend 1763 passed/1 skipped, frontend 56 passed, both 0 failed. Re-run after any new fix, not before.

## 6. Screenshot storage

Per the mandate: `~/Downloads/TraceLink_Product_Audit/V24/` (Desktop/Tablet/Mobile/Workflows/Viewer/Before/After/Errors subfolders) and `docs/ui-audit/V24/`. Not yet created — `computer` screenshot/zoom actions were intermittently unavailable this session (CDP timeouts); all evidence gathered via `get_page_text`/`javascript_tool`/`find`/network-request inspection instead, which is fully sufficient for the findings recorded but doesn't produce image files. Create these directories and start capturing real screenshots once `computer` actions are reliably available and/or once owner-authenticated screens are reachable.

## 7. Progress this session (update after every milestone — see `V24_ISSUE_DATABASE.md` for full detail)

- **V24-001 found, fixed, and browser-verified**: Reading Intelligence completely non-functional for every `.txt`/`.md`/`.log` document (High severity, previously undiscovered). Commit `ec60082` (+ bundle rebuild `e28dfa9`).
- Public Viewer workflow (Phase 3) exercised: session load, page navigation, Reading Intelligence timer (start/pause/resume/accumulate), link revocation → terminal "Link Revoked" state.
- Adversarial API testing (Phase 4, non-destructive subset): nonexistent/garbage/SQL-injection-shaped/unicode tokens, malformed JSON, empty body, negative/zero chunk numbers — all handled cleanly, no crashes, no injection.
- Two disposable test documents created and cleaned up (`ead9d4d7…`, `1af9376b…`, `a9bbfd25…` — all deleted after use, no real data touched).
- **Still blocked**: everything requiring owner login (see §3–4). Have not attempted Phases 2, 6, 7 (most of it), 8 (org/role boundaries), 9, 10, or the BUG-006/007/008 live check.
- Regression baseline after V24-001: backend unchanged at 1763 passed/1 skipped (no backend changes this fix); frontend now 63 passed, 0 failed (11 files, +1 test file).
