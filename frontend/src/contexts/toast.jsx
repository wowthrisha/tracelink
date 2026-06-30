import { C } from '../constants/tokens.js';

const { createContext, useContext, useState, useCallback } = React;

export const ToastCtx = createContext(null);
export function useToast() { return useContext(ToastCtx); }

function Toast({ t }) {
  const icons  = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  const colors = { success: C.success, error: C.error, warning: C.warning, info: C.teal2 };
  const bgs    = { success: C.successBg, error: C.errorBg, warning: C.warningBg, info: C.infoBg };
  const bdrs   = { success: C.successBdr, error: C.errorBdr, warning: C.warningBdr, info: C.infoBdr };
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

export function ToastProvider({ children }) {
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
      <div role="status" aria-live="polite" aria-atomic="false" style={{
        position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
        display: 'flex', flexDirection: 'column', gap: 8, pointerEvents: 'none'
      }}>
        {toasts.map(t => <Toast key={t.id} t={t} />)}
      </div>
    </ToastCtx.Provider>
  );
}
