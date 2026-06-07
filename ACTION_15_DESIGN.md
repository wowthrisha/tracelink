# Action 15 Design: Organizations + SSO Foundation

**Status:** IN PROGRESS  
**Risk:** P1 — single-owner model blocks team use; required for Fortune 500 procurement  
**Effort:** 5 hours

## Problem

SecureDoc is purely single-user. Teams cannot share a document library, admins cannot manage access across members, and SSO/SAML requires an org-scoped identity model. Enterprise procurement requires workspace-level access control.

## Solution

Add an `organizations` table and `org_memberships` table. Documents gain an optional `org_id` — when set, org members with appropriate roles can access them. Supabase handles SAML/OIDC auth; this layer handles the role-to-permission mapping.

## Roles (Ordered by Permission Level)

| Role | Upload | Share | Analytics | Manage Members | Org Settings |
|------|--------|-------|-----------|----------------|--------------|
| viewer | ✗ | ✗ | ✗ (own only) | ✗ | ✗ |
| editor | ✓ | ✓ own | ✗ | ✗ | ✗ |
| admin | ✓ | ✓ all | ✓ all | ✓ (non-owner) | ✗ |
| owner | ✓ | ✓ all | ✓ all | ✓ all | ✓ |

## Schema

```sql
-- Migration 016

CREATE TABLE organizations (
  id UUID PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  slug VARCHAR(100) NOT NULL UNIQUE,  -- URL-safe identifier
  saml_domain VARCHAR(255),           -- maps SAML email domain → this org
  is_active BOOL NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE org_memberships (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  role VARCHAR(16) NOT NULL DEFAULT 'viewer',  -- viewer | editor | admin | owner
  invited_by_user_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(org_id, user_id)
);

ALTER TABLE documents ADD COLUMN org_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/orgs | Create org (caller becomes owner) |
| GET | /api/orgs | List orgs current user belongs to |
| GET | /api/orgs/{id} | Get org + membership count |
| PATCH | /api/orgs/{id} | Update name/slug (owner only) |
| DELETE | /api/orgs/{id} | Delete org (owner only) |
| GET | /api/orgs/{id}/members | List members |
| POST | /api/orgs/{id}/members | Add member (admin/owner only) |
| PATCH | /api/orgs/{id}/members/{user_id} | Change role (admin/owner only) |
| DELETE | /api/orgs/{id}/members/{user_id} | Remove member (admin/owner) |

## Document Sharing in Org Context

- `POST /api/documents/upload` accepts optional `org_id` body param
- If `org_id` provided and caller is org member with editor+ role → `doc.org_id` set
- `GET /api/documents` returns org-shared docs when caller is org member
- Existing user-scoped access (user_id match) unchanged — purely additive

## Security Rules

- Owner cannot be removed via the members API (prevents lockout)
- Role change cannot escalate beyond actor's own role
- `org_id` in upload is validated: caller must be editor+ in that org
- Org deletion cascades memberships; documents get org_id=NULL (not deleted)

## Files Changed

| File | Change |
|------|--------|
| `app/models/org.py` | `Organization`, `OrgMembership` models + `ORG_ROLES` |
| `alembic/versions/016_add_organizations.py` | Tables + documents.org_id column |
| `app/routers/orgs.py` | Full org + membership CRUD |
| `app/services/org_service.py` | Role enforcement helpers |
| `app/routers/documents.py` | Accept org_id in upload; org-scoped list |
| `app/main.py` | Include orgs router |
| `tests/integration/test_enterprise_phase4.py` | All Phase 4 tests |
