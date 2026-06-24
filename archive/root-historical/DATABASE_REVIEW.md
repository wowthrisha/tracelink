# Database Review

Scope: `backend/app/models/*.py` (14 model files) vs `backend/alembic/versions/001`-`024`. Migration chain verified unbroken (001→024, every `down_revision` matches, every migration has a `downgrade()`).

## Tables (summary)

| Table | Key columns | Model-declared indexes | PII? |
|---|---|---|---|
| documents | id (PK), user_id, org_id, group_id (FK→document_groups, SET NULL), parent_document_id (FK→documents, SET NULL), status, file_type, retention_policy, lifecycle_state, expires_at | user_id, lifecycle_state, expires_at | no |
| document_pages | document_id (FK→documents, CASCADE), page_number | unique(document_id, page_number) | no |
| share_links | document_id (FK→documents, CASCADE), token (UNIQUE), password_hash, allowed_emails/domains/ip_allowlist (JSON text), max_views, max_concurrent_sessions | document_id | no |
| access_events | link_id (FK→share_links, CASCADE), event_type, viewer_email, ip_hash, session_id | link_id, created_at | **yes** — viewer_email plaintext |
| document_groups | user_id, name, color | user_id; unique(user_id, name) | no |
| viewer_sessions | session_id (PK), link_id (FK CASCADE), viewer_email, viewer_email_masked, viewer_profile_id (FK→viewer_profiles, SET NULL) | link_id, last_seen_at, viewer_profile_id | **yes** |
| viewer_annotations | link_id (FK CASCADE), viewer_email, viewer_profile_id (FK SET NULL), parent_id (self-FK CASCADE, reply threading) | (link_id, page_number), session_id, viewer_profile_id | **yes** |
| viewer_bookmarks | link_id, session_id, page_number | unique(link_id, session_id, page_number); (link_id, session_id) | no |
| viewer_profiles | id, email (UNIQUE) | email | **yes — global cross-document identity** |
| user_billing | user_id (PK), stripe_customer_id, stripe_subscription_id | **none declared in model** | no |
| webhook_endpoints | user_id, url, secret, events | user_id | no |
| webhook_deliveries | webhook_id (FK CASCADE) | webhook_id | no |
| api_keys | user_id, key_hash (UNIQUE) | user_id, key_hash | no |
| organizations | slug (UNIQUE), custom_domain (UNIQUE) | slug | no |
| org_memberships | org_id (FK CASCADE), user_id, role | unique(org_id, user_id); user_id | no |
| admin_audit_log | org_id, actor_user_id, ip_hash | actor_user_id, org_id, created_at | ip_hash (hashed, not raw) |
| storage_snapshots | user_id, org_id, snapshot_at | (user_id, snapshot_at), (org_id, snapshot_at) | no |

## Finding 1 (P2): Model/migration index drift

The following indexes exist in Alembic migrations but are **not declared in the corresponding SQLAlchemy model's `__table_args__`** — meaning the index physically exists in any DB created via `alembic upgrade head`, but `Base.metadata` (what the ORM believes the schema looks like) is out of sync with it:

| Index | Created by | Missing from model |
|---|---|---|
| `ix_documents_file_type` | migration 009 | `app/models/document.py` |
| `ix_documents_org_id` | migration 016 | `app/models/document.py` |
| `ix_documents_parent_id` | migration 018 | `app/models/document.py` |
| `ix_documents_status_updated` (composite: status, updated_at DESC) | migration 012 | `app/models/document.py` |
| `ix_access_events_link_id_created` (composite: link_id, created_at DESC) | migration 012 | `app/models/event.py` |
| `ix_user_billing_stripe_customer`, `ix_user_billing_stripe_sub` | migration 006 | `app/models/billing.py` (no `__table_args__` at all) |
| `ix_viewer_annotations_parent` (on parent_id, used for reply-thread queries) | migration 023 | `app/models/annotation.py` |
| `ix_viewer_sessions_link_session` (composite: link_id, session_id — the hot-path session-validation lookup) | migration 020 | `app/models/session.py` |

**Impact:** Functionally harmless today (indexes exist in the real DB; queries use them). Risk surfaces if anyone ever (a) flips on Alembic autogenerate, which will propose spurious `DROP INDEX` migrations against indexes the model doesn't know about, or (b) reads the model as documentation of the schema and concludes an index is missing when it isn't. **Recommendation:** backfill `__table_args__` in all 5 affected model files to match the migrations — pure documentation/tooling fix, zero runtime risk, ~30 min of work.

## Finding 2 (P1): `viewer_profiles` has no retention path

`viewer_profiles` (migration 024) stores a global, cross-document `email` keyed identity for every viewer who has ever opened any share link. `app/services/retention.py` and `app/workers/cleanup.py` delete documents and cascade through `share_links → access_events / viewer_sessions / viewer_annotations / viewer_bookmarks`, but **nothing references `viewer_profiles`** — there is no FK from `viewer_profiles` back to a link or document, so cascade delete cannot reach it, and no standalone cleanup task does either. A viewer's email persists indefinitely even after every document/link they ever touched has been retention-deleted.

**Recommendation:** add a cleanup pass (in `app/workers/cleanup.py`) that deletes any `viewer_profiles` row with no remaining `viewer_sessions`/`viewer_annotations` referencing its `id`, run on the same daily schedule as `cleanup_expired_documents()`.

## Finding 3 (P3): Constraint-naming fragility

Migration 002 creates `UniqueConstraint("name")` on `document_groups` without an explicit name (Postgres auto-generates one); migration 005 has to know and hardcode that auto-generated name (`document_groups_name_key`) to drop and replace it with `uq_group_user_name`. Works, but any future Postgres-version naming-convention change could break the `005` migration on a from-scratch `alembic upgrade head` run. **Recommendation:** not urgent — only matters for fresh installs, which already pass today — but new migrations should always pass `name=` explicitly to `UniqueConstraint`/`Index`.

## Hot-path query coverage (sanity check)

Cross-referenced columns appearing in router `WHERE` clauses against declared indexes — `document_id`, `user_id`, `link_id`, `session_id` are all indexed where they're filtered on. The two composite indexes from migration 012/020 (`access_events(link_id, created_at)`, `viewer_sessions(link_id, session_id)`) specifically target the analytics-heatmap and per-request session-validation hot paths and are present in the DB (just undocumented in the model, per Finding 1) — no missing-index risk identified on the read paths reviewed.

## Orphan Risk

All FK relationships reviewed use explicit `ondelete=CASCADE` or `ondelete=SET NULL` (no bare FKs relying on application-level cleanup) — `document_pages`, `share_links`, `access_events`, `viewer_sessions`, `viewer_annotations`, `viewer_bookmarks`, `webhook_deliveries`, `org_memberships` all cascade correctly off their parent. The one exception is `viewer_profiles` (Finding 2), which has no parent FK to cascade from in the first place — it's an orphan-by-design gap, not a broken cascade.
