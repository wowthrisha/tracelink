# SecureDoc — Secret Rotation Runbook

**Date:** 2026-06-08  
**Applies to:** Exposed Supabase anon key (commits `ffac077`, `704ca80`, `cc50838` + former HEAD of `TRACEVIEW_AUDIT_B.md`)  
**Severity:** Treat as compromised — key was publicly readable in `wowthrisha/tracelink` (public repo)

---

## Step 1 — Rotate the Supabase Anon Key (required, do first)

Rotating the key renders the exposed value useless immediately, even before history scrub.

1. Open [supabase.com/dashboard](https://supabase.com/dashboard) → Project `zznenaqcvzxtqxzilpyh`
2. Go to **Project Settings → API**
3. Under **Project API keys**, click **Reset** next to `anon` / `public`
4. Confirm the reset — Supabase generates a new `anon` key and invalidates the old one instantly
5. Copy the new `anon` key

---

## Step 2 — Update Railway Environment Variables

1. Open [railway.app](https://railway.app) → Project → Service (API)
2. Go to **Variables**
3. Update `SUPABASE_ANON_KEY` to the new value from Step 1
4. Redeploy the service (Railway auto-redeploys on variable change)

---

## Step 3 — Update `frontend/SecureDoc.html` Meta Tag

The frontend reads the anon key from a `<meta name="supabase-anon-key">` tag. In production this is served by the backend, which injects env values.

Verify your backend template / static file serves the new key:

```bash
# On the deployed Railway instance, confirm the key is updated:
curl https://secure.wowmyspace.com/ | grep supabase-anon-key
# Should show the new key, not the old sb_publishable_uT... value
```

If the key is hardcoded in `frontend/SecureDoc.html` (local dev copy), update it there too.

---

## Step 4 — Remove `TRACEVIEW_AUDIT_B.md` from Git Tracking

```bash
# Already executed — confirmed with git status:
git rm --cached TRACEVIEW_AUDIT_B.md
# TRACEVIEW_AUDIT_B.md is now in .gitignore
```

Commit this change:

```bash
git add .gitignore
git commit -m "Remove TRACEVIEW_AUDIT_B.md from tracking; add to .gitignore"
```

---

## Step 5 — Optional: Scrub Git History

> **Warning:** This rewrites history. All forks and clones will diverge. Only proceed if you control all clones and the repo has no active PRs.

Install `git-filter-repo` (preferred over BFG):

```bash
pip install git-filter-repo
```

Remove the file from all history:

```bash
git filter-repo --path TRACEVIEW_AUDIT_B.md --invert-paths --force
```

Force-push all branches and tags:

```bash
git push origin --force --all
git push origin --force --tags
```

Notify any collaborators to `git clone` fresh — their local copies still have the old commits.

---

## Step 6 — Verify the Old Key No Longer Works

After rotating (Step 1), confirm the old key is rejected:

```bash
# Replace OLD_KEY with the revoked value — expect 401
curl -H "apikey: OLD_KEY" \
     "https://zznenaqcvzxtqxzilpyh.supabase.co/auth/v1/settings"
# Expected response: {"code": 401, "error": "invalid_api_key", ...}
```

---

## Checklist

- [ ] Supabase anon key rotated via dashboard
- [ ] Railway `SUPABASE_ANON_KEY` updated + service redeployed
- [ ] Frontend serving new key (verified via `curl`)
- [ ] `TRACEVIEW_AUDIT_B.md` removed from git tracking (committed)
- [ ] Old key confirmed invalid
- [ ] (Optional) Git history scrubbed + force-pushed

---

## What Was Exposed

| Secret | Type | Status |
|--------|------|--------|
| Supabase project URL `https://zznenaqcvzxtqxzilpyh.supabase.co` | Non-secret (project identifier, safe to know) | No rotation needed |
| Supabase anon key (`sb_publishable_...`) | Client-facing public key — low risk but rotatable | **Rotate** |
| JWT secret / service-role key | **Not exposed** — was never in the repository | No action needed |
| Storage credentials | **Not exposed** — only in Railway env vars | No action needed |

The Supabase `anon` key is designed to be browser-visible (it gates only RLS policies, not the database itself). However: (a) rotating it is free and instant; (b) in this project the RLS policies may not be fully configured, making the exposure higher risk than typical.
