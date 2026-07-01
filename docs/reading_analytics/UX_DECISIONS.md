# UX Decisions — Reading Intelligence Engine

## Viewer Experience

### Always-visible status bar (never intrusive)

**Decision:** Mount the reading status bar below the main viewer canvas, not overlaid on top of it.

**Why:** Overlays compete with the document for attention and cause visual noise. The bottom bar occupies a dedicated 32px strip — always visible, never obscuring content, never requiring dismissal.

**Alternative rejected:** A floating overlay (like many analytics tools use). Rejected because it would cover the bottom of the document and feel like "being watched."

---

### Default: collapsed insights

**Decision:** The "Show Reading Insights" panel is collapsed by default.

**Why:** Most viewers are focused on reading, not self-analysis. The insights are opt-in. A viewer who wants to know their stats can expand the panel; a viewer who doesn't is not distracted.

**Alternative rejected:** Always-expanded panel. Rejected because it adds visual weight and creates the feeling of surveillance.

---

### Timer starts only after document is ready and first page visible

**Decision:** `isDocumentReady = session && imgReady` — the timer does not start until the session exists AND the first page image has fired `onLoad`.

**Why:** Time spent waiting for the document to load is not reading time. If the document takes 3 seconds to load, the viewer should not be "charged" for that time. This matches how Kindle measures reading time.

**Technical implementation:** `imgReady` state in `usePageLoader` is set to `true` in the `onLoad` handler of the page image. `useReadingAnalytics` receives this as the `isDocumentReady` prop and only calls `_resume()` when both are true.

---

### Active-only timing with automatic pause

**Decision:** The timer pauses automatically on: tab hidden, window blur, idle >30s, document loading.

**Why:** "Time spent" is meaningful only as active reading time. If a viewer has this tab open but is in another tab for 20 minutes, that time should not count. This is the same model Kindle uses for "reading time" and DocSend uses for "time spent."

**Idle threshold:** 30 seconds. Below 30s, a moment of thought is part of reading. Above 30s, the reader has almost certainly left or is idle.

---

### Display format: `Reading 2m 14s | Left ≈5m | Pg 3 / 20`

**Decision:** Show elapsed time, estimated remaining, and current page in a compact monospace row.

**Why:** These are the three most useful pieces of information for a reading-in-progress context. Reading time is motivating (I've spent time on this). Remaining is planning-relevant (will I finish this in my commute?). Page count is orientation (am I halfway?).

**Format notes:**
- `≈` prefix on remaining indicates it's an estimate
- `<1m` shown when remaining < 60s (not "0m 45s" — that creates false precision)
- Time format: `2m 14s` (not `02:14` — colon format is for video, not text)

---

## Owner Experience (InsightsModal)

### Four-tab layout: Reading / Pages / Viewers / Insights

**Decision:** Tabbed layout so each analytics dimension is browsable independently.

**Why:** A single scrolling dashboard becomes overwhelming with 6 score types, a heatmap, per-viewer rows, and NL insights. Tabs give each view breathing room.

**Tab ordering:** "Reading" first (most valuable), then "Pages" (familiar from previous version), then "Viewers", then "Insights".

---

### AI scores as gauge circles, not raw numbers in a table

**Decision:** Engagement, Absorption, Focus, Consistency, Stability, Understanding shown as circular gauge badges with color coding (green/teal/amber at 70/45/below).

**Why:** Scores are meaningful relative to 0–100, not as absolute numbers. A circle encoding immediately communicates "good/ok/needs attention" without requiring the owner to interpret a number.

**Color semantics:**
- Green (`#3DD68C`) = 70+ (strong engagement)
- Teal (`#5AC8D0`) = 45–69 (moderate, room to improve)
- Amber (`#E09A45`) = <45 (low engagement, actionable insight needed)

---

### NL insights generated only from sufficient data

**Decision:** No insights are generated until thresholds are met (≥5 sessions for slow-page detection, ≥10 sessions for drop-off patterns).

**Why:** With 1–2 sessions, any pattern is noise. Showing "page 3 takes too long" based on a single viewer is misleading and could prompt unnecessary document changes.

**User messaging:** When no insights are available: "No insights yet — more reading sessions will generate patterns." This is honest about the data requirement.

---

### Drop-off rate shown as a right-justified annotation on heatmap bars

**Decision:** Drop-off rate `↓12%` appears to the right of each heatmap bar, only when >0%.

**Why:** Drop-off is the most actionable per-page signal for document improvement. Surfacing it directly on the heatmap row — without a separate table — reduces the cognitive load of cross-referencing two visualizations.
