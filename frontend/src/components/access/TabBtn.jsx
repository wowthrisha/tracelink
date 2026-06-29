import { C } from '../../constants/tokens.js';
const { useState } = React;

export function TabBtn({ tab, active, onClick }) {
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        padding: '9px 16px', background: 'none', border: 'none',
        borderBottom: active ? `2px solid ${C.teal1}` : '2px solid transparent',
        color: active ? C.textPrimary : hov ? C.textSecondary : C.textMuted,
        fontSize: 13, fontWeight: active ? 600 : 400, cursor: 'pointer',
        fontFamily: "'DM Sans',sans-serif", transition: 'all .12s', marginBottom: -1
      }}>
      {tab.label}
    </button>
  );
}
