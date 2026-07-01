/**
 * Reading Intelligence Engine — always-visible viewer status bar.
 *
 * Mounts below the main viewer canvas. Displays:
 *   Reading <time> · Remaining ≈ <time> · Page <n> / <total>
 *
 * Toggle: "Show Reading Insights" expands a compact panel with per-session stats.
 * Default: collapsed (OFF).
 *
 * Does NOT fetch from the backend — reads from the hook's display state.
 * All displayed values come from real accumulated data, never fabricated.
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

function _fmtRemaining(ms) {
  if (ms == null || ms < 0) return '—';
  if (ms < 60_000) return '<1m';
  const m = Math.ceil(ms / 60_000);
  return `≈${m}m`;
}

// Tiny gauge bar, 0–100%
function GaugeBar({ pct, color }) {
  return (
    <div style={{
      height: 3, background: 'rgba(255,255,255,0.07)', borderRadius: 2, overflow: 'hidden',
      marginTop: 4, width: '100%',
    }}>
      <div style={{
        height: '100%', width: `${Math.min(100, Math.max(0, pct))}%`,
        background: color || '#5AC8D0', borderRadius: 2,
        transition: 'width 0.6s ease',
      }} />
    </div>
  );
}

// Compact stat cell
function StatCell({ label, value, sub }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'rgba(110,140,144,0.75)' }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 700, color: '#F0F2F1', fontFamily: "'DM Mono', monospace", letterSpacing: '-0.01em' }}>{value}</span>
      {sub && <span style={{ fontSize: 9, color: 'rgba(110,140,144,0.6)' }}>{sub}</span>}
    </div>
  );
}

export function ReadingStatusBar({ display, page, pageCount, isActive }) {
  const [expanded, setExpanded] = useState(false);

  if (!display) return null;

  const {
    totalActiveMs,
    estimatedRemainingMs,
    completedPages,
    avgMsPerPage,
    readingSpeedWpm,
    completionPct,
  } = display;

  const readingStr = _fmtMs(totalActiveMs);
  const remainingStr = _fmtRemaining(estimatedRemainingMs);
  const pageStr = pageCount > 0 ? `${page} / ${pageCount}` : '—';
  const avgStr = avgMsPerPage ? _fmtMs(avgMsPerPage) : '—';
  const speedStr = readingSpeedWpm ? `${readingSpeedWpm} wpm` : '—';

  return (
    <div style={{
      borderTop: '1px solid rgba(90,200,208,0.1)',
      background: 'rgba(8,11,12,0.97)',
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      userSelect: 'none',
      flexShrink: 0,
    }}>
      {/* ── Main status row ─────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 0,
        padding: '0 14px', height: 32,
      }}>
        {/* Reading timer */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginRight: 14 }}>
          {/* Active indicator dot */}
          <div style={{
            width: 5, height: 5, borderRadius: '50%', flexShrink: 0,
            background: isActive ? '#5AC8D0' : 'rgba(90,200,208,0.3)',
            boxShadow: isActive ? '0 0 5px #5AC8D0' : 'none',
            transition: 'background 0.4s, box-shadow 0.4s',
          }} />
          <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, color: isActive ? '#F0F2F1' : 'rgba(110,140,144,0.7)', letterSpacing: '0.01em', minWidth: 54 }}>
            {readingStr}
          </span>
        </div>

        <Divider />

        {/* Remaining */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, margin: '0 14px' }}>
          <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: 'rgba(110,140,144,0.65)', letterSpacing: '0.03em' }}>Left</span>
          <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, color: '#B0C4C8', letterSpacing: '0.01em', minWidth: 36 }}>
            {remainingStr}
          </span>
        </div>

        <Divider />

        {/* Page */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, margin: '0 14px' }}>
          <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: 'rgba(110,140,144,0.65)', letterSpacing: '0.03em' }}>Pg</span>
          <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, color: '#B0C4C8', letterSpacing: '0.01em' }}>
            {pageStr}
          </span>
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Insights toggle */}
        <button
          onClick={() => setExpanded(v => !v)}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            background: expanded ? 'rgba(90,200,208,0.1)' : 'none',
            border: `1px solid ${expanded ? 'rgba(90,200,208,0.25)' : 'rgba(90,200,208,0.12)'}`,
            borderRadius: 5, padding: '2px 8px', cursor: 'pointer',
            color: expanded ? '#5AC8D0' : 'rgba(110,140,144,0.75)',
            fontSize: 10, fontWeight: 600, letterSpacing: '0.02em',
            transition: 'all 0.15s',
          }}
        >
          <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
            <rect x=".5" y="5.5" width="1.5" height="3" rx=".5" fill="currentColor" opacity=".8"/>
            <rect x="3.75" y="3" width="1.5" height="5.5" rx=".5" fill="currentColor" opacity=".8"/>
            <rect x="7" y=".5" width="1.5" height="8" rx=".5" fill="currentColor" opacity=".8"/>
          </svg>
          Reading Insights
          <svg width="8" height="8" viewBox="0 0 8 8" fill="none" style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
            <path d="M1.5 2.5L4 5.5L6.5 2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
          </svg>
        </button>
      </div>

      {/* ── Expanded insights panel ──────────────────────────────────────── */}
      {expanded && (
        <div style={{
          borderTop: '1px solid rgba(90,200,208,0.08)',
          padding: '10px 16px 12px',
          display: 'flex', gap: 20, flexWrap: 'wrap',
          background: 'rgba(8,11,12,0.98)',
        }}>
          <StatCell
            label="Time Active"
            value={readingStr}
            sub="total active reading"
          />
          <StatCell
            label="Remaining"
            value={remainingStr}
            sub="estimated"
          />
          <StatCell
            label="Avg / Page"
            value={avgStr}
            sub={readingSpeedWpm ? `${readingSpeedWpm} wpm` : null}
          />
          <StatCell
            label="Pages Read"
            value={completedPages > 0 ? completedPages : '—'}
            sub={pageCount > 0 ? `of ${pageCount}` : null}
          />
          <div style={{ flex: 1, minWidth: 120, display: 'flex', flexDirection: 'column', gap: 3, justifyContent: 'flex-end' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'rgba(110,140,144,0.75)' }}>Progress</span>
              <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, fontWeight: 700, color: completionPct >= 75 ? '#3DD68C' : '#5AC8D0' }}>{completionPct}%</span>
            </div>
            <GaugeBar
              pct={completionPct}
              color={completionPct >= 75 ? '#3DD68C' : completionPct >= 40 ? '#5AC8D0' : '#3A8A90'}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function Divider() {
  return (
    <div style={{ width: 1, height: 16, background: 'rgba(90,200,208,0.1)', flexShrink: 0 }} />
  );
}
