# Credential Verification Report
Sprint 4.5A — Production Blocker Elimination
Date: 2026-06-22
Phase: 5 of 7
Method: Direct source reading of TRACEVIEW_AUDIT_B.md, SecureDoc.html (current), and git history.

---

## Credential Found

**Key:** `sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc`
**Project URL:** `https://zznenaqcvzxtqxzilpyh.supabase.co`
**Source file:** `TRACEVIEW_AUDIT_B.md` lines 361–362 (documentation/audit file)
**Git history:** Appears in `frontend/SecureDoc.html` in commit `ffac077` ("Phase1: SecureDoc architecture")

---

## Verification Findings

### Finding 1 — Key Type

**The `sb_publishable_` prefix identifies this as a Supabase anon/public key.**

Supabase issues two client-side key types:
- `sb_publishable_*` — the anon key, designed to be embedded in client HTML and JavaScript. It is safe to expose publicly.
- `sb_secret_*` — the service role key, must never be public.

The key in question uses the `sb_publishable_` prefix. This confirms it is an **anon key** — the same type of key every Supabase application embeds in its frontend HTML. It is not a secret.

**Status: PUBLIC KEY — Not a secret. No rotation required.**

### Finding 2 — Current State of SecureDoc.html

Verified by reading `frontend/SecureDoc.html` lines 8–9:

```html
<meta name="supabase-url" content="SECUREDOC_SUPABASE_URL" />
<meta name="supabase-anon-key" content="SECUREDOC_SUPABASE_ANON_KEY" />
```

The live file uses template placeholders, not literal values. The actual key is injected at runtime via environment variables.

**The credential was removed from the production codebase in commit `704ca80` ("Phase B security remediation"). This cleanup already occurred.**

### Finding 3 — Git History Exposure

The literal key value is present in exactly **one historical commit**: `ffac077` ("Phase1: SecureDoc architecture") — the initial commit.

Commits `704ca80` and `cc50838` (previously flagged in the governance audit) already contain the placeholder values, not the literal key. The prior audit may have flagged these commits by their surrounding context rather than verifying their actual content.

**Timeline:**
| Commit | Content |
|---|---|
| `ffac077` (initial) | `sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc` — literal key |
| `704ca80` (Phase B) | `SECUREDOC_SUPABASE_URL` / `SECUREDOC_SUPABASE_ANON_KEY` — placeholders |
| `cc50838` (Phase E1) | `SECUREDOC_SUPABASE_URL` / `SECUREDOC_SUPABASE_ANON_KEY` — placeholders |
| Current HEAD | Placeholders only |

### Finding 4 — Other Credentials in Repository

Cross-checked all other credentials identified in TRACEVIEW_AUDIT_B.md:

| Credential | Location | In Git? | Status |
|---|---|---|---|
| Stripe secret key | `.env` | No (`.gitignore`) | SAFE ✅ |
| Stripe webhook secret | `.env` | No (`.gitignore`) | SAFE ✅ |
| JWT secret | `.env` | No (`.gitignore`) | SAFE ✅ |
| Redis password | `.env` | No (`.gitignore`) | SAFE ✅ |
| Supabase anon key | `ffac077` (historical) | Yes (historical) | PUBLIC KEY — Not secret |
| Supabase service role key | Nowhere found | No | SAFE ✅ |
| IP hash salt | `.env` | No (`.gitignore`) | SAFE ✅ |

**No secret credentials are exposed in git history or in the current codebase.**

---

## B-02 Severity Reclassification

**Previous severity in Sprint 4.4 governance audit:** P0 CRITICAL

**Revised severity after verification: MEDIUM (RESOLVED)**

**Rationale:**
1. The key is a public anon key, designed by Supabase to be client-facing and non-secret
2. The live `SecureDoc.html` already uses placeholders (remediated in `704ca80`)
3. The historical commit exposes only the anon key — no service role keys, no Stripe secrets, no JWT secrets
4. Security risk from a public anon key depends entirely on Supabase RLS configuration, not on the key value itself

**TRACEVIEW_AUDIT_B.md itself** (the file that prompted the P0 classification) states at line 365: *"The Supabase anon key is designed to be public (client-facing) and the `sb_publishable_` prefix confirms this."* It rated this MEDIUM, not P0, at lines 607 and 687.

The P0 classification in the Sprint 4.4 governance report was a mistake — it did not account for the key type.

---

## Remaining Recommendations (Not Blockers)

### Recommendation 1 — Git History Purge (LOW priority)

The anon key in commit `ffac077` is not a secret, but purging it from history eliminates the appearance of a credential leak in future audits. This is hygiene, not emergency.

When to do: During a planned maintenance window, not as a production blocker.

**How (when ready):**
```bash
# Using BFG Repo Cleaner (safer than git filter-branch):
# bfg --replace-text secrets.txt repo.git
# Or git filter-branch targeting ffac077 specifically
# Requires force-push and team re-clone
```

### Recommendation 2 — Supabase RLS Audit (MEDIUM priority)

The protection against anon key misuse is Supabase's Row Level Security (RLS) policies. Verify:
- No Supabase tables are publicly readable/writable without a valid Supabase JWT
- The anon key cannot be used to enumerate users or bypass auth
- The SecureDoc API's server-side JWT verification (via JWKS) is the real auth boundary

This is a Supabase project configuration review, not a code change.

### Recommendation 3 — Remove TRACEVIEW_AUDIT_B.md Reference (LOW priority)

`TRACEVIEW_AUDIT_B.md` quotes the literal anon key at line 362 as part of its documentation. Future automated secret scanners (GitHub, GitGuardian) may flag this. Redacting the key value from the audit file would prevent false positives.

---

## Summary

| Item | Status |
|---|---|
| Key type | Public anon key (sb_publishable_ prefix) |
| Key active? | UNKNOWN — Supabase project may still be active |
| Live codebase | Placeholders only — credential not present |
| Git history | Present in ffac077 (initial commit) only |
| Rotation required? | NO — public key, not secret |
| B-02 certification status | **RESOLVED — not a production blocker** |
| Remaining action | Git history purge (hygiene, low priority) |
