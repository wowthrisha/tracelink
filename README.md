# SecureDoc

Secure document sharing platform with per-link access control, viewer analytics, and Supabase authentication.

---

## Architecture

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy async + Celery |
| Database | PostgreSQL (prod) / SQLite (tests) |
| Storage | Supabase Storage (S3-compatible) |
| Auth | Supabase (JWKS / ES256 JWT) |
| Task queue | Celery + Redis |
| Frontend | Single-file React + Babel (`frontend/SecureDoc.html`) |

---

## Development Setup

### 1. Prerequisites

- Python 3.12+
- PostgreSQL running locally (or use Docker)
- Redis running locally
- Supabase project (free tier is fine)

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
# Install Poppler for PDF rasterization:
# macOS:  brew install poppler
# Ubuntu: apt-get install poppler-utils
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in every value — see "Required env vars" below
```

### 4. Run database migrations

```bash
cd backend
alembic upgrade head
```

### 5. Start the stack

```bash
# Terminal 1 — Backend (FastAPI on :8000)
./start.sh backend

# Terminal 2 — PDF worker (Celery)
./start.sh worker
```

Or start the backend directly:
```bash
cd backend
USE_DEMO_STORAGE=1 python run_demo.py   # local disk storage (no Supabase needed)
```

Backend: `http://localhost:8000` · API docs: `http://localhost:8000/docs`

### 6. Serve the frontend

The backend auto-serves the frontend at `http://localhost:8000/` via StaticFiles.

For live frontend development:
```bash
cd frontend && python3 -m http.server 5500
# Open http://localhost:5500/SecureDoc.html
```

### 7. Run tests

```bash
cd backend && PYTHONPATH=. pytest tests/ -q
# Expected: 149 passed, 0 failed
```

---

## Globally Shareable Links — Cloudflare Quick Tunnel

SecureDoc generates share links using `APP_PUBLIC_BASE_URL`. Run a Cloudflare Quick Tunnel to get a public HTTPS URL in seconds — **no card, no DNS changes, no cert.pem, no `cloudflared login`**.

> **Note on custom domains:** `wowmyspace.com` is currently on GoDaddy/Wix and not yet connected to Cloudflare DNS. Until DNS is migrated, use a Quick Tunnel (temporary `trycloudflare.com` URL). The app is fully ready for the custom domain — just update `APP_PUBLIC_BASE_URL` when the time comes.

### How it works

```
Viewer's browser
    → https://abc123.trycloudflare.com/v/{token}
    → Cloudflare edge  (no DNS setup needed — trycloudflare.com is Cloudflare's domain)
    → Cloudflare Quick Tunnel  (free, ephemeral, no login)
    → localhost:8000  (your FastAPI backend)
    → /v/{token} → /static/SecureDoc.html?token={token}
```

### Quick tunnel setup (~30 seconds)

**Step 1 — Install cloudflared** (if not already)

```bash
brew install cloudflared
```

**Step 2 — Start the tunnel** (Terminal 3)

```bash
./start.sh quicktunnel
```

This starts `cloudflared tunnel --url http://localhost:8000`, detects the public URL from the output, and **automatically updates `backend/.env`**. Output looks like:

```
  cloudflared | Your quick Tunnel has been created!
  cloudflared | https://random-words-123.trycloudflare.com
  ────────────────────────────────────────────────────────
  Public URL detected and saved to backend/.env:

    https://random-words-123.trycloudflare.com

  Share links will now be:  https://random-words-123.trycloudflare.com/v/<token>

  Next step — restart the backend to apply:
    ./start.sh backend
  ────────────────────────────────────────────────────────
```

**Step 3 — Restart the backend** (Terminal 1)

```bash
# Ctrl+C the backend if it's running, then:
./start.sh backend
```

The backend now generates links like:
```
https://random-words-123.trycloudflare.com/v/{token}
```

**Step 4 — Verify**

```bash
./start.sh check
# Shows: Mode: Cloudflare Quick Tunnel (globally shareable)
```

### Manual URL update (if auto-detect fails)

If the auto-detect misses the URL, copy it from the cloudflared output and run:

```bash
./start.sh set-url https://your-words.trycloudflare.com
./start.sh backend
```

### How share links are generated

`APP_PUBLIC_BASE_URL` in `backend/.env` is the **single source of truth** for all share link URLs:

```
share link = {APP_PUBLIC_BASE_URL}/v/{token}
```

| Mode | APP_PUBLIC_BASE_URL |
|---|---|
| Local dev only | `http://localhost:8000` |
| Quick tunnel (temp) | `https://random-words.trycloudflare.com` (auto-set) |
| Custom domain (future) | `https://secure.wowmyspace.com` |

### Frontend API routing

`frontend/api.js` auto-detects the environment — no source changes needed:

| Where the page loads | API calls go to |
|---|---|
| `localhost:5500` (dev server) | `http://localhost:8000` (detected by port) |
| `*.trycloudflare.com` (quick tunnel) | same origin (relative `/api/...`) |
| `secure.wowmyspace.com` (custom domain) | same origin |

### Known limitations of quick tunnels

- The URL **changes every time** cloudflared restarts — existing share links using the old URL will stop working.
- The tunnel must stay running for viewers to access documents.
- For stable links, use a named tunnel with a custom domain (see below).

---

## Required Environment Variables

Copy `.env.example` to `.env` and fill in every value.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `STORAGE_ENDPOINT_URL` | Yes | Supabase Storage S3 endpoint |
| `STORAGE_ACCESS_KEY_ID` | Yes | Supabase Storage access key |
| `STORAGE_SECRET_ACCESS_KEY` | Yes | Supabase Storage secret key (service role) |
| `STORAGE_BUCKET_NAME` | Yes | S3 bucket name (default: `securedoc-docs`) |
| `JWT_SECRET` | Yes | Random secret for internal share-link tokens |
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Supabase publishable anon key |
| `APP_PUBLIC_BASE_URL` | Yes | Root URL for all generated share links |
| `ALLOWED_ORIGINS` | Yes | Comma-separated CORS origins |
| `APP_ENV` | No | `development` (default) or `production` |
| `CLOUDFLARE_TUNNEL_TOKEN` | No | Token from Zero Trust dashboard (for tunnel mode) |

### Generate JWT_SECRET

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Get Supabase Storage credentials

1. Go to Supabase dashboard → Storage → S3 Connection
2. Copy the endpoint URL, access key ID, and secret
3. Create a bucket named `securedoc-docs` (set to private)

---

## Deployment

### Option A — Cloudflare Quick Tunnel (current recommended path)

Run the backend locally and expose it globally. No server, no card, no DNS changes.
See the **Globally Shareable Links** section for the full walkthrough.

```bash
./start.sh quicktunnel   # auto-sets APP_PUBLIC_BASE_URL in .env
./start.sh backend       # restart to apply
```

### Option A2 — Cloudflare Named Tunnel (when domain is on Cloudflare)

Use this once `wowmyspace.com` DNS is migrated to Cloudflare:

```
APP_PUBLIC_BASE_URL=https://secure.wowmyspace.com
CLOUDFLARE_TUNNEL_TOKEN=<from Zero Trust dashboard>
```

```bash
./start.sh tunnel
```

### Option B — Cloud server (Railway / Fly / VPS)

1. Deploy `backend/` to your hosting provider
2. Set start command: `python run_demo.py`
3. Add all env vars with production values
4. Set `APP_ENV=production`
5. Set `APP_PUBLIC_BASE_URL` to your server's public URL

```
APP_ENV=production
APP_PUBLIC_BASE_URL=https://your-server-domain.com
FRONTEND_BASE_URL=https://your-server-domain.com
ALLOWED_ORIGINS=https://your-server-domain.com
JWT_SECRET=<64-char random hex>
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=<publishable anon key>
STORAGE_ENDPOINT_URL=https://your-project.storage.supabase.co/storage/v1/s3
STORAGE_ACCESS_KEY_ID=<from Supabase Storage S3 settings>
STORAGE_SECRET_ACCESS_KEY=<service role key — NEVER expose to frontend>
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
```

### Frontend — served by backend

The backend serves the frontend from `frontend/` via `/static/`. No separate frontend deployment needed.

If hosting the HTML separately (CDN / GitHub Pages):
- Set `<meta name="api-base" content="https://your-backend-url.com">` in `SecureDoc.html`
- Set `<meta name="supabase-url">` and `<meta name="supabase-anon-key">` accordingly

---

## Security Notes

- **Never commit `.env`** — it contains real credentials. `.gitignore` protects it.
- **`JWT_SECRET` must be generated manually** — it signs internal share-link tokens. A weak or guessable secret allows token forgery.
- **`STORAGE_SECRET_ACCESS_KEY` is the Supabase service role key** — it has full storage access. Never expose it to the browser or include it in frontend code.
- **`SUPABASE_ANON_KEY` is safe for the frontend** — it is the publishable key and is already in `SecureDoc.html`.
- Auth tokens are verified via Supabase JWKS (public key, no shared secret). The backend fetches public keys at startup and caches them for 1 hour.
- All page images are served through the backend proxy — direct S3 URLs are never exposed to viewers.
