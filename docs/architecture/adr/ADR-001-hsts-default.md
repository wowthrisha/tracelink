# ADR-001: HSTS Enabled by Default

**Status:** Accepted
**Date:** 2026-06-07

## Context

HSTS defaulted to disabled (`hsts_max_age=0`) to avoid locking out operators who hadn't confirmed HTTPS. In practice, every deployment without explicit configuration was vulnerable to SSL strip attacks.

## Decision

Set default to `hsts_max_age=31536000` (1 year) with `; preload`. Raise a startup **error** (not warning) if HSTS is disabled in production.

## Consequences

- All new deployments are protected against SSL strip immediately
- Meets NIST SP 800-52 and PCI DSS 4.0 requirement 6.5.1
- Operators on HTTP-only proxies must set `HTTPS_REDIRECT=false` explicitly
- Rollback: `HSTS_MAX_AGE=0` in env disables immediately
