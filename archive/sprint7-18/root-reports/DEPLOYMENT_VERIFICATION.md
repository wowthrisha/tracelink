# Deployment Verification — JWKS outage fix

## Local verification — DONE

- `backend/tests/integration/test_jwks_outage.py` drives the real FastAPI
  app (real routing, real `Depends` chain, real `list_documents` query
  logic) through an in-process ASGI transport — this is a genuine end-to-end
  HTTP request/response cycle, not a mock of the endpoint itself. With a
  simulated Supabase outage it now returns `503` with a clean body; with a
  warm cache it returns `200` and never touches the network. Both pass.
- Full existing suite re-run after the change: `1699 passed, 1 skipped` —
  identical pass count to the pre-fix baseline, confirming no regressions.
- Command: `cd backend && PYTHONPATH=. python -m pytest tests/ -q`

## Production verification — BLOCKED, not done

Two things are required to close this out that are outside what I can do
from here, and neither is a code change:

1. **Restore the Supabase project.** `zznenaqcvzxtqxzilpyh.supabase.co`
   still fails DNS resolution as of this writing (`NXDOMAIN` on both 1.1.1.1
   and 8.8.8.8, re-checked at verification time). This needs your Supabase
   dashboard access:
   - If the project shows as **paused** (common on free tier after ~1 week
     idle): resume it. DNS should return within minutes.
   - If the project is **gone**: recreate it, then update `SUPABASE_URL`,
     `SUPABASE_ANON_KEY`, and (if storage was on the same project)
     `STORAGE_ENDPOINT_URL` in Railway's environment variables, and restart
     the service.

2. **Deploy this code fix to Railway and confirm.** The Railway CLI in this
   environment is not authenticated (`railway whoami` fails with
   `invalid_grant` / token expired), so I cannot push, redeploy, or query
   the live service's logs directly. You (or a session with valid Railway
   credentials) needs to:
   ```
   railway login
   railway up          # or: git push, if deploys are triggered from a connected repo
   ```

## What I confirmed live, without credentials

```
$ curl -s -o /dev/null -w "%{http_code}" https://wowmyspace--tracelink.up.railway.app/app
200                                                    # app itself is serving

$ curl -s https://wowmyspace--tracelink.up.railway.app/api/documents
{"detail":"Authorization header missing"}   HTTP 401   # expected — no token supplied,
                                                        # request never reaches the JWKS
                                                        # fetch, so this alone doesn't
                                                        # reproduce the reported 500
```

I don't have a valid login token for the production instance, so I could not
personally reproduce the live `500` end-to-end against Railway — the
reproduction in this fix is the local integration test, which simulates the
identical failure (Supabase JWKS unreachable) against the real application
code.

## Closing checklist

- [x] Root cause traced and documented (`ROOT_CAUSE_ANALYSIS.md`)
- [x] Code fix implemented (`FIX_IMPLEMENTATION.md`)
- [x] Regression tests added and passing locally (`REGRESSION_REPORT.md`)
- [x] Full local suite green, no regressions
- [ ] Supabase project resumed/recreated — **needs your action**
- [ ] Fix deployed to Railway — **needs `railway login` with valid
      credentials, then a deploy**
- [ ] `GET /api/documents` returns `200` in production with a real user
      token — **cannot be confirmed until the two items above are done**

Once the Supabase project is back and this fix is deployed, send me the
result of:
```
curl -i https://wowmyspace--tracelink.up.railway.app/api/documents \
  -H "Authorization: Bearer <a real access token from a signed-in session>"
```
and I'll confirm the `200`/`503` behavior matches expectations, or keep
digging if it doesn't.
