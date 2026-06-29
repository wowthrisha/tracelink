import { C } from '../constants/tokens.js';
import { SectionLabel, StatusDot } from './atoms.jsx';
import { useToast } from '../contexts/toast.jsx';

const { useState, useEffect } = React;

export function DocumentPicker({ onSelect }) {
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
              {(() => { const p = d.page_count ?? 0; const v = d.total_views || 0; return `${p} ${p === 1 ? 'page' : 'pages'} · ${v.toLocaleString()} ${v === 1 ? 'view' : 'views'}`; })()}
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
