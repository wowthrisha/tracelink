# Technical Debt Register — Sprint V7.0 (Phase 6)

Every remaining debt item identified across this sprint and the prior governance sprint, categorized, with Risk/Complexity/Priority estimates. No large refactors implemented — this is a register, not a fix list. Priority: P0 (do next) / P1 (soon) / P2 (planned) / P3 (opportunistic).

## Architecture

| Item | Risk | Complexity | Priority | Source |
|---|---|---|---|---|
| `documents.py:upload_document` (~180 lines) mixes validation, ID resolution, storage, retention, and task dispatch inline | Low (works today) | Medium (needs per-piece test coverage) | P2 | `MODULE_BOUNDARIES_AND_CODE_QUALITY.md` |
| `viewer.py:download_document` reimplements link/session validation inline instead of reusing cached-lookup helpers | Low | Medium | P2 | Same |
| `AccessScreen.jsx` (~900 lines, 3 unrelated feature domains) — natural 3-way split already identified | Low | Medium (clean boundaries already exist) | P1 | Same |
| 7 frontend components call the API client directly instead of receiving props (bypass their owning screen/hook) | Low | Medium-high (coordinated multi-file change) | P2 | Same |
| Response-serialization convention drift across 6+ routers (hand-rolled dict builders vs. Pydantic response models) | Low | Medium | P2 | `CODE_STANDARDIZATION.md`, `API_MATURITY_REPORT.md` |

## Security

| Item | Risk | Complexity | Priority | Source |
|---|---|---|---|---|
| AUTH-006: session token in `localStorage`, real XSS-exposure vector | **Medium-high** | High (full auth-architecture migration, plan already written) | **P0** | `SECURITY_HARDENING_PLAN.md` |
| `resolve_annotation` allows any viewer session on a link to resolve any other viewer's annotation — undecided whether this is intentional collaborative behavior or a bug | Low-medium (ambiguous) | Low (once decided) | P1 (needs a product decision first, not engineering) | `SECURITY_GOVERNANCE.md` |
| Two security-sensitive config defaults (`ip_hash_salt`, `domain_verify_salt`) ship with hardcoded, documented-but-unenforced insecure defaults — no startup-time production guard (unlike HSTS, which does enforce) | Medium | Low (mirror the existing HSTS validator pattern) | **P0** | This sprint's release-readiness research |
| No general-purpose log-redaction layer — exception tracebacks and free-text log messages are emitted verbatim; a stray credential in an error message would leak into structured logs unredacted | Medium | Medium | P1 | Same |
| Org-scoping gap: `webhooks.py`/`api_keys.py`/`billing.py`/`groups.py` are scoped to `user_id` only, not `org_id` — blocks proper multi-tenancy and complicates future SSO/RBAC work | Low today, compounds later | High | P1 | `FUTURE_READINESS.md` |

## Performance / Scalability

| Item | Risk | Complexity | Priority | Source |
|---|---|---|---|---|
| 5 confirmed unbounded list endpoints (`list_documents`, `list_links`, `storage_dashboard`, `list_members`, per-viewer reading sessions) | Low today, grows with account size | Medium (needs coordinated frontend consumption, not backend-only) | P1 | `SCALABILITY_REVIEW.md` |
| `storage_dashboard` sorts its entire unbounded document set in Python instead of SQL | Low today | Low-medium (coupled to the pagination fix above) | P1 | Same |
| Document upload fully buffers the file into memory before the size-limit check runs | Low (adapter limits mitigate) | High (streaming validation is a real architecture change) | P2 | Same |
| `requeue_orphaned_uploads` dispatches one task per orphan with no batching — thundering-herd risk after a worker-fleet outage | Low (rare trigger condition) | Medium (needs load-testing to size correctly) | P2 | Same |
| `viewer.py:download_document`'s synchronous PDF write blocks the event loop (new finding this sprint) | Low-medium | Low (mirror the adjacent `run_in_executor` pattern already used one line above) | **P1** | `CODE_STANDARDIZATION.md` |
| `services/toc/cache.py:invalidate_toc()` is dead code — TOC cache invalidation relies purely on a 5-minute TTL instead | Very low | Low | P3 | `REPOSITORY_HEALTH.md` |

## Developer Experience

| Item | Risk | Complexity | Priority | Source |
|---|---|---|---|---|
| README's environment-variable table is factually wrong (`JWT_SECRET` unused, `SUPABASE_SERVICE_KEY` misnamed, `STORAGE_BACKEND` doesn't exist) | Low risk, high friction | **Very low** (pure doc correction) | **P0** | `DEVELOPER_EXPERIENCE.md` |
| `.env.example` missing the variables the docs reference | Low risk, high friction | Very low | **P0** | Same |
| `DEVELOPER_GUIDE.md`'s docker-compose command uses service names that don't match `docker-compose.yml` | Low risk, high friction | Very low | **P0** | Same |
| `DEVELOPER_GUIDE.md` says frontend tests go in `frontend/src/tests/`; actual convention is colocated `__tests__/` folders | Low | Very low | P1 | Same |
| No PR template, no CODEOWNERS | Low | Low | P2 | Same |
| No linter (ESLint) or type-checker (mypy/ruff) configured anywhere in the repo | Medium (correctness/consistency drift over time with 20 engineers) | Medium (initial config + baseline noise + CI wiring) | P1 | `REPOSITORY_HEALTH.md` (V6.0) |
| No documented "why no build framework/router library" for the frontend's unusual architecture | Low, pure confusion cost | Very low | P2 | `DEVELOPER_EXPERIENCE.md` |
| `tests/regression/` (a real, distinct test category) isn't mentioned in any engineer-facing doc | Low | Very low | P2 | Same |

## Maintainability

| Item | Risk | Complexity | Priority | Source |
|---|---|---|---|---|
| Typed-vs-raw-dict Pydantic schema split across routers, with no documented rule for which pattern to use | Medium (compounds as more endpoints are added the "wrong" way) | Medium (endpoint-by-endpoint migration) | P1 | `LONG_TERM_MAINTAINABILITY.md`, `CODE_STANDARDIZATION.md` |
| No spacing-token scale on the frontend (color tokens exist, spacing doesn't) | Low | Low (additive, no migration needed for new usage) | P1 | `FRONTEND_MATURITY.md` |
| `Document.org_id` has no `ForeignKey` constraint (org delete silently orphans documents) | Medium (data-integrity + confusing delete-modal copy) | Medium (needs a product decision: cascade vs. block vs. reassign) | P1 (decision), P2 (implementation) | `SECURITY_GOVERNANCE.md` |
| `ORG_ROLES` fixed 4-value tuple with no extension point | Low today | High (touches every `role_gte()` call site's assumptions) | P2 | `FUTURE_READINESS.md` |

## Documentation

| Item | Risk | Complexity | Priority | Source |
|---|---|---|---|---|
| Version numbering incoherent across the repo (4 disagreeing signals: package.json 1.0.0, git tag v1.0.0-beta, docs claiming v8.1.0, a cert doc at v3.2.2) | Medium (external-facing confusion — auditors, security researchers) | Low (pick one source of truth, update the rest) | **P0** | This sprint's release-readiness research |
| `docs/release/` has 14 overlapping files with no single canonical release doc | Medium | Medium (needs human judgment on which content is authoritative) | P1 | `ENGINEERING_GOVERNANCE.md` |
| `ARCHITECTURE.md`/`OVERVIEW.md` genuinely **contradict** each other on the watermarking model and cache-revocation TTLs (not just coverage gaps) | Medium (a wrong number here misleads an incident responder) | Low-medium (needs one source-code verification pass, then the merge is mechanical — outline already written) | **P0** | `DOCUMENTATION_MATURITY.md` |
| No canonical database-schema/ERD document exists despite 27 migrations | Medium | Medium | P1 | `ENGINEERING_GOVERNANCE.md` |
| `archive/README.md` points at 6 paths that don't exist | Low | Very low | P2 | Same |
| Both root architecture diagrams under-represent or omit the Reading Intelligence Engine and Organizations subsystems | Low-medium | Low (once the merge above happens) | P1 | `DOCUMENTATION_MATURITY.md` |
| `docs/operations/BACKUP_RESTORE.md` describes PITR/S3/WAL-replication infrastructure that isn't actually implemented anywhere in the repo — reads as real, isn't | **Medium-high** (a team could believe DR coverage exists that doesn't) | Low (doc correction — scope the doc to what's real, or flag the rest as "planned") | **P0** | This sprint's release-readiness research |

## Testing

| Item | Risk | Complexity | Priority | Source |
|---|---|---|---|---|
| No lint/type-check step exists in CI beyond `ruff` for backend (confirmed: CI does run backend lint + full test matrix + a migration smoke test + frontend build + dependency audit + Bandit scan — genuinely solid) but **no frontend lint/type-check at all** | Low-medium | Medium | P1 | `DEVELOPER_EXPERIENCE.md`, this sprint's release-readiness research |
| No alerting/monitoring consumption layer despite excellent raw instrumentation (Prometheus, structured JSON logs, OpenTelemetry all genuinely well-built) — no Grafana dashboard, no Alertmanager config anywhere in-repo | **High** (a production incident could go unnoticed) | Medium (provisioning work, not code) | **P0** | This sprint's release-readiness research |
| Backup automation exists and is well-built (pg_dump, verified, rotated) but is gated behind an opt-in docker-compose profile — a plain `docker compose up` does not back up anything | **High** | Very low (flip the default, or make the gate loud/documented at deploy time) | **P0** | Same |
| No versioned, tagged deployment artifact — CI builds a Docker image but never pushes/tags it, so "rollback" means re-checkout-and-rebuild, not switching to a known-good image | Medium-high | Medium (registry + tagging strategy) | P1 | Same |

---

## Summary by priority

- **P0 (7 items)** — mostly small/contained: two security-default fixes, three documentation corrections (README env vars, `.env.example`, docker-compose service names), the ARCHITECTURE.md/OVERVIEW.md contradiction resolution, and one genuinely urgent operational gap each on monitoring-consumption and backup-defaults. Notably, most P0 items are **cheap to fix** — the priority comes from risk/impact, not from being hard.
- **P1 (11 items)** — the bulk of real architectural and process debt; each needs dedicated scoped work, not a quick patch.
- **P2 (9 items)** — real but lower urgency, appropriate for opportunistic scheduling.
- **P3 (1 item)** — trivial dead-code cleanup, no urgency.

This register intentionally does not recommend fixing everything — several items (RBAC expansion, i18n, full multi-tenancy) are correctly NOT READY per `FUTURE_READINESS.md` and shouldn't be pulled forward until there's an actual product decision to build the feature they'd support.
