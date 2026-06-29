import { C, mono } from '../../constants/tokens.js';
import { RiskBadge } from '../atoms.jsx';
const { useState } = React;

export function DocAnalyticsRow({ doc, isLast }) {
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
