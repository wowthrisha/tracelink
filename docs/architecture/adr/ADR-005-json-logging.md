# ADR-005: JSON Logging Enabled by Default

**Status:** Accepted
**Date:** 2026-06-07

## Context

`enable_json_logging` defaulted to `False`, so all production deployments without explicit configuration got plaintext logs with no structured fields — making log aggregation, alerting, and incident response difficult.

## Decision

Change default to `True`. Operators who need plaintext (local dev without log aggregator) set `ENABLE_JSON_LOGGING=false`.

## Consequences

- All new deployments get structured logs compatible with Grafana Loki, Datadog, CloudWatch out of the box
- Local development logs are harder to read in terminal — mitigated by `ENABLE_JSON_LOGGING=false` in local `.env`
