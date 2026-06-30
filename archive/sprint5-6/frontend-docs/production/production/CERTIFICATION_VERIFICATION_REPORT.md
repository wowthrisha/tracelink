# Certification Verification Report — Sprint 5.3

**Date:** 2026-06-23  
**Verifier:** Independent audit pass  
**Method:** Source code inspection, CLI execution, runtime tests  
**Sprint 5.3 Claims Source:** PRODUCTION_CERTIFICATION_FINAL.md, phase reports, MASTER_ACTION_LOG.md

---

## 1. Database — Migration 025

### Claim: Migration 025 exists

**Status: VERIFIED**

File confirmed at:
```
backend/alembic/versions/025_performance_indexes.py
```

### Claim: Migration executes cleanly

**Status: FALSE**

`alembic history` fails with:

```
FAILED: Could not determine revision id from filename 025_performance_indexes.py.
Be sure the 'revision' variable is declared inside the script
```

Root cause: The migration file documents the revision in the docstring (`Revision ID: 025`) but is missing the required Python variable declarations that Alembic parses at load time:

```python
# REQUIRED — NOT PRESENT in 025_performance_indexes.py:
revision = "025"
down_revision = "024"
```

All 24 prior migrations (001–024) have these variables. Migration 025 does not.

**Consequence:** `alembic upgrade head` fails. The migration cannot be applied to any database via Alembic's standard toolchain. The migration chain is broken.

**How tests still pass:** The test suite uses `Base.metadata.create_all` (confirmed in `tests/conftest.py:51`), not Alembic. `create_all` reads index declarations from the SQLAlchemy model classes directly, bypassing the migration chain entirely. The three new indexes exist in the model files and are therefore present in test databases — but would not be applied to a production PostgreSQL instance via `alembic upgrade head`.

### Claim: New indexes exist in model declarations

**Status: VERIFIED**

All three indexes present with matching names and column order:

| Index | File | Columns |
|-------|------|---------|
| `ix_access_events_link_event` | `models/event.py:48` | `["link_id", "event_type"]` |
| `ix_share_links_doc_revoked` | `models/link.py:15` | `["document_id", "revoked_at"]` |
| `ix_documents_group_id` | `models/document.py:25` | `["group_id"]` |

Migration column order matches model declarations exactly.

### Claim: No duplicate indexes introduced

**Status: VERIFIED**

Each of the three index names appears in exactly one migration file (`025_performance_indexes.py`). No other migration file references them.

---

## 2. Analytics — SQL GROUP BY DATE

### Claim: Python-side bucketing was removed

**Status: VERIFIED**

The following identifiers no longer exist anywhere in `analytics_service.py`:
- `week_ts_rows`
- `for ts in`
- `ts.strftime`
- `ts.replace(tzinfo=timezone.utc)` (within get_overview context)

Confirmed via grep — zero matches.

### Claim: SQL GROUP BY implementation exists

**Status: VERIFIED**

`analytics_service.py` lines 149–164:

```python
week_q = (
    select(
        func.date(AccessEvent.created_at).label("day"),
        func.count().label("cnt"),
    )
    .where(
        AccessEvent.event_type == "opened",
        AccessEvent.created_at >= week_start,
    )
    .group_by(func.date(AccessEvent.created_at))
)
if scoped_link_ids:
    week_q = week_q.where(AccessEvent.link_id.in_(scoped_link_ids))
date_counts = {str(row.day): row.cnt for row in (await db.execute(week_q)).all()}
```

### Claim: Tests cover the new path

**Status: VERIFIED**

`test_analytics.py::TestAnalyticsOverview::test_overview_returns_required_fields` exercises the endpoint and asserts `len(body["views_last_7_days"]) == 7`. The `views_last_7_days` field is produced exclusively by the new GROUP BY DATE query path. Test passes.

---

## 3. Security — href Sanitization

### Claim: href sanitization exists in ViewerScreen

**Status: VERIFIED**

`frontend/src/screens/ViewerScreen.jsx` lines 537–541:

```javascript
let safeHref = null;
try { const u = new URL(link.url); if (/^https?:$/i.test(u.protocol)) safeHref = link.url; } catch {}
<a key={i} href={safeHref || '#'} target={safeHref ? '_blank' : undefined} rel="noopener noreferrer"
  onClick={safeHref ? undefined : e => e.preventDefault()}
```

Old pattern `href={link.url}` confirmed absent.

### Claim: Only http/https allowed; javascript:, data:, vbscript: are blocked

**Status: VERIFIED**

Tested the exact regex `/^https?:$/i` against all claimed-blocked protocols via Node.js:

| Input | Expected | Result |
|-------|----------|--------|
| `https://example.com` | ALLOW | ALLOW ✓ |
| `http://example.com` | ALLOW | ALLOW ✓ |
| `javascript:alert(1)` | BLOCK | BLOCK ✓ |
| `data:text/html,...` | BLOCK | BLOCK ✓ |
| `vbscript:msgbox(1)` | BLOCK | BLOCK ✓ |
| `JAVASCRIPT:alert(1)` | BLOCK | BLOCK ✓ |
| `""` (empty) | BLOCK | BLOCK ✓ |
| `not-a-url` | BLOCK | BLOCK ✓ |

All 8 cases pass.

---

## 4. API — Rate Limits and Validation

### Claim: All analytics GET endpoints have rate limits

**Status: VERIFIED**

`analytics.py` router decorators, in order:

| Line | Endpoint | Decorator |
|------|----------|-----------|
| 19–20 | `GET /overview` | `@limiter.limit("30/minute")` |
| 29–30 | `GET /documents` | `@limiter.limit("30/minute")` |
| 56–57 | `GET /groups` | `@limiter.limit("30/minute")` |
| 73–74 | `GET /page-heatmap` | `@limiter.limit("30/minute")` |
| 100–101 | `GET /events` | `@limiter.limit("30/minute")` |
| 188–189 | `POST /events` | `@limiter.limit("60/minute")` |

All 6 endpoints (5 GET + 1 POST) have rate limit decorators. Each has `request: Request` as the first parameter, required by SlowAPI.

### Claim: Invalid group_id returns 400

**Status: VERIFIED**

`analytics.py` lines 41–44:

```python
try:
    group_uuid = uuid.UUID(group_id)
except ValueError:
    raise HTTPException(status_code=400, detail="Invalid group_id format")
```

### Claim: Missing gate token returns 404

**Status: VERIFIED**

`viewer.py` line 152–153 (gate handler):

```python
if not link:
    raise HTTPException(status_code=404, detail="Link not found")
```

`api.js` line 315–317:

```javascript
if (r.status === 404) {
    return { status: 'not_found', requires_password: false, requires_email: false };
}
```

---

## 5. Frontend — Build and Dead Code

### Claim: Build succeeds

**Status: VERIFIED**

```
dist/app.bundle.js  246.6kb
⚡ Done in 22ms
```

Exit code 0.

### Claim: No stale references, no broken imports

**Status: VERIFIED**

- `href={link.url}` (old unsafe pattern): absent from ViewerScreen
- `safeHref` (new pattern): present in ViewerScreen
- `safeUrl` (LinksPanel original): present and unchanged in LinksPanel
- No import errors — build succeeds cleanly

---

## 6. Testing — Count and Quality

### Claim: Test count is 1624

**Status: VERIFIED**

```
1624 passed, 1 skipped, 20 warnings in 67.69s
```

Run confirmed independently. Count matches Sprint 5.3 claim exactly.

### Claim: No xfail tests hiding failures

**Status: VERIFIED**

`grep -rn "xfail\|pytest.mark.skip"` across all test files returns zero matches. No `@pytest.mark.xfail` decorators exist in the test suite.

### Claim: The 1 skipped test is not a security test

**Status: VERIFIED**

The single skipped test:

```
tests/integration/test_phase_e2_stability.py::TestLibreOfficeTimeout::test_timeout_used_in_subprocess_call
SKIPPED — reason: libreoffice not available
```

Skip is conditional on `shutil.which("libreoffice")` returning None. This is a LibreOffice document conversion timeout test, not a security test. Skip reason is environment availability, not hidden failure.

---

## Summary Table

| Claim | Status |
|-------|--------|
| Migration 025 file exists | VERIFIED |
| **Migration 025 executes cleanly via alembic** | **FALSE** |
| Index names match model declarations | VERIFIED |
| No duplicate indexes across migrations | VERIFIED |
| Python timestamp loop removed | VERIFIED |
| SQL GROUP BY DATE implemented | VERIFIED |
| GROUP BY DATE path covered by tests | VERIFIED |
| ViewerScreen href sanitization exists | VERIFIED |
| javascript:/data:/vbscript: all blocked | VERIFIED |
| All 5 GET analytics endpoints rate-limited | VERIFIED |
| POST /events rate-limited | VERIFIED |
| Invalid group_id returns 400 | VERIFIED |
| Missing gate token returns 404 | VERIFIED |
| Frontend build succeeds | VERIFIED |
| No stale/broken references in changed files | VERIFIED |
| Test count is 1624 | VERIFIED |
| No xfail tests | VERIFIED |
| Skipped test is non-security/non-critical | VERIFIED |

---

## Defect Found

**D-001 — CRITICAL: Migration 025 cannot be applied by Alembic**

- **File:** `backend/alembic/versions/025_performance_indexes.py`
- **Missing:** `revision = "025"` and `down_revision = "024"` Python variable declarations
- **Impact:** `alembic upgrade head` fails with parse error. The migration chain is broken from revision 025 onward. A fresh production database or any database upgrade via the standard deployment path will not receive the three new indexes.
- **Tests unaffected:** Test suite uses `Base.metadata.create_all` which reads model index declarations directly, bypassing Alembic. Tests pass but do not validate the migration path.
- **Fix required:** Add the two missing variable declarations to `025_performance_indexes.py`.

---

## Final Verdict

**CERTIFICATION REQUIRES CORRECTION**

One defect (D-001) prevents the Sprint 5.3 database hardening from taking effect in production. All other claims are independently verified as true. The defect is a two-line fix. Certification can be re-issued after D-001 is resolved.
