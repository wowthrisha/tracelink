// Extract share token and initial screen from URL — must run before React mounts.
(function () {
  var hash = window.location.hash;
  var params = new URLSearchParams(window.location.search);
  if (hash.startsWith('#view/')) {
    window.__PUBLIC_TOKEN = hash.slice(6);
    window.__INITIAL_SCREEN = 'viewer';
  } else if (params.has('token')) {
    window.__PUBLIC_TOKEN = params.get('token');
    window.__INITIAL_SCREEN = 'viewer';
  }
})();

const _apiMeta = document.querySelector('meta[name="api-base"]');
const _explicitBase = (_apiMeta && _apiMeta.content.trim()) ? _apiMeta.content.trim() : '';
// Auto-detect: when served from localhost:5500/5501 (local dev), route to backend on :8000.
// When served from the backend itself (production via Cloudflare tunnel), use empty = same-origin.
const API_BASE = _explicitBase || (() => {
  const port = window.location.port;
  if (port === '5500' || port === '5501') {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return ''; // same-origin — all /api/* calls go to the same host (Cloudflare → backend)
})();

const AUTH_TOKEN_KEY = 'securedoc_token';

function authHeaders() {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

function _clearAndReload() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  window.location.reload();
}

function _downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

window.SecureDocAPI = {

  // ── Auth ───────────────────────────────────────────────────────────────────

  async auth(mode, email, password) {
    const supabaseUrl = document.querySelector('meta[name="supabase-url"]')?.content;
    const supabaseAnon = document.querySelector('meta[name="supabase-anon-key"]')?.content;

    // ── Sign Up: use backend admin endpoint (no email confirmation required) ──
    if (mode === 'signup') {
      const base = API_BASE.replace(/\/$/, '');
      const r = await fetch(`${base}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await r.json();
      if (r.status === 503) {
        // Service role key not configured — fall back to Supabase flow with email confirmation
        return this._supabaseSignup(supabaseUrl, supabaseAnon, email, password);
      }
      if (!r.ok) {
        throw new Error(data.detail || data.message || 'Registration failed');
      }
      if (!data.access_token) {
        throw new Error('Registration succeeded but no token returned. Try signing in.');
      }
      return data.access_token;
    }

    // ── Sign In: direct Supabase password grant ──
    if (!supabaseUrl || !supabaseAnon) {
      throw new Error('Supabase not configured. Add supabase-url and supabase-anon-key meta tags.');
    }
    const r = await fetch(`${supabaseUrl}/auth/v1/token?grant_type=password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': supabaseAnon },
      body: JSON.stringify({ email, password }),
    });
    const data = await r.json();
    if (!r.ok) {
      throw new Error(data.error_description || data.msg || data.message || 'Authentication failed');
    }
    if (!data.access_token) {
      throw new Error('No access token returned. Check your credentials.');
    }
    return data.access_token;
  },

  async _supabaseSignup(supabaseUrl, supabaseAnon, email, password) {
    if (!supabaseUrl || !supabaseAnon) {
      throw new Error('Supabase not configured. Add supabase-url and supabase-anon-key meta tags.');
    }
    const r = await fetch(`${supabaseUrl}/auth/v1/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': supabaseAnon },
      body: JSON.stringify({ email, password }),
    });
    const data = await r.json();
    if (!r.ok) {
      throw new Error(data.error_description || data.msg || data.message || 'Authentication failed');
    }
    if (!data.access_token) {
      throw new Error('Account created — check your email (and spam folder) to confirm before signing in.');
    }
    return data.access_token;
  },

  async forgotPassword(email) {
    const supabaseUrl = document.querySelector('meta[name="supabase-url"]')?.content;
    const supabaseAnon = document.querySelector('meta[name="supabase-anon-key"]')?.content;
    if (!supabaseUrl || !supabaseAnon) {
      throw new Error('Supabase not configured.');
    }
    const r = await fetch(`${supabaseUrl}/auth/v1/recover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': supabaseAnon },
      body: JSON.stringify({ email }),
    });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw new Error(data.error_description || data.msg || 'Failed to send reset email');
    }
  },

  async resetPassword(accessToken, newPassword) {
    const supabaseUrl = document.querySelector('meta[name="supabase-url"]')?.content;
    const supabaseAnon = document.querySelector('meta[name="supabase-anon-key"]')?.content;
    if (!supabaseUrl || !supabaseAnon) {
      throw new Error('Supabase not configured.');
    }
    const r = await fetch(`${supabaseUrl}/auth/v1/user`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'apikey': supabaseAnon,
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ password: newPassword }),
    });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw new Error(data.error_description || data.msg || 'Password reset failed');
    }
  },

  // ── Documents ──────────────────────────────────────────────────────────────

  async uploadDocument(file, onProgress, groupId = null, retentionPolicy = 'never') {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('filename', file.name);
    if (groupId) fd.append('group_id', groupId);
    if (retentionPolicy) fd.append('retention_policy', retentionPolicy);
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE}/api/documents/upload`);
      const token = localStorage.getItem(AUTH_TOKEN_KEY);
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.upload.onprogress = e => {
        if (e.lengthComputable) onProgress(Math.round(e.loaded / e.total * 100));
      };
      xhr.onload = () => {
        if (xhr.status === 401) { _clearAndReload(); return; }
        const body = JSON.parse(xhr.response);
        xhr.status === 202 ? resolve(body) : reject(body);
      };
      xhr.onerror = () => reject({ detail: 'Network error' });
      xhr.send(fd);
    });
  },

  async getStorageDashboard(orgId = null) {
    const qs = orgId ? `?org_id=${encodeURIComponent(orgId)}` : '';
    const r = await fetch(`${API_BASE}/api/storage/dashboard${qs}`, { headers: { ...authHeaders() } });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async getStorageForecast() {
    const r = await fetch(`${API_BASE}/api/storage/forecast`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async updateRetention(docId, retentionPolicy, lifecycleState = null) {
    const body = { retention_policy: retentionPolicy };
    if (lifecycleState) body.lifecycle_state = lifecycleState;
    const r = await fetch(`${API_BASE}/api/documents/${docId}/retention`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async getDocuments() {
    const r = await fetch(`${API_BASE}/api/documents`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async pollDocumentStatus(docId) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}/status`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async reprocessDocument(docId) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}/reprocess`, {
      method: 'POST',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async extractSidecars(docId) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}/extract-sidecars`, {
      method: 'POST',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async deleteDocument(docId) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (r.status !== 204) throw await r.json();
  },

  // ── Links ──────────────────────────────────────────────────────────────────

  async createLink(payload) {
    const r = await fetch(`${API_BASE}/api/links`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async getLinks(documentId) {
    const r = await fetch(`${API_BASE}/api/links?document_id=${documentId}`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async revokeLink(linkId) {
    const r = await fetch(`${API_BASE}/api/links/${linkId}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async updateLink(linkId, patch) {
    const r = await fetch(`${API_BASE}/api/links/${linkId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(patch),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async resolveFeedback(docId, annotationId) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}/feedback/${annotationId}/resolve`, {
      method: 'PATCH',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  // ── Viewer (public — no auth) ───────────────────────────────────────────────

  async getGateRequirements(token) {
    const r = await fetch(`${API_BASE}/api/viewer/gate/${token}`);
    if (r.status === 404) {
      return { status: 'not_found', requires_password: false, requires_email: false };
    }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async validateLink(token, password = null, email = null, sessionId = null) {
    const r = await fetch(`${API_BASE}/api/viewer/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, password, email, session_id: sessionId }),
    });
    if (!r.ok) {
      const body = await r.json();
      body._status = r.status;
      throw body;
    }
    return r.json();
  },

  // Read-only reference to the resolved API base so other inline scripts can
  // construct URLs consistently without duplicating the auto-detect logic.
  apiBase: API_BASE,

  // Build the X-Session-ID header object for secure session transport.
  // Replaces query-param session_id on all viewer endpoints so the token
  // is never written into URLs, access logs, or the browser history.
  sessionHeaders(sessionId) {
    return sessionId ? { 'X-Session-ID': sessionId } : {};
  },

  getPageUrl(linkToken, pageNumber) {
    if (!linkToken) {
      console.error('[SecureDoc] getPageUrl: linkToken is missing', { linkToken, pageNumber });
    }
    // session_id is no longer in the URL — callers must add X-Session-ID header.
    const base = API_BASE.replace(/\/$/, '');
    const page = Math.max(1, parseInt(pageNumber, 10) || 1);
    return `${base}/api/viewer/page/${linkToken}/${page}`;
  },

  getThumbUrl(linkToken, pageNumber) {
    if (!linkToken) {
      console.error('[SecureDoc] getThumbUrl: linkToken is missing', { linkToken, pageNumber });
    }
    const base = API_BASE.replace(/\/$/, '');
    const page = Math.max(1, parseInt(pageNumber, 10) || 1);
    return `${base}/api/viewer/thumb/${linkToken}/${page}`;
  },

  async getToc(linkToken, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/toc/${encodeURIComponent(linkToken)}`,
      { headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async getTextChunk(linkToken, chunkNumber, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const chunk = Math.max(1, parseInt(chunkNumber, 10) || 1);
    const r = await fetch(
      `${base}/api/viewer/text/${encodeURIComponent(linkToken)}/${chunk}`,
      { headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async getDocumentLinks(linkToken, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/links/${encodeURIComponent(linkToken)}`,
      { headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) return { pages: [] };
    return r.json();
  },

  async getWordPositions(linkToken, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/words/${encodeURIComponent(linkToken)}`,
      { headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) return { pages: [] };
    return r.json();
  },

  async getPageHeatmap(documentId) {
    const params = new URLSearchParams({ document_id: documentId });
    const r = await fetch(`${API_BASE}/api/analytics/page-heatmap?${params}`, {
      headers: { ...authHeaders() },
    });
    // Never force-reload on analytics 401 — token may be absent in link-based viewer
    if (!r.ok) return null;
    return r.json();
  },

  async searchDocument(linkToken, q, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const params = new URLSearchParams({ q: q || '' });
    const r = await fetch(
      `${base}/api/viewer/search/${encodeURIComponent(linkToken)}?${params}`,
      { headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Search failed' }));
    return r.json();
  },

  async downloadDocument(linkToken, sessionId, filename) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/download/${encodeURIComponent(linkToken)}`,
      { headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Download failed' }));
    _downloadBlob(await r.blob(), filename || 'document.pdf');
  },

  logEvent(token, sessionId, eventType, pageNumber = null, metadata = {}) {
    // Fire-and-forget — public endpoint, never needs auth
    fetch(`${API_BASE}/api/analytics/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token,
        session_id: sessionId,
        event_type: eventType,
        page_number: pageNumber,
        metadata,
      }),
    }).catch(() => {});
  },

  // ── Analytics ──────────────────────────────────────────────────────────────

  async getAnalyticsOverview() {
    const r = await fetch(`${API_BASE}/api/analytics/overview`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async getDocumentAnalytics(groupId = null) {
    const params = new URLSearchParams();
    if (groupId) params.append('group_id', groupId);
    const r = await fetch(`${API_BASE}/api/analytics/documents?${params}`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async getGroupAnalytics() {
    const r = await fetch(`${API_BASE}/api/analytics/groups`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async getEvents(documentId = null, groupId = null, limit = 50, offset = 0) {
    const params = new URLSearchParams({ limit, offset });
    if (documentId) params.append('document_id', documentId);
    if (groupId) params.append('group_id', groupId);
    const r = await fetch(`${API_BASE}/api/analytics/events?${params}`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  // ── Groups ─────────────────────────────────────────────────────────────────

  async getGroups() {
    const r = await fetch(`${API_BASE}/api/groups`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async createGroup(payload) {
    const r = await fetch(`${API_BASE}/api/groups`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async updateGroup(groupId, payload) {
    const r = await fetch(`${API_BASE}/api/groups/${groupId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async deleteGroup(groupId) {
    const r = await fetch(`${API_BASE}/api/groups/${groupId}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (r.status !== 204) throw await r.json();
  },

  async assignDocumentsToGroup(groupId, documentIds) {
    const r = await fetch(`${API_BASE}/api/groups/${groupId}/documents`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ document_ids: documentIds }),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json();
    return r.json();
  },

  async removeDocumentFromGroup(groupId, documentId) {
    const r = await fetch(`${API_BASE}/api/groups/${groupId}/documents/${documentId}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (r.status !== 204) throw await r.json();
  },

  // ── Helpers ────────────────────────────────────────────────────────────────

  formatBytes(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  },

  // ── Annotations (viewer) ───────────────────────────────────────────────────

  async getAnnotations(linkToken, pageNumber, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/annotations/${encodeURIComponent(linkToken)}/${pageNumber}`,
      { headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load annotations' }));
    return r.json();
  },

  async createAnnotation(linkToken, payload, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/annotations/${encodeURIComponent(linkToken)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...this.sessionHeaders(sessionId) },
        body: JSON.stringify(payload),
      }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to create annotation' }));
    return r.json();
  },

  async updateAnnotation(linkToken, annotationId, payload, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/annotations/${encodeURIComponent(linkToken)}/${annotationId}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...this.sessionHeaders(sessionId) },
        body: JSON.stringify(payload),
      }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to update annotation' }));
    return r.json();
  },

  async deleteAnnotation(linkToken, annotationId, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/annotations/${encodeURIComponent(linkToken)}/${annotationId}`,
      { method: 'DELETE', headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to delete annotation' }));
  },

  async getBookmarks(linkToken, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/bookmarks/${encodeURIComponent(linkToken)}`,
      { headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) return { bookmarks: [] };
    return r.json();
  },

  async toggleBookmark(linkToken, pageNumber, sessionId, label = null) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/bookmarks/${encodeURIComponent(linkToken)}/${pageNumber}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...this.sessionHeaders(sessionId) },
        body: JSON.stringify({ label }),
      }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to toggle bookmark' }));
    return r.json();
  },

  async exportAnnotations(docId) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}/annotations/export`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Export failed' }));
    _downloadBlob(await r.blob(), `annotations_${docId.slice(0, 8)}.csv`);
  },

  async getDocumentAnnotations(docId, annotationType = null, resolved = null) {
    const params = new URLSearchParams();
    if (annotationType) params.set('annotation_type', annotationType);
    if (typeof resolved === 'boolean') params.set('resolved', String(resolved));
    const r = await fetch(`${API_BASE}/api/documents/${docId}/annotations?${params}`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load annotations' }));
    return r.json();
  },

  async resolveAnnotation(linkToken, annotationId, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/annotations/${encodeURIComponent(linkToken)}/${annotationId}/resolve`,
      { method: 'PATCH', headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to resolve annotation' }));
    return r.json();
  },

  async replyToAnnotation(linkToken, parentId, text, sessionId, pageNumber) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/annotations/${encodeURIComponent(linkToken)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...this.sessionHeaders(sessionId) },
        body: JSON.stringify({
          page_number: pageNumber,
          annotation_type: 'comment',
          coords: { x: 0.5, y: 0.5 },
          comment_text: text,
          parent_id: parentId,
          color: '#5ac8d0',
        }),
      }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to post reply' }));
    return r.json();
  },

  async getFeedback(docId, filters = null) {
    const params = new URLSearchParams();
    // Back-compat: a bare boolean/null was the old signature (resolved-only).
    const f = (filters !== null && typeof filters === 'object') ? filters : { resolved: filters };
    if (typeof f.resolved === 'boolean') params.set('resolved', String(f.resolved));
    if (f.search) params.set('search', f.search);
    if (f.date_from) params.set('date_from', f.date_from);
    if (f.date_to) params.set('date_to', f.date_to);
    if (f.page_number !== null && f.page_number !== undefined && !Number.isNaN(f.page_number)) params.set('page_number', String(f.page_number));
    if (f.author_role) params.set('author_role', f.author_role);
    if (f.reviewer) params.set('reviewer', f.reviewer);
    const r = await fetch(`${API_BASE}/api/documents/${docId}/feedback?${params}`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load feedback' }));
    return r.json();
  },

  async getFeedbackReviewers(docId) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}/feedback/reviewers`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load reviewers' }));
    const data = await r.json();
    return data.reviewers || [];
  },

  async replyToFeedback(docId, annotationId, commentText) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}/feedback/${annotationId}/reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ comment_text: commentText }),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to post reply' }));
    return r.json();
  },

  async exportFeedback(docId, filters = null) {
    const params = new URLSearchParams();
    const f = filters || {};
    if (typeof f.resolved === 'boolean') params.set('resolved', String(f.resolved));
    if (f.search) params.set('search', f.search);
    if (f.date_from) params.set('date_from', f.date_from);
    if (f.date_to) params.set('date_to', f.date_to);
    if (f.page_number !== null && f.page_number !== undefined && !Number.isNaN(f.page_number)) params.set('page_number', String(f.page_number));
    if (f.author_role) params.set('author_role', f.author_role);
    if (f.reviewer) params.set('reviewer', f.reviewer);
    const r = await fetch(`${API_BASE}/api/documents/${docId}/feedback/export?${params}`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Export failed' }));
    const disposition = r.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="([^"]+)"/);
    const filename = match ? match[1] : `feedback_conversations_${docId.slice(0, 8)}.csv`;
    _downloadBlob(await r.blob(), filename);
  },

  async exportReviewerActivity(docId) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}/feedback/export-reviewer-activity`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Export failed' }));
    _downloadBlob(await r.blob(), `reviewer_activity_${docId.slice(0, 8)}.csv`);
  },

  async getVisualAnnotations(docId, annotationType = null) {
    const params = new URLSearchParams();
    if (annotationType) params.set('annotation_type', annotationType);
    const r = await fetch(`${API_BASE}/api/documents/${docId}/annotations-visual?${params}`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load annotations' }));
    return r.json();
  },

  async exportVisualAnnotations(docId) {
    const r = await fetch(`${API_BASE}/api/documents/${docId}/annotations-visual/export`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Export failed' }));
    _downloadBlob(await r.blob(), `annotations_${docId.slice(0, 8)}.csv`);
  },

  async getAnnotationThread(linkToken, annotationId, sessionId) {
    const base = API_BASE.replace(/\/$/, '');
    const r = await fetch(
      `${base}/api/viewer/annotations/${encodeURIComponent(linkToken)}/${annotationId}/thread`,
      { headers: this.sessionHeaders(sessionId) }
    );
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load thread' }));
    return r.json();
  },

  // ── API Keys ──────────────────────────────────────────────────────────────
  async listApiKeys() {
    const r = await fetch(`${API_BASE}/api/api-keys`, { headers: { ...authHeaders() } });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load API keys' }));
    return r.json();
  },

  async createApiKey(name, scopes = [], expiresAt = null) {
    const body = { name, scopes };
    if (expiresAt) body.expires_at = expiresAt;
    const r = await fetch(`${API_BASE}/api/api-keys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to create API key' }));
    return r.json();
  },

  async revokeApiKey(keyId) {
    const r = await fetch(`${API_BASE}/api/api-keys/${keyId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ is_active: false }),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to revoke API key' }));
    return r.json();
  },

  async deleteApiKey(keyId) {
    const r = await fetch(`${API_BASE}/api/api-keys/${keyId}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to delete API key' }));
  },

  // ── Webhooks ──────────────────────────────────────────────────────────────
  async listWebhooks() {
    const r = await fetch(`${API_BASE}/api/webhooks`, { headers: { ...authHeaders() } });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load webhooks' }));
    return r.json();
  },

  async createWebhook(url, events, description = '') {
    const body = { url, events };
    if (description) body.description = description;
    const r = await fetch(`${API_BASE}/api/webhooks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to create webhook' }));
    return r.json();
  },

  async updateWebhook(webhookId, patch) {
    const r = await fetch(`${API_BASE}/api/webhooks/${webhookId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(patch),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to update webhook' }));
    return r.json();
  },

  async deleteWebhook(webhookId) {
    const r = await fetch(`${API_BASE}/api/webhooks/${webhookId}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to delete webhook' }));
  },

  async testWebhook(webhookId) {
    const r = await fetch(`${API_BASE}/api/webhooks/${webhookId}/test`, {
      method: 'POST',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Test ping failed' }));
    return r.json();
  },

  async getWebhookDeliveries(webhookId, limit = 50) {
    const r = await fetch(`${API_BASE}/api/webhooks/${webhookId}/deliveries?limit=${limit}`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load deliveries' }));
    return r.json();
  },

  // ── Audit Log ─────────────────────────────────────────────────────────────
  async getAuditLog(orgId = null, limit = 50, offset = 0) {
    const qs = new URLSearchParams({ limit, offset });
    if (orgId) qs.set('org_id', orgId);
    const r = await fetch(`${API_BASE}/api/admin/audit-log?${qs}`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load audit log' }));
    return r.json();
  },

  // ── Organizations ─────────────────────────────────────────────────────────
  async listOrgs() {
    const r = await fetch(`${API_BASE}/api/orgs`, { headers: { ...authHeaders() } });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load organizations' }));
    return r.json();
  },

  async createOrg(name) {
    const r = await fetch(`${API_BASE}/api/orgs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ name }),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to create organization' }));
    return r.json();
  },

  async updateOrg(orgId, patch) {
    const r = await fetch(`${API_BASE}/api/orgs/${orgId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(patch),
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to update organization' }));
    return r.json();
  },

  async deleteOrg(orgId) {
    const r = await fetch(`${API_BASE}/api/orgs/${orgId}`, {
      method: 'DELETE',
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to delete organization' }));
  },

  async listOrgMembers(orgId) {
    const r = await fetch(`${API_BASE}/api/orgs/${orgId}/members`, {
      headers: { ...authHeaders() },
    });
    if (r.status === 401) { _clearAndReload(); return; }
    if (!r.ok) throw await r.json().catch(() => ({ detail: 'Failed to load members' }));
    return r.json();
  },
};
