/**
 * InsightsModal — owner analytics overlay.
 *
 * Tabs:
 *   Pages    — legacy page heatmap (views + avg time, same as before)
 *   Reading  — Reading Intelligence Engine heatmap (active time, AI scores)
 *   Viewers  — per-viewer engagement breakdown
 *   Insights — NL insights generated from reading patterns
 *
 * Data is fetched by the caller (ViewerScreen) and passed as props.
 * readingData = { summary, heatmap, insights, viewers } | null
 */

import { fmtDate } from '../utils/viewer.js';

const { useState } = React;

function _fmtMs(ms) {
  if (ms == null || ms <= 0) return '—';
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${String(s % 60).padStart(2, '0')}s`;
}

function _score(val) {
  if (val == null) return '—';
  return `${Math.round(val)}`;
}

function _pct(val) {
  if (val == null) return '—';
  return `${Math.round(val * 10) / 10}%`;
}

function ScorePill({ value, label }) {
  if (value == null) return null;
  const v = Math.round(value);
  const color = v >= 70 ? '#3DD68C' : v >= 45 ? '#5AC8D0' : '#E09A45';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
      <div style={{
        width: 36, height: 36, borderRadius: '50%',
        border: `2px solid ${color}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'DM Mono', monospace", fontSize: 12, fontWeight: 700, color,
      }}>{v}</div>
      <span style={{ fontSize: 8, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'rgba(110,140,144,0.7)' }}>{label}</span>
    </div>
  );
}

function TabBtn({ label, active, onClick }) {
  return (
    <button onClick={onClick} style={{
      background: active ? 'rgba(90,200,208,0.12)' : 'none',
      border: 'none', borderBottom: `2px solid ${active ? '#5AC8D0' : 'transparent'}`,
      color: active ? '#5AC8D0' : 'rgba(110,140,144,0.75)',
      fontSize: 10, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase',
      padding: '6px 10px', cursor: 'pointer', transition: 'all 0.15s',
    }}>{label}</button>
  );
}

// ── Legacy page heatmap (original InsightsModal body) ─────────────────────────

function PagesTab({ data }) {
  if (!data || data.pages.length === 0) {
    return <EmptyState>No page views recorded yet.</EmptyState>;
  }
  return (
    <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(130,142,158,0.55)', marginBottom: 4 }}>
        Most Viewed Pages · {data.total_views} total views
      </div>
      {data.pages.map((p, i) => {
        const maxViews = data.pages[0]?.views || 1;
        const barPct = Math.max(3, Math.round((p.views / maxViews) * 100));
        const heat = p.pct > 15 ? '#ff6b35' : p.pct > 8 ? '#ffd166' : '#5ac8d0';
        return (
          <div key={p.page} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ fontFamily: 'ui-monospace,monospace', fontSize: 9, color: 'rgba(130,142,158,0.7)', width: 40, flexShrink: 0, textAlign: 'right' }}>
              {i < 3 ? '🔥' : ''} p.{p.page}
            </div>
            <div style={{ flex: 1, height: 14, background: 'rgba(255,255,255,0.04)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${barPct}%`, height: '100%', background: `linear-gradient(90deg, ${heat}88, ${heat})`, borderRadius: 3 }} />
            </div>
            <div style={{ fontFamily: 'ui-monospace,monospace', fontSize: 9, color: 'rgba(148,160,176,0.8)', width: 38, flexShrink: 0, textAlign: 'right' }}>
              {p.views}v {p.avg_time_sec > 0 ? `${p.avg_time_sec}s` : ''}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Reading Intelligence heatmap ─────────────────────────────────────────────

function ReadingTab({ summary, heatmap }) {
  if (!summary && !heatmap) {
    return <EmptyState>No reading sessions recorded yet.</EmptyState>;
  }

  const s = summary;
  return (
    <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Aggregate AI scores */}
      {s && (
        <>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(130,142,158,0.55)', marginBottom: 2 }}>
            Aggregate Scores · {s.total_sessions} session{s.total_sessions !== 1 ? 's' : ''}
          </div>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-start', flexWrap: 'wrap', marginBottom: 6 }}>
            <ScorePill value={s.avg_engagement_score} label="Engage" />
            <ScorePill value={s.avg_absorption_score} label="Absorb" />
            <ScorePill value={s.avg_focus_score} label="Focus" />
            <ScorePill value={s.avg_reading_consistency} label="Consist" />
            <ScorePill value={s.avg_attention_stability} label="Attn" />
            <ScorePill value={s.avg_understanding_confidence} label="Understand" />
          </div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 4 }}>
            <KV label="Avg Active" value={_fmtMs(s.avg_active_ms)} />
            <KV label="Completion" value={_pct(s.avg_completion_pct)} />
            <KV label="Median" value={_fmtMs(s.median_completion_ms)} />
            <KV label="Unique Viewers" value={s.unique_viewers ?? '—'} />
          </div>
        </>
      )}

      {/* Per-page heatmap */}
      {heatmap && heatmap.pages && heatmap.pages.length > 0 && (
        <>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(130,142,158,0.55)', margin: '4px 0 2px' }}>
            Page Heatmap
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {heatmap.pages.map(p => {
              const maxMs = heatmap.pages[0]?.avg_active_ms || 1;
              const barPct = Math.max(3, Math.round((p.avg_active_ms / maxMs) * 100));
              const dropPct = p.drop_off_rate * 100;
              const heat = p.is_hotspot ? '#ff6b35' : p.avg_active_ms > 60_000 ? '#ffd166' : '#5ac8d0';
              return (
                <div key={p.page_number} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: 9, color: 'rgba(130,142,158,0.7)', width: 30, flexShrink: 0, textAlign: 'right' }}>
                    {p.is_hotspot ? '🔥' : ''}p.{p.page_number}
                  </span>
                  <div style={{ flex: 1, height: 13, background: 'rgba(255,255,255,0.04)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ width: `${barPct}%`, height: '100%', background: `linear-gradient(90deg,${heat}66,${heat})`, borderRadius: 2 }} />
                  </div>
                  <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: 9, color: 'rgba(148,160,176,0.8)', width: 52, flexShrink: 0, textAlign: 'right', whiteSpace: 'nowrap' }}>
                    {_fmtMs(p.avg_active_ms)}
                  </span>
                  {dropPct > 0 && (
                    <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: 8, color: 'rgba(224,90,69,0.65)', width: 32, flexShrink: 0, textAlign: 'right' }}>
                      ↓{Math.round(dropPct)}%
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

// ── Per-viewer breakdown ──────────────────────────────────────────────────────

function ViewersTab({ viewers }) {
  if (!viewers || viewers.length === 0) {
    return <EmptyState>No viewer sessions yet.</EmptyState>;
  }
  return (
    <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(130,142,158,0.55)', marginBottom: 2 }}>
        {viewers.length} Session{viewers.length !== 1 ? 's' : ''}
      </div>
      {viewers.map((v, i) => (
        <div key={v.session_id || i} style={{
          background: 'rgba(255,255,255,0.025)', borderRadius: 6, padding: '7px 9px',
          border: '1px solid rgba(90,200,208,0.07)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
            <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: 9, color: 'rgba(90,200,208,0.7)' }}>
              {v.viewer_email || 'Anonymous'}
            </span>
            <span style={{ fontFamily: 'ui-monospace,monospace', fontSize: 9, color: 'rgba(110,140,144,0.6)' }}>
              {v.started_at ? fmtDate(v.started_at) : ''}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <KV label="Active" value={_fmtMs(v.total_active_ms)} />
            <KV label="Compl" value={_pct(v.completion_pct)} />
            <KV label="Engage" value={_score(v.engagement_score)} />
            <KV label="Focus" value={_score(v.focus_score)} />
            <KV label="Pages" value={v.pages_visited ?? '—'} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── NL insights list ──────────────────────────────────────────────────────────

function InsightsTab({ insights }) {
  if (!insights || insights.length === 0) {
    return <EmptyState>No insights yet — more reading sessions will generate patterns.</EmptyState>;
  }
  const typeColor = { warning: '#E09A45', positive: '#3DD68C', info: '#5AC8D0', anomaly: '#E05A45' };
  return (
    <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 7 }}>
      {insights.map((ins, i) => (
        <div key={i} style={{
          background: 'rgba(255,255,255,0.025)', borderRadius: 6, padding: '7px 10px',
          borderLeft: `2px solid ${typeColor[ins.type] || '#5AC8D0'}`,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: '#E8EDF0', lineHeight: 1.4 }}>{ins.message}</span>
            <span style={{
              fontFamily: 'ui-monospace,monospace', fontSize: 8, color: 'rgba(110,140,144,0.55)',
              flexShrink: 0,
            }}>{ins.confidence != null ? `${Math.round(ins.confidence * 100)}%` : ''}</span>
          </div>
          {ins.context && (
            <div style={{ fontSize: 9, color: 'rgba(110,140,144,0.65)', marginTop: 3, lineHeight: 1.4 }}>
              {ins.context}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function KV({ label, value }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      <span style={{ fontSize: 8, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'rgba(110,140,144,0.6)' }}>{label}</span>
      <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, color: '#C0D0D4' }}>{value}</span>
    </div>
  );
}

function EmptyState({ children }) {
  return (
    <div style={{ padding: '28px 16px', textAlign: 'center', color: 'rgba(130,142,158,0.55)', fontSize: 12 }}>
      {children}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function InsightsModal({
  docName,
  loading,
  data,           // legacy: { pages, total_views }
  readingData,    // new: { summary, heatmap, insights, viewers } | null
  readingLoading,
  onClose,
  C, mono,
}) {
  const hasReading = !!(readingData?.summary || readingData?.heatmap);
  const [tab, setTab] = useState(hasReading ? 'reading' : 'pages');

  return (
    <div style={{
      position: 'fixed', top: 56, right: 16, zIndex: 700,
      width: 360,
      background: 'rgba(12,16,24,0.94)',
      backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
      border: '1px solid rgba(90,200,208,0.2)',
      borderRadius: 10,
      boxShadow: '0 8px 40px rgba(0,0,0,0.75), 0 0 0 1px rgba(90,200,208,0.07)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 12px', borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <rect x="1" y="7" width="2" height="4" rx="0.5" fill="#5ac8d0" opacity=".9"/>
          <rect x="5" y="4" width="2" height="7" rx="0.5" fill="#5ac8d0" opacity=".9"/>
          <rect x="9" y="1" width="2" height="10" rx="0.5" fill="#5ac8d0" opacity=".9"/>
        </svg>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'rgba(220,228,238,0.9)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          Analytics
        </span>
        <span style={{ fontSize: 10, color: 'rgba(130,142,158,0.7)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 120 }} title={docName}>{docName}</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(148,160,176,0.7)', fontSize: 14, padding: '0 2px', lineHeight: 1, marginLeft: 4 }}>✕</button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '0 4px' }}>
        {hasReading && <TabBtn label="Reading" active={tab === 'reading'} onClick={() => setTab('reading')} />}
        <TabBtn label="Pages" active={tab === 'pages'} onClick={() => setTab('pages')} />
        {hasReading && <TabBtn label="Viewers" active={tab === 'viewers'} onClick={() => setTab('viewers')} />}
        {hasReading && <TabBtn label="Insights" active={tab === 'insights'} onClick={() => setTab('insights')} />}
      </div>

      {/* Body */}
      {(loading || readingLoading) && tab !== 'pages' ? (
        <div style={{ padding: '28px 16px', textAlign: 'center', color: 'rgba(130,142,158,0.7)', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <span style={{ display: 'inline-block', width: 14, height: 14, border: '1.5px solid rgba(90,200,208,0.3)', borderTop: '1.5px solid #5ac8d0', borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
          Loading…
        </div>
      ) : loading && tab === 'pages' ? (
        <div style={{ padding: '28px 16px', textAlign: 'center', color: 'rgba(130,142,158,0.7)', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <span style={{ display: 'inline-block', width: 14, height: 14, border: '1.5px solid rgba(90,200,208,0.3)', borderTop: '1.5px solid #5ac8d0', borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
          Loading insights…
        </div>
      ) : (
        <div style={{ maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
          {tab === 'pages' && <PagesTab data={data} />}
          {tab === 'reading' && <ReadingTab summary={readingData?.summary} heatmap={readingData?.heatmap} />}
          {tab === 'viewers' && <ViewersTab viewers={readingData?.viewers} />}
          {tab === 'insights' && <InsightsTab insights={readingData?.insights} />}
        </div>
      )}
    </div>
  );
}
