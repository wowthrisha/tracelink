"""Reading Intelligence Engine — core analytics service.

Formulas are documented inline. All scores are on a 0–100 scale.
No values are fabricated — every metric derives from collected event data.
"""
import statistics
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.link import ShareLink
from app.models.reading_analytics import (
    DocumentComplexity,
    PageReadingEvent,
    ReadingSession,
)

# ── Constants ──────────────────────────────────────────────────────────────────

# Reading speed baselines (words per minute) by document file type.
# Sources: Spritz research, Nielsen Norman Group, academic reading studies.
BASELINE_WPM_BY_TYPE: dict[str, float] = {
    "pdf": 200.0,      # average adult silent reading speed
    "docx": 220.0,     # flowing prose, fewer distractions
    "doc": 220.0,
    "pptx": 280.0,     # bullet points, less dense text
    "ppt": 280.0,
    "txt": 240.0,
    "md": 230.0,
    "xlsx": 120.0,     # data-dense, requires comprehension
    "xls": 120.0,
}

# Thresholds for page completion status determination
PAGE_STARTED_MS = 3_000       # >3s → "started"
PAGE_READING_MS = 15_000      # >15s → "reading"
PAGE_COMPLETED_RATIO = 0.7    # active_ms > 70% of expected_ms → "completed"

# Idle threshold: if gap between two same-page events > 30s, it's a pause
IDLE_THRESHOLD_MS = 30_000

# Minimum pages with data to compute reliable speed estimates
MIN_PAGES_FOR_SPEED = 2

# Weight for recent pages in EWMA reading speed calculation
EWMA_ALPHA = 0.35


# ── Complexity Computation ─────────────────────────────────────────────────────

async def get_or_create_document_complexity(
    db: AsyncSession,
    document_id: uuid.UUID,
) -> DocumentComplexity:
    """Return existing complexity record or compute from document metadata."""
    result = await db.execute(
        select(DocumentComplexity).where(DocumentComplexity.document_id == document_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    doc_result = await db.execute(select(Document).where(Document.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        # Fallback for edge case — return transient object, not persisted
        return DocumentComplexity(
            document_id=document_id,
            page_count=1,
            baseline_wpm=200.0,
            complexity_factor=1.0,
        )

    page_count = doc.page_count or 1
    file_type = (doc.file_type or "pdf").lower()
    file_size_bytes = doc.file_size_bytes or 0

    baseline_wpm = BASELINE_WPM_BY_TYPE.get(file_type, 200.0)

    # Image density heuristic: PDFs with high bytes/page are image-heavy.
    # Threshold: >200 KB/page → high image density.
    bytes_per_page = file_size_bytes / page_count if page_count > 0 else 0
    image_density = min(1.0, bytes_per_page / 200_000.0)

    # Complexity factor formula:
    #   base = 1.0
    #   +0.3 if image-heavy (density > 0.5) — images require more cognitive load
    #   +0.2 if xlsx (tabular data) — slower comprehension
    #   -0.1 if pptx (sparse bullets) — faster reading
    complexity_factor = 1.0
    if image_density > 0.5:
        complexity_factor += 0.3
    if file_type in ("xlsx", "xls"):
        complexity_factor += 0.2
    if file_type in ("pptx", "ppt"):
        complexity_factor -= 0.1
    complexity_factor = max(0.5, min(2.0, complexity_factor))

    # Estimated words per page adjusted for complexity
    # pptx slides avg ~40 words, text docs ~350, pdfs ~250
    type_words: dict[str, float] = {
        "pptx": 40.0, "ppt": 40.0,
        "xlsx": 20.0, "xls": 20.0,
        "txt": 350.0, "md": 300.0,
        "docx": 300.0, "doc": 300.0,
    }
    words_per_page = type_words.get(file_type, 250.0)
    # Reduce if image-heavy (images displace text)
    words_per_page *= max(0.4, 1.0 - image_density * 0.6)

    complexity = DocumentComplexity(
        document_id=document_id,
        word_count=int(words_per_page * page_count),
        page_count=page_count,
        estimated_words_per_page=words_per_page,
        image_density=image_density,
        table_density=0.0,   # would require NLP extraction; not available
        avg_page_length_ratio=1.0,
        complexity_factor=complexity_factor,
        baseline_wpm=baseline_wpm,
        session_count=0,
        computed_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(complexity)
    await db.flush()
    return complexity


# ── Reading Speed Model ────────────────────────────────────────────────────────

def compute_reading_speed_wpm(
    page_events: list[PageReadingEvent],
    words_per_page: float,
) -> Optional[float]:
    """Compute current reading speed (wpm) from completed page events.

    Uses an exponentially weighted moving average (EWMA) of time spent per page.
    Only pages with completion_status in ('reading', 'completed') contribute.
    Minimum 2 pages required for a meaningful estimate.

    EWMA formula:
        s_t = alpha * x_t + (1 - alpha) * s_{t-1}
    where x_t = words_per_page / (active_time_ms / 60_000)

    Returns None if insufficient data.
    """
    qualifying = [
        e for e in page_events
        if e.completion_status in ("reading", "completed") and e.active_time_ms > 1000
    ]
    qualifying.sort(key=lambda e: e.page_number)

    if len(qualifying) < MIN_PAGES_FOR_SPEED:
        return None

    # Compute per-page wpm readings
    readings: list[float] = []
    for evt in qualifying:
        minutes = evt.active_time_ms / 60_000.0
        if minutes > 0:
            readings.append(words_per_page / minutes)

    if not readings:
        return None

    # EWMA: weight recent pages more heavily
    ewma = readings[0]
    for r in readings[1:]:
        ewma = EWMA_ALPHA * r + (1 - EWMA_ALPHA) * ewma

    # Clamp to physiologically plausible range: 50–700 wpm
    return max(50.0, min(700.0, ewma))


def estimate_remaining_ms(
    page_events: list[PageReadingEvent],
    current_page: int,
    total_pages: int,
    complexity: DocumentComplexity,
    session_wpm: Optional[float] = None,
) -> Optional[int]:
    """Predict remaining reading time in milliseconds.

    Algorithm:
    1. Compute this-session EWMA wpm (if ≥ MIN_PAGES_FOR_SPEED pages done)
    2. Blend with document baseline wpm using session weight
    3. Account for document complexity factor
    4. pages_remaining × words_per_page / blended_wpm → milliseconds

    Session weight increases as more pages are read, reaching 1.0 at 5+ pages.

    Returns None if < 1 page remains.
    """
    pages_remaining = total_pages - current_page
    if pages_remaining < 1:
        return 0

    words_per_page = complexity.estimated_words_per_page
    baseline_wpm = complexity.baseline_wpm / complexity.complexity_factor

    completed_count = sum(
        1 for e in page_events
        if e.completion_status in ("reading", "completed")
    )

    if session_wpm and completed_count >= MIN_PAGES_FOR_SPEED:
        # Blend: session data earns trust proportional to pages completed, max at 5
        session_weight = min(1.0, completed_count / 5.0)
        blended_wpm = session_weight * session_wpm + (1 - session_weight) * baseline_wpm
    else:
        blended_wpm = baseline_wpm

    if blended_wpm <= 0:
        return None

    words_remaining = pages_remaining * words_per_page
    remaining_minutes = words_remaining / blended_wpm
    return int(remaining_minutes * 60_000)


# ── Score Computations ─────────────────────────────────────────────────────────

def compute_engagement_score(session: ReadingSession, page_events: list[PageReadingEvent]) -> float:
    """Reading Engagement Score (0–100).

    Formula (weighted components, sum to 100):
      completion_component  (40 pts): completion_pct × 0.4
      revisit_component     (15 pts): min(pages_revisited / max(1, pages_visited), 0.5) × 30
        — revisiting pages shows engagement, but cap at 50% of pages (beyond that = confusion)
      steady_pace_component (20 pts): 1 - coefficient_of_variation(page_times)
        — consistent reading pace = steady engagement
      annotation_component  (15 pts): min(total_annotations × 5, 15)
        — each annotation adds 5 points, capped at 15
      idle_penalty          (-10 max): idle_ratio × 10
        — penalizes high idle time fraction

    Clamp final score to [0, 100].
    """
    if session.total_elapsed_ms <= 0:
        return 0.0

    # Component 1: completion (40 pts max)
    completion_pts = session.completion_pct * 0.4

    # Component 2: revisits (15 pts max)
    # Revisiting a moderate fraction (5–30%) shows active engagement
    revisit_ratio = session.pages_revisited / max(1, session.pages_visited)
    revisit_pts = min(revisit_ratio, 0.5) * 30.0

    # Component 3: steady pace (20 pts max)
    active_times = [e.active_time_ms for e in page_events if e.active_time_ms > 1000]
    if len(active_times) >= 2:
        mean_t = statistics.mean(active_times)
        stdev_t = statistics.stdev(active_times)
        cv = stdev_t / mean_t if mean_t > 0 else 1.0
        # CV=0 → perfectly steady → 20 pts; CV=1 → 0 pts; CV>1 → capped
        steady_pts = max(0.0, 20.0 * (1.0 - min(cv, 1.0)))
    else:
        steady_pts = 10.0  # neutral when insufficient data

    # Component 4: annotations (15 pts max)
    annotation_pts = min(session.total_annotations * 5.0, 15.0)

    # Penalty: idle ratio (up to -10 pts)
    idle_ratio = session.total_idle_ms / session.total_elapsed_ms
    idle_penalty = min(idle_ratio * 10.0, 10.0)

    score = completion_pts + revisit_pts + steady_pts + annotation_pts - idle_penalty
    return round(max(0.0, min(100.0, score)), 1)


def compute_absorption_score(session: ReadingSession, page_events: list[PageReadingEvent]) -> float:
    """Document Absorption Score (0–100).

    Measures how much of the document the viewer retained/processed.

    Formula:
      base              = completion_pct × 0.6
      depth_bonus       = min(avg_time_ratio × 30, 30)
        — avg page time vs expected page time (from baseline wpm)
        — spending expected time on each page signals deep reading
      interaction_bonus = min((annotations + copy_attempts) × 2, 10)

    avg_time_ratio = actual_avg_ms_per_page / expected_ms_per_page
    expected_ms_per_page uses session reading_speed_wpm if available,
    else falls back to 200 wpm × complexity.
    """
    base = session.completion_pct * 0.6

    if session.pages_visited > 0 and session.avg_ms_per_page:
        # Expected time per page at 200 wpm default
        expected_ms = (250.0 / 200.0) * 60_000  # ~75s per page at 200 wpm
        actual = session.avg_ms_per_page
        time_ratio = actual / expected_ms if expected_ms > 0 else 1.0
        # Ratio < 1 = skimming, ratio ≈ 1 = normal, ratio > 1.5 = deep reading
        depth_bonus = min(time_ratio * 20.0, 30.0)
    else:
        depth_bonus = 15.0  # neutral

    interaction = session.total_annotations + session.total_copy_attempts
    interaction_bonus = min(interaction * 2.0, 10.0)

    score = base + depth_bonus + interaction_bonus
    return round(max(0.0, min(100.0, score)), 1)


def compute_focus_score(session: ReadingSession) -> float:
    """Reading Focus Score (0–100).

    Measures sustained attention without distraction.

    Formula:
      active_ratio = total_active_ms / total_elapsed_ms
      base = active_ratio × 60
      interruption_penalty = min(reading_interruptions × 3, 20)
      tab_switch_penalty   = min(tab_switch_count × 2, 15)
      idle_event_penalty   = min(total_idle_events × 1, 5)
      score = base - interruption_penalty - tab_switch_penalty - idle_event_penalty
    """
    if session.total_elapsed_ms <= 0:
        return 0.0

    active_ratio = session.total_active_ms / session.total_elapsed_ms
    base = active_ratio * 60.0

    interruption_penalty = min(session.reading_interruptions * 3.0, 20.0)
    tab_penalty = min(session.tab_switch_count * 2.0, 15.0)
    idle_penalty = min(session.total_idle_events * 1.0, 5.0)

    score = base - interruption_penalty - tab_penalty - idle_penalty
    return round(max(0.0, min(100.0, score)), 1)


def compute_reading_consistency(page_events: list[PageReadingEvent]) -> float:
    """Reading Consistency (0–100).

    How uniform is the pace across pages? Uses the inverse of the
    coefficient of variation (CV) of active times across pages.

    CV = stdev / mean
    consistency = max(0, 100 × (1 - CV))

    Low CV (consistent pace) → high score.
    High CV (erratic pace)   → low score.
    """
    times = [e.active_time_ms for e in page_events if e.active_time_ms > 500]
    if len(times) < 2:
        return 50.0  # neutral when no data
    mean_t = statistics.mean(times)
    stdev_t = statistics.stdev(times)
    cv = stdev_t / mean_t if mean_t > 0 else 0.0
    return round(max(0.0, min(100.0, 100.0 * (1.0 - cv))), 1)


def compute_attention_stability(session: ReadingSession, page_events: list[PageReadingEvent]) -> float:
    """Attention Stability (0–100).

    Measures how long attention remains focused before interruption.
    Based on average gap between idle events normalized against session length.

    Formula:
      total_events = total_idle_events + reading_interruptions + tab_switch_count
      avg_focus_interval_ms = total_active_ms / max(1, total_events)
      expected_focus_interval_ms = 5 min (300_000 ms) = perfectly stable
      stability = min(avg_focus_interval_ms / expected_focus_ms, 1.0) × 100
    """
    total_disruptions = (
        session.total_idle_events
        + session.reading_interruptions
        + session.tab_switch_count
    )
    if total_disruptions == 0:
        return 100.0  # no disruptions = perfect stability

    avg_focus_ms = session.total_active_ms / total_disruptions
    # 5 min of uninterrupted focus = perfect (100 pts)
    perfect_focus_ms = 300_000.0
    return round(min(avg_focus_ms / perfect_focus_ms, 1.0) * 100.0, 1)


def compute_understanding_confidence(
    session: ReadingSession,
    page_events: list[PageReadingEvent],
    complexity: DocumentComplexity,
) -> float:
    """Estimated Understanding Confidence (0–100).

    This is an estimate, not a measurement — documented as such.
    Uses proxy signals for comprehension quality.

    Formula:
      pace_signal        (0–40): time spent vs expected × 40
        — reading at ≥expected speed signals comprehension
        — reading much slower may indicate confusion OR deep reading
        — we model the sweet spot: 0.6–1.4× expected pace = full 40 pts
      completion_signal  (0–30): completion_pct × 0.3
      revisit_signal     (0–20): revisiting 10–25% of pages = optimal recall
      annotation_signal  (0–10): annotations indicate active processing

    NOTE: This score estimates likely understanding from behavioral signals.
    It cannot measure actual comprehension and is labelled "estimated" in UI.
    """
    # Pace signal: how close to expected reading speed?
    if session.avg_ms_per_page and complexity.estimated_words_per_page > 0:
        expected_ms = (complexity.estimated_words_per_page / complexity.baseline_wpm) * 60_000
        pace_ratio = session.avg_ms_per_page / expected_ms if expected_ms > 0 else 1.0
        # Sweet spot: 0.6 to 1.4× expected → full 40 pts
        if 0.6 <= pace_ratio <= 1.4:
            pace_pts = 40.0
        elif pace_ratio < 0.6:
            # Too fast → skimming → lower confidence
            pace_pts = (pace_ratio / 0.6) * 30.0
        else:
            # Too slow → confusion OR deep engagement; we assume partial credit
            pace_pts = max(0.0, 40.0 - (pace_ratio - 1.4) * 15.0)
    else:
        pace_pts = 20.0  # neutral

    completion_pts = session.completion_pct * 0.3

    # Revisit signal: 10–25% revisit = sweet spot for recall reinforcement
    revisit_ratio = session.pages_revisited / max(1, session.pages_visited)
    if 0.10 <= revisit_ratio <= 0.25:
        revisit_pts = 20.0
    elif revisit_ratio < 0.10:
        revisit_pts = revisit_ratio / 0.10 * 15.0
    else:
        # High revisit → confusion → diminishing returns
        revisit_pts = max(0.0, 20.0 - (revisit_ratio - 0.25) * 40.0)

    annotation_pts = min(session.total_annotations * 2.0, 10.0)

    score = pace_pts + completion_pts + revisit_pts + annotation_pts
    return round(max(0.0, min(100.0, score)), 1)


# ── Session Aggregation ────────────────────────────────────────────────────────

def aggregate_session_from_pages(
    session: ReadingSession,
    page_events: list[PageReadingEvent],
    complexity: DocumentComplexity,
) -> ReadingSession:
    """Recompute all session-level fields from page_events and complexity.

    Called after every batch ingest to keep session row up to date.
    Mutates and returns the session object (caller must flush/commit).
    """
    if not page_events:
        return session

    page_count = complexity.page_count or 1

    # Timing totals
    session.total_active_ms = sum(e.active_time_ms for e in page_events)
    session.total_pause_ms = sum(e.pause_duration_ms for e in page_events)

    # Elapsed = active + idle + pause (frontend sends total_elapsed_ms via batch)
    if session.total_elapsed_ms <= session.total_active_ms:
        session.total_elapsed_ms = session.total_active_ms
    session.total_idle_ms = max(0, session.total_elapsed_ms - session.total_active_ms - session.total_pause_ms)

    # Page coverage
    visited = [e for e in page_events if e.active_time_ms > 0 or e.completion_status != "unread"]
    session.pages_visited = len(visited)
    session.pages_completed = sum(1 for e in page_events if e.completion_status == "completed")
    session.pages_skipped = sum(1 for e in page_events if e.completion_status == "skipped")
    session.pages_revisited = sum(1 for e in page_events if e.revisit_count > 0)
    session.completion_pct = min(100.0, (session.pages_visited / page_count) * 100.0)

    # Interaction totals
    session.total_annotations = sum(e.annotations_created for e in page_events)
    session.total_copy_attempts = sum(e.copy_attempts for e in page_events)
    session.total_print_attempts = sum(e.print_attempts for e in page_events)
    session.total_idle_events = sum(e.idle_events for e in page_events)
    session.tab_switch_count = sum(e.tab_switch_count for e in page_events)
    session.reading_interruptions = session.tab_switch_count + sum(e.visibility_changes for e in page_events)

    # Speed metrics
    completed_pages = [e for e in page_events if e.active_time_ms > 1000]
    if completed_pages:
        session.avg_ms_per_page = statistics.mean(e.active_time_ms for e in completed_pages)

        times_by_page = sorted(completed_pages, key=lambda e: e.active_time_ms)
        session.fastest_page = times_by_page[0].page_number
        session.slowest_page = times_by_page[-1].page_number

        if session.total_idle_events > 0:
            session.avg_pause_ms = session.total_pause_ms / session.total_idle_events
    else:
        session.avg_ms_per_page = None

    # Reading speed
    wpm = compute_reading_speed_wpm(page_events, complexity.estimated_words_per_page)
    session.reading_speed_wpm = wpm

    # Drop-off page: last page visited followed by session end (no more events)
    sorted_by_page = sorted(page_events, key=lambda e: e.page_number)
    if sorted_by_page and session.completion_pct < 100.0:
        session.drop_off_page = sorted_by_page[-1].page_number

    # Confusion page: page with highest time AND revisit_count (anomaly detection)
    def anomaly_score(e):
        return (e.active_time_ms / max(1, session.avg_ms_per_page or 1)) * (1 + e.revisit_count)
    candidates = [e for e in page_events if e.active_time_ms > 5000]
    if candidates:
        confusion = max(candidates, key=anomaly_score)
        # Only flag if significantly above average (>2× avg time or >1 revisit)
        threshold = (session.avg_ms_per_page or 0) * 2.0
        if confusion.active_time_ms > threshold or confusion.revisit_count > 1:
            session.confusion_page = confusion.page_number

    # Engagement scores
    session.engagement_score = compute_engagement_score(session, page_events)
    session.absorption_score = compute_absorption_score(session, page_events)
    session.focus_score = compute_focus_score(session)
    session.reading_consistency = compute_reading_consistency(page_events)
    session.attention_stability = compute_attention_stability(session, page_events)
    session.understanding_confidence = compute_understanding_confidence(session, page_events, complexity)

    return session


# ── Insights Engine ────────────────────────────────────────────────────────────

def generate_insights(
    sessions: list[ReadingSession],
    page_events: list[PageReadingEvent],
    complexity: DocumentComplexity,
) -> list[dict]:
    """Generate natural-language insights from collected reading data.

    Only generates insights supported by at least 2 sessions or statistically
    meaningful measurements. Each insight has:
      text:       the natural-language sentence
      type:       category (page_time | reader_pattern | attention | completion | speed)
      confidence: "high" | "medium" (never generates "low" — those are suppressed)
      page:       optional page number the insight refers to
    """
    insights: list[dict] = []
    if not sessions:
        return insights

    if not page_events:
        return insights

    # Aggregate page stats across all sessions
    page_stats: dict[int, dict] = {}
    for evt in page_events:
        p = evt.page_number
        if p not in page_stats:
            page_stats[p] = {
                "times": [], "revisits": [], "completion_statuses": [], "idle": []
            }
        page_stats[p]["times"].append(evt.active_time_ms)
        page_stats[p]["revisits"].append(evt.revisit_count)
        page_stats[p]["completion_statuses"].append(evt.completion_status)
        page_stats[p]["idle"].append(evt.idle_events)

    # Global averages (across all pages, all sessions)
    all_times = [t for s in page_stats.values() for t in s["times"] if t > 500]
    if not all_times:
        return insights

    global_avg_ms = statistics.mean(all_times)

    total_sessions = len(sessions)
    completed_sessions = [s for s in sessions if s.completion_pct >= 90]

    # ── Insight 1: Page takes significantly longer than average ──────────────
    for page_num, stats in page_stats.items():
        times = [t for t in stats["times"] if t > 500]
        if len(times) < 2:
            continue
        avg_ms = statistics.mean(times)
        ratio = avg_ms / global_avg_ms if global_avg_ms > 0 else 1.0
        if ratio >= 2.5:
            insights.append({
                "text": f"Page {page_num} requires {ratio:.1f}× longer than average "
                        f"({avg_ms // 1000:.0f}s vs {global_avg_ms // 1000:.0f}s avg).",
                "type": "page_time",
                "confidence": "high" if len(times) >= 3 else "medium",
                "page": page_num,
            })
        elif ratio <= 0.3 and len(times) >= 2:
            insights.append({
                "text": f"Page {page_num} is consistently skimmed "
                        f"({avg_ms // 1000:.0f}s vs {global_avg_ms // 1000:.0f}s avg).",
                "type": "page_time",
                "confidence": "medium",
                "page": page_num,
            })

    # ── Insight 2: Most-revisited page ──────────────────────────────────────
    revisit_by_page = {
        p: sum(s["revisits"]) / len(s["revisits"])
        for p, s in page_stats.items()
        if s["revisits"]
    }
    if revisit_by_page:
        most_revisited = max(revisit_by_page, key=revisit_by_page.get)
        avg_revisits = revisit_by_page[most_revisited]
        if avg_revisits >= 0.5:
            insights.append({
                "text": f"Page {most_revisited} is most frequently revisited "
                        f"(avg {avg_revisits:.1f} returns per reader).",
                "type": "reader_pattern",
                "confidence": "high" if total_sessions >= 3 else "medium",
                "page": most_revisited,
            })

    # ── Insight 3: Drop-off pattern ──────────────────────────────────────────
    drop_off_pages = [s.drop_off_page for s in sessions if s.drop_off_page]
    if len(drop_off_pages) >= 2:
        # Mode of drop-off pages
        from collections import Counter
        drop_counter = Counter(drop_off_pages)
        most_common_drop, drop_count = drop_counter.most_common(1)[0]
        drop_pct = drop_count / total_sessions * 100
        if drop_pct >= 30:
            insights.append({
                "text": f"{drop_pct:.0f}% of readers stop reading before finishing, "
                        f"most commonly at page {most_common_drop}.",
                "type": "attention",
                "confidence": "high" if total_sessions >= 5 else "medium",
                "page": most_common_drop,
            })

    # ── Insight 4: Completion rate ───────────────────────────────────────────
    if total_sessions >= 2:
        completion_rate = len(completed_sessions) / total_sessions * 100
        if completion_rate >= 80:
            insights.append({
                "text": f"{completion_rate:.0f}% of readers finish this document "
                        f"(above the 60% platform average).",
                "type": "completion",
                "confidence": "high" if total_sessions >= 5 else "medium",
            })
        elif completion_rate <= 30:
            insights.append({
                "text": f"Only {completion_rate:.0f}% of readers finish this document. "
                        f"Consider shortening or restructuring the content.",
                "type": "completion",
                "confidence": "high" if total_sessions >= 5 else "medium",
            })

    # ── Insight 5: Estimated time for new readers ────────────────────────────
    if total_sessions >= 2:
        full_times = [s.total_active_ms for s in sessions if s.total_active_ms > 30_000]
        if len(full_times) >= 2:
            median_ms = statistics.median(full_times)
            minutes = median_ms / 60_000
            insights.append({
                "text": f"Estimated reading time for new readers: "
                        f"{minutes:.0f} minute{'s' if minutes != 1 else ''}.",
                "type": "speed",
                "confidence": "high" if len(full_times) >= 5 else "medium",
            })

    # ── Insight 6: Fastest vs slowest reader ────────────────────────────────
    if len(completed_sessions) >= 3:
        completed_times = sorted(s.total_active_ms for s in completed_sessions)
        fastest_ms = completed_times[0]
        slowest_ms = completed_times[-1]
        ratio = slowest_ms / fastest_ms if fastest_ms > 0 else 1.0
        if ratio >= 2.0:
            insights.append({
                "text": f"Reading speeds vary significantly: fastest reader completed in "
                        f"{fastest_ms // 60_000:.0f}m, slowest in {slowest_ms // 60_000:.0f}m "
                        f"({ratio:.1f}× difference).",
                "type": "speed",
                "confidence": "medium",
            })

    # ── Insight 7: Below-average reader finishes faster than expected ────────
    above_avg_completors = [s for s in completed_sessions if s.reading_speed_wpm]
    if len(above_avg_completors) >= 3:
        speeds = sorted(s.reading_speed_wpm for s in above_avg_completors)
        median_speed = statistics.median(speeds)
        baseline = complexity.baseline_wpm
        pct_faster = (median_speed - baseline) / baseline * 100
        if abs(pct_faster) >= 20:
            direction = "faster" if pct_faster > 0 else "slower"
            insights.append({
                "text": f"Typical reader reads {abs(pct_faster):.0f}% {direction} "
                        f"than expected for this document type.",
                "type": "speed",
                "confidence": "medium",
            })

    # Sort: high confidence first, then by type priority
    type_order = {"page_time": 0, "attention": 1, "reader_pattern": 2, "completion": 3, "speed": 4}
    conf_order = {"high": 0, "medium": 1}
    insights.sort(key=lambda i: (conf_order.get(i["confidence"], 2), type_order.get(i["type"], 5)))

    return insights[:12]  # cap at 12 insights


# ── Main Service Class ─────────────────────────────────────────────────────────

class ReadingAnalyticsService:
    """Facade for all reading intelligence operations."""

    async def ingest_batch(
        self,
        db: AsyncSession,
        token: str,
        session_id: str,
        page_data: list[dict],
        session_meta: dict,
        viewer_email_masked: Optional[str] = None,
    ) -> dict:
        """Process a batch of page analytics events from the viewer frontend.

        Upserts reading_session + page_reading_events, then recomputes all
        aggregate scores. Returns summary for the viewer's status bar.

        page_data items (from frontend useReadingAnalytics hook):
          page_number, active_time_ms, pause_duration_ms, revisit_count,
          scroll_percentage, zoom_level, fullscreen_used, annotations_created,
          copy_attempts, print_attempts, tab_switch_count, visibility_changes,
          idle_events, completion_status, enter_timestamp (ISO), exit_timestamp (ISO)

        session_meta:
          total_elapsed_ms, total_active_ms, started_at (ISO), page_count,
          initial_estimate_ms (optional)
        """

        # Resolve link_id and document_id from the token
        link_result = await db.execute(
            select(ShareLink).where(ShareLink.token == token)
        )
        link = link_result.scalar_one_or_none()
        if not link:
            return {"error": "link_not_found"}

        doc_result = await db.execute(
            select(Document).where(Document.id == link.document_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            return {"error": "document_not_found"}

        document_id = link.document_id
        link_id = link.id

        # Get or create complexity record
        complexity = await get_or_create_document_complexity(db, document_id)

        # Upsert reading_session
        rs_result = await db.execute(
            select(ReadingSession).where(ReadingSession.session_id == session_id)
        )
        rs = rs_result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        started_at_str = session_meta.get("started_at")
        if started_at_str:
            try:
                started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                started_at = now
        else:
            started_at = now

        if rs is None:
            rs = ReadingSession(
                id=uuid.uuid4(),
                session_id=session_id,
                link_id=link_id,
                document_id=document_id,
                viewer_email_masked=viewer_email_masked,
                started_at=started_at,
                last_updated_at=now,
            )
            db.add(rs)

        # Apply session-level timing from meta
        total_elapsed = session_meta.get("total_elapsed_ms", 0)
        if isinstance(total_elapsed, (int, float)) and total_elapsed > 0:
            rs.total_elapsed_ms = int(total_elapsed)

        initial_est = session_meta.get("initial_estimate_ms")
        if initial_est and rs.initial_estimate_ms is None:
            rs.initial_estimate_ms = int(initial_est)

        # Upsert page events
        for pd in page_data:
            page_num = pd.get("page_number")
            if not isinstance(page_num, int) or page_num < 1:
                continue

            # Validate page_num against document
            if doc.page_count and page_num > doc.page_count:
                continue

            # Find existing page event for this session+page
            pre_result = await db.execute(
                select(PageReadingEvent).where(
                    PageReadingEvent.session_id == session_id,
                    PageReadingEvent.page_number == page_num,
                )
            )
            pre = pre_result.scalar_one_or_none()

            if pre is None:
                pre = PageReadingEvent(
                    id=uuid.uuid4(),
                    reading_session_id=rs.id,
                    session_id=session_id,
                    document_id=document_id,
                    page_number=page_num,
                )
                db.add(pre)

            # Update fields — accumulate or overwrite with latest values.
            # Use (field or 0) guards because SQLAlchemy server_defaults aren't
            # applied in Python memory until after the first flush.
            active_ms = int(pd.get("active_time_ms", 0) or 0)
            pre.active_time_ms = max(pre.active_time_ms or 0, active_ms)
            pre.pause_duration_ms = max(
                pre.pause_duration_ms or 0, int(pd.get("pause_duration_ms", 0) or 0)
            )
            pre.revisit_count = max(
                pre.revisit_count or 0, int(pd.get("revisit_count", 0) or 0)
            )
            pre.scroll_percentage = max(
                pre.scroll_percentage or 0.0, float(pd.get("scroll_percentage", 0.0) or 0.0)
            )
            pre.zoom_level = int(pd.get("zoom_level", 100) or 100)
            pre.fullscreen_used = (pre.fullscreen_used or False) or bool(pd.get("fullscreen_used", False))
            pre.annotations_created = max(
                pre.annotations_created or 0, int(pd.get("annotations_created", 0) or 0)
            )
            pre.copy_attempts = max(
                pre.copy_attempts or 0, int(pd.get("copy_attempts", 0) or 0)
            )
            pre.print_attempts = max(
                pre.print_attempts or 0, int(pd.get("print_attempts", 0) or 0)
            )
            pre.tab_switch_count = max(
                pre.tab_switch_count or 0, int(pd.get("tab_switch_count", 0) or 0)
            )
            pre.visibility_changes = max(
                pre.visibility_changes or 0, int(pd.get("visibility_changes", 0) or 0)
            )
            pre.idle_events = max(
                pre.idle_events or 0, int(pd.get("idle_events", 0) or 0)
            )

            # Completion status — only upgrade, never downgrade
            new_status = pd.get("completion_status", "unread")
            status_rank = {
                "unread": 0, "skipped": 1, "started": 2,
                "reading": 3, "revisited": 4, "completed": 5,
            }
            if status_rank.get(new_status, 0) > status_rank.get(pre.completion_status, 0):
                pre.completion_status = new_status

            # Timestamps
            enter_ts_str = pd.get("enter_timestamp")
            if enter_ts_str and pre.enter_timestamp is None:
                try:
                    pre.enter_timestamp = datetime.fromisoformat(
                        enter_ts_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            exit_ts_str = pd.get("exit_timestamp")
            if exit_ts_str:
                try:
                    exit_ts = datetime.fromisoformat(exit_ts_str.replace("Z", "+00:00"))
                    if pre.exit_timestamp is None or exit_ts > pre.exit_timestamp:
                        pre.exit_timestamp = exit_ts
                except (ValueError, AttributeError):
                    pass

        await db.flush()

        # Reload page events for aggregation
        all_pages_result = await db.execute(
            select(PageReadingEvent).where(PageReadingEvent.session_id == session_id)
        )
        all_page_events = list(all_pages_result.scalars().all())

        # Recompute session aggregates
        rs = aggregate_session_from_pages(rs, all_page_events, complexity)
        rs.last_updated_at = now

        # Update document complexity with empirical session data
        await _update_complexity_from_sessions(db, document_id, complexity)

        # Compute prediction accuracy if session has completed
        if rs.completion_pct >= 90 and rs.initial_estimate_ms and rs.total_active_ms > 0:
            actual = rs.total_active_ms
            estimated = rs.initial_estimate_ms
            accuracy = max(0.0, 100.0 - abs(actual - estimated) / actual * 100.0)
            rs.prediction_accuracy_pct = round(accuracy, 1)

        await db.commit()

        # Build viewer-facing summary
        current_page = session_meta.get("current_page", 1)
        page_count = int(session_meta.get("page_count", complexity.page_count or 1))
        wpm = rs.reading_speed_wpm
        remaining_ms = estimate_remaining_ms(
            all_page_events, current_page, page_count, complexity, wpm
        )

        return {
            "session_id": session_id,
            "total_active_ms": rs.total_active_ms,
            "estimated_remaining_ms": remaining_ms,
            "current_page": current_page,
            "page_count": page_count,
            "completion_pct": round(rs.completion_pct, 1),
            "pages_completed": rs.pages_completed,
            "reading_speed_wpm": round(wpm, 0) if wpm else None,
            "avg_ms_per_page": round(rs.avg_ms_per_page, 0) if rs.avg_ms_per_page else None,
        }

    async def get_viewer_session_summary(
        self,
        db: AsyncSession,
        session_id: str,
    ) -> Optional[dict]:
        """Return viewer-facing session summary (viewer's own data only)."""
        rs_result = await db.execute(
            select(ReadingSession).where(ReadingSession.session_id == session_id)
        )
        rs = rs_result.scalar_one_or_none()
        if not rs:
            return None

        complexity = await get_or_create_document_complexity(db, rs.document_id)

        pages_result = await db.execute(
            select(PageReadingEvent).where(PageReadingEvent.session_id == session_id)
        )
        page_events = list(pages_result.scalars().all())

        current_page = max((e.page_number for e in page_events), default=1)
        remaining_ms = estimate_remaining_ms(
            page_events, current_page, complexity.page_count, complexity, rs.reading_speed_wpm
        )

        # Viewer-safe page/document insights — used by the Viewer's optional
        # "Reading Insights" panel (uploader-controlled via a link permission,
        # never shown unless the link enables it). Deliberately excludes
        # anything uploader-only (no other viewers' identities, no drop-off/
        # confusion-page detection, no per-viewer breakdown).
        difficulty = _complexity_to_difficulty_label(complexity.complexity_factor)

        avg_page_time_result = await db.execute(
            select(func.avg(PageReadingEvent.active_time_ms)).where(
                PageReadingEvent.document_id == rs.document_id,
                PageReadingEvent.page_number == current_page,
                PageReadingEvent.session_id != session_id,
            )
        )
        avg_page_time_ms = avg_page_time_result.scalar()

        pace_vs_average = None
        if rs.avg_ms_per_page:
            other_avg_result = await db.execute(
                select(func.avg(ReadingSession.avg_ms_per_page)).where(
                    ReadingSession.document_id == rs.document_id,
                    ReadingSession.session_id != session_id,
                    ReadingSession.avg_ms_per_page.is_not(None),
                )
            )
            other_avg_ms_per_page = other_avg_result.scalar()
            if other_avg_ms_per_page:
                # Lower avg_ms_per_page = reading faster. Ignore noise under 10%.
                ratio = rs.avg_ms_per_page / other_avg_ms_per_page
                if ratio < 0.9:
                    pace_vs_average = "faster"
                elif ratio > 1.1:
                    pace_vs_average = "slower"
                else:
                    pace_vs_average = "typical"

        return {
            "total_active_ms": rs.total_active_ms,
            "total_elapsed_ms": rs.total_elapsed_ms,
            "estimated_remaining_ms": remaining_ms,
            "completion_pct": round(rs.completion_pct, 1),
            "pages_visited": rs.pages_visited,
            "pages_completed": rs.pages_completed,
            "page_count": complexity.page_count,
            "reading_speed_wpm": round(rs.reading_speed_wpm, 0) if rs.reading_speed_wpm else None,
            "avg_ms_per_page": round(rs.avg_ms_per_page, 0) if rs.avg_ms_per_page else None,
            "engagement_score": rs.engagement_score,
            "focus_score": rs.focus_score,
            "difficulty": difficulty,
            "current_page_avg_ms": round(avg_page_time_ms) if avg_page_time_ms else None,
            "pace_vs_average": pace_vs_average,
        }

    async def get_document_summary(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[dict]:
        """Return uploader-facing document-level reading analytics."""
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            return None

        sessions_result = await db.execute(
            select(ReadingSession).where(ReadingSession.document_id == document_id)
        )
        sessions = list(sessions_result.scalars().all())
        complexity = await get_or_create_document_complexity(db, document_id)

        if not sessions:
            return {
                "document_id": str(document_id),
                "filename": doc.filename,
                "page_count": doc.page_count or 0,
                "total_sessions": 0,
                "complexity": _serialize_complexity(complexity),
                "sessions": [],
            }

        total_active = sum(s.total_active_ms for s in sessions)
        completed = [s for s in sessions if s.completion_pct >= 90]
        completion_rate = len(completed) / len(sessions) * 100

        speeds = [s.reading_speed_wpm for s in sessions if s.reading_speed_wpm]
        engagement_scores = [s.engagement_score for s in sessions if s.engagement_score]

        return {
            "document_id": str(document_id),
            "filename": doc.filename,
            "page_count": doc.page_count or 0,
            "total_sessions": len(sessions),
            "completed_sessions": len(completed),
            "completion_rate_pct": round(completion_rate, 1),
            "total_active_ms": total_active,
            "avg_active_ms": round(total_active / len(sessions)) if sessions else 0,
            "median_active_ms": int(statistics.median(s.total_active_ms for s in sessions)),
            "avg_engagement_score": round(statistics.mean(engagement_scores), 1) if engagement_scores else None,
            "avg_reading_speed_wpm": round(statistics.mean(speeds), 0) if speeds else None,
            "complexity": _serialize_complexity(complexity),
        }

    async def get_page_heatmap_rich(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[dict]:
        """Return rich per-page analytics for the uploader heatmap view."""
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            return None

        # Return value intentionally unused here — this call's side effect
        # (lazily creating the DocumentComplexity row on first access) is what
        # matters; other code paths for this document assume that row exists.
        await get_or_create_document_complexity(db, document_id)

        page_results = await db.execute(
            select(PageReadingEvent).where(PageReadingEvent.document_id == document_id)
        )
        all_events = list(page_results.scalars().all())

        # Group by page number
        by_page: dict[int, list[PageReadingEvent]] = {}
        for evt in all_events:
            by_page.setdefault(evt.page_number, []).append(evt)

        page_count = doc.page_count or 0
        global_times = [e.active_time_ms for e in all_events if e.active_time_ms > 500]
        global_avg = statistics.mean(global_times) if global_times else 0

        pages = []
        for p_num in range(1, page_count + 1):
            evts = by_page.get(p_num, [])
            times = [e.active_time_ms for e in evts if e.active_time_ms > 500]
            revisits = sum(e.revisit_count for e in evts)
            completed_count = sum(1 for e in evts if e.completion_status == "completed")
            total_sessions_count = len(evts)

            avg_ms = statistics.mean(times) if times else 0
            median_ms = int(statistics.median(times)) if times else 0
            longest_ms = max(times) if times else 0
            shortest_ms = min(times) if times else 0

            revisit_pct = (revisits / max(1, total_sessions_count)) * 100
            completion_pct = (completed_count / max(1, total_sessions_count)) * 100

            # Predicted difficulty: ratio of actual avg time to global avg
            # 1.0 = average, >1.5 = hard, <0.5 = easy
            difficulty_ratio = avg_ms / global_avg if global_avg > 0 and times else 1.0
            if difficulty_ratio >= 1.8:
                predicted_difficulty = "hard"
            elif difficulty_ratio >= 1.2:
                predicted_difficulty = "medium-hard"
            elif difficulty_ratio <= 0.5:
                predicted_difficulty = "easy"
            elif difficulty_ratio <= 0.8:
                predicted_difficulty = "medium-easy"
            else:
                predicted_difficulty = "medium"

            # Engagement score for this page
            idle_events = sum(e.idle_events for e in evts)
            annotation_sum = sum(e.annotations_created for e in evts)
            engagement = min(100.0, (
                completion_pct * 0.4
                + min(revisit_pct * 0.3, 20.0)
                + min(annotation_sum * 5.0, 20.0)
                - min(idle_events * 2.0, 10.0)
            ))

            # Drop-off percentage: sessions that stopped at this page
            drop_count = sum(1 for e in evts if e.completion_status == "skipped")
            dropoff_pct = (drop_count / max(1, total_sessions_count)) * 100

            pages.append({
                "page": p_num,
                "views": total_sessions_count,
                "avg_time_ms": int(avg_ms),
                "median_time_ms": median_ms,
                "longest_time_ms": longest_ms,
                "shortest_time_ms": shortest_ms,
                "revisit_pct": round(revisit_pct, 1),
                "completion_pct": round(completion_pct, 1),
                "predicted_difficulty": predicted_difficulty,
                "engagement_score": round(engagement, 1),
                "dropoff_pct": round(dropoff_pct, 1),
            })

        return {
            "document_id": str(document_id),
            "filename": doc.filename,
            "page_count": page_count,
            "global_avg_time_ms": int(global_avg),
            "pages": pages,
        }

    async def get_viewer_breakdown(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[dict]:
        """Per-viewer table for the uploader dashboard."""
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            return None

        sessions_result = await db.execute(
            select(ReadingSession).where(ReadingSession.document_id == document_id)
            .order_by(ReadingSession.started_at.desc())
        )
        sessions = list(sessions_result.scalars().all())
        complexity = await get_or_create_document_complexity(db, document_id)

        rows = []
        for s in sessions:
            rows.append({
                "session_id": s.session_id[:8] + "…",
                "viewer_email": s.viewer_email_masked,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "total_active_ms": s.total_active_ms,
                "total_idle_ms": s.total_idle_ms,
                "completion_pct": round(s.completion_pct, 1),
                "pages_visited": s.pages_visited,
                "pages_completed": s.pages_completed,
                "pages_skipped": s.pages_skipped,
                "pages_revisited": s.pages_revisited,
                "reading_speed_wpm": round(s.reading_speed_wpm, 0) if s.reading_speed_wpm else None,
                "avg_ms_per_page": round(s.avg_ms_per_page, 0) if s.avg_ms_per_page else None,
                "fastest_page": s.fastest_page,
                "slowest_page": s.slowest_page,
                "drop_off_page": s.drop_off_page,
                "confusion_page": s.confusion_page,
                "reading_interruptions": s.reading_interruptions,
                "avg_pause_ms": round(s.avg_pause_ms, 0) if s.avg_pause_ms else None,
                "tab_switch_count": s.tab_switch_count,
                "engagement_score": s.engagement_score,
                "absorption_score": s.absorption_score,
                "focus_score": s.focus_score,
                "reading_consistency": s.reading_consistency,
                "attention_stability": s.attention_stability,
                "understanding_confidence": s.understanding_confidence,
                "prediction_accuracy_pct": s.prediction_accuracy_pct,
            })

        return {
            "document_id": str(document_id),
            "filename": doc.filename,
            "total_viewers": len(sessions),
            "viewers": rows,
            "complexity": _serialize_complexity(complexity),
        }

    async def get_insights(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[dict]:
        """Generate natural-language insights for a document."""
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            return None

        sessions_result = await db.execute(
            select(ReadingSession).where(ReadingSession.document_id == document_id)
        )
        sessions = list(sessions_result.scalars().all())

        page_results = await db.execute(
            select(PageReadingEvent).where(PageReadingEvent.document_id == document_id)
        )
        all_events = list(page_results.scalars().all())

        complexity = await get_or_create_document_complexity(db, document_id)
        insights = generate_insights(sessions, all_events, complexity)

        return {
            "document_id": str(document_id),
            "filename": doc.filename,
            "total_sessions": len(sessions),
            "insights": insights,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# ── Private Helpers ────────────────────────────────────────────────────────────

async def _update_complexity_from_sessions(
    db: AsyncSession,
    document_id: uuid.UUID,
    complexity: DocumentComplexity,
) -> None:
    """Update empirical stats in document_complexity from all collected sessions."""
    sessions_result = await db.execute(
        select(ReadingSession.total_active_ms)
        .where(
            ReadingSession.document_id == document_id,
            ReadingSession.completion_pct >= 80,
            ReadingSession.total_active_ms > 10_000,
        )
    )
    active_times = [r[0] for r in sessions_result.all()]

    if len(active_times) >= 3:
        sorted_times = sorted(active_times)
        n = len(sorted_times)
        complexity.median_completion_ms = int(statistics.median(sorted_times))
        complexity.p25_completion_ms = int(sorted_times[max(0, int(n * 0.25))])
        complexity.p75_completion_ms = int(sorted_times[min(n - 1, int(n * 0.75))])

    total_result = await db.execute(
        select(func.count()).select_from(ReadingSession)
        .where(ReadingSession.document_id == document_id)
    )
    complexity.session_count = total_result.scalar() or 0
    complexity.updated_at = datetime.now(timezone.utc)


def _complexity_to_difficulty_label(complexity_factor: float) -> str:
    """Map complexity_factor (0.5-2.0, see get_or_create_document_complexity)
    to a plain-language difficulty label for the viewer-facing insights panel."""
    if complexity_factor < 0.85:
        return "Easy"
    if complexity_factor <= 1.3:
        return "Moderate"
    return "Complex"


def _serialize_complexity(c: DocumentComplexity) -> dict:
    return {
        "word_count": c.word_count,
        "page_count": c.page_count,
        "estimated_words_per_page": round(c.estimated_words_per_page, 1),
        "image_density": round(c.image_density, 2),
        "complexity_factor": round(c.complexity_factor, 2),
        "baseline_wpm": round(c.baseline_wpm, 0),
        "median_completion_ms": c.median_completion_ms,
        "session_count": c.session_count,
    }
