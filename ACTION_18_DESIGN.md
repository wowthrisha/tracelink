# Action 18 Design: Document Version History

**Status:** IN PROGRESS  
**Risk:** P2 — Required for compliance workflows; "which version did the investor see?"  
**Effort:** 3 hours

## Problem

When a document is updated, all existing share links point to the new content with no record of what was seen at a given point in time. Compliance and legal workflows require knowing exactly which version was reviewed.

## Solution

Add `version INT` and `parent_document_id UUID` to documents. Each upload can optionally specify a `parent_document_id` to create a new version in the chain. The version chain is purely additive — existing documents/links are unchanged. Share links always point to the specific document_id they were created with (no implicit redirection to latest version).

## Schema Change

```sql
-- Migration 018

ALTER TABLE documents ADD COLUMN version INT NOT NULL DEFAULT 1;
ALTER TABLE documents ADD COLUMN parent_document_id UUID REFERENCES documents(id) ON DELETE SET NULL;
```

## Upload Flow

```
POST /api/documents/upload
  body: { file, parent_document_id: "<uuid>" }  # optional

If parent_document_id provided:
  - Validate caller owns parent document
  - new_version = parent.version + 1
  - doc.parent_document_id = parent.id
  - doc.version = new_version

Else:
  - doc.version = 1
  - doc.parent_document_id = None
```

## Version History API

`GET /api/documents/{id}/versions`
- Returns the full version chain for the document (from root to latest)
- Ordered by version number ascending
- Returns: `{versions: [{id, filename, version, status, page_count, created_at}]}`

## Response Changes

`GET /api/documents` + `GET /api/documents/{id}/status` now include `version` and `parent_document_id` fields.

## Security

- Only the document owner can create a new version (same rule as upload)
- `parent_document_id` must be owned by the caller (cross-user version chains blocked)

## Files Changed

| File | Change |
|------|--------|
| `app/models/document.py` | `version` and `parent_document_id` fields |
| `alembic/versions/018_add_version_history.py` | Migration |
| `app/routers/documents.py` | Accept `parent_document_id` in upload; version endpoint |
