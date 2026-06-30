import { C, mono } from '../../constants/tokens.js';
import { SectionLabel } from '../atoms.jsx';
const { useState } = React;

export function KpiCard({ k }) {
  const [hov, setHov] = useState(false);
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      title={k.tooltip || undefined}
      style={{
        background: C.surface, border: `1px solid ${hov ? C.borderMed : C.border}`,
        borderRadius: 10, padding: '13px 15px', transition: 'border-color .15s',
        cursor: k.tooltip ? 'help' : 'default',
      }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <SectionLabel>{k.label}</SectionLabel>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {k.tooltip && (
            <span style={{ fontSize: 8, color: C.textDim, border: `1px solid ${C.border}`, borderRadius: '50%', width: 12, height: 12, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1 }} aria-label={`Info: ${k.tooltip}`}>?</span>
          )}
          <span style={{ fontSize: 11, color: C.textDim }}>{k.icon}</span>
        </div>
      </div>
      <div style={{
        ...mono, fontSize: 26, fontWeight: 700, letterSpacing: '-2px',
        color: C.textPrimary, lineHeight: 1, marginBottom: 5
      }}>{k.value}</div>
    </div>
  );
}
