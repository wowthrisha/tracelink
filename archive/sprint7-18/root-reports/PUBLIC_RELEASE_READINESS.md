# Public Release Readiness — Sprint V7.0 (Phase 9)

Pretending TraceLink is going public next week: versioning, release process, rollback, migrations, backup, observability, monitoring, incident response, logging, configuration, deployment.

## Versioning — incoherent, the most confusing finding of this phase

Four disagreeing signals exist simultaneously: `frontend/package.json` says `"1.0.0"`; the only git tag is `v1.0.0-beta`; multiple docs (`DEPLOYMENT.md`, `RC1_DEPLOYMENT_REPORT.md`, `RC1_CERTIFICATION.md`) claim `v8.1.0`; and `ZERO_DEFECT_CERTIFICATION.md` is stamped `v3.2.2` while `docs/engineering/CHANGELOG.md` is frozen at `3.2.1` and the actively-maintained root `CHANGELOG.md` has no version number at all, just an `[Unreleased]` heading. Compounding this, `RC1_DEPLOYMENT_REPORT.md` claims "26 migrations" against an actual 27. There is no version-bump discipline anywhere in CI. **An external security researcher or customer looking at this repo today cannot determine what version they're looking at.**

## Release process — real CI, no CD

`.github/workflows/ci.yml` is genuinely solid: backend lint (ruff), full test matrix against real Postgres+Redis services, a dedicated `alembic upgrade head` migration smoke test, frontend build, `pip-audit`/`npm audit` dependency scanning, a Bandit security scan, and a Docker build check. But the Docker build never pushes (`push: false`) — there is no deploy/release job at all. `docs/release/`'s 14 files read as one-time "RC-1" point-in-time reports, not a repeatable release process doc. Deployment today is `docker compose up --build` from whatever's checked out — manual, not automated.

## Rollback strategy — documented at the DB layer, absent at the deployment layer

`alembic downgrade -1` is documented in `BACKUP_RESTORE.md`, `RUNBOOK.md`, and `INCIDENT_RESPONSE.md`, and (see Migrations below) is genuinely implemented for all 27 migrations. But there's no versioned deployment artifact to roll the *application* back to — Docker images built by CI carry no tag/label, and the build is never pushed to a registry. In practice, "rollback" means `git checkout <previous commit>` and rebuild, not "redeploy the last known-good image." This is the single largest gap between what's documented and what's operationally real.

## Database migrations — genuinely well-built

All 27 migrations have real `downgrade()` implementations (verified by sampling the 6 most recent). The one exception (`008_add_printed_event_type.py`, a no-op downgrade) is an explicitly-commented, correct Postgres limitation (enum values can't be removed), not an oversight. A dedicated advisory-lock-based migration runner serializes concurrent API/worker startup. `BACKUP_RESTORE.md` asserts a "no destructive single-migration schema changes" convention, but nothing in CI actually enforces that claim — it's a stated discipline, not a machine-checked one.

## Backup strategy — real automation, but opt-in and oversold

`scripts/backup.sh`/`restore.sh` are genuinely well-built: gzip verification, rotation, a pre-restore safety backup, typed-confirmation requirement. Wired into `docker-compose.yml` as a real, schedulable service (daily 02:00 UTC). **But it's gated behind `profiles: [backup]`** — a plain `docker compose up` does not start it; an operator must know to explicitly opt in. Separately, `BACKUP_RESTORE.md` describes S3 upload, WAL-based point-in-time recovery, cross-region replication, and monthly restore-verification drills — **none of which correspond to anything actually configured in the repo.** The local pg_dump backup is real; the disaster-recovery story beyond it is aspirational documentation, not implementation, and reads as if it were both.

## Observability — excellent instrumentation, zero consumption layer

`metrics.py` defines ~20 well-designed Prometheus metrics with explicit anti-PII and cardinality-explosion safeguards. `json_logging.py` implements a real structured-JSON formatter designed for Loki/Datadog/CloudWatch ingestion, with session-ID redaction (only an 8-char prefix is ever logged). `telemetry.py` wires OpenTelemetry tracing (no-op by default, ready to point at Tempo/Jaeger/Honeycomb/X-Ray). This is genuinely mature instrumentation. **What's entirely missing: no Grafana dashboard, no Alertmanager config, nothing in the repo that actually consumes any of this.** An archived internal assessment already on file in the repo itself independently reached the same conclusion.

## Monitoring/alerting — thresholds documented, nothing wired

`docker-compose.yml` has real healthchecks for `db`, `redis`, `api`, and `worker`. `RUNBOOK.md` documents concrete alerting thresholds (5xx rate, p99 latency, queue depth, cache hit rate) and references PagerDuty/Slack channels — but these are all external, undocumented-in-repo integrations. Nothing in the repo enforces or fires any of these thresholds today.

## Incident response — a genuine strength

`INCIDENT_RESPONSE.md` is a real, specific, actionable runbook — not boilerplate. It names actual tables/columns from this codebase (`viewer_sessions`, `access_events`, `webhook_deliveries`), gives copy-pasteable commands for P0/P1/P2 scenarios (service-down, data-breach/token-compromise, stuck processing queue, high error rate, webhook failures), and ends with a structured post-mortem template. This is materially better than typical generic incident docs and should be held up as the model for other operational docs in this repo.

## Logging — consistent, narrowly redacted

One code path drives both dev and prod logging (a single `enable_json_logging` flag), so there's no dev-vs-prod drift risk. Session IDs are correctly redacted to an 8-char prefix everywhere. **Gap**: there is no general-purpose redaction layer — exception tracebacks and free-text log messages are emitted verbatim, so a stray credential embedded in an error message would leak into structured logs unredacted. No explicit `log_level` config field exists either.

## Configuration management — solid, with one real enforcement gap

`config.py` uses `pydantic_settings.BaseSettings` uniformly, every field env-var-backed with sane defaults, well-documented in `.env.example`. **Real gap**: two security-sensitive fields (`ip_hash_salt`, `domain_verify_salt`) ship with hardcoded, comment-only-warned insecure defaults — unlike HSTS, which has an actual `model_validator` that fails startup in production if left unconfigured, these two have no equivalent enforcement. This is the most concrete, cheapest-to-fix security gap found in this entire phase. No hardcoded live credentials found anywhere in the repo.

## Deployment — a stateless design genuinely implemented, shipped as single-instance

`SCALING.md` states the API is fully stateless, and this holds up under inspection: the process-local viewer cache is correctly documented and designed as a short-TTL read-through layer (not authoritative state), and the page cache correctly implements a proper L1-local/L2-Redis tiered design so horizontal scaling doesn't break cache correctness. `SCALING.md` documents concrete scaling tiers up to Kubernetes+HPA. But the shipped `docker-compose.yml` hardcodes single-instance service hostnames directly into connection strings — true horizontal scaling would require compose/env changes not present out of the box, even though the application code itself is ready for it.

---

## Top 5 gaps of most concern before a real public release

1. **No versioned, tagged, deployable rollback target** — CI builds but never publishes an image; rollback today means source-checkout-and-rebuild, a real risk during a bad release.
2. **Version numbering is incoherent across the repo** — 4 disagreeing signals will confuse any external party trying to know what they're looking at.
3. **No alerting/monitoring consumption layer** despite excellent raw instrumentation — a production incident could go unpaged today.
4. **Backup automation is opt-in, and the documented DR strategy overstates what's actually implemented** (PITR/S3/replication described, not built).
5. **No production-time enforcement on two security-sensitive config defaults**, unlike the HSTS pattern that already proves the codebase knows how to do this correctly.

Every one of these is fixable without a large refactor — three are documentation/config corrections, two are provisioning/registry work — which is worth stating plainly: this is a codebase that is operationally *close* to public-release-ready, not fundamentally unready. The gap is consistency and follow-through on already-proven patterns (the HSTS enforcement, the real incident-response runbook, the real backup script), not missing capability.
