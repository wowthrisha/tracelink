export function InsightsModal({ docName, loading, data, onClose, C, mono }) {
  return (
    <div style={{
      position: 'fixed', top: 56, right: 16, zIndex: 700,
      width: 340,
      background: 'rgba(12,16,24,0.92)',
      backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
      border: '1px solid rgba(90,200,208,0.2)',
      borderRadius: 10,
      boxShadow: '0 8px 40px rgba(0,0,0,0.75), 0 0 0 1px rgba(90,200,208,0.07)',
      overflow: 'hidden',
    }}>
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
          Page Insights
        </span>
        <span style={{ fontSize: 10, color: 'rgba(130,142,158,0.7)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 120 }} title={docName}>{docName}</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(148,160,176,0.7)', fontSize: 14, padding: '0 2px', lineHeight: 1, marginLeft: 4 }}>✕</button>
      </div>
      {loading && (
        <div style={{ padding: '28px 16px', textAlign: 'center', color: 'rgba(130,142,158,0.7)', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <span style={{ display: 'inline-block', width: 14, height: 14, border: '1.5px solid rgba(90,200,208,0.3)', borderTop: '1.5px solid #5ac8d0', borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
          Loading insights…
        </div>
      )}
      {!loading && (!data || data.pages.length === 0) && (
        <div style={{ padding: '28px 16px', textAlign: 'center', color: 'rgba(130,142,158,0.55)', fontSize: 12 }}>
          No page views recorded yet.
        </div>
      )}
      {!loading && data && data.pages.length > 0 && (
        <div style={{ padding: '10px 12px', maxHeight: 'calc(100vh - 140px)', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
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
                  <div style={{
                    width: `${barPct}%`, height: '100%',
                    background: `linear-gradient(90deg, ${heat}88, ${heat})`,
                    borderRadius: 3,
                  }} />
                </div>
                <div style={{ fontFamily: 'ui-monospace,monospace', fontSize: 9, color: 'rgba(148,160,176,0.8)', width: 38, flexShrink: 0, textAlign: 'right' }}>
                  {p.views}v {p.avg_time_sec > 0 ? `${p.avg_time_sec}s` : ''}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
