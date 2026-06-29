import { C } from '../constants/tokens.js';

export function GateMessage({ icon, title, msg }) {
  return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: C.bg }}>
      <div style={{
        background: C.surface, border: `1px solid ${C.borderMed}`, borderRadius: 14,
        padding: '36px 32px', width: 340, display: 'flex', flexDirection: 'column', gap: 12,
        alignItems: 'center', boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
      }}>
        <div style={{ fontSize: 32 }}>{icon}</div>
        <div style={{ fontSize: 15, fontWeight: 600, color: C.textPrimary }}>{title}</div>
        <div style={{ fontSize: 12, color: C.textMuted, textAlign: 'center', lineHeight: 1.6 }}>{msg}</div>
      </div>
    </div>
  );
}
