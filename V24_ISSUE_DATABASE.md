# V24 Issue Database

| ID | Severity | Area | Finding | Evidence | Status |
|---|---|---|---|---|---|
| V24-001 | **High** | Reading Intelligence / Viewer | `isDocumentReady` was derived solely from `imgReady` (PDF/image `<img>` `onLoad`). The page-image-loading effect explicitly skips text documents entirely, so `imgReady` never becomes true for `.txt`/`.md`/`.log` documents — the entire Reading Intelligence timer, active-time tracking, and backend flush never ran for any text-format document in the product. | [BROWSER VERIFIED] — public share link, disposable doc: "Timer paused — not started" persisted 8+ seconds including a real click; zero `POST /api/reading/batch` requests fired despite the 5s flush interval. Re-verified after fix: timer counts up correctly ("Reading time: Ns, timer running"), `POST /api/reading/batch` fires repeatedly with 200s. | **FIXED** (`ec60082`), 7 new unit tests, regression suite green |

## Investigated, no defect found

| Area | What was checked | Evidence | Verdict |
|---|---|---|---|
| Public viewer — link revocation | Opened a live session, revoked the link out-of-band (simulating an owner action), reloaded | [BROWSER VERIFIED] — clean terminal state: "🚫 Link Revoked — This share link has been revoked by the document owner." | No defect |
| Reading Intelligence — accumulator correctness across page navigation | Live smoke test: page 1 → wait → page 2 → wait, checked total time monotonically increased, never reset | [BROWSER VERIFIED] (qualitative) + [SOURCE VERIFIED] (per-page bucket accumulation logic, previously hardened in ENG-048) + [REGRESSION VERIFIED] (`test_reading_analytics.py`, 37 tests, part of this session's full suite run) | No defect. Precise timing-accuracy claims not independently re-derived — MCP tool round-trip latency makes wall-clock-precise assertions unreliable in this harness; relying on the existing regression suite for that guarantee is the correct evidence tier here, not a gap. |
| Idle detection / auto-pause | Real idle time (~30s, no synthetic mouse events between tool calls) correctly triggered "timer paused"; a real click correctly resumed it | [BROWSER VERIFIED] | No defect |
| `/api/viewer/gate/{token}` — nonexistent token | `curl` nonexistent token → | [API VERIFIED] 404 | No defect |
| `/api/viewer/gate/{token}` — 5000-char garbage token | `curl` | [API VERIFIED] 404, no crash | No defect |
| `/api/viewer/gate/{token}` — SQL-injection-shaped token (`' OR '1'='1`) | `curl`, properly URL-encoded | [API VERIFIED] 404, `{"detail":"Link not found"}` — no injection, no 500 | No defect |
| `/api/viewer/gate/{token}` — emoji/unicode token | `curl` | [API VERIFIED] 404, clean | No defect |
| `POST /api/viewer/validate` — empty body `{}` | `curl` | [API VERIFIED] 404 (empty token → not found) | No defect |
| `POST /api/viewer/validate` — malformed JSON | `curl` | [API VERIFIED] 422 (FastAPI request validation) | No defect |
| `/api/viewer/text/{token}/{chunk}` — negative/zero chunk number, fake token | `curl` | [API VERIFIED] 400 `session_id is required` (session check runs first; chunk-number validation and token lookup both correctly unreachable without a session) | No defect |

## Automation-tool artifacts (NOT product defects — logged for transparency, not filed as bugs)

| Observation | Root cause | Disposition |
|---|---|---|
| `computer` tool's `left_click` on the toolbar "Next page" button (via accessibility-tree `ref`) did not navigate the page | Confirmed via direct `element.click()` in `javascript_tool` that the button works correctly — this was a `computer`-tool coordinate/viewport-scaling quirk, not a rendering or event-handling bug in the product | Not a defect. Switched to JS-driven clicks for the remainder of this session's interactive testing. |
| `computer` `screenshot`/`zoom` actions intermittently timed out (`CDP Page.captureScreenshot` 30s timeout) | Environment/extension-level, not app-related | Worked around via `get_page_text`/`javascript_tool`/`find`, which were reliable throughout |

## Blocked — cannot verify without owner login

Every item in Phase 1 (BUG-006/007/008 live check) and essentially all of Phases 2, 6, 7, 8 (partially), 9, 10 require an authenticated owner session: Dashboard, Documents list, Access Control, Analytics, Organizations, API Keys, Webhooks, Audit Log, Notifications, Billing, Storage, Profile, Settings. **Not attempted, not fabricated** — the assistant does not enter credentials into login forms under any circumstances. See `V24_CHECKPOINT.md` §3–4.
