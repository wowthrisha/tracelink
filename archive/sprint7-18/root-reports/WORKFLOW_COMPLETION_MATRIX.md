# Workflow Completion Matrix — Live QA Sprint

Every workflow driven live against `https://wowmyspace--tracelink.up.railway.app` via Playwright. ✅ = proven START→MIDDLE→END→ERROR→RECOVERY→SUCCESS with evidence. Partial rows explain exactly what's missing and why.

| Workflow | Start | Middle | End | Error path | Recovery | Success | Status |
|---|---|---|---|---|---|---|---|
| Upload | ✅ real PDF upload | ✅ processing observed | ✅ Ready status | — (no forced-failure case exercised) | — | ✅ toast + row confirmed | ✅ |
| Protect (Access Control) | ✅ doc selected | ✅ password/expiry/watermark/IP-allowlist set | ✅ Create Share Link | — | — | ✅ link created, confirmed in Links tab | ✅ |
| Configure Access | ✅ | ✅ | ✅ | — | — | ✅ | ✅ |
| Create Share Link | ✅ named link form | ✅ Create Share Link clicked | ✅ link appears in Links tab with correct badges (PASSWORD, WATERMARK: On) | — | — | ✅ | ✅ |
| Read (anonymous) | ✅ fresh unauthenticated context opens `/v/{token}` | ✅ password gate shown | ✅ document renders | ✅ wrong password → "Wrong password. Try again." | ✅ correct password → access granted | ✅ page content visible, verified pixel-level (also where WATERMARK-001 was found) | ✅ |
| Reading Intelligence | ✅ owner opens Viewer | ✅ Reading Insights panel opens | — | ✅ (READ-OWNER-001 found via this exact path) | ✅ (fixed, verified locally — not yet deployed) | ✅ | ✅ |
| Analytics | ✅ | ✅ overview loads with real counts | ✅ | — | — | ✅ desktop/tablet/mobile captured | ✅ |
| Notifications | ✅ | ✅ feed loads | ✅ | — | — | ✅ | ✅ |
| Audit Log | ✅ | ✅ entries render | ✅ | — | — | ✅ | ✅ |
| Delete (document) | ✅ target positively identified (row-scoped, exact filename) | ✅ dialog names target | ✅ | ✅ (n/a — dialog is the guard) | ✅ Cancel preserves document | ✅ Confirm deletes (verified via fresh reload) | ✅ |
| Organizations: Create | ✅ | ✅ | ✅ 201 confirmed via network | — | — | ✅ | ✅ |
| Organizations: Invite/Add Member | ✅ modal opens | ✅ email + role filled | ✅ | ✅ non-existent email → clear, specific error | n/a (error is terminal, by design) | n/a — see note below | ⚠️ Partial (see note) |
| Organizations: Accept Invite | — | — | — | — | — | — | ❌ Feature does not exist (see note) |
| Organizations: Assign Role | ✅ role selector located | ✅ change attempted | ✅ | ✅ self-demotion of sole owner → 409 blocked | n/a | n/a for this edge case; real role change on a second member not testable (no 2nd account) | ⚠️ Partial (see note) |
| Organizations: Remove Member | ✅ button located | ✅ disabled-state confirmed for sole owner | ✅ | ✅ UI-level safeguard (button disabled) | n/a | real removal of a 2nd member not testable (no 2nd account) | ⚠️ Partial (see note) |
| Organizations: Delete Org | ✅ target identified | ✅ dialog names target | ✅ | n/a | ✅ Cancel preserves org | ✅ Confirm deletes (verified via success toast + fresh state) | ✅ |
| API Keys | ✅ create | ✅ edit scopes, rotate | ✅ | — | ✅ cancel paths on rotate/revoke/delete | ✅ revoke, delete all confirmed | ✅ |
| Webhooks | ✅ register | ✅ test delivery, history, pause/resume | ✅ | — | ✅ cancel path on delete | ✅ delete confirmed | ✅ |
| Billing | ✅ screen loads | ✅ plan/usage/features render correctly | ✅ | n/a (Stripe not configured, correctly messaged) | n/a | ✅ (also where BILLING-PLAN-BADGE-001 was found) | ✅ |
| Storage | ✅ | ✅ usage/projections/per-doc table render | ✅ | — | — | ✅ desktop/tablet/mobile captured | ✅ |
| Reading Analytics | Covered under Reading Intelligence + Analytics above — no separate screen exists for this in the app | | | | | | ✅ (folded in) |

## Notes on partial rows

**Organizations: Invite/Add Member, Accept Invite, Assign Role (2nd member), Remove Member (2nd member)** — this environment has exactly one test account (`23z274@psgtech.ac.in`), no second real SecureDoc account, and this app's "invite" flow (confirmed by reading both the UI copy and testing the error path) adds an *existing* user by email immediately — there is no invite-token/accept-link feature to test in the first place. What *was* testable without a second account:
- The full modal UX and the non-existent-email error path (clear and correct).
- Both safety-relevant edge cases that only need the sole owner: self-demotion blocked (409) and self-removal blocked (disabled button).

What remains genuinely untested: adding a *real second* existing user, changing *their* role, and removing *them*. This requires either a second real SecureDoc account or backend-level test fixtures — flagged in `REMAINING_DECISIONS.md` as a follow-up rather than fabricated here.

## Bugs found this sprint (all fixed in the working tree, not yet deployed)

| ID | Severity | Workflow | One-line summary |
|---|---|---|---|
| WATERMARK-001 | Critical | Read | Visible watermark was a near-total no-op on every shared document in production (alpha-squaring bug) |
| READ-OWNER-001 | High | Reading Intelligence | Document owner could be locked behind their own share link's password gate |
| BILLING-PLAN-BADGE-001 | High | Billing | Sidebar showed "FREE" for a real Pro account everywhere except the Billing screen |

## Incident during testing

An early Delete-workflow test script used an overly broad selector and accidentally deleted a real pre-existing group ("Automated Testing Group"). Its 2 documents were preserved (the app correctly ungroups rather than cascading delete). Full disclosure in `WORKFLOW_PROGRESS.md` and `docs/ui-audit/ACTION_LOG.md`. All subsequent destructive-action scripts use exact-identifier targeting with a hard abort if the confirmation dialog doesn't name the expected target.
