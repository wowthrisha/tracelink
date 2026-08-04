# Known Limitations

Companion to [`FINAL_RELEASE_CERTIFICATION.md`](FINAL_RELEASE_CERTIFICATION.md). Each item states what's actually known versus not, with evidence class.

## Verification environment

- **No browser-automation tool is available in this environment** (Playwright, chromium-cli, or equivalent — checked repeatedly across the V18.0/V20.0/V21.0 sprints via `ToolSearch` and binary lookups, consistently absent). Every UI-facing claim in this repository's engineering documentation is Source Verified (code read and structurally correct) or API/Integration Verified (backend behavior exercised directly against the real local Docker stack), never Browser Verified. A genuine click-through regression pass across every screen has not been performed by this session — it would require either a browser-automation tool being made available, or manual QA by a human tester.
- Load/scale testing was never performed (out of scope by every sprint's own explicit constraints — no destructive or synthetic load generation). Scalability findings in this repository are architectural inferences from source review, not measured performance data.

## Open security items

- **ENG-039**: API keys created with zero granted scopes can still call every endpoint in `orgs.py`, `api_keys.py`, and `billing.py` — those three routers don't enforce `require_scope(...)` the way 7 other routers do. JWT/browser-authenticated users are unaffected. Recommend a security-reviewed rollout of scope enforcement to these routers before broadly issuing API keys to third-party integrators.
- **AUTH-006** (ENG-026, deferred): session token lives in `localStorage`, a real XSS-exposure vector. A phased migration plan exists (`docs/security/SECURITY_HARDENING_PLAN.md`) but hasn't been scheduled. Exploitability requires a chained XSS vulnerability; this session's XSS testing (ENG-009) found none live in the current codebase.
- **ENG-037**: `is_link_active()` was extracted as a "single source of truth" for link-active status, but the real access-enforcement path (`LinkService.validate_link()`) still independently duplicates the check rather than calling the shared predicate. Both currently agree — no live bug — but this is exactly the kind of duplication the refactor was meant to eliminate, and nothing would catch future drift between the two copies.
- **ENG-038**: `ensure_not_last_owner()` has an unguarded TOCTOU race (no row locking) — two simultaneous requests against an org's last two owners could both pass the check. Pre-existing, not introduced by this session's work; narrow window, low blast radius (an orgless-owner state, not data loss or unauthorized access).

## Missing capabilities

- **No profile/account-settings screen** (ENG-033, PROF-001): a signed-in user has no in-app way to change their password or manage their account. This is new-feature work requiring product/design direction (what fields, what flow), not a bug fix — a full proposal is preserved at `archive/sprint7-18/root-reports/PRODUCT_PROPOSAL.md`.
- **No automated CD/deploy job**: CI (`​.github/workflows/ci.yml`) is comprehensive (lint, full test matrix, migration smoke test, dependency/security scanning, Docker build check) but the Docker build never pushes an image, and no deploy job exists in the workflow. The actual live deployment mechanism is Railway's auto-deploy-from-`origin/main`, which works but is undocumented as a repeatable, reviewable process — a genuine gap for anyone deploying this repository outside Railway.
- **Observability wiring unconfirmed** (ENG-017): Prometheus metrics are instrumented in code (`app/metrics.py`), but whether they're actually scraped and alerted on in the live production environment requires infrastructure access this session doesn't have.

## Documentation debt

- `docs/release/` still contains 13 pre-existing historical reports (RC1-era, predating this session's V-numbered sprints — `RC1_CERTIFICATION.md`, `ZERO_DEFECT_CERTIFICATION.md`, `ENTERPRISE_READINESS_CERTIFICATION.md`, etc.) that were not folded into `archive/` during this sprint's documentation consolidation — flagged for a future pass rather than left silently unaddressed.
- `docs/product-review/` similarly has 9 files from an earlier product-review sprint not cross-checked against the current `ENGINEERING_BACKLOG.md` this session.
