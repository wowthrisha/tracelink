# Database Schema — Reading Analytics

Migration: `026_reading_analytics.py` (down_revision = "025")

---

## Table: `reading_sessions`

One row per viewer session. Aggregated on each batch ingest.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | Integer | PK, autoincrement | |
| session_id | String(32) | UNIQUE, NOT NULL, indexed | Opaque viewer token |
| link_id | Integer | FK(links.id) CASCADE | |
| document_id | String | NOT NULL, indexed | |
| viewer_email | String | nullable | Populated if gate auth |
| started_at | DateTime | server_default=now() | |
| last_event_at | DateTime | nullable | Updated on each batch |
| total_active_ms | Integer | default=0 | Accumulated active time |
| total_elapsed_ms | Integer | default=0 | Wall clock elapsed |
| pages_visited | Integer | default=0 | Distinct pages entered |
| pages_completed | Integer | default=0 | Pages with status=completed |
| completion_pct | Float | default=0.0 | pages_completed / page_count × 100 |
| engagement_score | Float | nullable | 0–100 |
| absorption_score | Float | nullable | 0–100 |
| focus_score | Float | nullable | 0–100 |
| reading_consistency | Float | nullable | 0–100 |
| attention_stability | Float | nullable | 0–100 |
| understanding_confidence | Float | nullable | 0–100 |
| drop_off_page | Integer | nullable | Last page before session end |
| confusion_page | Integer | nullable | Page with most idle/revisit activity |
| initial_estimate_ms | Integer | nullable | Initial remaining time estimate |
| page_count | Integer | nullable | Document total pages |
| created_at | DateTime | server_default=now() | |
| updated_at | DateTime | server_default=now(), onupdate=now() | |

**Indexes:**
- `ix_rs_session_id` on `session_id` (UNIQUE)
- `ix_rs_document_started` on `(document_id, started_at)`

---

## Table: `page_reading_events`

One row per (session, page). Upserted on each batch. Active time never decreases.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | Integer | PK, autoincrement | |
| reading_session_id | Integer | FK(reading_sessions.id) CASCADE | |
| page_number | Integer | NOT NULL | 1-based |
| active_time_ms | Integer | default=0 | Monotonically non-decreasing |
| pause_duration_ms | Integer | default=0 | |
| revisit_count | Integer | default=0 | |
| scroll_percentage | Float | default=0.0 | 0–100 |
| zoom_level | Integer | default=100 | Integer % |
| fullscreen_used | Boolean | default=False | |
| annotations_created | Integer | default=0 | |
| copy_attempts | Integer | default=0 | |
| print_attempts | Integer | default=0 | |
| tab_switch_count | Integer | default=0 | |
| visibility_changes | Integer | default=0 | |
| idle_events | Integer | default=0 | |
| completion_status | Enum | default='unread' | See enum below |
| enter_timestamp | DateTime | nullable | |
| exit_timestamp | DateTime | nullable | |
| created_at | DateTime | server_default=now() | |
| updated_at | DateTime | server_default=now(), onupdate=now() | |

**Enum `page_completion_status_enum`:**
`unread | started | reading | completed | revisited | skipped`

**Compound UNIQUE constraint:** `(reading_session_id, page_number)`

**Indexes:**
- `ix_pre_reading_session` on `reading_session_id`
- `ix_pre_document_page` on `(reading_session_id, page_number)`

---

## Table: `document_complexity`

One row per document. Computed once from file metadata, cached indefinitely (refreshed if session_count changes significantly).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| document_id | String | PK | |
| word_count | Integer | nullable | Estimated from file size |
| estimated_words_per_page | Integer | nullable | word_count / page_count |
| image_density | Float | nullable | bytes_per_page / 200_000, clamped 0–1 |
| complexity_factor | Float | default=1.0 | Multiplier on baseline WPM |
| baseline_wpm | Integer | nullable | Adjusted for file type + complexity |
| median_completion_ms | Integer | nullable | Median across all sessions |
| session_count | Integer | default=0 | Total sessions recorded |
| created_at | DateTime | server_default=now() | |
| updated_at | DateTime | server_default=now(), onupdate=now() | |

---

## Migration Notes

The migration creates a PostgreSQL native enum type `page_completion_status_enum`. This must be dropped manually on `downgrade()` after dropping the table:

```python
op.execute("DROP TYPE IF EXISTS page_completion_status_enum")
```

All FK relationships use `ondelete='CASCADE'` — deleting a link or document cascades to sessions and page events automatically.
