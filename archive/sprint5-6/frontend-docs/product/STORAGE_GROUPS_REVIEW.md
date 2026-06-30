# Storage & Groups Integration Review — Sprint 4.8 Phase 3

**Method:** Full source code trace of `StorageScreen.jsx`, `UploadScreen.jsx`, `group.py` (model), `document.py` (model), `groups.py` (router), `storage.py` (router), and `AnalyticsScreen.jsx`.

---

## Current Architecture

### DocumentGroup model (`backend/app/models/group.py`)

```python
class DocumentGroup(Base):
    __tablename__ = "document_groups"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: UUID (PK)
    user_id: UUID (not nullable, indexed)
    name: str (max 100)
    color: str (hex, max 7)
    description: str (max 500, nullable)
    created_at, updated_at
    documents: relationship → Document.group (one-to-many)
```

**Key facts:**
- Groups are flat — no `parent_group_id`, no hierarchy
- Groups are user-scoped — `user_id` is on `DocumentGroup`, not per-org
- Group names are unique per user

### Document model (`backend/app/models/document.py`)

```python
group_id: UUID (FK → document_groups.id, SET NULL on delete, nullable)
```

**Key facts:**
- One document belongs to at most one group
- Deleting a group → `group_id` SET NULL (documents persist, ungrouped)
- No pivot table — no many-to-many

### Groups router (`backend/app/routers/groups.py`)

| Endpoint | Description |
|----------|-------------|
| `GET /api/groups` | List user's groups with document_count |
| `POST /api/groups` | Create group |
| `GET /api/groups/{id}` | Get single group |
| `PATCH /api/groups/{id}` | Update name/color/description |
| `DELETE /api/groups/{id}` | Delete group (unassigns documents) |
| `PUT /api/groups/{id}/documents` | Assign list of doc IDs to group |
| `DELETE /api/groups/{id}/documents/{doc_id}` | Remove single doc from group |

### Storage router (`backend/app/routers/storage.py`)

The storage dashboard endpoint does NOT join or filter by `group_id`. It returns per-document and per-org breakdowns — groups are invisible to the Storage screen.

---

## Question-by-Question Analysis

### Can groups become folders?

**Partially, with the current schema.** Groups already function as flat folders:
- Documents belong to one group (one parent)
- Groups can be created, renamed, deleted
- Deleting a group orphans documents (does not delete them)

What's missing for folder-like UX:
- Groups are not visible in the Storage screen
- No nested/hierarchical groups (no `parent_group_id`)
- No "move document between groups" UI in StorageScreen
- No "open folder" navigation mode — the group filter is a chip bar, not a folder tree

The schema supports flat folders already. **Hierarchy would require a migration.**

---

### Can documents belong to groups?

**YES — already implemented end-to-end.** Assignment is functional:
- `UploadScreen.jsx:154–164`: `handleAssignGroup()` calls `assignDocumentsToGroup()` or `removeDocumentFromGroup()`
- `DocRow.jsx:67–79`: Dropdown shows groups on hover; `onChange` fires assignment
- Backend validates ownership: `groups.py:190–218` confirms both group and document belong to the user

What doesn't work:
- The Storage screen ignores `group_id` entirely
- The Analytics screen shows `group_name` in the per-document table (good), but the Storage screen shows no group column

---

### Does the schema already support this?

| Capability | Schema support | UI support |
|-----------|---------------|-----------|
| Flat grouping (1 group per doc) | ✅ Yes | ✅ Yes (Upload screen) |
| Filter docs by group | ✅ Yes (query by group_id) | ✅ Yes (chip filter) |
| Batch assign docs to group | ✅ Yes (PUT endpoint) | ✅ Yes (dropdown per row) |
| Storage by group | ✅ Derivable (JOIN docs + groups) | ❌ No |
| Nested/hierarchical groups | ❌ No (no parent_group_id) | ❌ No |
| Multiple groups per document | ❌ No (no pivot table) | ❌ No |
| Cross-user shared groups | ❌ No (group is user-scoped) | ❌ No |

---

### What migration would be required for each capability?

#### Option A: Show groups in Storage (Immediate)

**No migration required.**

The storage query in `storage.py` can be extended with a `LEFT JOIN` to `document_groups`. No schema change. The `StorageScreen.jsx` UI would add a group column and a group breakdown card.

#### Option B: Nested groups / folder hierarchy

**Migration required:**
- Add `parent_group_id UUID FK → document_groups.id (nullable)` to `document_groups`
- This is a non-destructive additive column — low risk
- Backend router would need recursive queries (or a depth-limited JOIN) for subtree listing
- UI would need a tree component

#### Option C: Multiple groups per document (tags/labels)

**Migration required:**
- Create new pivot table `document_group_members(document_id UUID, group_id UUID, PRIMARY KEY (document_id, group_id))`
- Drop `documents.group_id` (destructive, or migrate existing assignments to pivot table)
- High risk — all group-assignment queries change

#### Option D: Cross-user shared groups

**Migration + new auth model required:**
- Group must have an `org_id` FK instead of/in addition to `user_id`
- New permissions model for "who can read/write documents in this group"
- This is a significant architectural change

---

### What security implications exist?

| Change | Security implication |
|--------|---------------------|
| Show groups in StorageScreen | None — user already sees their own groups in UploadScreen |
| Group name in storage table | None — the user owns both the group and the document |
| Nested groups | Risk of infinite loops in recursive queries if `parent_group_id` cycles; need depth limit |
| Multi-group (pivot) | Group membership queries must still scope to `user_id` to prevent cross-user reads |
| Cross-user shared groups | **High risk** — new authorization layer needed; current model assumes user owns everything |

The current model is simple and secure: all group operations are gated by `user_id` comparison at the DB query level. Every router endpoint that touches groups verifies `DocumentGroup.user_id == user_uuid` before any operation. This pattern is safe and consistent.

---

## Ranked Recommendations

### Immediate — Add group breakdown to Storage screen

**What:** Show group column in the per-document storage table. Add "Storage by Group" summary card above the per-document table.

**Why:** This is a JOIN query already supported by the data model. Zero migration. Closes the disconnect between two screens that should be the same mental model ("my documents organized by group").

**Backend change:** Extend `GET /api/storage/dashboard` or add `GET /api/storage/by-group` that groups documents by `group_id`.  
**Frontend change:** Add group column to `StorageScreen.jsx:114` table header and rows. Add summary card.  
**Database change:** None.  
**Risk:** Low.

---

### Later — Folder-style navigation in UploadScreen

**What:** Instead of (or in addition to) the chip filter strip, add a left-rail folder tree that shows groups as folders. Clicking a group "opens" it and shows its documents in the main table. This is the same data; it's a UX change, not a data change.

**Why:** With 10+ groups, the chip strip becomes unwieldy (already wraps, no overflow handling: `UploadScreen.jsx:229`). A folder sidebar is more scalable.

**Backend change:** None.  
**Frontend change:** New `FolderSidebar` component in UploadScreen.jsx.  
**Database change:** None.  
**Risk:** Medium (UI refactor).

---

### Later — Nested groups (subfolder hierarchy)

**What:** Allow groups to contain sub-groups by adding `parent_group_id` to `document_groups`.

**Why:** Users organizing 100+ documents across multiple projects may want "Legal > Contracts" or "Q4 > Reports > Internal".

**Backend change:** Router updates for recursive listing.  
**Frontend change:** Tree component.  
**Database change:** `ALTER TABLE document_groups ADD COLUMN parent_group_id UUID REFERENCES document_groups(id) ON DELETE SET NULL;` — additive, low risk.  
**Risk:** Medium. Recommend doing only after Immediate item above is shipped and validated with users.

---

### Do Not Implement — Multiple groups per document

**What:** Allow a document to belong to multiple groups simultaneously (tags/labels pattern).

**Why it sounds appealing:** "Tag" semantics are familiar from email clients (Gmail labels, etc.).

**Why not now:**
1. Requires dropping `documents.group_id` and creating a pivot table — breaking change with data migration.
2. The existing analytics, storage, and filter queries all assume `group_id IS a direct FK`. Every query would need rewriting.
3. The existing UX (one group per doc, shown as a chip) is already clear. Multi-group membership introduces display complexity (multiple chips per row, which group takes precedence for analytics?).
4. No user has requested this — the existing model handles all current workflows.

**Verdict:** Do Not Implement.

---

### Do Not Implement — Cross-user shared groups

**What:** Organizations share a group, all org members see the same documents.

**Why not now:**
- The org model (`orgs.py`) exists but member addition requires raw Supabase UUIDs (no user-lookup endpoint). Cross-user group sharing would depend on the same broken flow.
- The document ownership model is `user_id` scoped — shared groups would need a `user_id → org_id` pivot that doesn't exist.
- Security surface increases significantly.

**Verdict:** Do Not Implement until org member management is fully functional.

---

## Summary

| Capability | Verdict | Effort | Migration? |
|-----------|---------|--------|-----------|
| Storage screen group column | Immediate | 2–3 hours frontend, 1 hour backend | No |
| Folder nav in UploadScreen | Later | 1–2 days frontend | No |
| Nested groups (hierarchy) | Later | 1 day backend + frontend + 1 migration | Yes (additive) |
| Multiple groups per doc | Do Not Implement | 3–4 days + destructive migration | Yes (breaking) |
| Cross-user shared groups | Do Not Implement | 1 week + org member fixes | Yes (breaking) |

---

*Generated: Sprint 4.8 Phase 3 — no implementation performed.*
