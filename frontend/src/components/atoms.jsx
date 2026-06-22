import { C, mono } from '../constants/tokens.js';

const { useState } = React;

/* ─── STYLE HELPER ─────────────────────────────────────────── */
export const label = (size = 9, extraStyle = {}) => ({
  fontSize: size, letterSpacing: '0.8px', textTransform: 'uppercase',
  color: C.teal3, fontWeight: 600, ...extraStyle
});

/* ─── SHARED ATOMS ─────────────────────────────────────────── */
export function SectionLabel({ children, style }) {
  return <div style={{ ...label(), ...style }}>{children}</div>;
}

export function StatusDot({ status, size = 6 }) {
  const map = { active: C.success, error: C.error, processing: C.teal2, inactive: C.slate2 };
  return (
    <span style={{
      display: 'inline-block', width: size, height: size, borderRadius: '50%',
      background: map[status] || C.slate1, flexShrink: 0,
      ...(status === 'processing' ? { animation: 'pulse 1.4s ease infinite' } : {})
    }} />
  );
}

export function RiskBadge({ level }) {
  const map = {
    HIGH: { c: C.error, bg: C.errorBg, b: C.errorBdr },
    MED: { c: C.warning, bg: C.warningBg, b: C.warningBdr },
    LOW: { c: C.success, bg: C.successBg, b: C.successBdr },
  };
  const s = map[level] || { c: C.textMuted, bg: 'transparent', b: C.border };
  return (
    <span style={{
      ...mono, fontSize: 9, fontWeight: 700, letterSpacing: '0.9px',
      color: s.c, textTransform: 'uppercase', background: s.bg,
      border: `1px solid ${s.b}`, borderRadius: 4, padding: '2px 7px'
    }}>
      {level}
    </span>
  );
}

export function Chip({ children, color = C.teal2, bg, border }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, color, letterSpacing: '0.3px',
      background: bg || 'rgba(90,200,208,0.08)',
      border: `1px solid ${border || 'rgba(90,200,208,0.2)'}`,
      borderRadius: 5, padding: '2px 8px'
    }}>
      {children}
    </span>
  );
}

/* ─── BUTTON ───────────────────────────────────────────────── */
export function Btn({ children, variant = 'primary', disabled, onClick, style, size = 'md' }) {
  const [hov, setHov] = useState(false);
  const pad = size === 'sm' ? '5px 11px' : size === 'lg' ? '10px 20px' : '8px 15px';
  const fz = size === 'sm' ? 11 : size === 'lg' ? 14 : 12.5;
  const base = {
    padding: pad, borderRadius: 7, fontSize: fz, fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer', border: 'none',
    fontFamily: "'DM Sans', sans-serif", letterSpacing: '0.1px',
    transition: 'all .15s ease', display: 'inline-flex', alignItems: 'center',
    gap: 6, whiteSpace: 'nowrap', ...style,
  };
  if (disabled) return (
    <button disabled style={{
      ...base, background: 'transparent',
      color: 'rgba(90,200,208,0.2)', border: '1px solid rgba(90,200,208,0.08)',
      textDecoration: 'line-through', cursor: 'not-allowed'
    }}>{children}</button>
  );
  if (variant === 'primary') return (
    <button onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        ...base, background: hov ? C.teal1 : C.teal2, color: '#080B0C', fontWeight: 700,
        boxShadow: hov ? `0 0 20px rgba(90,200,208,0.3)` : '0 0 0 rgba(0,0,0,0)'
      }}>
      {children}
    </button>
  );
  if (variant === 'secondary') return (
    <button onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        ...base, background: hov ? C.accentBgHover : C.accentBg,
        color: hov ? C.teal1 : C.textSecondary,
        border: `1px solid ${hov ? C.borderActive : C.borderMed}`
      }}>
      {children}
    </button>
  );
  if (variant === 'ghost') return (
    <button onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        ...base, background: hov ? C.accentBg : 'transparent',
        color: hov ? C.teal2 : C.textMuted, border: 'none'
      }}>
      {children}
    </button>
  );
  if (variant === 'danger') return (
    <button onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        ...base, background: hov ? '#F06855' : C.error, color: '#fff',
        boxShadow: hov ? `0 0 18px rgba(224,90,69,0.35)` : 'none'
      }}>
      {children}
    </button>
  );
  if (variant === 'outline-danger') return (
    <button onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        ...base, background: hov ? C.errorBg : 'transparent',
        color: C.error, border: `1px solid ${hov ? C.error : C.errorBdr}`
      }}>
      {children}
    </button>
  );
}

/* ─── CARD ─────────────────────────────────────────────────── */
export function Card({ children, style, onClick, noPad, hover = true }) {
  const [hov, setHov] = useState(false);
  return (
    <div onClick={onClick}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        background: C.surface,
        border: `1px solid ${(hov && onClick && hover) ? C.borderHover : C.border}`,
        borderRadius: 10, padding: noPad ? 0 : '16px 18px',
        transition: 'border-color .15s, background .15s',
        cursor: onClick ? 'pointer' : 'default',
        ...(hov && onClick && hover ? { background: C.surfaceMid } : {}),
        ...style
      }}>
      {children}
    </div>
  );
}

/* ─── MODAL ─────────────────────────────────────────────────── */
export function Modal({ open, onClose, title, children, width = 440 }) {
  if (!open) return null;
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(8,11,12,0.75)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', animation: 'fadeIn .15s ease'
    }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="fade-up" style={{
        background: C.surface, border: `1px solid ${C.borderMed}`,
        borderRadius: 12, width, maxWidth: '90vw', overflow: 'hidden',
        boxShadow: '0 24px 80px rgba(0,0,0,0.7)'
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px', borderBottom: `1px solid ${C.border}`
        }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary }}>{title}</span>
          <button onClick={onClose} style={{
            background: 'none', border: 'none',
            color: C.textMuted, cursor: 'pointer', fontSize: 18, lineHeight: 1,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 28, height: 28, borderRadius: 6,
            transition: 'background .12s', fontFamily: 'sans-serif'
          }}
            onMouseEnter={e => e.currentTarget.style.background = C.accentBg}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>✕</button>
        </div>
        <div style={{ padding: '20px' }}>{children}</div>
      </div>
    </div>
  );
}

/* ─── TOGGLE ───────────────────────────────────────────────── */
export function Toggle({ enabled, locked, onChange }) {
  return (
    <div onClick={() => !locked && onChange(!enabled)}
      style={{
        width: 32, height: 18, borderRadius: 9,
        background: enabled ? C.teal2 : C.surface3,
        border: `1px solid ${enabled ? C.teal3 : C.border}`,
        position: 'relative', cursor: locked ? 'not-allowed' : 'pointer',
        opacity: locked ? 0.4 : 1, transition: 'all .2s', flexShrink: 0
      }}>
      <div style={{
        position: 'absolute', top: 2,
        left: enabled ? 15 : 2,
        width: 12, height: 12, borderRadius: '50%',
        background: enabled ? '#080B0C' : C.textMuted,
        transition: 'left .18s cubic-bezier(.22,1,.36,1)'
      }} />
    </div>
  );
}

/* ─── FORM FIELD ───────────────────────────────────────────── */
export function Field({ label: lbl, children, hint }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <label style={{ ...label(10), color: C.textMuted }}>{lbl}</label>
      {children}
      {hint && <span style={{ fontSize: 10, color: C.textDim }}>{hint}</span>}
    </div>
  );
}

/* ─── DIVIDER ──────────────────────────────────────────────── */
export function Divider({ style }) {
  return <div style={{ height: 1, background: C.border, ...style }} />;
}

/* ══════════════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════════════ */
const NAV_SECTIONS = [
  {
    items: [
      { id: 'upload', icon: '⊕', label: 'Upload', badge: null },
      { id: 'viewer', icon: '◫', label: 'Viewer', badge: null },
    ]
  },
  {
    label: 'Security',
    items: [
      { id: 'access', icon: '◈', label: 'Access Control', badge: null },
    ]
  },
  {
    label: 'Insights',
    items: [
      { id: 'analytics', icon: '▦', label: 'Analytics', badge: null },
      { id: 'storage', icon: '◻', label: 'Storage', badge: null },
    ]
  },
  {
    label: 'Developers',
    items: [
      { id: 'apikeys', icon: '⌗', label: 'API Keys', badge: null },
      { id: 'webhooks', icon: '⇌', label: 'Webhooks', badge: null },
      { id: 'auditlog', icon: '≡', label: 'Audit Log', badge: null },
    ]
  },
  {
    label: 'Workspace',
    items: [
      { id: 'orgs', icon: '◉', label: 'Organizations', badge: null },
      { id: 'notifications', icon: '◎', label: 'Notifications', badge: null },
    ]
  },
  {
    label: 'Account',
    items: [
      { id: 'billing', icon: '◇', label: 'Billing', badge: null },
    ]
  },
];

export function Sidebar({ active, setActive, userEmail, onLogout, plan }) {
  const handleNav = (id) => {
    setActive(id);
  };
  return (
    <div style={{
      width: 210, background: C.surfaceAlt,
      borderRight: `1px solid ${C.border}`,
      display: 'flex', flexDirection: 'column', flexShrink: 0, height: '100%'
    }}>

      {/* Logo */}
      <div style={{
        height: 54, borderBottom: `1px solid ${C.border}`,
        display: 'flex', alignItems: 'center', padding: '0 16px', gap: 10, flexShrink: 0
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 7, flexShrink: 0,
          background: `linear-gradient(135deg, ${C.teal1} 0%, ${C.teal3} 100%)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <rect x="2" y="1" width="8" height="10" rx="1.5" stroke="#080B0C" strokeWidth="1.5" />
            <line x1="4" y1="4.5" x2="8" y2="4.5" stroke="#080B0C" strokeWidth="1.2" strokeLinecap="round" />
            <line x1="4" y1="6.5" x2="8" y2="6.5" stroke="#080B0C" strokeWidth="1.2" strokeLinecap="round" />
            <line x1="4" y1="8.5" x2="6.5" y2="8.5" stroke="#080B0C" strokeWidth="1.2" strokeLinecap="round" />
            <circle cx="10" cy="10.5" r="2.5" fill="#080B0C" stroke="#080B0C" strokeWidth="0.5" />
            <path d="M9 10.5l.8.8 1.6-1.6" stroke={C.teal1} strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: '-0.4px', color: C.textPrimary, lineHeight: 1.2 }}>SecureDoc</div>
          <div style={{ fontSize: 9, color: C.teal3, letterSpacing: '0.5px', fontWeight: 500 }}>Document Security</div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '8px 0', overflow: 'auto' }}>
        {NAV_SECTIONS.map((sec, si) => (
          <div key={si} style={{ marginBottom: 4 }}>
            {sec.label && (
              <div style={{ ...label(8), padding: '10px 16px 4px', color: C.textDim }}>{sec.label}</div>
            )}
            {sec.items.map(item => (
              <NavItem key={item.id} item={item} isActive={active === item.id} onClick={() => handleNav(item.id)} />
            ))}
          </div>
        ))}
      </nav>

      {/* System status */}
      <div style={{
        padding: '10px 14px', borderTop: `1px solid ${C.border}`,
        background: 'rgba(61,214,140,0.03)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <StatusDot status="active" size={5} />
          <span style={{ fontSize: 10, color: C.success, fontWeight: 600, letterSpacing: '0.3px' }}>All systems operational</span>
        </div>
        <Divider style={{ marginBottom: 8 }} />
        {/* User */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
            background: `linear-gradient(135deg, ${C.teal4}, ${C.slate3})`,
            border: `1px solid ${C.borderMed}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 10, color: C.teal1, fontWeight: 700
          }}>{userEmail ? userEmail[0].toUpperCase() : '?'}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, lineHeight: 1.3 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>
                {userEmail ? userEmail.split('@')[0] : 'User'}
              </div>
              {plan === 'pro' ? (
                <span style={{
                  fontSize: 8, fontWeight: 700, letterSpacing: '0.5px',
                  background: `linear-gradient(135deg, ${C.teal1}, ${C.teal3})`,
                  color: '#080B0C', padding: '1px 5px', borderRadius: 3,
                }}>PRO</span>
              ) : (
                <span style={{
                  fontSize: 8, fontWeight: 600, letterSpacing: '0.5px',
                  color: C.textDim, border: `1px solid ${C.border}`,
                  padding: '1px 5px', borderRadius: 3,
                }}>FREE</span>
              )}
            </div>
            <div style={{
              ...mono, fontSize: 9, color: C.textMuted, overflow: 'hidden',
              textOverflow: 'ellipsis', whiteSpace: 'nowrap'
            }}>{userEmail || ''}</div>
          </div>
          <button onClick={onLogout} title="Sign out"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: C.textDim, fontSize: 14, lineHeight: 1, padding: 4,
              borderRadius: 5, transition: 'color .12s, background .12s',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0
            }}
            onMouseEnter={e => { e.currentTarget.style.color = C.error; e.currentTarget.style.background = C.errorBg; }}
            onMouseLeave={e => { e.currentTarget.style.color = C.textDim; e.currentTarget.style.background = 'none'; }}>
            ⏻
          </button>
        </div>
      </div>
    </div>
  );
}

export function NavItem({ item, isActive, onClick }) {
  const [hov, setHov] = useState(false);
  return (
    <div onClick={onClick}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 9,
        padding: '9px 16px', cursor: 'pointer', margin: '1px 8px', borderRadius: 7,
        background: isActive ? C.accentBg : hov ? 'rgba(90,200,208,0.04)' : 'transparent',
        border: `1px solid ${isActive ? C.borderMed : 'transparent'}`,
        transition: 'all .12s'
      }}>
      <span style={{ fontSize: 12, color: isActive ? C.teal1 : C.textDim, lineHeight: 1, width: 14, textAlign: 'center' }}>{item.icon}</span>
      <span style={{
        fontSize: 12.5, fontWeight: isActive ? 600 : 400,
        color: isActive ? C.teal1 : hov ? C.textSecondary : C.textMuted, flex: 1
      }}>{item.label}</span>
      {item.badge && (
        <span style={{
          ...mono, fontSize: 9, background: C.errorBg, color: C.error,
          border: `1px solid ${C.errorBdr}`, borderRadius: 10, padding: '1px 5px'
        }}>{item.badge}</span>
      )}
    </div>
  );
}

/* ─── HEADER ───────────────────────────────────────────────── */
export function Header({ screen, breadcrumb, children }) {
  const titles = { upload: 'Upload Dashboard', viewer: 'Document Viewer', access: 'Access Control', analytics: 'Analytics', storage: 'Storage', billing: 'Billing', apikeys: 'API Keys', webhooks: 'Webhooks', auditlog: 'Audit Log', orgs: 'Organizations', notifications: 'Notifications' };
  const icons = { upload: '⊕', viewer: '◫', access: '◈', analytics: '▦' };
  return (
    <div className="header-root" style={{
      height: 54, background: C.surfaceAlt, borderBottom: `1px solid ${C.border}`,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 20px', flexShrink: 0
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, overflow: 'hidden', flexShrink: 1 }}>
        <span style={{ fontSize: 14, color: C.textDim, flexShrink: 0 }}>{icons[screen]}</span>
        <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.4px', color: C.textPrimary, flexShrink: 0, whiteSpace: 'nowrap' }}>{titles[screen]}</span>
        {breadcrumb && (
          <>
            <span style={{ color: C.textDim, fontSize: 13, flexShrink: 0 }}>›</span>
            <span style={{ fontSize: 13, color: C.textMuted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{breadcrumb}</span>
          </>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>{children}</div>
    </div>
  );
}
