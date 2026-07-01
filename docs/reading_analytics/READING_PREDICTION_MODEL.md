# Reading Prediction Model

## Reading Speed Estimation

### Signal Collection

Every 5 seconds, the frontend hook records per-page active time (milliseconds). Pages with `active_time_ms < 1000ms` are filtered out as non-reads (fast navigation, accidental visits).

For each qualifying page:
```
page_wpm = (words_per_page) / (active_time_ms / 60_000)
```

### EWMA Smoothing (α = 0.35)

Raw per-page WPM is noisy. We smooth using Exponentially Weighted Moving Average with α = 0.35 (weights recent pages more heavily while retaining history):

```python
ewma = readings[0]
for r in readings[1:]:
    ewma = α * r + (1 - α) * ewma
# Output clamped to [50, 700] wpm
```

α = 0.35 gives half-life of ~1.6 pages — fast enough to adapt to difficulty changes within a document, stable enough to resist single-page outliers.

### Session Blending

Early in a session (< 5 completed pages), the EWMA may be unreliable. We blend with a document-level baseline WPM:

```python
session_weight = min(1.0, completed_pages / 5.0)
blended_wpm = session_weight * session_wpm + (1 - session_weight) * baseline_wpm
```

`baseline_wpm` comes from `document_complexity.baseline_wpm`, which is initialized from the document's file type:

| Document type | Baseline WPM |
|---|---|
| Plain text (.txt, .md) | 250 |
| PDF | 200 |
| PPTX | 150 |
| DOCX | 220 |
| XLSX | 100 |

---

## Remaining Time Estimation

```python
words_remaining = pages_remaining * words_per_page
remaining_minutes = words_remaining / blended_wpm
remaining_ms = remaining_minutes * 60_000
```

`words_per_page` is estimated from the document's byte size:
```python
bytes_per_page = file_size_bytes / page_count
words_per_page = max(50, min(500, bytes_per_page / 20))
```

---

## Document Complexity

Document complexity adjusts the baseline WPM and affects engagement score interpretation:

```python
bytes_per_page = file_size_bytes / page_count
image_density = min(1.0, bytes_per_page / 200_000.0)

complexity_factor = 1.0
if image_density > 0.5:    complexity_factor += 0.3  # heavy images → slower reading
if file_type == 'xlsx':    complexity_factor += 0.2  # dense tabular data
if file_type == 'pptx':    complexity_factor -= 0.1  # sparse slides → faster

baseline_wpm = baseline_by_type[file_type] / complexity_factor
```

---

## Completion Status Upgrade Model

Page completion status transitions (only upgrade, never downgrade):

```
unread → started  (active_time > 3s)
started → reading (active_time > 15s)
reading → completed (active_time ≥ 0.7 × expected_time_for_page)
any → revisited (page visited more than once)
```

`expected_time_for_page = (words_per_page / baseline_wpm) × 60_000`

The 0.7 coefficient means a page is "completed" when the viewer has spent at least 70% of the expected reading time — allowing for fast readers while catching skimmers.

---

## AI Score Formulas

### Engagement Score (0–100)

```
completion_pts  = completion_pct × 0.4              (max 40)
revisit_pts     = min(revisit_ratio, 0.5) × 30     (max 15)
steady_pts      = 20 × (1 - min(CV, 1.0))          (max 20)
annotation_pts  = min(annotations × 5, 15)          (max 15)
idle_penalty    = min(idle_ratio × 10, 10)           (max -10)

engagement = completion_pts + revisit_pts + steady_pts + annotation_pts - idle_penalty
```

Where:
- `revisit_ratio = pages_revisited / pages_visited`
- `CV = stdev(page_active_times) / mean(page_active_times)` (reading consistency)
- `idle_ratio = total_idle_events / max(1, pages_visited)`

### Focus Score (0–100)

```
base                 = active_ratio × 60
interruption_penalty = min(visibility_changes × 3, 20)
tab_penalty          = min(tab_switches × 2, 15)
idle_penalty         = min(idle_events × 1, 5)

focus = max(0, base - interruption_penalty - tab_penalty - idle_penalty)
```

Where `active_ratio = total_active_ms / max(1, total_elapsed_ms)`

### Reading Consistency (0–100)

Measures how evenly the reader distributes time across pages:

```
CV = stdev(page_active_times) / mean(page_active_times)
consistency = max(0, 100 × (1 - CV))
```

CV = 0 → perfectly even (score 100). CV = 1 → standard deviation equals mean (score 0).

### Attention Stability (0–100)

Measures how long the reader maintains focus between disruptions:

```
total_disruptions = idle_events + visibility_changes + tab_switches
avg_focus_ms      = total_active_ms / max(1, total_disruptions)
stability         = min(avg_focus_ms / 300_000, 1.0) × 100
```

300,000ms = 5 minutes — a reader who sustains focus for 5 minutes between disruptions scores 100.

### Absorption Score (0–100)

Composite of engagement and focus, weighted toward engagement:

```
absorption = 0.6 × engagement_score + 0.4 × focus_score
```

### Understanding Confidence (0–100)

Infers comprehension from pace, completion, revisits, and annotations:

```
pace_ratio      = actual_avg_ms_per_page / expected_ms_per_page
pace_pts        = 40 if 0.6 ≤ pace_ratio ≤ 1.4
                  else 40 × (1 - min(abs(pace_ratio-1.0)-0.4, 1.0))
completion_pts  = completion_pct × 0.3              (max 30)
revisit_pts     = 20 if 0.10 ≤ revisit_ratio ≤ 0.25
                  else 20 × max(0, 1 - abs(revisit_ratio-0.175)/0.25)
annotation_pts  = min(annotations × 2, 10)

understanding = pace_pts + completion_pts + revisit_pts + annotation_pts
```

Sweet spot: reading at 60–140% of expected pace (neither skimming nor struggling), 10–25% of pages revisited (verifying comprehension without confusion), and creating annotations.
