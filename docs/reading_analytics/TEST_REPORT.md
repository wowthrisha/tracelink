# Test Report — Reading Intelligence Engine

## Summary

| Suite | Tests | Passed | Skipped | Failed |
|---|---|---|---|---|
| Unit (reading analytics) | 40 | 40 | 0 | 0 |
| Integration (reading API) | 27 | 27 | 0 | 0 |
| **New total** | **67** | **67** | **0** | **0** |
| Full suite (pre-existing) | 1624 | 1624 | 1 | 0 |
| **Full suite (post-feature)** | **1691** | **1691** | **1** | **0** |

**Zero regressions** across the full test suite.

---

## Unit Tests: `tests/unit/test_reading_analytics.py`

### TestReadingSpeedWpm
- `test_returns_none_when_no_qualifying_pages` — pages with <1000ms are filtered
- `test_single_qualifying_page_returns_page_wpm` — single data point, no EWMA needed
- `test_ewma_weights_recent_pages` — EWMA adapts toward recent reading speed
- `test_clamped_to_700_wpm_max` — extreme speed clamped
- `test_clamped_to_50_wpm_min` — very slow reading clamped

### TestEstimateRemainingMs
- `test_returns_zero_when_on_last_page` — no remaining pages
- `test_uses_baseline_when_no_qualifying_pages` — fallback to baseline WPM
- `test_blends_session_and_baseline` — session weight at 0.6 (3/5 pages complete)
- `test_fully_session_weighted_after_5_pages` — 100% session weight after 5 qualifying pages

### TestEngagementScore
- `test_perfect_completion_max_completion_pts` — 100% completion → 40 pts
- `test_revisit_ratio_contributes` — revisit adds up to 15 pts
- `test_idle_penalty_applied` — high idle ratio reduces score
- `test_annotation_pts_capped_at_15` — cap enforced
- `test_zero_with_all_zero_inputs` — no data → ~0

### TestFocusScore
- `test_high_active_ratio_high_score` — 90% active → high base
- `test_tab_switches_reduce_score` — tab_switch_count penalty
- `test_visibility_changes_reduce_score` — interruption penalty
- `test_score_clamped_to_zero` — never negative

### TestReadingConsistency
- `test_perfectly_even_pages_score_100` — identical times → CV=0 → 100
- `test_high_variance_low_score` — wildly uneven times → low score
- `test_single_page_returns_100` — no variance possible

### TestAttentionStability
- `test_no_disruptions_returns_100` — zero disruptions → max score
- `test_many_disruptions_low_score` — many events → low avg focus interval
- `test_five_min_avg_scores_100` — 300k ms per disruption = 100

### TestAbsorptionScore
- `test_composite_of_engagement_and_focus` — 0.6 × engagement + 0.4 × focus
- `test_clamped_to_100` — never exceeds 100

### TestUnderstandingConfidence
- `test_sweet_spot_pace_max_pace_pts` — pace 0.6–1.4× → 40 pts
- `test_too_fast_reduced_pace_pts` — 0.2× pace → reduced
- `test_revisit_sweet_spot_contributes` — 10–25% revisits → 20 pts
- `test_annotation_pts_added` — annotations increment score

### TestAggregateSession
- `test_all_scores_computed_from_real_data` — end-to-end aggregation
- `test_completion_pct_from_page_count` — uses session.page_count
- `test_drop_off_page_set` — correctly identifies last completed page

### TestGenerateInsights
- `test_no_insights_below_threshold` — 3 sessions → no insights
- `test_slow_page_insight_generated` — ratio ≥ 2.5× with ≥ 5 sessions
- `test_positive_completion_insight` — ≥ 80% completion generates positive insight
- `test_high_dropoff_warning` — ≥ 30% drop at same page
- `test_insights_capped_at_12` — never returns more than 12
- `test_sorted_by_confidence_descending` — highest confidence first

---

## Integration Tests: `tests/integration/test_reading_api.py`

### Auth
- `test_batch_rejects_invalid_token` — 401 on bad token
- `test_session_get_requires_token` — 401 without token
- `test_summary_requires_auth` — 403 for viewer on owner endpoint
- `test_heatmap_requires_auth`
- `test_insights_requires_auth`
- `test_viewers_requires_auth`

### Validation
- `test_page_out_of_range_rejected` — page > page_count → 400
- `test_total_elapsed_capped` — >86.4M ms capped, not rejected
- `test_invalid_completion_status_rejected` — unknown status → 400
- `test_page_data_max_500_items` — 501 items → 422

### Ingest + Query
- `test_batch_ingest_creates_session` — session created on first batch
- `test_batch_ingest_returns_204` — correct status code
- `test_session_get_returns_data` — data visible after ingest
- `test_active_time_never_decreases` — second batch with lower time → original kept
- `test_completion_status_only_upgrades` — `completed → started` batch → status stays `completed`
- `test_tab_switches_accumulate` — multiple batches → tab counts sum
- `test_multi_session_aggregation` — two sessions → summary reflects both
- `test_page_count_validated_against_document` — correct page_count used

### Heatmap
- `test_heatmap_returns_all_pages` — all ingested pages appear
- `test_heatmap_hotspot_detection` — hotspot flag set for long-average pages
- `test_heatmap_aggregates_across_sessions` — multi-session averages computed

### Viewers
- `test_viewers_returns_per_session_breakdown` — each session as separate row
- `test_viewers_includes_scores` — engagement/focus/consistency present

### Insights
- `test_insights_empty_for_single_session` — below threshold → no insights
- `test_insights_structure` — correct response shape

---

## Bugs Caught and Fixed During Testing

1. **`active_time_ms` None before flush** — SQLAlchemy server_default is not applied in Python until after a flush. Fixed with `max(pre.active_time_ms or 0, active_ms)`.
2. **Wrong fixture pairing** — `sample_link` uses `sample_document_in_db`, not `sample_document`. Tests updated to use the correct fixture.
3. **page_count mismatch** — `sample_document` has `page_count=3`. Tests using pages 4-5 had them silently dropped. Fixed by using pages 1–3.
4. **Understanding confidence formula** — default `_session()` helper had `completion_pct=100.0` which inflated scores in "low confidence" tests. Fixed by zeroing the field.
5. **Slow-page insight threshold** — test used ratio of 2.1× (below 2.5× threshold). Fixed test data to achieve 3.08× ratio.
