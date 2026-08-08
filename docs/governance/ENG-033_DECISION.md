# ENG-033 — Decision Record: Profile / Account-Settings Screen

**Status**: OPEN / DECISION REQUIRED (V22.0, 2026-08-07 — re-confirmed, not implemented)
**Type**: Product/design decision, not an engineering defect

## Decision required

Whether to build an in-app profile/account-settings screen, and if so, what capabilities it exposes (password change, email change, session/device management, account deletion, notification preferences, etc.).

## Current state

Source-verified: `find frontend/src -iname "*profile*"` returns nothing; `atoms.jsx`'s Sidebar nav config has no Profile/Settings entry. A signed-in user has no in-app way to change their password, view active sessions, or manage account-level settings. Password reset exists only via the logged-out "forgot password" email flow.

## Available options

1. **Do nothing (status quo)** — password changes remain reset-email-only; no new screen. Zero engineering cost, but a real, user-facing capability gap for a document-security product where users reasonably expect account self-service.
2. **Minimal profile screen** — display name/email (read-only, since these come from Supabase auth) + a "change password" action that reuses the existing Supabase reset-password flow, triggered in-app instead of requiring the user to sign out first.
3. **Full account-settings screen** — adds session/device listing and revocation, notification preferences, and account deletion, on top of (2). Meaningfully larger scope: new backend endpoints for session listing (ties into whatever comes out of AUTH-006/refresh-token work), a deletion flow with data-retention/GDPR implications, and new UI patterns not yet established anywhere else in the product.

## Trade-offs

- Option 1 costs nothing but leaves a real usability gap open indefinitely.
- Option 2 is small, self-contained, and reuses existing backend machinery (Supabase password-reset) — low risk, low effort, addresses the most commonly needed capability (password change) without inventing new architecture.
- Option 3 is the "complete" answer but pulls in unresolved dependencies (session/device tracking doesn't exist yet; would benefit from landing after any AUTH-006 cookie-session migration, since that work already touches session lifecycle) and product-policy questions (data retention on deletion) this engineering pass has no authority to answer unilaterally.

## Recommended default

Option 2 (minimal profile screen) as a first increment, if/when this is picked up — smallest scope that closes the actual gap (no self-service password change), defers the harder session-management and deletion questions to a later, explicitly-scoped follow-up rather than blocking on them.

## What blocks implementation

No product/design sign-off exists on which of the above scopes to build, what the deletion/data-retention policy should be (needed before option 3 could even be scoped), or whether session-management should wait for the AUTH-006 cookie migration to land first (building it against the current localStorage-token model would need rework if that migration proceeds). Per the governing mandate, this is left **OPEN / DECISION REQUIRED** — no code or UI implemented.
