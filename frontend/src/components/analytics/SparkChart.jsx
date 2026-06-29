import { C, mono } from '../../constants/tokens.js';

// SVG gradient id="aGrad" is document-scoped. Safe as long as only one SparkChart
// renders at a time (currently true — overview tab only). If multiple instances are
// needed in future, parameterise the id prop.
export function SparkChart({ range, sparkData }) {
  let pts;
  if (sparkData && sparkData.length > 0) {
    const max = Math.max(...sparkData.map(d => d.count), 1);
    pts = sparkData.map(d => Math.min(100, Math.max(8, (d.count / max) * 90)));
  } else {
    const seeds = { '24h': 1, '7d': 2, '30d': 3, '90d': 4 };
    const s = seeds[range] || 2;
    pts = Array.from({ length: 28 }, (_, i) =>
      Math.min(100, Math.max(8, 20 + Math.abs(Math.sin((i + s) * .7) * 55 + Math.cos(i * .3 + s) * 32)))
    );
  }
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
        <path d={area} fill="url(#aGrad)" />
        <path d={path} fill="none" stroke={C.teal2} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={(pts.length - 1) * dx} cy={H - pts[pts.length - 1] * .78} r="3.5" fill={C.teal1} />
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5 }}>
        {(sparkData && sparkData.length === 7 ? sparkData.map(d => d.date.slice(5)) : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']).map((d, di) => (
          <span key={di} style={{ ...mono, fontSize: 8, color: C.textDim }}>{typeof d === 'string' ? d : d}</span>
        ))}
      </div>
    </div>
  );
}
