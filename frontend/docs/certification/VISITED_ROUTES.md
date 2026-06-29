# VISITED ROUTES — Sprint 5.5 Engineering Investigation
**Date:** 2026-06-29  
**Sprint:** 5.5 Phase 2  
**Method:** Source code review of all router files + API client

---

## Backend Routes (All Reviewed)

### Auth — `/api/auth`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/auth/register` | POST | auth.py | ✅ |

### Documents — `/api/documents`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/documents/upload` | POST | documents.py | ✅ |
| `/api/documents` | GET | documents.py | ✅ |
| `/api/documents/{id}` | GET | documents.py | ✅ |
| `/api/documents/{id}/status` | GET | documents.py | ✅ |
| `/api/documents/{id}` | DELETE | documents.py | ✅ |
| `/api/documents/{id}/reprocess` | POST | documents.py | ✅ |
| `/api/documents/{id}/extract-sidecars` | POST | documents.py | ✅ |
| `/api/documents/{id}/versions` | GET | documents.py | ✅ |
| `/api/documents/{id}/annotations/export` | GET | annotations.py | ✅ |
| `/api/documents/{id}/annotations/visual` | GET | annotations.py | ✅ |
| `/api/documents/{id}/annotations/export-visual` | GET | annotations.py | ✅ |
| `/api/documents/{id}/feedback` | GET | annotations.py | ✅ |
| `/api/documents/{id}/feedback/reviewers` | GET | annotations.py | ✅ |
| `/api/documents/{id}/feedback/export` | GET | annotations.py | ✅ |
| `/api/documents/{id}/feedback/reviewer-activity` | GET | annotations.py | ✅ |
| `/api/documents/{id}/annotations` | GET | annotations.py | ✅ |
| `/api/documents/{id}/retention` | PATCH | storage.py | ✅ |

### Links — `/api/links`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/links` | GET | links.py | ✅ |
| `/api/links` | POST | links.py | ✅ |
| `/api/links/{id}` | GET | links.py | ✅ |
| `/api/links/{id}` | PATCH | links.py | ✅ |
| `/api/links/{id}` | DELETE | links.py | ✅ |
| `/api/links/{id}/hard` | DELETE | links.py | ✅ |

### Viewer — `/api/viewer`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/viewer/gate/{token}` | GET | viewer.py | ✅ |
| `/api/viewer/validate` | POST | viewer.py | ✅ |
| `/api/viewer/page/{token}/{page}` | GET | viewer.py | ✅ |
| `/api/viewer/thumb/{token}/{page}` | GET | viewer.py | ✅ |
| `/api/viewer/toc/{token}` | GET | viewer.py | ✅ |
| `/api/viewer/download/{token}` | GET | viewer.py | ✅ |
| `/api/viewer/text/{token}/{chunk}` | GET | viewer.py | ✅ |
| `/api/viewer/search/{token}` | GET | viewer.py | ✅ |
| `/api/viewer/links/{token}` | GET | viewer.py | ✅ |
| `/api/viewer/word-positions/{token}` | GET | viewer.py | ✅ |
| `/api/viewer/annotations/{token}/{page}` | GET | annotations.py | ✅ |
| `/api/viewer/annotations/{token}` | POST | annotations.py | ✅ |
| `/api/viewer/annotations/{token}/{id}` | PUT | annotations.py | ✅ |
| `/api/viewer/annotations/{token}/{id}` | DELETE | annotations.py | ✅ |
| `/api/viewer/annotations/{token}/{id}/resolve` | POST | annotations.py | ✅ |
| `/api/viewer/bookmarks/{token}` | GET | annotations.py | ✅ |
| `/api/viewer/bookmarks/{token}/{page}` | POST | annotations.py | ✅ |
| `/api/viewer/feedback/{token}/{id}` | GET | annotations.py | ✅ |
| `/api/viewer/feedback/{token}/{id}/reply` | POST | annotations.py | ✅ |
| `/api/viewer/feedback/{token}/{id}/resolve` | POST | annotations.py | ✅ |

### Analytics — `/api/analytics`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/analytics/overview` | GET | analytics.py | ✅ |
| `/api/analytics/documents` | GET | analytics.py | ✅ |
| `/api/analytics/groups` | GET | analytics.py | ✅ |
| `/api/analytics/events` | GET | analytics.py | ✅ |
| `/api/analytics/events` | POST | analytics.py | ✅ |
| `/api/analytics/page-heatmap` | GET | analytics.py | ✅ |

### Storage — `/api/storage`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/storage/dashboard` | GET | storage.py | ✅ |
| `/api/storage/forecast` | GET | storage.py | ✅ |
| `/api/storage/documents` | GET | storage.py | ✅ |

### Groups — `/api/groups`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/groups` | GET | groups.py | ✅ |
| `/api/groups` | POST | groups.py | ✅ |
| `/api/groups/{id}` | GET | groups.py | ✅ |
| `/api/groups/{id}` | PATCH | groups.py | ✅ |
| `/api/groups/{id}` | DELETE | groups.py | ✅ |
| `/api/groups/{id}/documents` | PUT | groups.py | ✅ |
| `/api/groups/{id}/documents/{doc_id}` | DELETE | groups.py | ✅ |

### Webhooks — `/api/webhooks`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/webhooks` | GET | webhooks.py | ✅ |
| `/api/webhooks` | POST | webhooks.py | ✅ |
| `/api/webhooks/{id}` | GET | webhooks.py | ✅ |
| `/api/webhooks/{id}` | PATCH | webhooks.py | ✅ |
| `/api/webhooks/{id}` | DELETE | webhooks.py | ✅ |
| `/api/webhooks/{id}/deliveries` | GET | webhooks.py | ✅ |
| `/api/webhooks/{id}/test` | POST | webhooks.py | ✅ |

### API Keys — `/api/api-keys`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/api-keys` | GET | api_keys.py | ✅ |
| `/api/api-keys` | POST | api_keys.py | ✅ |
| `/api/api-keys/{id}` | GET | api_keys.py | ✅ |
| `/api/api-keys/{id}` | PATCH | api_keys.py | ✅ |
| `/api/api-keys/{id}` | DELETE | api_keys.py | ✅ |

### Organizations — `/api/orgs`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/orgs` | GET | orgs.py | ✅ |
| `/api/orgs` | POST | orgs.py | ✅ |
| `/api/orgs/{id}` | GET | orgs.py | ✅ |
| `/api/orgs/{id}` | PATCH | orgs.py | ✅ |
| `/api/orgs/{id}` | DELETE | orgs.py | ✅ |
| `/api/orgs/{id}/members` | GET | orgs.py | ✅ |
| `/api/orgs/{id}/members` | POST | orgs.py | ✅ |
| `/api/orgs/{id}/members/{user_id}` | PATCH | orgs.py | ✅ |
| `/api/orgs/{id}/members/{user_id}` | DELETE | orgs.py | ✅ |
| `/api/orgs/{id}/domain/token` | GET | orgs.py | ✅ |
| `/api/orgs/{id}/domain/verify` | POST | orgs.py | ✅ |

### Admin — `/api/admin`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/admin/audit-log` | GET | admin.py | ✅ |

### Billing — `/api/billing`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/billing/status` | GET | billing.py | ✅ |
| `/api/billing/checkout` | POST | billing.py | ✅ |
| `/api/billing/portal` | POST | billing.py | ✅ |
| `/api/billing/webhook` | POST | billing.py | ✅ |

### Notifications — `/api/notifications`
| Route | Method | File | Reviewed |
|-------|--------|------|---------|
| `/api/notifications/stream` | GET | notifications.py | ✅ (SSE) |

---

## Frontend Screens (All Reviewed)

| Screen | File | Status |
|--------|------|--------|
| Upload Dashboard | UploadScreen.jsx | ✅ |
| Access Control | AccessScreen.jsx | ✅ |
| Analytics | AnalyticsScreen.jsx | ✅ |
| Storage | StorageScreen.jsx | ✅ |
| API Keys | ApiKeysScreen.jsx | ✅ |
| Webhooks | WebhooksScreen.jsx | ✅ |
| Audit Log | AuditLogScreen.jsx | ✅ |
| Organizations | OrgsScreen.jsx | ✅ |
| Notifications | NotificationsScreen.jsx | ✅ |
| Billing | BillingScreen.jsx | ✅ |
| Viewer | ViewerScreen.jsx | ✅ |
| App Shell | AppShell.jsx | ✅ |
| Login | LoginScreen.jsx | ✅ |

**Total routes reviewed: 75 backend routes + 13 frontend screens**
