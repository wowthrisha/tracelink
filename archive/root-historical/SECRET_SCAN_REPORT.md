# SecureDoc — Secret Scan Report

**Date:** 2026-06-08  
**Scan scope:** Full repository tree (`/Users/thrisha/traceview/securedoc/`)  
**Method:** Recursive grep for known credential patterns + project-URL strings

---

## Summary

| Result | Count |
|--------|-------|
| Live credentials found in tracked files | **1** (remediated) |
| Live credentials in git history | **3 commits** (rotation required) |
| Credential references in test code | 1 (assertion only — no credential value stored) |
| False positives / documentation references | 1 (redacted) |

---

## Findings

### CRITICAL — Remediated (P0-2 / P0-3)

**File:** `TRACEVIEW_AUDIT_B.md` (lines 361–362)  
**Credential type:** Supabase project URL + anon key  
**Pattern matched:** `zznenaqcvzxtqxzilpyh.supabase.co`, `sb_publishable_` prefix  
**Status:** `git rm --cached TRACEVIEW_AUDIT_B.md` executed; file added to `.gitignore`  
**History exposure:** Commits `ffac077`, `704ca80`, `cc50838` — key present in git history  
**Action required:** Rotate Supabase anon key via dashboard (see `SECRET_ROTATION_RUNBOOK.md`)

---

### Low — Test Assertion (no credential stored)

**File:** `backend/tests/integration/test_phase_b_security.py` (line 369)  
**Content:** `assert "zznenaqcvzxtqxzilpyh" not in env_example`  
**Assessment:** This is a project-URL string used in a negative assertion to confirm the credential is absent from `.env.example`. No credential value is stored or tested against. No action required.

---

### Low — Documentation Reference (redacted)

**File:** `RELEASE_BLOCKERS.md` (line 13, original)  
**Content:** P0-2 description previously quoted the anon key verbatim as context.  
**Action taken:** Key value redacted; description preserved.

---

## Scan Coverage

Files scanned for patterns `sb_publishable_`, `zznenaqcvzxtqxzilpyh`, `supabase.co`:

| File type | Result |
|-----------|--------|
| `*.py` | 1 test assertion (no value) |
| `*.js`, `*.jsx` | Clean — no hardcoded credentials; meta-tag pattern reads from DOM at runtime |
| `*.html` | Clean — `SecureDoc.html` has empty `supabase-url`/`supabase-anon-key` meta tags (values injected via Railway env vars) |
| `*.env*` | `.env.example` clean — placeholder text only |
| `*.yml`, `*.yaml` | Clean |
| `*.json` | Clean |
| `*.md` | `TRACEVIEW_AUDIT_B.md` — remediated; `RELEASE_BLOCKERS.md` — redacted |
| `docker-compose.yml` | Clean — reads from `.env` file, no hardcoded values |

---

## Residual Risk

The key value remains accessible via `git log` / `git show` on the public repository `wowthrisha/tracelink` until one of:
1. **Key is rotated** (renders the leaked value useless — preferred immediate action)
2. **History is scrubbed** via `git filter-repo` + force-push (destructive; coordinate with any forks/clones)

See `SECRET_ROTATION_RUNBOOK.md` for step-by-step rotation and optional history scrub procedures.
