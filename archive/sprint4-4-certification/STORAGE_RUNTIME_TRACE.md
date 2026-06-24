# Storage Screen Runtime Trace — Sprint 4.6D
Date: 2026-06-22
Status: Root cause confirmed. Fix applied.
Symptom: "Failed to construct 'URL': Invalid URL" + "undefined docs" in production after commit 77598f8.

---

## Summary

Commit 77598f8 correctly fixed `api.js`. The source code and the committed bundle are both correct.
Production still shows the error because `api.js` is served as a static file with a 1-hour browser cache
and has NO URL cache-busting, unlike `app.bundle.js`. Browsers served the old `api.js` (with `new URL()`)
from cache for up to 3600 seconds after the deploy.

The fix in this sprint adds mtime-based cache-busting for `api.js` in `serve_app()`, matching the
existing pattern for `app.bundle.js`.

---

## Task 1 — Every Occurrence of Searched Patterns

### `new URL(`

| File | Line | Content |
|---|---|---|
| `frontend/api.js` | None | **Zero occurrences** — fix from 77598f8 is in source |
| `frontend/dist/app.bundle.js` | 7 | `new URL(c.url)` — URL parsing for webhook SSRF guard |
| `frontend/dist/app.bundle.js` | 7 | `new URL(w)` — URL parsing (unrelated to storage) |

`new URL(` does NOT appear in any storage-related context in the current source or bundle.

### `storage/dashboard`

| File | Line | Content |
|---|---|---|
| `frontend/api.js` | 183 | `` fetch(`${API_BASE}/api/storage/dashboard${qs}`) `` |
| `frontend/dist/app.bundle.js` | — | **NOT FOUND** — bundle uses `getStorageDashboard()` reference to `window.SecureDocAPI`, not inline string |

The bundle calls `window.SecureDocAPI.getStorageDashboard()`. The actual URL string lives in `api.js`, which is a separate static file not bundled into `app.bundle.js`.

### `getStorageDashboard`

| File | Line | Content |
|---|---|---|
| `frontend/api.js` | 181 | Function definition (FIXED — no `new URL()`) |
| `frontend/src/screens/StorageScreen.jsx` | 39 | `window.SecureDocAPI.getStorageDashboard()` call |
| `frontend/src/screens/StorageScreen.jsx` | 50 | `window.SecureDocAPI.getStorageDashboard()` (after retention update) |
| `frontend/dist/app.bundle.js` | 7 | `window.SecureDocAPI.getStorageDashboard()` — bundle calls through window |

### `StorageScreen`

| File | Line | Content |
|---|---|---|
| `frontend/src/screens/StorageScreen.jsx` | 30 | `export function StorageScreen()` |
| `frontend/dist/app.bundle.js` | 7 | Bundled component (references `window.SecureDocAPI`) |

---

## Task 2 — Exact Execution Path When Storage Screen Loads

```
Browser requests GET /app
  └── serve_app() in backend/app/main.py:432
        ├── reads SecureDoc.html from frontend_dir
        ├── injects Supabase credentials
        ├── cache-busts app.bundle.js: src="/static/dist/app.bundle.js?v={mtime}"
        └── returns HTML with Cache-Control: no-cache, must-revalidate

Browser parses HTML
  ├── <script src="/static/api.js">               ← NO version parameter
  │     StaticFiles mount → security_headers.py:85-89
  │     Response: Cache-Control: public, max-age=3600, stale-while-revalidate=60
  │     → Browser may serve STALE api.js from cache for up to 3600s
  │
  └── <script src="/static/dist/app.bundle.js?v=1750609980">
        URL has version parameter → browser/CDN always fetches fresh copy

React mounts → AppShell → user clicks Storage → StorageScreen mounts

StorageScreen.jsx:37-44 useEffect fires:
  Promise.all([
    window.SecureDocAPI.getStorageDashboard(),   ← calls api.js function
    window.SecureDocAPI.getStorageForecast(),
  ])

If api.js is STALE (old cached version from before 77598f8):
  getStorageDashboard() at old api.js:182:
    const url = new URL(`${API_BASE}/api/storage/dashboard`)
                         ^ API_BASE = '' in production
                         ^ new URL('/api/storage/dashboard') throws synchronously
  TypeError: Failed to construct 'URL': Invalid URL
  → Promise.all rejects
  → .catch fires: toast("Failed to construct 'URL': Invalid URL", 'error')
  → dashboard stays null, forecast stays null
  → "0 B · 0 documents" header (|| 0 fallback)
  → "undefined docs" summary card (no fallback in old code)
  → empty document table

If api.js is FRESH (new version from 77598f8):
  getStorageDashboard() at api.js:181-187:
    const qs = orgId ? `?org_id=${encodeURIComponent(orgId)}` : ''
    fetch(`${API_BASE}/api/storage/dashboard${qs}`, ...)
         ^ fetch('/api/storage/dashboard', ...) ← works correctly
  → 200 OK → dashboard loaded → screen renders correctly
```

---

## Task 3 — API Calls and URL Constructors

### First API call executed
`window.SecureDocAPI.getStorageDashboard()` — fired by `Promise.all` in `StorageScreen.jsx:38-40`

### All API calls executed on storage screen mount
1. `getStorageDashboard()` → `fetch('/api/storage/dashboard')` (or absolute URL in local dev)
2. `getStorageForecast()` → `fetch('/api/storage/forecast')`

### URL constructors
- Current source `api.js`: **zero `new URL()` calls** for storage
- Old cached `api.js` (before 77598f8): `new URL('/api/storage/dashboard')` at line 182

---

## Task 4 — Diagnostic Conclusions

### Was commit 77598f8 fixing the active code path?

**YES for source. NO for browser execution.**

`api.js` was correctly patched. The file on disk and in the Railway Docker image is correct. However, `api.js` is served as `/static/api.js` with no URL cache-busting. After deploy, any browser that had loaded the page within 3600 seconds continued to execute the old `api.js` from its HTTP cache.

### Is `frontend/dist/app.bundle.js` updated?

**YES.** Committed in 77598f8 (mtime Jun 22 22:23). The bundle calls `window.SecureDocAPI.getStorageDashboard()` — it does not contain the storage URL string directly.

### Is Railway serving the latest bundle?

**YES.** The bundle URL includes `?v={mtime}` injected by `serve_app()`. After deploy, the HTML returns a new versioned URL. Browsers and CDNs fetch the fresh bundle.

### Is `api.js` cache-busted?

**NO. This is the root cause.**

`api.js` URL in `SecureDoc.html`: `src="/static/api.js"` — static, unversioned.
`serve_app()` in `main.py` only cache-busts `app.bundle.js`, not `api.js`.
`SecurityHeadersMiddleware` adds `Cache-Control: public, max-age=3600, stale-while-revalidate=60` to all `.js` files under `/static/`.
Result: `api.js` is cached for 1 hour. A deploy does not invalidate it.

---

## Task 5 — Exact Runtime Error

```
TypeError: Failed to construct 'URL': Invalid URL
    at new URL (native)
    at Object.getStorageDashboard (api.js:182)       ← old cached version
    at StorageScreen.jsx:39  [Promise.all invocation]
    at StorageScreen.jsx:37  [useEffect callback]

Caught by: StorageScreen.jsx:42
  .catch(e => toast(_errMsg(e, 'Failed to load storage data'), 'error'))

_errMsg(e) path: e is TypeError, e.detail is undefined → falls back to e.message
e.message = "Failed to construct 'URL': Invalid URL"
Toast text = "Failed to construct 'URL': Invalid URL"
```

Secondary symptom: dashboard state remains `null`.
- `StorageScreen.jsx:66`: `dashboard?.document_count || 0` → "0 documents" (has fallback)
- `StorageScreen.jsx:74`: `${dashboard?.document_count ?? 0} docs` → "0 docs" (fixed in 77598f8)
- Old code before 77598f8: `${dashboard?.document_count} docs` → "undefined docs"

---

## Task 6 — Root Cause Statement

**File**: `backend/app/main.py`
**Function**: `serve_app()` at line 432
**Missing code**: cache-busting for `/static/api.js` URL

**File**: `frontend/SecureDoc.html`
**Line**: 23
**Content**: `<script src="/static/api.js"></script>` — no version parameter

**Cache path**:
```
SecurityHeadersMiddleware.dispatch()
  backend/app/middleware/security_headers.py:82-89
  path.endswith('.js') → True
  Cache-Control: public, max-age=3600, stale-while-revalidate=60
```

**api.js cache-busting gap vs bundle**:
```
app.bundle.js → serve_app() replaces src with ?v={mtime}  → always fresh after deploy
api.js        → no replacement, static URL                 → stale for up to 3600s
```

**Fix**: Add the same mtime-based URL versioning to `api.js` in `serve_app()`.

---

## Fix

### File: `backend/app/main.py` (modified)

Added after the bundle cache-busting block (after line 465):

```python
# Cache-bust api.js with the same mtime strategy used for the bundle.
# Without this, browsers serve a stale api.js for up to static_asset_max_age
# seconds after a deploy, because the URL never changes.
api_js_path = os.path.join(frontend_dir, "api.js")
try:
    api_js_mtime = int(os.path.getmtime(api_js_path))
except OSError:
    api_js_mtime = 0
content = content.replace(
    'src="/static/api.js"',
    f'src="/static/api.js?v={api_js_mtime}"',
)
```

This change:
1. Reads the mtime of `api.js` from disk (same as the bundle pattern)
2. Replaces the bare `src="/static/api.js"` with a versioned URL in the served HTML
3. On every new deploy where `api.js` changes, the URL changes → browsers and CDNs fetch the fresh file
4. When `api.js` has NOT changed, mtime is identical → browsers serve from cache (correct behavior)

---

## Verification

| Check | Result |
|---|---|
| `new URL(` in `frontend/api.js` | Zero occurrences |
| `new URL(` near storage in bundle | Zero occurrences |
| `serve_app()` cache-busts `api.js` | Yes — after this fix |
| `serve_app()` cache-busts `app.bundle.js` | Yes — unchanged |
| `npm run build` | `dist/app.bundle.js 202.5kb` ✅ |
| `npm test` | 13/13 passed ✅ |
