# TraceLink (SecureDoc) — V22.0 Residual Risk Closure Certification

**This is the authoritative certification for the V22.0 "Residual Risk Closure" sprint.** It builds on, and does not contradict, `docs/release/FINAL_RELEASE_CERTIFICATION.md` (V21.0) — that document's product/UI/Viewer/Reading-Intelligence/architecture findings are unchanged and not re-litigated here. This document covers only what V22.0 closed, found, or left open: API-key authorization (ENG-039/041/042/043), the bounded authorization-consistency sweep, observability (ENG-017/044), the Viewer-toggle inventory (ENG-040), the two duplication/concurrency investigations (ENG-037/038), and the three decision/architectural-risk items (ENG-033, ENG-034, AUTH-006/ENG-026).

## 1. Baseline and release candidate commit

V22.0 started from commit `1c31090` (confirmed clean working tree, single-branch history, migration head `027`, per `docs/engineering/V22_BASELINE.md`). This certification reflects the repository at commit `953def4` (branch `main`) — **[SOURCE VERIFIED]** via `git log --oneline -1`. Working tree is clean at that commit (confirmed via `git status --short` immediately before writing this document). Not pushed to `origin/main` this sprint; Railway's auto-deploy-on-push means nothing in this sprint has reached production. No destructive action was taken against real user data at any point — all live verification this sprint used the two established local test accounts and disposable entities created and cleaned up in the course of testing.

## 2. Priority 1 — ENG-039: API-key zero-scope authorization gap

**[SOURCE VERIFIED] + [TEST VERIFIED] + [API VERIFIED].** Confirmed real, not a false positive. Full endpoint-by-endpoint matrix in `docs/security/ENG-039_ORG_AUTHORIZATION_TRACE.md`. Root cause: `orgs.py` (12 routes), `api_keys.py` (6 routes), `billing.py` (3 routes) used only `Depends(get_current_user)` with no `require_scope(...)` check, so an API key created with **zero** scopes could still invite/remove/promote organization members, rotate/delete other API keys, and read/change billing state — the only three routers among thirteen missing this check.

**Fix (root cause, not per-endpoint patch)**: extended `API_SCOPES` with 6 new scopes (`organizations:{read,write}`, `api_keys:{read,write}`, `billing:{read,write}`), applied `Depends(require_scope(...))` to all 21 routes across the three routers, and added `_reject_scope_escalation()` so an API-key caller can never create or update a key with scopes it does not itself hold (JWT/browser callers remain unrestricted, by design — JWT is the owner-level auth path). New regression suite: `backend/tests/integration/test_eng039_org_api_key_scopes.py`, 28 tests covering no-key/invalid-key/revoked-key/expired-key/zero-scope-key/correctly-scoped-key/incorrectly-scoped-key/org-member/org-admin/org-owner/cross-organization-access, both allowed and denied paths. Denial responses return `403` with a generic "missing required scope" message — no internal detail exposed. Proven to detect the original bug via `git stash` revert (12/28 tests failed pre-fix, all 28 pass post-fix).

**Cross-check for the same defect class elsewhere**: extended the matrix to all 10 authenticated-router families. Found and fixed 3 more instances of the identical pattern — **ENG-041** (`admin.py`'s `/audit-log`), **ENG-042** (`annotations.py`'s 10 uploader-facing document routes), **ENG-043** (`notifications.py`'s SSE `/stream`) — each scoped to the correct read/write scope per its actual data-access nature. Confirmed 7 other routers (`documents`, `links`, `groups`, `webhooks`, `storage`, `analytics`, `reading`) were **already correctly scoped** — not modified, per the mandate's "only modify another module if the same defect is objectively demonstrated" instruction. `viewer.py` and the viewer-session `/api/viewer/...` annotation routes correctly use a separate, non-`get_current_user` auth model and were confirmed out of scope.

## 3. Priority 2 — Bounded authorization-consistency review

**[SOURCE VERIFIED] + [TEST VERIFIED].** Full matrix in `docs/security/API_AUTHORIZATION_MATRIX.md`, covering every user-authenticated router and explaining the two distinct auth models in this codebase (user-authenticated vs. viewer-session-authenticated). 8 new regression tests (`test_priority2_scope_consistency.py`) covering the 3 routers fixed under ENG-041/042/043. No missing scope checks, scope bypasses, empty-scope fallbacks, IDOR opportunities, privilege-escalation paths, or fail-open behavior found beyond what ENG-039/041/042/043 already closed — **no unlimited security rewrite performed**, per the mandate's explicit bound.

## 4. Priority 3 — ENG-017: Observability

**[SOURCE VERIFIED] + [API VERIFIED].** Re-classified with full IMPLEMENTED/WIRED/TESTED/DEPLOYED/EXTERNALLY-MONITORED evidence in `ENGINEERING_BACKLOG.md`. Structured logging, correlation/request IDs, `/health` and `/ready` (both confirmed live, correct responses), `/metrics` (confirmed IP-allowlist/token-gated — `403` from outside, real accumulated data from inside), security-event logging, and audit logging are all confirmed IMPLEMENTED and WIRED. **One genuine gap found and fixed**: zero Celery worker instrumentation. Added `celery_task_duration_seconds`/`celery_tasks_total` (Histogram/Counter, labels `task_name`/`outcome`) wired into `process_document`'s success/error/retry paths, with 3 new unit tests. **One new gap found while verifying, filed as ENG-044** (open): the API and Celery worker are separate OS processes; `prometheus_client`'s default registry is per-process, so worker-recorded metrics are invisible on the API's `/metrics` without a `PROMETHEUS_MULTIPROC_DIR` multiprocess-registry setup — confirmed via a real document upload processed by the real local worker, checked against `/metrics` immediately after (metric families registered, zero samples). Per the mandate, this is classified as an infrastructure/deployment requirement, not an application-code defect, and is not fixed this sprint. No claim of Grafana, alerting, or external production monitoring is made — none was found to exist.

## 5. Priority 4 — ENG-040: Uploader-controlled Viewer toggle sweep

**[SOURCE VERIFIED].** Full inventory in `docs/security/ENG-040_VIEWER_TOGGLE_INVENTORY.md` — all 8 uploader-controlled Viewer permissions (`can_download`, `can_print`, `can_copy`, `can_right_click`, `watermark_enabled`, `can_annotate`, `enable_info`, `show_reading_insights`) traced against configurability/visibility/persistence/API-enforcement/Viewer-enforcement/edit-propagation/safe-defaults/audit-logging. 7 of 8 already fully correct. The 8th, `show_reading_insights`, was the exact defect class this sweep exists to catch — already found and fixed earlier this sprint (ENG-035/036) before this formal sweep began. No decorative toggles found; no new toggles created (verification-only pass, per the mandate). Permission-edit propagation to already-open viewer sessions confirmed within the ~10s link-cache TTL via `invalidate_link()` and independently re-confirmed live this closeout pass (see §9's end-to-end link-lifecycle test).

## 6. Priority 5 — ENG-037: `is_link_active()` duplication

**[SOURCE VERIFIED] + [TEST VERIFIED].** Confirmed real: `validate_link()` (the actual enforcement path) independently re-implements the revoked/expired checks rather than calling the boolean predicate `is_link_active()`. Investigated a literal merge and deliberately **did not perform it** — `validate_link()`'s checks carry per-reason HTTP status/detail and analytics event types a boolean predicate can't express, and `max_views` is an atomic `UPDATE...RETURNING` (concurrency-correct) that a shared predicate cannot structurally replace; forcing a merge would add a reason-code abstraction layer for a risk that is currently only theoretical (both implementations agree today). Instead added a 6-test regression tripwire (`test_eng037_link_active_consistency.py`) that fails immediately if the two implementations ever disagree. Closed — no code merge, per the mandate's "only if it reduces complexity" constraint.

## 7. Priority 6 — ENG-038: `ensure_not_last_owner()` TOCTOU

**[ENGINEERING INFERENCE — reclassified LOW-RISK, not fixed].** Per the mandate's explicit "do not fix concurrency based on intuition — first construct a reproducible test" instruction, attempted genuine reproduction against the real local Docker stack: 2 live owners on a real test organization, concurrent `DELETE /api/orgs/{id}/members/{user_id}` requests via `asyncio.gather`, 2 clean data-bearing trials (a 3rd hit a network-level timeout under real DB contention, discarded as inconclusive rather than counted). **Race did not reproduce** in either clean trial — exactly one owner remained each time, the second request correctly blocked with `409`. Reclassified from an assumed-exploitable finding to LOW-RISK INFERENCE. Deliberately did not add a `SELECT ... FOR UPDATE` lock without a reproducible failing test, per the mandate's own instruction against intuition-based fixes. Remains open, documented, not fixed.

## 8. ENG-033 / ENG-034 / AUTH-006 — Decision and architectural-risk items

**[PRODUCT DECISION] / [PRODUCT DECISION] / [ENGINEERING INFERENCE, deferred].**

- **ENG-033** (no profile/account-settings screen): full decision record in `docs/governance/ENG-033_DECISION.md` — 3 options, recommended default (minimal password-change screen reusing the existing Supabase reset flow), blocked on product/design sign-off and a data-retention policy for the fuller account-deletion option. Left **OPEN/DECISION REQUIRED**, nothing implemented.
- **ENG-034** (no CD/deploy job): full decision record in `docs/governance/ENG-034_DECISION.md` — 3 options, recommended default (CI-gated branch protection, no new infrastructure needed), the full CD job blocked on an ops decision (deploy target, registry/credentials, rollback procedure). Left **OPEN/DECISION REQUIRED**, no workflow changes made.
- **AUTH-006/ENG-026** (session token in `localStorage`): re-evaluated in `docs/security/SECURITY_HARDENING_PLAN.md` §9. New evidence this sprint: `backend/app/middleware/security_headers.py`'s hash-based CSP (`script-src 'self'` + exact SHA-384 hashes for React/ReactDOM, no `unsafe-inline`/`unsafe-eval`) is a genuine mitigating control, narrowing the realistic exploit chain to two independent failures (a working XSS injection AND defeating the hash-allowlisted CSP) rather than one. No live or source XSS still found. Severity revised **Medium-High → Medium**. The full migration plan, blast radius (60 frontend + 72 backend call sites), CSRF-double-submit design, phased rollout, and rollback strategy remain documented and ready (§§1-8, unchanged and accurate). No approved migration decision exists in the repository, so per the mandate this is **not implemented** — preserved as a documented architectural risk.

## 9. Final re-certification — test evidence

| Suite | Result | Evidence class |
|---|---|---|
| Backend (`pytest tests/unit tests/integration tests/regression`) | **1751 passed, 1 skipped, 0 failed** | **[TEST VERIFIED]** — host-run, final commit |
| Frontend (`vitest`) | **13/13 passed** | **[TEST VERIFIED]** |
| Frontend build (`esbuild`) | **succeeded, 309.2kb** | **[TEST VERIFIED]** |
| Migrations (`alembic`) | **single head (027); live DB `alembic current` = 027** | **[TEST VERIFIED]** against the live local Docker Postgres |
| Static checks (debugger/console.log/print/TODO/secrets) | **zero matches on V22.0-touched files** | **[SOURCE VERIFIED]** |
| `git status` | **clean** (except this sprint's own commits) | **[SOURCE VERIFIED]** |
| Live API smoke (`/health`, documents/orgs/links/api-keys/webhooks/admin-audit-log/billing) | **all 200; `/metrics` correctly 403 from outside the allowlist** | **[API VERIFIED]** |
| Live link lifecycle (create → validate → edit → propagation → revoke → validate) | **create 200 → validate reflects `can_download:false` → PATCH 200 → validate immediately reflects `can_download:true` → DELETE 200 → validate returns 410** | **[API VERIFIED]**, disposable link on the test account's own document |
| Browser-driven end-to-end test | **not performed** | **[BLOCKED — INSUFFICIENT EVIDENCE]** — no browser-automation tool available in this environment, stated honestly rather than fabricated |

One environment-selection artifact encountered and resolved during this pass, documented for future sessions: running the backend suite via `docker compose exec api pytest` produces 25 failures, all traced to pre-existing tests that hardcode the host absolute path `/Users/thrisha/traceview/securedoc/...` (not present inside the container's `/app` filesystem) — not a regression. The host-run invocation above is this repository's correct, established test-execution path.

## 10. Backlog status

`ENGINEERING_BACKLOG.md` — 44 tracked items, recounted directly from the table: **27 closed, 7 deferred (with re-confirmed reasoning), 3 reviewed-not-implemented, 1 justified-not-changed, 6 open**. Every open item is blocked on a named, non-engineering input:

| ID | Item | Blocker |
|---|---|---|
| ENG-019 | Dashboard toggle sweep incomplete | Needs browser-automation tooling or manual QA (carried from V21.0, unchanged) |
| ENG-033 | No profile/account-settings screen | Product/design decision — see §8 |
| ENG-034 | No CD/deploy job | Ops deployment-policy decision — see §8 |
| ENG-037 | `is_link_active()` duplication | Closed this sprint with a tripwire, not a merge — retained here only as the tripwire's documentation pointer, not an open defect |
| ENG-038 | `ensure_not_last_owner()` TOCTOU | Reclassified LOW-RISK INFERENCE this sprint; no reproducible failure to fix against |
| ENG-044 | Celery worker metrics invisible cross-process | Needs a `PROMETHEUS_MULTIPROC_DIR` ops/infra decision |

(ENG-037 is listed above only for completeness against the backlog table's literal "Open (low urgency, needs care)" status label, which reflects the tripwire's intentionally-permanent nature, not an unresolved defect — see §6.)

**Zero unexplained backlog entries.** Every item is FIXED, PROVEN FALSE, VERIFIED AND DEFERRED WITH A SPECIFIC REASON, or CLASSIFIED AS A PRODUCT/INFRASTRUCTURE DECISION.

## 11. Security and authorization status

**[SOURCE VERIFIED] + [TEST VERIFIED].** The zero-scope-means-unlimited-access defect class (ENG-039/041/042/043) is closed across all 4 confirmed instances, with regression coverage proving both the original bug and the fix. The bounded consistency review (§3) found no further instances. Deny-by-default is now the enforced posture for API-key scope checking across orgs/api-keys/billing/admin-audit-log/annotations/notifications, matching the 7 routers that were already correct. AUTH-006 remains a documented, unimplemented architectural risk (§8) — real but requiring a chained XSS this session found no evidence of, against a CSP that materially narrows the realistic exploit path.

## 12. Observability status

**[SOURCE VERIFIED] + [API VERIFIED].** IMPLEMENTED + WIRED: structured logging, correlation/request IDs, `/health`, `/ready`, `/metrics` (IP-allowlist/token-gated), security-event logging, audit logging, and (as of this sprint) Celery task duration/outcome metrics for `process_document`. TESTED: the new Celery metrics via 3 unit tests; the rest via this sprint's live `/metrics` checks and the pre-existing suite. NOT DEPLOYED / EXTERNALLY MONITORED: no claim of Grafana, alerting rules, or a production monitoring stack is made — none was found to exist, and building one is out of this sprint's scope. ENG-044 (cross-process Celery metric visibility) is the one open gap, classified as an OPERATIONS requirement per the mandate, not fixed in application code.

## 13. Viewer-toggle status

**[SOURCE VERIFIED].** All 8 uploader-controlled Viewer capabilities confirmed real, correctly enforced (server-side where a server action exists to gate, client-side-only and correctly documented as a UX gate where none exists), safely defaulted, and propagating to open sessions within the cache TTL. See §5.

## 14. Known limitations (V22.0-specific; see also V21.0's `KNOWN_LIMITATIONS.md` for carried-forward items)

- No browser-automation tool available in this environment — all V22.0 verification is Source, Test, or API/Integration Verified, never Browser Verified, stated explicitly rather than implied.
- AUTH-006 (session token in `localStorage`) remains an unimplemented, documented architectural risk — mitigated but not eliminated by the confirmed CSP.
- ENG-044 (Celery worker metrics invisible on `/metrics` due to per-process registry isolation) is open, needs ops/infra input on a multiprocess-registry deployment change.
- ENG-033 and ENG-034 remain open pending product/design and ops decisions respectively, each with a full decision record ready to act on once that input arrives.
- ENG-019 (dashboard toggle sweep incomplete) and ENG-038 (TOCTOU, reclassified low-risk) are carried forward unchanged from V21.0/this sprint, per §10.

## 15. Deployment status

Not pushed to `origin/main` this sprint. All work verified against the local Docker stack (`docker compose up --build` — `db`/`redis`/`api`/`worker`/`beat` services, all healthy at time of final verification) and, for backend test execution, a host-side Python environment per this repository's established convention. Railway's auto-deploy-from-`origin/main` remains the actual live deployment mechanism and was not triggered.

## 16. Release recommendation

Every objectively-demonstrated engineering risk named in the V22.0 mandate's canonical list is closed with evidence (ENG-039/041/042/043 fixed and regression-tested; ENG-017 re-classified with one real gap fixed; ENG-040 verified with no defect found; ENG-037 closed with a tripwire) or classified with a specific, named reason it cannot be closed by this engineering pass alone (ENG-038 low-risk inference with reproduction evidence; ENG-033/034 product/ops decisions with full decision records; AUTH-006 a documented, mitigated architectural risk; ENG-044 an operations requirement). The final regression suite is green (1751/1/0 backend, 13/13 frontend), the migration chain is at head, the working tree is clean, and a live end-to-end link-lifecycle check against the real stack confirms core enforcement and permission-propagation behavior. No Critical or High severity item is open. No fabricated fix, invented defect, or unverified deployment claim appears anywhere in this document or in `ENGINEERING_BACKLOG.md`'s V22.0 entries.

**RELEASE STATUS: READY WITH DOCUMENTED LIMITATIONS**
