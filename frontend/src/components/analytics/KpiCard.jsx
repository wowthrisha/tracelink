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
            // BUG-008: this used to be a plain <span> — it had an aria-label and
            // sat inside a div with a native `title`, which looks accessible, but
            // neither element was focusable, so keyboard/screen-reader users could
            // never Tab to it and the aria-label was never announced in normal
            // navigation (only reachable via a screen reader's verbose "browse all
            // elements" mode). A real <button> is natively focusable, triggers the
            // `title` tooltip on focus in modern browsers (not just hover), and
            // gets its aria-label announced like any other interactive control.
            <button
              type="button"
              title={k.tooltip}
              aria-label={`Info: ${k.tooltip}`}
              style={{
                fontSize: 8, color: C.textDim, background: 'none',
                border: `1px solid ${C.border}`, borderRadius: '50%',
                width: 12, height: 12, padding: 0, display: 'inline-flex',
                alignItems: 'center', justifyContent: 'center', lineHeight: 1,
                cursor: 'help', fontFamily: 'inherit',
              }}
            >?</button>
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
