/**
 * Reading Intelligence Engine — always-visible viewer status bar.
 *
 * Shows: Reading timer · Estimated remaining · Page progress
 * Toggle: "Reading Insights" expands a compact stats panel (OFF by default)
 *
 * Uses display.isActive from the hook — no DOM API calls in render.
 * All values are real measurements from useReadingAnalytics, never fabricated.
 */

const { useState } = React;

function _fmtMs(ms) {
  if (ms == null || ms < 0) return '—';
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
}

function _fmtRemaining(ms, sessionStarted) {
  if (!sessionStarted) return '—';
  if (ms == null || ms < 0) return '—';
  if (ms < 60_000) return '<1m';
  const m = Math.ceil(ms / 60_000);
  if (m > 999) return '>16h';
  return `≈${m}m`;
}

function ProgressBar({ pct, color }) {
  return (
    <div style={{
      height: 3, background: 'rgba(255,255,255,0.07)', borderRadius: 2, overflow: 'hidden', width: '100%', marginTop: 4,
    }}>
      <div style={{
        height: '100%', width: `${Math.min(100, Math.max(0, pct))}%`,
        background: color || '#5AC8D0', borderRadius: 2, transition: 'width 0.8s ease',
      }} />
    </div>
  );
}

function Stat({ label, value, sub }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 70 }}>
      <span style={{
        fontSize: 8, fontWeight: 700, letterSpacing: '0.08em',
        textTransform: 'uppercase', color: 'rgba(110,140,144,0.65)',
      }}>{label}</span>
      <span style={{
        fontSize: 13, fontWeight: 700, color: '#F0F2F1',
        fontFamily: "'DM Mono', monospace", letterSpacing: '-0.01em',
        lineHeight: 1.2,
      }}>{value}</span>
      {sub && <span style={{ fontSize: 9, color: 'rgba(110,140,144,0.55)', marginTop: 1 }}>{sub}</span>}
    </div>
  );
}

function Sep() {
  return <div style={{ width: 1, height: 16, background: 'rgba(90,200,208,0.1)', flexShrink: 0, alignSelf: 'center' }} />;
}

const PACE_SENTENCE = {
  faster: 'You are reading faster than most readers.',
  typical: 'You are reading at a typical pace for this document.',
  slower: 'You are reading slower than most readers — that\'s okay, take your time.',
};

export function ReadingStatusBar({ display, insights, page, pageCount }) {
  const [expanded, setExpanded] = useState(false);

  if (!display) return null;

  const {
    isActive,
    totalActiveMs,
    estimatedRemainingMs,
    currentPageActiveMs,
    pagesVisited,
    avgMsPerPage,
    readingSpeedWpm,
    completionPct,
  } = display;

  const sessionStarted = totalActiveMs > 0 || isActive;

  return (
    <div role="region" aria-label="Reading progress" style={{
      borderTop: '1px solid rgba(90,200,208,0.09)',
      background: 'rgba(8,11,12,0.98)',
      backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)',
      userSelect: 'none', flexShrink: 0, zIndex: 20,
    }}>
      {/* ── Status row ─────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', padding: '0 14px', height: 32, gap: 0 }}>

        {/* Active indicator + timer */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginRight: 12 }}>
          <div
            title={isActive ? 'Timer running' : 'Timer paused — move mouse or click to resume'}
            aria-hidden="true"
            style={{
              width: 5, height: 5, borderRadius: '50%', flexShrink: 0,
              background: isActive ? '#5AC8D0' : 'rgba(90,200,208,0.25)',
              boxShadow: isActive ? '0 0 6px #5AC8D0' : 'none',
              transition: 'background 0.4s, box-shadow 0.4s',
            }}
          />
          <span title="Total active reading time"
            aria-label={`Reading time: ${sessionStarted ? _fmtMs(totalActiveMs) : 'not started'}, timer ${isActive ? 'running' : 'paused'}`}
            style={{
              fontFamily: "'DM Mono', monospace", fontSize: 11, letterSpacing: '0.01em',
              color: sessionStarted ? '#F0F2F1' : 'rgba(110,140,144,0.5)',
              minWidth: 56, transition: 'color 0.3s',
            }}>
            {sessionStarted ? _fmtMs(totalActiveMs) : 'Waiting…'}
          </span>
        </div>

        <Sep />

        {/* Remaining */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, margin: '0 12px' }}>
          <span style={{ fontSize: 9, fontWeight: 600, color: 'rgba(110,140,144,0.55)', letterSpacing: '0.04em' }}>LEFT</span>
          <span title="Estimated time remaining based on your reading pace" style={{
            fontFamily: "'DM Mono', monospace", fontSize: 11, color: '#B0C4C8',
            minWidth: 38,
          }}>
            {_fmtRemaining(estimatedRemainingMs, sessionStarted)}
          </span>
        </div>

        <Sep />

        {/* Page */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, margin: '0 12px' }}>
          <span style={{ fontSize: 9, fontWeight: 600, color: 'rgba(110,140,144,0.55)', letterSpacing: '0.04em' }}>PG</span>
          <span title={`Page ${page} of ${pageCount}`} style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, color: '#B0C4C8' }}>
            {pageCount > 0 ? `${page} / ${pageCount}` : '—'}
          </span>
        </div>

        {/* Flex gap */}
        <div style={{ flex: 1 }} />

        {/* Insights toggle */}
        <button
          onClick={() => setExpanded(v => !v)}
          aria-expanded={expanded}
          aria-label={expanded ? 'Hide Reading Insights' : 'Show Reading Insights'}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, cursor: 'pointer',
            background: expanded ? 'rgba(90,200,208,0.1)' : 'transparent',
            border: `1px solid ${expanded ? 'rgba(90,200,208,0.25)' : 'rgba(90,200,208,0.1)'}`,
            borderRadius: 5, padding: '3px 9px',
            color: expanded ? '#5AC8D0' : 'rgba(110,140,144,0.65)',
            fontSize: 10, fontWeight: 600, letterSpacing: '0.02em',
            transition: 'all 0.15s', fontFamily: "'DM Sans', sans-serif",
          }}
        >
          <svg width="9" height="9" viewBox="0 0 9 9" fill="none" aria-hidden="true">
            <rect x=".5" y="5.5" width="1.5" height="3" rx=".5" fill="currentColor" opacity=".8"/>
            <rect x="3.75" y="3" width="1.5" height="5.5" rx=".5" fill="currentColor" opacity=".8"/>
            <rect x="7" y=".5" width="1.5" height="8" rx=".5" fill="currentColor" opacity=".8"/>
          </svg>
          Reading Insights
          <svg
            width="8" height="8" viewBox="0 0 8 8" fill="none" aria-hidden="true"
            style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
          >
            <path d="M1.5 2.5L4 5.5L6.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
          </svg>
        </button>
      </div>

      {/* ── Expanded panel ────────────────────────────────────────────── */}
      {expanded && (
        <div style={{
          borderTop: '1px solid rgba(90,200,208,0.07)',
          padding: '10px 16px 12px',
          display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'flex-end',
          background: 'rgba(6,8,9,0.6)',
        }}>
          <Stat label="Active" value={_fmtMs(totalActiveMs)} sub="time reading" />
          <Stat label="This page" value={_fmtMs(currentPageActiveMs)} sub="current page" />
          <Stat label="Avg / page" value={avgMsPerPage ? _fmtMs(avgMsPerPage) : '—'} sub={readingSpeedWpm ? `${readingSpeedWpm} wpm` : 'estimating…'} />
          <Stat label="Pages seen" value={pagesVisited > 0 ? pagesVisited : '—'} sub={pageCount > 0 ? `of ${pageCount}` : ''} />
          {insights?.difficulty && <Stat label="Difficulty" value={insights.difficulty} />}

          {/* Progress gauge */}
          <div style={{ flex: 1, minWidth: 100, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
              <span style={{
                fontSize: 8, fontWeight: 700, letterSpacing: '0.08em',
                textTransform: 'uppercase', color: 'rgba(110,140,144,0.65)',
              }}>Progress</span>
              <span style={{
                fontFamily: "'DM Mono', monospace", fontSize: 12, fontWeight: 700,
                color: completionPct >= 80 ? '#3DD68C' : '#5AC8D0',
              }}>
                {completionPct > 0 ? `${completionPct}%` : '—'}
              </span>
            </div>
            <ProgressBar
              pct={completionPct}
              color={completionPct >= 75 ? '#3DD68C' : completionPct >= 40 ? '#5AC8D0' : '#3A8A90'}
            />
          </div>
        </div>
      )}

      {/* Comparative insights — only rendered when the uploader has enabled
          "Reading Insights" on this link; otherwise `insights` stays null and
          nothing here renders. */}
      {expanded && (insights?.currentPageAvgMs || insights?.paceVsAverage) && (
        <div style={{
          borderTop: '1px solid rgba(90,200,208,0.07)',
          padding: '8px 16px 10px',
          display: 'flex', flexDirection: 'column', gap: 3,
          background: 'rgba(6,8,9,0.6)',
        }}>
          {insights.currentPageAvgMs && (
            <span style={{ fontSize: 10.5, color: 'rgba(176,196,200,0.85)' }}>
              Most readers spend about {_fmtMs(insights.currentPageAvgMs)} on this page.
            </span>
          )}
          {insights.paceVsAverage && (
            <span style={{ fontSize: 10.5, color: 'rgba(176,196,200,0.85)' }}>
              {PACE_SENTENCE[insights.paceVsAverage]}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
