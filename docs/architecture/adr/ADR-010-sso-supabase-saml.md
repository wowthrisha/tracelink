# ADR-010: SSO via Supabase SAML

**Status:** Accepted
**Date:** 2026-06-07

## Context

Two options evaluated for enterprise SSO:

1. **WorkOS SDK** — turnkey SAML/OIDC; ~$0.10/user/month for enterprise tier
2. **Supabase SAML** — Supabase Auth natively supports SAML 2.0 (since 2023); free up to certain limits

## Decision

Implement SSO via Supabase Auth SAML. The existing JWT validation in `auth.py` already validates Supabase JWTs. Supabase handles the SAML SP/IdP integration; our application only needs:

1. `Organization` model (already implemented)
2. Org membership resolution in `auth.py:get_current_user()`
3. SSO-initiation endpoint

## Consequences

- No new vendor or billing relationship introduced
- Supports Google Workspace, Azure AD, and Okta out of the box via Supabase
- Supabase SAML is less battle-tested than WorkOS for edge cases (attribute mapping, JIT provisioning) — requires thorough testing before GA
