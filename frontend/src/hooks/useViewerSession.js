// React hooks via UMD CDN global (no npm react package).
const { useState, useRef, useEffect } = React;
import { _errMsg } from '../utils/viewer.js';

/**
 * Manages the full session lifecycle for the document viewer:
 * link token resolution, gate probing, link validation, re-authentication
 * on 401, and all DRM event listeners (right-click, keyboard, print, blur).
 *
 * @param {object|null} doc            - Document object (doc.id used for admin links).
 * @param {string|null} publicToken    - Pre-resolved token for public viewer URLs.
 * @param {object}      [opts]
 * @param {Function}    [opts.onValidated] - Called after successful validation.
 *   ViewerScreen passes `() => _setPageRef.current?.()` to reset to page 1.
 *   Stored in a ref internally so it does not need to be stable across renders.
 * @param {Function}    [opts.toast]   - Toast notification function from useToast().
 *   ViewerScreen passes its own toast instance. Used for DRM warnings and errors.
 *   Called with optional chaining (toast?.()) so a missing value is safe.
 *
 * CRITICAL: reinitRef.current is assigned in the render body on every render,
 * NOT in a useEffect. This is intentional — the assignment must close over the
 * current session and pendingToken values. Moving it to useEffect would make it
 * one render stale, causing the wrong token to be used on 401 re-auth.
 */
export function useViewerSession(doc, publicToken, { onValidated, toast } = {}) {
  const [session, setSession] = useState(null);
  const [blurred, setBlurred] = useState(false);
  const [initializing, setInit] = useState(true);
  const [gateInfo, setGateInfo] = useState(null);
  const [gateError, setGateError] = useState(null);
  const [pendingToken, setPendingToken] = useState(null);

  const reinitRef = useRef(null);

  // Stable ref for onValidated — never in effect deps.
  const _onValidatedRef = useRef(onValidated);
  useEffect(() => { _onValidatedRef.current = onValidated; });

  const docId = doc?.id || '';

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
      _onValidatedRef.current?.();
    } catch (e) {
      const status = e._status;
      if (status === 401) {
        // Password wrong or missing — keep gate visible, show error
        setGateError(e.detail === 'Wrong password' ? 'Wrong password. Try again.' : null);
      } else if (status === 403 || status === 429) {
        // 403: domain/IP/email/concurrent denied — keep gate visible
        setGateError(_errMsg(e, 'Access denied'));
      } else if (status === 410 || status === 404) {
        // Revoked/expired/gone — clear stored session, show terminal gate
        sessionStorage.removeItem(`securedoc_sess_${token}`);
        const detail = (typeof e.detail === 'string' ? e.detail : '').toLowerCase();
        const terminalStatus = status === 404 ? 'not_found'
          : detail.includes('revoked') ? 'revoked' : 'expired';
        setGateInfo({ status: terminalStatus, requires_password: false, requires_email: false });
      } else {
        toast?.(_errMsg(e, 'Failed to open viewer'), 'error');
      }
    } finally { setInit(false); }
  };

  // Expose revalidation to loadPage (which has empty deps and can't close over doValidate directly).
  // Assigned in render body — NOT in useEffect — so it always closes over current session/pendingToken.
  reinitRef.current = async () => {
    const token = session?.link_token || pendingToken;
    if (!token) return;
    sessionStorage.removeItem(`securedoc_sess_${token}`);
    try {
      const gate = await window.SecureDocAPI.getGateRequirements(token);
      if (gate.status !== 'active' || gate.requires_password || gate.requires_email) {
        setSession(null);
        setGateInfo(gate);
        setPendingToken(token);
        setInit(false);
      } else {
        await doValidate(token, null, null);
      }
    } catch { toast?.('Session expired. Please reload the page.', 'error'); }
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
        toast?.(_errMsg(e, 'Failed to open viewer'), 'error');
        setInit(false);
      }
    })();
  }, [docId]);

  // DRM protections — right-click block, keyboard shortcuts, print lifecycle, blur overlay.
  // deps: [session] preserves current behavior exactly (listeners re-registered on session change).
  useEffect(() => {
    if (!session) return;
    const perms = session.permissions || {};

    const blockRC = e => { if (!perms.can_right_click) { e.preventDefault(); window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'right_click_attempt'); toast?.('Right-click disabled in secure viewer.', 'warning'); } };
    const blockKB = e => {
      const k = e.key?.toLowerCase(), ctrl = e.ctrlKey || e.metaKey;
      if (ctrl) {
        if (k === 'p' && !perms.can_print) { e.preventDefault(); e.stopPropagation(); window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'print_attempt'); toast?.('Action disabled in secure viewer.', 'warning'); }
        if (['a', 'c', 'x', 'u'].includes(k) && !perms.can_copy) { e.preventDefault(); e.stopPropagation(); window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'copy_attempt'); toast?.('Action disabled in secure viewer.', 'warning'); }
        if (k === 's' && !perms.can_download) { e.preventDefault(); e.stopPropagation(); window.SecureDocAPI?.logEvent(session.link_token, session.session_id, 'download_attempt'); toast?.('Action disabled in secure viewer.', 'warning'); }
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

  // Tab visibility — blur document when tab loses focus for mobile tab-switch detection.
  useEffect(() => {
    if (!session) return;
    const onVis = () => setBlurred(document.hidden);
    document.addEventListener('visibilitychange', onVis);
    return () => document.removeEventListener('visibilitychange', onVis);
  }, [session]);

  return {
    session, setSession,
    blurred,
    initializing,
    gateInfo, setGateInfo,
    gateError, setGateError,
    pendingToken, setPendingToken,
    reinitRef,
    doValidate,
  };
}
