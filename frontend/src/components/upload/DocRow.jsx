import { C, mono } from '../../constants/tokens.js';
import { fmtDate } from '../../utils/viewer.js';
import { StatusDot, RiskBadge, Btn } from '../atoms.jsx';

const { useState } = React;

export function DocRow({ doc, isLast, onView, onAccess, onDelete, onReprocess, onQuickShare, groups, onAssignGroup }) {
  const [hov, setHov] = useState(false);
  const isProcessing = doc.status === 'processing';
  const isError = doc.status === 'error';
  const isUploaded = doc.status === 'uploaded';
  const canRetry = isProcessing || isError || isUploaded;
  const canShare = doc.status === 'ready';
  // BUG-004: this used to read `doc.expires` (a field that has never existed
  // on the API response — the real field is `expires_at`), so this column
  // silently rendered '—' for every document regardless of its actual
  // retention expiry. It also compared against a hardcoded absolute date
  // instead of a rolling "expiring soon" window, matching AccessScreen.jsx's
  // link-expiry indicator pattern.
  const isExpired = doc.lifecycle_state === 'expired' || (doc.expires_at && new Date(doc.expires_at) < new Date());
  const expiringSoon = !isExpired && doc.expires_at && (new Date(doc.expires_at) - Date.now()) < 7 * 24 * 60 * 60 * 1000;
  return (
    <tr onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      onClick={onView}
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
        color: isExpired ? C.error : expiringSoon ? C.warning : doc.expires_at ? C.textSecondary : C.textMuted
      }}>
        {isExpired ? 'Expired' : doc.expires_at ? fmtDate(doc.expires_at) : '—'}
      </td>
      <td style={{ padding: '12px 14px' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', gap: 4, opacity: hov ? 1 : 0, transition: 'opacity .15s', alignItems: 'center' }}>
          {canRetry && <Btn variant="ghost" size="sm" onClick={onReprocess} style={{ color: C.warning }}>↺ Retry</Btn>}
          <Btn variant="ghost" size="sm" onClick={onView}>View</Btn>
          <Btn variant="ghost" size="sm" onClick={onAccess}>Access</Btn>
          {canShare
            ? <Btn variant="secondary" size="sm" onClick={() => onQuickShare(doc)}>↗ Share</Btn>
            : <Btn variant="secondary" size="sm" disabled>↗ Share</Btn>
          }
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
