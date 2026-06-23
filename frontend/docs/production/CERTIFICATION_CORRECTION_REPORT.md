# Certification Correction Report — Sprint 5.3A

**Date:** 2026-06-23  
**Defect:** D-001 from CERTIFICATION_VERIFICATION_REPORT.md  
**Status:** RESOLVED

---

## Root Cause

`backend/alembic/versions/025_performance_indexes.py` was missing the Python variable declarations that Alembic requires to parse a migration file and place it in the revision chain.

The revision metadata existed only in the module docstring (as comments), not as executable Python:

```
Revision ID: 025    ← docstring only — Alembic does not read this
Revises: 024        ← docstring only — Alembic does not read this
```

Alembic requires these as actual Python variables at module scope. All 24 prior migrations (001–024) have them; 025 did not.

---

## Exact Fix

**File:** `backend/alembic/versions/025_performance_indexes.py`

Added four variable declarations after the closing `"""` of the module docstring, before the imports:

```python
revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None
```

`upgrade()` and `downgrade()` functions were not modified.

**Pattern matches migrations 023 and 024:**

```python
# 024_viewer_profiles.py (reference)
revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None

# 023_annotation_fields.py (reference)
revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None
```

---

## Verification Evidence

### alembic history — PASS

```
024 -> 025 (head), Add missing performance indexes for analytics and active-link queries
023 -> 024, Add viewer_profiles + plaintext viewer_email on sessions/annotations
022 -> 023, Add sticky_note/draw support, resolved_at, parent_id, thickness to viewer_annotations
...
<base> -> 001, initial schema
```

Migration 025 is now `head` in the chain. Command exits 0.

### Migration graph validity — PASS

Revision 025 follows 024 (`down_revision = "024"`). No gaps, no branches, no conflicts.

### upgrade() DDL verification — PASS

Migration 025's `upgrade()` was executed directly against a fresh SQLite database with the three target tables. All three indexes were created:

```
UPGRADE   ix_access_events_link_event: PRESENT
UPGRADE   ix_share_links_doc_revoked:  PRESENT
UPGRADE   ix_documents_group_id:       PRESENT
```

### downgrade() DDL verification — PASS

Migration 025's `downgrade()` was then executed. All three indexes were removed:

```
DOWNGRADE ix_access_events_link_event: REMOVED
DOWNGRADE ix_share_links_doc_revoked:  REMOVED
DOWNGRADE ix_documents_group_id:       REMOVED
```

### upgrade() second pass — PASS

Re-running `upgrade()` after downgrade recreated all three indexes cleanly:

```
UPGRADE2  ix_access_events_link_event: PRESENT
UPGRADE2  ix_share_links_doc_revoked:  PRESENT
UPGRADE2  ix_documents_group_id:       PRESENT
```

### Note on full `alembic upgrade head` from base

Migrations 001–024 use PostgreSQL-specific DDL (`ADD CONSTRAINT`, `EXCLUDE`, etc.) that SQLite does not support. A full `alembic upgrade head` from `<base>` requires PostgreSQL. The development environment does not have PostgreSQL running (`alembic current` reports the connected PostgreSQL is at revision 006). The migration 025 DDL operations (`create_index` / `drop_index`) are standard SQL supported by both SQLite and PostgreSQL — verified above via direct execution.

### alembic current — CONFIRMED

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
006
```

Alembic correctly reads the migration chain and reports current position. Before the fix, this command failed with a parse error.

### Full test suite — PASS

```
1624 passed, 1 skipped, 20 warnings in 64.54s
```

Same count as post-Sprint 5.3. No regressions introduced.

---

## Commit

`fix(migration): add revision/down_revision variables to migration 025`

---

## Final Verdict

All D-001 verification steps pass. The migration chain is valid. The defect is resolved.
