import { C, mono } from '../constants/tokens.js';
import { _errMsg } from '../utils/viewer.js';
import { useToast } from '../contexts/toast.jsx';
import { SectionLabel, RiskBadge, StatusDot, Divider } from './atoms.jsx';

const { useState } = React;

export function ViewerInfoPanel({ doc, docId, page, session, pageCount, onSidecarExtract }) {
  const toast = useToast();
  const [extracting, setExtracting] = useState(false);
  const [extractDone, setExtractDone] = useState(false);
  const hasAuth = !!(typeof localStorage !== 'undefined' && localStorage.getItem?.('securedoc_token'));
  const effectiveDocId = doc?.id || (hasAuth ? session?.document_id : null);
  const canExtract = !!effectiveDocId && !extractDone;

  const handleExtract = async () => {
    const eid = doc?.id || session?.document_id;
    if (!eid) return;
    setExtracting(true);
    try {
      await window.SecureDocAPI.extractSidecars(eid);
      setExtractDone(true);
      onSidecarExtract?.();
    } catch (err) {
      toast(_errMsg(err, 'Failed to start extraction — try again.'), 'error');
    }
    finally { setExtracting(false); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Re-extract action — shown at top so it's always visible without scrolling */}
      {canExtract && (
        <div style={{
          background: extractDone ? 'rgba(80,190,120,0.07)' : 'rgba(90,200,208,0.07)',
          border: `1px solid ${extractDone ? 'rgba(80,190,120,0.25)' : 'rgba(90,200,208,0.22)'}`,
          borderRadius: 7, padding: '10px 12px',
        }}>
          <div style={{ fontSize: 11, color: extractDone ? C.success : C.teal2, fontWeight: 600, marginBottom: 6 }}>
            {extractDone ? '✓ Extraction complete' : '↺ Enable hyperlinks & highlights'}
          </div>
          {!extractDone && (
            <>
              <div style={{ fontSize: 10, color: C.textMuted, lineHeight: 1.55, marginBottom: 8 }}>
                Extract clickable links and word-level search highlights from this document.
              </div>
              <button
                onClick={handleExtract}
                disabled={extracting}
                style={{
                  width: '100%', padding: '6px 0', type: 'button',
                  background: extracting ? 'rgba(90,200,208,0.06)' : 'rgba(90,200,208,0.14)',
                  border: '1px solid rgba(90,200,208,0.3)', borderRadius: 5,
                  color: extracting ? C.textMuted : C.teal2,
                  fontSize: 11, fontWeight: 600, cursor: extracting ? 'default' : 'pointer',
                  fontFamily: "'DM Sans',sans-serif",
                }}>
                {extracting ? 'Extracting…' : 'Run extraction'}
              </button>
            </>
          )}
          {extractDone && (
            <div style={{ fontSize: 10, color: C.textMuted }}>
              Hyperlinks and word highlights are now active. If you don't see them, scroll to refresh.
            </div>
          )}
        </div>
      )}

      <div>
        <SectionLabel>Document Info</SectionLabel>
        <div style={{ marginTop: 8, fontSize: 12, fontWeight: 600, color: C.textPrimary, lineHeight: 1.5 }}>
          {doc?.name || session?.document_filename || 'Document'}
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
            { label: 'Annotations', ok: !!session?.permissions?.can_annotate },
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
