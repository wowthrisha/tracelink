# Reading Analytics API Reference

Base URL: `/api/reading`

All timestamps are ISO 8601 UTC. All durations are milliseconds (integer).

---

## POST /api/reading/batch

Submit a batch of reading events from the viewer. Fire-and-forget; called every 5 seconds.

**Auth:** Viewer link token (query param or body field `token`). Validated via `enforcer.is_active_session()`.

**Rate limit:** 30 requests/minute per IP.

### Request Body

```json
{
  "token": "abc123...",
  "session_id": "550e8400e29b41d4a716446655440000",
  "page_data": [
    {
      "page_number": 3,
      "active_time_ms": 45000,
      "pause_duration_ms": 12000,
      "revisit_count": 1,
      "scroll_percentage": 87.5,
      "zoom_level": 100,
      "fullscreen_used": false,
      "annotations_created": 0,
      "copy_attempts": 0,
      "print_attempts": 0,
      "tab_switch_count": 2,
      "visibility_changes": 2,
      "idle_events": 1,
      "completion_status": "completed",
      "enter_timestamp": "2024-01-15T10:00:00Z",
      "exit_timestamp": "2024-01-15T10:00:45Z"
    }
  ],
  "session_meta": {
    "total_elapsed_ms": 180000,
    "total_active_ms": 120000,
    "started_at": "2024-01-15T09:57:00Z",
    "page_count": 20,
    "current_page": 4,
    "initial_estimate_ms": 600000
  }
}
```

**Validation:**
- `page_data`: max 500 items
- `total_elapsed_ms`: capped at 86,400,000 (24h)
- `page_number`: must be 1 ≤ n ≤ document.page_count
- `completion_status`: one of `unread | started | reading | completed | revisited | skipped`

**Response:** `204 No Content`

---

## GET /api/reading/session/{session_id}

Retrieve the viewer's own session summary. Used by the viewer's status bar.

**Auth:** `?token=<link_token>` query parameter.

**Rate limit:** 60 requests/minute.

### Response (200)

```json
{
  "session_id": "550e8400e29b41d4a716446655440000",
  "total_active_ms": 125000,
  "total_elapsed_ms": 180000,
  "completion_pct": 65.0,
  "pages_visited": 13,
  "pages_completed": 8,
  "engagement_score": 72.3,
  "focus_score": 68.1,
  "reading_consistency": 81.4,
  "started_at": "2024-01-15T09:57:00Z",
  "last_event_at": "2024-01-15T10:02:00Z"
}
```

---

## GET /api/reading/document/{document_id}/summary

Aggregate reading statistics across all sessions for a document.

**Auth:** `require_scope("analytics:read")` — uploader/owner only.

**Rate limit:** 30 requests/minute.

### Response (200)

```json
{
  "document_id": "uuid...",
  "total_sessions": 42,
  "unique_viewers": 38,
  "avg_active_ms": 234000,
  "avg_elapsed_ms": 310000,
  "avg_completion_pct": 61.2,
  "median_completion_ms": 198000,
  "avg_engagement_score": 67.8,
  "avg_absorption_score": 63.2,
  "avg_focus_score": 71.4,
  "avg_reading_consistency": 74.9,
  "avg_attention_stability": 55.3,
  "avg_understanding_confidence": 58.7,
  "drop_off_distribution": {
    "page_3": 12,
    "page_7": 8,
    "page_15": 5
  }
}
```

---

## GET /api/reading/document/{document_id}/heatmap

Per-page reading statistics aggregated across all sessions.

**Auth:** `require_scope("analytics:read")`

**Rate limit:** 30 requests/minute.

### Response (200)

```json
{
  "document_id": "uuid...",
  "total_sessions": 42,
  "pages": [
    {
      "page_number": 1,
      "session_count": 42,
      "avg_active_ms": 45000,
      "median_active_ms": 38000,
      "avg_scroll_percentage": 94.2,
      "completion_rate": 0.88,
      "revisit_rate": 0.12,
      "drop_off_rate": 0.05,
      "avg_idle_events": 0.3,
      "avg_tab_switches": 0.1,
      "is_hotspot": true
    }
  ]
}
```

`is_hotspot`: true when `avg_active_ms` is ≥ 1.5× the document median.

---

## GET /api/reading/document/{document_id}/insights

Natural language insights derived from reading patterns. Only generated when data thresholds are met (never fabricated).

**Auth:** `require_scope("analytics:read")`

**Rate limit:** 20 requests/minute.

### Response (200)

```json
{
  "document_id": "uuid...",
  "session_count": 42,
  "insights": [
    {
      "type": "warning",
      "message": "Page 7 takes viewers 3.2× longer than average — consider simplifying the content.",
      "context": "Avg 187s on page 7 vs 58s document average across 28 sessions.",
      "page": 7,
      "confidence": 0.87
    },
    {
      "type": "positive",
      "message": "85% of viewers who start this document finish it — exceptional completion rate.",
      "context": null,
      "page": null,
      "confidence": 0.95
    }
  ]
}
```

**Insight types:** `warning | positive | info | anomaly`

Insights are only generated when:
- Slow page: ratio ≥ 2.5× and ≥ 5 sessions with data for that page
- High drop-off: ≥ 30% of sessions drop off at same page
- Completion milestone: ≥ 80% or ≤ 20% completion across sessions
- Revisit hotspot: revisit_rate ≥ 0.5 on a page
- Speed anomaly: viewer avg vs baseline ≥ 2× or ≤ 0.5×

Maximum 12 insights returned, sorted by confidence descending.

---

## GET /api/reading/document/{document_id}/viewers

Per-session viewer breakdown.

**Auth:** `require_scope("analytics:read")`

**Rate limit:** 20 requests/minute.

### Response (200)

```json
{
  "document_id": "uuid...",
  "viewers": [
    {
      "session_id": "550e...",
      "viewer_email": "viewer@example.com",
      "started_at": "2024-01-15T09:57:00Z",
      "last_event_at": "2024-01-15T10:05:00Z",
      "total_active_ms": 234000,
      "total_elapsed_ms": 480000,
      "completion_pct": 75.0,
      "pages_visited": 15,
      "pages_completed": 12,
      "engagement_score": 74.2,
      "focus_score": 69.8,
      "reading_consistency": 82.1,
      "drop_off_page": 16,
      "confusion_page": null
    }
  ]
}
```

`viewer_email`: populated if the link had email gate auth; null for anonymous viewers.

---

## Error Responses

All endpoints return standard error shapes:

```json
{ "detail": "Human-readable error message" }
```

| Status | Meaning |
|---|---|
| 400 | Validation error (bad page number, invalid status, etc.) |
| 401 | Token invalid or expired |
| 403 | Scope insufficient (owner endpoint called by viewer) |
| 404 | Session or document not found |
| 429 | Rate limit exceeded |
