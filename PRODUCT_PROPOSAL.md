# Product Proposal — Profile / Account Settings Screen (PROF-001)

**Status**: Proposal only — not scheduled, not implemented this sprint
**Source finding**: PROF-001 (🔴 High, verified) — `find frontend/src -iname "*profile*"` returns nothing, and `AppShell.jsx`'s nav config (`frontend/src/components/atoms.jsx:278-320`) has no Profile/Settings entry. There is genuinely no way for a signed-in user to change their password or manage their account inside the app today.

This is written as a proposal rather than implemented directly because it's a new screen (new UI, at minimum one new backend endpoint), not a bug patch — the remediation brief explicitly scopes new-feature work out of this sprint and asks for a proposal instead.

---

## 1. Problem

A logged-in user has no in-app path to:
- change their password (the only path today is the logged-out "Forgot password" email-reset flow on `LoginScreen.jsx`)
- see which email/account they're signed in as, beyond the small sidebar label
- delete their account

This is a real gap, not a nice-to-have: password rotation is a baseline expectation for any authenticated product, and its absence pushes every password change through an email round-trip.

## 2. UX flow

**Entry point**: add a "Profile" (or "Account") item to the `Sidebar`'s `NAV_SECTIONS` (`atoms.jsx:315-319`, the existing "Account" section that today only has Billing), routed the same way every other screen is (`AppShell.jsx` screen-switch pattern already used for `upload`/`viewer`/`access`/etc.).

**Screen layout** (matches the existing screen conventions — `Header` + `Card`-based sections, consistent with `BillingScreen.jsx` / `StorageScreen.jsx`):

```
┌─ Header: "Profile" ──────────────────────────────┐
│                                                    │
│  ┌ Account ─────────────────────────────────┐    │
│  │  Email        you@example.com (read-only) │    │
│  │  Plan         FREE / PRO badge             │    │
│  │  Member since  <created_at>                │    │
│  └──────────────────────────────────────────┘    │
│                                                    │
│  ┌ Change Password ─────────────────────────┐    │
│  │  Current Password   [........]            │    │
│  │  New Password       [........]            │    │
│  │  Confirm Password   [........]            │    │
│  │                         [Update Password] │    │
│  └──────────────────────────────────────────┘    │
│                                                    │
│  ┌ Danger Zone ──────────────────────────────┐    │
│  │  Delete Account                            │    │
│  │  Permanently deletes your account and all  │    │
│  │  documents, links, and organizations you   │    │
│  │  own. This cannot be undone.               │    │
│  │                         [Delete Account]   │    │
│  └──────────────────────────────────────────┘    │
│                                                    │
└────────────────────────────────────────────────┘
```

- "Change Password" reuses the existing `resetPassword`-style Supabase call pattern already in `api.js`, but scoped to an *authenticated* re-auth (verify current password via a fresh Supabase password-grant call before allowing the change — don't let a hijacked session silently change the password without re-proving it).
- "Delete Account" opens a `Modal` (reuse the existing `Modal` component and the confirmation-copy pattern already used in `OrgsScreen.jsx`'s delete-org modal) requiring the user to type their email to confirm, consistent with how other irreversible actions in this app are gated.

## 3. API requirements

Two new backend endpoints, following the existing `backend/app/routers/auth.py` pattern (uses the Supabase Admin API with the service-role key, same as `register`):

- **`POST /api/auth/change-password`** (authenticated, `Depends(get_current_user)`)
  - Body: `{ current_password: str, new_password: str }`
  - Re-verifies `current_password` via a Supabase password-grant call (same call shape as `SecureDocAPI.auth('login', ...)` today) before calling the Supabase Admin API to update the password — mirrors the re-auth pattern Supabase itself recommends for sensitive changes.
  - Returns 200 on success, 401 if `current_password` doesn't verify.

- **`DELETE /api/auth/account`** (authenticated, `Depends(get_current_user)`)
  - Requires the request body to echo the user's email as a confirmation (`{ confirm_email: str }`), matching the pattern the proposal's delete-modal enforces client-side.
  - Deletes the Supabase user via Admin API, **and** cascades cleanup in the app's own tables: documents owned by the user, links, groups, org memberships (or org itself if sole owner — needs a product decision on whether sole-owned orgs block deletion or transfer/delete, same class of decision `ORG-001`'s existing cascade-warning modal already signals the team cares about).
  - This is the riskiest part of the feature — recommend an audit-log entry (`account.deleted`) and possibly a soft-delete/grace-period instead of immediate hard delete, given the blast radius (documents, share links, org data). Flagging as a decision point, not deciding it here.

## 4. Database impact

- **No new tables required** for password change — identity is fully delegated to Supabase Auth today (confirmed: no local `User`/`users` table exists in `backend/app/models/`), so password change is a pure Supabase Admin API call, same shape as the existing `register` flow in `auth.py`.
- **Account deletion** touches existing tables transitively (documents, links, groups, org memberships — all already keyed on `user_id`), no schema change needed, but the cascade logic needs careful review (see §3) since several of those tables likely aren't set up for hard-delete-on-user-removal today and this needs verification against current FK/cascade config before implementation — not assumed here.

## 5. Permissions

- Both endpoints require the caller to be the authenticated user acting on their own account — no cross-user capability, no admin-override needed for change-password. Standard `Depends(get_current_user)`, no new scope/role needed.
- Account deletion should probably be blocked (or require an extra step) if the user is the sole owner of an organization with other members — needs a product decision before implementation (see §3), not just an engineering one.

## 6. Implementation estimate

| Piece | Estimate |
|---|---|
| Backend: change-password endpoint + re-auth check + tests | 0.5–1 day |
| Backend: delete-account endpoint + cascade logic + tests (larger due to the cascade-decision needed first) | 1–2 days |
| Frontend: new `ProfileScreen.jsx` + nav entry + wiring | 0.5–1 day |
| Product decision on org-ownership-transfer-on-delete | Blocking, not an engineering estimate |
| **Total** | **~2–4 engineering days**, gated on one product decision |

## 7. Recommendation

Password change is low-risk and should be picked up as a standalone small feature soon — it's a real, common-sense gap. Account deletion is higher-risk (cascading data loss, org-ownership edge cases) and deserves its own product conversation before an engineer starts on it, independent of this remediation sprint's timeline.
