"""Unit tests for the Reading Intelligence Engine service layer.

Tests cover:
  - Reading speed model (EWMA)
  - Remaining time estimation
  - Page completion status logic
  - Engagement / absorption / focus scores
  - Reading consistency / attention stability
  - Understanding confidence
  - Insights engine
  - Edge cases: no data, single page, 100% completion, max idle
"""
import uuid
from datetime import datetime, timezone


from app.models.reading_analytics import (
    DocumentComplexity,
    PageReadingEvent,
    ReadingSession,
)
from app.services.reading_analytics_service import (
    MIN_PAGES_FOR_SPEED,
    aggregate_session_from_pages,
    compute_absorption_score,
    compute_attention_stability,
    compute_engagement_score,
    compute_focus_score,
    compute_reading_consistency,
    compute_reading_speed_wpm,
    compute_understanding_confidence,
    estimate_remaining_ms,
    generate_insights,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _page(
    page_number: int,
    active_time_ms: int = 60_000,
    completion_status: str = "completed",
    revisit_count: int = 0,
    idle_events: int = 0,
    tab_switch_count: int = 0,
    visibility_changes: int = 0,
    annotations_created: int = 0,
    copy_attempts: int = 0,
    pause_duration_ms: int = 0,
    scroll_percentage: float = 100.0,
) -> PageReadingEvent:
    e = PageReadingEvent()
    e.id = uuid.uuid4()
    e.reading_session_id = uuid.uuid4()
    e.session_id = "aabbcc112233"
    e.document_id = uuid.uuid4()
    e.page_number = page_number
    e.active_time_ms = active_time_ms
    e.pause_duration_ms = pause_duration_ms
    e.revisit_count = revisit_count
    e.idle_events = idle_events
    e.tab_switch_count = tab_switch_count
    e.visibility_changes = visibility_changes
    e.annotations_created = annotations_created
    e.copy_attempts = copy_attempts
    e.scroll_percentage = scroll_percentage
    e.zoom_level = 100
    e.fullscreen_used = False
    e.print_attempts = 0
    e.completion_status = completion_status
    e.created_at = datetime.now(timezone.utc)
    e.updated_at = datetime.now(timezone.utc)
    return e


def _session(
    total_active_ms: int = 600_000,
    total_elapsed_ms: int = 720_000,
    total_idle_ms: int = 60_000,
    total_pause_ms: int = 60_000,
    pages_visited: int = 10,
    pages_completed: int = 10,
    pages_skipped: int = 0,
    pages_revisited: int = 2,
    completion_pct: float = 100.0,
    avg_ms_per_page: float = 60_000.0,
    total_annotations: int = 0,
    total_copy_attempts: int = 0,
    total_idle_events: int = 2,
    reading_interruptions: int = 2,
    avg_pause_ms: float = 30_000.0,
    tab_switch_count: int = 1,
    reading_speed_wpm: float = 200.0,
) -> ReadingSession:
    s = ReadingSession()
    s.id = uuid.uuid4()
    s.session_id = "aabbcc112233"
    s.link_id = uuid.uuid4()
    s.document_id = uuid.uuid4()
    s.total_active_ms = total_active_ms
    s.total_elapsed_ms = total_elapsed_ms
    s.total_idle_ms = total_idle_ms
    s.total_pause_ms = total_pause_ms
    s.pages_visited = pages_visited
    s.pages_completed = pages_completed
    s.pages_skipped = pages_skipped
    s.pages_revisited = pages_revisited
    s.completion_pct = completion_pct
    s.avg_ms_per_page = avg_ms_per_page
    s.total_annotations = total_annotations
    s.total_copy_attempts = total_copy_attempts
    s.total_idle_events = total_idle_events
    s.reading_interruptions = reading_interruptions
    s.avg_pause_ms = avg_pause_ms
    s.tab_switch_count = tab_switch_count
    s.reading_speed_wpm = reading_speed_wpm
    s.started_at = datetime.now(timezone.utc)
    s.last_updated_at = datetime.now(timezone.utc)
    # Reset optional fields
    s.fastest_page = None
    s.slowest_page = None
    s.drop_off_page = None
    s.confusion_page = None
    s.initial_estimate_ms = None
    s.prediction_accuracy_pct = None
    s.viewer_email_masked = None
    s.total_print_attempts = 0
    s.engagement_score = None
    s.absorption_score = None
    s.focus_score = None
    s.reading_consistency = None
    s.attention_stability = None
    s.understanding_confidence = None
    return s


def _complexity(
    page_count: int = 10,
    words_per_page: float = 250.0,
    baseline_wpm: float = 200.0,
    complexity_factor: float = 1.0,
) -> DocumentComplexity:
    c = DocumentComplexity()
    c.document_id = uuid.uuid4()
    c.page_count = page_count
    c.estimated_words_per_page = words_per_page
    c.baseline_wpm = baseline_wpm
    c.complexity_factor = complexity_factor
    c.image_density = 0.0
    c.table_density = 0.0
    c.avg_page_length_ratio = 1.0
    c.word_count = int(words_per_page * page_count)
    c.median_completion_ms = None
    c.session_count = 0
    return c


# ── Reading Speed Tests ────────────────────────────────────────────────────────

class TestReadingSpeedWpm:
    def test_returns_none_when_no_pages(self):
        assert compute_reading_speed_wpm([], 250.0) is None

    def test_returns_none_below_min_pages(self):
        pages = [_page(i, active_time_ms=60_000, completion_status="completed") for i in range(1, MIN_PAGES_FOR_SPEED)]
        assert compute_reading_speed_wpm(pages, 250.0) is None

    def test_computes_simple_speed(self):
        # 2 pages, 1 min each, 250 words/page → 250 wpm
        pages = [
            _page(1, active_time_ms=60_000, completion_status="completed"),
            _page(2, active_time_ms=60_000, completion_status="completed"),
        ]
        wpm = compute_reading_speed_wpm(pages, 250.0)
        assert wpm is not None
        # EWMA of [250, 250] = 250 (steady state)
        assert abs(wpm - 250.0) < 10

    def test_ewma_weights_recent_pages(self):
        # Start slow (120 wpm), then speed up (300 wpm × 3 pages)
        pages = [
            _page(1, active_time_ms=125_000, completion_status="completed"),  # ~120 wpm
            _page(2, active_time_ms=50_000, completion_status="completed"),   # 300 wpm
            _page(3, active_time_ms=50_000, completion_status="completed"),   # 300 wpm
            _page(4, active_time_ms=50_000, completion_status="completed"),   # 300 wpm
        ]
        wpm = compute_reading_speed_wpm(pages, 250.0)
        # EWMA should be closer to 300 than to 120
        assert wpm > 230, f"Expected wpm > 230 but got {wpm}"

    def test_ignores_unread_pages(self):
        pages = [
            _page(1, active_time_ms=60_000, completion_status="unread"),
            _page(2, active_time_ms=60_000, completion_status="started"),
            _page(3, active_time_ms=60_000, completion_status="completed"),
            _page(4, active_time_ms=60_000, completion_status="completed"),
        ]
        # Only pages 3+4 qualify (completion_status in reading/completed)
        wpm = compute_reading_speed_wpm(pages, 250.0)
        assert wpm is not None

    def test_ignores_very_short_page_times(self):
        # Pages with <1000ms should be excluded (navigation flicker, not reading)
        pages = [
            _page(1, active_time_ms=500, completion_status="completed"),
            _page(2, active_time_ms=60_000, completion_status="completed"),
            _page(3, active_time_ms=60_000, completion_status="completed"),
        ]
        wpm = compute_reading_speed_wpm(pages, 250.0)
        assert wpm is not None

    def test_clamps_to_physiological_range(self):
        # Very fast but above 1000ms threshold: 1500ms/page × 250 words → 10000 wpm, clamped to 700
        pages = [
            _page(1, active_time_ms=1_500, completion_status="reading"),
            _page(2, active_time_ms=1_500, completion_status="reading"),
            _page(3, active_time_ms=1_500, completion_status="reading"),
        ]
        wpm = compute_reading_speed_wpm(pages, 250.0)
        assert wpm is not None
        assert wpm <= 700


# ── Remaining Time Estimation Tests ───────────────────────────────────────────

class TestEstimateRemainingMs:
    def test_returns_zero_on_last_page(self):
        c = _complexity(page_count=10)
        result = estimate_remaining_ms([], current_page=10, total_pages=10, complexity=c)
        assert result == 0

    def test_uses_baseline_when_no_session_data(self):
        c = _complexity(page_count=10, words_per_page=250.0, baseline_wpm=200.0, complexity_factor=1.0)
        # No page events, no session_wpm → uses baseline 200 wpm
        # 9 pages × 250 words = 2250 words / 200 wpm = 11.25 min = 675_000 ms
        result = estimate_remaining_ms([], current_page=1, total_pages=10, complexity=c)
        assert result is not None
        expected = int((9 * 250 / 200) * 60_000)
        assert abs(result - expected) < 5000  # within 5s

    def test_blends_session_and_baseline(self):
        c = _complexity(page_count=10, words_per_page=250.0, baseline_wpm=200.0)
        pages = [
            _page(i, active_time_ms=30_000, completion_status="completed")
            for i in range(1, 6)
        ]
        # 5 pages at 30s each → 500 wpm (reading speed), well above baseline 200
        wpm = compute_reading_speed_wpm(pages, 250.0)
        result = estimate_remaining_ms(pages, current_page=5, total_pages=10, complexity=c, session_wpm=wpm)
        # With session data, remaining should be < pure baseline estimate
        baseline_remaining = int((5 * 250 / 200) * 60_000)
        assert result is not None
        assert result < baseline_remaining  # faster reader → less time remaining

    def test_session_weight_caps_at_1_after_5_pages(self):
        c = _complexity(page_count=20, words_per_page=250.0, baseline_wpm=200.0)
        pages = [
            _page(i, active_time_ms=60_000, completion_status="completed")
            for i in range(1, 11)
        ]
        wpm = compute_reading_speed_wpm(pages, 250.0)
        result = estimate_remaining_ms(pages, current_page=10, total_pages=20, complexity=c, session_wpm=wpm)
        assert result is not None
        # After 5+ pages, session weight = 1.0 → pure session estimate
        # 10 pages × 250 words / 250 wpm = 10 min = 600_000 ms
        assert abs(result - 600_000) < 60_000  # within 1 minute

    def test_complexity_factor_increases_remaining(self):
        c_easy = _complexity(page_count=10, baseline_wpm=200.0, complexity_factor=1.0)
        c_hard = _complexity(page_count=10, baseline_wpm=200.0, complexity_factor=2.0)
        r_easy = estimate_remaining_ms([], current_page=1, total_pages=10, complexity=c_easy)
        r_hard = estimate_remaining_ms([], current_page=1, total_pages=10, complexity=c_hard)
        # Harder document → more time remaining
        assert r_hard > r_easy


# ── Engagement Score Tests ─────────────────────────────────────────────────────

class TestEngagementScore:
    def test_perfect_reader_scores_near_100(self):
        # 100% completion, steady pace, 3 annotations, no idle
        s = _session(
            completion_pct=100.0,
            pages_revisited=1,
            pages_visited=10,
            total_annotations=3,
            total_idle_ms=0,
            total_elapsed_ms=600_000,
        )
        pages = [_page(i, active_time_ms=60_000) for i in range(1, 11)]
        score = compute_engagement_score(s, pages)
        assert score >= 70, f"Expected ≥70 but got {score}"

    def test_empty_session_scores_zero(self):
        s = _session(total_elapsed_ms=0)
        score = compute_engagement_score(s, [])
        assert score == 0.0

    def test_idle_heavy_session_penalized(self):
        s_low_idle = _session(total_idle_ms=0, total_elapsed_ms=600_000, completion_pct=80.0)
        s_high_idle = _session(total_idle_ms=480_000, total_elapsed_ms=600_000, completion_pct=80.0)
        pages = [_page(i) for i in range(1, 9)]
        score_low = compute_engagement_score(s_low_idle, pages)
        score_high = compute_engagement_score(s_high_idle, pages)
        assert score_low > score_high

    def test_score_clamped_to_0_100(self):
        s = _session(completion_pct=0.0, total_elapsed_ms=1, total_idle_ms=0)
        score = compute_engagement_score(s, [])
        assert 0.0 <= score <= 100.0


# ── Focus Score Tests ──────────────────────────────────────────────────────────

class TestFocusScore:
    def test_no_interruptions_high_score(self):
        s = _session(
            total_active_ms=600_000,
            total_elapsed_ms=600_000,
            reading_interruptions=0,
            tab_switch_count=0,
            total_idle_events=0,
        )
        score = compute_focus_score(s)
        assert score >= 55  # 100% active ratio × 60

    def test_many_interruptions_lower_score(self):
        s_clean = _session(reading_interruptions=0, tab_switch_count=0, total_idle_events=0)
        s_noisy = _session(reading_interruptions=10, tab_switch_count=8, total_idle_events=5)
        assert compute_focus_score(s_clean) > compute_focus_score(s_noisy)

    def test_zero_elapsed_returns_zero(self):
        s = _session(total_elapsed_ms=0)
        assert compute_focus_score(s) == 0.0


# ── Reading Consistency Tests ──────────────────────────────────────────────────

class TestReadingConsistency:
    def test_perfectly_consistent_pace(self):
        # All pages same time → stdev=0 → CV=0 → 100.0
        pages = [_page(i, active_time_ms=60_000) for i in range(1, 6)]
        score = compute_reading_consistency(pages)
        assert score == 100.0

    def test_highly_variable_pace_lower_score(self):
        pages = [
            _page(1, active_time_ms=5_000),
            _page(2, active_time_ms=180_000),
            _page(3, active_time_ms=3_000),
            _page(4, active_time_ms=200_000),
        ]
        score = compute_reading_consistency(pages)
        assert score < 50, f"Expected <50 but got {score}"

    def test_neutral_score_with_single_page(self):
        pages = [_page(1, active_time_ms=60_000)]
        score = compute_reading_consistency(pages)
        assert score == 50.0  # neutral

    def test_ignores_very_short_pages(self):
        # Pages <500ms should be excluded (flicker/navigation artifacts)
        pages = [
            _page(1, active_time_ms=100),   # excluded
            _page(2, active_time_ms=60_000),
            _page(3, active_time_ms=60_000),
        ]
        score = compute_reading_consistency(pages)
        # Only 2 valid pages, both same → 100.0
        assert score == 100.0


# ── Attention Stability Tests ──────────────────────────────────────────────────

class TestAttentionStability:
    def test_no_disruptions_perfect_stability(self):
        s = _session(total_idle_events=0, reading_interruptions=0, tab_switch_count=0)
        score = compute_attention_stability(s, [])
        assert score == 100.0

    def test_frequent_disruptions_lower_stability(self):
        s_stable = _session(total_idle_events=0, reading_interruptions=0, tab_switch_count=0)
        s_noisy = _session(total_idle_events=30, reading_interruptions=20, tab_switch_count=10)
        assert compute_attention_stability(s_stable, []) > compute_attention_stability(s_noisy, [])

    def test_score_clamped_to_100(self):
        s = _session(total_active_ms=10_000_000, total_idle_events=1, reading_interruptions=0, tab_switch_count=0)
        score = compute_attention_stability(s, [])
        assert score <= 100.0


# ── Absorption Score Tests ─────────────────────────────────────────────────────

class TestAbsorptionScore:
    def test_high_completion_high_score(self):
        s = _session(completion_pct=100.0, total_annotations=3, avg_ms_per_page=75_000)
        pages = [_page(i) for i in range(1, 11)]
        score = compute_absorption_score(s, pages)
        assert score >= 60

    def test_zero_completion_low_score(self):
        s = _session(completion_pct=0.0, total_annotations=0, avg_ms_per_page=0, pages_visited=0)
        score = compute_absorption_score(s, [])
        assert score <= 20


# ── Understanding Confidence Tests ────────────────────────────────────────────

class TestUnderstandingConfidence:
    def test_expected_pace_full_completion_high_score(self):
        c = _complexity(words_per_page=250.0, baseline_wpm=200.0)
        # Expected ms/page = 250/200 * 60_000 = 75_000 ms
        s = _session(avg_ms_per_page=75_000, completion_pct=100.0, pages_revisited=2, pages_visited=10, total_annotations=2)
        pages = [_page(i) for i in range(1, 11)]
        score = compute_understanding_confidence(s, pages, c)
        assert score >= 70, f"Expected ≥70 but got {score}"

    def test_too_fast_pace_lower_score(self):
        c = _complexity(words_per_page=250.0, baseline_wpm=200.0)
        # Extreme skimmer: 5s/page (0.067× expected), 0% completion, no revisits
        s = _session(
            avg_ms_per_page=5_000, completion_pct=0.0,
            pages_revisited=0, pages_visited=1,
            total_annotations=0,
        )
        pages = []
        score = compute_understanding_confidence(s, pages, c)
        # pace_pts ≈ 3, completion_pts = 0, revisit_pts = 0, annotation_pts = 0
        assert score < 20, f"Expected <20 but got {score}"


# ── Aggregate Session Tests ────────────────────────────────────────────────────

class TestAggregateSession:
    def test_full_read_completion_100(self):
        c = _complexity(page_count=5)
        pages = [_page(i, completion_status="completed") for i in range(1, 6)]
        s = _session(total_elapsed_ms=300_000, pages_visited=5)
        result = aggregate_session_from_pages(s, pages, c)
        assert result.pages_completed == 5
        assert result.completion_pct == 100.0

    def test_fastest_and_slowest_pages_identified(self):
        c = _complexity(page_count=5)
        pages = [
            _page(1, active_time_ms=10_000, completion_status="completed"),
            _page(2, active_time_ms=120_000, completion_status="completed"),
            _page(3, active_time_ms=60_000, completion_status="completed"),
        ]
        s = _session(total_elapsed_ms=200_000)
        result = aggregate_session_from_pages(s, pages, c)
        assert result.fastest_page == 1
        assert result.slowest_page == 2

    def test_drop_off_page_detected(self):
        c = _complexity(page_count=10)
        pages = [_page(i, completion_status="completed") for i in range(1, 6)]
        s = _session(total_elapsed_ms=300_000, completion_pct=50.0)
        result = aggregate_session_from_pages(s, pages, c)
        # Completion <100%, so drop_off_page should be set
        assert result.drop_off_page == 5

    def test_all_scores_computed(self):
        c = _complexity(page_count=5)
        pages = [_page(i, active_time_ms=60_000, completion_status="completed") for i in range(1, 6)]
        s = _session(total_elapsed_ms=300_000, completion_pct=100.0)
        result = aggregate_session_from_pages(s, pages, c)
        assert result.engagement_score is not None
        assert result.absorption_score is not None
        assert result.focus_score is not None
        assert result.reading_consistency is not None
        assert result.attention_stability is not None
        assert result.understanding_confidence is not None
        for score_name in ["engagement_score", "absorption_score", "focus_score",
                           "reading_consistency", "attention_stability", "understanding_confidence"]:
            val = getattr(result, score_name)
            assert 0.0 <= val <= 100.0, f"{score_name}={val} out of range"


# ── Insights Engine Tests ──────────────────────────────────────────────────────

class TestGenerateInsights:
    def _make_sessions(self, count: int, completion_pct: float = 100.0, active_ms: int = 600_000):
        sessions = []
        for i in range(count):
            s = _session(
                completion_pct=completion_pct,
                total_active_ms=active_ms + i * 1000,  # slight variation
                pages_revisited=1,
            )
            if completion_pct < 100.0:
                s.drop_off_page = 8
            sessions.append(s)
        return sessions

    def test_no_insights_with_no_data(self):
        insights = generate_insights([], [], _complexity())
        assert insights == []

    def test_returns_list_of_dicts(self):
        sessions = self._make_sessions(3)
        c = _complexity(page_count=10)
        pages = [_page(i, active_time_ms=60_000) for i in range(1, 11)] * 3
        insights = generate_insights(sessions, pages, c)
        assert isinstance(insights, list)
        for ins in insights:
            assert "text" in ins
            assert "type" in ins
            assert "confidence" in ins

    def test_slow_page_detected(self):
        c = _complexity(page_count=4)
        # Pages 1,2,4 take 30s each; page 3 takes 300s (10× longer)
        # global_avg = (3*30_000 + 300_000)/4 = 97_500; ratio = 300_000/97_500 = 3.08 > 2.5
        pages = (
            [_page(1, active_time_ms=30_000)] * 3
            + [_page(2, active_time_ms=30_000)] * 3
            + [_page(3, active_time_ms=300_000)] * 3  # 10× others
            + [_page(4, active_time_ms=30_000)] * 3
        )
        sessions = self._make_sessions(3)
        insights = generate_insights(sessions, pages, c)
        page_time_insights = [i for i in insights if i["type"] == "page_time" and i.get("page") == 3]
        assert len(page_time_insights) > 0, "Expected 'page_time' insight for page 3"

    def test_completion_insight_generated(self):
        sessions = self._make_sessions(5, completion_pct=100.0)
        c = _complexity(page_count=5)
        pages = [_page(i, active_time_ms=60_000) for i in range(1, 6)] * 5
        insights = generate_insights(sessions, pages, c)
        completion_insights = [i for i in insights if i["type"] == "completion"]
        assert len(completion_insights) > 0

    def test_cap_at_12_insights(self):
        sessions = self._make_sessions(10)
        c = _complexity(page_count=20)
        # Many pages with huge variance → many potential insights
        pages = []
        for pg in range(1, 21):
            ms = 5_000 * pg  # linearly increasing (high variance)
            pages.extend([_page(pg, active_time_ms=ms)] * 10)
        insights = generate_insights(sessions, pages, c)
        assert len(insights) <= 12

    def test_high_confidence_before_medium(self):
        sessions = self._make_sessions(5, completion_pct=100.0)
        c = _complexity(page_count=5)
        pages = [_page(i, active_time_ms=60_000) for i in range(1, 6)] * 5
        insights = generate_insights(sessions, pages, c)
        confidences = [i["confidence"] for i in insights]
        for i, conf in enumerate(confidences):
            if conf == "medium":
                # No "high" confidence after "medium" (sorted correctly)
                remaining = confidences[i:]
                assert "high" not in remaining, "High confidence insight found after medium"
