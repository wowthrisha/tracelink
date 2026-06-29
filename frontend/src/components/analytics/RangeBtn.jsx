import { C, mono } from '../../constants/tokens.js';
const { useState } = React;

export function RangeBtn({ r, active, onClick }) {
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        ...mono, fontSize: 10, padding: '5px 11px', borderRadius: 6,
        border: `1px solid ${active ? C.teal2 : hov ? C.borderMed : C.border}`,
        background: active ? C.accentBg : hov ? 'rgba(90,200,208,0.05)' : 'transparent',
        color: active ? C.teal1 : C.textMuted, cursor: 'pointer',
        fontFamily: "'DM Mono',monospace", transition: 'all .12s'
      }}>
      {r}
    </button>
  );
}
