# RC1 RUNTIME REPORT — Sprint 6.2
**Date:** 2026-06-30
**Release:** RC-1 (v8.1.0)

---

## Runtime Environment

| Component | State |
|-----------|-------|
| Backend | Running — PID 49183, localhost:8000 |
| Database | Running — PostgreSQL at localhost:5432, migration at head (025) |
| Redis | Running — localhost:6379 |
| Storage | DemoStorageService (local disk `/tmp/securedoc_storage/`) |
| Frontend bundle | `/static/dist/app.bundle.js` — 249.3 KB |
| Auth | Supabase JWT configured; API key `sd_70mp7y_…` active |

---

## Health Check

`GET /health` → 200 OK

```json
{
  "status": "ok",
  "checks": {
    "db": "ok",
    "redis": "ok",
    "storage": "DemoStorageService",
    "worker": "ok",
    "auth_configured": true,
    "storage_credentials": "configured"
  },
  "version": "8.1.0"
}
```

All subsystems healthy. `worker: "ok"` confirms Celery worker connectivity check passes.

---

## API Endpoint Runtime Verification

Every endpoint used by the frontend was called with a valid `sd_` key and returned the expected HTTP status and content type.

### Documents
| Call | Status | Notes |
|------|--------|-------|
| `GET /api/documents` | 200 | Returns `{documents: [...]}` array |
| `GET /api/documents/{uuid}` | 200 | Returns single document object |
| `GET /api/documents/00000000-…` | 404 | Expected — confirms 404 handling works |

### Analytics
| Call | Status | Notes |
|------|--------|-------|
| `GET /api/analytics/overview` | 200 | Returns `total_views_today`, `total_documents`, etc. |
| `GET /api/analytics/events` | 200 | Returns events array |
| `GET /api/analytics/documents` | 200 | Returns per-document analytics |
| `GET /api/analytics/groups` | 200 | Returns group analytics |

### Links
| Call | Status | Notes |
|------|--------|-------|
| `GET /api/links?document_id=…` | 200 | Returns links array |

### Storage
| Call | Status | Notes |
|------|--------|-------|
| `GET /api/storage/dashboard` | 200 | Used by StorageScreen |
| `GET /api/storage/forecast` | 200 | Used by StorageScreen |
| `GET /api/storage/snapshots` | 404 | Not used by frontend — non-issue |

### Configuration & Admin
| Call | Status | Notes |
|------|--------|-------|
| `GET /api/api-keys` | 200 | Returns `{api_keys: [...]}` |
| `GET /api/webhooks` | 200 | Returns webhooks array |
| `GET /api/orgs` | 200 | Returns orgs array |
| `GET /api/billing/status` | 200 | Returns billing plan info |
| `GET /api/admin/audit-log` | 200 | Returns audit events |
| `GET /api/groups` | 200 | Returns groups array |

### Static Assets
| Call | Status | Notes |
|------|--------|-------|
| `GET /static/SecureDoc.html` | 200 | App shell |
| `GET /static/api.js` | 200 | Frontend API client |
| `GET /static/dist/app.bundle.js` | 200 | 249.3 KB esbuild bundle |

---

## Release Blocking Issues

**Zero.** No 500 errors. No broken contracts. No missing endpoints that the frontend calls. No malformed response shapes observed.

---

## Previously Identified Sprint 6.1 Fixes — Runtime Confirmed

| Fix | Runtime Confirmation |
|-----|---------------------|
| UX-001: Upload button label | Bundle contains "↑ Upload" (not "↑ Upload PDF") |
| UX-002: Views Today label | Bundle contains "Views Today" on both UploadScreen and AnalyticsScreen |
| UX-003: Event labels | Bundle contains complete `eventLabel()` switch with 25+ mappings |
| UX-004: Billing message | Bundle contains "Contact your administrator to enable paid plan upgrades." |
| UX-005: RiskBadge null | Bundle contains early return for missing level |
| UX-006: Risk fallback | Bundle does not contain `\|\| 'HIGH'` in AccessScreen |
| UX-007: Pluralization | Bundle contains conditional `page/pages · view/views` |

---

## Verdict

Runtime is stable. All endpoints respond correctly. No release blocking issues found.
