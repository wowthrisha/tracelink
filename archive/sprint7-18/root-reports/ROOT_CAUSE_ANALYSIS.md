# Root Cause Analysis — `GET /api/documents` returns HTTP 500

**Incident**: Railway production deployment fails immediately after login;
`GET /api/documents` returns `HTTP 500` with traceback `httpcore.ConnectError:
Name or service not known`.

**Status**: Root cause confirmed. Code-level fix implemented and tested
(see `FIX_IMPLEMENTATION.md`). Underlying infrastructure (Supabase project
DNS) is **not yet restored** — see `DEPLOYMENT_VERIFICATION.md`.

---

## 1. Execution path of `GET /api/documents`

```
GET /api/documents
  └─ FastAPI routing → app/routers/documents.py:list_documents
       ├─ Depends(require_scope("documents:read"))   [app/auth.py]
       │    └─ Depends(get_current_user)
       │         └─ verify_supabase_token(token)
       │              └─ _get_public_key(kid)
       │                   └─ _fetch_jwks()             ← OUTBOUND CALL
       │                        GET {SUPABASE_URL}/auth/v1/.well-known/jwks.json
       ├─ Depends(get_db)                              [app/database.py]
       │    └─ AsyncSession over DATABASE_URL (asyncpg) — no outbound HTTP
       └─ list_documents() body
            ├─ SELECT OrgMembership WHERE user_id = ...
            ├─ SELECT Document WHERE user_id = ... OR org_id IN (...)
            ├─ SELECT ShareLink COUNT ... GROUP BY document_id
            ├─ SELECT ShareLink JOIN AccessEvent COUNT ... GROUP BY document_id
            └─ SELECT DocumentGroup WHERE id IN (...)
```

## 2. Every outbound network call in this request

| # | Call | Library | Triggered by | Verdict |
|---|------|---------|---------------|---------|
| 1 | `GET {SUPABASE_URL}/auth/v1/.well-known/jwks.json` | `httpx` | `app/auth.py:_fetch_jwks()`, invoked from `_get_public_key()` on every request when the in-process JWKS cache is empty or older than `_JWKS_TTL` (1h) | **This is the failing call** |
| — | Postgres (`DATABASE_URL`) | `asyncpg` via SQLAlchemy | `get_db` dependency + all queries in `list_documents` | Ruled out — different exception family (`asyncpg`/`OSError`, never `httpcore.ConnectError`) |
| — | Redis (`REDIS_URL`) | `redis.asyncio` / `slowapi` | Only used for rate limiting, and only on routes carrying an explicit `@limiter.limit(...)` decorator | Ruled out — `list_documents` has **no** rate-limit decorator; Redis is never touched on this route |
| — | S3 / MinIO (`STORAGE_ENDPOINT_URL`) | `boto3`/`aioboto3` | Only used by upload/download/watermark endpoints | Ruled out — `list_documents` never calls the storage service |
| — | OCR / embeddings / analytics / retention services | n/a | No such services exist in this codebase's request path for this route | Ruled out — not present |
| — | Other internal Railway services | n/a | This is a single-service (API) deployment; no service-to-service calls exist in this path | Ruled out |

`httpcore.ConnectError` is raised exclusively by `httpx`/`httpcore` transports.
Of every dependency in the call graph above, **only the JWKS fetch uses
httpx** — every other component (Postgres, Redis, boto3) raises a different
exception type on connection failure. The exception signature alone
identifies the JWKS fetch as the failure point, independent of the DNS
evidence below.

## 3. The exact failing hostname

```
$ nslookup zznenaqcvzxtqxzilpyh.supabase.co 1.1.1.1
** server can't find zznenaqcvzxtqxzilpyh.supabase.co: NXDOMAIN

$ nslookup zznenaqcvzxtqxzilpyh.supabase.co 8.8.8.8
** server can't find zznenaqcvzxtqxzilpyh.supabase.co: NXDOMAIN
```

Confirmed via two independent public resolvers (Cloudflare and Google) — this
is not a local/sandbox DNS quirk. For comparison, the storage subdomain for
the *same* Supabase project still resolves:

```
$ nslookup zznenaqcvzxtqxzilpyh.storage.supabase.co 8.8.8.8
Name:    zznenaqcvzxtqxzilpyh.storage.supabase.co
Address: 172.64.155.33
Address: 104.18.32.223
```

The pattern (storage subdomain alive, main API/auth gateway subdomain gone)
is consistent with the Supabase project itself having been **paused or
deleted**, not with a typo in configuration — the same project ref
(`zznenaqcvzxtqxzilpyh`) is used consistently everywhere it appears (see §4).

## 4. Environment variables in this request chain — verified

| Variable | Where used | Value observed | Verdict |
|---|---|---|---|
| `SUPABASE_URL` | `app/auth.py:_fetch_jwks`, `app/main.py` (meta tag templating, startup JWKS preload, health checks) | `https://zznenaqcvzxtqxzilpyh.supabase.co` (identical in `backend/.env` and in the live HTML served by the Railway deployment) | **Set correctly, but the hostname it points to no longer resolves.** Not a missing-variable or typo problem — it's an infra-side removal. |
| `SUPABASE_ANON_KEY` | Frontend meta tag / Supabase REST calls from the browser | Present, non-empty | Not implicated — irrelevant to server-side JWKS fetch failure |
| `DATABASE_URL` | `app/database.py` | Present (Railway Postgres) | Not implicated — DB queries never execute because the request fails earlier, in the auth dependency, before `get_db`'s queries run |
| `REDIS_URL` | `app/middleware/rate_limit.py` | Present | Not implicated — never touched on this route (no rate-limit decorator on `list_documents`) |
| `STORAGE_ENDPOINT_URL` | `app/services/storage.py` | Present (Supabase Storage) | Not implicated — never touched on this route |

No variable is **missing**. No variable holds the **wrong value** relative to
what the rest of the system expects (frontend meta tag and backend JWKS
fetch use the identical `SUPABASE_URL`). This rules out "missing variable,"
"wrong hostname configured," "wrong Railway service name," and "incorrect
internal URL" as the cause.

## 5. Classification

| Candidate cause | Verdict |
|---|---|
| Missing environment variable | No — `SUPABASE_URL`/`SUPABASE_ANON_KEY` are both set |
| Wrong hostname in config | No — the configured hostname matches what's used consistently across frontend and backend; it's simply no longer live |
| Wrong Railway service name / internal URL | No — this project has no internal Railway-to-Railway service calls in this path; the only outbound call is to an external Supabase endpoint over the public internet |
| Deleted/paused external service | **Yes — most likely.** `NXDOMAIN` on the main API gateway subdomain while the storage subdomain for the same project still resolves matches a paused/deleted Supabase project |
| Bad DNS configuration on Railway's side | Unlikely — confirmed `NXDOMAIN` from two independent public resolvers outside Railway's network, meaning the domain itself isn't being served anywhere, not a Railway-local resolver problem |
| **Application bug: no error handling around the JWKS network call** | **Yes — this is the code defect that turned an external outage into a hard 500 for every authenticated request, rather than a contained, recoverable failure.** |

Two separate problems compound this incident:

1. **Infrastructure**: the Supabase project backing `SUPABASE_URL` is
   unreachable. This requires action in the Supabase/Railway dashboards and
   is outside what a code change can fix (see `DEPLOYMENT_VERIFICATION.md`).
2. **Code defect**: `_fetch_jwks()` had no error handling, so *any* transient
   or permanent failure reaching Supabase (DNS, timeout, 5xx) crashed every
   JWT-authenticated endpoint in the app with an unhandled 500, with no
   fallback and no informative error. This is fixed — see
   `FIX_IMPLEMENTATION.md`.
