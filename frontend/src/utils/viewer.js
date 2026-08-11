// Format an ISO date string as "Jan 1, 2026"; '—' for missing/null.
export function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

// Is the current page's content actually on screen and readable?
// PDF/image pages become ready when their <img> fires onLoad (imgReady);
// text/md/log documents have no <img> at all, so their equivalent signal is
// "the current chunk finished loading successfully" (V24-001 — imgReady never
// becomes true for text docs, since the image-loading effect explicitly skips
// them, which silently kept Reading Intelligence from ever starting on them).
export function isDocumentContentReady({ isTextDoc, imgReady, textLoading, textContent }) {
  if (isTextDoc) return !textLoading && !!textContent;
  return !!imgReady;
}

// Extract a human-readable message from an API error or any thrown value.
export function _errMsg(e, fallback) {
  if (!e) return fallback || 'An error occurred';
  if (typeof e === 'string') return e;
  if (e.detail) {
    if (typeof e.detail === 'string') return e.detail;
    if (Array.isArray(e.detail) && e.detail[0]?.msg) return e.detail[0].msg;
    return JSON.stringify(e.detail);
  }
  if (e.message) return e.message;
  return fallback || 'An error occurred';
}
