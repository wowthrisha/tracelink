import { C, mono } from '../../constants/tokens.js';

export function DonutChart({ overview }) {
  const totalAttempts = (overview?.total_views_today || 0) + (overview?.blocked_attempts_today || 0);
  const hasData = totalAttempts > 0;
  const viewedPct = hasData ? Math.round((overview.total_views_today / totalAttempts) * 100) : 0;
  const blockedPct = hasData ? 100 - viewedPct : 0;
  const segs = [
    { label: 'Viewed', pct: viewedPct, color: C.teal2 },
    { label: 'Blocked', pct: blockedPct, color: C.error },
  ];
  const r = 36, cx = 50, cy = 50, sw = 13, circ = 2 * Math.PI * r;
  let cum = 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <svg viewBox="0 0 100 100" style={{ width: 86, height: 86, flexShrink: 0 }}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(90,200,208,0.08)" strokeWidth={sw} />
        {hasData && segs.map((s, i) => {
          const len = (s.pct / 100) * circ, gap = circ - len;
          const off = -cum * circ / 100 - circ * .25;
          cum += s.pct;
          return <circle key={i} cx={cx} cy={cy} r={r} fill="none"
            stroke={s.color} strokeWidth={sw} strokeDasharray={`${len} ${gap}`} strokeDashoffset={off} />;
        })}
        <text x={cx} y={cy - 4} textAnchor="middle" fontFamily="'DM Mono',monospace"
          fontSize={hasData ? 14 : 9} fontWeight="700" fill={hasData ? C.teal1 : C.textDim}>{hasData ? `${viewedPct}%` : 'No data'}</text>
        <text x={cx} y={cy + 10} textAnchor="middle" fontFamily="'DM Mono',monospace"
          fontSize="5.5" fill={C.textDim}>{hasData ? 'success rate' : 'today'}</text>
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {hasData ? segs.map(s => (
          <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: s.color }} />
            <span style={{ fontSize: 11, color: C.textSecondary, flex: 1 }}>{s.label}</span>
            <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>{s.pct}%</span>
          </div>
        )) : (
          <span style={{ fontSize: 11, color: C.textMuted, maxWidth: 140 }}>No views or blocked attempts recorded yet today.</span>
        )}
      </div>
    </div>
  );
}
