import { C, mono } from '../../constants/tokens.js';

// SVG gradient id="aGrad" is document-scoped. Safe as long as only one SparkChart
// renders at a time (currently true — overview tab only). If multiple instances are
// needed in future, parameterise the id prop.
export function SparkChart({ sparkData }) {
  const hasData = sparkData && sparkData.length > 0;
  // No fabricated data: with nothing real to show, render a flat baseline
  // instead of a plausible-looking wave, so "no activity yet" reads as
  // "no activity yet" rather than as a real trend.
  const pts = hasData
    ? sparkData.map(d => Math.min(100, Math.max(8, (d.count / Math.max(...sparkData.map(x => x.count), 1)) * 90)))
    : Array.from({ length: 7 }, () => 8);
  const W = 480, H = 90;
  const dx = W / (pts.length - 1);
  const path = pts.map((v, i) => `${i === 0 ? 'M' : 'L'} ${i * dx},${H - v * .78}`).join(' ');
  const area = path + ` L ${(pts.length - 1) * dx},${H} L 0,${H} Z`;
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 90, overflow: 'visible' }}>
        <defs>
          <linearGradient id="aGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={C.teal1} stopOpacity="0.18" />
            <stop offset="100%" stopColor={C.teal1} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#aGrad)" opacity={hasData ? 1 : 0.35} />
        <path d={path} fill="none" stroke={C.teal2} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" opacity={hasData ? 1 : 0.35} />
        {hasData && <circle cx={(pts.length - 1) * dx} cy={H - pts[pts.length - 1] * .78} r="3.5" fill={C.teal1} />}
      </svg>
      {!hasData && (
        <div style={{ textAlign: 'center', fontSize: 10, color: C.textDim, marginTop: -6, marginBottom: 6 }}>No activity recorded yet</div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5 }}>
        {(sparkData && sparkData.length === 7 ? sparkData.map(d => d.date.slice(5)) : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']).map((d, di) => (
          <span key={di} style={{ ...mono, fontSize: 8, color: C.textDim }}>{typeof d === 'string' ? d : d}</span>
        ))}
      </div>
    </div>
  );
}
