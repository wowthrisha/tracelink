# Release Blockers — TraceLink / SecureDoc

This document classifies every open gap found across this sprint's security, scalability, architecture, code-quality, and UI/Viewer certifications into exactly one tier: **blocks release**, **must verify before enterprise security claims**, **must fix before scaling**, or **recommended, non-blocking**. Nothing here is invented — every item cites the certification document and section it came from. Per the Golden Rule governing this sprint, if an item's evidence is insufficient to classify with confidence, that is stated explicitly rather than guessed.

---

## Tier 0 — Blocks release

**None found.**

No confirmed, live-observed defect from this sprint's testing (security boundary probing, repository cleanup, full UI re-certification, deep Viewer re-certification) rises to an active, reproducible break in core functionality, data isolation, or security enforcement. This is a claim bounded by what was actually tested — the gaps below are real, but they are evidence gaps or scale-triggered risks, not confirmed defects.

## Tier 1 — Must verify before making enterprise security guarantees

These are cases where the *pattern* is architecturally sound (source-code verified) but the *live enforcement* was not independently proven this sprint, because doing so would have required actions outside this sprint's authorized scope (a second real account, artificial load generation, or waiting out a multi-hour timer).

1. **Cross-account IDOR** — `SECURITY_CERTIFICATION.md` §2. The query-scoped authorization pattern (`WHERE user_id == current_user_id`) is sound by construction and independently re-confirmed by code read this sprint, but was never exercised live with two distinct accounts, since only one real test account existed. **This is the single largest gap in this sprint's security work.** Before telling an enterprise customer "your documents are isolated from other tenants," create a second test account and prove it.
2. **Rate-limit boundary (429 at request 21)** — `SECURITY_CERTIFICATION.md` §4. The 20/minute limit's existence and Redis-backed cross-replica correctness are source-verified; whether it actually fires at exactly the 21st request was not tested, to avoid generating artificial traffic.
3. **XSS on fields beyond link labels** — `SECURITY_CERTIFICATION.md` §5. One field (link label) was live-tested and correctly escaped. Document filenames, organization names, webhook descriptions, and API key names were not each individually re-tested — the inference that they're equally safe (same JSX pipeline, no `dangerouslySetInnerHTML` found) is reasonable but not proof.
4. **Expired-link enforcement, live confirmation** — `UI_EXCELLENCE_SCORECARD.md` (Viewer section). Source-verified as the identical code path as revocation (which *was* live-confirmed), but the expiry branch itself was never triggered live, since the UI's date-only expiry granularity makes a real-time wait-it-out test impractical.

**None of these block shipping today** — they block making an unconditional, tested guarantee about these specific boundaries. If an enterprise customer's security questionnaire asks "have you tested tenant isolation with two accounts," the honest answer this sprint is "the pattern is verified by code, not yet by live cross-account test."

## Tier 2 — Must fix (or verify) before horizontal scaling

These are architecturally safe *today* (single-replica deployment, current usage patterns) but become real risk at higher scale or replica count. All from `SCALABILITY_CERTIFICATION.md`.

1. **DB connection pooling has no cluster-wide budget** (§2, §11) — safe at 1 API replica; becomes an outage risk the moment a second replica is added without addressing pool sizing across replicas. **Priority: before 1,000 users, specifically before running >1 API replica.**
2. **Process-local viewer cache has no cross-process invalidation broadcast** (§6, `ARCHITECTURE_CERTIFICATION.md` §3) — bounded, documented ≤10s staleness for link/permission changes (not revocation, which is unaffected). Only matters if horizontally scaled *and* a customer has a hard requirement for provably-instant (not ≤10s) propagation.
3. **5 of 6 list endpoints have no pagination** (§1) — safe while per-account document/link/key/webhook counts stay small; becomes a real cost the moment a power-user account accumulates a large library. **Priority: before 10,000 users.**
4. **Storage call sites' blocking-I/O safety not exhaustively re-audited this sprint** (§9) — flagged specifically because this exact bug class (synchronous boto3 calls blocking the async event loop) already caused one confirmed real issue in this codebase (fixed in `viewer.py`'s download path, V4.0). Cheap to verify, compounds badly under load if present elsewhere. **Priority: before 1,000 users.**

## Tier 3 — Recommended, non-blocking

1. **No frontend equivalent of `ruff`** — `CODE_QUALITY_CERTIFICATION.md` §6. Backend dead-code detection is now rigorous (AST-verified); frontend unused-import detection has no equivalent tool installed. Stated as a real gap, not a defect.
2. **`AccessScreen.jsx` oversized (~900 lines)** — `ISSUE_DATABASE.md` M-13, a long-standing, deliberately deferred refactor.
3. **Duplicated 7-key `permissions` dict** — `ARCHITECTURE_DECISIONS.md` AD-7, deliberately extended rather than consolidated, with recorded rationale.
4. **Observability wiring unconfirmed** — `ARCHITECTURE_CERTIFICATION.md` §7. Prometheus metrics are instrumented in code; whether they're actually scraped/alerted-on in production was not verified this sprint.
5. **Large-PDF (100+ page) Viewer stress not freshly re-tested** — `UI_EXCELLENCE_SCORECARD.md`, carried forward from this sprint's Viewer work, which prioritized the explicitly-named edge cases over a fresh large-document stress pass.

---

## Verdict

**No Tier 0 blockers exist.** The codebase is releasable in its current single-replica deployment shape, with the Tier 1 items disclosed as untested-not-unsound and the Tier 2 items scoped to future scale thresholds that have not yet been reached. See `FINAL_RELEASE_CERTIFICATION.md` for the overall go/no-go synthesis across all five certification documents.
