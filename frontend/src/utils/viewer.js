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
