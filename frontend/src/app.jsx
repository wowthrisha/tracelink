    const { useState, useEffect, useRef, useCallback, useContext, createContext } = React;

    /* ─── DESIGN TOKENS ───────────────────────────────────────── */
    const C = {
      bg: '#080B0C',
      surface: '#0E1416',
      surfaceAlt: '#0B0F10',
      surfaceMid: '#131C1E',
      surface2: '#192224',
      surface3: '#1E2A2C',
      border: 'rgba(90,200,208,0.1)',
      borderMed: 'rgba(90,200,208,0.18)',
      borderHover: 'rgba(90,200,208,0.28)',
      borderActive: 'rgba(90,200,208,0.45)',
      // teal scale
      teal0: '#C8F4F8',
      teal1: '#8BE2EA',
      teal2: '#5AC8D0',
      teal3: '#3A8A90',
      teal4: '#255A60',
      // slate scale
      slate1: '#6B8A8E',
      slate2: '#4A6266',
      slate3: '#2C3E40',
      accentBg: 'rgba(90,200,208,0.07)',
      accentBgHover: 'rgba(90,200,208,0.12)',
      // text
      textPrimary: '#F0F2F1',
      textSecondary: '#B0C4C8',
      textMuted: '#6E8C90',
      textDim: '#3A5558',
      // semantic
      success: '#3DD68C',
      successBg: 'rgba(61,214,140,0.08)',
      successBdr: 'rgba(61,214,140,0.22)',
      error: '#E05A45',
      errorBg: 'rgba(224,90,69,0.08)',
      errorBdr: 'rgba(224,90,69,0.22)',
      warning: '#E09A45',
      warningBg: 'rgba(224,154,69,0.08)',
      warningBdr: 'rgba(224,154,69,0.22)',
      info: '#5AC8D0',
      infoBg: 'rgba(90,200,208,0.08)',
      infoBdr: 'rgba(90,200,208,0.22)',
    };

    const mono = { fontFamily: "'DM Mono', monospace" };

    /* ─── TOAST CONTEXT ───────────────────────────────────────── */
    const ToastCtx = createContext(null);
    function useToast() { return useContext(ToastCtx); }

    function ToastProvider({ children }) {
      const [toasts, setToasts] = useState([]);
      const add = useCallback((msg, type = 'info', duration = 3200) => {
        const id = Date.now() + Math.random();
        setToasts(t => [...t, { id, msg, type, dying: false }]);
        setTimeout(() => setToasts(t => t.map(x => x.id === id ? { ...x, dying: true } : x)), duration - 400);
        setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), duration);
      }, []);
      return (
        <ToastCtx.Provider value={add}>
          {children}
          <div style={{
            position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
            display: 'flex', flexDirection: 'column', gap: 8, pointerEvents: 'none'
          }}>
            {toasts.map(t => <Toast key={t.id} t={t} />)}
          </div>
        </ToastCtx.Provider>
      );
    }

    function Toast({ t }) {
      const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
      const colors = { success: C.success, error: C.error, warning: C.warning, info: C.teal2 };
      const bgs = { success: C.successBg, error: C.errorBg, warning: C.warningBg, info: C.infoBg };
      const bdrs = { success: C.successBdr, error: C.errorBdr, warning: C.warningBdr, info: C.infoBdr };
      return (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          background: C.surface2, border: `1px solid ${bdrs[t.type]}`,
          borderLeft: `3px solid ${colors[t.type]}`,
          borderRadius: 8, padding: '10px 14px', minWidth: 260, maxWidth: 360,
          pointerEvents: 'all', boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          animation: t.dying ? 'toastOut .35s ease forwards' : 'toastIn .3s cubic-bezier(.22,1,.36,1) both',
        }}>
          <span style={{ color: colors[t.type], fontWeight: 700, fontSize: 13 }}>{icons[t.type]}</span>
          <span style={{ fontSize: 13, color: C.textSecondary, lineHeight: 1.4 }}>{t.msg}</span>
        </div>
      );
    }

    /* ─── SHARED ATOMS ─────────────────────────────────────────── */
    const label = (size = 9, extraStyle = {}) => ({
      fontSize: size, letterSpacing: '0.8px', textTransform: 'uppercase',
      color: C.teal3, fontWeight: 600, ...extraStyle
    });

    function SectionLabel({ children, style }) {
      return <div style={{ ...label(), ...style }}>{children}</div>;
    }

    function StatusDot({ status, size = 6 }) {
      const map = { active: C.success, error: C.error, processing: C.teal2, inactive: C.slate2 };
      return (
        <span style={{
          display: 'inline-block', width: size, height: size, borderRadius: '50%',
          background: map[status] || C.slate1, flexShrink: 0,
          ...(status === 'processing' ? { animation: 'pulse 1.4s ease infinite' } : {})
        }} />
      );
    }

    function RiskBadge({ level }) {
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

    function Chip({ children, color = C.teal2, bg, border }) {
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
    function Btn({ children, variant = 'primary', disabled, onClick, style, size = 'md' }) {
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
    function Card({ children, style, onClick, noPad, hover = true }) {
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
    function Modal({ open, onClose, title, children, width = 440 }) {
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
    function Toggle({ enabled, locked, onChange }) {
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
    function Field({ label: lbl, children, hint }) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          <label style={{ ...label(10), color: C.textMuted }}>{lbl}</label>
          {children}
          {hint && <span style={{ fontSize: 10, color: C.textDim }}>{hint}</span>}
        </div>
      );
    }

    /* ─── DIVIDER ──────────────────────────────────────────────── */
    function Divider({ style }) {
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
        ]
      },
      {
        label: 'Account',
        items: [
          { id: 'billing', icon: '◇', label: 'Billing', badge: null },
        ]
      },
    ];

    function Sidebar({ active, setActive, userEmail, onLogout, plan }) {
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

    function NavItem({ item, isActive, onClick }) {
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
    function Header({ screen, breadcrumb, children }) {
      const titles = { upload: 'Upload Dashboard', viewer: 'Document Viewer', access: 'Access Control', analytics: 'Analytics' };
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

    /* ══════════════════════════════════════════════════════════════
       SCREEN 1 — UPLOAD DASHBOARD
    ══════════════════════════════════════════════════════════════ */
    /* Mocks removed — all data from real API */

    function UploadScreen({ onViewDoc, onAccessDoc }) {
      const toast = useToast();
      const [dragging, setDragging] = useState(false);
      const [uploading, setUploading] = useState(false);
      const [progress, setProgress] = useState(0);
      const [uploadDone, setUploadDone] = useState(false);
      const [uploadedDoc, setUploadedDoc] = useState(null);
      const [search, setSearch] = useState('');
      const [deleteModal, setDeleteModal] = useState(null);
      const [docs, setDocs] = useState([]);
      const [overview, setOverview] = useState(null);
      const [docsLoading, setDocsLoading] = useState(true);
      const [deleting, setDeleting] = useState(false);
      const [groups, setGroups] = useState([]);
      const [activeGroupFilter, setActiveGroupFilter] = useState(null);
      const [selectedGroupId, setSelectedGroupId] = useState('');
      const [groupModal, setGroupModal] = useState(null); // null | 'new' | {id,name,color,description}
      const [groupForm, setGroupForm] = useState({ name: '', color: '#6366f1', description: '' });
      const [groupSaving, setGroupSaving] = useState(false);
      const fileRef = useRef();
      const pollRef = useRef(null);

      const fetchDocs = useCallback(async () => {
        try {
          const data = await window.SecureDocAPI.getDocuments();
          setDocs(data.documents || []);
          const ov = await window.SecureDocAPI.getAnalyticsOverview();
          setOverview(ov);
        } catch (e) { toast(e.detail || 'Failed to load documents', 'error'); }
        finally { setDocsLoading(false); }
      }, []);

      const fetchGroups = useCallback(async () => {
        try {
          const data = await window.SecureDocAPI.getGroups();
          setGroups(data.groups || []);
        } catch (e) { /* non-critical */ }
      }, []);

      useEffect(() => { fetchDocs(); fetchGroups(); }, []);

      const MAX_POLL_ATTEMPTS = 150; // 150 × 2s = 5 minutes before giving up
      const startPoll = useCallback((docId, fileType = 'pdf') => {
        clearInterval(pollRef.current);
        let attempts = 0;
        pollRef.current = setInterval(async () => {
          attempts += 1;
          if (attempts > MAX_POLL_ATTEMPTS) {
            clearInterval(pollRef.current);
            setUploading(false);
            toast('Processing is taking longer than expected. Check back later.', 'error');
            return;
          }
          try {
            const s = await window.SecureDocAPI.pollDocumentStatus(docId);
            if (s.status === 'ready' || s.status === 'error') {
              clearInterval(pollRef.current);
              setUploading(false);
              await fetchDocs();
              if (s.status === 'ready') {
                setUploadDone(true);
                const unit = (fileType === 'pdf' || fileType === 'docx' || fileType === 'doc') ? 'pages' : 'chunks';
                toast(`Upload complete — ${s.page_count} ${unit} ready`, 'success');
              } else toast(`Processing error: ${s.error_message || 'unknown'}`, 'error');
            }
          } catch { }
        }, 2000);
      }, [fetchDocs]);

      useEffect(() => () => clearInterval(pollRef.current), []);

      const _detectFileType = (file) => {
        const name = file.name.toLowerCase();
        if (name.endsWith('.pdf')) return 'pdf';
        if (name.endsWith('.docx')) return 'docx';
        if (name.endsWith('.doc')) return 'doc';
        if (name.endsWith('.txt')) return 'txt';
        if (name.endsWith('.md')) return 'md';
        if (name.endsWith('.log')) return 'log';
        return null;
      };

      const _isDocType = (ft) => ft === 'pdf' || ft === 'docx' || ft === 'doc';

      const simulate = async (file) => {
        if (!file) return;
        const fileType = _detectFileType(file);
        if (!fileType) {
          toast('Supported formats: PDF, DOCX, DOC, TXT, MD, LOG', 'error'); return;
        }
        const sizeLimit = _isDocType(fileType) ? 100 * 1024 * 1024 : 10 * 1024 * 1024;
        const sizeLabelMB = _isDocType(fileType) ? 100 : 10;
        if (file.size > sizeLimit) {
          toast(`File exceeds ${sizeLabelMB} MB limit.`, 'error'); return;
        }
        setUploading(true); setProgress(0); setUploadDone(false);
        try {
          const res = await window.SecureDocAPI.uploadDocument(file, p => setProgress(p), selectedGroupId || null);
          setUploadedDoc(res);
          toast(_isDocType(fileType) ? 'Upload complete — converting pages to images' : 'Upload complete — preparing text document', 'info');
          startPoll(res.id, fileType);
          await fetchDocs();
        } catch (e) {
          setUploading(false);
          const msg = (e && (e.detail || e.message)) || 'Upload failed';
          toast(msg, 'error');
        }
      };

      const handleSaveGroup = async () => {
        if (!groupForm.name.trim()) { toast('Group name is required', 'error'); return; }
        setGroupSaving(true);
        try {
          if (groupModal === 'new') {
            await window.SecureDocAPI.createGroup(groupForm);
            toast(`Group "${groupForm.name}" created`, 'success');
          } else {
            await window.SecureDocAPI.updateGroup(groupModal.id, groupForm);
            toast(`Group "${groupForm.name}" updated`, 'success');
          }
          await fetchGroups();
          setGroupModal(null);
        } catch (e) {
          toast(e.detail || 'Failed to save group', 'error');
        } finally { setGroupSaving(false); }
      };

      const handleDeleteGroup = async (g) => {
        try {
          await window.SecureDocAPI.deleteGroup(g.id);
          toast(`Group "${g.name}" deleted`, 'success');
          if (activeGroupFilter === g.id) setActiveGroupFilter(null);
          await fetchGroups(); await fetchDocs();
        } catch (e) { toast(e.detail || 'Failed to delete group', 'error'); }
      };

      const handleAssignGroup = async (doc, gid) => {
        try {
          if (gid) {
            await window.SecureDocAPI.assignDocumentsToGroup(gid, [doc.id]);
          } else if (doc.group_id) {
            await window.SecureDocAPI.removeDocumentFromGroup(doc.group_id, doc.id);
          }
          await fetchDocs(); await fetchGroups();
          toast(gid ? 'Document added to group' : 'Removed from group', 'success');
        } catch (e) { toast(e.detail || 'Failed to assign group', 'error'); }
      };

      const handleDelete = async (doc) => {
        setDeleting(true);
        try {
          await window.SecureDocAPI.deleteDocument(doc.id);
          setDeleteModal(null);
          await fetchDocs();
          toast('Document deleted.', 'success');
        } catch (e) { toast(e.detail || 'Delete failed', 'error'); }
        finally { setDeleting(false); }
      };

      const handleReprocess = async (doc) => {
        try {
          await window.SecureDocAPI.reprocessDocument(doc.id);
          toast('Reprocessing started…', 'info');
          await fetchDocs();
          startPoll(doc.id, doc.file_type || 'pdf');
        } catch (e) { toast(e.detail || 'Failed to reprocess', 'error'); }
      };

      const filtered = docs.filter(d =>
        (d.filename || d.name || '').toLowerCase().includes(search.toLowerCase()) &&
        (!activeGroupFilter || d.group_id === activeGroupFilter)
      );

      const weekViews = (overview?.views_last_7_days || []).reduce((a, d) => a + d.count, 0);
      const highRiskCount = docs.filter(d => d.risk === 'HIGH').length;

      const stats = [
        { label: 'Total Documents', value: (overview?.total_documents || 0).toString(), sub: `${docs.filter(d => d.status === 'ready').length} ready`, icon: '◫', color: C.teal2 },
        { label: 'Active Shares', value: (overview?.active_links || 0).toString(), sub: `${overview?.expiring_soon_count || 0} expiring within 14d`, icon: '◈', color: C.teal2 },
        { label: 'Total Views', value: (overview?.total_views_today || 0).toLocaleString(), sub: `+${weekViews} this week`, icon: '▦', color: C.success },
        { label: 'Blocked Attempts', value: (overview?.blocked_attempts_today || 0).toString(), sub: `${highRiskCount} high-risk docs`, icon: '⊗', color: C.warning },
      ];

      return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
          <Header screen="upload">
            <Btn variant="secondary" size="sm" onClick={() => toast('Search feature coming soon', 'info')}>⌕ Filter</Btn>
            <Btn variant="primary" size="sm" onClick={() => fileRef.current.click()}>↑ Upload PDF</Btn>
          </Header>

          <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10 }}>
              {stats.map(s => <StatCard key={s.label} s={s} />)}
            </div>

            {/* Upload zone / progress */}
            {!uploading && !uploadDone && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div onDragOver={e => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); simulate(e.dataTransfer.files[0]).catch(() => {}); }}
                  onClick={() => fileRef.current.click()}
                  style={{
                    border: `1.5px dashed ${dragging ? C.teal1 : C.borderMed}`,
                    borderRadius: 10, padding: '24px', textAlign: 'center',
                    background: dragging ? C.accentBg : 'transparent',
                    cursor: 'pointer', transition: 'all .15s'
                  }}>
                  <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt,.md,.log" style={{ display: 'none' }} onChange={e => simulate(e.target.files[0]).catch(() => {})} />
                  <div style={{
                    width: 36, height: 36, borderRadius: 8, background: C.accentBg,
                    border: `1px solid ${C.borderMed}`, display: 'flex', alignItems: 'center',
                    justifyContent: 'center', margin: '0 auto 10px', fontSize: 16, color: C.teal2
                  }}>⊕</div>
                  <div style={{ fontSize: 13, color: C.textSecondary, fontWeight: 600, marginBottom: 4 }}>
                    Drop file here or <span style={{ color: C.teal2 }}>click to browse</span>
                  </div>
                  <div style={{ ...mono, fontSize: 10, color: C.textMuted }}>PDF · DOCX · DOC · TXT · MD · LOG · Doc max 100 MB · Text max 10 MB</div>
                </div>
                {/* Group selector for upload */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <SectionLabel>Assign to group</SectionLabel>
                  <select value={selectedGroupId} onChange={e => setSelectedGroupId(e.target.value)}
                    style={{
                      fontSize: 11, background: C.surface2, border: `1px solid ${C.border}`,
                      borderRadius: 6, padding: '4px 8px', color: C.textSecondary,
                      flex: 1, maxWidth: 220
                    }}>
                    <option value="">— None —</option>
                    {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                  </select>
                  <Btn variant="ghost" size="sm" onClick={() => { setGroupForm({ name: '', color: '#6366f1', description: '' }); setGroupModal('new'); }}>+ New group</Btn>
                </div>
              </div>
            )}

            {(uploading || uploadDone) && (
              <Card style={{ padding: '14px 18px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <StatusDot status={uploading ? 'processing' : 'active'} />
                    <span style={{ fontSize: 13, fontWeight: 600 }}>
                      {uploading ? 'Uploading & processing…' : '✓ Processing complete'}
                    </span>
                  </div>
                  <span style={{ ...mono, fontSize: 11, color: C.textMuted }}>{Math.round(progress)}%</span>
                </div>
                <div style={{ height: 4, background: C.surface3, borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', width: `${progress}%`,
                    background: `linear-gradient(90deg, ${C.teal3}, ${C.teal1})`,
                    borderRadius: 3, transition: 'width .2s ease'
                  }} />
                </div>
                {uploadDone && (
                  <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                    <Btn variant="primary" size="sm" onClick={() => { setUploadDone(false); if (uploadedDoc) onAccessDoc(uploadedDoc); }}>
                      Configure Access →
                    </Btn>
                    <Btn variant="ghost" size="sm" onClick={() => setUploadDone(false)}>Dismiss</Btn>
                  </div>
                )}
              </Card>
            )}

            {/* Groups filter strip */}
            {groups.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                <SectionLabel>Groups</SectionLabel>
                <button onClick={() => setActiveGroupFilter(null)}
                  style={{
                    fontSize: 10, padding: '3px 10px', borderRadius: 20,
                    border: `1px solid ${!activeGroupFilter ? C.teal2 : C.border}`,
                    background: !activeGroupFilter ? C.accentBg : 'transparent',
                    color: !activeGroupFilter ? C.teal1 : C.textMuted, cursor: 'pointer'
                  }}>All</button>
                {groups.map(g => (
                  <div key={g.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <button onClick={() => setActiveGroupFilter(activeGroupFilter === g.id ? null : g.id)}
                      style={{
                        fontSize: 10, padding: '3px 10px', borderRadius: 20, cursor: 'pointer',
                        border: `1px solid ${activeGroupFilter === g.id ? g.color : C.border}`,
                        background: activeGroupFilter === g.id ? `${g.color}22` : 'transparent',
                        color: activeGroupFilter === g.id ? g.color : C.textMuted, display: 'flex', alignItems: 'center', gap: 5
                      }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: g.color, display: 'inline-block' }} />
                      {g.name} <span style={{ opacity: 0.6 }}>({g.document_count})</span>
                    </button>
                    <button onClick={() => { setGroupForm({ name: g.name, color: g.color, description: g.description || '' }); setGroupModal(g); }}
                      style={{ fontSize: 9, padding: '2px 5px', borderRadius: 4, border: `1px solid ${C.border}`, background: 'transparent', color: C.textDim, cursor: 'pointer' }}>✎</button>
                    <button onClick={() => handleDeleteGroup(g)}
                      style={{ fontSize: 9, padding: '2px 5px', borderRadius: 4, border: `1px solid ${C.border}`, background: 'transparent', color: C.textDim, cursor: 'pointer' }}>✕</button>
                  </div>
                ))}
                <Btn variant="ghost" size="sm" onClick={() => { setGroupForm({ name: '', color: '#6366f1', description: '' }); setGroupModal('new'); }}>+ Group</Btn>
              </div>
            )}

            {/* Documents table */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <SectionLabel>Documents</SectionLabel>
                  <Chip color={C.textMuted} bg="transparent" border={C.border}>{filtered.length}</Chip>
                  {activeGroupFilter && (() => { const g = groups.find(x => x.id === activeGroupFilter); return g ? <Chip color={g.color} bg={`${g.color}22`} border="transparent">{g.name}</Chip> : null; })()}
                </div>
                <input style={{ width: 200, fontSize: 12 }} placeholder="Search documents…"
                  value={search} onChange={e => setSearch(e.target.value)} />
              </div>

              <Card noPad>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                      {['Document', 'Status', 'Risk', 'Pages', 'Views', 'Expires', ''].map(h => (
                        <th key={h} style={{ ...label(9), padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: C.textDim }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {docsLoading ? (
                      <tr><td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: C.textMuted, fontSize: 13 }}>
                        Loading documents…
                      </td></tr>
                    ) : filtered.length === 0 ? (
                      <tr><td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: C.textMuted, fontSize: 13 }}>
                        {docs.length === 0 ? 'No documents yet — upload your first PDF above' : 'No documents match your search'}
                      </td></tr>
                    ) : filtered.map((d, i) => (
                      <DocRow key={d.id} doc={d} isLast={i === filtered.length - 1}
                        onView={() => onViewDoc(d)} onAccess={() => onAccessDoc(d)}
                        onDelete={() => setDeleteModal(d)}
                        onReprocess={() => handleReprocess(d)}
                        groups={groups} onAssignGroup={handleAssignGroup} />
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>

            {/* Footer hint */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0' }}>
              <StatusDot status="active" size={5} />
              <span style={{ fontSize: 10, color: C.textMuted }}>All documents converted to images — download disabled by default</span>
            </div>
          </div>

          <Modal open={!!deleteModal} onClose={() => setDeleteModal(null)} title="Delete Document" width={400}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{
                background: C.errorBg, border: `1px solid ${C.errorBdr}`,
                borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
              }}>
                <strong style={{ color: C.error }}>⚠ This cannot be undone.</strong><br />
                All share links for <strong style={{ color: C.textPrimary }}>"{deleteModal?.filename || deleteModal?.name}"</strong> will be permanently revoked.
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <Btn variant="secondary" onClick={() => setDeleteModal(null)}>Cancel</Btn>
                <Btn variant="danger" onClick={() => handleDelete(deleteModal)}>Delete Document</Btn>
              </div>
            </div>
          </Modal>

          {/* Group create / edit modal */}
          <Modal open={!!groupModal} onClose={() => setGroupModal(null)}
            title={groupModal === 'new' ? 'New Group' : `Edit Group: ${groupForm.name}`} width={380}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <Field label="Name">
                <input value={groupForm.name} onChange={e => setGroupForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Q4 Reports" autoFocus />
              </Field>
              <Field label="Color">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <input type="color" value={groupForm.color}
                    onChange={e => setGroupForm(f => ({ ...f, color: e.target.value }))}
                    style={{ width: 40, height: 32, padding: 2, borderRadius: 6, border: `1px solid ${C.border}`, cursor: 'pointer', background: 'transparent' }} />
                  <span style={{ ...mono, fontSize: 11, color: C.textMuted }}>{groupForm.color}</span>
                  {['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316'].map(c => (
                    <button key={c} onClick={() => setGroupForm(f => ({ ...f, color: c }))}
                      style={{ width: 18, height: 18, borderRadius: '50%', background: c, border: groupForm.color === c ? `2px solid ${C.textPrimary}` : 'none', cursor: 'pointer', padding: 0 }} />
                  ))}
                </div>
              </Field>
              <Field label="Description (optional)">
                <input value={groupForm.description}
                  onChange={e => setGroupForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Brief description" />
              </Field>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <Btn variant="secondary" onClick={() => setGroupModal(null)}>Cancel</Btn>
                <Btn variant="primary" loading={groupSaving} onClick={handleSaveGroup}>
                  {groupModal === 'new' ? 'Create Group' : 'Save Changes'}
                </Btn>
              </div>
            </div>
          </Modal>
        </div>
      );
    }

    function StatCard({ s }) {
      const [hov, setHov] = useState(false);
      return (
        <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
          style={{
            background: C.surface, border: `1px solid ${hov ? C.borderMed : C.border}`,
            borderRadius: 10, padding: '14px 16px', transition: 'all .15s'
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

    function DocRow({ doc, isLast, onView, onAccess, onDelete, onReprocess, groups, onAssignGroup }) {
      const [hov, setHov] = useState(false);
      const isProcessing = doc.status === 'processing';
      const isError = doc.status === 'error';
      const isUploaded = doc.status === 'uploaded';
      const canRetry = isProcessing || isError || isUploaded;
      return (
        <tr onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
          onClick={onAccess}
          style={{
            borderBottom: isLast ? 'none' : `1px solid ${C.border}`,
            background: hov ? 'rgba(90,200,208,0.03)' : 'transparent', transition: 'background .1s',
            cursor: 'pointer'
          }}>
          <td style={{ padding: '12px 14px', maxWidth: 220 }}>
            <div style={{
              fontSize: 12.5, fontWeight: 600, color: C.textPrimary, marginBottom: 2,
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
            }}>{doc.filename || doc.name}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <div style={{ ...mono, fontSize: 9, color: C.textMuted }}>{(doc.id || '').slice(0, 8)}… · {doc.file_size_bytes ? `${(doc.file_size_bytes / 1024 / 1024).toFixed(1)} MB` : '—'}</div>
              {doc.group_name && (
                <span style={{
                  fontSize: 9, padding: '1px 6px', borderRadius: 10,
                  background: `${doc.group_color || '#6366f1'}22`,
                  color: doc.group_color || '#6366f1',
                  border: `1px solid ${doc.group_color || '#6366f1'}44`
                }}>{doc.group_name}</span>
              )}
            </div>
          </td>
          <td style={{ padding: '12px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <StatusDot status={doc.status} />
              <span style={{
                fontSize: 11.5, color: isError ? C.error : isProcessing ? C.teal2 : C.textSecondary,
                textTransform: 'capitalize', fontWeight: isError ? 600 : 400
              }}>
                {doc.status}
              </span>
            </div>
          </td>
          <td style={{ padding: '12px 14px' }}><RiskBadge level={doc.risk} /></td>
          <td style={{ ...mono, padding: '12px 14px', fontSize: 11, color: C.textSecondary }}>{doc.page_count ?? 0}</td>
          <td style={{ ...mono, padding: '12px 14px', fontSize: 11, color: C.textSecondary }}>{(doc.total_views || doc.views || 0).toLocaleString()}</td>
          <td style={{
            ...mono, padding: '12px 14px', fontSize: 10,
            color: doc.expires ? (new Date(doc.expires) < new Date('2026-05-16') ? C.warning : C.textSecondary) : C.textMuted
          }}>
            {doc.expires || '—'}
          </td>
          <td style={{ padding: '12px 14px' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', gap: 4, opacity: hov ? 1 : 0, transition: 'opacity .15s', alignItems: 'center' }}>
              {canRetry && <Btn variant="ghost" size="sm" onClick={onReprocess} style={{ color: C.warning }}>↺ Retry</Btn>}
              <Btn variant="ghost" size="sm" onClick={onView}>View</Btn>
              <Btn variant="ghost" size="sm" onClick={onAccess}>Access</Btn>
              {groups && groups.length > 0 && (
                <select defaultValue="" onChange={e => { onAssignGroup(doc, e.target.value || null); e.target.value = ''; }}
                  onClick={e => e.stopPropagation()}
                  style={{
                    fontSize: 10, background: C.surface2, border: `1px solid ${C.border}`,
                    borderRadius: 5, padding: '3px 6px', color: C.textMuted, cursor: 'pointer',
                    maxWidth: 110
                  }}>
                  <option value="" disabled>Group…</option>
                  <option value="">— Remove —</option>
                  {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
                </select>
              )}
              <Btn variant="ghost" size="sm" onClick={onDelete} style={{ color: C.error }}>✕</Btn>
            </div>
          </td>
        </tr>
      );
    }

    /* ══════════════════════════════════════════════════════════════
       SCREEN 2 — DOCUMENT VIEWER
    ══════════════════════════════════════════════════════════════ */

    /* ─── DOCUMENT PICKER ──────────────────────────────────────────
       Shared empty-state component shown in Viewer and Access Control
       when no document is selected yet. Fetches the docs list and lets
       the user click to select one without leaving the current tab.
    ─────────────────────────────────────────────────────────────── */
    function DocumentPicker({ onSelect }) {
      const toast = useToast();
      const [docs, setDocs] = useState([]);
      const [loading, setLoading] = useState(true);

      useEffect(() => {
        window.SecureDocAPI.getDocuments()
          .then(data => setDocs((data.documents || []).filter(d => d.status === 'ready')))
          .catch(() => toast('Failed to load documents', 'error'))
          .finally(() => setLoading(false));
      }, []);

      if (loading) {
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: C.textMuted, padding: 32 }}>
            <span style={{ display: 'inline-block', width: 16, height: 16, border: `1.5px solid ${C.border}`, borderTop: `1.5px solid ${C.teal2}`, borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
            Loading documents…
          </div>
        );
      }

      if (docs.length === 0) {
        return (
          <div data-testid="document-picker-empty" style={{ textAlign: 'center', padding: '40px 20px', color: C.textMuted }}>
            <div style={{ fontSize: 32, marginBottom: 12, color: C.textDim }}>◫</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary, marginBottom: 6 }}>No ready documents</div>
            <div style={{ fontSize: 12, color: C.textMuted, lineHeight: 1.7 }}>
              Upload and process a PDF in the <strong style={{ color: C.textSecondary }}>Upload</strong> tab, then return here.
            </div>
          </div>
        );
      }

      return (
        <div data-testid="document-picker" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ marginBottom: 4 }}>
            <SectionLabel>Select a document to open</SectionLabel>
            <div style={{ fontSize: 11, color: C.textMuted, marginTop: 4 }}>{docs.length} ready document{docs.length !== 1 ? 's' : ''}</div>
          </div>
          {docs.map(d => (
            <div key={d.id} onClick={() => onSelect(d)}
              data-testid="doc-picker-item"
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '13px 16px', background: C.surface,
                border: `1px solid ${C.border}`, borderRadius: 9, cursor: 'pointer',
                transition: 'all .12s'
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = C.borderHover; e.currentTarget.style.background = C.surfaceMid; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.background = C.surface; }}>
              <div style={{
                width: 36, height: 36, background: C.accentBg, border: `1px solid ${C.borderMed}`,
                borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, color: C.teal2, flexShrink: 0
              }}>◫</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {d.filename || d.name}
                </div>
                <div style={{ fontSize: 10, color: C.textMuted, marginTop: 2 }}>
                  {d.page_count ?? 0} pages · {(d.total_views || 0).toLocaleString()} views
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <StatusDot status={d.status} />
                <span style={{ fontSize: 10, color: C.success, fontWeight: 600 }}>Ready</span>
              </div>
            </div>
          ))}
        </div>
      );
    }

    class ViewerErrorBoundary extends React.Component {
      constructor(props) { super(props); this.state = { error: null }; }
      static getDerivedStateFromError(error) { return { error }; }
      componentDidCatch(error, info) { console.error('ViewerErrorBoundary caught:', error, info); }
      render() {
        if (this.state.error) {
          return (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 14, color: C.textMuted, padding: 32 }}>
              <div style={{ fontSize: 32 }}>⚠</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: C.textPrimary }}>Viewer encountered an error</div>
              <div style={{ ...mono, fontSize: 11, color: C.textDim, maxWidth: 400, textAlign: 'center' }}>{String(this.state.error)}</div>
              <button onClick={() => this.setState({ error: null })}
                style={{ marginTop: 8, padding: '7px 18px', borderRadius: 7, border: `1px solid ${C.borderMed}`, background: C.surface, color: C.textSecondary, cursor: 'pointer', fontSize: 12 }}>
                Retry
              </button>
            </div>
          );
        }
        return this.props.children;
      }
    }

    function GateMessage({ icon, title, msg }) {
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

    function AccessGate({ gateInfo, onSubmit, error }) {
      const requiresPw = gateInfo?.requires_password;
      const requiresEmail = gateInfo?.requires_email;
      const status = gateInfo?.status;
      const [pw, setPw] = useState('');
      const [email, setEmail] = useState('');
      const [shaking, setShaking] = useState(false);
      useEffect(() => {
        if (error) { setShaking(true); setTimeout(() => setShaking(false), 500); }
      }, [error]);

      const gateInputStyle = {
        background: 'rgba(90,200,208,0.04)', border: `1px solid ${C.borderMed}`,
        borderRadius: 8, color: C.textPrimary, fontFamily: "'DM Sans', sans-serif",
        fontSize: 13, padding: '10px 13px', outline: 'none', width: '100%',
        boxSizing: 'border-box',
      };

      if (status === 'not_found') return <GateMessage icon="&#x1F50D;" title="Link Not Found" msg="This share link does not exist or has been removed." />;
      if (status === 'revoked') return <GateMessage icon="&#x1F6AB;" title="Link Revoked" msg="This share link has been revoked by the document owner." />;
      if (status === 'expired') return <GateMessage icon="&#x23F1;" title="Link Expired" msg="This share link has expired and is no longer accessible." />;

      const canSubmit = (!requiresEmail || email.trim()) && (!requiresPw || pw);
      const handleSubmit = () => { if (canSubmit) onSubmit(email.trim() || null, pw || null); };

      return (
        <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: C.bg }}>
          <div style={{
            background: C.surface, border: `1px solid ${C.borderMed}`, borderRadius: 14,
            padding: '36px 32px', width: 360, display: 'flex', flexDirection: 'column', gap: 16,
            boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
            animation: shaking ? 'shake .4s' : undefined,
          }}>
            <div style={{ textAlign: 'center', fontSize: 28 }}>
              {requiresPw && requiresEmail ? '\uD83D\uDD10' : requiresPw ? '\uD83D\uDD12' : '\uD83D\uDCE7'}
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: C.textPrimary, textAlign: 'center' }}>
              {requiresPw && requiresEmail ? 'Email & Password Required' : requiresPw ? 'Password Required' : 'Email Verification Required'}
            </div>
            <div style={{ fontSize: 12, color: C.textMuted, textAlign: 'center', lineHeight: 1.6 }}>
              {requiresPw && requiresEmail
                ? 'Enter your institutional email and the document password.'
                : requiresPw
                  ? 'This document is password protected.'
                  : 'Enter your email address to verify you have access to this document.'}
            </div>
            {requiresEmail && (
              <input type="email" placeholder="you@institution.edu" value={email}
                onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !requiresPw && handleSubmit()}
                autoFocus={true}
                style={gateInputStyle} />
            )}
            {requiresPw && (
              <input type="password" placeholder="Enter password" value={pw}
                onChange={e => setPw(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                autoFocus={!requiresEmail}
                style={gateInputStyle} />
            )}
            {error && <div style={{ fontSize: 11, color: C.error, textAlign: 'center' }}>{error}</div>}
            <Btn onClick={handleSubmit} disabled={!canSubmit} size="lg">Open Document</Btn>
          </div>
        </div>
      );
    }

    // ── Viewer Layout System constants ─────────────────────────────────────────
    const LAYOUT = { FIT_WIDTH: 'fit-width', FIT_HEIGHT: 'fit-height', CUSTOM: 'custom' };
    const ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200, 300, 400];
    const ZOOM_MIN = 10;
    const ZOOM_MAX = 400;
    const ZOOM_STEP = 10;

    // Persist layout preferences across sessions
    function _saveLayoutPref(mode, zoom) {
      try { localStorage.setItem('sdoc-layout-mode', mode); } catch {}
      try { localStorage.setItem('sdoc-layout-zoom', String(zoom)); } catch {}
    }
    function _loadLayoutPref() {
      let mode = LAYOUT.FIT_WIDTH, zoom = 100;
      try { const m = localStorage.getItem('sdoc-layout-mode'); if (m) mode = m; } catch {}
      try { const z = parseInt(localStorage.getItem('sdoc-layout-zoom') || '100', 10); if (z >= ZOOM_MIN && z <= ZOOM_MAX) zoom = z; } catch {}
      return { mode, zoom };
    }

    function ViewerScreen({ doc, publicToken, onSelectDoc }) {
      const toast = useToast();
      const [page, setPage] = useState(1);
      // Layout system: fit-width, fit-height, or custom zoom
      const _initPref = _loadLayoutPref();
      const [layoutMode, setLayoutMode] = useState(_initPref.mode);
      const [customZoom, setCustomZoom] = useState(_initPref.zoom);
      // Legacy zoom alias (kept for sessionStorage restore compat)
      const zoom = layoutMode === LAYOUT.CUSTOM ? customZoom : 100;
      const [showInfo, setShowInfo] = useState(false);
      const [session, setSession] = useState(null);
      const [imgSrc, setImgSrc] = useState('');
      const [imgLoading, setImgLoading] = useState(false);
      const [pageError, setPageError] = useState(null);
      const [blurred, setBlurred] = useState(false);
      const [initializing, setInit] = useState(true);
      const [gateInfo, setGateInfo] = useState(null);
      const [gateError, setGateError] = useState(null);
      const [pendingToken, setPendingToken] = useState(null);
      const [textContent, setTextContent] = useState('');
      const [textLoading, setTextLoading] = useState(false);
      const [textError, setTextError] = useState(null);
      // Phase 7: smooth transitions — keep prev image visible while next loads
      const [prevImgSrc, setPrevImgSrc] = useState('');
      const [imgReady, setImgReady] = useState(false);
      // Phase 7: in-viewer search
      const [showSearch, setShowSearch] = useState(false);
      // Phase 7: TOC sidebar for text/md documents
      const [showToc, setShowToc] = useState(false);
      // Premium: laser pointer, magnifier, fullscreen, page jump
      const [showLaser, setShowLaser] = useState(false);
      const [showMagnifier, setShowMagnifier] = useState(false);
      const [showInsights, setShowInsights] = useState(false);
      const [insightsData, setInsightsData] = useState(null);
      const [insightsLoading, setInsightsLoading] = useState(false);
      const [isFullscreen, setIsFullscreen] = useState(false);
      const [pageInputStr, setPageInputStr] = useState('');
      const [showPageList, setShowPageList] = useState(false);
      const pageImgRef = useRef(null);
      const pageContainerRef = useRef(null); // Feature 4: magnifier needs page container
      // Feature 1: hyperlink overlay
      const pageLinksRef = useRef({});   // {pageNum: [{x,y,w,h,url}]}
      const [linksLoaded, setLinksLoaded] = useState(false);
      // Feature 2: search highlighting
      const wordPositionsRef = useRef({}); // {pageNum: [{t,x,y,w,h}]}
      const wordPositionsFetched = useRef(false); // avoid re-fetching after empty result
      const [searchHighlightQuery, setSearchHighlightQuery] = useState('');
      const [searchHighlights, setSearchHighlights] = useState([]);
      const [searchResultPages, setSearchResultPages] = useState(new Set()); // pages with any match (for fallback glow)
      const [activeHighlightIdx, setActiveHighlightIdx] = useState(0); // which match is orange
      // Phase 7: mobile/touch support — extended for pinch-to-zoom
      const touchRef = useRef({ x: null, y: null, pinchDist: null });

      // ── Phase 7: request deduplication — one inflight fetch per page key ─────
      const inflightRef = useRef(new Map());
      // Ref tracks the currently displayed imgSrc so loadPage (empty-deps callback)
      // can capture it for the crossfade background without a stale closure.
      const imgSrcRef = useRef('');

      // ── Page image cache ─────────────────────────────────────────────────────
      // Blob URLs are stored per "token:page" key so navigating back to a page
      // already viewed is instant and requires no extra network round-trip.
      // Cache-Control: no-store on the backend means the browser won't cache
      // these, so we must do it ourselves.
      //
      // We cap the cache at MAX_CACHED_PAGES and revoke evicted blob URLs to
      // prevent unbounded memory growth during long sessions.
      const MAX_CACHED_PAGES = 30;
      const pageCache = useRef(new Map());

      const _cacheSet = useCallback((key, blobUrl) => {
        pageCache.current.set(key, blobUrl);
        if (pageCache.current.size > MAX_CACHED_PAGES) {
          // Evict the oldest entry (insertion order) and free its memory
          const firstKey = pageCache.current.keys().next().value;
          const evicted = pageCache.current.get(firstKey);
          URL.revokeObjectURL(evicted);
          pageCache.current.delete(firstKey);
        }
      }, []);

      // Revoke all blob URLs when the viewer unmounts or the session ends
      const _clearPageCache = useCallback(() => {
        for (const url of pageCache.current.values()) {
          URL.revokeObjectURL(url);
        }
        pageCache.current.clear();
      }, []);

      const loadPage = useCallback(async (token, pageNum, sessionId) => {
        if (!token || !sessionId) {
          console.error('[SecureDoc] loadPage: token or sessionId missing',
            { token: token ? '[set]' : '[missing]', pageNum, sessionId: sessionId ? '[set]' : '[missing]' });
          setImgLoading(false);
          return;
        }
        const key = `${token}:${pageNum}`;

        // Cache hit — instant display (no network round-trip; crossfade from current page)
        if (pageCache.current.has(key)) {
          const cached = pageCache.current.get(key);
          setPrevImgSrc(imgSrcRef.current);
          setImgSrc(cached);
          setImgReady(true);
          setImgLoading(false);
          return;
        }

        // Phase 7: request deduplication — if this page is already being fetched,
        // wait for the existing promise instead of firing a second request.
        if (inflightRef.current.has(key)) {
          try { await inflightRef.current.get(key); } catch {}
          if (pageCache.current.has(key)) {
            const cached = pageCache.current.get(key);
            setImgSrc(cached);
            setImgReady(true);
          }
          setImgLoading(false);
          return;
        }

        // Phase 7: smooth transition — save current page as background, keep it visible
        // while the new page fetches. imgReady controls crossfade opacity.
        setPrevImgSrc(imgSrcRef.current);
        setImgReady(false);
        setImgLoading(true);
        setPageError(null);

        const url = window.SecureDocAPI.getPageUrl(token, pageNum);
        const fetchPromise = (async () => {
          try {
            const r = await fetch(url, { headers: window.SecureDocAPI.sessionHeaders(sessionId) });
            if (!r.ok) {
              let detail = null;
              try { detail = (await r.json()).detail; } catch {}
              console.error('[SecureDoc] page fetch HTTP error', r.status, url, detail);
              setPageError(detail || `Unable to load page (${r.status})`);
              setImgReady(true);
              return;
            }
            const blobUrl = URL.createObjectURL(await r.blob());
            _cacheSet(key, blobUrl);
            setImgSrc(blobUrl);
            setPageError(null);
            // imgReady set by onLoad handler to trigger crossfade after browser decodes image
          } catch {
            console.warn('[SecureDoc] page fetch network error, falling back to img src', url);
            setImgSrc(url);
            setImgReady(true);
          } finally {
            setImgLoading(false);
            inflightRef.current.delete(key);
          }
        })();

        inflightRef.current.set(key, fetchPromise);
        await fetchPromise;
      }, []);

      const prefetchPage = useCallback((token, pageNum, sessionId, total) => {
        if (pageNum < 1 || pageNum > total) return;
        const key = `${token}:${pageNum}`;
        if (pageCache.current.has(key)) return;
        fetch(window.SecureDocAPI.getPageUrl(token, pageNum), { headers: window.SecureDocAPI.sessionHeaders(sessionId) })
          .then(r => r.ok ? r.blob() : Promise.reject())
          .then(blob => { _cacheSet(key, URL.createObjectURL(blob)); })
          .catch(() => {});
      }, []);

      const loadTextChunk = useCallback(async (token, chunkNum, sessionId) => {
        if (!token || !sessionId) return;
        setTextLoading(true);
        setTextError(null);
        try {
          const data = await window.SecureDocAPI.getTextChunk(token, chunkNum, sessionId);
          setTextContent(data.content);
        } catch (e) {
          setTextError(e?.detail || 'Unable to load content');
        } finally {
          setTextLoading(false);
        }
      }, []);

      const docName = doc?.filename || doc?.name || session?.document_filename || 'Document';
      const docId = doc?.id || '';
      const PAGE_COUNT = session?.page_count || 1;
      const isTextDoc = !!(session?.doc_type && ['txt', 'md', 'log'].includes(session.doc_type));

      const doValidate = async (token, email, password) => {
        setInit(true);
        setGateError(null);
        try {
          // Reuse existing session if available (prevents accumulating slots on refresh)
          const storedSessionId = sessionStorage.getItem(`securedoc_sess_${token}`);
          const res = await window.SecureDocAPI.validateLink(token, password, email, storedSessionId);
          res.created_at = new Date().toISOString();
          // Persist session so page refreshes reuse the same slot
          sessionStorage.setItem(`securedoc_sess_${token}`, res.session_id);
          setSession({ ...res, link_token: token });
          setGateInfo(null);
          setPage(1);
        } catch (e) {
          const status = e._status;
          if (status === 401) {
            // Password wrong or missing — keep gate visible, show error
            setGateError(e.detail === 'Wrong password' ? 'Wrong password. Try again.' : null);
          } else if (status === 403 || status === 429) {
            // 403: domain/IP/email/concurrent denied — keep gate visible
            setGateError(e.detail || 'Access denied');
          } else if (status === 410 || status === 404) {
            // Revoked/expired/gone — clear stored session, show terminal gate
            sessionStorage.removeItem(`securedoc_sess_${token}`);
            const detail = (e.detail || '').toLowerCase();
            const terminalStatus = status === 404 ? 'not_found'
              : detail.includes('revoked') ? 'revoked' : 'expired';
            setGateInfo({ status: terminalStatus, requires_password: false, requires_email: false });
          } else {
            toast(e.detail || 'Failed to open viewer', 'error');
          }
        } finally { setInit(false); }
      };

      // Auto-create link + probe gate requirements, then validate if no restrictions
      useEffect(() => {
        if (!docId && !publicToken) { setInit(false); return; }
        (async () => {
          try {
            let token = publicToken;
            if (!token) {
              try {
                const data = await window.SecureDocAPI.getLinks(docId);
                const active = (data.links || []).filter(l => !l.revoked_at && (!l.expires_at || new Date(l.expires_at) > new Date()));
                if (active.length > 0) { token = active[0].token; }
              } catch { }
              if (!token) {
                const nl = await window.SecureDocAPI.createLink({ document_id: docId, label: 'Admin Preview' });
                token = nl.token;
              }
            }
            setPendingToken(token);
            const gate = await window.SecureDocAPI.getGateRequirements(token);
            if (gate.status !== 'active' || gate.requires_password || gate.requires_email) {
              setGateInfo(gate);
              setInit(false);
              return;
            }
            // No gate restrictions — auto-validate immediately
            await doValidate(token, null, null);
          } catch (e) {
            toast(e.detail || 'Failed to open viewer', 'error');
            setInit(false);
          }
        })();
      }, [docId]);

      // Security protections — must stay here so hook count is always the same
      useEffect(() => {
        if (!session) return;
        const perms = session.permissions || {};

        const blockRC = e => { if (!perms.can_right_click) { e.preventDefault(); window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'right_click_attempt'); toast('Right-click disabled in secure viewer.', 'warning'); } };
        const blockKB = e => {
          const k = e.key?.toLowerCase(), ctrl = e.ctrlKey || e.metaKey;
          if (ctrl) {
            if (k === 'p' && !perms.can_print) { e.preventDefault(); e.stopPropagation(); window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'print_attempt'); toast('Action disabled in secure viewer.', 'warning'); }
            if (['a', 'c', 'x', 'u'].includes(k) && !perms.can_copy) { e.preventDefault(); e.stopPropagation(); window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'copy_attempt'); toast('Action disabled in secure viewer.', 'warning'); }
            if (k === 's' && !perms.can_download) { e.preventDefault(); e.stopPropagation(); window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'download_attempt'); toast('Action disabled in secure viewer.', 'warning'); }
          }
        };
        const onBP = () => { if (!perms.can_print) { document.querySelectorAll('.viewer-page').forEach(el => el.style.visibility = 'hidden'); window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'print_attempt'); } };
        const onAP = () => document.querySelectorAll('.viewer-page').forEach(el => el.style.visibility = 'visible');
        const onBlur = () => setBlurred(true), onFocus = () => setBlurred(false);
        document.addEventListener('contextmenu', blockRC); document.addEventListener('keydown', blockKB);
        window.addEventListener('beforeprint', onBP); window.addEventListener('afterprint', onAP);
        window.addEventListener('blur', onBlur); window.addEventListener('focus', onFocus);
        return () => { document.removeEventListener('contextmenu', blockRC); document.removeEventListener('keydown', blockKB); window.removeEventListener('beforeprint', onBP); window.removeEventListener('afterprint', onAP); window.removeEventListener('blur', onBlur); window.removeEventListener('focus', onFocus); };
      }, [session]);

      // Revoke all blob URLs when the viewer unmounts to prevent memory leaks
      useEffect(() => () => _clearPageCache(), []);

      // Load page — checks in-memory blob cache first; fetches on miss.
      // Depends on individual session fields so the effect only re-fires when
      // the token, session_id, or page number actually changes (not on every
      // object re-allocation after a validate call that reused the same slot).
      //
      // Note: page_viewed is logged server-side on every /api/viewer/page request;
      // the frontend only logs client-side events (print_attempt, copy_attempt, etc.)
      useEffect(() => {
        if (!session) return;
        if (isTextDoc) return; // text/md/log handled by text effect below
        // Skip network call entirely when document isn't ready yet — show status inline
        if (session.doc_status && session.doc_status !== 'ready') {
          const msgs = {
            uploaded: 'Document is queued for processing — please wait and refresh.',
            processing: 'Document is still processing — please wait a moment and refresh.',
            error: 'Document processing failed. Please contact the document owner.',
          };
          setPageError(msgs[session.doc_status] || `Document not available (${session.doc_status})`);
          return;
        }
        setPageError(null);
        loadPage(session.link_token, page, session.session_id);
        // Log completion when the viewer reaches the last page (client-side event)
        if (page === session.page_count) {
          window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'completed');
        }
      }, [session?.link_token, session?.session_id, page, session?.doc_status, session?.doc_type, loadPage]);

      // Prefetch the next and previous pages in the background as soon as the
      // current page has finished loading, so navigation feels instantaneous.
      useEffect(() => {
        if (!session || imgLoading || isTextDoc) return;
        prefetchPage(session.link_token, page + 1, session.session_id, PAGE_COUNT);
        if (page > 1) prefetchPage(session.link_token, page - 1, session.session_id, PAGE_COUNT);
      }, [session?.link_token, session?.session_id, page, imgLoading, PAGE_COUNT, prefetchPage, isTextDoc]);

      // Eagerly prefetch page 2 in parallel with page 1 the moment a session
      // is established, so forward navigation feels instant on page 1.
      useEffect(() => {
        if (!session || isTextDoc) return;
        const pc = session.page_count || 1;
        if (pc >= 2) prefetchPage(session.link_token, 2, session.session_id, pc);
      }, [session?.link_token, session?.session_id, session?.doc_type]); // intentionally omit prefetchPage — stable ref

      // Load text chunk — only runs for text documents (txt/md/log)
      useEffect(() => {
        if (!session || !isTextDoc) return;
        if (session.doc_status && session.doc_status !== 'ready') {
          const msgs = {
            uploaded: 'Document is queued for processing — please wait and refresh.',
            processing: 'Document is still processing — please wait a moment and refresh.',
            error: 'Document processing failed. Please contact the document owner.',
          };
          setTextError(msgs[session.doc_status] || `Document not available (${session.doc_status})`);
          return;
        }
        setTextError(null);
        loadTextChunk(session.link_token, page, session.session_id);
        if (page === session.page_count) {
          window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'completed');
        }
      }, [session?.link_token, session?.session_id, page, session?.doc_status, session?.doc_type, loadTextChunk]);

      const goNext = useCallback(() => setPage(p => Math.min(p + 1, PAGE_COUNT)), [PAGE_COUNT]);
      const goPrev = useCallback(() => setPage(p => Math.max(p - 1, 1)), []);

      // Layout helpers (stable identity — no setState in dep array needed)
      const _setLayout = useCallback((mode, zoom) => {
        setLayoutMode(mode);
        if (zoom !== undefined) setCustomZoom(zoom);
        _saveLayoutPref(mode, zoom !== undefined ? zoom : customZoom);
      }, [customZoom]);

      const _zoomBy = useCallback((delta) => {
        setCustomZoom(z => {
          const next = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z + delta));
          setLayoutMode(LAYOUT.CUSTOM);
          _saveLayoutPref(LAYOUT.CUSTOM, next);
          return next;
        });
      }, []);

      const _zoomTo = useCallback((pct) => {
        setCustomZoom(pct);
        setLayoutMode(LAYOUT.CUSTOM);
        _saveLayoutPref(LAYOUT.CUSTOM, pct);
      }, []);

      const toggleFullscreen = useCallback(() => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen?.().catch(() => {});
        } else {
          document.exitFullscreen?.();
        }
      }, []);

      // Feature 1: load hyperlink sidecar once when session activates
      useEffect(() => {
        if (!session?.link_token || !session?.session_id || isTextDoc) return;
        window.SecureDocAPI.getDocumentLinks(session.link_token, session.session_id)
          .then(data => {
            const map = {};
            for (const p of (data.pages || [])) map[p.page] = p.links || [];
            pageLinksRef.current = map;
            setLinksLoaded(true);
          })
          .catch(() => {});
      }, [session?.link_token, session?.session_id, isTextDoc]);

      // Feature 2: compute search highlights when page or query changes
      const _computeHighlights = useCallback((pageNum, query) => {
        if (!query) { setSearchHighlights([]); return; }
        const words = wordPositionsRef.current[pageNum] || [];
        const ql = query.toLowerCase();
        setSearchHighlights(words.filter(w => w.t && w.t.toLowerCase().includes(ql)));
      }, []);

      useEffect(() => {
        if (!searchHighlightQuery || !session?.link_token) {
          setSearchHighlights([]);
          return;
        }
        // If already fetched (even if empty), just recompute from what we have
        if (wordPositionsFetched.current) {
          _computeHighlights(page, searchHighlightQuery);
          return;
        }
        wordPositionsFetched.current = true;
        window.SecureDocAPI.getWordPositions(session.link_token, session.session_id)
          .then(data => {
            const map = {};
            for (const p of (data.pages || [])) map[p.page] = p.words || [];
            wordPositionsRef.current = map;
            _computeHighlights(page, searchHighlightQuery);
          })
          .catch(() => {});
      }, [searchHighlightQuery, page, session?.link_token, session?.session_id, _computeHighlights]);

      useEffect(() => {
        const h = e => {
          if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goNext();
          if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') goPrev();
          // Ctrl+F / Cmd+F opens in-viewer search
          if ((e.ctrlKey || e.metaKey) && e.key === 'f' && session) {
            e.preventDefault();
            setShowSearch(v => !v);
          }
        };
        // Block browser native page-zoom from trackpad pinch (ctrlKey+wheel).
        // Zoom is controlled ONLY by the toolbar +/− buttons.
        const blockPinchZoom = e => { if (e.ctrlKey || e.metaKey) e.preventDefault(); };
        window.addEventListener('keydown', h);
        window.addEventListener('wheel', blockPinchZoom, { passive: false });
        return () => {
          window.removeEventListener('keydown', h);
          window.removeEventListener('wheel', blockPinchZoom);
        };
      }, [goNext, goPrev, session, _zoomBy, _setLayout]);

      // Phase 7: viewer state persistence — restore page/zoom from sessionStorage
      useEffect(() => {
        if (!session?.session_id) return;
        try {
          const saved = sessionStorage.getItem(`securedoc_vstate_${session.session_id}`);
          if (saved) {
            const { pg, zm } = JSON.parse(saved);
            if (pg && pg >= 1 && pg <= (session.page_count || 1)) setPage(pg);
            if (zm && zm >= ZOOM_MIN && zm <= ZOOM_MAX) {
              setCustomZoom(zm);
              setLayoutMode(LAYOUT.CUSTOM);
            }
          }
        } catch {}
      }, [session?.session_id]);

      // Phase 7: save viewer state on change
      useEffect(() => {
        if (!session?.session_id) return;
        try {
          sessionStorage.setItem(
            `securedoc_vstate_${session.session_id}`,
            JSON.stringify({ pg: page, zm: customZoom })
          );
        } catch {}
      }, [session?.session_id, page, customZoom]);

      // Phase 7: keep imgSrcRef in sync so loadPage (empty-deps callback) can
      // capture the current page URL for the crossfade background layer.
      useEffect(() => { imgSrcRef.current = imgSrc; }, [imgSrc]);

      // Phase 7: tab visibility — blur document when tab loses focus (already
      // handled by blur/focus events), but also handle visibilitychange for
      // more reliable mobile tab-switch detection
      useEffect(() => {
        if (!session) return;
        const onVis = () => setBlurred(document.hidden);
        document.addEventListener('visibilitychange', onVis);
        return () => document.removeEventListener('visibilitychange', onVis);
      }, [session]);

      useEffect(() => {
        const h = () => setIsFullscreen(!!document.fullscreenElement);
        document.addEventListener('fullscreenchange', h);
        return () => document.removeEventListener('fullscreenchange', h);
      }, []);

      useEffect(() => {
        if (document.getElementById('sdoc-vx-styles')) return;
        const s = document.createElement('style');
        s.id = 'sdoc-vx-styles';
        s.textContent = '@keyframes sdoc-shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}';
        document.head.appendChild(s);
      }, []);

      // All hooks have run — safe to conditionally return now
      if (gateInfo && !session) {
        return (
          <AccessGate
            gateInfo={gateInfo}
            error={gateError}
            onSubmit={(email, pw) => { setGateError(null); doValidate(pendingToken, email, pw); }}
          />
        );
      }

      // No document selected (authenticated mode only — public token always has a doc).
      // Show an inline picker so the user can select without leaving the Viewer tab.
      if (!docId && !publicToken && !initializing) {
        return (
          <div data-testid="viewer-screen" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Header screen="viewer" />
            <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
              <DocumentPicker onSelect={(d) => { if (onSelectDoc) onSelectDoc(d); }} />
            </div>
          </div>
        );
      }

      return (
        <div data-testid="viewer-screen" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
          {/* Chrome-style top toolbar — all viewer controls in one compact row */}
          <ViewerToolbar
            doc={doc}
            docName={docName}
            isTextDoc={isTextDoc}
            page={page} PAGE_COUNT={PAGE_COUNT}
            pageInputStr={pageInputStr} setPageInputStr={setPageInputStr} setPage={setPage}
            goPrev={goPrev} goNext={goNext}
            layoutMode={layoutMode} customZoom={customZoom}
            _zoomBy={_zoomBy} _zoomTo={_zoomTo} _setLayout={_setLayout}
            LAYOUT={LAYOUT} ZOOM_STEP={ZOOM_STEP} ZOOM_PRESETS={ZOOM_PRESETS}
            showLaser={showLaser} setShowLaser={setShowLaser}
            showMagnifier={showMagnifier} setShowMagnifier={setShowMagnifier}
            showInsights={showInsights} setShowInsights={v => {
              setShowInsights(v);
              if (v && !insightsData && !insightsLoading && doc?.id) {
                setInsightsLoading(true);
                window.SecureDocAPI.getPageHeatmap(doc.id)
                  .then(d => setInsightsData(d))
                  .catch(() => setInsightsData(null))
                  .finally(() => setInsightsLoading(false));
              }
            }}
            hasInsights={!!doc?.id}
            isFullscreen={isFullscreen} toggleFullscreen={toggleFullscreen}
            showToc={showToc} setShowToc={setShowToc}
            showSearch={showSearch} setShowSearch={setShowSearch}
            showInfo={showInfo} setShowInfo={setShowInfo}
            showPageList={showPageList} setShowPageList={setShowPageList}
            canDownload={!!session?.permissions?.can_download}
            canPrint={!!session?.permissions?.can_print}
            onDownload={async () => {
              if (!session?.permissions?.can_download) return;
              toast('Preparing download…', 'info');
              try {
                await window.SecureDocAPI.downloadDocument(session.link_token, session.session_id, session.document_filename);
                toast('Download complete', 'success');
              } catch (e) { toast(e?.detail || 'Download failed', 'error'); }
            }}
            onPrint={() => {
              if (session?.permissions?.can_print) {
                window.print();
                window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'printed');
              }
            }}
            C={C} mono={mono}
          />

          {/* Feature 3: Search panel — fixed viewport overlay, never pushes content */}
          {showSearch && session && (
            <SearchPanel
              session={session}
              onClose={() => { setShowSearch(false); setSearchHighlightQuery(''); setActiveHighlightIdx(0); setSearchResultPages(new Set()); }}
              onNavigate={p => setPage(p)}
              onQueryChange={q => { setSearchHighlightQuery(q); if (!q) setSearchResultPages(new Set()); }}
              onActiveChange={idx => setActiveHighlightIdx(idx)}
              onResultsChange={results => setSearchResultPages(new Set((results || []).map(r => r.page)))}
            />
          )}

          {/* Feature 7: Insights modal — fixed overlay, owner-only */}
          {showInsights && doc?.id && (
            <InsightsModal
              docName={docName}
              loading={insightsLoading}
              data={insightsData}
              onClose={() => setShowInsights(false)}
              C={C} mono={mono}
            />
          )}

          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            {/* Universal TOC sidebar — PDF (page nav) and text/docx/doc (chunk nav) */}
            {showToc && session && (
              <TocSidebar
                linkToken={session.link_token}
                sessionId={session.session_id}
                currentPage={page}
                docType={session.doc_type || 'pdf'}
                onNavigate={p => { setPage(p); setShowToc(false); }}
                onClose={() => setShowToc(false)}
              />
            )}

            {/* Thumbnail strip — PDF only, toggleable via Pages button */}
            {!isTextDoc && showPageList && (
              <div className="sidebar-mobile-hidden" style={{
                width: 86, background: '#0d1117', borderRight: '1px solid rgba(255,255,255,0.06)',
                overflow: 'auto', padding: '10px 6px', display: 'flex', flexDirection: 'column', gap: 5, flexShrink: 0
              }}>
                <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: 'rgba(130,142,158,0.6)', textTransform: 'uppercase', padding: '0 4px 6px', borderBottom: '1px solid rgba(255,255,255,0.05)', marginBottom: 4 }}>Pages</div>
                {Array.from({ length: PAGE_COUNT }, (_, i) => i + 1).map(p => (
                  <PageThumb
                    key={p} p={p} active={page === p} onClick={() => setPage(p)}
                    token={session?.link_token} sessionId={session?.session_id}
                    docReady={session?.doc_status === 'ready'}
                  />
                ))}
              </div>
            )}

            {/* Main canvas */}
            <div style={{
              flex: 1, overflow: 'auto', background: '#060809',
              display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '20px 16px', gap: 12,
              position: 'relative'
            }}
              onTouchStart={e => { touchRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }; }}
              onTouchEnd={e => {
                if (!touchRef.current.x) return;
                const dx = e.changedTouches[0].clientX - touchRef.current.x;
                const dy = e.changedTouches[0].clientY - touchRef.current.y;
                if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 45) {
                  if (dx < 0) goNext(); else goPrev();
                }
                touchRef.current = { x: null, y: null };
              }}
            >
              {/* Reading progress bar */}
              {session && PAGE_COUNT > 0 && (
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, zIndex: 10, pointerEvents: 'none' }}>
                  <div style={{
                    height: '100%',
                    width: `${PAGE_COUNT > 1 ? Math.round(((page - 1) / (PAGE_COUNT - 1)) * 100) : 100}%`,
                    background: 'linear-gradient(90deg, #5ac8d0, #3db8c0)',
                    transition: 'width 0.4s ease',
                    boxShadow: '0 0 4px #5ac8d0',
                  }} />
                </div>
              )}

              {/* Security badges */}
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
                <div style={{
                  ...mono, fontSize: 9, letterSpacing: '0.9px', color: 'rgba(90,200,208,0.75)',
                  background: 'rgba(90,200,208,0.07)', border: '1px solid rgba(90,200,208,0.18)',
                  borderRadius: 4, padding: '3px 9px', textTransform: 'uppercase'
                }}>
                  ◈ WATERMARKED · TRACKED
                </div>
                {!session?.permissions?.can_download && (
                  <div style={{
                    ...mono, fontSize: 9, letterSpacing: '0.8px', color: 'rgba(224,90,69,0.75)',
                    background: 'rgba(224,90,69,0.06)', border: '1px solid rgba(224,90,69,0.18)',
                    borderRadius: 4, padding: '3px 9px', textTransform: 'uppercase'
                  }}>
                    ✕ DOWNLOAD DISABLED
                  </div>
                )}
                {session?.expires_at && (
                  <div style={{
                    ...mono, fontSize: 9, letterSpacing: '0.8px', color: 'rgba(224,154,69,0.7)',
                    background: 'rgba(224,154,69,0.06)', border: '1px solid rgba(224,154,69,0.18)',
                    borderRadius: 4, padding: '3px 9px', textTransform: 'uppercase'
                  }}>
                    ⏱ EXPIRES {session.expires_at.slice(0, 10)}
                  </div>
                )}
              </div>

              {initializing && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: C.textMuted, marginTop: 40 }}>
                  <span style={{ display: 'inline-block', width: 18, height: 18, border: `1.5px solid ${C.border}`, borderTop: `1.5px solid ${C.teal2}`, borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
                  Opening secure viewer…
                </div>
              )}
              {!initializing && session && !isTextDoc && (() => {
                // Compute page dimensions based on layout mode
                const _pgStyle = (() => {
                  if (layoutMode === LAYOUT.FIT_WIDTH) {
                    return { width: '100%', maxWidth: '100%', height: undefined };
                  }
                  if (layoutMode === LAYOUT.FIT_HEIGHT) {
                    return { width: 'auto', maxWidth: '100%', height: 'calc(100vh - 220px)', maxHeight: '100%' };
                  }
                  // CUSTOM zoom: 100% = 590px (fits a letter-size PDF at typical DPI)
                  return { width: `${customZoom * 5.9}px`, maxWidth: '100%', height: undefined };
                })();
                return (
                <div ref={pageContainerRef} className="viewer-page" style={{
                  position: 'relative', ...(_pgStyle),
                  aspectRatio: layoutMode === LAYOUT.FIT_HEIGHT ? undefined : '8.5/11',
                  flexShrink: 0, transition: 'width .25s ease, height .25s ease',
                  borderRadius: 2, overflow: 'hidden',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.5), 0 8px 48px rgba(0,0,0,0.8), 0 20px 60px rgba(0,0,0,0.35)',
                }}
                  onContextMenu={e => e.preventDefault()}
                  onTouchStart={e => {
                    if (e.touches.length === 2) {
                      const dx = e.touches[0].clientX - e.touches[1].clientX;
                      const dy = e.touches[0].clientY - e.touches[1].clientY;
                      touchRef.current.pinchDist = Math.sqrt(dx * dx + dy * dy);
                    } else {
                      touchRef.current.pinchDist = null;
                    }
                  }}
                  onTouchMove={e => {
                    if (e.touches.length === 2 && touchRef.current.pinchDist != null) {
                      e.preventDefault();
                      const dx = e.touches[0].clientX - e.touches[1].clientX;
                      const dy = e.touches[0].clientY - e.touches[1].clientY;
                      const dist = Math.sqrt(dx * dx + dy * dy);
                      const ratio = dist / touchRef.current.pinchDist;
                      touchRef.current.pinchDist = dist;
                      // Each move event = scale the zoom by the delta ratio
                      setCustomZoom(z => {
                        const next = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.round(z * ratio)));
                        if (next !== z) {
                          setLayoutMode(LAYOUT.CUSTOM);
                          _saveLayoutPref(LAYOUT.CUSTOM, next);
                        }
                        return next;
                      });
                    }
                  }}>

                  {/* Phase 7 crossfade: background layer holds previous page while next loads */}
                  {prevImgSrc && prevImgSrc !== imgSrc && (
                    <img
                      src={prevImgSrc}
                      draggable={false}
                      style={{
                        position: 'absolute', inset: 0,
                        width: '100%', height: '100%', objectFit: 'contain', display: 'block',
                        userSelect: 'none', pointerEvents: 'none',
                        filter: blurred ? 'blur(14px)' : 'none',
                        opacity: imgReady ? 0 : 1,
                        transition: 'opacity .22s ease, filter .3s',
                      }}
                      alt=""
                    />
                  )}

                  {/* Current page — fades in when browser has decoded the new image */}
                  {imgSrc && (
                    <img ref={pageImgRef} src={imgSrc} draggable={false}
                      onLoad={() => setImgReady(true)}
                      onError={() => setImgReady(true)}
                      style={{
                        width: '100%', height: '100%', objectFit: 'contain', display: 'block',
                        userSelect: 'none', WebkitTouchCallout: 'none', WebkitUserSelect: 'none',
                        filter: blurred ? 'blur(14px)' : 'none',
                        opacity: imgReady ? 1 : 0,
                        transition: 'opacity .22s ease, filter .3s',
                      }}
                      alt={`Page ${page}`}
                    />
                  )}

                  {/* Non-blocking loading badge — floats over image, doesn't obscure previous page */}
                  {imgLoading && (
                    <div style={{
                      position: 'absolute', bottom: 8, right: 8, zIndex: 2, pointerEvents: 'none',
                      display: 'flex', alignItems: 'center', gap: 5,
                      background: 'rgba(6,8,9,0.72)', borderRadius: 20, padding: '4px 10px'
                    }}>
                      <span style={{ display: 'inline-block', width: 12, height: 12, border: `1.5px solid ${C.border}`, borderTop: `1.5px solid ${C.teal2}`, borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
                      <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>p.{page}</span>
                    </div>
                  )}

                  {pageError && (
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: C.surface, flexDirection: 'column', gap: 10, padding: '20px 24px' }}>
                      <span style={{ fontSize: 22, color: 'rgba(224,154,69,0.7)' }}>⚠</span>
                      <span style={{ ...mono, fontSize: 11, color: C.textMuted, textAlign: 'center', lineHeight: 1.5 }}>{pageError}</span>
                    </div>
                  )}

                  {blurred && (
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(6,8,9,0.4)' }}>
                      <div style={{ ...mono, fontSize: 11, color: C.teal2, padding: '8px 16px', background: 'rgba(6,8,9,0.85)', borderRadius: 6, border: `1px solid ${C.borderMed}` }}>Focus window to resume</div>
                    </div>
                  )}
                  <div style={{
                    position: 'absolute', inset: 0, pointerEvents: 'none',
                    background: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.025) 3px, rgba(0,0,0,0.025) 4px)'
                  }} />
                  {/* Premium: light-sweep shimmer — purely cosmetic, server-side watermark unaffected */}
                  <div style={{
                    position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 2,
                    background: 'linear-gradient(105deg, transparent 40%, rgba(255,255,255,0.022) 50%, transparent 60%)',
                    backgroundSize: '250% 100%',
                    animation: 'sdoc-shimmer 5s ease-in-out infinite',
                  }} />

                  {/* Feature 2: Search highlight overlays — yellow (inactive) / orange (active) */}
                  {searchHighlights.map((m, i) => {
                    const isActive = i === activeHighlightIdx;
                    return (
                      <div key={i} style={{
                        position: 'absolute',
                        left: `${m.x * 100}%`, top: `${m.y * 100}%`,
                        width: `${m.w * 100}%`, height: `${m.h * 100}%`,
                        background: isActive ? 'rgba(255,145,0,0.55)' : 'rgba(255,220,0,0.32)',
                        border: isActive ? '1.5px solid rgba(255,120,0,0.85)' : '1px solid rgba(255,200,0,0.45)',
                        borderRadius: 1, pointerEvents: 'none', zIndex: 6,
                        boxShadow: isActive ? '0 0 6px rgba(255,145,0,0.4)' : 'none',
                        transition: 'background .15s, border .15s, box-shadow .15s',
                      }} />
                    );
                  })}

                  {/* Feature 2 fallback: page-match glow when word positions unavailable */}
                  {searchHighlightQuery && searchResultPages.has(page) && searchHighlights.length === 0 && (
                    <div style={{
                      position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 5,
                      boxShadow: 'inset 0 0 0 3px rgba(255,200,0,0.55)',
                      borderRadius: 2,
                    }} />
                  )}

                  {/* Feature 1: Hyperlink clickable overlays — transparent, pointer-events active */}
                  {linksLoaded && (pageLinksRef.current[page] || []).map((link, i) => (
                    <a key={i} href={link.url} target="_blank" rel="noopener noreferrer"
                      style={{
                        position: 'absolute',
                        left: `${link.x * 100}%`, top: `${link.y * 100}%`,
                        width: `${link.w * 100}%`, height: `${link.h * 100}%`,
                        cursor: 'pointer', pointerEvents: 'auto', zIndex: 7,
                        display: 'block',
                      }}
                      title={link.url}
                    />
                  ))}
                </div>
                );
              })()}

              {!initializing && session && isTextDoc && (
                <div className="viewer-page" style={{
                  position: 'relative', width: '100%', maxWidth: 800, flexShrink: 0,
                  borderRadius: 2, overflow: 'hidden', boxShadow: '0 8px 48px rgba(0,0,0,0.7)',
                  background: C.surface
                }}
                  onContextMenu={e => e.preventDefault()}>
                  {textLoading && (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 24px', flexDirection: 'column', gap: 10 }}>
                      <span style={{ display: 'inline-block', width: 22, height: 22, border: `1.5px solid ${C.border}`, borderTop: `1.5px solid ${C.teal2}`, borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
                      <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>Loading chunk {page}…</span>
                    </div>
                  )}
                  {!textLoading && textError && (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 24px', flexDirection: 'column', gap: 10 }}>
                      <span style={{ fontSize: 22, color: 'rgba(224,154,69,0.7)' }}>⚠</span>
                      <span style={{ ...mono, fontSize: 11, color: C.textMuted, textAlign: 'center', lineHeight: 1.5 }}>{textError}</span>
                    </div>
                  )}
                  {!textLoading && !textError && (
                    <pre style={{
                      margin: 0, padding: '20px 24px',
                      fontFamily: 'ui-monospace, "SFMono-Regular", Consolas, monospace',
                      fontSize: 13, lineHeight: 1.7, color: '#e2e8f0',
                      whiteSpace: 'pre-wrap', wordBreak: 'break-word', overflowX: 'hidden',
                      userSelect: session?.permissions?.can_copy ? 'text' : 'none',
                      WebkitUserSelect: session?.permissions?.can_copy ? 'text' : 'none',
                      filter: blurred ? 'blur(14px)' : 'none', transition: 'filter .3s',
                      minHeight: 200
                    }}>
                      {textContent}
                    </pre>
                  )}
                  {/* watermark overlay — pointer-events:none so it doesn't block selection */}
                  {session?.watermark_text && (
                    <div style={{
                      position: 'absolute', inset: 0, pointerEvents: 'none',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      overflow: 'hidden', userSelect: 'none'
                    }}>
                      <div style={{
                        ...mono, fontSize: 16, fontWeight: 700,
                        color: 'rgba(90,200,208,0.18)',
                        transform: 'rotate(-30deg)', whiteSpace: 'nowrap', letterSpacing: '0.05em'
                      }}>
                        {session.watermark_text}
                      </div>
                    </div>
                  )}
                  {blurred && (
                    <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(6,8,9,0.4)' }}>
                      <div style={{ ...mono, fontSize: 11, color: C.teal2, padding: '8px 16px', background: 'rgba(6,8,9,0.85)', borderRadius: 6, border: `1px solid ${C.borderMed}` }}>Focus window to resume</div>
                    </div>
                  )}
                </div>
              )}
              {!initializing && !session && (
                <div style={{ textAlign: 'center', color: C.textMuted, marginTop: 40 }}>
                  <div style={{ fontSize: 13, marginBottom: 8 }}>Document not ready for viewing</div>
                  <div style={{ ...mono, fontSize: 10, color: C.textDim }}>Status: {doc?.status} — wait for processing to complete</div>
                </div>
              )}

            </div>

            {/* Info panel */}
            {showInfo && (
              <div style={{
                width: 230, background: C.surfaceAlt, borderLeft: `1px solid ${C.border}`,
                padding: 16, overflow: 'auto', flexShrink: 0
              }} className="slide-in">
                <ViewerInfoPanel doc={doc} docId={docId} page={page} session={session} pageCount={PAGE_COUNT} />
              </div>
            )}
          </div>

          {/* Feature 5: Laser pointer — GPU-accelerated, ref-based (no setState on mousemove) */}
          <LaserPointer active={showLaser} />
          {/* Feature 4: Rectangular magnifier */}
          <RectMagnifier active={showMagnifier} imgSrc={imgSrc} pageContainerRef={pageContainerRef} />
        </div>
      );
    }

    // ── Professional top toolbar ──────────────────────────────────────────────
    function ViewerToolbar({
      doc, docName, isTextDoc,
      page, PAGE_COUNT, pageInputStr, setPageInputStr, setPage,
      goPrev, goNext,
      layoutMode, customZoom, _zoomBy, _zoomTo, _setLayout,
      LAYOUT, ZOOM_STEP, ZOOM_PRESETS,
      showLaser, setShowLaser, showMagnifier, setShowMagnifier,
      showInsights, setShowInsights, hasInsights,
      isFullscreen, toggleFullscreen,
      showToc, setShowToc, showSearch, setShowSearch, showInfo, setShowInfo,
      showPageList, setShowPageList,
      canDownload, canPrint, onDownload, onPrint,
      C, mono,
    }) {
      const btn = {
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'rgba(148,160,176,0.85)', borderRadius: 4, padding: '3px 7px',
        fontSize: 11, lineHeight: '16px', transition: 'color .1s, background .1s',
        display: 'flex', alignItems: 'center', gap: 3, whiteSpace: 'nowrap',
        fontFamily: "'DM Sans', sans-serif", flexShrink: 0,
      };
      const on = { background: 'rgba(90,200,208,0.12)', color: '#5ac8d0' };
      const sep = <div style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.07)', margin: '0 2px', flexShrink: 0 }} />;

      const groupName = doc?.group_name || 'General';
      const groupColor = doc?.group_color || '#6b7280';

      const commitPage = () => {
        const p = parseInt(pageInputStr, 10);
        if (!isNaN(p) && p >= 1 && p <= PAGE_COUNT) setPage(p);
        setPageInputStr('');
      };

      const zoomLabel = layoutMode === LAYOUT.FIT_WIDTH ? 'W'
        : layoutMode === LAYOUT.FIT_HEIGHT ? 'H'
        : `${customZoom}%`;

      return (
        <div style={{
          height: 42, background: '#10151d',
          borderBottom: '1px solid rgba(255,255,255,0.055)',
          display: 'flex', alignItems: 'center', padding: '0 8px',
          flexShrink: 0, userSelect: 'none', gap: 0, zIndex: 50,
          boxShadow: '0 1px 0 rgba(0,0,0,0.35)',
        }}>

          {/* ── LEFT: sidebar toggles ── */}
          <button onClick={() => setShowToc(v => !v)} title="Table of Contents"
            style={{ ...btn, ...(showToc ? on : {}) }}>
            <svg width="13" height="10" viewBox="0 0 13 10" fill="none" style={{ flexShrink: 0 }}>
              <rect x="0" y="0" width="3" height="2" rx="0.5" fill="currentColor" opacity=".7"/>
              <rect x="5" y="0" width="8" height="2" rx="0.5" fill="currentColor"/>
              <rect x="0" y="4" width="3" height="2" rx="0.5" fill="currentColor" opacity=".7"/>
              <rect x="5" y="4" width="8" height="2" rx="0.5" fill="currentColor"/>
              <rect x="0" y="8" width="3" height="2" rx="0.5" fill="currentColor" opacity=".7"/>
              <rect x="5" y="8" width="5" height="2" rx="0.5" fill="currentColor"/>
            </svg>
            TOC
          </button>

          {!isTextDoc && (
            <button onClick={() => setShowPageList(v => !v)} title="Page list"
              style={{ ...btn, ...(showPageList ? on : {}) }}>
              <svg width="11" height="12" viewBox="0 0 11 12" fill="none" style={{ flexShrink: 0 }}>
                <rect x="1" y="0" width="9" height="11" rx="1" stroke="currentColor" strokeWidth="1.2" fill="none"/>
                <rect x="3" y="3" width="5" height="1" rx="0.4" fill="currentColor"/>
                <rect x="3" y="5.5" width="5" height="1" rx="0.4" fill="currentColor"/>
                <rect x="3" y="8" width="3" height="1" rx="0.4" fill="currentColor"/>
              </svg>
              Pages
            </button>
          )}

          <button onClick={() => setShowSearch(v => !v)} title="Search (Ctrl+F)"
            style={{ ...btn, ...(showSearch ? on : {}) }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
              <circle cx="5" cy="5" r="3.5" stroke="currentColor" strokeWidth="1.3" fill="none"/>
              <line x1="7.8" y1="7.8" x2="11" y2="11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            Search
          </button>

          {sep}

          {/* ── Doc breadcrumb: Group › Filename ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, minWidth: 0, overflow: 'hidden', flexShrink: 1 }}>
            <span style={{
              fontSize: 10, padding: '1px 7px', borderRadius: 10,
              background: `${groupColor}1a`, color: groupColor,
              border: `1px solid ${groupColor}33`,
              fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: '0.02em',
              whiteSpace: 'nowrap', flexShrink: 0,
            }}>{groupName}</span>
            <svg width="5" height="9" viewBox="0 0 5 9" fill="none" style={{ flexShrink: 0, opacity: 0.35 }}>
              <path d="M1 1l3 3.5L1 8" stroke="rgba(180,190,200,1)" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span style={{
              fontSize: 11.5, fontWeight: 500, color: 'rgba(210,218,228,0.9)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              fontFamily: "'DM Sans',sans-serif",
            }} title={docName}>{docName || '—'}</span>
          </div>

          <div style={{ flex: 1, minWidth: 12 }} />

          {/* ── CENTER: page navigation ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
            <button onClick={goPrev} disabled={page <= 1} title="Previous (←)"
              style={{ ...btn, opacity: page <= 1 ? 0.25 : 1, padding: '3px 5px', fontSize: 15 }}>‹</button>
            <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(255,255,255,0.055)', borderRadius: 4, border: '1px solid rgba(255,255,255,0.09)', overflow: 'hidden' }}>
              <input
                type="text"
                value={pageInputStr !== '' ? pageInputStr : String(page)}
                onChange={e => setPageInputStr(e.target.value)}
                onFocus={e => { setPageInputStr(String(page)); e.target.select(); }}
                onBlur={commitPage}
                onKeyDown={e => {
                  if (e.key === 'Enter') { commitPage(); e.target.blur(); }
                  if (e.key === 'Escape') { setPageInputStr(''); e.target.blur(); }
                }}
                style={{
                  ...mono, fontSize: 11, fontWeight: 700, color: 'rgba(220,228,238,1)',
                  background: 'transparent', border: 'none',
                  padding: '3px 0 3px 6px', textAlign: 'center', width: 28, outline: 'none',
                }}
              />
              <span style={{ ...mono, fontSize: 11, color: 'rgba(100,112,128,0.9)', padding: '0 6px 0 2px' }}>/ {PAGE_COUNT}</span>
            </div>
            <button onClick={goNext} disabled={page >= PAGE_COUNT} title="Next (→)"
              style={{ ...btn, opacity: page >= PAGE_COUNT ? 0.25 : 1, padding: '3px 5px', fontSize: 15 }}>›</button>
          </div>

          {!isTextDoc && (<>
            {sep}
            {/* ── Fit-Width / Fit-Height buttons ── */}
            <button onClick={() => _setLayout(LAYOUT.FIT_WIDTH)} title="Fit to width"
              style={{ ...btn, ...(layoutMode === LAYOUT.FIT_WIDTH ? on : {}), padding: '3px 7px', fontSize: 10, fontWeight: 600 }}>
              W
            </button>
            <button onClick={() => _setLayout(LAYOUT.FIT_HEIGHT)} title="Fit to height"
              style={{ ...btn, ...(layoutMode === LAYOUT.FIT_HEIGHT ? on : {}), padding: '3px 7px', fontSize: 10, fontWeight: 600 }}>
              H
            </button>
            {sep}
            {/* ── Zoom pill: − [level] + ── */}
            <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(255,255,255,0.045)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 4, overflow: 'hidden', flexShrink: 0 }}>
              <button onClick={() => _zoomBy(-ZOOM_STEP)} title="Zoom out"
                style={{ ...btn, padding: '3px 6px', fontSize: 14, borderRadius: 0, borderRight: '1px solid rgba(255,255,255,0.07)' }}>−</button>
              <select
                value={layoutMode === LAYOUT.CUSTOM ? customZoom : layoutMode === LAYOUT.FIT_WIDTH ? 'fw' : 'fh'}
                onChange={e => {
                  const v = e.target.value;
                  if (v === 'fw') _setLayout(LAYOUT.FIT_WIDTH);
                  else if (v === 'fh') _setLayout(LAYOUT.FIT_HEIGHT);
                  else _zoomTo(parseInt(v, 10));
                }}
                title="Zoom level"
                style={{
                  ...mono, fontSize: 10, color: 'rgba(165,175,188,0.9)',
                  background: 'transparent', border: 'none',
                  padding: '3px 2px', cursor: 'pointer',
                  width: 44, textAlign: 'center', appearance: 'none', WebkitAppearance: 'none', outline: 'none',
                }}>
                {ZOOM_PRESETS.map(p => <option key={p} value={p}>{p}%</option>)}
                {layoutMode === LAYOUT.CUSTOM && !ZOOM_PRESETS.includes(customZoom) && (
                  <option value={customZoom}>{customZoom}%</option>
                )}
                {layoutMode === LAYOUT.FIT_WIDTH && <option value="fw">W-fit</option>}
                {layoutMode === LAYOUT.FIT_HEIGHT && <option value="fh">H-fit</option>}
              </select>
              <button onClick={() => _zoomBy(ZOOM_STEP)} title="Zoom in"
                style={{ ...btn, padding: '3px 6px', fontSize: 14, borderRadius: 0, borderLeft: '1px solid rgba(255,255,255,0.07)' }}>+</button>
            </div>
            {sep}
            {/* ── Magnifier toggle ── */}
            <button onClick={() => { setShowMagnifier(v => !v); if (showLaser) setShowLaser(false); }}
              title="Rectangular magnifier (2.5×)"
              style={{ ...btn, ...(showMagnifier ? on : {}), padding: '3px 7px' }}>
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ flexShrink: 0 }}>
                <circle cx="5.5" cy="5.5" r="4" stroke="currentColor" strokeWidth="1.3" fill="none"/>
                <line x1="8.8" y1="8.8" x2="12" y2="12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="3.5" y1="5.5" x2="7.5" y2="5.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity=".6"/>
                <line x1="5.5" y1="3.5" x2="5.5" y2="7.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity=".6"/>
              </svg>
              Magnify
            </button>
            {sep}
            {/* ── Laser pointer toggle ── */}
            <button onClick={() => { setShowLaser(v => !v); if (showMagnifier) setShowMagnifier(false); }}
              title="Laser pointer (presentation mode)"
              style={{ ...btn, ...(showLaser ? { ...on, color: '#ff4444' } : {}), padding: '3px 7px' }}>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
                <circle cx="6" cy="6" r="3" fill={showLaser ? '#ff4444' : 'currentColor'} opacity={showLaser ? 1 : 0.7}/>
                <circle cx="6" cy="6" r="5" stroke={showLaser ? '#ff4444' : 'currentColor'} strokeWidth="1" fill="none" opacity="0.4"/>
              </svg>
              Laser
            </button>
          </>)}

          <div style={{ flex: 1, minWidth: 12 }} />

          {/* ── RIGHT: actions ── */}
          {hasInsights && (
            <>
              <button onClick={() => setShowInsights(v => !v)} title="Page engagement insights"
                style={{ ...btn, ...(showInsights ? on : {}), padding: '3px 7px' }}>
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ flexShrink: 0 }}>
                  <rect x="1" y="7" width="2" height="4" rx="0.5" fill="currentColor" opacity=".9"/>
                  <rect x="5" y="4" width="2" height="7" rx="0.5" fill="currentColor" opacity=".9"/>
                  <rect x="9" y="1" width="2" height="10" rx="0.5" fill="currentColor" opacity=".9"/>
                </svg>
                Insights
              </button>
              {sep}
            </>
          )}
          <button onClick={toggleFullscreen} title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen (F)'}
            style={{ ...btn, padding: '3px 7px' }}>
            {isFullscreen
              ? <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M4 1H1v3M8 1h3v3M4 11H1V8M8 11h3V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
              : <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M1 4V1h3M8 1h3v3M11 8v3H8M4 11H1V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>
            }
          </button>
          {sep}
          <button onClick={onDownload} disabled={!canDownload} title="Download"
            style={{ ...btn, opacity: canDownload ? 1 : 0.28 }}>
            <svg width="11" height="12" viewBox="0 0 11 12" fill="none" style={{ flexShrink: 0 }}>
              <path d="M5.5 1v7M2.5 5.5l3 3 3-3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M1 10h9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            Download
          </button>
          <button onClick={onPrint} disabled={!canPrint} title="Print"
            style={{ ...btn, opacity: canPrint ? 1 : 0.28 }}>
            <svg width="12" height="11" viewBox="0 0 12 11" fill="none" style={{ flexShrink: 0 }}>
              <rect x="2" y="4" width="8" height="5" rx="1" stroke="currentColor" strokeWidth="1.2" fill="none"/>
              <path d="M3 4V2h6v2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
              <rect x="3.5" y="6" width="5" height="1" rx="0.4" fill="currentColor" opacity=".7"/>
              <rect x="3.5" y="7.8" width="3" height="1" rx="0.4" fill="currentColor" opacity=".7"/>
            </svg>
            Print
          </button>
          {sep}
          <button onClick={() => setShowInfo(v => !v)} title="Document info"
            style={{ ...btn, ...(showInfo ? on : {}), padding: '3px 7px' }}>
            <svg width="11" height="13" viewBox="0 0 11 13" fill="none" style={{ flexShrink: 0 }}>
              <circle cx="5.5" cy="3" r="1.2" fill="currentColor"/>
              <rect x="4.5" y="6" width="2" height="5" rx="0.8" fill="currentColor"/>
            </svg>
            Info
          </button>
        </div>
      );
    }

    // ── Feature 5: Laser pointer — GPU-accelerated, ref-based, zero setState lag ─
    function LaserPointer({ active }) {
      const dotRef = useRef(null);
      useEffect(() => {
        if (!active) return;
        const move = e => {
          if (dotRef.current) {
            dotRef.current.style.transform = `translate(${e.clientX - 10}px, ${e.clientY - 10}px)`;
            dotRef.current.style.opacity = '1';
          }
        };
        document.addEventListener('mousemove', move, { passive: true });
        return () => document.removeEventListener('mousemove', move);
      }, [active]);
      if (!active) return null;
      return (
        <div ref={dotRef} style={{
          position: 'fixed', top: 0, left: 0,
          width: 20, height: 20, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,60,60,1) 0%, rgba(255,60,60,0.7) 35%, rgba(255,60,60,0.15) 70%, transparent 100%)',
          boxShadow: '0 0 8px 3px rgba(255,50,50,0.55), 0 0 18px 6px rgba(255,50,50,0.25)',
          pointerEvents: 'none', zIndex: 9999,
          transform: 'translate(-9999px,-9999px)',
          willChange: 'transform',
        }} />
      );
    }

    // ── Feature 4: Rectangular magnifier — GPU-accelerated, ref-based ────────
    function RectMagnifier({ active, imgSrc, pageContainerRef }) {
      const MAG_W = 272, MAG_H = 180, SCALE = 2.5;
      const magnRef = useRef(null);

      useEffect(() => {
        if (!active || !pageContainerRef?.current) return;
        const container = pageContainerRef.current;

        const move = e => {
          const mag = magnRef.current;
          if (!mag || !imgSrc) return;
          const imgEl = container.querySelector('img[alt]');
          if (!imgEl) return;
          const imgRect = imgEl.getBoundingClientRect();
          const cx = e.clientX - imgRect.left;
          const cy = e.clientY - imgRect.top;
          if (cx < 0 || cy < 0 || cx > imgRect.width || cy > imgRect.height) {
            mag.style.opacity = '0'; return;
          }
          // Position magnifier to the right; flip left if near viewport edge
          let mx = e.clientX + 24;
          let my = e.clientY - MAG_H / 2;
          if (mx + MAG_W > window.innerWidth - 8) mx = e.clientX - MAG_W - 24;
          if (my < 8) my = 8;
          if (my + MAG_H > window.innerHeight - 8) my = window.innerHeight - MAG_H - 8;
          mag.style.transform = `translate(${mx}px, ${my}px)`;
          // Background-image zoom: position so cursor area is centred in magnifier
          const bgX = -(cx * SCALE - MAG_W / 2);
          const bgY = -(cy * SCALE - MAG_H / 2);
          mag.style.backgroundImage = `url("${imgSrc}")`;
          mag.style.backgroundSize = `${imgRect.width * SCALE}px ${imgRect.height * SCALE}px`;
          mag.style.backgroundPosition = `${bgX}px ${bgY}px`;
          mag.style.opacity = '1';
        };
        const leave = () => { if (magnRef.current) magnRef.current.style.opacity = '0'; };

        container.addEventListener('mousemove', move, { passive: true });
        container.addEventListener('mouseleave', leave, { passive: true });
        return () => {
          container.removeEventListener('mousemove', move);
          container.removeEventListener('mouseleave', leave);
        };
      }, [active, imgSrc, pageContainerRef]);

      if (!active) return null;
      return (
        <div ref={magnRef} style={{
          position: 'fixed', top: 0, left: 0, width: MAG_W, height: MAG_H,
          borderRadius: 8, overflow: 'hidden',
          border: '1.5px solid rgba(90,200,208,0.45)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.72), 0 0 0 1px rgba(90,200,208,0.12)',
          backgroundRepeat: 'no-repeat',
          opacity: 0, pointerEvents: 'none', zIndex: 1200,
          willChange: 'transform, opacity, background-position',
          transform: 'translate(-9999px,-9999px)',
          transition: 'opacity .08s',
        }}>
          <div style={{
            position: 'absolute', bottom: 6, right: 8, pointerEvents: 'none',
            fontFamily: 'ui-monospace,monospace', fontSize: 9, letterSpacing: '0.06em',
            color: 'rgba(90,200,208,0.9)', background: 'rgba(6,8,9,0.78)',
            padding: '2px 7px', borderRadius: 3,
            border: '1px solid rgba(90,200,208,0.22)',
          }}>2.5× ZOOM</div>
        </div>
      );
    }

    // ── Feature 7 (viewer): Insights modal — page engagement heatmap ──────────
    function InsightsModal({ docName, loading, data, onClose, C, mono }) {
      return (
        <div style={{
          position: 'fixed', top: 56, right: 16, zIndex: 700,
          width: 340,
          background: 'rgba(12,16,24,0.92)',
          backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
          border: '1px solid rgba(90,200,208,0.2)',
          borderRadius: 10,
          boxShadow: '0 8px 40px rgba(0,0,0,0.75), 0 0 0 1px rgba(90,200,208,0.07)',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '10px 12px', borderBottom: '1px solid rgba(255,255,255,0.06)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <rect x="1" y="7" width="2" height="4" rx="0.5" fill="#5ac8d0" opacity=".9"/>
              <rect x="5" y="4" width="2" height="7" rx="0.5" fill="#5ac8d0" opacity=".9"/>
              <rect x="9" y="1" width="2" height="10" rx="0.5" fill="#5ac8d0" opacity=".9"/>
            </svg>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'rgba(220,228,238,0.9)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              Page Insights
            </span>
            <span style={{ fontSize: 10, color: 'rgba(130,142,158,0.7)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 120 }} title={docName}>{docName}</span>
            <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'rgba(148,160,176,0.7)', fontSize: 14, padding: '0 2px', lineHeight: 1, marginLeft: 4 }}>✕</button>
          </div>
          {loading && (
            <div style={{ padding: '28px 16px', textAlign: 'center', color: 'rgba(130,142,158,0.7)', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <span style={{ display: 'inline-block', width: 14, height: 14, border: '1.5px solid rgba(90,200,208,0.3)', borderTop: '1.5px solid #5ac8d0', borderRadius: '50%', animation: 'spin .65s linear infinite' }} />
              Loading insights…
            </div>
          )}
          {!loading && (!data || data.pages.length === 0) && (
            <div style={{ padding: '28px 16px', textAlign: 'center', color: 'rgba(130,142,158,0.55)', fontSize: 12 }}>
              No page views recorded yet.
            </div>
          )}
          {!loading && data && data.pages.length > 0 && (
            <div style={{ padding: '10px 12px', maxHeight: 360, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'rgba(130,142,158,0.55)', marginBottom: 4 }}>
                Most Viewed Pages · {data.total_views} total views
              </div>
              {data.pages.slice(0, 15).map((p, i) => {
                const maxViews = data.pages[0]?.views || 1;
                const barPct = Math.max(3, Math.round((p.views / maxViews) * 100));
                const heat = p.pct > 15 ? '#ff6b35' : p.pct > 8 ? '#ffd166' : '#5ac8d0';
                return (
                  <div key={p.page} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ fontFamily: 'ui-monospace,monospace', fontSize: 9, color: 'rgba(130,142,158,0.7)', width: 40, flexShrink: 0, textAlign: 'right' }}>
                      {i < 3 ? '🔥' : ''} p.{p.page}
                    </div>
                    <div style={{ flex: 1, height: 14, background: 'rgba(255,255,255,0.04)', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{
                        width: `${barPct}%`, height: '100%',
                        background: `linear-gradient(90deg, ${heat}88, ${heat})`,
                        borderRadius: 3,
                      }} />
                    </div>
                    <div style={{ fontFamily: 'ui-monospace,monospace', fontSize: 9, color: 'rgba(148,160,176,0.8)', width: 38, flexShrink: 0, textAlign: 'right' }}>
                      {p.views}v {p.avg_time_sec > 0 ? `${p.avg_time_sec}s` : ''}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    // ── Feature 3 (fixed): Search panel — glassmorphism fixed viewport overlay ─
    function SearchPanel({ session, onClose, onNavigate, onQueryChange, onActiveChange, onResultsChange }) {
      const [query, setQuery] = useState('');
      const [results, setResults] = useState([]);
      const [loading, setLoading] = useState(false);
      const [currentIdx, setCurrentIdx] = useState(0);
      const inputRef = useRef(null);

      useEffect(() => { inputRef.current?.focus(); }, []);

      useEffect(() => {
        onQueryChange?.(query.trim());
        if (!query.trim() || !session) { setResults([]); onActiveChange?.(0); onResultsChange?.([]); return; }
        const timer = setTimeout(async () => {
          setLoading(true);
          try {
            const data = await window.SecureDocAPI.searchDocument(
              session.link_token, query, session.session_id
            );
            const found = data.results || [];
            setResults(found);
            setCurrentIdx(0);
            onActiveChange?.(0);
            onResultsChange?.(found);
            if (found.length > 0) onNavigate(found[0].page);
          } catch {
            setResults([]);
          } finally {
            setLoading(false);
          }
        }, 450);
        return () => clearTimeout(timer);
      }, [query, session?.link_token, session?.session_id]);

      const goTo = (idx, rs) => { const r = (rs || results)[idx]; if (r) { onNavigate(r.page); onActiveChange?.(idx); } };
      const goNext = () => {
        const next = (currentIdx + 1) % Math.max(1, results.length);
        setCurrentIdx(next); goTo(next);
      };
      const goPrev = () => {
        const prev = (currentIdx - 1 + Math.max(1, results.length)) % Math.max(1, results.length);
        setCurrentIdx(prev); goTo(prev);
      };

      const iBtn = {
        background: 'none', border: 'none', cursor: 'pointer', padding: '3px 5px',
        color: 'rgba(148,160,176,0.8)', borderRadius: 4, lineHeight: 1,
        transition: 'color .1s, background .1s', fontSize: 12,
      };

      return (
        <div style={{
          position: 'fixed', top: 56, right: 16, zIndex: 600,
          background: 'rgba(14,18,28,0.9)',
          backdropFilter: 'blur(20px)', WebkitBackdropFilter: 'blur(20px)',
          border: '1px solid rgba(90,200,208,0.22)',
          borderRadius: 10, padding: '10px 12px', width: 340,
          boxShadow: '0 8px 40px rgba(0,0,0,0.7), 0 0 0 1px rgba(90,200,208,0.08)',
          display: 'flex', flexDirection: 'column', gap: 0,
        }}>
          {/* Input row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ flexShrink: 0, color: '#5ac8d0', opacity: 0.8 }}>
              <circle cx="5.5" cy="5.5" r="4" stroke="currentColor" strokeWidth="1.4" fill="none"/>
              <line x1="8.8" y1="8.8" x2="12" y2="12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <input
              ref={inputRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') { e.preventDefault(); e.shiftKey ? goPrev() : goNext(); }
                if (e.key === 'Escape') onClose();
              }}
              placeholder="Search entire document…"
              style={{
                flex: 1, background: 'transparent', border: 'none', outline: 'none',
                fontSize: 12.5, color: 'rgba(220,228,238,0.95)',
                fontFamily: "'DM Sans',sans-serif", letterSpacing: '0.01em',
              }}
            />
            <span style={{
              fontFamily: 'ui-monospace,monospace', fontSize: 10,
              color: loading ? '#5ac8d0' : results.length > 0 ? 'rgba(148,160,176,0.85)' : query.trim() ? 'rgba(200,80,80,0.8)' : 'transparent',
              flexShrink: 0, minWidth: 32, textAlign: 'right',
            }}>
              {loading ? '…' : results.length > 0 ? `${currentIdx + 1}/${results.length}` : query.trim() ? '0' : ''}
            </span>
            <div style={{ display: 'flex', gap: 1, borderLeft: '1px solid rgba(255,255,255,0.07)', paddingLeft: 6, marginLeft: 2 }}>
              <button onClick={goPrev} disabled={results.length === 0} title="Previous (Shift+Enter)" style={iBtn}>↑</button>
              <button onClick={goNext} disabled={results.length === 0} title="Next (Enter)" style={iBtn}>↓</button>
              <button onClick={onClose} title="Close (Esc)" style={{ ...iBtn, fontSize: 13 }}>✕</button>
            </div>
          </div>

          {/* Divider + results */}
          {results.length > 0 && (
            <>
              <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '8px -12px' }} />
              <div style={{ maxHeight: 240, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2, margin: '0 -2px' }}>
                {results.slice(0, 50).map((r, i) => {
                  const isActive = i === currentIdx;
                  return (
                    <div key={i}
                      onClick={() => { setCurrentIdx(i); onNavigate(r.page); }}
                      style={{
                        fontFamily: 'ui-monospace,monospace', fontSize: 10.5,
                        color: isActive ? 'rgba(220,228,238,0.95)' : 'rgba(148,160,176,0.85)',
                        background: isActive ? 'rgba(90,200,208,0.12)' : 'transparent',
                        borderRadius: 5, padding: '5px 8px', lineHeight: 1.55,
                        cursor: 'pointer', transition: 'background .1s',
                        border: isActive ? '1px solid rgba(90,200,208,0.2)' : '1px solid transparent',
                      }}>
                      <span style={{ color: '#5ac8d0', fontWeight: 700, marginRight: 5 }}>p.{r.page}</span>
                      {r.snippet}
                    </div>
                  );
                })}
              </div>
              {results.length > 50 && (
                <div style={{ fontSize: 9.5, color: 'rgba(100,112,128,0.7)', textAlign: 'center', paddingTop: 6, fontFamily: "'DM Sans',sans-serif" }}>
                  Showing 50 of {results.length} results
                </div>
              )}
            </>
          )}

          {!loading && query.trim() && results.length === 0 && (
            <div style={{ fontSize: 11, color: 'rgba(148,160,176,0.6)', padding: '8px 2px 2px', fontFamily: "'DM Sans',sans-serif" }}>
              No matches found
            </div>
          )}
        </div>
      );
    }

    // ── Universal TOC sidebar — works for PDF (page nav) and text (chunk nav) ──
    function TocSidebar({ linkToken, sessionId, currentPage, docType, onNavigate, onClose }) {
      const [toc, setToc] = useState([]);
      const [loading, setLoading] = useState(true);
      const [error, setError] = useState(false);
      // DOCX/DOC use the image pipeline — navigate by page, same as PDF
      const isImageDoc = docType === 'pdf' || docType === 'docx' || docType === 'doc';

      useEffect(() => {
        if (!linkToken || !sessionId) return;
        setLoading(true);
        setError(false);
        window.SecureDocAPI.getToc(linkToken, sessionId)
          .then(data => {
            setToc(data.toc || []);
            if (!data.supported) setError(true);
          })
          .catch(() => { setToc([]); setError(true); })
          .finally(() => setLoading(false));
      }, [linkToken, sessionId]);

      // Resolve the navigation target for a TOC entry
      const navTarget = (entry) => isImageDoc
        ? (entry.page != null ? entry.page : null)
        : (entry.chunk != null ? entry.chunk : null);

      // Determine if this entry is the "current" one
      const isCurrent = (entry) => navTarget(entry) === currentPage;

      // Confidence badge color
      const confidenceColor = (c) => c >= 0.9 ? C.teal2 : c >= 0.75 ? '#e0a030' : C.textDim;

      return (
        <div style={{
          width: 240, background: C.surfaceAlt, borderRight: `1px solid ${C.border}`,
          display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0
        }}>
          <div style={{
            padding: '10px 12px', borderBottom: `1px solid ${C.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0
          }}>
            <span style={{ ...mono, fontSize: 10, color: C.teal2, letterSpacing: '0.6px' }}>
              TABLE OF CONTENTS
            </span>
            <button
              onClick={onClose}
              aria-label="Close TOC"
              style={{ background: 'none', border: 'none', color: C.textMuted, cursor: 'pointer', fontSize: 14, padding: '2px 4px' }}>
              ✕
            </button>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '6px 0' }}>
            {loading ? (
              <div style={{ padding: '16px 12px', color: C.textMuted, fontSize: 11 }}>Loading…</div>
            ) : error && toc.length === 0 ? (
              <div style={{ padding: '16px 12px', color: C.textDim, fontSize: 11 }}>
                {isImageDoc ? 'No bookmarks found.' : 'No headings found.'}
              </div>
            ) : toc.length === 0 ? (
              <div style={{ padding: '16px 12px', color: C.textDim, fontSize: 11 }}>No headings found</div>
            ) : toc.map((entry, i) => {
              const target = navTarget(entry);
              const active = isCurrent(entry);
              const indent = 12 + (entry.level - 1) * 10;
              return (
                <div
                  key={entry.id || i}
                  role="button"
                  tabIndex={0}
                  aria-label={`Go to: ${entry.title}`}
                  onClick={() => target != null && onNavigate(target)}
                  onKeyDown={e => e.key === 'Enter' && target != null && onNavigate(target)}
                  style={{
                    padding: `5px ${indent}px 5px ${indent}px`,
                    cursor: target != null ? 'pointer' : 'default',
                    fontSize: 11, lineHeight: 1.45,
                    color: active ? C.teal1 : C.textSecondary,
                    background: active ? C.accentBg : 'transparent',
                    borderLeft: active ? `2px solid ${C.teal2}` : '2px solid transparent',
                    transition: 'all .1s',
                    fontWeight: entry.level <= 2 ? 600 : 400,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    display: 'flex', alignItems: 'center', gap: 4,
                  }}
                  onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(90,200,208,0.05)'; }}
                  onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
                  title={entry.title}>
                  {entry.level > 1 && (
                    <span style={{ color: C.textDim, flexShrink: 0, fontSize: 9 }}>
                      {'›'.repeat(entry.level - 1)}
                    </span>
                  )}
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', flex: 1 }}>
                    {entry.title}
                  </span>
                  {isImageDoc && entry.page != null && (
                    <span style={{ color: C.textDim, fontSize: 9, flexShrink: 0, marginLeft: 4 }}>
                      {entry.page}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          {!loading && toc.length > 0 && (
            <div style={{ padding: '6px 12px', borderTop: `1px solid ${C.border}`, fontSize: 9, color: C.textDim }}>
              {toc.length} section{toc.length !== 1 ? 's' : ''}
              {isImageDoc ? ' · click to jump' : ' · click to jump to chunk'}
            </div>
          )}
        </div>
      );
    }

    // ── Thumbnail fetch semaphore ──────────────────────────────────────────────
    // Without throttling, the sidebar mounts all PAGE_COUNT PageThumb components
    // simultaneously the moment a session is established.  Each sets an <img>
    // src, firing every thumbnail request at once.  For a 60-page document that
    // is 60 simultaneous HTTP requests — even with the browser's 6-conn/domain
    // limit that is 10 sequential rounds that hammer the backend connection pool.
    //
    // The semaphore limits how many thumbnail fetches are in-flight at once.
    // We use a hidden Image preloader so the queue slot is released only after
    // the browser has fully loaded (or errored on) the image, not just when the
    // HTTP request fires.  This prevents the queue from draining faster than the
    // backend can serve responses.
    const _THUMB_CONCURRENCY = 6;
    const _thumbQueue = (() => {
      let running = 0;
      const pending = [];
      function drain() {
        while (running < _THUMB_CONCURRENCY && pending.length > 0) {
          const { resolve } = pending.shift();
          running++;
          resolve(() => { running--; drain(); });
        }
      }
      return { acquire: () => new Promise(resolve => { pending.push({ resolve }); drain(); }) };
    })();

    function PageThumb({ p, active, onClick, token, sessionId, docReady }) {
      const [hov, setHov] = useState(false);
      const [thumbSrc, setThumbSrc] = useState(null);
      const [thumbError, setThumbError] = useState(false);
      const containerRef = useRef(null);

      // Phase 7: IntersectionObserver lazy loading.
      // Thumbnails only enter the semaphore queue when they are scrolled into
      // the visible area of the sidebar — prevents loading 500 thumbnails at
      // once for large documents where most pages are off-screen.
      React.useEffect(() => {
        if (!token || !sessionId || !docReady) return;
        let cancelled = false;
        let observer = null;

        const startLoad = () => {
          if (cancelled || thumbSrc) return;
          setThumbError(false);

          _thumbQueue.acquire().then(release => {
            if (cancelled) { release(); return; }
            // Use fetch + blob so X-Session-ID header is sent — keeps session_id
            // out of URLs, access logs, and the browser's image request history.
            const url = window.SecureDocAPI.getThumbUrl(token, p);
            fetch(url, { headers: window.SecureDocAPI.sessionHeaders(sessionId) })
              .then(r => r.ok ? r.blob() : Promise.reject())
              .then(blob => {
                if (!cancelled) setThumbSrc(URL.createObjectURL(blob));
                release();
              })
              .catch(() => { if (!cancelled) setThumbError(true); release(); });
          }).catch(() => {});
        };

        if (typeof IntersectionObserver !== 'undefined' && containerRef.current) {
          observer = new IntersectionObserver(
            entries => { if (entries[0].isIntersecting) { startLoad(); observer.disconnect(); } },
            { rootMargin: '200px' }  // start loading 200px before entering viewport
          );
          observer.observe(containerRef.current);
        } else {
          // Fallback for environments without IntersectionObserver
          startLoad();
        }

        return () => {
          cancelled = true;
          if (observer) observer.disconnect();
        };
      }, [token, sessionId, p, docReady]);

      const showImg = thumbSrc && !thumbError;

      return (
        <div ref={containerRef} onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
          style={{
            width: '100%', aspectRatio: '8.5/11', background: C.surface2,
            border: `1px solid ${active ? C.teal2 : hov ? C.borderMed : C.border}`,
            borderRadius: 4, cursor: 'pointer', position: 'relative', overflow: 'hidden',
            transition: 'border-color .1s', flexShrink: 0
          }}>
          {showImg ? (
            <img
              src={thumbSrc}
              draggable={false}
              onError={() => setThumbError(true)}
              style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', pointerEvents: 'none' }}
              alt={`Page ${p}`}
            />
          ) : (
            <div style={{ position: 'absolute', inset: '5px 4px', display: 'flex', flexDirection: 'column', gap: 2 }}>
              {[65, 80, 55, 75, 60, 50, 70, 58, 48].map((w, i) => (
                <div key={i} style={{
                  height: i === 0 ? 3 : 1.5, width: `${w + (p * 7 + i * 3) % 20}%`,
                  background: active ? 'rgba(90,200,208,0.3)' : 'rgba(176,196,200,0.15)',
                  borderRadius: 1
                }} />
              ))}
            </div>
          )}
          <div style={{
            ...mono, fontSize: 7, color: active ? C.teal2 : C.textDim,
            position: 'absolute', bottom: 2, right: 3
          }}>{p}</div>
        </div>
      );
    }

    function MockPage({ page, docId }) {
      const seed = page * 137;
      const lines = Array.from({ length: 20 + (seed % 5) }, (_, i) => ({
        w: 55 + (seed * (i + 1) * 7) % 38,
        indent: i % 8 === 0 ? 0 : (seed * i) % 6,
        h: i === 0 || i === 9 ? 4 : i % 4 === 0 ? 1.5 : 1.5,
        isHead: i === 0 || i === 9,
      }));
      return (
        <div style={{
          width: '100%', height: '100%', background: '#F2EFE9',
          padding: '9% 11%', display: 'flex', flexDirection: 'column', gap: 0
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            marginBottom: '5%', paddingBottom: '2.5%', borderBottom: '1px solid rgba(0,0,0,0.1)'
          }}>
            <div style={{ width: '28%', height: 7, background: 'rgba(0,0,0,0.18)', borderRadius: 1 }} />
            <div style={{ width: '18%', height: 5, background: 'rgba(0,0,0,0.08)', borderRadius: 1 }} />
          </div>
          {lines.map((l, i) => (
            <div key={i} style={{
              marginLeft: `${l.indent}%`, width: `${l.w}%`,
              height: l.isHead ? 5 : l.h,
              background: l.isHead ? 'rgba(0,0,0,0.22)' : 'rgba(0,0,0,0.1)',
              borderRadius: 1, marginBottom: l.isHead ? 5 : 4
            }} />
          ))}
          <div style={{
            marginTop: 'auto', paddingTop: '2.5%', borderTop: '1px solid rgba(0,0,0,0.07)',
            display: 'flex', justifyContent: 'space-between'
          }}>
            <div style={{ ...mono, fontSize: 7, color: 'rgba(0,0,0,0.25)' }}>{docId}</div>
            <div style={{ fontSize: 7, color: 'rgba(0,0,0,0.2)', fontFamily: "'DM Mono',monospace" }}>
              Page {page} of {PAGE_COUNT}
            </div>
          </div>
        </div>
      );
    }

    function WatermarkOverlay({ docId }) {
      return (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', transform: 'rotate(-35deg)', pointerEvents: 'none'
        }}>
          <div style={{
            ...mono, fontSize: 16, fontWeight: 700, letterSpacing: '3px',
            color: 'rgba(58,138,144,0.14)', textTransform: 'uppercase', whiteSpace: 'nowrap',
            userSelect: 'none', textAlign: 'center', lineHeight: 2.2
          }}>
            CONFIDENTIAL<br />
            <span style={{ fontSize: 9, letterSpacing: '2px' }}>{docId} · TRACKED</span>
          </div>
        </div>
      );
    }

    function ViewerInfoPanel({ doc, docId, page, session, pageCount }) {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <SectionLabel>Document Info</SectionLabel>
            <div style={{ marginTop: 8, fontSize: 12, fontWeight: 600, color: C.textPrimary, lineHeight: 1.5 }}>
              {doc?.name || session?.document_filename || 'Q4 Financial Report.pdf'}
            </div>
            <div style={{ ...mono, fontSize: 9, color: C.textMuted, marginTop: 3 }}>{docId || session?.document_id?.slice(0, 8)}</div>
            {doc && (
              <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                <RiskBadge level={doc.risk || 'HIGH'} />
                <StatusDot status={doc.status || 'active'} />
              </div>
            )}
          </div>
          <Divider />
          <div>
            <SectionLabel>Active Restrictions</SectionLabel>
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
              {[
                { label: 'Download', ok: !!session?.permissions?.can_download },
                { label: 'Print', ok: !!session?.permissions?.can_print },
                { label: 'Copy text', ok: !!session?.permissions?.can_copy },
                { label: 'Watermark', ok: !!session?.permissions?.watermark_enabled },
                { label: 'View tracking', ok: true },
                { label: 'Expiry', ok: !!session?.expires_at },
              ].map(r => (
                <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: r.ok ? C.success : C.error, width: 10 }}>
                    {r.ok ? '✓' : '✕'}
                  </span>
                  <span style={{ fontSize: 11, color: r.ok ? C.textSecondary : C.textMuted }}>{r.label}</span>
                </div>
              ))}
            </div>
          </div>
          <Divider />
          <div>
            <SectionLabel>Session</SectionLabel>
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 5 }}>
              {[
                ['Page', `${page} / ${pageCount || 1}`],
                ['Viewer', '—'],
                ['Session', session?.session_id?.slice(0, 8) || '—'],
                ['Started', session?.created_at ? new Date(session.created_at).toISOString().slice(11, 16) + ' UTC' : '—'],
              ].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 10, color: C.textMuted }}>{k}</span>
                  <span style={{ ...mono, fontSize: 10, color: C.textSecondary }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }

    /* ══════════════════════════════════════════════════════════════
       SCREEN 3 — ACCESS CONTROL
    ══════════════════════════════════════════════════════════════ */
    function AccessScreen({ doc, onSelectDoc }) {
      const toast = useToast();
      const [tab, setTab] = useState('policy');
      const [links, setLinks] = useState([]);
      const [linksLoading, setLinksLoading] = useState(true);
      const [creating, setCreating] = useState(false);
      const [revokeModal, setRevokeModal] = useState(false);
      const [revoking, setRevoking] = useState(null);
      const [linkCopied, setLinkCopied] = useState(null);
      const [saved, setSaved] = useState(false);
      // Policy form
      const [password, setPassword] = useState('');
      const [showPass, setShowPass] = useState(false);
      const [expiry, setExpiry] = useState('');
      const [maxViews, setMaxViews] = useState('');
      const [maxConcurrentSessions, setMaxConcurrentSessions] = useState('');
      const [allowedEmails, setAllowedEmails] = useState('');
      const [allowedDomains, setAllowedDomains] = useState('');
      const [ipAllowlist, setIpAllowlist] = useState('');
      const [label_txt, setLabel] = useState('');
      const [permissions, setPermissions] = useState({
        can_download: false,
        can_print: false,
        can_copy: false,
        can_right_click: false,
        watermark_enabled: true,
      });

      const docName = doc?.filename || doc?.name || 'Document';
      const docId = doc?.id || '';

      const fetchLinks = useCallback(async () => {
        if (!docId) { setLinksLoading(false); return; }
        try {
          const data = await window.SecureDocAPI.getLinks(docId);
          setLinks(data.links || []);
        } catch (e) { toast(e.detail || 'Failed to load links', 'error'); }
        finally { setLinksLoading(false); }
      }, [docId]);

      useEffect(() => { fetchLinks(); }, [fetchLinks]);

      const activeLinks = links.filter(l => !l.revoked_at && (!l.expires_at || new Date(l.expires_at) > new Date()));

      const handleSave = async () => {
        setCreating(true);
        try {
          const payload = { document_id: docId };
          if (label_txt) payload.label = label_txt;
          if (password) payload.password = password;
          if (maxViews) payload.max_views = parseInt(maxViews);
          if (maxConcurrentSessions) payload.max_concurrent_sessions = parseInt(maxConcurrentSessions);
          if (expiry) payload.expires_at = new Date(expiry + 'T23:59:59').toISOString();
          if (allowedEmails) payload.allowed_emails = allowedEmails.split('\n').map(e => e.trim()).filter(Boolean);
          if (allowedDomains) payload.allowed_domains = allowedDomains.split(',').map(d => d.trim()).filter(Boolean);
          if (ipAllowlist) payload.ip_allowlist = ipAllowlist.split(',').map(i => i.trim()).filter(Boolean);
          payload.permissions = permissions;
          await window.SecureDocAPI.createLink(payload);
          setSaved(true); setTimeout(() => setSaved(false), 2500);
          toast('Access policy saved — new link created', 'success');
          await fetchLinks(); setTab('link');
        } catch (e) { toast(e.detail || 'Failed to create link', 'error'); }
        finally { setCreating(false); }
      };

      const handleRevoke = async () => {
        setRevokeModal(false);
        for (const l of activeLinks) { try { await window.SecureDocAPI.revokeLink(l.id); } catch { } }
        toast('All access revoked. Share links are now invalid.', 'error');
        await fetchLinks();
      };

      const handleCopy = (text, lbl) => {
        try { navigator.clipboard.writeText(text); } catch { }
        setLinkCopied(text);
        setTimeout(() => setLinkCopied(null), 2200);
        toast(`${lbl} copied to clipboard`, 'success');
      };

      const TABS = [
        { id: 'policy', label: 'Policy' },
        { id: 'link', label: 'Share Link' },
        { id: 'log', label: 'Access Log' },
      ];

      // No document selected — show inline picker so user stays on this tab.
      if (!docId) {
        return (
          <div data-testid="access-screen" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Header screen="access" />
            <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
              <DocumentPicker onSelect={(d) => { if (onSelectDoc) onSelectDoc(d); }} />
            </div>
          </div>
        );
      }

      return (
        <div data-testid="access-screen" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
          <Header screen="access" breadcrumb={docName.length > 32 ? docName.slice(0, 32) + '…' : docName}>
            {activeLinks.length > 0
              ? <Btn variant="outline-danger" size="sm" onClick={() => setRevokeModal(true)}>✕ Revoke All Access</Btn>
              : <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: C.errorBg, border: `1px solid ${C.errorBdr}`,
                borderRadius: 6, padding: '4px 10px'
              }}>
                <StatusDot status="error" size={5} />
                <span style={{ ...mono, fontSize: 10, color: C.error, letterSpacing: '0.5px' }}>NO ACTIVE LINKS</span>
              </div>
            }
          </Header>

          <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* Document identity bar */}
            <Card style={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 38, height: 38, background: C.accentBg,
                    border: `1px solid ${C.borderMed}`, borderRadius: 8,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 15, color: C.teal2
                  }}>◫</div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: 2 }}>{docName}</div>
                    <div style={{ ...mono, fontSize: 9, color: C.textMuted }}>{docId}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <StatusDot status={activeLinks.length === 0 ? 'error' : 'active'} />
                    <span style={{ fontSize: 11, color: activeLinks.length === 0 ? C.error : C.success, fontWeight: 600 }}>
                      {activeLinks.length === 0 ? 'Revoked' : 'Active'}
                    </span>
                  </div>
                  <RiskBadge level={doc?.risk || 'HIGH'} />
                  <Chip color={C.textMuted} bg="transparent" border={C.border}>
                    {doc?.total_views ?? 0} views
                  </Chip>
                </div>
              </div>
            </Card>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 0, borderBottom: `1px solid ${C.border}`, marginBottom: -2 }}>
              {TABS.map(t => <TabBtn key={t.id} tab={t} active={tab === t.id} onClick={() => setTab(t.id)} />)}
            </div>

            {tab === 'policy' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }} className="fade-in">
                {/* Auth card */}
                <Card>
                  <SectionLabel style={{ marginBottom: 14 }}>Authentication</SectionLabel>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <Field label="Password Protection">
                      <div style={{ position: 'relative' }}>
                        <input type={showPass ? 'text' : 'password'} value={password}
                          onChange={e => setPassword(e.target.value)}
                          placeholder="Leave blank to disable" style={{ paddingRight: 52 }} />
                        <button onClick={() => setShowPass(v => !v)}
                          style={{
                            position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                            background: 'none', border: 'none', color: C.textMuted, cursor: 'pointer',
                            fontSize: 10, fontWeight: 600, letterSpacing: '0.5px', fontFamily: "'DM Mono',monospace"
                          }}>
                          {showPass ? 'HIDE' : 'SHOW'}
                        </button>
                      </div>
                    </Field>
                    <Field label="Allowed Domains" hint="Comma-separated, e.g. @acme.io">
                      <input value={allowedDomains} onChange={e => setAllowedDomains(e.target.value)} placeholder="@acme.io, @partner.com" />
                    </Field>
                    <Field label="Allowed Emails">
                      <textarea value={allowedEmails} onChange={e => setAllowedEmails(e.target.value)}
                        rows={3} style={{ fontFamily: "'DM Mono',monospace", fontSize: 11, resize: 'vertical' }} />
                    </Field>
                  </div>
                </Card>

                {/* Limits card */}
                <Card>
                  <SectionLabel style={{ marginBottom: 14 }}>Access Limits</SectionLabel>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <Field label="Expiry Date">
                      <input type="date" value={expiry} onChange={e => setExpiry(e.target.value)} />
                    </Field>
                    <Field label="Max View Count">
                      <input type="number" value={maxViews} onChange={e => setMaxViews(e.target.value)} placeholder="Unlimited" />
                    </Field>
                    <Field label="Max Concurrent Sessions">
                      <input type="number" value={maxConcurrentSessions} onChange={e => setMaxConcurrentSessions(e.target.value)} placeholder="Unlimited" min="1" />
                    </Field>
                    <Field label="IP Allowlist" hint="CIDR or exact, e.g. 10.0.0.0/24">
                      <input value={ipAllowlist} onChange={e => setIpAllowlist(e.target.value)} placeholder="10.0.0.0/24, 192.168.1.1" />
                    </Field>
                  </div>
                </Card>

                {/* Permissions */}
                <Card style={{ gridColumn: '1 / -1' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <SectionLabel style={{ marginBottom: 12 }}>Document Permissions</SectionLabel>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
                        {Object.entries({
                          can_download: 'Download',
                          can_print: 'Print',
                          can_copy: 'Copy Text',
                          can_right_click: 'Right Click',
                          watermark_enabled: 'Watermark'
                        }).map(([key, labelText]) => (
                          <div key={key} style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '8px 10px', background: 'rgba(90,200,208,0.03)',
                            border: `1px solid ${C.border}`, borderRadius: 7
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                              <span style={{ fontSize: 13, color: permissions[key] ? C.teal1 : C.textMuted }}>{permissions[key] ? '✓' : '—'}</span>
                              <span style={{ fontSize: 12, color: permissions[key] ? C.textPrimary : C.textMuted, fontWeight: 500 }}>{labelText}</span>
                            </div>
                            <Toggle enabled={permissions[key]} onChange={() => setPermissions(p => ({ ...p, [key]: !p[key] }))} />
                          </div>
                        ))}
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginLeft: 20, flexShrink: 0 }}>
                      <Btn variant="primary" onClick={handleSave} style={{ minWidth: 130 }}>
                        {saved ? '✓ Saved' : 'Save Policy'}
                      </Btn>
                      <Btn variant="secondary" onClick={() => toast('New link generated', 'success')} style={{ minWidth: 130 }}>
                        ⟳ New Link
                      </Btn>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {tab === 'link' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }} className="fade-in">
                {linksLoading ? (
                  <div style={{ padding: '24px', color: C.textMuted, fontSize: 13 }}>Loading links…</div>
                ) : links.length === 0 ? (
                  <Card><div style={{ textAlign: 'center', color: C.textMuted, fontSize: 13, padding: '12px 0' }}>No share links yet — create one in the Policy tab.</div></Card>
                ) : links.map(link => (
                  <Card key={link.id}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <StatusDot status={link.revoked_at ? 'error' : 'active'} />
                        <span style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>{link.label || 'Untitled Link'}</span>
                        {link.has_password && <Chip color={C.warning} bg={C.warningBg} border={C.warningBdr}>PASSWORD</Chip>}
                        {link.revoked_at && <Chip color={C.error} bg={C.errorBg} border={C.errorBdr}>REVOKED</Chip>}
                      </div>
                      {!link.revoked_at && (
                        <Btn variant="outline-danger" size="sm" onClick={async () => { try { await window.SecureDocAPI.revokeLink(link.id); toast('Link revoked', 'info'); await fetchLinks(); } catch (e) { toast(e.detail || 'Failed', 'error'); } }}>Revoke</Btn>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
                      <div style={{
                        flex: 1, ...mono, fontSize: 11,
                        background: C.surfaceAlt, border: `1px solid ${C.border}`, borderRadius: 7,
                        padding: '9px 12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                      }}>
                        {link.revoked_at
                          ? <span style={{ color: C.error }}>— link revoked —</span>
                          : <a href={link.share_url} target="_blank" rel="noopener noreferrer"
                               style={{ color: C.teal1, textDecoration: 'none' }}
                               onMouseEnter={e => e.target.style.textDecoration = 'underline'}
                               onMouseLeave={e => e.target.style.textDecoration = 'none'}>
                              {link.share_url}
                            </a>
                        }
                      </div>
                      <Btn variant={linkCopied === link.share_url ? 'secondary' : 'primary'} size="sm"
                        onClick={() => handleCopy(link.share_url, 'Share link')} disabled={!!link.revoked_at}>
                        {linkCopied === link.share_url ? '✓ Copied' : '⧉ Copy'}
                      </Btn>
                      {!link.revoked_at && (
                        <Btn variant="ghost" size="sm" onClick={() => window.open(link.share_url, '_blank')}
                          title="Open link in new tab">↗</Btn>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 20 }}>
                      {(() => {
                        const expiresVal = link.expires_at ? link.expires_at.slice(0, 10) : 'Never';
                        const expiringSoon = link.expires_at && !link.revoked_at &&
                          (new Date(link.expires_at) - Date.now()) < 3 * 24 * 60 * 60 * 1000;
                        return [
                          ['Views', `${link.view_count}${link.max_views ? ' / ' + link.max_views : ''}`],
                          ['Expires', expiresVal],
                          ['Created', link.created_at?.slice(0, 10) || '—'],
                        ].map(([k, v]) => (
                          <div key={k} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                            <span style={{ ...label(8) }}>{k}</span>
                            <span style={{ ...mono, fontSize: 11, color: k === 'Expires' && expiringSoon ? C.warning : C.textSecondary }}>{v}</span>
                          </div>
                        ));
                      })()}
                    </div>
                    {!link.revoked_at && (
                      <div style={{ marginTop: 12 }}>
                        <div style={{ background: C.surfaceAlt, borderRadius: 7, padding: 14, border: `1px solid ${C.border}` }}>
                          <SectionLabel style={{ marginBottom: 8 }}>Embed Code</SectionLabel>
                          <pre style={{ ...mono, fontSize: 10, color: C.textSecondary, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                            {`<iframe\n  src="${link.share_url}"\n  width="100%" height="600"\n  frameborder="0" sandbox="allow-scripts allow-same-origin">\n</iframe>`}
                          </pre>
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            )}

            {tab === 'log' && (
              <div className="fade-in">
                <AccessLog docId={docId} />
              </div>
            )}
          </div>

          {/* Revoke confirmation modal */}
          <Modal open={revokeModal} onClose={() => setRevokeModal(false)} title="Revoke All Access" width={420}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{
                background: C.errorBg, border: `1px solid ${C.errorBdr}`,
                borderRadius: 8, padding: '12px 14px', fontSize: 13, color: C.textSecondary, lineHeight: 1.6
              }}>
                <strong style={{ color: C.error }}>⚠ This action is immediate and irreversible.</strong><br />
                All active share links for <strong style={{ color: C.textPrimary }}>"{docName}"</strong> will stop working instantly. Viewers mid-session will be kicked out.
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {['All share links invalidated', 'Active sessions terminated', 'Access log preserved'].map(item => (
                  <div key={item} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12, color: C.textMuted }}>
                    <span style={{ color: C.error, fontWeight: 700 }}>✕</span> {item}
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <Btn variant="secondary" onClick={() => setRevokeModal(false)}>Cancel</Btn>
                <Btn variant="danger" onClick={handleRevoke}>Revoke All Access</Btn>
              </div>
            </div>
          </Modal>
        </div>
      );
    }

    function TabBtn({ tab, active, onClick }) {
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

    function PermRow({ perm }) {
      const [enabled, setEnabled] = useState(perm.val);
      return (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '8px 10px', background: 'rgba(90,200,208,0.03)',
          border: `1px solid ${C.border}`, borderRadius: 7
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{ fontSize: 10, color: enabled ? C.success : C.error, fontWeight: 700 }}>
              {enabled ? '✓' : '✕'}
            </span>
            <span style={{ fontSize: 11.5, color: C.textSecondary }}>{perm.label}</span>
          </div>
          <Toggle enabled={enabled} locked={perm.locked} onChange={v => setEnabled(v)} />
        </div>
      );
    }

    function AccessLog({ docId }) {
      const toast = useToast();
      const [events, setEvents] = useState([]);
      const [loading, setLoading] = useState(true);

      const fetchEvents = useCallback(() => {
        if (!docId) { setLoading(false); return; }
        setLoading(true);
        window.SecureDocAPI.getEvents(docId, 50)
          .then(data => setEvents(data.events || []))
          .catch(e => toast(e.detail || 'Failed to load events', 'error'))
          .finally(() => setLoading(false));
      }, [docId]);

      useEffect(() => { fetchEvents(); }, [fetchEvents]);

      return (
        <Card noPad>
          <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <SectionLabel>Access Log — Last 50 Events</SectionLabel>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Chip color={C.textMuted} bg="transparent" border={C.border}>{events.length} events</Chip>
              <Btn variant="ghost" size="sm" onClick={fetchEvents} style={{ fontSize: 11 }}>⟳ Refresh</Btn>
            </div>
          </div>
          {loading ? <div style={{ padding: '24px', color: C.textMuted, fontSize: 13 }}>Loading…</div> : events.length === 0 ? <div style={{ padding: '24px', textAlign: 'center', color: C.textMuted, fontSize: 13 }}>No events yet</div> : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr style={{ borderBottom: `1px solid ${C.border}` }}>
                {['Time', 'Email', 'Session', 'Event', 'Page', 'Risk'].map(h => (
                  <th key={h} style={{ ...label(9), padding: '9px 14px', textAlign: 'left', color: C.textDim }}>{h}</th>
                ))}
              </tr></thead>
              <tbody>{events.map((e, i) => {
                const isBlocked = ['print_attempt', 'copy_attempt', 'right_click_attempt', 'download_attempt'].includes(e.event_type);
                return (
                  <tr key={e.id || i} style={{ borderBottom: i === events.length - 1 ? 'none' : `1px solid ${C.border}`, background: isBlocked ? 'rgba(224,90,69,0.04)' : 'transparent' }}>
                    <td style={{ ...mono, padding: '10px 14px', fontSize: 9, color: C.textMuted }}>{e.created_at?.slice(0, 16) || '—'}</td>
                    <td style={{ ...mono, padding: '10px 14px', fontSize: 10, color: C.textSecondary }}>{e.viewer_email || '—'}</td>
                    <td style={{ ...mono, padding: '10px 14px', fontSize: 9, color: C.textMuted }}>{e.session_id?.slice(0, 8) || '—'}</td>
                    <td style={{ padding: '10px 14px' }}><span style={{ fontSize: 10, fontWeight: 600, color: isBlocked ? C.error : C.success }}>{isBlocked ? '✕ ' : ''}{e.event_type.replace(/_/g, ' ')}</span></td>
                    <td style={{ ...mono, padding: '10px 14px', fontSize: 10, color: C.textMuted }}>{e.page_number || '—'}</td>
                    <td style={{ padding: '10px 14px' }}><RiskBadge level={isBlocked ? 'HIGH' : 'LOW'} /></td>
                  </tr>
                );
              })}</tbody>
            </table>
          )}
        </Card>
      );
    }

    /* ══════════════════════════════════════════════════════════════
       SCREEN 4 — ANALYTICS
    ══════════════════════════════════════════════════════════════ */
    function AnalyticsScreen() {
      const toast = useToast();
      const [range, setRange] = useState('7d');
      const [analyticsTab, setAnalyticsTab] = useState('overview'); // 'overview' | 'documents' | 'groups'

      const [overview, setOverview] = useState(null);
      const [docStats, setDocStats] = useState([]);
      const [groupStats, setGroupStats] = useState([]);
      const [analyticsLoading, setAnalyticsLoading] = useState(true);
      const [selectedHeatmapDoc, setSelectedHeatmapDoc] = useState(null); // {id, filename}
      const [heatmapData, setHeatmapData] = useState(null);
      const [heatmapLoading, setHeatmapLoading] = useState(false);

      useEffect(() => {
        Promise.all([
          window.SecureDocAPI.getAnalyticsOverview(),
          window.SecureDocAPI.getDocumentAnalytics(),
          window.SecureDocAPI.getGroupAnalytics(),
        ])
          .then(([ov, ds, gs]) => { setOverview(ov); setDocStats(ds.documents || []); setGroupStats(gs.groups || []); })
          .catch(e => toast(e.detail || 'Failed to load analytics', 'error'))
          .finally(() => setAnalyticsLoading(false));
      }, []);

      const totalViews = overview?.total_views_today || 0;
      const activeDocs = docStats.filter(d => d.total_views > 0);
      const avgSessionSec = activeDocs.length > 0
        ? activeDocs.reduce((a, d) => a + (d.avg_time_on_page_sec || 0), 0) / activeDocs.length : 0;
      const avgSessionStr = avgSessionSec > 0
        ? `${Math.floor(avgSessionSec / 60)}m ${Math.round(avgSessionSec % 60)}s` : '—';
      const avgCompletion = activeDocs.length > 0
        ? Math.round(activeDocs.reduce((a, d) => a + (d.completion_rate_pct || 0), 0) / activeDocs.length) : 0;
      const kpis = [
        { label: 'Total Views', value: totalViews.toLocaleString(), icon: '▦' },
        { label: 'Active Links', value: (overview?.active_links || 0).toString(), icon: '◫' },
        { label: 'Avg Session', value: avgSessionStr, icon: '⏱' },
        { label: 'Blocked Attempts', value: (overview?.blocked_attempts_today || 0).toString(), icon: '⊗' },
        { label: 'Active Docs', value: activeDocs.length.toString(), icon: '◈' },
        { label: 'Completion', value: avgCompletion > 0 ? `${avgCompletion}%` : '—', icon: '⊕' },
      ];

      const topDocs = docStats.map(d => ({
        name: d.filename, views: d.total_views || 0, unique: d.unique_sessions || 0,
        avgTime: d.avg_time_on_page_sec > 0 ? `${Math.floor(d.avg_time_on_page_sec / 60)}m ${Math.round(d.avg_time_on_page_sec % 60)}s` : '—',
        risk: d.risk_score || 'LOW',
        group_name: d.group_name || null, group_color: d.group_color || null,
      }));

      return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }} className="fade-in">
          <Header screen="analytics">
            {/* Analytics tabs */}
            <div style={{ display: 'flex', gap: 2, background: C.surface2, borderRadius: 8, padding: 3 }}>
              {[['overview', 'Overview'], ['documents', 'By Document'], ['groups', 'By Group']].map(([id, label]) => (
                <button key={id} onClick={() => setAnalyticsTab(id)}
                  style={{
                    fontSize: 11, padding: '5px 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
                    background: analyticsTab === id ? C.surface : 'transparent',
                    color: analyticsTab === id ? C.teal1 : C.textMuted,
                    fontFamily: "'DM Sans',sans-serif", fontWeight: analyticsTab === id ? 600 : 400,
                    transition: 'all .12s'
                  }}>{label}</button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 3 }}>
              {analyticsTab === 'overview' && ['24h', '7d', '30d', '90d'].map(r => (
                <RangeBtn key={r} r={r} active={range === r} onClick={() => setRange(r)} />
              ))}
            </div>
            <Btn variant="secondary" size="sm" onClick={() => toast('Export started — CSV ready in a moment', 'success')}>
              ↓ Export CSV
            </Btn>
          </Header>

          <div style={{ flex: 1, overflow: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* ── BY DOCUMENT TAB ── */}
            {analyticsTab === 'documents' && (
              <>
                <Card noPad>
                  <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <SectionLabel>Per-Document Analytics</SectionLabel>
                    <Chip color={C.textMuted} bg="transparent" border={C.border}>{docStats.length} docs</Chip>
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                        {['Document', 'Group', 'Views', 'Sessions', 'Completion', 'Blocked', 'Risk', ''].map(h => (
                          <th key={h} style={{ ...label(9), padding: '8px 14px', textAlign: 'left', color: C.textDim }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {docStats.length === 0 ? (
                        <tr><td colSpan={8} style={{ padding: 24, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>No documents yet</td></tr>
                      ) : docStats.map((d, i) => {
                        const isSelected = selectedHeatmapDoc?.id === d.id;
                        return (
                          <tr key={d.id} onClick={() => {
                            if (isSelected) { setSelectedHeatmapDoc(null); setHeatmapData(null); return; }
                            setSelectedHeatmapDoc({ id: d.id, filename: d.filename });
                            setHeatmapData(null);
                            setHeatmapLoading(true);
                            window.SecureDocAPI.getPageHeatmap(d.id)
                              .then(data => setHeatmapData(data))
                              .catch(() => setHeatmapData(null))
                              .finally(() => setHeatmapLoading(false));
                          }} style={{
                            borderBottom: i === docStats.length - 1 ? 'none' : `1px solid ${C.border}`,
                            background: isSelected ? 'rgba(90,200,208,0.04)' : 'transparent',
                            cursor: 'pointer', transition: 'background .1s',
                          }}>
                            <td style={{ padding: '10px 14px', fontSize: 12, color: C.textPrimary, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.filename}</td>
                            <td style={{ padding: '10px 14px' }}>
                              {d.group_name ? (
                                <span style={{ fontSize: 9, padding: '2px 7px', borderRadius: 10, background: `${d.group_color || '#6366f1'}22`, color: d.group_color || '#6366f1', border: `1px solid ${d.group_color || '#6366f1'}44` }}>{d.group_name}</span>
                              ) : <span style={{ fontSize: 9, color: C.textDim }}>—</span>}
                            </td>
                            <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textSecondary }}>{d.total_views}</td>
                            <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{d.unique_sessions}</td>
                            <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{d.completion_rate_pct}%</td>
                            <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: d.blocked_attempts > 0 ? C.error : C.textMuted }}>{d.blocked_attempts}</td>
                            <td style={{ padding: '10px 14px' }}><RiskBadge level={d.risk_score} /></td>
                            <td style={{ padding: '10px 14px', color: C.teal2, fontSize: 10 }}>{isSelected ? '▲ Hide' : '▦ Heatmap'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </Card>

                {/* Page Heatmap panel — Features 3 & 4 */}
                {selectedHeatmapDoc && (
                  <Card style={{ padding: 0 }}>
                    <div style={{ padding: '12px 16px', borderBottom: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 13, color: '#5ac8d0' }}>▦</span>
                      <div>
                        <div style={{ fontSize: 12.5, fontWeight: 600, color: C.textPrimary }}>{selectedHeatmapDoc.filename}</div>
                        <div style={{ fontSize: 10, color: C.textDim, marginTop: 1 }}>Page engagement heatmap · click any row to drill in</div>
                      </div>
                      {heatmapData && (
                        <span style={{ marginLeft: 'auto', ...mono, fontSize: 10, color: C.textMuted }}>{heatmapData.total_views} total page views</span>
                      )}
                    </div>

                    {heatmapLoading && (
                      <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>Loading heatmap…</div>
                    )}

                    {!heatmapLoading && heatmapData && heatmapData.pages.length === 0 && (
                      <div style={{ padding: 32, textAlign: 'center', color: C.textMuted, fontSize: 12 }}>
                        No page views recorded yet for this document.
                      </div>
                    )}

                    {!heatmapLoading && heatmapData && heatmapData.pages.length > 0 && (
                      <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 5 }}>
                        {/* Top pages header */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                          <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: C.textDim }}>Most Viewed Pages</span>
                          <span style={{ ...mono, fontSize: 9, color: C.textDim }}>· {heatmapData.page_count} pages total</span>
                        </div>
                        {heatmapData.pages.slice(0, 20).map((p, i) => {
                          const maxViews = heatmapData.pages[0]?.views || 1;
                          const barPct = Math.max(2, Math.round((p.views / maxViews) * 100));
                          const heat = p.pct > 15 ? '#ff6b35' : p.pct > 8 ? '#ffd166' : '#5ac8d0';
                          return (
                            <div key={p.page} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                              <div style={{ ...mono, fontSize: 10, color: C.textMuted, width: 52, flexShrink: 0, textAlign: 'right' }}>
                                {i < 3 ? '🔥' : ''} p.{p.page}
                              </div>
                              <div style={{ flex: 1, height: 16, background: 'rgba(255,255,255,0.04)', borderRadius: 3, overflow: 'hidden' }}>
                                <div style={{
                                  width: `${barPct}%`, height: '100%',
                                  background: `linear-gradient(90deg, ${heat}aa, ${heat})`,
                                  borderRadius: 3, transition: 'width .3s ease',
                                }} />
                              </div>
                              <div style={{ ...mono, fontSize: 10, color: C.textSecondary, width: 52, flexShrink: 0 }}>
                                {p.views} view{p.views !== 1 ? 's' : ''}
                              </div>
                              <div style={{ ...mono, fontSize: 9, color: C.textDim, width: 48, flexShrink: 0 }}>
                                {p.avg_time_sec > 0 ? `${p.avg_time_sec}s avg` : ''}
                              </div>
                            </div>
                          );
                        })}
                        {heatmapData.pages.length > 20 && (
                          <div style={{ fontSize: 10, color: C.textDim, textAlign: 'center', paddingTop: 4 }}>
                            Showing top 20 of {heatmapData.pages.length} pages with views
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                )}
              </>
            )}

            {/* ── BY GROUP TAB ── */}
            {analyticsTab === 'groups' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {groupStats.length === 0 ? (
                  <Card style={{ padding: 32, textAlign: 'center' }}>
                    <div style={{ fontSize: 13, color: C.textMuted, marginBottom: 8 }}>No groups created yet</div>
                    <div style={{ fontSize: 11, color: C.textDim }}>Create groups in the Documents screen to organise your files</div>
                  </Card>
                ) : (
                  <>
                    {/* Group KPI cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
                      {groupStats.map(g => (
                        <Card key={g.group_id} style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                            <div style={{ width: 10, height: 10, borderRadius: '50%', background: g.group_color, flexShrink: 0 }} />
                            <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.group_name}</div>
                            <RiskBadge level={g.risk_score} />
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                            {[
                              { l: 'Docs', v: g.document_count },
                              { l: 'Views', v: g.total_views },
                              { l: 'Sessions', v: g.unique_sessions },
                              { l: 'Active Links', v: g.active_links },
                              { l: 'Blocked', v: g.blocked_attempts, warn: g.blocked_attempts > 0 },
                            ].map(it => (
                              <div key={it.l}>
                                <div style={{ fontSize: 8, color: C.textDim, textTransform: 'uppercase', letterSpacing: 1 }}>{it.l}</div>
                                <div style={{ ...mono, fontSize: 18, fontWeight: 700, color: it.warn ? C.error : C.textPrimary }}>{it.v}</div>
                              </div>
                            ))}
                          </div>
                        </Card>
                      ))}
                    </div>
                    {/* Group comparison table */}
                    <Card noPad>
                      <div style={{ padding: '10px 14px', borderBottom: `1px solid ${C.border}` }}>
                        <SectionLabel>Group Comparison</SectionLabel>
                      </div>
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                            {['Group', 'Docs', 'Total Views', 'Sessions', 'Active Links', 'Blocked', 'Risk'].map(h => (
                              <th key={h} style={{ ...label(9), padding: '8px 14px', textAlign: 'left', color: C.textDim }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {groupStats.map((g, i) => (
                            <tr key={g.group_id} style={{ borderBottom: i === groupStats.length - 1 ? 'none' : `1px solid ${C.border}` }}>
                              <td style={{ padding: '10px 14px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: g.group_color, flexShrink: 0 }} />
                                  <span style={{ fontSize: 12, fontWeight: 600, color: C.textPrimary }}>{g.group_name}</span>
                                </div>
                              </td>
                              <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textSecondary }}>{g.document_count}</td>
                              <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textSecondary }}>{g.total_views}</td>
                              <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{g.unique_sessions}</td>
                              <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{g.active_links}</td>
                              <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: g.blocked_attempts > 0 ? C.error : C.textMuted }}>{g.blocked_attempts}</td>
                              <td style={{ padding: '10px 14px' }}><RiskBadge level={g.risk_score} /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </Card>
                  </>
                )}
              </div>
            )}

            {/* ── OVERVIEW TAB ── */}
            {analyticsTab === 'overview' && <>

              {/* KPI row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 10 }}>
                {kpis.map(k => <KpiCard key={k.label} k={k} />)}
              </div>

              {/* Charts */}
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
                <Card>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                    <div>
                      <SectionLabel>Views Over Time</SectionLabel>
                      <div style={{ ...mono, fontSize: 9, color: C.textDim, marginTop: 3 }}>
                        Daily view count · {range}
                      </div>
                    </div>
                    <div style={{ ...mono, fontSize: 22, fontWeight: 700, letterSpacing: '-1.5px', color: C.teal1 }}>{(overview?.views_last_7_days || []).reduce((a, d) => a + d.count, 0).toLocaleString()}</div>
                  </div>
                  <SparkChart range={range} sparkData={overview?.views_last_7_days} />
                </Card>
                <Card>
                  <SectionLabel style={{ marginBottom: 14 }}>Access Outcomes</SectionLabel>
                  <DonutChart overview={overview} />
                  <Divider style={{ margin: '12px 0' }} />
                  <SectionLabel style={{ marginBottom: 8 }}>Top Documents</SectionLabel>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {(() => {
                      const top3 = [...docStats].sort((a, b) => (b.total_views || 0) - (a.total_views || 0)).slice(0, 3);
                      const topTotal = top3.reduce((s, d) => s + (d.total_views || 0), 0);
                      if (top3.length === 0) return <div style={{ fontSize: 11, color: C.textMuted }}>No views yet</div>;
                      return top3.map(d => {
                        const pct = topTotal > 0 ? Math.round((d.total_views / topTotal) * 100) : 0;
                        return (
                          <div key={d.id}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                              <span style={{ ...mono, fontSize: 10, color: C.textSecondary, overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '70%' }}>{d.filename}</span>
                              <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>{d.total_views}</span>
                            </div>
                            <div style={{ height: 3, background: 'rgba(90,200,208,0.1)', borderRadius: 2 }}>
                              <div style={{
                                height: '100%', width: `${pct}%`,
                                background: `linear-gradient(90deg, ${C.teal4}, ${C.teal1})`, borderRadius: 2
                              }} />
                            </div>
                          </div>
                        );
                      });
                    })()}
                  </div>
                </Card>
              </div>

              {/* Table + security events */}
              <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: 12 }}>
                <Card noPad>
                  <div style={{
                    padding: '10px 14px', borderBottom: `1px solid ${C.border}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                  }}>
                    <SectionLabel>Document Performance</SectionLabel>
                    <Chip color={C.textMuted} bg="transparent" border={C.border}>{topDocs.length} docs</Chip>
                  </div>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                        {['Document', 'Group', 'Views', 'Unique', 'Avg Time', 'Risk'].map(h => (
                          <th key={h} style={{ ...label(9), padding: '8px 14px', textAlign: 'left', color: C.textDim }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {topDocs.map((d, i) => <DocAnalyticsRow key={d.name} doc={d} isLast={i === topDocs.length - 1} />)}
                    </tbody>
                  </table>
                </Card>

                <Card>
                  <SectionLabel style={{ marginBottom: 10 }}>Groups at a Glance</SectionLabel>
                  {groupStats.length === 0 ? (
                    <div style={{ fontSize: 11, color: C.textMuted, padding: '8px 0' }}>No groups yet</div>
                  ) : groupStats.slice(0, 5).map(g => (
                    <div key={g.group_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 7, height: 7, borderRadius: '50%', background: g.group_color, flexShrink: 0 }} />
                        <span style={{ fontSize: 10, color: C.textSecondary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 90 }}>{g.group_name}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>{g.total_views}v</span>
                        <RiskBadge level={g.risk_score} />
                      </div>
                    </div>
                  ))}
                  <Divider style={{ margin: '12px 0' }} />
                  <SectionLabel style={{ marginBottom: 8 }}>Security Activity</SectionLabel>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: 10, color: C.textSecondary }}>Blocked today</span>
                      <span style={{ ...mono, fontSize: 10, color: overview?.blocked_attempts_today > 0 ? C.error : C.success }}>{overview?.blocked_attempts_today || 0}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: 10, color: C.textSecondary }}>Active links</span>
                      <span style={{ ...mono, fontSize: 10, color: C.teal1 }}>{overview?.active_links || 0}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: 10, color: C.textSecondary }}>Expiring soon</span>
                      <span style={{ ...mono, fontSize: 10, color: overview?.expiring_soon_count > 0 ? C.warning : C.textMuted }}>{overview?.expiring_soon_count || 0}</span>
                    </div>
                  </div>
                </Card>
              </div>
            </>}
          </div>
        </div>
      );
    }

    function KpiCard({ k }) {
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

    function RangeBtn({ r, active, onClick }) {
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

    function SparkChart({ range, sparkData }) {
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

    function DonutChart({ overview }) {
      const totalAttempts = (overview?.total_views_today || 0) + (overview?.blocked_attempts_today || 0);
      const viewedPct = totalAttempts > 0 ? Math.round((overview.total_views_today / totalAttempts) * 100) : 100;
      const blockedPct = totalAttempts > 0 ? 100 - viewedPct : 0;
      const segs = [
        { label: 'Viewed', pct: viewedPct, color: C.teal2 },
        { label: 'Blocked', pct: blockedPct, color: C.error },
      ];
      const r = 36, cx = 50, cy = 50, sw = 13, circ = 2 * Math.PI * r;
      let cum = 0;
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <svg viewBox="0 0 100 100" style={{ width: 86, height: 86, flexShrink: 0 }}>
            <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(90,200,208,0.08)" strokeWidth={sw} />
            {segs.map((s, i) => {
              const len = (s.pct / 100) * circ, gap = circ - len;
              const off = -cum * circ / 100 - circ * .25;
              cum += s.pct;
              return <circle key={i} cx={cx} cy={cy} r={r} fill="none"
                stroke={s.color} strokeWidth={sw} strokeDasharray={`${len} ${gap}`} strokeDashoffset={off} />;
            })}
            <text x={cx} y={cy - 4} textAnchor="middle" fontFamily="'DM Mono',monospace"
              fontSize="14" fontWeight="700" fill={C.teal1}>{viewedPct}%</text>
            <text x={cx} y={cy + 10} textAnchor="middle" fontFamily="'DM Mono',monospace"
              fontSize="5.5" fill={C.textDim}>success rate</text>
          </svg>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {segs.map(s => (
              <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: s.color }} />
                <span style={{ fontSize: 11, color: C.textSecondary, flex: 1 }}>{s.label}</span>
                <span style={{ ...mono, fontSize: 10, color: C.textMuted }}>{s.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    function DocAnalyticsRow({ doc, isLast }) {
      const [hov, setHov] = useState(false);
      return (
        <tr onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
          style={{
            borderBottom: isLast ? 'none' : `1px solid ${C.border}`,
            background: hov ? 'rgba(90,200,208,0.03)' : 'transparent', transition: 'background .1s'
          }}>
          <td style={{
            padding: '10px 14px', fontSize: 12, color: doc.views === 0 ? C.textMuted : C.textPrimary,
            fontWeight: doc.views > 100 ? 600 : 400, maxWidth: 180, overflow: 'hidden',
            textOverflow: 'ellipsis', whiteSpace: 'nowrap'
          }}>{doc.name}</td>
          <td style={{ padding: '10px 14px' }}>
            {doc.group_name ? (
              <span style={{ fontSize: 9, padding: '2px 7px', borderRadius: 10, background: `${doc.group_color || '#6366f1'}22`, color: doc.group_color || '#6366f1', border: `1px solid ${doc.group_color || '#6366f1'}44` }}>{doc.group_name}</span>
            ) : <span style={{ fontSize: 9, color: C.textDim }}>—</span>}
          </td>
          <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textSecondary }}>{doc.views}</td>
          <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{doc.unique}</td>
          <td style={{ ...mono, padding: '10px 14px', fontSize: 11, color: C.textMuted }}>{doc.avgTime}</td>
          <td style={{ padding: '10px 14px' }}><RiskBadge level={doc.risk} /></td>
        </tr>
      );
    }

    /* ══════════════════════════════════════════════════════════════
       ROOT APP
    ══════════════════════════════════════════════════════════════ */
    /* ─── JWT HELPER ──────────────────────────────────────────── */
    function parseJwtEmail(token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        return payload.email || '';
      } catch { return ''; }
    }

    /* ══════════════════════════════════════════════════════════════
       LOGIN SCREEN
    ══════════════════════════════════════════════════════════════ */
    function LoginScreen({ onLogin }) {
      // mode: 'login' | 'signup' | 'forgot' | 'reset'
      const [mode, setMode] = useState(() => {
        // Detect Supabase password-reset callback: hash contains access_token + type=recovery
        if (typeof window !== 'undefined') {
          const hash = window.location.hash;
          if (hash.includes('type=recovery') && hash.includes('access_token=')) {
            return 'reset';
          }
        }
        return 'login';
      });
      const [resetToken] = useState(() => {
        if (typeof window === 'undefined') return '';
        const params = new URLSearchParams(window.location.hash.replace('#', ''));
        return params.get('access_token') || '';
      });
      const [email, setEmail] = useState('');
      const [password, setPassword] = useState('');
      const [newPassword, setNewPassword] = useState('');
      const [loading, setLoading] = useState(false);
      const [error, setError] = useState('');
      const [info, setInfo] = useState('');

      const handleSubmit = async (e) => {
        e && e.preventDefault();
        setLoading(true);
        setError('');
        setInfo('');
        try {
          if (mode === 'forgot') {
            if (!email.trim()) { setError('Email is required.'); setLoading(false); return; }
            await window.SecureDocAPI.forgotPassword(email.trim());
            setInfo('Password reset email sent — check your inbox. The link expires in 1 hour.');
            setLoading(false);
            return;
          }
          if (mode === 'reset') {
            if (!newPassword || newPassword.length < 6) { setError('Password must be at least 6 characters.'); setLoading(false); return; }
            await window.SecureDocAPI.resetPassword(resetToken, newPassword);
            setInfo('Password updated successfully. You can now sign in.');
            setMode('login');
            setLoading(false);
            return;
          }
          if (!email.trim() || !password) { setError('Email and password are required.'); setLoading(false); return; }
          const token = await window.SecureDocAPI.auth(mode, email.trim(), password);
          localStorage.setItem('securedoc_token', token);
          onLogin(token);
        } catch (err) {
          const msg = err.message || 'Authentication failed.';
          if (msg.toLowerCase().includes('confirm')) { setInfo(msg); }
          else { setError(msg); }
        } finally {
          setLoading(false);
        }
      };

      const inputStyle = {
        background: 'rgba(90,200,208,0.04)', border: `1px solid ${C.borderMed}`,
        borderRadius: 8, color: C.textPrimary, fontFamily: "'DM Sans', sans-serif",
        fontSize: 13, padding: '10px 13px', outline: 'none', width: '100%',
        transition: 'border-color .15s',
      };

      return (
        <div style={{
          height: '100vh', width: '100vw', background: C.bg,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          animation: 'fadeIn .25s ease'
        }}>
          <div className="fade-up" style={{
            width: 360, background: C.surface, border: `1px solid ${C.borderMed}`,
            borderRadius: 14, padding: '32px 28px',
            boxShadow: '0 24px 80px rgba(0,0,0,0.55)'
          }}>
            {/* Logo */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                background: `linear-gradient(135deg, ${C.teal1} 0%, ${C.teal3} 100%)`,
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <svg width="15" height="15" viewBox="0 0 14 14" fill="none">
                  <rect x="2" y="1" width="8" height="10" rx="1.5" stroke="#080B0C" strokeWidth="1.5" />
                  <line x1="4" y1="4.5" x2="8" y2="4.5" stroke="#080B0C" strokeWidth="1.2" strokeLinecap="round" />
                  <line x1="4" y1="6.5" x2="8" y2="6.5" stroke="#080B0C" strokeWidth="1.2" strokeLinecap="round" />
                  <line x1="4" y1="8.5" x2="6.5" y2="8.5" stroke="#080B0C" strokeWidth="1.2" strokeLinecap="round" />
                  <circle cx="10" cy="10.5" r="2.5" fill="#080B0C" stroke="#080B0C" strokeWidth="0.5" />
                  <path d="M9 10.5l.8.8 1.6-1.6" stroke={C.teal1} strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.4px', color: C.textPrimary, lineHeight: 1.2 }}>SecureDoc</div>
                <div style={{ fontSize: 9, color: C.teal3, letterSpacing: '0.5px', fontWeight: 500 }}>Document Security</div>
              </div>
            </div>

            {/* Mode toggle — hidden for forgot/reset flows */}
            {(mode === 'login' || mode === 'signup') && (
              <div style={{
                display: 'flex', background: C.surfaceAlt, borderRadius: 8,
                padding: 3, marginBottom: 24, gap: 2
              }}>
                {[['login', 'Sign In'], ['signup', 'Sign Up']].map(([m, lbl]) => (
                  <button key={m} type="button" onClick={() => { setMode(m); setError(''); setInfo(''); }}
                    style={{
                      flex: 1, padding: '7px 0', border: `1px solid ${mode === m ? C.borderMed : 'transparent'}`,
                      borderRadius: 6, cursor: 'pointer', fontFamily: "'DM Sans', sans-serif",
                      fontSize: 12, fontWeight: mode === m ? 600 : 400,
                      background: mode === m ? C.accentBg : 'transparent',
                      color: mode === m ? C.teal1 : C.textMuted,
                      transition: 'all .15s'
                    }}>
                    {lbl}
                  </button>
                ))}
              </div>
            )}
            {(mode === 'forgot' || mode === 'reset') && (
              <div style={{ marginBottom: 20, fontSize: 13, color: C.textMuted }}>
                {mode === 'forgot' ? 'Reset your password' : 'Set a new password'}
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Email field — shown for login, signup, forgot */}
              {mode !== 'reset' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <label style={{ fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: C.textMuted, fontWeight: 600 }}>
                    Email
                  </label>
                  <input
                    type="email" value={email} autoFocus={mode !== 'reset'} autoComplete="email"
                    onChange={e => setEmail(e.target.value)}
                    onFocus={e => e.target.style.borderColor = C.borderActive}
                    onBlur={e => e.target.style.borderColor = C.borderMed}
                    placeholder="you@example.com" style={inputStyle} />
                </div>
              )}

              {/* Password field — shown for login and signup only */}
              {(mode === 'login' || mode === 'signup') && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={{ fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: C.textMuted, fontWeight: 600 }}>
                      Password
                    </label>
                    {mode === 'login' && (
                      <button type="button"
                        onClick={() => { setMode('forgot'); setError(''); setInfo(''); }}
                        style={{ fontSize: 10, color: C.teal3, background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontFamily: "'DM Sans', sans-serif" }}>
                        Forgot password?
                      </button>
                    )}
                  </div>
                  <input
                    type="password" value={password} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                    onChange={e => setPassword(e.target.value)}
                    onFocus={e => e.target.style.borderColor = C.borderActive}
                    onBlur={e => e.target.style.borderColor = C.borderMed}
                    placeholder="••••••••" style={inputStyle} />
                </div>
              )}

              {/* New password field — shown for reset flow only */}
              {mode === 'reset' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <label style={{ fontSize: 10, letterSpacing: '0.8px', textTransform: 'uppercase', color: C.textMuted, fontWeight: 600 }}>
                    New Password
                  </label>
                  <input
                    type="password" value={newPassword} autoFocus autoComplete="new-password"
                    onChange={e => setNewPassword(e.target.value)}
                    onFocus={e => e.target.style.borderColor = C.borderActive}
                    onBlur={e => e.target.style.borderColor = C.borderMed}
                    placeholder="At least 6 characters" style={inputStyle} />
                </div>
              )}

              {error && (
                <div style={{
                  fontSize: 12, color: C.error, background: C.errorBg,
                  border: `1px solid ${C.errorBdr}`, borderRadius: 7, padding: '9px 12px', lineHeight: 1.5
                }}>{error}</div>
              )}

              {info && (
                <div style={{
                  fontSize: 12, color: C.teal1, background: C.infoBg,
                  border: `1px solid ${C.infoBdr}`, borderRadius: 7, padding: '9px 12px', lineHeight: 1.5
                }}>
                  {info}
                  {mode === 'signup' && (
                    <div style={{ marginTop: 6, color: C.teal3, fontSize: 11 }}>
                      Check your <strong>spam / junk folder</strong> if the email doesn't arrive within 2 minutes.
                    </div>
                  )}
                </div>
              )}

              <button type="submit" disabled={loading}
                style={{
                  width: '100%', padding: '11px 0', border: 'none', borderRadius: 8,
                  background: loading ? C.teal3 : C.teal2, color: '#080B0C',
                  fontFamily: "'DM Sans', sans-serif", fontSize: 13, fontWeight: 700,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  transition: 'background .15s',
                  boxShadow: loading ? 'none' : '0 0 20px rgba(90,200,208,0.25)'
                }}
                onMouseEnter={e => !loading && (e.target.style.background = C.teal1)}
                onMouseLeave={e => !loading && (e.target.style.background = C.teal2)}>
                {loading ? 'Please wait…'
                  : mode === 'login' ? 'Sign In'
                  : mode === 'signup' ? 'Create Account'
                  : mode === 'forgot' ? 'Send Reset Email'
                  : 'Set New Password'}
              </button>

              {(mode === 'forgot') && (
                <button type="button" onClick={() => { setMode('login'); setError(''); setInfo(''); }}
                  style={{ fontSize: 11, color: C.textMuted, background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontFamily: "'DM Sans', sans-serif", textAlign: 'center' }}>
                  ← Back to Sign In
                </button>
              )}
            </form>
          </div>
        </div>
      );
    }

    /* ══════════════════════════════════════════════════════════════
       BILLING SCREEN
    ══════════════════════════════════════════════════════════════ */
    function BillingScreen({ onPlanChange }) {
      const [billing, setBilling] = useState(null);
      const [loading, setLoading] = useState(true);
      const [actionLoading, setActionLoading] = useState('');
      const [error, setError] = useState('');

      useEffect(() => {
        async function load() {
          try {
            const r = await fetch(`${window.SecureDocAPI?.apiBase || ''}/api/billing/status`, {
              headers: { ...authHeaders() },
            });
            if (r.ok) {
              const data = await r.json();
              setBilling(data);
              if (onPlanChange) onPlanChange(data.plan || 'free');
            }
          } catch (_) {}
          finally { setLoading(false); }
        }
        load();
      }, []);

      // Helper to get auth headers without importing
      function authHeaders() {
        const token = localStorage.getItem('securedoc_token');
        return token ? { 'Authorization': `Bearer ${token}` } : {};
      }

      async function handleUpgrade() {
        setActionLoading('upgrade');
        setError('');
        try {
          const r = await fetch(`${window.SecureDocAPI?.apiBase || ''}/api/billing/checkout`, {
            method: 'POST',
            headers: { ...authHeaders() },
          });
          if (r.status === 503) {
            setError('Billing is not configured on this server.');
            return;
          }
          if (!r.ok) {
            const d = await r.json();
            setError(d.detail || 'Failed to start checkout.');
            return;
          }
          const { url } = await r.json();
          window.location.href = url;
        } catch (e) {
          setError('Network error. Please try again.');
        } finally {
          setActionLoading('');
        }
      }

      async function handleManage() {
        setActionLoading('manage');
        setError('');
        try {
          const r = await fetch(`${window.SecureDocAPI?.apiBase || ''}/api/billing/portal`, {
            method: 'POST',
            headers: { ...authHeaders() },
          });
          if (!r.ok) {
            const d = await r.json();
            setError(d.detail || 'Failed to open billing portal.');
            return;
          }
          const { url } = await r.json();
          window.open(url, '_blank');
        } catch (e) {
          setError('Network error. Please try again.');
        } finally {
          setActionLoading('');
        }
      }

      const isPro = billing?.plan === 'pro';
      const billingEnabled = billing?.billing_enabled !== false;

      return (
        <div style={{ flex: 1, overflow: 'auto', padding: '28px 32px', maxWidth: 640 }}>
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 18, fontWeight: 700, color: C.textPrimary, marginBottom: 4 }}>Billing & Plan</div>
            <div style={{ fontSize: 12, color: C.textMuted }}>Manage your subscription and usage.</div>
          </div>

          {loading ? (
            <div style={{ color: C.textMuted, fontSize: 13 }}>Loading billing status…</div>
          ) : (
            <>
              {/* Current plan card */}
              <div style={{
                background: C.surface, border: `1px solid ${isPro ? C.borderMed : C.border}`,
                borderRadius: 12, padding: '20px 22px', marginBottom: 16,
                boxShadow: isPro ? `0 0 24px rgba(90,200,208,0.08)` : 'none',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div>
                    <div style={{ fontSize: 11, color: C.textDim, letterSpacing: '0.8px', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>Current Plan</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 22, fontWeight: 700, color: C.textPrimary }}>{isPro ? 'Pro' : 'Free'}</span>
                      {isPro && (
                        <span style={{
                          fontSize: 9, fontWeight: 700, letterSpacing: '0.8px',
                          background: `linear-gradient(135deg, ${C.teal1}, ${C.teal3})`,
                          color: '#080B0C', padding: '2px 7px', borderRadius: 4,
                        }}>ACTIVE</span>
                      )}
                    </div>
                  </div>
                  {billing?.subscription_status && billing.subscription_status !== 'inactive' && (
                    <div style={{ fontSize: 11, color: C.textMuted, textAlign: 'right' }}>
                      <div style={{ color: billing.subscription_status === 'active' ? C.success : C.warning }}>
                        {billing.subscription_status.replace('_', ' ').toUpperCase()}
                      </div>
                      {billing.current_period_end && (
                        <div style={{ marginTop: 2 }}>
                          Renews {new Date(billing.current_period_end).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Feature list */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {[
                    { label: 'Document uploads', value: isPro ? 'Unlimited' : 'Up to 10' },
                    { label: 'Share links per document', value: 'Unlimited' },
                    { label: 'Access control & password protection', value: 'Included' },
                    { label: 'Viewer analytics', value: 'Included' },
                    { label: 'Watermarking', value: 'Included' },
                    { label: 'Priority support', value: isPro ? 'Included' : '—' },
                  ].map(({ label: lbl, value }) => (
                    <div key={lbl} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                      <span style={{ color: C.textMuted }}>{lbl}</span>
                      <span style={{ color: value === '—' ? C.textDim : C.textPrimary, fontWeight: 500 }}>{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {error && (
                <div style={{
                  fontSize: 12, color: C.error, background: C.errorBg,
                  border: `1px solid ${C.errorBdr}`, borderRadius: 7,
                  padding: '9px 12px', marginBottom: 14, lineHeight: 1.5
                }}>{error}</div>
              )}

              {!billingEnabled && (
                <div style={{
                  fontSize: 12, color: C.textMuted, background: 'rgba(255,255,255,0.03)',
                  border: `1px solid ${C.border}`, borderRadius: 7,
                  padding: '9px 12px', marginBottom: 14, lineHeight: 1.5
                }}>
                  Billing is not configured on this server. Set <code style={{ ...mono, fontSize: 11, color: C.teal2 }}>STRIPE_SECRET_KEY</code> to enable upgrades.
                </div>
              )}

              <div style={{ display: 'flex', gap: 10 }}>
                {!isPro && billingEnabled && (
                  <button
                    onClick={handleUpgrade}
                    disabled={actionLoading === 'upgrade'}
                    style={{
                      padding: '10px 20px', border: 'none', borderRadius: 8,
                      background: actionLoading === 'upgrade' ? C.teal3 : C.teal2,
                      color: '#080B0C', fontFamily: "'DM Sans', sans-serif",
                      fontSize: 13, fontWeight: 700, cursor: actionLoading === 'upgrade' ? 'not-allowed' : 'pointer',
                    }}>
                    {actionLoading === 'upgrade' ? 'Redirecting…' : 'Upgrade to Pro'}
                  </button>
                )}
                {isPro && billing?.stripe_customer_id && billingEnabled && (
                  <button
                    onClick={handleManage}
                    disabled={actionLoading === 'manage'}
                    style={{
                      padding: '10px 20px', border: `1px solid ${C.borderMed}`, borderRadius: 8,
                      background: 'transparent', color: C.teal1,
                      fontFamily: "'DM Sans', sans-serif", fontSize: 13, fontWeight: 600,
                      cursor: actionLoading === 'manage' ? 'not-allowed' : 'pointer',
                    }}>
                    {actionLoading === 'manage' ? 'Opening…' : 'Manage Subscription'}
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      );
    }

    function App() {
      const [token, setToken] = useState(() => localStorage.getItem('securedoc_token'));
      const [screen, setScreen] = useState('upload');
      const [activeDoc, setActiveDoc] = useState(null);
      const [plan, setPlan] = useState('free');

      const userEmail = token ? parseJwtEmail(token) : '';

      const handleViewDoc = doc => { setActiveDoc(doc); setScreen('viewer'); };
      const handleAccessDoc = doc => { setActiveDoc(doc); setScreen('access'); };
      const handleLogin = (newToken) => {
        setToken(newToken);
        // If redirected back from Stripe checkout, go to billing screen
        const params = new URLSearchParams(window.location.search);
        if (params.get('billing') === 'success') {
          setScreen('billing');
          window.history.replaceState({}, '', window.location.pathname);
        }
      };
      const handleLogout = () => {
        localStorage.removeItem('securedoc_token');
        setToken(null);
      };

      // On mount: if returning from Stripe, go to billing screen
      useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get('billing') === 'success' && token) {
          setScreen('billing');
          window.history.replaceState({}, '', window.location.pathname);
        }
      }, []);

      if (!window.SecureDocAPI) {
        return (
          <ToastProvider>
            <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 14, background: C.bg, color: C.textMuted }}>
              <div style={{ ...mono, fontSize: 13, color: C.error }}>api.js not found</div>
              <div style={{ fontSize: 12, color: C.textMuted, textAlign: 'center', maxWidth: 380, lineHeight: 1.7 }}>
                Ensure <span style={{ ...mono, color: C.teal2 }}>api.js</span> is in the same directory.<br />
                Serve with: <span style={{ ...mono, color: C.teal2 }}>python3 -m http.server 5500</span>
              </div>
            </div>
          </ToastProvider>
        );
      }

      // Public viewer — bypass auth entirely
      const urlParams = new URLSearchParams(window.location.search);
      const hashToken = window.location.hash.startsWith('#view/') ? window.location.hash.slice(6) : null;
      const publicToken = hashToken || urlParams.get('token');

      if (publicToken) {
        return (
          <ToastProvider>
            <div style={{ height: '100vh', width: '100vw', background: C.bg, display: 'flex', flexDirection: 'column' }}>
              <ViewerErrorBoundary>
                <ViewerScreen doc={{ id: null }} publicToken={publicToken} />
              </ViewerErrorBoundary>
            </div>
          </ToastProvider>
        );
      }

      // Not authenticated — show login
      if (!token) {
        return (
          <ToastProvider>
            <LoginScreen onLogin={handleLogin} />
          </ToastProvider>
        );
      }

      // Authenticated — normal app
      return (
        <ToastProvider>
          <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: C.bg }}>
            <Sidebar active={screen} setActive={setScreen}
              userEmail={userEmail} onLogout={handleLogout} plan={plan} />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {screen === 'upload' && <UploadScreen onViewDoc={handleViewDoc} onAccessDoc={handleAccessDoc} />}
              {screen === 'viewer' && <ViewerErrorBoundary><ViewerScreen doc={activeDoc} onSelectDoc={handleViewDoc} /></ViewerErrorBoundary>}
              {screen === 'access' && <AccessScreen doc={activeDoc} onSelectDoc={handleAccessDoc} />}
              {screen === 'analytics' && <AnalyticsScreen />}
              {screen === 'billing' && <BillingScreen onPlanChange={setPlan} />}
            </div>
          </div>
        </ToastProvider>
      );
    }

    ReactDOM.createRoot(document.getElementById('root')).render(<App />);
