import { C, mono } from '../../constants/tokens.js';
import { SectionLabel } from '../atoms.jsx';
const { useState } = React;

export function KpiCard({ k }) {
  const [hov, setHov] = useState(false);
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        background: C.surface, border: `1px solid ${hov ? C.borderMed : C.border}`,
        borderRadius: 10, padding: '13px 15px', transition: 'border-color .15s'
      }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <SectionLabel>{k.label}</SectionLabel>
        <span style={{ fontSize: 11, color: C.textDim }}>{k.icon}</span>
      </div>
      <div style={{
        ...mono, fontSize: 26, fontWeight: 700, letterSpacing: '-2px',
        color: C.textPrimary, lineHeight: 1, marginBottom: 5
      }}>{k.value}</div>
    </div>
  );
}
