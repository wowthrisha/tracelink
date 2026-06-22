import { C, mono } from '../../constants/tokens.js';
import { _errMsg } from '../../utils/viewer.js';
import { Btn, Modal } from '../atoms.jsx';

const { useState, useEffect } = React;

const QUICK_SHARE_DEFAULTS = {
  can_download: false,
  can_print: false,
  can_copy: false,
  can_right_click: false,
  watermark_enabled: true,
  can_annotate: false,
  enable_info: true,
};

export function QuickShareModal({ doc, onClose, onConfigure }) {
  const [phase, setPhase] = useState('loading'); // 'loading' | 'ready' | 'error'
  const [shareUrl, setShareUrl] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const createLink = async () => {
    setPhase('loading');
    setError(null);
    try {
      const result = await window.SecureDocAPI.createLink({
        document_id: doc.id,
        label: 'Quick Share',
        permissions: QUICK_SHARE_DEFAULTS,
      });
      setShareUrl(result.share_url);
      setPhase('ready');
    } catch (e) {
      setError(_errMsg(e, 'Failed to create share link'));
      setPhase('error');
    }
  };

  useEffect(() => { createLink(); }, [doc.id]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
    } catch {
      // clipboard failed — URL is still visible and selectable
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const docName = doc?.filename || doc?.name || 'Document';

  return (
    <Modal open title={`Share "${docName.length > 40 ? docName.slice(0, 40) + '…' : docName}"`} onClose={onClose} width={420}>
      {phase === 'loading' && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: '12px 0' }}>
          <div style={{ width: 22, height: 22, border: `2px solid ${C.teal2}`, borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
          <span style={{ fontSize: 12, color: C.textMuted }}>Creating share link…</span>
        </div>
      )}

      {phase === 'ready' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ fontSize: 11.5, color: C.textMuted, lineHeight: 1.5 }}>
            Share link created — watermark on, download off.
          </div>

          <div style={{
            background: C.surface2, border: `1px solid ${C.border}`,
            borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8
          }}>
            <div style={{
              ...mono, fontSize: 10.5, color: C.textSecondary,
              wordBreak: 'break-all', lineHeight: 1.5, userSelect: 'all'
            }}>
              {shareUrl}
            </div>
            <Btn
              variant={copied ? 'secondary' : 'primary'}
              size="sm"
              onClick={handleCopy}
              style={{ alignSelf: 'flex-start', minWidth: 100 }}
            >
              {copied ? '✓ Copied' : '⧉ Copy link'}
            </Btn>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <button
              onClick={() => { onClose(); onConfigure(doc); }}
              style={{
                background: 'none', border: 'none', padding: 0,
                fontSize: 11.5, color: C.teal2, cursor: 'pointer',
                textDecoration: 'underline', textUnderlineOffset: 3
              }}>
              Configure in Access Control →
            </button>
            <Btn variant="secondary" size="sm" onClick={onClose}>Done</Btn>
          </div>
        </div>
      )}

      {phase === 'error' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{
            background: C.errorBg, border: `1px solid ${C.errorBdr}`,
            borderRadius: 8, padding: '10px 12px', fontSize: 12, color: C.error, lineHeight: 1.5
          }}>
            {error}
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Btn variant="secondary" size="sm" onClick={onClose}>Cancel</Btn>
            <Btn variant="primary" size="sm" onClick={createLink}>Retry</Btn>
          </div>
        </div>
      )}
    </Modal>
  );
}
