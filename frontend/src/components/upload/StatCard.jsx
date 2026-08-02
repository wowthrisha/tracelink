import { C, mono } from '../../constants/tokens.js';
import { SectionLabel } from '../atoms.jsx';

const { useState } = React;

export function StatCard({ s }) {
  const [hov, setHov] = useState(false);
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      title={s.tooltip || undefined}
      style={{
        background: C.surface, border: `1px solid ${hov ? C.borderMed : C.border}`,
        borderRadius: 10, padding: '14px 16px', transition: 'all .15s',
        cursor: s.tooltip ? 'help' : 'default'
      }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <SectionLabel>{s.label}</SectionLabel>
        <span style={{ fontSize: 13, color: s.color, opacity: .6 }}>{s.icon}</span>
      </div>
      <div style={{
        ...mono, fontSize: 28, fontWeight: 700, letterSpacing: '-2px',
        color: C.textPrimary, lineHeight: 1, marginBottom: 5
      }}>{s.value}</div>
      <div style={{ fontSize: 11, color: C.textMuted }}>{s.sub}</div>
    </div>
  );
}
